"""
SMC value objects: validation, derived views and serialisation.

These are pure domain objects, so the checks here are exact -- an inverted zone
must raise, ``to_dict`` must round-trip the enums to their string values, and
the ``mitigation_blocks`` view must filter rather than re-detect.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from aetheros.trading.domain.enums import (
    Confidence,
    Direction,
    LiquidityEventKind,
    SMCZoneKind,
    StructureBreakType,
    TrendState,
)
from aetheros.trading.domain.provenance import Provenance, SourceTier
from aetheros.trading.domain.smc import (
    DealingRange,
    LiquidityEvent,
    SMCAnalysis,
    SMCZone,
    StructureBreak,
)

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def _zone(**overrides) -> SMCZone:
    params = {
        "kind": SMCZoneKind.ORDER_BLOCK,
        "direction": Direction.UP,
        "top": 101.0,
        "bottom": 100.0,
        "index": 5,
        "timestamp": NOW,
        "timeframe": "1d",
        "confidence": Confidence.MEDIUM,
    }
    params.update(overrides)
    return SMCZone(**params)


def _break(**overrides) -> StructureBreak:
    params = {
        "kind": StructureBreakType.BOS,
        "direction": Direction.UP,
        "index": 9,
        "timestamp": NOW,
        "timeframe": "1d",
        "broken_level": 100.5,
        "broken_index": 4,
        "break_price": 101.5,
        "trend_before": TrendState.UPTREND,
        "confidence": Confidence.HIGH,
    }
    params.update(overrides)
    return StructureBreak(**params)


def test_zone_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="strictly above its bottom"):
        _zone(top=100.0, bottom=100.0)
    with pytest.raises(ValueError, match="strictly above its bottom"):
        _zone(top=99.0, bottom=100.0)


def test_zone_rejects_non_finite_bounds():
    with pytest.raises(ValueError, match="must be finite"):
        _zone(top=math.inf)
    with pytest.raises(ValueError, match="must be finite"):
        _zone(bottom=math.nan)


def test_zone_mitigation_invariants():
    with pytest.raises(ValueError, match="cannot be mitigated before it forms"):
        _zone(mitigation_index=4)
    with pytest.raises(ValueError, match="must record the bar that did it"):
        _zone(mitigated=True)
    with pytest.raises(ValueError, match="invalidated without being touched"):
        _zone(invalidated=True)
    # A touched-then-closed-through zone is a coherent object.
    zone = _zone(mitigated=True, invalidated=True, mitigation_index=7)
    assert zone.mitigated and zone.invalidated


def test_zone_geometry():
    zone = _zone(top=101.5, bottom=99.5)
    assert zone.height == pytest.approx(2.0)
    assert zone.midpoint == pytest.approx(100.5)


def test_zone_to_dict_serialises_enums_and_bounds():
    payload = _zone(
        kind=SMCZoneKind.FAIR_VALUE_GAP,
        direction=Direction.DOWN,
        top=101.5,
        bottom=100.5,
        evidence=("three-candle imbalance",),
    ).to_dict()

    assert payload["kind"] == "fair_value_gap"
    assert payload["direction"] == "down"
    assert payload["confidence"] == "medium"
    assert payload["top"] == 101.5
    assert payload["height"] == pytest.approx(1.0)
    assert payload["timestamp"] == NOW.isoformat()
    assert payload["evidence"] == ["three-candle imbalance"]


def test_break_rejects_a_swing_that_is_not_earlier():
    with pytest.raises(ValueError, match="earlier swing point"):
        _break(index=4, broken_index=4)
    with pytest.raises(ValueError, match="earlier swing point"):
        _break(index=4, broken_index=7)


def test_break_rejects_non_positive_and_non_finite_prices():
    with pytest.raises(ValueError, match="must be positive"):
        _break(broken_level=0.0)
    with pytest.raises(ValueError, match="must be finite"):
        _break(break_price=math.inf)


def test_break_to_dict_records_what_it_changed_from():
    payload = _break(
        kind=StructureBreakType.CHOCH,
        direction=Direction.DOWN,
        trend_before=TrendState.UPTREND,
    ).to_dict()

    assert payload["kind"] == "choch"
    assert payload["direction"] == "down"
    assert payload["trend_before"] == "uptrend"


def test_liquidity_event_validation_and_serialisation():
    with pytest.raises(ValueError, match="must be positive"):
        LiquidityEvent(
            kind=LiquidityEventKind.SWEEP,
            direction=Direction.DOWN,
            level=0.0,
            extreme=101.0,
            index=3,
            timestamp=NOW,
            timeframe="1d",
            confidence=Confidence.LOW,
        )
    payload = LiquidityEvent(
        kind=LiquidityEventKind.EQUAL_LOWS,
        direction=Direction.UP,
        level=99.5,
        extreme=99.4,
        index=12,
        timestamp=NOW,
        timeframe="1d",
        confidence=Confidence.MEDIUM,
        evidence=("swings at 4 and 12 within tolerance",),
    ).to_dict()
    assert payload["kind"] == "equal_lows"
    assert payload["level"] == 99.5
    assert payload["extreme"] == 99.4


def test_dealing_range_validation():
    with pytest.raises(ValueError, match="strictly above its low"):
        DealingRange(
            high=100.0, low=100.0, equilibrium=100.0, position="equilibrium",
            price_ratio=0.5, high_index=3, low_index=7,
        )
    with pytest.raises(ValueError, match="Unknown range position"):
        DealingRange(
            high=110.0, low=100.0, equilibrium=105.0, position="cheap",
            price_ratio=0.5, high_index=3, low_index=7,
        )
    with pytest.raises(ValueError, match="must be finite"):
        DealingRange(
            high=110.0, low=100.0, equilibrium=105.0, position="premium",
            price_ratio=math.inf, high_index=3, low_index=7,
        )


def test_dealing_range_keeps_an_out_of_range_ratio():
    # Price above the range low..high band is real information; never clamped.
    dealing_range = DealingRange(
        high=107.5, low=99.5, equilibrium=103.5, position="premium",
        price_ratio=1.0625, high_index=19, low_index=12,
    )
    assert dealing_range.to_dict()["price_ratio"] == pytest.approx(1.0625)


def test_analysis_derived_views_filter_without_redetecting():
    held = _zone(
        index=4,
        mitigated=True,
        mitigation_index=9,
        evidence=("price returned into the zone and held",),
    )
    closed_through = _zone(
        index=6, mitigated=True, invalidated=True, mitigation_index=10
    )
    fresh = _zone(index=8)
    gap = _zone(kind=SMCZoneKind.FAIR_VALUE_GAP, index=2)
    analysis = SMCAnalysis(
        instrument_key="TEST",
        timeframe="1d",
        last_price=105.0,
        zones=(held, closed_through, fresh, gap),
    )

    assert analysis.order_blocks == (held, closed_through, fresh)
    assert analysis.fair_value_gaps == (gap,)
    assert analysis.mitigation_blocks == (held,)


def test_analysis_to_dict_includes_derived_views_and_limitations():
    held = _zone(index=4, mitigated=True, mitigation_index=9)
    analysis = SMCAnalysis(
        instrument_key="TEST",
        timeframe="1d",
        last_price=105.0,
        trend=TrendState.UPTREND,
        breaks=(_break(),),
        zones=(held,),
        liquidity=(),
        dealing_range=DealingRange(
            high=107.5, low=99.5, equilibrium=103.5, position="discount",
            price_ratio=0.44, high_index=19, low_index=12,
        ),
        provenance=Provenance(source="test", tier=SourceTier.DERIVED),
        limitations=("Too few confirmed swings for an equal-highs read.",),
        computed_at=NOW,
    )
    payload = analysis.to_dict()

    assert payload["trend"] == "uptrend"
    assert payload["computed_at"] == NOW.isoformat()
    assert len(payload["breaks"]) == 1 and payload["breaks"][0]["kind"] == "bos"
    assert len(payload["mitigation_blocks"]) == 1
    assert payload["mitigation_blocks"][0]["index"] == 4
    assert payload["dealing_range"]["position"] == "discount"
    assert payload["provenance"]["tier"] == SourceTier.DERIVED.value
    assert payload["limitations"] == ["Too few confirmed swings for an equal-highs read."]


def test_analysis_defaults_are_empty_not_none():
    analysis = SMCAnalysis(instrument_key="TEST", timeframe="1d", last_price=100.0)
    assert analysis.breaks == ()
    assert analysis.zones == ()
    assert analysis.liquidity == ()
    assert analysis.dealing_range is None
    assert analysis.limitations == ()
    assert analysis.mitigation_blocks == ()
    assert analysis.to_dict()["dealing_range"] is None
