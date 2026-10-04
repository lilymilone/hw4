# Campus Customs: Yale Bulldog Blue store + Professor Dan

A customer website for Campus Customs (officially licensed Yale apparel), with a chatbot,
**Professor Dan** (Handsome Dan the bulldog as a kind old professor). Shoppers can:
- browse products and open each one's own page
- create an account and log in
- chat about merch, and see matching items appear on the page
- get honest prices and stock by size, read straight from a local SQLite database

The front end is **React + Vite + TypeScript**. The back end is **FastAPI**, and its
"brain" is a **PydanticAI agent** that uses an OpenAI model.

## What's in this repo

```
hw4/
├── AI_prompts.md          the prompts I typed into my vibe coder, one section per problem
├── requirements.txt       Python packages for the back end
├── .env.example           template for your .env (placeholders only)
├── .gitignore             keeps .env, the database and product images out of git
├── README.md              this file
├── frontend/              Vite React TypeScript app (the website)
├── backend/
│   ├── main.py            FastAPI app (run with: uvicorn main:app --reload --port 8000)
│   ├── agent.py           ┐
│   ├── models.py          │ the agent: these four files
│   ├── tools.py           │
│   └── prompts/prompt.md  ┘
└── output/
    ├── harness.md         how the whole system works (start here)
    ├── design.md          the visual design and why
    ├── usability.md       the four usability improvements
    ├── app_check.html     live-site test with screenshots (double-click to open)
    ├── app_check_images/  screenshots linked from app_check.html
    └── audit_trail.json   append-only log of the agent's activity
```

**The agent is four files in `backend/`:**
- `prompts/prompt.md`: Professor Dan's instructions (voice, honesty and safety rules)
- `agent.py`: builds the agent, runs its loop, checks replies, writes the audit trail
- `tools.py`: the read-only database tools it can call
- `models.py`: every structured type

## How to run it

You need **Python 3.10+** and **Node.js 20.19+ or 22.12+**. It was tested with
Python 3.14 and Node 24.

### 1. Put the data back (it is not in git)
The database and product images come from the course data pack. Place them in a
`data/` folder at the top of the repo, next to `backend/` and `frontend/`:

```
hw4/
└── data/
    ├── campus_customs.db    tables: catalogue, inventory, users, chat_messages
    └── products/            the 102 product images named in the catalogue
```

### 2. Add your OpenAI API key
Copy the template, then open `.env` and replace the placeholder with your own key:

```bash
cp .env.example .env
```

The back end reads `OPENAI_API_KEY` from your environment, or from a `.env` file in
`backend/` or any folder above it (such as this one). `.env` is git-ignored.

### 3. Start the back end (terminal 1)
From the `hw4/` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Check it at http://localhost:8000/api/health. It should say `{"ok":true}`.

### 4. Start the front end (terminal 2)
From the `hw4/` folder:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server forwards `/api` and `/media` requests
to the back end on port 8000, so both servers need to be running.

### 5. Try it
- **Log in** with the seed test user `test@campuscustoms.yale.edu` (password from the
  assignment), or create a new account.
- **Open the chat** ("Ask Professor Dan", bottom right) and try:
  - "What hoodies do you have?" The matching cards appear on the page.
  - On a product page: "Do you have this in pink?" or "Is it in stock in L?"
  - "Is the Ice Hockey Left Chest Hoodie available in large?" It's sold out in L, so
    he suggests similar hoodies that are in stock in L.
- **On Products,** tap a size under **My size** to see your size's stock on every card.

## Good to know
- **The agent can't change the database.** Its tools open it read-only. The site only
  adds rows when someone creates an account (`users`) or a logged-in shopper chats
  (`chat_messages`).
- **The audit trail is never wiped.** Every chat message adds one record to
  `output/audit_trail.json`, and earlier records stay as they are.
- **Some files are created on first run and never committed:**
  - `.env`
  - `data/`
  - `.venv/`
  - `frontend/node_modules/`
  - `backend/.session_secret`: the cookie-signing key, made automatically the first time
    the server starts.
- **For details,** see `output/harness.md`. It covers the architecture, specs and loop
  limits, every data type, the tools, the safety rules and the audit trail.
