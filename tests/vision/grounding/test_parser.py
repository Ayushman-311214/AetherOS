"""
Unit tests for the grounding target parser.

The parser is pure lexical normalisation -- no perception, no LLM -- so every
phrase has one correct structured reading. These pin the vocabulary the spec
calls out: an element kind, a spatial relation to an anchor, and an ordinal.
"""

from __future__ import annotations

from aetheros.vision.grounding.parser import parse_target


class TestElementType:
    def test_button_is_recognised(self) -> None:
        t = parse_target("the Search button")
        assert t.element_type == "button"
        assert t.text == "search"

    def test_icon_is_recognised(self) -> None:
        t = parse_target("Click the Chrome icon")
        assert t.element_type == "icon"
        assert t.text == "chrome"

    def test_input_synonyms_map_to_field(self) -> None:
        assert parse_target("the username input").element_type == "field"
        assert parse_target("the search textbox").element_type == "field"

    def test_plain_label_has_no_type(self) -> None:
        t = parse_target("Submit")
        assert t.element_type is None
        assert t.text == "submit"


class TestSpatialRelation:
    def test_below_with_anchor(self) -> None:
        t = parse_target("the button below Login")
        assert t.relation == "below"
        assert t.anchor == "login"
        assert t.element_type == "button"

    def test_left_of_phrase_beats_bare_left(self) -> None:
        t = parse_target("the field to the left of Search")
        assert t.relation == "left_of"
        assert t.anchor == "search"

    def test_next_to_is_near(self) -> None:
        t = parse_target("the icon next to Settings")
        assert t.relation == "near"
        assert t.anchor == "settings"


class TestOrdinal:
    def test_leftmost(self) -> None:
        t = parse_target("the leftmost result")
        assert t.ordinal == "leftmost"

    def test_first_and_last(self) -> None:
        assert parse_target("the first link").ordinal == "first"
        assert parse_target("the last row").ordinal == "last"

    def test_no_ordinal(self) -> None:
        assert parse_target("the OK button").ordinal is None
