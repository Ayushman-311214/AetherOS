"""
Deterministic match scoring for grounding candidates.

Kept separate from the engine so the numbers are unit-testable in isolation:
given a target label and a candidate's text, ``text_match_score`` always
returns the same value, with no perception or I/O involved. The scale is 0..1,
graded from an exact match down through phrase/substring/token overlap, so the
engine can rank candidates and map the winner onto a confidence band.
"""

from __future__ import annotations

import re


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text.casefold())


def text_match_score(target: str, candidate: str) -> float:
    """Score how well ``candidate`` text satisfies the ``target`` label.

    * exact (case-insensitive) equality            -> 1.0
    * target appears as a whole word / phrase       -> 0.85
    * target is a substring of the candidate        -> 0.7
    * candidate is a substring of the target         -> 0.6
    * partial token overlap (Jaccard)               -> 0.3..0.7
    * no overlap                                     -> 0.0

    An empty target scores 0.0 everywhere: there is nothing to match on, so the
    engine must fall back to element type or ordinal rather than to text.
    """

    t = (target or "").strip().casefold()
    c = (candidate or "").strip().casefold()

    if not t or not c:
        return 0.0

    if t == c:
        return 1.0

    # Whole-word / phrase containment, e.g. target "search" in "search bar".
    if re.search(rf"\b{re.escape(t)}\b", c):
        return 0.85

    if t in c:
        return 0.7

    if c in t:
        return 0.6

    t_tokens = set(_tokens(t))
    c_tokens = set(_tokens(c))
    if not t_tokens or not c_tokens:
        return 0.0

    overlap = t_tokens & c_tokens
    if not overlap:
        return 0.0

    jaccard = len(overlap) / len(t_tokens | c_tokens)
    return 0.3 + 0.4 * jaccard


def type_match_score(target_type: str | None, label: str) -> float:
    """Score a detection ``label`` against a desired element ``target_type``."""

    if not target_type:
        return 0.0

    t = target_type.casefold()
    l = (label or "").casefold()
    if not l:
        return 0.0

    if t == l:
        return 1.0
    if t in l or l in t:
        return 0.5
    return 0.0


__all__ = ["text_match_score", "type_match_score"]
