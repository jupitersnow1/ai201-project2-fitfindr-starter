"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

# Groq's strongest general-purpose chat model (confirmed available on the account).
_DEFAULT_MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────

_client = None


def _get_groq_client():
    """Initialize and return a cached Groq client using GROQ_API_KEY from .env."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Add it to a .env file in the project root."
            )
        _client = Groq(api_key=api_key)
    return _client


def _chat(prompt: str, *, temperature: float = 0.7, max_tokens: int = 400,
          system: str | None = None) -> str:
    """
    Send a single-turn prompt to the LLM and return its text response.

    Keeps the messages shape in one place so both tools call the model the
    same way. Raises if the API errors — callers decide how to fall back.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = _get_groq_client().chat.completions.create(
        model=_DEFAULT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

# Common query filler that carries no item meaning — dropped before scoring so a
# match on "tee" counts and a match on "looking"/"for" does not.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "my",
    "me", "i", "im", "looking", "look", "need", "want", "wanted", "find", "some",
    "something", "please", "that", "this", "these", "those", "is", "are", "be",
    "under", "below", "less", "than", "max", "size", "around", "about",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", value.lower() if value else "")


def _tokenize(value: str) -> set[str]:
    return {token for token in _normalize_text(value).split() if token}


def _content_tokens(value: str) -> set[str]:
    """Tokens with filler words removed — what a match should actually count."""
    return {token for token in _tokenize(value) if token not in _STOPWORDS}


def _match_size(listing_size: str, requested_size: str) -> bool:
    if not requested_size or not listing_size:
        return True
    listing_size = listing_size.lower().strip()
    requested_size = requested_size.lower().strip()
    if requested_size == listing_size:
        return True
    if requested_size in listing_size or listing_size in requested_size:
        return True
    return False


def _score_listing(listing: dict, description_tokens: set[str]) -> int:
    """
    Score keyword overlap, weighting the title higher than the rest of the
    fields so "graphic tee" beats an item that merely mentions it in passing.
    """
    title_tokens = _content_tokens(listing.get("title") or "")
    rest_tokens = _content_tokens(" ".join(
        [
            listing.get("description") or "",
            listing.get("category") or "",
            " ".join(listing.get("style_tags") or []),
            " ".join(listing.get("colors") or []),
            listing.get("brand") or "",
            listing.get("platform") or "",
        ]
    ))

    score = 0
    for token in description_tokens:
        if token in title_tokens:
            score += 3
        elif token in rest_tokens:
            score += 1
    return score


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    description_tokens = _content_tokens(description or "")

    filtered = []
    for listing in listings:
        if max_price is not None and listing.get("price") is not None:
            if listing["price"] > max_price:
                continue
        if not _match_size(listing.get("size", ""), size):
            continue
        score = _score_listing(listing, description_tokens)
        if score <= 0:
            continue
        filtered.append((score, listing))

    filtered.sort(key=lambda item: item[0], reverse=True)
    return [listing for _, listing in filtered[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _format_item(item: dict) -> str:
    """One-line description of a listing/wardrobe item for an LLM prompt."""
    name = item.get("title") or item.get("name") or "item"
    bits = []
    if item.get("category"):
        bits.append(item["category"])
    if item.get("colors"):
        bits.append("/".join(item["colors"]))
    if item.get("style_tags"):
        bits.append(", ".join(item["style_tags"]))
    detail = f" ({'; '.join(bits)})" if bits else ""
    return f"{name}{detail}"


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    item_title = new_item.get("title", "this piece")
    item_line = _format_item(new_item)

    system = (
        "You are a sharp, friendly personal stylist. Be concrete and concise — "
        "name specific pieces, keep it to 2–4 sentences, and don't use bullet points."
    )

    if not items:
        prompt = (
            f"A shopper is considering this secondhand item:\n  {item_line}\n\n"
            "They don't have a wardrobe saved yet. Suggest how to style this piece: "
            "what kinds of items pair well with it, what vibe it suits, and a couple "
            "of concrete combinations using common basics."
        )
    else:
        wardrobe_lines = "\n".join(f"  - {_format_item(it)}" for it in items)
        prompt = (
            f"A shopper is considering this secondhand item:\n  {item_line}\n\n"
            f"Here is their current wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1–2 complete outfits built around the new item, naming the "
            "specific wardrobe pieces it should be worn with. Only use pieces from "
            "the wardrobe above, plus the new item."
        )

    try:
        result = _chat(prompt, temperature=0.7, system=system)
        if result:
            return result
    except Exception:
        pass

    # Fallback so the agent loop never breaks if the API is unavailable.
    if not items:
        return (
            f"This {item_title} would shine with clean denim or tailored black "
            "trousers and chunky sneakers for a casual, modern vibe. Add a simple "
            "black bag or silver jewelry to finish it off."
        )
    return (
        f"This {item_title} would pair well with neutral basics from your wardrobe — "
        "think a simple top, your go-to bottoms, and clean shoes to keep it the focal point."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return (
            "Can't write a fit card without an outfit yet — generate an outfit "
            "suggestion first, then try again."
        )

    title = new_item.get("title", "this find")
    platform = new_item.get("platform", "the marketplace")
    price = new_item.get("price")
    price_text = f"${price:.0f}" if isinstance(price, (int, float)) else "a steal"

    system = (
        "You write short, authentic OOTD captions for Instagram/TikTok — casual, "
        "a little playful, never like a product description."
    )
    prompt = (
        f"Write a 2–4 sentence outfit caption for a secondhand find.\n"
        f"Item: {title}\n"
        f"Price: {price_text}\n"
        f"Platform: {platform}\n"
        f"Outfit: {outfit}\n\n"
        "Mention the item name, price, and platform naturally (once each), capture "
        "the vibe in specific terms, and keep it sounding like a real person's post. "
        "A few tasteful emojis or hashtags are fine. Return only the caption."
    )

    try:
        # Higher temperature so different finds yield noticeably different captions.
        result = _chat(prompt, temperature=1.0, max_tokens=200, system=system)
        if result:
            return result
    except Exception:
        pass

    # Fallback caption if the API is unavailable.
    return (
        f"Just scored {title} on {platform} for {price_text}. {outfit} "
        "Easy, wearable, and low-key elevated. ✨"
    )
