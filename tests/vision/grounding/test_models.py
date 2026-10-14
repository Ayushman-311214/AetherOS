"""
Unit tests for the grounding data models.

The models carry the public contract, so these pin the two calculations the
agent depends on -- the bbox (x/y/width/height) and the centre click point --
and the shape of the serialised result.
"""

from __future__ import annotations

from aetheros.vision.grounding.models import (
    BAND_HIGH,
    GroundingCandidate,
    GroundingResult,
)


def _candidate(**kw) -> GroundingCandidate:
    base = dict(
        text="Search",
        left=100,
        top=50,
        right=180,
        bottom=90,
        score=0.9,
        source="ocr",
    )
    base.update(kw)
    return GroundingCandidate(**base)


class TestCandidateGeometry:
    def test_width_height(self) -> None:
        c = _candidate()
        assert c.width == 80
        assert c.height == 40

    def test_center_is_the_midpoint(self) -> None:
        c = _candidate()
        assert c.center == (140, 70)

    def test_to_dict_bbox_and_center(self) -> None:
        d = _candidate().to_dict()
        assert d["bbox"] == {"x": 100, "y": 50, "width": 80, "height": 40}
        assert d["center"] == {"x": 140, "y": 70}


class TestResult:
    def test_from_candidate_carries_geometry(self) -> None:
        r = GroundingResult.from_candidate(
            _candidate(),
            query="the Search button",
            confidence=0.9,
            band=BAND_HIGH,
            safe_to_act=True,
            reason="matched",
            candidates_considered=3,
            target={"raw": "the Search button"},
        )
        assert r.success is True
        assert r.matched_text == "Search"
        assert r.bbox == {"x": 100, "y": 50, "width": 80, "height": 40}
        assert r.center == {"x": 140, "y": 70}
        assert r.safe_to_act is True

    def test_failure_is_not_safe(self) -> None:
        r = GroundingResult.failure(query="ghost", reason="not found")
        assert r.success is False
        assert r.safe_to_act is False
        assert r.center is None
        assert r.to_dict()["reason"] == "not found"
