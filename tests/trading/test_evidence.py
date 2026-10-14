"""
EvidenceService: turning deterministic reads into sourced, weighted claims.

The evidence layer must never invent a claim the inputs do not support, and it
must carry provenance/quality through so a mock or stale input can never be
laundered into a confident real signal (spec sections 8, 15, 61).
"""

from __future__ import annotations

from aetheros.trading.domain.enums import (
    Assertion,
    Confidence,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.domain.evidence import Evidence
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.enums import DataQualityStatus
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)

from .conftest import make_market_data


def _build(data):
    technical = TechnicalAnalysisService().compute(data)
    structure = MarketStructureService().analyze(data)
    volume = EvidenceService.build_volume_analysis(data)
    evidence = EvidenceService().build(
        data=data, technical=technical, structure=structure, volume=volume
    )
    return evidence


def test_uptrend_yields_bullish_leaning_evidence(uptrend_data):
    evidence = _build(uptrend_data)
    assert len(evidence) > 0
    up = sum(e.weight for e in evidence if e.direction is Direction.UP)
    down = sum(e.weight for e in evidence if e.direction is Direction.DOWN)
    assert up > down  # a clean uptrend should lean up on balance


def test_every_item_is_weighted_and_typed(uptrend_data):
    for e in _build(uptrend_data):
        assert 0.0 <= e.weight <= 1.0
        assert isinstance(e.type, EvidenceType)
        assert isinstance(e.assertion, Assertion)
        assert e.detail  # human-readable, non-empty
        assert e.id.startswith("ev_")


def test_evidence_inherits_provenance_and_quality(uptrend_data):
    for e in _build(uptrend_data):
        assert e.provenance.tier is SourceTier.PRIMARY
        assert e.quality.status is uptrend_data.quality.status


def test_mock_evidence_is_not_reliable():
    data = make_market_data(
        [100.0 + i * 0.5 for i in range(120)], tier=SourceTier.MOCK
    )
    evidence = _build(data)
    assert len(evidence) > 0
    # A calculated claim on non-mock data would be reliable; mock never is.
    assert all(not e.is_reliable for e in evidence)
    assert all(e.provenance.is_mock for e in evidence)


def test_primary_calculated_evidence_is_reliable(uptrend_data):
    evidence = _build(uptrend_data)
    calculated = [e for e in evidence if e.assertion is Assertion.CALCULATED]
    assert calculated  # uptrend produces calculated indicator claims
    assert all(e.is_reliable for e in calculated)


def test_evidence_is_deterministic(uptrend_data):
    a = [e.to_dict() for e in _build(uptrend_data)]
    b = [e.to_dict() for e in _build(uptrend_data)]
    # Content-addressed ids and detail must match run to run.
    assert [e["id"] for e in a] == [e["id"] for e in b]
    assert [e["detail"] for e in a] == [e["detail"] for e in b]


def test_stable_id_is_content_addressed():
    prov = Provenance(source="t", tier=SourceTier.PRIMARY)
    quality = DataQuality(status=DataQualityStatus.OK)
    kw = dict(
        instrument_key="TEST",
        type=EvidenceType.MOMENTUM,
        assertion=Assertion.CALCULATED,
        direction=Direction.UP,
        detail="RSI 60 shows bullish momentum.",
        weight=0.4,
        confidence=Confidence.MEDIUM,
        provenance=prov,
        quality=quality,
    )
    # Same content -> same id, even though created_at differs.
    assert Evidence(**kw).id == Evidence(**kw).id


def test_weight_is_clamped_into_unit_interval():
    prov = Provenance(source="t", tier=SourceTier.PRIMARY)
    quality = DataQuality(status=DataQualityStatus.OK)
    base = dict(
        instrument_key="TEST",
        type=EvidenceType.TREND,
        assertion=Assertion.CALCULATED,
        direction=Direction.UP,
        detail="x",
        confidence=Confidence.LOW,
        provenance=prov,
        quality=quality,
    )
    assert Evidence(**base, weight=5.0).weight == 1.0
    assert Evidence(**base, weight=-2.0).weight == 0.0


def test_volume_analysis_reports_relative_volume(uptrend_data):
    vol = EvidenceService.build_volume_analysis(uptrend_data)
    assert vol is not None
    assert vol.relative_volume >= 0.0
    assert vol.trend in ("rising", "falling", "flat")
    assert vol.observation
