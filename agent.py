"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "adjustments": [],           # filters relaxed during a fallback retry
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    normalized = query.lower().strip()
    parsed = {
        "description": normalized,
        "size": None,
        "max_price": None,
    }

    def _cut(text: str, match: re.Match) -> str:
        # Remove a matched span by slicing — NOT re.sub on the matched text,
        # which would re-interpret metachars like "$" in "$30" as a pattern.
        return text[:match.start()] + " " + text[match.end():]

    # Parse price first so its number (e.g. the 30 in "$30") is consumed here and
    # can't be mistaken for a size by the bare-number fallback below.
    price_match = re.search(r"(?:under|below|less than|max|<=|£|€|\$)\s*([0-9]+(?:\.[0-9]{1,2})?)", normalized)
    if price_match:
        try:
            parsed["max_price"] = float(price_match.group(1))
        except ValueError:
            parsed["max_price"] = None
        normalized = _cut(normalized, price_match)

    size_match = re.search(r"\bsize\s*([xs]{1,3}|xxl|xl|l|m|s|[0-9]{1,2})\b", normalized)
    if not size_match:
        size_match = re.search(r"\b(xs|s|m|l|xl|xxl|[0-9]{1,2})\b", normalized)
    if size_match:
        parsed["size"] = size_match.group(1).upper()
        normalized = _cut(normalized, size_match)

    parsed["description"] = re.sub(r"\s+", " ", normalized).strip()
    return parsed


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # TODO: implement the planning loop
    session = _new_session(query, wardrobe)

    if not query or not query.strip():
        session["error"] = "Please enter something you'd like to search for."
        return session

    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    # First pass: search with the user's exact constraints.
    size = parsed["size"]
    max_price = parsed["max_price"]
    results = search_listings(parsed["description"], size, max_price)

    # Fallback retry: on a zero-result search, progressively loosen the
    # constraints — drop the size filter first, then the price ceiling — rather
    # than giving up immediately. We record what we relaxed so we can tell the user.
    if not results and size is not None:
        size = None
        results = search_listings(parsed["description"], size, max_price)
    if not results and max_price is not None:
        max_price = None
        results = search_listings(parsed["description"], size, max_price)

    session["search_results"] = results
    if results:
        if size != parsed["size"]:
            session["adjustments"].append(f"the size filter ({parsed['size']})")
        if max_price != parsed["max_price"]:
            session["adjustments"].append(f"the under-${parsed['max_price']:.0f} price limit")

    if not session["search_results"]:
        # Specific, actionable failure: say what failed and what to try next.
        if parsed["size"] or parsed["max_price"]:
            reason = " — even after dropping the size and price filters"
            hint = "Try describing the item differently or with fewer keywords."
        else:
            reason = ""
            hint = "Try different or fewer keywords."
        session["error"] = (
            f"No thrift finds matched \"{query.strip()}\"{reason}. {hint}"
        )
        return session

    session["selected_item"] = session["search_results"][0]
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
