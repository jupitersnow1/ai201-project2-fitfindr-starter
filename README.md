# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```
# FitFindr 🛍️

FitFindr is an AI styling agent for secondhand shopping. You describe what you're
looking for in plain language ("vintage graphic tee under $30"); it searches a mock
listings dataset, suggests outfits that pair the find with your existing wardrobe,
and writes a shareable "fit card" caption — all in one interaction.

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file in the project root (free key at
[console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Running it

**Web UI (Gradio):**
```bash
python app.py
```
Then open the localhost URL shown in your terminal (usually http://localhost:7860).

**CLI smoke test (happy path + no-results path):**
```bash
python agent.py
```

**Tests** (parsing + scoring logic — runs offline, no API key needed):
```bash
python -m pytest -q
```

---

## Tool Inventory

The agent uses **three required tools**, defined as standalone functions in
[`tools.py`](tools.py). `search_listings` is pure Python; the two generative tools
call the **Groq LLM** (`llama-3.3-70b-versatile`) through a shared `_chat()` helper.

### 1. `search_listings(description, size, max_price) → list[dict]`
**Purpose:** Find listings in `data/listings.json` that match the user's request.

- **Inputs:**
  - `description` (str) — keywords describing the item (e.g. `"vintage graphic tee"`)
  - `size` (str | None) — size to filter by (e.g. `"M"`, `"8"`); `None` skips size filtering
  - `max_price` (float | None) — inclusive price ceiling; `None` skips price filtering
- **Returns:** A list of up to 3 listing dicts, **sorted by relevance** (best first).
  Each dict has `id`, `title`, `description`, `category`, `style_tags`, `size`,
  `condition`, `price`, `colors`, `brand`, `platform`. Returns `[]` if nothing matches.
- **How it ranks:** keyword overlap with the description, with stopwords removed and
  **title matches weighted 3× higher** than other fields, so a query for "graphic tee"
  surfaces an actual tee rather than an item that merely mentions one.

### 2. `suggest_outfit(new_item, wardrobe) → str`
**Purpose:** Suggest 1–2 complete outfits built around the found item.

- **Inputs:**
  - `new_item` (dict) — the selected listing dict from `search_listings`
  - `wardrobe` (dict) — the user's wardrobe with an `items` list (may be empty)
- **Returns:** A non-empty string with outfit ideas. When the wardrobe has items, the
  LLM names specific pieces from it; when it's empty, the LLM gives general styling advice.

### 3. `create_fit_card(outfit, new_item) → str`
**Purpose:** Write a short, shareable OOTD-style caption.

- **Inputs:**
  - `outfit` (str) — the suggestion string from `suggest_outfit`
  - `new_item` (dict) — the selected listing dict (for item name, price, platform)
- **Returns:** A 2–4 sentence caption mentioning the item, price, and platform. Uses a
  higher LLM temperature so different finds produce noticeably different captions.

---

## Planning Loop (conditional logic)

The loop lives in `run_agent()` ([`agent.py`](agent.py)) and is **decision-driven, not
a fixed sequence** — each step's result determines whether the next runs:

1. **Guard the input.** If the query is empty/whitespace → set `error`, stop.
2. **Parse the query** into `description`, `size`, `max_price`.
3. **Search.** Call `search_listings` with the parsed constraints.
   - **If results are found** → continue to step 4.
   - **If zero results** → **retry with loosened constraints** (see Stretch Feature
     below): drop the size filter, then the price ceiling. If a loosened search
     succeeds, record what was relaxed and continue.
   - **If still zero results** → set an actionable `error` and stop **without** calling
     `suggest_outfit` or `create_fit_card`.
4. **Select** the top-ranked listing as `selected_item`.
5. **Suggest an outfit** from `selected_item` + the wardrobe.
6. **Create a fit card** from the outfit + `selected_item`.
7. **Return** the session.

The key adaptive branch: a no-results query **does not** call all three tools — it stops
after the search and reports why, so the agent behaves differently from the happy path.

## State Management

All state for one interaction lives in a single **session dict** created by
`_new_session()`. Each step writes its output into the session; the next step reads
what it needs from it — the user never re-enters anything.

| Field | Written by | Read by |
|---|---|---|
| `query` | `_new_session` | `_parse_query` |
| `parsed` (`description`, `size`, `max_price`) | step 2 | `search_listings` |
| `search_results` | `search_listings` | item selection |
| `selected_item` | step 4 | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | `_new_session` (from `app.py`) | `suggest_outfit` |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` |
| `fit_card` | `create_fit_card` | UI |
| `adjustments` | retry step | UI (note shown to user) |
| `error` | any failing step | UI / early return |

The hand-offs that matter for continuity: the item from `search_listings` flows into
`suggest_outfit` as `selected_item`, and that outfit string flows into `create_fit_card`
as `outfit` — both via the session, with no re-entry.

---

## Error Handling

| Tool | Failure mode | Agent response |
|---|---|---|
| `search_listings` | No listing matches the query | Retry with loosened filters; if still empty, set a specific `error` ("No thrift finds matched … Try describing the item differently") and stop before the generative tools run. |
| `suggest_outfit` | Empty wardrobe **or** Groq API error | Empty wardrobe → general styling advice (no crash). API error → caught, returns a short fallback message so the loop continues. |
| `create_fit_card` | Empty/blank outfit **or** Groq API error | Blank outfit → a guard message telling the user to generate an outfit first. API error → caught, returns a fallback caption. None of these raise. |

**Concrete example from testing.** Querying `"designer ballgown size XXS under $5"`
(deliberately impossible) triggers the failure path: the agent retries after dropping the
size and price filters, still finds nothing, and returns:

> No thrift finds matched "designer ballgown size XXS under $5" — even after dropping the
> size and price filters. Try describing the item differently or with fewer keywords.

The UI shows that message in the listing panel and leaves the outfit/fit-card panels
empty — `suggest_outfit` and `create_fit_card` are never called.

---

## Stretch Feature: Retry Logic with Fallback (+1)

On a **zero-result search**, the agent doesn't give up — it automatically retries with
progressively loosened constraints: first it drops the **size** filter, then the
**price** ceiling. If a loosened search succeeds, it records what it relaxed in
`session["adjustments"]`, and the UI tells the user, e.g.:

> Note: no exact match, so I dropped the size filter (XXS).

**Example:** `"graphic tee size XXS"` has no XXS tee in the dataset, so the agent drops
the size filter, finds the Graphic Tee in size L, and surfaces it with the note above.

---

## Spec Reflection

- **Where the spec helped:** Writing the per-tool interfaces in `planning.md` (inputs,
  return shape, failure mode) *before* coding made the implementations fall out cleanly —
  each tool had one job and a defined contract, and the planning loop was just wiring those
  contracts together through the session dict.
- **Where I diverged, and why:** The plan originally specified **rule-based** outfit and
  caption generation. I switched `suggest_outfit` and `create_fit_card` to **LLM calls**
  (Groq) because the rule-based templates produced stiff, repetitive text, whereas the
  assignment asks for natural, varied styling advice and captions. I kept a rule-based
  *fallback* inside each tool so an API outage degrades gracefully instead of crashing.

---

## AI Usage Transparency

I used **Claude (Claude Code)** throughout. Specific instances:

1. **Fixing search relevance.** A query for "graphic tee" was returning trousers. Claude
   traced it to two bugs — my query parser grabbing the `30` from `$30` as a *size*, and
   flat keyword scoring letting stopwords dominate. **I reviewed and approved** the fixes
   (parse price before size; weight title matches; drop stopwords), and we locked them in
   with pytest tests so they can't regress.

2. **Wiring in the LLM and the fallback.** I directed Claude to implement `suggest_outfit`
   and `create_fit_card` with Groq. When it added a hardcoded fallback that *fabricated*
   specific styling advice on API failure, **I pushed back** — hardcoding plausible-looking
   output felt dishonest — and we changed it toward an honest "couldn't generate right now"
   message instead of faking a real suggestion.

3. **Adding a test safety net.** I asked Claude to add pytest coverage for the parsing and
   scoring logic. **I reviewed** the proposed tests to confirm they actually pin the two
   bugs we'd fixed (the `$30`→size mis-parse and stopword-dominated ranking), so a later
   change can't silently reintroduce them. **I decided** to keep the LLM tools out of the
   unit tests, since asserting on generated text is brittle — they're verified by running
   the app instead.

---

## Project Layout

```
ai201-project2-fitfindr-starter/
├── app.py                 # Gradio UI + handle_query()
├── agent.py               # run_agent() planning loop + query parsing + session state
├── tools.py               # the three tools (+ Groq client + scoring helpers)
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # wardrobe format + example wardrobe
├── utils/data_loader.py   # data loading helpers
├── tests/                 # pytest: parsing + scoring
├── planning.md            # design doc (tools, loop, state, architecture, AI plan)
└── requirements.txt
```
