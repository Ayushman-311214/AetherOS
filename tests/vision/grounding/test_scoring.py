"""
Unit tests for the deterministic match scoring.

The scale is graded on purpose -- exact match beats phrase beats substring beats
token overlap -- so the engine can rank and band candidates. These lock the
grades so a later tweak cannot silently reshuffle that order.
"""

from __future__ import annotations

import pytest

from aetheros.vision.grounding.scoring import text_match_score, type_match_score


class TestTextMatchScore:
    def test_exact_is_one(self) -> None:
        assert text_match_score("search", "Search") == 1.0

    def test_whole_word_phrase(self) -> None:
        assert text_match_score("search", "Search bar") == 0.85

    def test_substring_of_candidate(self) -> None:
        # "set" is not a whole word in "settings", so it scores as a substring.
        assert text_match_score("set", "settings") == 0.7

    def test_candidate_substring_of_target(self) -> None:
        assert text_match_score("save file", "save") == 0.6

    def test_token_overlap_between(self) -> None:
        score = text_match_score("open file", "file menu")
        assert 0.3 < score < 0.7

    def test_no_overlap_is_zero(self) -> None:
        assert text_match_score("search", "File") == 0.0

    def test_empty_target_is_zero(self) -> None:
        assert text_match_score("", "anything") == 0.0

    def test_ordering_is_monotonic(self) -> None:
        exact = text_match_score("ok", "ok")
        phrase = text_match_score("ok", "ok button")
        substr = text_match_score("ok", "okay")
        assert exact > phrase > substr


class TestTypeMatchScore:
    def test_exact_type(self) -> None:
        assert type_match_score("button", "button") == 1.0

    def test_partial_type(self) -> None:
        assert type_match_score("button", "push-button") == 0.5

    def test_unrelated_type(self) -> None:
        assert type_match_score("button", "person") == 0.0

    def test_no_target_type(self) -> None:
        assert type_match_score(None, "button") == 0.0
