# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
search_listings will inspect all of the listings in data/listing.json file with similar descriptions to that of the query sent by the user. It shall return three items sorted by relavance. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A brief description of the item the user is anticipating to look for in the listings catalog
- `size` (str): The size of the item they are looking for (could be m, l, xl, or even 5, 7, 19, etc)
- `max_price` (float): The highest price amount the user is willing to pay for the item they are looking for. 

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of up to three listing dictionaries sorted by relevance to the query. Each listing contains fields such as `id`, `title`, `description`, `category`, `price`, `size`, `colors`, and other metadata from `data/listings.json`.

**What happens if it fails or returns nothing:**
If no listings match, the agent should stop the planning loop early, set a helpful session error message like "No matching thrift finds were found for your query," and not call `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Given a selected thrift listing and the user's wardrobe, this tool produces a natural-language outfit suggestion for the new item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The selected thrift listing dict from `search_listings`.
- `wardrobe` (dict): The user's wardrobe dict, containing an `items` list that may be empty.

**What it returns:**
A non-empty string describing 1–2 full outfit ideas that use the new item, ideally referencing pieces from the wardrobe when available.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, return general styling advice for the new item rather than raising an exception. If the tool cannot create a specific outfit from the wardrobe, return a fallback suggestion string such as "I couldn't build a complete outfit from your current wardrobe, but this piece would pair well with...".

---

### Tool 3: create_fit_card

**What it does:**
Generate a short social-caption-style blurb describing the outfit suggestion and the thrifted item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The selected thrift listing dict used for context.

**What it returns:**
A 2–4 sentence caption suitable for an Instagram/TikTok-style fit card, mentioning the item name, price, platform, and overall vibe.

**What happens if it fails or returns nothing:**
If `outfit` is missing, empty, or incomplete, return a safe fallback message string describing the item and its styling potential instead of raising an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The planning loop is decision driven rather than blindly sequential. It first parses the query to understand intent and parameters. Then it uses the results of each tool call to decide whether the next tool is necessary: 

```
if the query includes an item search intent -> call `search_listings` first

if `search_listings` returns results -> call `suggest_outfit` with the selected top item and wardrobe.

if `search_listings` returns no results -> stop early and set an error message. 

if `search_outfit` returns a valid outfit string -> call `create_fit_card` 

if `search_outfit` returns no usable outfit text -> return a fallback response instead of forcing `create_fit_card` 

if the query is purely about styling a known items from the wardrobe and not searching for a listing, the loop can skip `seach_listings` and move directly to `suggest_outfit` 

This means the agen reacts to what it receives~ seach output, wardrobe contents, and the quality of the outfit suggestion
```
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->

**Step 3:**
<!-- Continue until the full interaction is complete -->

**Final output to user:**
<!-- What does the user actually see at the end? -->
