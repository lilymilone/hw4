"""Campus Customs shop assistant: builds the PydanticAI agent and answers one chat message.

main.py calls `chat()` for every message sent from the website's chat widget.
How the agent behaves (voice, honesty and safety rules, how to use its tools) lives
in prompts/prompt.md, which is loaded as the agent's instructions. Every run is
recorded in output/audit_trail.json (append-only).
"""

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep the server log clean

from pydantic_ai import Agent, ModelRetry, RunContext, UsageLimits
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import (
    AgentReply,
    AuditRecord,
    AuditStep,
    ChatDeps,
    ChatResponse,
    ChatTurn,
    PageResults,
    ProductDetail,
    ProductSearchResult,
    PublicUser,
    SimilarProducts,
    StockCheck,
    StopReason,
    ViewedPage,
)
from tools import AGENT_TOOLS, product_matches

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# A mid-priced model is enough for a shop chat that looks everything up with tools.
# Set CHAT_MODEL to try another (gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, gpt-6-astra).
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.6-terra")
# Loop limits for one shopper message. When one is hit the run stops safely (the shopper
# gets a polite "try asking another way") instead of looping or running up the bill.
MAX_MODEL_REQUESTS = 6   # model calls: a few tool rounds, then the answer
MAX_TOOL_CALLS = 10      # tool calls in total
MAX_TOKENS = 120_000     # tokens in total (normal messages used about 5,000 to 22,000 in testing)
TOOL_RETRIES = 2         # a tool given bad input, or a reply that fails a check, gets 2 more tries
CALL_TIMEOUT = 60        # seconds for any one call to OpenAI
LIMITS = UsageLimits(request_limit=MAX_MODEL_REQUESTS, tool_calls_limit=MAX_TOOL_CALLS, total_tokens_limit=MAX_TOKENS)
MAX_CARDS = 6            # small cards under a chat reply
MAX_PAGE_RESULTS = 48    # cards on the page (the biggest shelf has 29)

log = logging.getLogger("campus_customs")


class MissingApiKey(RuntimeError):
    pass


def _read_env_file(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip("\"'")
    return values


def openai_api_key() -> str:
    """OPENAI_API_KEY from the environment, else the nearest .env file in backend/ or a folder above it."""
    if os.getenv("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    for folder in (BACKEND_DIR, *BACKEND_DIR.parents):
        env_file = folder / ".env"
        if env_file.is_file():
            key = _read_env_file(env_file).get("OPENAI_API_KEY")
            if key:
                return key
    raise MissingApiKey("No OPENAI_API_KEY found in the environment or a .env file.")


def load_prompt() -> str:
    return PROMPT_PATH.read_text()


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, AgentReply]:
    """Built on the first chat message, so the shop still runs if the key is missing."""
    model = OpenAIResponsesModel(
        CHAT_MODEL,
        provider=OpenAIProvider(api_key=openai_api_key()),
        settings={"timeout": CALL_TIMEOUT},
    )
    agent = Agent(
        model,
        deps_type=ChatDeps,
        output_type=AgentReply,
        tools=AGENT_TOOLS,
        retries=TOOL_RETRIES,
    )

    @agent.instructions
    def system_prompt() -> str:
        # Read on every message, so edits to prompt.md apply without a restart.
        return load_prompt()

    # Dynamic instructions: code that runs before every model call and puts what it
    # returns into the agent's context, built from this message's deps.
    @agent.instructions
    def who_is_chatting(ctx: RunContext[ChatDeps]) -> str:
        s = ctx.deps.shopper
        if s:
            return (
                "## Who you're talking to\n"
                f"A logged-in customer: {s.first_name} {s.last_name}, email {s.email} (customer #{s.id}). "
                "Their earlier messages with you are saved to their account, so you can refer back to them."
            )
        return (
            "## Who you're talking to\n"
            "A guest who isn't logged in. You don't know their name or email, and this chat isn't saved. "
            "If they ask, they can log in or create an account to have you remember them."
        )

    @agent.instructions
    def where_they_are(ctx: RunContext[ChatDeps]) -> str:
        page = ctx.deps.page
        if page is None:
            return ""
        if page.kind == "product":
            return (
                "## What they're looking at\n"
                f'They are on the product page for "{page.product_name}" (product_id: {page.product_id}). '
                'If they say "this", "it", "this one" or ask about a color, size, price or stock without naming '
                "a product, they mean this one. Look it up with get_product_details or check_stock using that "
                "product_id before you answer."
            ) + _my_size_note(page)
        if page.kind == "products" and page.category:
            note = f"## What they're looking at\nThey are browsing the {page.category} shelf on the Products page."
        else:
            note = f"## What they're looking at\nThey are on the {page.kind} page of the website."
        return note + _my_size_note(page)

    @agent.instructions
    def what_the_shield_removed(ctx: RunContext[ChatDeps]) -> str:
        if not ctx.deps.removed:
            return ""
        return (
            "## Removed for safety\n"
            f"Before this message reached you, the website removed {' and '.join(ctx.deps.removed)} from it "
            "(you'll see [removed] in its place). It was not saved or sent anywhere. In one short, kind sentence, "
            "tell the shopper they never need to share that in chat, then help with the rest of their message."
        )

    @agent.output_validator
    def numbers_come_from_the_database(ctx: RunContext[ChatDeps], out: AgentReply) -> AgentReply:
        page_title = out.show_on_page.title if out.show_on_page else ""
        invented = unsupported_numbers(f"{out.reply}\n{page_title}", ctx.deps)
        if invented:
            raise ModelRetry(
                f"Your reply states {', '.join(invented)}, but no database tool returned that number during "
                "this message. Look it up with check_stock, get_product_details or search_products and use "
                "only the exact prices and stock counts they return. Don't estimate, round or add up totals."
            )
        return out

    @agent.output_validator
    def no_claims_of_actions_that_did_not_happen(ctx: RunContext[ChatDeps], out: AgentReply) -> AgentReply:
        claim = ACTION_CLAIM_RE.search(out.reply)
        if claim:
            raise ModelRetry(
                f'Your reply says "{claim.group(0)}", but you can\'t do that: this shop chat has no cart, '
                "ordering, holds, refunds or messaging, and you can't change anything. Don't claim an action "
                "happened; say what you can do instead (look things up, show products on the page)."
            )
        if PAGE_CLAIM_RE.search(out.reply) and not _page_ids(out, ctx.deps):
            raise ModelRetry(
                "Your reply says products are on the page, but show_on_page doesn't point at a search that "
                "found products. Set show_on_page with the search_id of a search that found matches, or "
                "don't say anything is on the page."
            )
        return out

    return agent


# ---------------------------------------------------------------------------
# The "never claim an action that didn't happen" check
# ---------------------------------------------------------------------------
ACTION_CLAIM_RE = re.compile(
    r"\b(added (?:it |them |that |this )?to (?:your |the )?cart"
    r"|placed (?:your|the|an) order|(?:your )?order (?:is|has been|was) (?:placed|confirmed)"
    r"|reserved (?:it|them|one|that|this|a)\b|(?:put|placed|kept) (?:it|them|one|that) on hold"
    r"|held (?:it|them|one|that) for you|refund (?:is|has been|was) (?:processed|issued)"
    r"|i(?:'|’)?ve (?:emailed|texted|messaged|sent you|updated|changed|saved)"
    r"|i (?:emailed|texted|updated the (?:price|stock)|changed the (?:price|stock)))",
    re.IGNORECASE,
)
PAGE_CLAIM_RE = re.compile(
    r"\b(?:put|placed|added|shown?|showing|pulled up|listed|loaded)\b[^.!?\n]{0,60}\bon the page\b"
    r"|\bon the page (?:for you|now)\b",
    re.IGNORECASE,
)


def _my_size_note(page: ViewedPage) -> str:
    if not page.my_size:
        return ""
    return (
        f"\nThey set their size to {page.my_size} with the site's \"My size\" picker. If they ask about stock or "
        f"\"my size\" without naming a size, use {page.my_size}."
    )


# ---------------------------------------------------------------------------
# The "never invent a price or quantity" check
# ---------------------------------------------------------------------------
# Every dollar amount and stock count in a reply must be a number a database tool
# returned during this message (or one the shopper typed, like "under $60").
# Anything else sends the reply back to the agent to fix before the shopper sees it.
PRICE_RE = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")
_SIZE = r"(?:XXL|XL|XS|S|M|L)"
QUANTITY_RES = [
    re.compile(r"\b(\d+)\s+(?:left|remaining|in stock|available|units?|pieces?)\b", re.IGNORECASE),
    re.compile(r"\bonly\s+(\d+)\b", re.IGNORECASE),
    re.compile(r"\bhave\s+(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s+in\s+" + _SIZE + r"\b"),          # "12 in M"
    re.compile(r"\b" + _SIZE + r"\s*[(:\-–—]\s*(\d+)\b"),     # "XS (20)", "M: 12"
]


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)}


def unsupported_numbers(reply: str, deps: ChatDeps) -> list[str]:
    typed_by_shopper = _numbers(deps.shopper_message)
    problems = []
    for amount in PRICE_RE.findall(reply):
        value = float(amount.replace(",", ""))
        if value not in deps.seen_prices and value not in typed_by_shopper:
            problems.append(f"the price ${amount}")
    for pattern in QUANTITY_RES:
        for count in pattern.findall(reply):
            value = int(count)
            if value not in deps.seen_quantities and value not in typed_by_shopper:
                problems.append(f"the quantity {count}")
    return list(dict.fromkeys(problems))


def _history(turns: list[ChatTurn]) -> list[ModelMessage]:
    """The website keeps the conversation and sends recent turns with each message."""
    messages: list[ModelMessage] = []
    for t in turns:
        if t.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=t.content)]))
        elif messages:  # an assistant turn can't come first
            messages.append(ModelResponse(parts=[TextPart(content=t.content)]))
    return messages


async def chat(
    message: str,
    history: list[ChatTurn],
    shopper: PublicUser | None,
    page: ViewedPage | None,
    removed: list[str] | None = None,
) -> ChatResponse:
    """Run the agent loop for one shopper message, recording every step in the audit trail."""
    deps = ChatDeps(shopper=shopper, page=page, shopper_message=message, removed=removed or [])
    started, t0, run_id = _now(), time.perf_counter(), uuid.uuid4().hex[:8]
    steps: list[AuditStep] = []
    pending: dict[str, ToolCallPart] = {}  # tool calls waiting for their result
    stop: StopReason = "error"
    response: ChatResponse | None = None
    run = None
    try:
        agent = get_agent()
        # agent.iter runs the same loop as agent.run, but hands us each step as it happens.
        async with agent.iter(message, deps=deps, message_history=_history(history), usage_limits=LIMITS) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            pending[part.tool_call_id] = part
                elif Agent.is_model_request_node(node):
                    _record_results(node.request.parts, pending, steps)
            out = run.result.output
        stop = "answered"

        # Cards only for products a tool actually returned this turn, filled in from the
        # database: the model chooses which items to show, never what they cost.
        ids = [pid for pid in dict.fromkeys(out.product_ids) if pid in deps.seen_product_ids][:MAX_CARDS]
        response = ChatResponse(reply=out.reply.strip(), products=product_matches(ids, out.size), page=_page(out, deps))
        return response
    except MissingApiKey:
        stop = "no_api_key"
        raise
    except UsageLimitExceeded:
        stop = "step_limit"
        raise
    except UnexpectedModelBehavior:
        stop = "gave_up_after_retries"
        raise
    except ModelHTTPError:
        stop = "model_error"
        raise
    finally:
        _audit(run_id, started, t0, deps, steps, pending, stop, run, response)


# ---------------------------------------------------------------------------
# Audit trail: output/audit_trail.json, one record per shopper message, append-only
# ---------------------------------------------------------------------------
AUDIT_PATH = Path(os.environ.get("AUDIT_TRAIL_PATH", BACKEND_DIR.parent / "output" / "audit_trail.json"))
_audit_lock = threading.Lock()


def _now(ts: datetime | None = None) -> str:
    return (ts or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _short(text: str, limit: int = 220) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _is_output_tool(name: str | None) -> bool:
    return bool(name) and name.startswith("final_result")


def _summary(content) -> str:
    """A short, readable version of what a tool returned."""
    if isinstance(content, ProductSearchResult):
        text = f"search {content.search_id}: {content.total_matches} matches; first: " + ", ".join(p.name for p in content.products[:3])
        if content.sold_out_in_requested_size:
            text += f"; {len(content.sold_out_in_requested_size)} more sold out in that size"
    elif isinstance(content, StockCheck):
        text = f"{content.name}, ${content.price:.0f}. {content.summary}"
    elif isinstance(content, SimilarProducts):
        size = f" in {content.size}" if content.size else ""
        text = f"search {content.search_id}: {len(content.alternatives)} like {content.based_on}{size}: " + ", ".join(p.name for p in content.alternatives)
    elif isinstance(content, ProductDetail):
        text = f"{content.name}, ${content.price:.0f}; stock " + " ".join(f"{x.size}:{x.quantity}" for x in content.inventory)
    else:
        text = str(content)
    return _short(text)


def _record_results(parts, pending: dict[str, ToolCallPart], steps: list[AuditStep]) -> None:
    """Pair each tool result (or retry request) in a model request with the call that caused it."""
    for part in parts:
        if isinstance(part, ToolReturnPart) and not _is_output_tool(part.tool_name):
            call = pending.pop(part.tool_call_id, None)
            steps.append(AuditStep(
                time=_now(part.timestamp), step=len(steps) + 1, kind="tool_call", tool=part.tool_name,
                args=_short(call.args_as_json_str(), 160) if call else None, result=_summary(part.content),
            ))
        elif isinstance(part, RetryPromptPart):
            call = pending.pop(part.tool_call_id, None) if part.tool_call_id else None
            output_check = _is_output_tool(part.tool_name) or not part.tool_name
            steps.append(AuditStep(
                time=_now(part.timestamp), step=len(steps) + 1, kind="sent_back",
                tool="reply check" if output_check else part.tool_name,
                args=None if output_check or not call else _short(call.args_as_json_str(), 160),
                result=_short(part.content if isinstance(part.content, str) else json.dumps(part.content, default=str)),
            ))


def _audit(run_id, started, t0, deps: ChatDeps, steps, pending, stop: StopReason, run, response) -> None:
    """Never lets a problem writing the audit trail break the chat itself."""
    try:
        for call in pending.values():  # tools the model asked for but the loop stopped before running
            if not _is_output_tool(call.tool_name):
                steps.append(AuditStep(time=_now(), step=len(steps) + 1, kind="tool_call", tool=call.tool_name,
                                       args=_short(call.args_as_json_str(), 160), result="(not run: the loop stopped first)"))
        usage = run.usage if run is not None else None
        if callable(usage):  # a method in some PydanticAI versions, a property in others
            usage = usage()
        tokens = getattr(usage, "total_tokens", None)
        if tokens is None and usage is not None:
            tokens = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)
        page = deps.page
        page_label = None
        if page:
            page_label = page.kind + (f":{page.product_id}" if page.product_id else f":{page.category}" if page.category else "")
            page_label += f" (my size {page.my_size})" if page.my_size else ""
        record = AuditRecord(
            time=started,
            run_id=run_id,
            shopper=f"customer #{deps.shopper.id}" if deps.shopper else "guest",
            page=page_label,
            message=_short(deps.shopper_message, 200),
            shield_removed=deps.removed,
            model=CHAT_MODEL,
            steps=steps,
            stop_reason=stop,
            model_requests=getattr(usage, "requests", 0) or 0,
            tool_calls=sum(1 for st in steps if st.kind == "tool_call" and not st.result.startswith("(not run")),
            tokens=tokens,
            duration_ms=round((time.perf_counter() - t0) * 1000),
            reply=_short(response.reply, 300) if response else None,
            chat_cards=len(response.products) if response else 0,
            page_results=response.page.total if response and response.page else 0,
        )
        append_audit(record)
    except Exception:
        log.exception("Could not write the audit trail")


def append_audit(record: AuditRecord, path: Path | None = None) -> None:
    """Add one record to the end of the JSON array in the audit file, without rewriting earlier records.

    Only the closing "]" is replaced, so past entries are never wiped or changed. If the file
    can't be read as an array, nothing in it is touched: the record goes to a side file instead.
    """
    path = path or AUDIT_PATH
    entry = "  " + json.dumps(record.model_dump(), ensure_ascii=False, indent=2).replace("\n", "\n  ")
    with _audit_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            path.write_text("[\n" + entry + "\n]\n", encoding="utf-8")
            return
        with path.open("r+b") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell() - 1
            while pos >= 0:  # walk back over trailing whitespace to the closing bracket
                f.seek(pos)
                last = f.read(1)
                if not last.isspace():
                    break
                pos -= 1
            if pos < 0 or last != b"]":
                log.error("%s doesn't end with ']'; leaving it alone", path)
                with path.with_suffix(".unappended.jsonl").open("a", encoding="utf-8") as side:
                    side.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
                return
            before = pos - 1
            while before >= 0:  # is the array empty ("[ ]")?
                f.seek(before)
                prev = f.read(1)
                if not prev.isspace():
                    break
                before -= 1
            f.seek(pos)
            f.truncate()  # removes only the closing "]" and what follows it
            f.write((("\n" if prev == b"[" else ",\n") + entry + "\n]\n").encode("utf-8"))


def _page(out: AgentReply, deps: ChatDeps) -> PageResults | None:
    """Turn the agent's show_on_page request into every matching product, from the database.

    The agent only names its searches; the full, ordered match lists were recorded by
    search_products, so the page can show all 27 hoodies even though the model saw 8.
    """
    ids = _page_ids(out, deps)
    if not ids:
        return None  # nothing matched (or no request), so leave the page as it is
    products = product_matches(ids, out.size)
    return PageResults(title=out.show_on_page.title.strip(), total=len(products), products=products)


def _page_ids(out: AgentReply, deps: ChatDeps) -> list[str]:
    if out.show_on_page is None:
        return []
    ids: list[str] = []
    for search_id in out.show_on_page.search_ids:
        ids.extend(deps.searches.get(search_id, []))  # unknown search ids are ignored
    return list(dict.fromkeys(ids))[:MAX_PAGE_RESULTS]
