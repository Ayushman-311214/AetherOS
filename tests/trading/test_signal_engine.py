"""
Evidence-based signal engine (Phase 5).

Covers evidence aggregation, conflicting evidence, missing data, signal
generation, probability boundaries, confidence, risk/reward, invalidation,
determinism and explanation structure. Deterministic synthetic fixtures only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.domain.evidence import Evidence
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.market_intel.features import MarketFeatures
from aetheros.trading.signal_engine.evidence import EvidenceLedger, MissingSource
from aetheros.trading.signal_engine.features import features_to_evidence
from aetheros.trading.signal_engine.scoring import compute_scores
from aetheros.trading.signal_engine.service import SignalEngineService

_INST = Instrument.parse("TEST")
_PROV = Provenance(source="t", tier=SourceTier.PRIMARY)
_MOCK = Provenance(source="mock", tier=SourceTier.MOCK)
_QUAL = DataQuality(status=DataQualityStatus.OK)


def _ev(
    direction=Direction.UP,
    weight=0.5,
    *,
    etype=EvidenceType.MARKET_STRUCTURE,
    detail="test evidence",
    mock=False,
    assertion=Assertion.CALCULATED,
    quality=_QUAL,
):
    return Evidence(
        instrument_key="TEST",
        type=etype,
        assertion=assertion,
        direction=direction,
        detail=detail,
        weight=weight,
        confidence=Confidence.MEDIUM,
        provenance=_MOCK if mock else _PROV,
        quality=quality,
    )


def _analysis(direction=Direction.UP, evidence=(), is_mock=False):
    """A minimal TradingAnalysis-like stand-in via the real class."""
    from aetheros.trading.domain.analysis import TradingAnalysis, VolumeAnalysis
    from aetheros.trading.domain.technical import TechnicalSnapshot
    from aetheros.trading.domain.structure import MarketStructure
    from aetheros.trading.domain.enums import TrendState, Timeframe
    prov = _MOCK if is_mock else _PROV
    tech = TechnicalSnapshot(
        timeframe=Timeframe.D1, last_price=100.0, bars=50,
        provenance=prov,
    )
    struct = MarketStructure(
        trend=TrendState.UPTREND, trend_strength=0.6, swings=(),
        supports=(), resistances=(), signals=(),
        higher_highs=True, higher_lows=True, lower_highs=False, lower_lows=False,
    )
    return TradingAnalysis(
        instrument=_INST, timeframe_value="1d", last_price=100.0,
        direction=direction, directional_score=0.5,
        confidence=Confidence.MEDIUM, technical=tech, structure=struct,
        evidence=tuple(evidence), volume=None,
        quality=_QUAL, provenance=prov, limitations=(),
    )


def _market_features(**kw):
    base = dict(symbol="TEST", timeframe="1d")
    base.update(kw)
    return MarketFeatures(**base)


# ----------------------------------------------------------------------
# EvidenceLedger: aggregation + contradiction split + missing
# ----------------------------------------------------------------------


def test_ledger_splits_supporting_and_contradicting():
    items = (
        _ev(Direction.UP, 0.5),
        _ev(Direction.UP, 0.4),
        _ev(Direction.DOWN, 0.6),
    )
    ledger = EvidenceLedger(items=items, fused_direction=Direction.UP)
    assert len(ledger.supporting) == 2
    assert len(ledger.opposing) == 1
    assert ledger.opposing_weight == pytest.approx(0.6)
    assert ledger.net_weight == pytest.approx(0.3)


def test_ledger_unreliable_items_never_tip_direction():
    # A mock item is unreliable: counted, but cannot move the weight.
    items = (
        _ev(Direction.DOWN, 0.9, mock=True),
        _ev(Direction.UP, 0.5),
    )
    ledger = EvidenceLedger(items=items, fused_direction=Direction.UP)
    assert ledger.supporting_weight == pytest.approx(0.5)
    assert ledger.opposing_weight == pytest.approx(0.0)


def test_ledger_missing_sources_counted_not_neutral():
    items = (_ev(Direction.UP, 0.5),)
    missing = (MissingSource("liquidity", "not provided"),
               MissingSource("news", "provider offline"))
    ledger = EvidenceLedger(
        items=items, missing=missing, fused_direction=Direction.UP,
    )
    assert ledger.missing_count == 2
    # Missing sources reduce coverage, never add weight.
    cov = ledger.coverage(expected_sources=4)
    assert cov == pytest.approx(0.5)


def test_coverage_full_when_no_missing():
    ledger = EvidenceLedger(items=(_ev(),), fused_direction=Direction.UP)
    assert ledger.coverage(2) == pytest.approx(1.0)


# ----------------------------------------------------------------------
# Scoring: raw vs model vs probability vs confidence (separation)
# ----------------------------------------------------------------------


def test_scores_separate_raw_model_probability_confidence():
    items = (_ev(Direction.UP, 0.8), _ev(Direction.UP, 0.6))
    ledger = EvidenceLedger(items=items, fused_direction=Direction.UP)
    s = compute_scores(ledger, expected_sources=2)
    # Raw score is the aggregation, not a probability.
    assert -1.0 <= s.raw_evidence_score <= 1.0
    assert s.probability_up is None          # no calibrated model wired
    assert s.has_calibrated_probability is False
    assert s.confidence in (Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH)


def test_scores_surfaced_probability_only_when_reliable():
    items = (_ev(Direction.UP, 0.8),)
    ledger = EvidenceLedger(items=items, fused_direction=Direction.UP)
    s = compute_scores(
        ledger, calibrated_probability=0.74, probability_reliable=True,
    )
    assert s.probability_up == pytest.approx(0.74)
    assert s.has_calibrated_probability is True
    # When not reliable, the raw score is never back-filled into a probability.
    s2 = compute_scores(
        ledger, calibrated_probability=0.74, probability_reliable=False,
    )
    assert s2.probability_up is None


def test_confidence_drops_on_thin_evidence():
    thin = EvidenceLedger(items=(), fused_direction=Direction.UP)
    s = compute_scores(thin)
    assert s.confidence is Confidence.LOW
    # A strong agreeing read is more confident.
    strong = EvidenceLedger(
        items=tuple(_ev(Direction.UP, 0.6) for _ in range(4)),
        fused_direction=Direction.UP,
    )
    s2 = compute_scores(strong, expected_sources=4)
    assert s2.confidence in (Confidence.MEDIUM, Confidence.HIGH)


def test_confidence_drops_on_contradiction():
    items = tuple(_ev(Direction.UP, 0.5) for _ in range(2)) + tuple(
        _ev(Direction.DOWN, 0.5) for _ in range(2)
    )
    ledger = EvidenceLedger(items=items, fused_direction=Direction.UP)
    s = compute_scores(ledger)
    assert s.agreement == pytest.approx(0.5)  # split evidence -> low agreement


# ----------------------------------------------------------------------
# features_to_evidence: missing sources recorded, not neutral
# ----------------------------------------------------------------------


def test_features_missing_recorded_not_neutral():
    ev, missing, provided = features_to_evidence(
        market_features=None, liquidity_features=None, heatmap_cells=(),
        instrument=_INST, timeframe="1d",
        provenance=_PROV, quality=_QUAL,
    )
    assert provided == 0
    assert {m.source for m in missing} == {
        "market_features", "liquidity_features", "heatmap",
    }
    assert ev == []


def test_market_features_produce_evidence():
    mf = _market_features(
        trend_strength=0.7, structure_strength=0.6, momentum=3.0,
        regime="trending_bullish", regime_confidence=0.8,
        volume_delta=0.3, vwap_distance=1.5,
    )
    ev, missing, provided = features_to_evidence(
        market_features=mf, liquidity_features=None, heatmap_cells=(),
        instrument=_INST, timeframe="1d",
        provenance=_PROV, quality=_QUAL,
    )
    assert provided == 1
    assert len(ev) > 0
    # Market features should produce bullish evidence for the bull read.
    dirs = {e.direction for e in ev}
    assert Direction.UP in dirs


def test_neutral_feature_read_no_forced_direction():
    mf = _market_features()  # all zeros/unknown
    ev, _, _ = features_to_evidence(
        market_features=mf, liquidity_features=None, heatmap_cells=(),
        instrument=_INST, timeframe="1d",
        provenance=_PROV, quality=_QUAL,
    )
    # No fabricated directional evidence from a neutral read.
    assert not any(
        e.direction in (Direction.UP, Direction.DOWN) and e.is_reliable
        for e in ev
    )


# ----------------------------------------------------------------------
# SignalAssessment: the full engine read
# ----------------------------------------------------------------------


def test_assessment_shape_and_missing_accounting():
    eng = SignalEngineService(get_settings())
    analysis = _analysis(Direction.UP, evidence=(_ev(Direction.UP, 0.6),))
    r = eng.assess(
        analysis,
        market_features=_market_features(
            trend_strength=0.7, regime="trending_bullish",
            regime_confidence=0.8, momentum=3.0,
        ),
    )
    d = r.to_dict()
    assert d["direction"] == "up"
    assert "probability" in d and d["probability"] is None  # no calibrated model
    assert "scores" in d
    assert "contradicting" in d and "supporting" in d
    missing = {m["source"] for m in d["missing_sources"]}
    assert {"liquidity_features", "heatmap", "risk", "probability"} <= missing
    assert 0.0 <= d["coverage"] <= 1.0
    assert d["is_mock"] is False


def test_assessment_contradicting_evidence_surfaced():
    eng = SignalEngineService(get_settings())
    analysis = _analysis(
        Direction.UP,
        evidence=(
            _ev(Direction.UP, 0.6),
            _ev(Direction.DOWN, 0.7, detail="resistance wall"),
        ),
    )
    r = eng.assess(analysis)
    assert len(r.contradicting) >= 1
    assert any(e.detail == "resistance wall" for e in r.contradicting)
    # The contradiction is in the limitations/risk factors, not hidden.
    assert any("contradict" in lim for lim in r.limitations) or r.risk_factors


def test_assessment_no_false_precision_without_risk():
    eng = SignalEngineService(get_settings())
    r = eng.assess(_analysis(Direction.UP))
    # No risk engine wired -> no entry/targets/RR, honest invalidation.
    assert r.entry is None
    assert r.risk_reward_ratio is None
    assert r.targets == ()
    assert "not wired" in r.invalidation or "No" in r.invalidation


def _strip_wallclock(d):
    """Recursively drop wall-clock fields for a determinism comparison."""
    if isinstance(d, dict):
        return {
            k: _strip_wallclock(v)
            for k, v in d.items()
            if k not in ("created_at", "generated_at", "retrieved_at")
        }
    if isinstance(d, list):
        return [_strip_wallclock(v) for v in d]
    return d


def test_assessment_deterministic():
    eng = SignalEngineService(get_settings())
    a = _analysis(Direction.UP, evidence=(_ev(Direction.UP, 0.6),))
    mf = _market_features(trend_strength=0.7, regime="trending_bullish",
                          regime_confidence=0.8, momentum=3.0)
    r1 = _strip_wallclock(eng.assess(a, market_features=mf).to_dict())
    r2 = _strip_wallclock(eng.assess(a, market_features=mf).to_dict())
    assert r1 == r2


def test_assessment_not_actionable_on_mock():
    eng = SignalEngineService(get_settings())
    a = _analysis(Direction.UP, evidence=(_ev(Direction.UP, 0.6),), is_mock=True)
    r = eng.assess(a)
    assert r.is_mock is True
    assert r.is_actionable is False


def test_assessment_probability_never_fabricated():
    eng = SignalEngineService(get_settings())
    r = eng.assess(_analysis(Direction.UP))
    assert r.probability_up is None
    assert any("calibrated" in lim or "probability" in lim
               for lim in r.limitations)
