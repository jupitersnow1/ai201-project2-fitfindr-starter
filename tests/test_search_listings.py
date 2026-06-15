"""
Tests for tools.search_listings and its scoring helpers.

These exercise the relevance fixes: stopwords are ignored, title matches are
weighted above other fields, and the price/size filters behave as documented.
None of these touch the Groq API.
"""

from tools import search_listings, _score_listing, _content_tokens


# ── scoring helpers ─────────────────────────────────────────────────────────

def test_content_tokens_drops_stopwords():
    tokens = _content_tokens("looking for a vintage graphic tee")
    assert "tee" in tokens
    assert "graphic" in tokens
    assert "looking" not in tokens
    assert "for" not in tokens
    assert "a" not in tokens


def test_title_match_outweighs_body_match():
    query_tokens = {"graphic", "tee"}
    in_title = {"title": "Graphic Tee", "description": ""}
    in_body = {"title": "Plain Jeans", "description": "pairs with a graphic tee"}
    assert _score_listing(in_title, query_tokens) > _score_listing(in_body, query_tokens)


# ── search_listings ─────────────────────────────────────────────────────────

def test_relevant_item_ranks_first():
    results = search_listings("vintage graphic tee", max_price=30)
    assert results, "expected at least one match"
    # The top hit should actually be a tee, not an item that merely mentions one.
    assert "tee" in results[0]["title"].lower()


def test_noisy_query_still_finds_the_tee():
    # Full filler-laden phrasing must not derail the top result.
    results = search_listings("looking for a vintage graphic tee")
    assert results
    assert "tee" in results[0]["title"].lower()


def test_max_price_filters_results():
    results = search_listings("jacket", max_price=20)
    assert all(item["price"] <= 20 for item in results)


def test_size_filters_results():
    results = search_listings("tee", size="L")
    # "L" should match listings whose size contains L (e.g. "L", "XL").
    assert all("l" in item["size"].lower() for item in results)


def test_no_match_returns_empty_list():
    results = search_listings("zzzznonexistentkeyword")
    assert results == []
