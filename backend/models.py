"""Structured types for the Campus Customs backend: products, accounts and chat.

The API (main.py), the agent (agent.py) and its tools (tools.py) all share these,
so a price or stock count has the same shape everywhere it travels.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Products (read from the catalogue and inventory tables)
# ---------------------------------------------------------------------------
Category = Literal["Hoodies", "Crewnecks", "Quarter-zips", "Tees & tops", "Jackets"]
Size = Literal["XS", "S", "M", "L", "XL", "XXL"]


class SizeStock(BaseModel):
    size: str
    quantity: int


class ProductSummary(BaseModel):
    """One product as shown on a card on the Products page."""
    product_id: str
    name: str
    garment_type: str
    category: Category
    description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int


class ProductDetail(ProductSummary):
    """Everything the shop knows about one product, including stock by size."""
    search_tags: list[str]
    inventory: list[SizeStock]


class ProductSearchResult(BaseModel):
    """What the agent's search tool returns."""
    search_id: int = Field(
        description="This search's number within the current message. Put it in show_on_page.search_ids "
        "to show ALL of its matches as cards on the website."
    )
    total_matches: int = Field(description="How many products matched, even if fewer are listed.")
    products: list[ProductDetail]
    sold_out_in_requested_size: list[ProductDetail] = Field(
        default_factory=list,
        description="Products that match everything except that they are sold out in the size asked for. "
        "They exist; they just can't be bought in that size right now.",
    )


class SizeStatus(BaseModel):
    size: str
    quantity: int
    status: str = Field(description='"sold out", "only N left" or "in stock".')


class StockCheck(BaseModel):
    """What check_stock returns: the stock picture for one product, read straight from inventory."""
    product_id: str
    name: str
    price: float
    asked_size: str | None = Field(description="The size the shopper asked about, if any.")
    asked_size_quantity: int | None = Field(description="Units on hand in the asked size. 0 means sold out.")
    sizes: list[SizeStatus]
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]
    summary: str = Field(description="A plain-English summary you can repeat to the shopper.")


class SimilarProducts(BaseModel):
    """What find_similar_products returns: in-stock alternatives to one product."""
    search_id: int = Field(description="Put it in show_on_page.search_ids to show these alternatives on the website.")
    based_on: str = Field(description="The name of the product the alternatives are like.")
    size: str | None = Field(description="If given, every alternative is in stock in this size.")
    alternatives: list[ProductDetail] = Field(description="Closest matches first: same shelf, shared colors and themes.")
    why: list[str] = Field(description="For each alternative, what it has in common with the original.")


class ProductMatch(BaseModel):
    """One product card, in the chat or on the page. Built from the database, never from the model's text."""
    product_id: str                   # the card links to /products/{product_id}
    name: str
    price: float
    image_url: str
    description: str                  # the short info under the name
    category: Category
    in_stock: bool                    # in stock in at least one size
    size: str | None = None           # set when the shopper asked about one size
    size_quantity: int | None = None  # units in that size; 0 shows as "Sold out"
    inventory: list[SizeStock] = []   # stock in every size, for the shopper's "My size" badge


class PageResults(BaseModel):
    """Search results the website shows as product cards on the Products page."""
    title: str                        # e.g. "Navy hoodies under $70"
    total: int                        # how many products are in `products`
    products: list[ProductMatch]      # every match, best first


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PublicUser(BaseModel):
    """What the browser (and the chatbot) may know about a user. Never includes password_hash."""
    id: int
    first_name: str
    last_name: str
    name: str
    email: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """Where the shopper is on the website when they send a message, as the chat widget reports it.

    It comes from the browser, so the backend checks it (see ViewedPage) before the agent sees any of it.
    """
    path: str = Field(default="/", max_length=200)          # e.g. "/products/yale-mom-hoodie"
    product_id: str | None = Field(default=None, max_length=120)  # set on a single-item page
    category: Category | None = None                        # set when a style chip is chosen on Products
    my_size: Size | None = None                             # the size the shopper picked with "My size"


class ChatRequest(BaseModel):
    """What the chat widget sends: the new message, the recent conversation and the page they're on.

    For logged-in shoppers the backend ignores `history` and loads the saved conversation instead.
    """
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None


PageKind = Literal["home", "products", "product", "about", "login", "create-account", "other"]


class ViewedPage(BaseModel):
    """The checked version of PageContext that goes into the agent's context."""
    kind: PageKind
    product_id: str | None = None    # only if it's a real product
    product_name: str | None = None  # read from the database, not from the browser
    category: Category | None = None
    my_size: Size | None = None      # the shopper's saved size, if they picked one


class SavedMessage(BaseModel):
    """One message from a logged-in shopper's saved chat (a chat_messages row)."""
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductMatch]     # the chat cards, rebuilt from the database with today's prices
    created_at: str


class ChatHistory(BaseModel):
    """What GET /api/chat/history returns."""
    saved: bool                      # true when logged in (chats are saved); false for guests
    messages: list[SavedMessage]


class ShowOnPage(BaseModel):
    """The agent's request to put search results on the website."""
    title: str = Field(
        max_length=60,
        description='A short heading for the results, e.g. "Hoodies", "Navy crewnecks under $60", '
        '"Gifts for Yale moms". No counts; the website adds the real count.',
    )
    search_ids: list[int] = Field(
        min_length=1,
        description="search_id of each search_products call (from this message) whose matches belong on the page.",
    )


class AgentReply(BaseModel):
    """The agent's structured answer for one chat turn."""
    reply: str = Field(max_length=1500, description="Your message to the shopper, in plain text (short).")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_id of each product your reply recommends or talks about, best first, at most 6. "
            "Only use product_id values your tools returned during this message. Empty if none."
        ),
    )
    size: Size | None = Field(
        default=None,
        description="If the shopper asked about one specific size, that size, so each card shows its stock. Otherwise null.",
    )
    show_on_page: ShowOnPage | None = Field(
        default=None,
        description="When the shopper is browsing a kind of item or a theme, the searches whose matches the "
        "website should show as product cards. Null for questions about one product, policies or small talk.",
    )


class ChatResponse(BaseModel):
    """What the website receives for one chat message (the API contract).

    reply     the assistant's message, shown in the chat panel
    products  a few picks, shown as small cards under the reply
    page      every matching product, shown as cards on the Products page (null = leave the page alone)
    """
    reply: str
    products: list[ProductMatch]
    page: PageResults | None = None
    removed: list[str] = []           # what the sensitive-info shield took out, e.g. ["a card number"]
    message_shown: str | None = None  # the shopper's message as it was sent on and saved (set when something was removed)


# ---------------------------------------------------------------------------
# Audit trail (output/audit_trail.json, append-only)
# ---------------------------------------------------------------------------
StopReason = Literal["answered", "step_limit", "gave_up_after_retries", "model_error", "no_api_key", "error"]


class AuditStep(BaseModel):
    """One step of the agent loop: a tool call and what it returned, or a reply sent back to be fixed."""
    time: str                          # when the result came back (UTC, ISO 8601)
    step: int                          # 1, 2, 3... in order
    kind: Literal["tool_call", "sent_back"]
    tool: str | None                   # e.g. "check_stock"; for sent_back, the tool or the reply check
    args: str | None = None            # the tool's arguments, shortened
    result: str                        # what came back, shortened (or why it was sent back)


class AuditRecord(BaseModel):
    """Everything one chat message made the agent do, from question to stop."""
    time: str                          # when the message arrived (UTC, ISO 8601)
    run_id: str                        # short id tying the steps of one message together
    shopper: str                       # "guest" or "customer #3": never a name, email or password
    page: str | None                   # what they were looking at, e.g. "product:yale-mom-hoodie"
    message: str                       # the shopper's message (after the sensitive-info shield), shortened
    shield_removed: list[str]          # what the shield took out, if anything
    model: str
    steps: list[AuditStep]
    stop_reason: StopReason            # why the loop ended
    model_requests: int                # how many times the model was called (limit: 6)
    tool_calls: int                    # how many tools ran (limit: 10)
    tokens: int | None                 # total tokens used, for cost
    duration_ms: int
    reply: str | None                  # the answer shown, shortened (None if the run stopped early)
    chat_cards: int                    # product cards shown in the chat
    page_results: int                  # product cards put on the Products page


@dataclass
class ChatDeps:
    """Per-message context handed to the agent, its tools and its dynamic instructions."""
    shopper: PublicUser | None = None   # who is chatting (None = a guest)
    page: ViewedPage | None = None      # where they are on the site
    shopper_message: str = ""
    removed: list[str] = field(default_factory=list)  # what the sensitive-info shield took out of the message
    # Facts the database tools returned during this message. Only these may appear in
    # the reply (as cards, prices or stock counts); see agent.py's output check.
    seen_product_ids: set[str] = field(default_factory=set)
    seen_prices: set[float] = field(default_factory=set)
    seen_quantities: set[int] = field(default_factory=set)
    # Every search_products call this message: search_id -> ALL matching product_ids, best first.
    searches: dict[int, list[str]] = field(default_factory=dict)
