"""
Unit tests for the spatial-relation geometry.

Plain rectangles, no perception: each relation is a pure arithmetic predicate,
so these fix the meaning of below/above/left_of/right_of/near/inside that the
engine relies on when resolving "the button below Login".
"""

from __future__ import annotations

from dataclasses import dataclass

from aetheros.vision.grounding import spatial


@dataclass
class Box:
    left: int
    top: int
    right: int
    bottom: int


ANCHOR = Box(100, 100, 200, 140)  # centre (150, 120)


class TestSatisfies:
    def test_below_requires_horizontal_overlap(self) -> None:
        under = Box(110, 200, 190, 240)  # overlaps x, lower
        assert spatial.satisfies("below", under, ANCHOR, near_radius=500)

        far = Box(400, 200, 480, 240)  # lower but no x overlap
        assert not spatial.satisfies("below", far, ANCHOR, near_radius=500)

    def test_above(self) -> None:
        over = Box(110, 20, 190, 60)
        assert spatial.satisfies("above", over, ANCHOR, near_radius=500)
        assert not spatial.satisfies("below", over, ANCHOR, near_radius=500)

    def test_left_and_right(self) -> None:
        left = Box(10, 100, 60, 140)
        right = Box(300, 100, 360, 140)
        assert spatial.satisfies("left_of", left, ANCHOR, near_radius=500)
        assert spatial.satisfies("right_of", right, ANCHOR, near_radius=500)
        assert not spatial.satisfies("left_of", right, ANCHOR, near_radius=500)

    def test_near_uses_radius(self) -> None:
        close = Box(210, 110, 240, 130)
        assert spatial.satisfies("near", close, ANCHOR, near_radius=200)
        assert not spatial.satisfies("near", close, ANCHOR, near_radius=10)

    def test_inside(self) -> None:
        within = Box(140, 110, 160, 130)  # centre inside anchor
        assert spatial.satisfies("inside", within, ANCHOR, near_radius=0)

    def test_unknown_relation_is_false(self) -> None:
        assert not spatial.satisfies("diagonal", ANCHOR, ANCHOR, near_radius=5)


class TestDistance:
    def test_symmetric_and_zero_on_self(self) -> None:
        assert spatial.distance(ANCHOR, ANCHOR) == 0.0
        b = Box(150, 220, 150, 220)
        assert spatial.distance(ANCHOR, b) == spatial.distance(b, ANCHOR)
