"""Tools the shop assistant can call, and the database reads behind them.

The website's product pages (main.py) and the agent read products through the
same functions here, so the chatbot can never see a different price or stock
count from the one on the page.
"""

import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic_ai import ModelRetry, RunContext

from models import (
    Category,
    ChatDeps,
    ChatResponse,
    ChatTurn,
    PageContext,
    ProductDetail,
    ProductMatch,
    ProductSearchResult,
    ProductSummary,
    SavedMessage,
    SimilarProducts,
    SizeStatus,
    SizeStock,
    StockCheck,
    ViewedPage,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# CAMPUS_CUSTOMS_DB lets tests point at a throwaway copy instead of the real database.
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs.db"))
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_SEARCH_RESULTS = 8
LOW_STOCK = 5  # "only N left" at or below this, same as the product page

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def connect(write: bool = False) -> sqlite3.Connection:
    """Read-only unless the caller needs to write (only account creation does)."""
    mode = "rw" if write else "ro"
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def category_for(garment_type: str) -> Category:
    """Group the 22 different garment_type spellings into five shelves."""
    g = garment_type.lower()
    if "t-shirt" in g or ("shirt" in g and "sweatshirt" not in g):
        return "Tees & tops"
    if "quarter-zip" in g:
        return "Quarter-zips"
    if "jacket" in g:
        return "Jackets"
    if "hood" in g:
        return "Hoodies"
    return "Crewnecks"


PRODUCT_QUERY = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
    FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
"""


def _summary(row: sqlite3.Row) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=category_for(row["garment_type"]),
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=f"/media/{row['image_file_path']}",
        total_stock=row["total_stock"],
    )


def _size_key(size: str) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)


def list_products() -> list[ProductSummary]:
    with closing(connect()) as conn:
        rows = conn.execute(PRODUCT_QUERY + " GROUP BY c.product_id ORDER BY c.name").fetchall()
    return [_summary(r) for r in rows]


def all_product_details() -> list[ProductDetail]:
    """Every product with its stock by size (102 products, so this is quick)."""
    with closing(connect()) as conn:
        rows = conn.execute(PRODUCT_QUERY + " GROUP BY c.product_id ORDER BY c.name").fetchall()
        stock = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    sizes: dict[str, list[SizeStock]] = {}
    for s in sorted(stock, key=lambda s: _size_key(s["size"])):
        sizes.setdefault(s["product_id"], []).append(SizeStock(size=s["size"], quantity=s["quantity"]))
    return [
        ProductDetail(
            **_summary(r).model_dump(),
            search_tags=json.loads(r["search_tags"]),
            inventory=sizes.get(r["product_id"], []),
        )
        for r in rows
    ]


def get_product(product_id: str) -> ProductDetail | None:
    with closing(connect()) as conn:
        row = conn.execute(PRODUCT_QUERY + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)).fetchone()
        if row is None:
            return None
        stock = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    return ProductDetail(
        **_summary(row).model_dump(),
        search_tags=json.loads(row["search_tags"]),
        inventory=[SizeStock(size=s["size"], quantity=s["quantity"]) for s in sorted(stock, key=lambda s: _size_key(s["size"]))],
    )


def product_match(p: ProductDetail, size: str | None = None) -> ProductMatch:
    """A product card's worth of facts, taken from the database record."""
    in_size = next((s.quantity for s in p.inventory if s.size == size), None) if size else None
    return ProductMatch(
        product_id=p.product_id,
        name=p.name,
        price=p.price,
        image_url=p.image_url,
        description=p.description,
        category=p.category,
        in_stock=p.total_stock > 0,
        size=size if in_size is not None else None,
        size_quantity=in_size,
        inventory=p.inventory,
    )


def product_matches(product_ids: list[str], size: str | None = None) -> list[ProductMatch]:
    """Cards for these ids, in the same order, read fresh from the database. Unknown ids are skipped."""
    by_id = {p.product_id: p for p in all_product_details()}
    return [product_match(by_id[pid], size) for pid in product_ids if pid in by_id]


# ---------------------------------------------------------------------------
# Stock by size
# ---------------------------------------------------------------------------
# What shoppers type -> the size names used in the inventory table.
SIZE_WORDS = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "2xlarge": "XXL",
}


def normalize_size(text: str | None) -> str | None:
    """'small' -> 'S', 'x-large' -> 'XL', '2XL' -> 'XXL'. None if it isn't a size we stock."""
    if not text:
        return None
    key = re.sub(r"[^a-z0-9]", "", text.lower())
    return SIZE_WORDS.get(key)


def _status(quantity: int) -> str:
    if quantity == 0:
        return "sold out"
    if quantity <= LOW_STOCK:
        return f"only {quantity} left"
    return "in stock"


def stock_check(product_id: str, size: str | None = None) -> StockCheck | str:
    product = get_product(product_id)
    if product is None:
        return f"No product has the id {product_id!r}. Search for it instead."
    asked = normalize_size(size) if size else None
    if size and asked is None:
        return f"We don't stock a size called {size!r}. Our sizes are XS, S, M, L, XL and XXL."

    sizes = [SizeStatus(size=s.size, quantity=s.quantity, status=_status(s.quantity)) for s in product.inventory]
    in_stock = [s.size for s in sizes if s.quantity > 0]
    sold_out = [s.size for s in sizes if s.quantity == 0]
    asked_qty = next((s.quantity for s in sizes if s.size == asked), None) if asked else None

    parts = []
    if asked:
        if asked_qty is None:
            parts.append(f"There is no size {asked} listed for this item.")
        elif asked_qty == 0:
            parts.append(f"Size {asked} is SOLD OUT.")
        else:
            parts.append(f"Size {asked} is in stock ({asked_qty} left).")
    parts.append(
        "In stock: " + ", ".join(f"{s.size} ({s.quantity})" for s in sizes if s.quantity > 0) + "."
        if in_stock else "Sold out in every size."
    )
    if sold_out and in_stock:
        parts.append("Sold out: " + ", ".join(sold_out) + ".")

    return StockCheck(
        product_id=product.product_id,
        name=product.name,
        price=product.price,
        asked_size=asked,
        asked_size_quantity=asked_qty,
        sizes=sizes,
        in_stock_sizes=in_stock,
        sold_out_sizes=sold_out,
        summary=" ".join(parts),
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
STOPWORDS = {
    "a", "an", "and", "any", "anything", "are", "can", "do", "for", "have", "i", "im", "in", "is", "it",
    "looking", "me", "my", "need", "of", "on", "one", "or", "show", "some", "something", "that", "the",
    "to", "want", "what", "with", "you", "your", "got", "sell", "carry",
}
# A shopper's word -> words the catalogue uses for the same thing.
SYNONYMS = {
    "tee": {"shirt"}, "tshirt": {"shirt"}, "hoody": {"hoodie", "hood"}, "hoodie": {"hoodie", "hood", "hooded"},
    "sweater": {"sweater", "sweatshirt", "crewneck"}, "crew": {"crew", "crewneck"}, "grey": {"gray"},
    "zip": {"zip", "quarter"}, "jumper": {"sweatshirt", "crewneck"}, "mother": {"mom"}, "father": {"dad"},
    "grandmother": {"grandma"}, "grandfather": {"grandpa"},
}


# On (almost) every product, so they can't narrow a search down.
EVERYWHERE_WORDS = {"yale", "campus", "campu", "custom", "merch"}


def _words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # hoodies -> hoodie, moms -> mom
        out.add(w)
    return out


def _haystack(p: ProductDetail) -> set[str]:
    return _words(" ".join([p.name, p.garment_type, p.description, *p.colors, *p.search_tags]))


def _hits(term: str, words: set[str]) -> bool:
    return bool(({term} | SYNONYMS.get(term, set())) & words)


def _rank(products: list[ProductDetail], terms: set[str]) -> list[ProductDetail]:
    """Products that match ALL the shopper's words, best first.

    Words no product in the whole catalogue mentions (like "gift") can't narrow anything
    down, so they're ignored. If nothing matches every word, fall back to products that
    match the most words, so a search never comes back empty just for being specific.
    """
    catalogue = [_haystack(p) for p in all_product_details()]
    known = {t for t in terms if any(_hits(t, h) for h in catalogue)}
    if not known:
        return []  # e.g. "socks": nothing we sell matches
    scored = []
    for p in products:
        words, name = _haystack(p), _words(p.name)
        score = sum(_hits(t, words) for t in known)
        if score:
            scored.append((score, sum(_hits(t, name) for t in known), p))
    best = [x for x in scored if x[0] == len(known)] or scored
    best.sort(key=lambda x: (-x[0], -x[1], x[2].name))  # more words, then words in the name
    return [p for _, _, p in best]


def _same_color(wanted: str, colors: list[str]) -> bool:
    """'navy' matches 'navy blue'; 'grey' matches 'heather gray'."""
    want = _words(wanted) - {"color", "colour"}
    want = {"gray" if w == "grey" else w for w in want}
    return any(want <= _words(c) for c in colors)


def find_matches(
    query: str | None = None,
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> tuple[list[ProductDetail], list[ProductDetail]]:
    """Every matching product, best first, split into (available in the size asked for, sold out in it)."""
    products = all_product_details()
    if category:
        products = [p for p in products if p.category == category]
    if color:
        products = [p for p in products if _same_color(color, p.colors)]
    if max_price is not None:
        products = [p for p in products if p.price <= max_price]

    terms = _words(query or "") - STOPWORDS - EVERYWHERE_WORDS
    if terms:
        products = _rank(products, terms)

    # A size filter must never make a real product look like it doesn't exist:
    # matches that are sold out in that size come back separately.
    sold_out: list[ProductDetail] = []
    if size:
        wanted = normalize_size(size) or size.strip().upper()
        in_size = [p for p in products if any(s.size == wanted and s.quantity > 0 for s in p.inventory)]
        sold_out = [p for p in products if p not in in_size]
        products = in_size
    return products, sold_out


def search_catalogue(
    query: str | None = None,
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    limit: int = MAX_SEARCH_RESULTS,
    search_id: int = 1,
) -> ProductSearchResult:
    """What the agent sees: the best few matches in full, plus the total."""
    products, sold_out = find_matches(query, category, color, max_price, size)
    return ProductSearchResult(
        search_id=search_id,
        total_matches=len(products),
        products=products[:limit],
        sold_out_in_requested_size=sold_out[:3],
    )


# ---------------------------------------------------------------------------
# Similar products (Problem 9): in-stock alternatives instead of a dead end
# ---------------------------------------------------------------------------
# A word only counts as a shared theme (hockey, mom, Saybrook, vintage...) if few products
# have it. Words on lots of products (hoodie, navy, left chest) say little about likeness.
MAX_THEME_PRODUCTS = 12


FAMILY_WORDS = {"mom", "dad", "grandma", "grandpa", "aunt", "uncle", "brother", "sister", "cousin", "parent"}
# How a garment is made, not what it's about: a kangaroo pocket doesn't make two hoodies alike.
CONSTRUCTION_WORDS = {"drawstring", "hood", "hooded", "kangaroo", "pocket", "ribbed", "cuff", "hem", "zip", "pullover",
                      "crew", "crewneck", "chest", "left", "sleeve", "long", "short", "tee", "shirt", "t", "fleece"}


def _theme_words(p: ProductDetail) -> set[str]:
    words = _words(" ".join(p.search_tags + [p.name])) - STOPWORDS - EVERYWHERE_WORDS - CONSTRUCTION_WORDS
    if words & FAMILY_WORDS:
        words.add("family")  # a Yale Mom Hoodie is like a Yale Dad Hoodie
    return words


def _rare_words(products: list[ProductDetail]) -> set[str]:
    counts: dict[str, int] = {}
    for p in products:
        for w in _theme_words(p):
            counts[w] = counts.get(w, 0) + 1
    return {w for w, n in counts.items() if n <= MAX_THEME_PRODUCTS} | {"family"}


def _color_words(p: ProductDetail) -> set[str]:
    return {"gray" if w == "grey" else w for c in p.colors for w in _words(c)} - {"heather", "dark", "light"}


def similar_to(product_id: str, size: str | None = None, limit: int = 4) -> tuple[ProductDetail, list[tuple[ProductDetail, str]]] | str:
    """The products most like this one: same shelf, shared colors, shared themes (sport, college, family...).

    With a size, only products in stock in that size are suggested, so every suggestion can actually be bought.
    """
    products = all_product_details()
    base = next((p for p in products if p.product_id == product_id), None)
    if base is None:
        return f"No product has the id {product_id!r}. Search for it instead."
    wanted = normalize_size(size) if size else None
    if size and wanted is None:
        return f"We don't stock a size called {size!r}. Our sizes are XS, S, M, L, XL and XXL."

    rare = _rare_words(products)
    base_themes = _theme_words(base) & rare
    base_colors = _color_words(base)
    scored = []
    for p in products:
        if p.product_id == base.product_id:
            continue
        if wanted and not any(s.size == wanted and s.quantity > 0 for s in p.inventory):
            continue
        reasons, score = [], 0.0
        if p.category == base.category:
            score += 3
            reasons.append(f"also {p.category.lower()}")
        themes = sorted(base_themes & _theme_words(p))
        if themes:
            score += 3 * len(themes)
            reasons.append("same theme: " + ", ".join(themes[:3]))
        colors = sorted(base_colors & _color_words(p))
        if colors:
            score += len(colors)
            reasons.append("same colors: " + ", ".join(colors))
        if p.price == base.price:
            score += 0.5
            reasons.append("same price")
        if score >= 3:  # at least the same shelf, or a strong shared theme
            scored.append((score, -abs(p.price - base.price), p, "; ".join(reasons)))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2].name))
    return base, [(p, why) for _, _, p, why in scored[:limit]]


# ---------------------------------------------------------------------------
# Sensitive-info shield (Problem 9)
# ---------------------------------------------------------------------------
# Runs on every chat message before it reaches the AI model, the saved chat history
# or the logs. Shoppers sometimes paste things that should never be stored.
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SECRET_PATTERNS = [
    (re.compile(r"\b(cvv|cvc|cv2|security code)\b\W{0,3}(?:is\W{0,3})?\d{3,4}\b", re.IGNORECASE), r"\1 [removed]", "a card security code"),
    (re.compile(r"\b(password|passcode|pwd)\b(\s*(?:is|was|:|=)\s*)\S+", re.IGNORECASE), r"\1\2[removed]", "a password"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[number removed]", "a Social Security number"),
]


def _luhn_ok(digits: str) -> bool:
    """The checksum every real payment card number passes (so order numbers and phone numbers don't trip it)."""
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total, double = total + d, not double
    return total % 10 == 0


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    """Remove card numbers, security codes, passwords and SSNs. Returns (clean text, what was removed)."""
    removed: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            removed.append("a card number")
            return "[card number removed]"
        return m.group()

    text = _CARD_RE.sub(card, text)
    for pattern, replacement, label in _SECRET_PATTERNS:
        text, n = pattern.subn(replacement, text)
        if n:
            removed.append(label)
    return text, list(dict.fromkeys(removed))


# ---------------------------------------------------------------------------
# Page context: what the shopper is looking at
# ---------------------------------------------------------------------------
PAGE_KINDS = {"": "home", "products": "products", "about": "about", "login": "login", "create-account": "create-account"}


def resolve_page(page: PageContext | None) -> ViewedPage | None:
    """Turn what the browser says into facts the agent can trust.

    Only a product_id that exists in the catalogue gets through, and its name is read from the
    database, so nothing typed into the browser reaches the agent's context as-is.
    """
    if page is None:
        return None
    parts = [x for x in page.path.split("?")[0].split("/") if x]
    product_id = page.product_id or (parts[1] if len(parts) == 2 and parts[0] == "products" else None)
    product = get_product(product_id) if product_id else None
    if product:
        return ViewedPage(kind="product", product_id=product.product_id, product_name=product.name, my_size=page.my_size)
    kind = PAGE_KINDS.get(parts[0] if parts else "", "other") if len(parts) <= 1 else "other"
    return ViewedPage(kind=kind, category=page.category if kind == "products" else None, my_size=page.my_size)


# ---------------------------------------------------------------------------
# Chat history for logged-in shoppers (the chat_messages table)
# ---------------------------------------------------------------------------
MAX_SAVED_CHARS = 4000  # ChatTurn's limit


def save_chat_exchange(user_id: int, message: str, response: ChatResponse) -> None:
    """Save the shopper's message and the assistant's reply, together or not at all."""
    cards = json.dumps([m.model_dump() for m in response.products])
    with closing(connect(write=True)) as conn, conn:  # `with conn` commits both rows at once
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message)
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, response.reply, cards),
        )


def _rows(user_id: int, limit: int) -> list[sqlite3.Row]:
    """The shopper's most recent messages, oldest first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_chat_history(user_id: int, limit: int = 50) -> list[SavedMessage]:
    """For the chat panel. Cards are rebuilt from today's catalogue, so a reloaded card never shows an old price."""
    messages = []
    for r in _rows(user_id, limit):
        try:
            saved = json.loads(r["products_json"] or "[]")
            ids = [c["product_id"] for c in saved if isinstance(c, dict) and "product_id" in c]
        except (ValueError, TypeError):
            ids = []
        messages.append(
            SavedMessage(role=r["role"], content=r["content"], products=product_matches(ids), created_at=r["created_at"])
        )
    return messages


def recent_turns(user_id: int, limit: int = 20) -> list[ChatTurn]:
    """For the agent: the saved conversation, read from the database rather than trusted from the browser."""
    return [
        ChatTurn(role=r["role"], content=r["content"][:MAX_SAVED_CHARS])
        for r in _rows(user_id, limit)
        if r["role"] in ("user", "assistant")
    ]


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------
# Each tool notes the prices and stock numbers it hands the agent in ctx.deps,
# so agent.py can check that every number in the reply came from the database.


# Safety: tools only run on legitimate inputs. A bad input raises ModelRetry, which tells
# the agent what was wrong; after 2 failed retries the run stops safely instead of looping.
_PRODUCT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_QUERY_CHARS = 120


def _check_product_id(product_id: str) -> str:
    pid = (product_id or "").strip()
    if not pid or len(pid) > 120 or not _PRODUCT_ID_RE.match(pid):
        raise ModelRetry(
            f"{product_id!r} isn't a product_id. Use a product_id exactly as a search result gave it, "
            "e.g. 'basic-hoodie-big-yale', or search for the product first."
        )
    return pid


def _check_search(query: str | None, color: str | None, max_price: float | None) -> None:
    if query and len(query) > MAX_QUERY_CHARS:
        raise ModelRetry(f"Keep the search query under {MAX_QUERY_CHARS} characters: a few words the shopper used.")
    if color and len(color) > 40:
        raise ModelRetry("color should be a single color name, like 'navy' or 'gray'.")
    if max_price is not None and not 0 < max_price <= 1000:
        raise ModelRetry("max_price must be a dollar amount between 1 and 1000.")


def _remember(ctx: RunContext[ChatDeps], products: list[ProductDetail]) -> None:
    for p in products:
        ctx.deps.seen_product_ids.add(p.product_id)
        ctx.deps.seen_prices.add(p.price)
        ctx.deps.seen_quantities.add(p.total_stock)
        ctx.deps.seen_quantities.update(s.quantity for s in p.inventory)


def search_products(
    ctx: RunContext[ChatDeps],
    query: str | None = None,
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> ProductSearchResult:
    """Search the Campus Customs catalogue. Every filter is optional; combine them as needed.

    Args:
        query: Words describing what the shopper wants, e.g. "hockey", "Yale Mom", "Saybrook", "vintage bulldog".
        category: Limit to one shelf of the shop.
        color: A color the product must come in, e.g. "navy", "gray", "white".
        max_price: Highest price in US dollars.
        size: Only products in stock in this size: XS, S, M, L, XL or XXL.

    Returns up to 8 products, best match first, each with its real price, description, colors
    and stock by size, plus total_matches (how many matched in all). When a size is given,
    products that match but are sold out in that size are listed in sold_out_in_requested_size.
    Each search has a search_id: put it in show_on_page to show ALL its matches on the website.
    """
    _check_search(query, color, max_price)
    search_id = len(ctx.deps.searches) + 1
    matches, _ = find_matches(query, category, color, max_price, size)
    ctx.deps.searches[search_id] = [p.product_id for p in matches]  # the full list, for the page
    result = search_catalogue(query, category, color, max_price, size, search_id=search_id)
    _remember(ctx, result.products + result.sold_out_in_requested_size)
    ctx.deps.seen_quantities.add(result.total_matches)
    return result


def get_product_details(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetail | str:
    """Look up one product by its product_id: its description, price, colors and stock in every size.

    Args:
        product_id: The product_id from a search result, e.g. "basic-hoodie-big-yale".
    """
    product = get_product(_check_product_id(product_id))
    if product is None:
        return f"No product has the id {product_id!r}. Search for it instead."
    _remember(ctx, [product])
    return product


def check_stock(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> StockCheck | str:
    """Check how many of one product are in stock, size by size, straight from the inventory table.

    Use this whenever a shopper asks whether something is available, how many are left,
    or about a particular size. The summary says plainly which sizes are sold out.

    Args:
        product_id: The product_id from a search result, e.g. "fencing-left-chest-hoodie".
        size: The size the shopper asked about, if any: XS, S, M, L, XL or XXL ("small", "2XL" also work).
    """
    result = stock_check(_check_product_id(product_id), size)
    if isinstance(result, StockCheck):
        product = get_product(result.product_id)
        if product:
            _remember(ctx, [product])
    return result


def find_similar_products(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> SimilarProducts | str:
    """Find the products most like one product: same shelf, shared colors and themes (sport, college, family).

    Use it when the size a shopper wants is sold out, or when they ask for "something like this",
    "similar" or "other options". Pass the size they need, and every suggestion will be in stock in it.

    Args:
        product_id: The product to find alternatives to, e.g. "ice-hockey-left-chest-hoodie".
        size: The size the alternatives must be in stock in, if the shopper gave one.
    """
    found = similar_to(_check_product_id(product_id), size)
    if isinstance(found, str):
        return found
    base, alternatives = found
    search_id = len(ctx.deps.searches) + 1
    ctx.deps.searches[search_id] = [p.product_id for p, _ in alternatives]  # so they can go on the page too
    _remember(ctx, [base] + [p for p, _ in alternatives])
    return SimilarProducts(
        search_id=search_id,
        based_on=base.name,
        size=normalize_size(size) if size else None,
        alternatives=[p for p, _ in alternatives],
        why=[why for _, why in alternatives],
    )


AGENT_TOOLS = [search_products, get_product_details, check_stock, find_similar_products]
