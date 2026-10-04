"""Campus Customs API: products, accounts and the shop assistant chat.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

Routes
    GET  /api/products               every product, with stock by size (cards on the Products page)
    GET  /api/products/{product_id}  one product with stock by size
    GET  /media/products/<file>      product photos
    POST /api/auth/register          create an account (and log in)
    POST /api/auth/login             log in
    POST /api/auth/logout            log out
    GET  /api/auth/me                who is logged in (or null)
    POST /api/chat                   one message to the shop assistant (agent.py)
    GET  /api/chat/history           a logged-in shopper's saved chat (guests: empty)
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

import agent
import tools
from models import (
    ChatHistory,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    ProductDetail,
    PublicUser,
    RegisterRequest,
)

log = logging.getLogger("campus_customs")
BACKEND_DIR = Path(__file__).resolve().parent
SESSION_DAYS = 7


def session_secret() -> str:
    """The key that signs login cookies. Kept out of git (backend/.session_secret)."""
    if os.environ.get("SESSION_SECRET"):
        return os.environ["SESSION_SECRET"]
    path = BACKEND_DIR / ".session_secret"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
        path.chmod(0o600)
    return path.read_text().strip()


app = FastAPI(title="Campus Customs API")
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret(),
    session_cookie="cc_session",
    max_age=SESSION_DAYS * 24 * 3600,
    same_site="lax",  # the cookie isn't sent on requests started by other websites
    https_only=os.environ.get("HTTPS_ONLY") == "1",  # turn on when served over https
)

# Only the photo folder is public. Never mount data/ itself: it holds the database.
app.mount("/media/products", StaticFiles(directory=tools.DATA_DIR / "products"), name="product-images")


# ===========================================================================
# Products
# ===========================================================================
@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/products")
def list_products() -> list[ProductDetail]:
    # Includes stock by size and search tags, for the site's "My size" badges and search box.
    return tools.all_product_details()


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> ProductDetail:
    product = tools.get_product(product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


# ===========================================================================
# Simple in-memory rate limits (reset when the server restarts)
# ===========================================================================
_events: dict[str, deque[float]] = defaultdict(deque)


def _count_recent(key: str, window: float) -> int:
    q = _events[key]
    while q and q[0] < time.monotonic() - window:
        q.popleft()
    return len(q)


def _record(*keys: str) -> None:
    now = time.monotonic()
    for k in keys:
        _events[k].append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ===========================================================================
# Accounts
# ===========================================================================
# New accounts: pbkdf2_sha256$<iterations>$<salt>$<hash>. 600,000 rounds is OWASP's
# current recommendation for PBKDF2-SHA256.
# Seed accounts already in the database: pbkdf2_sha256$<salt>$<hash> made with
# 120,000 rounds. They still verify, so the test user can log in.
ITERATIONS = 600_000
SEED_ITERATIONS = 120_000


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)  # 128 random bits, different for every account
    return f"pbkdf2_sha256${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256" and parts[1].isdigit():
        _, iterations, salt, expected = parts
        iterations = int(iterations)
    elif len(parts) == 3 and parts[0] == "pbkdf2_sha256":
        _, salt, expected = parts
        iterations = SEED_ITERATIONS
    else:
        return False
    # compare_digest takes the same time whether the first or last character differs.
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), expected)


# Checked when an email isn't found, so "no such account" takes as long as
# "wrong password" and response times don't reveal which emails exist.
_DUMMY_HASH = hash_password(secrets.token_hex(16))

LOGIN_WINDOW = 15 * 60
MAX_FAILS_PER_ACCOUNT = 5   # per email, from one address
MAX_FAILS_PER_ADDRESS = 20  # across all emails, from one address
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD, MAX_PASSWORD = 8, 128
PUBLIC_COLUMNS = "id, name, email, first_name, last_name"


def _public(row: sqlite3.Row) -> PublicUser:
    # Seed users may only have `name`; fall back to splitting it.
    first, _, last = row["name"].partition(" ")
    return PublicUser(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        name=row["name"],
        email=row["email"],
    )


def current_user(request: Request) -> PublicUser | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    with closing(tools.connect()) as conn:
        row = conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        request.session.clear()
        return None
    return _public(row)


def _start_session(request: Request, user_id: int) -> None:
    request.session.clear()
    request.session["user_id"] = user_id


@app.post("/api/auth/register")
def register(body: RegisterRequest, request: Request) -> PublicUser:
    first, last = body.first_name.strip(), body.last_name.strip()
    email = body.email.strip().lower()

    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if len(first) > 50 or len(last) > 50:
        raise HTTPException(400, "Names can be up to 50 characters.")
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if not MIN_PASSWORD <= len(body.password) <= MAX_PASSWORD:
        raise HTTPException(400, f"Passwords need {MIN_PASSWORD} to {MAX_PASSWORD} characters.")

    password_hash = hash_password(body.password)
    taken = "An account with that email already exists. Try logging in instead."
    with closing(tools.connect(write=True)) as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(409, taken)
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, password_hash, first, last),
            )
            conn.commit()
        except sqlite3.IntegrityError:  # two sign-ups for the same email at the same moment
            raise HTTPException(409, taken)
        row = conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()

    _start_session(request, row["id"])
    return _public(row)


@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request) -> PublicUser:
    email = body.email.strip().lower()
    ip = _client_ip(request)
    account_key, address_key = f"login|{ip}|{email}", f"login|{ip}"
    if (
        _count_recent(account_key, LOGIN_WINDOW) >= MAX_FAILS_PER_ACCOUNT
        or _count_recent(address_key, LOGIN_WINDOW) >= MAX_FAILS_PER_ADDRESS
    ):
        raise HTTPException(429, "Too many attempts. Please wait a few minutes and try again.")

    with closing(tools.connect()) as conn:
        row = conn.execute(
            f"SELECT {PUBLIC_COLUMNS}, password_hash FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _record(account_key, address_key)
        # Same message either way, so it doesn't reveal which emails have accounts.
        raise HTTPException(401, "That email and password don't match our records.")

    _start_session(request, row["id"])
    return _public(row)


@app.post("/api/auth/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
def me(request: Request) -> PublicUser | None:
    return current_user(request)


# ===========================================================================
# Chat with the shop assistant
# ===========================================================================
CHAT_WINDOW = 5 * 60
MAX_CHATS_PER_ADDRESS = 30  # keeps one visitor from running up the AI bill


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    key = f"chat|{_client_ip(request)}"
    if _count_recent(key, CHAT_WINDOW) >= MAX_CHATS_PER_ADDRESS:
        raise HTTPException(429, "You're sending messages very quickly. Please wait a minute and try again.")
    _record(key)

    user = current_user(request)
    # Sensitive-info shield: card numbers, security codes, passwords and SSNs are removed
    # here, before the message can reach the AI model, the saved chat history or any log.
    message, removed = tools.redact_sensitive(body.message.strip())
    # Logged in: the conversation comes from the database (their saved chat), not the browser.
    # Guest: nothing is saved, so the widget sends the recent turns itself (shielded too).
    if user:
        history = tools.recent_turns(user.id)
    else:
        history = [t.model_copy(update={"content": tools.redact_sensitive(t.content)[0]}) for t in body.history]
    page = tools.resolve_page(body.page)

    try:
        response = await agent.chat(message, history, user, page, removed)
    except agent.MissingApiKey:
        log.error("Chat is off: no OPENAI_API_KEY found")
        raise HTTPException(503, "The shop assistant isn't switched on right now. Please try again later.")
    except (UsageLimitExceeded, UnexpectedModelBehavior, ModelHTTPError):
        log.exception("Shop assistant could not answer")
        raise HTTPException(502, "Sorry, I got a little tangled up on that one. Could you try asking another way?")
    except Exception:
        log.exception("Shop assistant failed")
        raise HTTPException(502, "Sorry, I'm having trouble right now. Please try again in a moment.")

    if removed:
        response.removed, response.message_shown = removed, message
    if user:
        tools.save_chat_exchange(user.id, message, response)  # the shielded version, never the original
    return response


@app.get("/api/chat/history")
def chat_history(request: Request) -> ChatHistory:
    user = current_user(request)
    if user is None:
        return ChatHistory(saved=False, messages=[])
    return ChatHistory(saved=True, messages=tools.load_chat_history(user.id))
