"""
Tests for agent._parse_query — extracting description, size, and max_price
from a natural-language query.

These lock in the parsing-order fix: price must be parsed before the bare-number
size fallback, so the "30" in "$30" becomes a price ceiling and never a size.
"""

from agent import _parse_query


def test_price_not_mistaken_for_size():
    parsed = _parse_query("looking for a vintage graphic tee under $30")
    assert parsed["max_price"] == 30.0
    assert parsed["size"] is None
    # The price phrase is stripped from the description.
    assert "$" not in parsed["description"]
    assert "30" not in parsed["description"]


def test_keyworded_size():
    parsed = _parse_query("90s track jacket in size M")
    assert parsed["size"] == "M"
    assert parsed["max_price"] is None


def test_numeric_shoe_size():
    parsed = _parse_query("black combat boots size 8")
    assert parsed["size"] == "8"
    assert parsed["max_price"] is None


def test_size_and_price_together():
    parsed = _parse_query("designer ballgown size XXS under $5")
    assert parsed["size"] == "XXS"
    assert parsed["max_price"] == 5.0


def test_no_filters():
    parsed = _parse_query("flowy midi skirt")
    assert parsed["size"] is None
    assert parsed["max_price"] is None
    assert "skirt" in parsed["description"]
