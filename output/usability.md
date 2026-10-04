# Usability improvements (Problem 9)

The core shop already worked: browsing, accounts, a chatbot that answers from the
database, chat search that updates the page, and customer memory. These four
improvements make it easier to use and better at its job. All four are built into
the running app.

| # | Improvement | Kind | Where to see it in the running app |
|---|---|---|---|
| 1 | **"My size", remembered across the shop** | Front end | The **My size** buttons on the Products page; a "Your size" badge on every product card; the single-item page; the chat |
| 2 | **Search and sort on the Products page** | Front end | The search box and **Sort** menu at the top of Products |
| 3 | **`find_similar_products`: in-stock alternatives** | Agent tool | Chat: ask about a size that's sold out, ask "anything like this?", or press **Find something similar** on a product page |
| 4 | **Sensitive-info shield** | Agent / backend safety | Chat: type a card number, a CVV or "my password is ..." |

---

## 1. "My size", remembered across the shop (front end)

### What I added
- **The size buttons.** A row of **My size** buttons (XS, S, M, L, XL, XXL) sits on
  the Products page (`components/SizePicker.tsx`). On a product's own page, the size
  boxes are buttons too: tapping one saves it as your size, and tapping it again
  clears it.
- **Remembered in the browser.** The size is saved in `localStorage` and shared
  through `MySizeProvider.tsx` / `useMySize.ts`, so it stays set across pages and
  later visits.
- **A badge on every product card,** on Products, on Home's favorites, and on the
  cards the chat puts on the page: **"Your size L: 8 in stock"**, or **"Your size L:
  Sold out"** in red (`components/ProductCard.tsx`). The numbers come from the
  database: `GET /api/products` now includes each product's stock by size.
- **"Only show items in stock in my size".** A checkbox on the Products page hides
  everything you couldn't buy in your size. It works together with the style chips
  and search ("hockey", in stock in L, gives 2 items).
- **On the single-item page** (`pages/ProductPage.tsx`):
  - Your size box gets a blue ring and a "Your size" tag.
  - Just under the price, a callout says **"Your size L: only 2 left."** or, in red,
    **"Your size L: sold out right now."**
  - When your size is sold out, a **Find something similar in L** button opens the
    chat with that question typed in (this is where improvement 3 comes in).
- **The chat knows it.** Your size is sent with each chat message as part of the
  page context. A dynamic instruction tells the agent "They set their size to L...".
  So "Is this available in my size?" on a product page checks L, without you having
  to say it.

### Why it helps
- **For shoppers:** Almost everyone shopping for clothes has one size in mind, and
  145 of the 612 size slots in our inventory are sold out. Before this, a shopper had
  to open each product to find out whether their size was available. Now one tap
  answers it for the whole shop at a glance, and they never fall in love with a
  hoodie only to find their size is gone.
- **For the business:** It lowers frustration and wasted clicks, which means fewer
  abandoned visits. And when a size is sold out, the shopper is pointed straight to
  an alternative instead of leaving.

### How to see it
1. Go to **Products** and tap **L** under "My size". Every card now shows "Your size
   L: ..." in navy or red.
2. Tick **Only show items in stock in my size**. The count drops and only buyable
   items remain.
3. Open **Ice Hockey Left Chest Hoodie**. The red callout says "Your size L: sold out
   right now", and the L box is tagged "Your size".
4. Open the chat on that page and ask **"Is this available in my size?"** The
   assistant checks L.

---

## 2. Search and sort on the Products page (front end)

### What I added
In `pages/Products.tsx`:
- **A search box** that filters as you type. Every word must appear somewhere in a
  product's name, description, colors, tags or shelf, so "navy hockey" finds navy
  hockey items, not everything navy. Press **/** anywhere on the page to jump to it,
  and **×** clears it.
- **A Sort menu:** Featured, Price low to high, Price high to low, Name A to Z.
- **A live count** that says what you're looking at: "2 of 102 items matching
  "hockey" in stock in size L".
- **A "no matches" message with a way forward.** If nothing matches (for example
  "pink beanie"), the page says so and offers an **Ask the shop assistant** button.
  The button opens the chat with the question already typed: Do you have anything
  like "pink beanie"?
- **Searches you can share.** The search, sort, shelf and size filter are all kept in
  the address bar (`?q=hockey&sort=price-asc&fit=1`). A search can be bookmarked or
  sent to a friend, and the browser's Back button works as expected.

### Why it helps
- **For shoppers:** With 102 products, scrolling isn't a way to find "the Saybrook
  one" or "something under $40". Many shoppers come in knowing exactly what they
  want: their residential college, their sport, "Yale Dad". Search gets them there
  in one step. Sorting by price helps students on a budget and parents comparing
  gifts.
- **For the business:** Faster finding means more items seen and more sales. And when
  someone searches for something we don't stock, they aren't stuck on an empty page:
  the "no matches" message hands them to the assistant, which suggests what we do
  have.

### How to see it
1. On **Products**, type **hockey**. 5 of 102 items show.
2. Choose **Sort → Price: low to high**. The prices run $32, $32, $58, $68, $68.
3. Type **pink beanie**. The "no matches" message appears. Press **Ask the shop
   assistant** and the chat opens with the question ready to send.

---

## 3. `find_similar_products`: in-stock alternatives instead of a dead end (agent tool)

### What I added
- **A new agent tool,** `find_similar_products(product_id, size)` in
  `backend/tools.py`. It ranks every other product by how alike it is:
  - the same shelf
  - shared **themes**: a sport, a college, "vintage bulldog", and Mom/Dad/Grandma
    counting as one "family" theme
  - shared colors
  - the same price

  Two rules keep the suggestions useful:
  - **Only real themes count.** A word counts as a theme only if few products have it.
    Words about construction ("drawstring", "kangaroo pocket") don't count.
  - **Every suggestion is buyable.** Given a size, it only suggests products **in stock
    in that size**.

  It returns a `SimilarProducts` result (`backend/models.py`): the alternatives,
  a `why` line for each (for example "also hoodies; same theme: hockey; same colors:
  navy"), and a `search_id`, so the alternatives can also be put on the page as cards.
- **Prompt rules** (`prompts/prompt.md`):
  - "Anything like this?" or "other options?" means call `find_similar_products`.
  - When the size asked for is sold out, the agent must say so clearly first. Then it
    calls `find_similar_products` with that size and offers the top 2 or 3, each with
    its reason, as cards.
- **It keeps the honesty guarantees.** The tool's prices and stock counts are recorded
  like every other tool's, so the "no invented numbers" check still applies. Each
  alternative's card shows its stock in the shopper's size, straight from the
  database.

### Why it helps
- **For shoppers:** "Sold out in your size" used to be the end of the conversation.
  Now it comes with three close matches they can actually buy, each with a reason.
  For example, the other hockey hoodie for a hockey fan, or the Yale Mom Crewneck
  when the Dad one is out in XL.
- **For the business:** It turns lost sales into sales. About 1 in 4 size slots is
  sold out, so this comes up a lot. Suggestions are limited to in-stock items, so
  the bot never recommends something that's also unavailable.

### How to see it
- **In the chat,** ask **"Is the Ice Hockey Left Chest Hoodie available in large?"**
  - **Expected:** "Size L is sold out right now...", then Yale Sports Hoodie Hockey
    (12 in L), Basic Hoodie Big Yale (8 in L) and Squash Left Chest Hoodie (25 in L).
  - **Cards:** each one shows "Size L: N in stock".
- **On the District Vit Hoodie Vintage Bulldog page,** ask **"Anything similar to
  this?"**. You get the other vintage-bulldog pieces.
- **With My size set to L,** open the Ice Hockey hoodie and press **Find something
  similar in L**.

---

## 4. Sensitive-info shield (agent / backend safety)

### What I added
- **`redact_sensitive()`** in `backend/tools.py`. It runs on every chat message in
  `POST /api/chat` (and on any history a guest's browser sends) **before** the
  message reaches the AI model, the saved chat history or the server logs. It
  removes:
  - **payment card numbers:** 13–19 digits, kept only if they pass the Luhn checksum
    real cards pass, so order numbers, phone numbers and product names like "2025
    Yale Vs Harvard" are left alone.
  - **card security codes:** "cvv 123", "security code: 4567".
  - **passwords:** "my password is ...", "pwd: ...".
  - **Social Security numbers:** 123-45-6789.
- **A dynamic instruction** (`what_the_shield_removed` in `agent.py`). It tells the
  agent what was removed, so the reply gently reminds the shopper they never need
  to share that in chat, and then still answers the rest of their question.
- **The response says what happened.** It includes `removed` and `message_shown`.
  The chat swaps the shopper's bubble for the cleaned version and shows a notice:
  **"Removed for your safety: a card number and a card security code. It wasn't
  saved or sent to our assistant."**
- **Only the cleaned text is saved.** For logged-in shoppers, `chat_messages` only
  ever receives the cleaned text.

### Why it helps
- **For shoppers:** People do paste card numbers and passwords into shop chats,
  especially when they think the bot can take payment (this site has no checkout).
  The shield makes sure that never leaves our server, isn't stored in their chat
  history, and is visibly taken out, so they know it's handled.
- **For the business:** Storing card numbers (even by accident, in a chat log) puts
  a shop in scope for card-security rules (PCI DSS). Sending them to a third-party AI
  service is a privacy risk. Removing them before they reach the model or the
  database means Campus Customs never holds that data. It also stops the chatbot
  from ever repeating a secret back.

### How to see it
1. Open the chat (as a guest or logged in) and send:
   **"Can I pay with my card 4242 4242 4242 4242, cvv 123? Is this hoodie in XXL?"**
   (4242... is a published test card number, not a real card.)
2. Your message turns into "Can I pay with my card [card number removed], cvv
   [removed]? ...", with the yellow "Removed for your safety" note. The assistant
   says you never need to share card details, then answers the XXL question.
3. Logged in, send **"my password is Bulldog123, what email does my account use?"**.
   The password is removed, and the assistant still tells you your email.
