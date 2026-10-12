"""
Visual observations: vision reads as trading evidence with provenance (Phase 17).

The bridge translates the vision subsystem's own reads (TextBlock/Detection --
stubbed here, no models and no display) into trading-side VisualObservation
records and VISUAL evidence. Confidence is preserved verbatim and capped below
API-derived numbers; an empty vision result is an honest empty, never a
fabricated read.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import Assertion, Direction, EvidenceType
from aetheros.trading.domain.visual import VisualObservation
from aetheros.trading.services.visual_service import (
    EVIDENCE_CONFIDENCE_FLOOR,
    VisualObservationService,
)
from aetheros.vision.models import Detection, TextBlock

from .conftest import make_market_data


def _text(text: str, confidence: float = 0.9) -> TextBlock:
    return TextBlock(
        text=text,
        confidence=confidence,
        left=10,
        top=20,
        right=110,
        bottom=40,
    )


def _detection(label: str, confidence: float = 0.8) -> Detection:
    return Detection(
        label=label,
        confidence=confidence,
        left=5,
        top=5,
        right=50,
        bottom=60,
    )


def _service() -> VisualObservationService:
    return VisualObservationService()


# ==============================================================
# Observations
# ==============================================================


def test_text_blocks_become_observations_with_bbox():
    obs = _service().observe_text([_text("AAPL", 0.95)], instrument_key="NASDAQ:AAPL")
    assert len(obs) == 1
    first = obs[0]
    assert first.kind == "text"
    assert first.label == "AAPL"
    assert first.confidence == pytest.approx(0.95)
    assert first.source == "ocr"
    assert first.bbox == (10, 20, 110, 40)
    assert first.id.startswith("vo_")


def test_detections_become_observations_with_bbox():
    obs = _service().observe_objects(
        [_detection("trendline", 0.71)], instrument_key="NASDAQ:AAPL"
    )
    assert len(obs) == 1
    assert obs[0].kind == "object"
    assert obs[0].label == "trendline"
    assert obs[0].confidence == pytest.approx(0.71)
    assert obs[0].source == "detection"


def test_empty_vision_result_is_an_honest_empty():
    for obs in (
        _service().observe_text([], instrument_key="X"),
        _service().observe_objects([], instrument_key="X"),
    ):
        assert len(obs) == 1
        assert obs[0].kind == "empty"
        assert obs[0].confidence == 0.0


def test_observation_ids_are_content_addressed():
    a = _service().observe_text([_text("AAPL", 0.9)], instrument_key="X")[0]
    b = _service().observe_text([_text("AAPL", 0.9)], instrument_key="X")[0]
    assert a.id == b.id


def test_observation_rejects_bad_kind_and_confidence():
    with pytest.raises(ValueError, match="Unknown visual-observation kind"):
        VisualObservation(kind="scribble", label="x", confidence=0.5, source="ocr")
    with pytest.raises(ValueError, match="confidence"):
        VisualObservation(kind="text", label="x", confidence=1.5, source="ocr")


def test_observation_to_dict_shape():
    payload = _service().observe_text([_text("1d", 0.8)], instrument_key="X")[0].to_dict()
    assert payload["kind"] == "text"
    assert payload["bbox"] == [10, 20, 110, 40]
    assert "observed_at" in payload


# ==============================================================
# Evidence promotion
# ==============================================================


def test_strong_reads_promote_to_uncertain_visual_evidence():
    data = make_market_data([100.0 + i for i in range(30)])
    obs = _service().observe_text([_text("ascending triangle", 0.71)], instrument_key="X")
    (item,) = _service().to_evidence(obs, data)
    assert item.type is EvidenceType.VISUAL
    assert item.assertion is Assertion.UNCERTAIN
    assert item.direction is Direction.UNKNOWN
    assert item.weight == pytest.approx(0.5)  # capped: visual never outweighs API
    assert "ascending triangle" in item.detail
    assert "0.71" in item.detail
    assert item.data["bbox"] == [10, 20, 110, 40]


def test_weak_reads_stay_observations_not_evidence():
    data = make_market_data([100.0 + i for i in range(30)])
    obs = _service().observe_text(
        [_text("maybe", EVIDENCE_CONFIDENCE_FLOOR - 0.1)], instrument_key="X"
    )
    assert _service().to_evidence(obs, data) == ()


def test_empty_observations_never_become_evidence():
    data = make_market_data([100.0 + i for i in range(30)])
    obs = _service().observe_text([], instrument_key="X")
    assert _service().to_evidence(obs, data) == ()


def test_visual_confidence_is_preserved_verbatim():
    data = make_market_data([100.0 + i for i in range(30)])
    obs = _service().observe_objects([_detection("support", 0.83)], instrument_key="X")
    (item,) = _service().to_evidence(obs, data)
    assert item.confidence.value == "high"  # from_score(0.83), not upgraded
    assert item.data["observation_id"] == obs[0].id


def test_evidence_inherits_data_provenance():
    from aetheros.trading.domain.enums import SourceTier

    data = make_market_data(
        [100.0 + i for i in range(30)], tier=SourceTier.MOCK
    )
    obs = _service().observe_text([_text("AAPL", 0.9)], instrument_key="X")
    (item,) = _service().to_evidence(obs, data)
    assert item.provenance.is_mock is True
    assert item.is_reliable is False  # UNCERTAIN never counts as reliable
