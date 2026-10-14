"""
Pure geometry helpers for spatial grounding.

These operate on anything exposing ``left/top/right/bottom`` (both
:class:`GroundingCandidate` and the vision models do), and answer the spatial
questions the parser produces: is this candidate below / above / left of /
right of / near / inside an anchor, and how far is it. No perception, no state
-- just arithmetic, so every relation is unit-testable with plain rectangles.
"""

from __future__ import annotations

import math
from typing import Protocol


class _Box(Protocol):
    left: int
    top: int
    right: int
    bottom: int


def center(box: _Box) -> tuple[float, float]:
    return ((box.left + box.right) / 2.0, (box.top + box.bottom) / 2.0)


def _h_overlap(a: _Box, b: _Box) -> bool:
    return a.left <= b.right and b.left <= a.right


def _v_overlap(a: _Box, b: _Box) -> bool:
    return a.top <= b.bottom and b.top <= a.bottom


def distance(a: _Box, b: _Box) -> float:
    """Euclidean distance between the two boxes' centres."""

    ax, ay = center(a)
    bx, by = center(b)
    return math.hypot(ax - bx, ay - by)


def satisfies(relation: str, candidate: _Box, anchor: _Box, *, near_radius: float) -> bool:
    """Whether ``candidate`` stands in ``relation`` to ``anchor``.

    "below"/"above" require the candidate to sit clear of the anchor vertically
    and to share some horizontal extent (so a control directly under a label
    qualifies but one off in a far corner does not); "left_of"/"right_of" are
    the horizontal mirror. "near" is a radius test; "inside" asks whether the
    candidate's centre falls within the anchor.
    """

    _, ay = center(anchor)
    ax, _ = center(anchor)
    cx, cy = center(candidate)

    if relation == "below":
        return cy > ay and _h_overlap(candidate, anchor)
    if relation == "above":
        return cy < ay and _h_overlap(candidate, anchor)
    if relation == "right_of":
        return cx > ax and _v_overlap(candidate, anchor)
    if relation == "left_of":
        return cx < ax and _v_overlap(candidate, anchor)
    if relation == "near":
        return distance(candidate, anchor) <= near_radius
    if relation == "inside":
        return (
            anchor.left <= cx <= anchor.right
            and anchor.top <= cy <= anchor.bottom
        )
    return False


__all__ = ["center", "distance", "satisfies"]
