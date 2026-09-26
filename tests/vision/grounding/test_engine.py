"""
Unit tests for the grounding engine.

The engine ties parsing, scoring, spatial geometry and confidence banding
together, so these drive it end to end against a fake VisionService with
recorded OCR blocks and detections -- no real screen, no real model. Each test
fixes one behaviour the agent depends on: a clean text match is safe to act on,
an ambiguous or weak one is not, a spatial relation and an ordinal resolve
geometrically, and a request with no perception or no match fails with a
structured, readable reason rather than a guessed click.
"""

from __future__ import annotations

import pytest

from aetheros.vision.grounding.engine import GroundingEngine
from aetheros.vision.grounding.models import BAND_HIGH, BAND_LOW, BAND_MEDIUM
from aetheros.vision.models import Detection, TextBlock

HIGH = 0.75
MEDIUM = 0.45


def _block(text, left, top, right, bottom, confidence=0.95):
    return TextBlock(
        text=text,
        confidence=confidence,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


def _det(label, left, top, right, bottom, confidence=0.9):
    return Detection(
        label=label,
        confidence=confidence,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


def _engine(vision):
    return GroundingEngine(vision, high_threshold=HIGH, medium_threshold=MEDIUM)


class TestTextGrounding:
    @pytest.mark.asyncio
    async def test_exact_match_is_high_and_safe(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr([_block("Search", 100, 50, 180, 90)])
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("the Search button", bgr_image)

        assert r.success is True
        assert r.matched_text == "Search"
        assert r.source == "ocr"
        assert r.confidence_band == BAND_HIGH
        assert r.safe_to_act is True
        assert r.bbox == {"x": 100, "y": 50, "width": 80, "height": 40}
        assert r.center == {"x": 140, "y": 70}

    @pytest.mark.asyncio
    async def test_best_scoring_candidate_wins(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr(
            [
                _block("Search settings", 0, 0, 200, 40),
                _block("Search", 0, 100, 120, 140),
            ]
        )
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("Search", bgr_image)

        # Exact "Search" (1.0) beats the phrase match "Search settings" (0.85),
        # and the 0.15 gap is wide enough not to read as ambiguous.
        assert r.matched_text == "Search"
        assert r.candidates_considered == 2
        assert r.safe_to_act is True


class TestDetectionGrounding:
    @pytest.mark.asyncio
    async def test_type_match_via_detector(
        self, make_vision_service, make_fake_ocr, make_fake_detector, bgr_image
    ) -> None:
        ocr = make_fake_ocr([])
        detector = make_fake_detector([_det("button", 20, 30, 120, 70)])
        engine = _engine(make_vision_service(ocr=ocr, detector=detector))

        r = await engine.ground("the button", bgr_image)

        assert r.success is True
        assert r.source == "detection"
        assert r.element_type == "button"
        assert r.confidence_band == BAND_HIGH
        assert r.center == {"x": 70, "y": 50}


class TestConfidenceBands:
    @pytest.mark.asyncio
    async def test_substring_match_is_medium_not_safe(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        # "set" is a substring of "settings" -> 0.7, under the 0.75 HIGH gate.
        ocr = make_fake_ocr([_block("settings", 0, 0, 100, 40)])
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("set", bgr_image)

        assert r.matched_text == "settings"
        assert r.confidence_band == BAND_MEDIUM
        assert r.safe_to_act is False

    @pytest.mark.asyncio
    async def test_token_overlap_is_low(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr([_block("file menu", 0, 0, 100, 40)])
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("open file", bgr_image)

        assert r.success is True
        assert r.confidence_band == BAND_LOW
        assert r.safe_to_act is False


class TestAmbiguity:
    @pytest.mark.asyncio
    async def test_two_equal_matches_are_penalised_and_unsafe(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr(
            [
                _block("Save", 0, 0, 60, 30),
                _block("Save", 200, 0, 260, 30),
            ]
        )
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("Save", bgr_image)

        # Both score 1.0; the tie drops confidence below HIGH and withholds
        # auto-action even though a match was clearly found.
        assert r.success is True
        assert r.confidence_band == BAND_MEDIUM
        assert r.safe_to_act is False
        assert "mbiguous" in r.reason


class TestSpatialRelation:
    @pytest.mark.asyncio
    async def test_below_anchor_selects_the_lower_element(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr(
            [
                _block("Login", 100, 50, 180, 80),
                _block("Submit", 100, 120, 180, 150),
            ]
        )
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("the button below Login", bgr_image)

        assert r.success is True
        assert r.matched_text == "Submit"
        assert r.center == {"x": 140, "y": 135}
        # Chosen by geometry, not a strong label: never auto-acted.
        assert r.safe_to_act is False

    @pytest.mark.asyncio
    async def test_missing_anchor_fails_clearly(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr([_block("Submit", 100, 120, 180, 150)])
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("the button below Login", bgr_image)

        assert r.success is False
        assert "login" in r.reason


class TestOrdinal:
    @pytest.mark.asyncio
    async def test_leftmost_picks_the_smallest_x(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr(
            [
                _block("Result", 300, 0, 380, 30),
                _block("Result", 10, 0, 90, 30),
                _block("Result", 150, 0, 230, 30),
            ]
        )
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("the leftmost result", bgr_image)

        assert r.success is True
        assert r.center["x"] == 50  # the block at left=10


class TestFailure:
    @pytest.mark.asyncio
    async def test_no_match_is_a_structured_failure(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr(
            [_block("File", 0, 0, 40, 20), _block("Edit", 0, 30, 40, 50)]
        )
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("Nonexistent", bgr_image)

        assert r.success is False
        assert r.safe_to_act is False
        assert r.center is None
        assert r.candidates_considered == 2

    @pytest.mark.asyncio
    async def test_no_perception_fails(
        self, make_vision_service, make_fake_ocr, bgr_image
    ) -> None:
        ocr = make_fake_ocr([], available=False)
        engine = _engine(make_vision_service(ocr=ocr))

        r = await engine.ground("anything", bgr_image)

        assert r.success is False
        assert "perception" in r.reason.lower()

    @pytest.mark.asyncio
    async def test_ocr_failure_is_survived_by_the_detector(
        self, make_vision_service, make_fake_ocr, make_fake_detector, bgr_image
    ) -> None:
        # OCR raises; a detector still grounds the target, so the caller gets a
        # result rather than an exception.
        ocr = make_fake_ocr(error=RuntimeError("ocr model crashed"))
        detector = make_fake_detector([_det("button", 20, 30, 120, 70)])
        engine = _engine(make_vision_service(ocr=ocr, detector=detector))

        r = await engine.ground("the button", bgr_image)

        assert r.success is True
        assert r.source == "detection"

