"""
ICT value objects: validation, derived views and serialisation.

These are pure domain objects, so the checks here are exact -- an inverted
window or an out-of-order Power of Three must raise, ``to_dict`` must round-trip
the enums to their string values, and the ``ICTAnalysis`` derived views must
filter rather than re-detect.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone

import pytest

from aetheros.trading.domain.enums import (
    AMDPhase,
    Direction,
    ICTConcept,
    KillZoneName,
    LiquidityPoolKind,
    SessionModelKind,
    SessionName,
    TrendState,
)
from aetheros.trading.domain.ict import (
    AMDPhaseWindow,
    DailyBias,
    ICTAnalysis,
    JudasSwing,
    KillZone,
    KillZoneWindow,
    LiquidityPool,
    MarketStructureShift,
    OTEZone,
    PowerOfThree,
    SessionModel,
    SessionWindow,
    TradingSession,
)
from aetheros.trading.domain.provenance import Provenance, SourceTier

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
NY = "America/New_York"
DAY = date(2026, 1, 15)


# ----------------------------------------------------------------------
# Builders
# ----------------------------------------------------------------------


def _session_window(**overrides) -> SessionWindow:
    params = {
        "session": SessionName.ASIA,
        "start_at": NOW,
        "end_at": NOW + timedelta(hours=8),
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 102.0,
        "candle_count": 8,
        "first_index": 0,
        "last_index": 7,
    }
    params.update(overrides)
    return SessionWindow(**params)


def _bias(**overrides) -> DailyBias:
    params = {
        "direction": Direction.UP,
        "prior_day_date": date(2026, 1, 14),
        "prior_day_high": 105.0,
        "prior_day_low": 95.0,
        "prior_day_close": 103.0,
        "last_price": 104.0,
        "price_ratio": 0.9,
        "position": "premium",
        "timeframe": "1d",
    }
    params.update(overrides)
    return DailyBias(**params)


def _shift(**overrides) -> MarketStructureShift:
    params = {
        "direction": Direction.UP,
        "index": 9,
        "timestamp": NOW,
        "timeframe": "1d",
        "broken_level": 100.0,
        "broken_index": 4,
        "break_price": 101.5,
        "prior_trend": TrendState.UPTREND,
        "displacement": 1.5,
        "left_fair_value_gap": True,
    }
    params.update(overrides)
    return MarketStructureShift(**params)


def _kill_zone_window(**overrides) -> KillZoneWindow:
    params = {
        "name": KillZoneName.NY_AM,
        "session": SessionName.NEW_YORK,
        "start_at": NOW,
        "end_at": NOW + timedelta(hours=1),
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 102.0,
        "candle_count": 1,
        "range_share": 0.5,
        "timeframe": "1h",
        "first_index": 0,
        "last_index": 0,
    }
    params.update(overrides)
    return KillZoneWindow(**params)


def _ote(**overrides) -> OTEZone:
    params = {
        "direction": Direction.UP,
        "leg_high": 110.0,
        "leg_low": 100.0,
        "band_top": 107.9,
        "band_bottom": 106.18,
        "low_ratio": 0.618,
        "high_ratio": 0.79,
        "retracement_ratio": 0.25,
        "in_zone": False,
        "index": 5,
        "timestamp": NOW,
        "timeframe": "1h",
    }
    params.update(overrides)
    return OTEZone(**params)


def _pool(**overrides) -> LiquidityPool:
    params = {
        "kind": LiquidityPoolKind.SESSION_HIGH,
        "direction": Direction.UP,
        "level": 105.0,
        "index": 3,
        "timestamp": NOW,
        "timeframe": "1h",
    }
    params.update(overrides)
    return LiquidityPool(**params)


def _judas(**overrides) -> JudasSwing:
    params = {
        "session": SessionName.LONDON,
        "direction": Direction.DOWN,
        "swept_level": 101.0,
        "sweep_extreme": 102.0,
        "sweep_index": 6,
        "session_open": 100.5,
        "reversal_price": 98.8,
        "reversal_index": 11,
        "timestamp": NOW,
        "timeframe": "1h",
    }
    params.update(overrides)
    return JudasSwing(**params)


def _phase(phase: AMDPhase, offset_hours: int, **overrides) -> AMDPhaseWindow:
    start = NOW + timedelta(hours=offset_hours)
    params = {
        "phase": phase,
        "start_at": start,
        "end_at": start + timedelta(hours=2),
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.0,
        "candle_count": 2,
        "range_share": 0.3,
    }
    params.update(overrides)
    return AMDPhaseWindow(**params)


def _power_of_three(**overrides) -> PowerOfThree:
    params = {
        "session": SessionName.NEW_YORK,
        "start_at": NOW,
        "end_at": NOW + timedelta(hours=6),
        "direction": Direction.UP,
        "manipulation_side": Direction.DOWN,
        "phases": (
            _phase(AMDPhase.ACCUMULATION, 0),
            _phase(AMDPhase.MANIPULATION, 2),
            _phase(AMDPhase.DISTRIBUTION, 4),
        ),
        "session_open": 100.0,
        "session_close": 103.0,
        "timeframe": "1h",
    }
    params.update(overrides)
    return PowerOfThree(**params)


def _model(**overrides) -> SessionModel:
    params = {
        "session": SessionName.LONDON,
        "previous_session": SessionName.ASIA,
        "kind": SessionModelKind.SWEEP_AND_REVERSE,
        "direction": Direction.UP,
        "level_taken": 105.0,
        "timestamp": NOW,
        "timeframe": "1h",
    }
    params.update(overrides)
    return SessionModel(**params)


# ----------------------------------------------------------------------
# Session / time definitions
# ----------------------------------------------------------------------


def test_session_must_name_its_timezone_and_have_length():
    with pytest.raises(ValueError, match="must name its timezone"):
        TradingSession(
            name=SessionName.ASIA, start=time(20), end=time(2), timezone=""
        )
    with pytest.raises(ValueError, match="non-zero length"):
        TradingSession(
            name=SessionName.ASIA, start=time(2), end=time(2), timezone=NY
        )


def test_session_membership_and_wrap():
    asia = TradingSession(
        name=SessionName.ASIA, start=time(20), end=time(2), timezone=NY
    )
    assert asia.wraps_midnight is True
    # 23:00 and 01:00 in the exchange's own clock are both inside the wrap.
    assert asia.contains(datetime(2026, 1, 15, 23, tzinfo=asia.tzinfo)) is True
    assert asia.contains(datetime(2026, 1, 16, 1, tzinfo=asia.tzinfo)) is True
    # Midday is not -- the window is measured in local wall clock, not UTC.
    assert asia.contains(datetime(2026, 1, 16, 12, tzinfo=asia.tzinfo)) is False
    # 01:00 UTC is 20:00 EST the previous evening: Asia's opening minute.
    assert asia.contains(datetime(2026, 1, 16, 1, tzinfo=timezone.utc)) is True


def test_session_window_on_spans_midnight_when_wrapping():
    asia = TradingSession(
        name=SessionName.ASIA, start=time(20), end=time(2), timezone=NY
    )
    start, end = asia.window_on(DAY)
    assert start.astimezone(asia.tzinfo).date() == DAY
    assert end.astimezone(asia.tzinfo).date() == date(2026, 1, 16)
    assert end > start


def test_session_to_dict_reports_the_wrap():
    payload = TradingSession(
        name=SessionName.ASIA, start=time(20), end=time(2), timezone=NY,
        label="Asian",
    ).to_dict()
    assert payload["name"] == "asia"
    assert payload["label"] == "Asian"
    assert payload["start"] == "20:00:00"
    assert payload["timezone"] == NY
    assert payload["wraps_midnight"] is True


def test_kill_zone_validation_and_serialisation():
    with pytest.raises(ValueError, match="must name its timezone"):
        KillZone(
            name=KillZoneName.NY_AM, session=SessionName.NEW_YORK,
            start=time(8, 30), end=time(11), timezone="",
        )
    with pytest.raises(ValueError, match="non-zero length"):
        KillZone(
            name=KillZoneName.NY_AM, session=SessionName.NEW_YORK,
            start=time(8, 30), end=time(8, 30), timezone=NY,
        )
    zone = KillZone(
        name=KillZoneName.NY_AM, session=SessionName.NEW_YORK,
        start=time(8, 30), end=time(11), timezone=NY, label="New York AM",
    )
    assert zone.wraps_midnight is False
    assert zone.contains(datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)) is True
    payload = zone.to_dict()
    assert payload["name"] == "ny_am"
    assert payload["session"] == "new_york"


# ----------------------------------------------------------------------
# Session windows
# ----------------------------------------------------------------------


def test_session_window_rejects_inverted_bounds_and_counts():
    with pytest.raises(ValueError, match="must end after it starts"):
        _session_window(end_at=NOW - timedelta(hours=1))
    with pytest.raises(ValueError, match="must contain at least one bar"):
        _session_window(candle_count=0)
    with pytest.raises(ValueError, match="cannot end before it begins"):
        _session_window(first_index=5, last_index=2)


def test_session_window_rejects_impossible_geometry():
    with pytest.raises(ValueError, match="high cannot be below its low"):
        _session_window(high=98.0)
    with pytest.raises(ValueError, match="open must lie within its range"):
        _session_window(open=110.0)
    with pytest.raises(ValueError, match="close must lie within its range"):
        _session_window(close=90.0)


def test_session_window_rejects_non_finite_levels():
    with pytest.raises(ValueError, match="Session high must be finite"):
        _session_window(high=math.inf)


def test_session_window_range_and_to_dict():
    window = _session_window()
    assert window.range == pytest.approx(6.0)
    payload = window.to_dict()
    assert payload["session"] == "asia"
    assert payload["range"] == pytest.approx(6.0)
    assert payload["candle_count"] == 8
    assert payload["start_at"] == NOW.isoformat()


# ----------------------------------------------------------------------
# Daily bias
# ----------------------------------------------------------------------


def test_daily_bias_validation():
    with pytest.raises(ValueError, match="high must be above its low"):
        _bias(prior_day_high=95.0)
    with pytest.raises(ValueError, match="Unknown range position"):
        _bias(position="cheap")
    with pytest.raises(ValueError, match="price ratio must be finite"):
        _bias(price_ratio=math.nan)


def test_daily_bias_to_dict_tags_its_concept():
    payload = _bias(evidence=("close above the prior day high",)).to_dict()
    assert payload["concept"] == ICTConcept.DAILY_BIAS.value
    assert payload["direction"] == "up"
    assert payload["trend"] == "unknown"
    assert payload["prior_day_date"] == "2026-01-14"
    assert payload["position"] == "premium"
    assert payload["evidence"] == ["close above the prior day high"]


# ----------------------------------------------------------------------
# Market structure shift
# ----------------------------------------------------------------------


def test_market_structure_shift_validation():
    with pytest.raises(ValueError, match="prices must be positive"):
        _shift(broken_level=0.0)
    with pytest.raises(ValueError, match="broken level must be finite"):
        _shift(broken_level=math.inf)
    with pytest.raises(ValueError, match="Displacement cannot be negative"):
        _shift(displacement=-0.5)
    with pytest.raises(ValueError, match="earlier swing point"):
        _shift(index=4, broken_index=4)


def test_market_structure_shift_to_dict():
    payload = _shift(
        direction=Direction.DOWN,
        prior_trend=TrendState.UPTREND,
        session=SessionName.NEW_YORK,
    ).to_dict()
    assert payload["concept"] == "market_structure_shift"
    assert payload["direction"] == "down"
    assert payload["prior_trend"] == "uptrend"
    assert payload["session"] == "new_york"
    assert payload["displacement"] == pytest.approx(1.5)
    assert payload["left_fair_value_gap"] is True
    # With no session resolved the field is explicitly null, not absent.
    assert _shift().to_dict()["session"] is None


# ----------------------------------------------------------------------
# Kill zones
# ----------------------------------------------------------------------


def test_kill_zone_window_validation():
    with pytest.raises(ValueError, match="must end after it starts"):
        _kill_zone_window(end_at=NOW - timedelta(hours=1))
    with pytest.raises(ValueError, match="high cannot be below its low"):
        _kill_zone_window(high=98.0)
    with pytest.raises(ValueError, match="range share must lie within 0 and 1"):
        _kill_zone_window(range_share=1.5)
    with pytest.raises(ValueError, match="must contain at least one bar"):
        _kill_zone_window(candle_count=0)
    with pytest.raises(ValueError, match="swept level must be positive"):
        _kill_zone_window(swept_level=0.0)


def test_kill_zone_window_range_and_to_dict():
    window = _kill_zone_window(swept_level=104.5, swept_direction=Direction.UP)
    assert window.range == pytest.approx(6.0)
    payload = window.to_dict()
    assert payload["concept"] == "kill_zone"
    assert payload["name"] == "ny_am"
    assert payload["range_share"] == pytest.approx(0.5)
    assert payload["swept_level"] == pytest.approx(104.5)
    assert payload["swept_direction"] == "up"


def test_kill_zone_window_without_a_sweep_serialises_nulls():
    payload = _kill_zone_window().to_dict()
    assert payload["swept_level"] is None
    assert payload["swept_direction"] is None


# ----------------------------------------------------------------------
# OTE
# ----------------------------------------------------------------------


def test_ote_validation():
    with pytest.raises(ValueError, match="leg must have a high above its low"):
        _ote(leg_low=110.0)
    with pytest.raises(ValueError, match="band top must be above its bottom"):
        _ote(band_top=100.0, band_bottom=100.0)
    with pytest.raises(ValueError, match="OTE ratios must satisfy"):
        _ote(low_ratio=0.8, high_ratio=0.79)
    with pytest.raises(ValueError, match="band top must be finite"):
        _ote(band_top=math.inf)


def test_ote_to_dict_keeps_the_band_and_the_ratios():
    payload = _ote().to_dict()
    assert payload["concept"] == "ote"
    assert payload["band_bottom"] == pytest.approx(106.18)
    assert payload["band_top"] == pytest.approx(107.9)
    assert payload["low_ratio"] == pytest.approx(0.618)
    assert payload["in_zone"] is False
    assert payload["retracement_ratio"] == pytest.approx(0.25)


# ----------------------------------------------------------------------
# Liquidity pools
# ----------------------------------------------------------------------


def test_liquidity_pool_validation():
    with pytest.raises(ValueError, match="level must be positive"):
        _pool(level=0.0)
    with pytest.raises(ValueError, match="level must be finite"):
        _pool(level=math.inf)
    with pytest.raises(ValueError, match="must record the bar that took it"):
        _pool(taken=True)
    with pytest.raises(ValueError, match="cannot be taken before it forms"):
        _pool(index=5, taken=True, taken_index=4)


def test_liquidity_pool_to_dict():
    payload = _pool(
        kind=LiquidityPoolKind.EQUAL_LOWS,
        direction=Direction.DOWN,
        taken=True,
        taken_index=9,
        session=SessionName.LONDON,
    ).to_dict()
    assert payload["concept"] == "liquidity_pool"
    assert payload["kind"] == "equal_lows"
    assert payload["direction"] == "down"
    assert payload["taken"] is True
    assert payload["taken_index"] == 9
    assert payload["session"] == "london"


# ----------------------------------------------------------------------
# Judas swing
# ----------------------------------------------------------------------


def test_judas_swing_validation():
    with pytest.raises(ValueError, match="swept level must be positive"):
        _judas(swept_level=0.0)
    with pytest.raises(ValueError, match="sweep extreme must be finite"):
        _judas(sweep_extreme=math.inf)
    with pytest.raises(ValueError, match="must record the bar that swept"):
        _judas(sweep_index=-1)
    with pytest.raises(ValueError, match="cannot reverse before it sweeps"):
        _judas(sweep_index=6, reversal_index=5)


def test_judas_swing_to_dict():
    payload = _judas().to_dict()
    assert payload["concept"] == "judas_swing"
    assert payload["session"] == "london"
    assert payload["direction"] == "down"
    assert payload["swept_level"] == pytest.approx(101.0)
    assert payload["reversal_price"] == pytest.approx(98.8)
    assert payload["reversal_index"] == 11


# ----------------------------------------------------------------------
# Power of Three
# ----------------------------------------------------------------------


def test_amd_phase_validation():
    with pytest.raises(ValueError, match="must end after it starts"):
        _phase(AMDPhase.ACCUMULATION, 0, end_at=NOW)
    with pytest.raises(ValueError, match="high cannot be below its low"):
        _phase(AMDPhase.ACCUMULATION, 0, high=98.0)
    with pytest.raises(ValueError, match="range share must lie within 0 and 1"):
        _phase(AMDPhase.ACCUMULATION, 0, range_share=-0.1)
    with pytest.raises(ValueError, match="must contain at least one bar"):
        _phase(AMDPhase.ACCUMULATION, 0, candle_count=0)


def test_amd_phase_range_and_to_dict():
    phase = _phase(AMDPhase.MANIPULATION, 2)
    assert phase.range == pytest.approx(3.0)
    payload = phase.to_dict()
    assert payload["phase"] == "manipulation"
    assert payload["range"] == pytest.approx(3.0)
    assert payload["range_share"] == pytest.approx(0.3)


def test_power_of_three_requires_the_three_phases_in_order():
    with pytest.raises(ValueError, match="exactly the accumulation"):
        _power_of_three(
            phases=(
                _phase(AMDPhase.MANIPULATION, 0),
                _phase(AMDPhase.ACCUMULATION, 2),
                _phase(AMDPhase.DISTRIBUTION, 4),
            )
        )
    with pytest.raises(ValueError, match="exactly the accumulation"):
        _power_of_three(
            phases=(_phase(AMDPhase.ACCUMULATION, 0), _phase(AMDPhase.MANIPULATION, 2))
        )


def test_power_of_three_rejects_a_non_finite_session_edge():
    with pytest.raises(ValueError, match="Session open must be finite"):
        _power_of_three(session_open=math.nan)
    with pytest.raises(ValueError, match="must end after it starts"):
        _power_of_three(end_at=NOW - timedelta(hours=1))


def test_power_of_three_phase_accessors_and_to_dict():
    amd = _power_of_three()
    assert amd.accumulation.phase is AMDPhase.ACCUMULATION
    assert amd.manipulation.phase is AMDPhase.MANIPULATION
    assert amd.distribution.phase is AMDPhase.DISTRIBUTION
    payload = amd.to_dict()
    assert payload["concept"] == "power_of_three"
    assert payload["direction"] == "up"
    # The false move goes the other way to the realised direction.
    assert payload["manipulation_side"] == "down"
    assert [phase["phase"] for phase in payload["phases"]] == [
        "accumulation",
        "manipulation",
        "distribution",
    ]


# ----------------------------------------------------------------------
# Session models
# ----------------------------------------------------------------------


def test_session_model_validation():
    with pytest.raises(ValueError, match="taken level must be positive"):
        _model(level_taken=0.0)
    with pytest.raises(ValueError, match="Level taken must be finite"):
        _model(level_taken=math.inf)
    with pytest.raises(ValueError, match="must name the session it follows"):
        _model(previous_session=None)
    # An undefined model is the one case with no predecessor.
    undefined = _model(previous_session=None, kind=SessionModelKind.UNDEFINED)
    assert undefined.previous_session is None


def test_session_model_to_dict():
    payload = _model().to_dict()
    assert payload["concept"] == "session_model"
    assert payload["session"] == "london"
    assert payload["previous_session"] == "asia"
    assert payload["kind"] == "sweep_and_reverse"
    assert payload["level_taken"] == pytest.approx(105.0)
    assert _model(previous_session=None, kind=SessionModelKind.UNDEFINED).to_dict()[
        "previous_session"
    ] is None


# ----------------------------------------------------------------------
# Aggregate
# ----------------------------------------------------------------------


def test_analysis_defaults_are_empty_not_none():
    analysis = ICTAnalysis(
        instrument_key="TEST", timeframe="1h", last_price=100.0,
        exchange_timezone=NY,
    )
    assert analysis.sessions == ()
    assert analysis.daily_bias is None
    assert analysis.market_structure_shifts == ()
    assert analysis.kill_zones == ()
    assert analysis.ote is None
    assert analysis.liquidity_pools == ()
    assert analysis.judas_swings == ()
    assert analysis.power_of_three == ()
    assert analysis.session_models == ()
    assert analysis.limitations == ()
    assert analysis.resting_pools == ()
    assert analysis.taken_pools == ()
    payload = analysis.to_dict()
    assert payload["daily_bias"] is None
    assert payload["ote"] is None
    assert payload["provenance"] is None


def test_analysis_derived_pool_views_filter_without_redetecting():
    resting = _pool(index=2, level=105.0)
    taken = _pool(index=4, level=99.0, taken=True, taken_index=7)
    analysis = ICTAnalysis(
        instrument_key="TEST", timeframe="1h", last_price=100.0,
        exchange_timezone=NY, liquidity_pools=(resting, taken),
    )

    assert analysis.resting_pools == (resting,)
    assert analysis.taken_pools == (taken,)
    # The views partition the pools: nothing is invented and nothing is lost.
    assert len(analysis.resting_pools) + len(analysis.taken_pools) == len(
        analysis.liquidity_pools
    )


def test_analysis_to_dict_serialises_every_detection_and_derived_view():
    taken = _pool(index=4, level=99.0, taken=True, taken_index=7)
    analysis = ICTAnalysis(
        instrument_key="RELIANCE",
        timeframe="1h",
        last_price=104.0,
        exchange_timezone=NY,
        sessions=(_session_window(),),
        daily_bias=_bias(),
        market_structure_shifts=(_shift(),),
        kill_zones=(_kill_zone_window(),),
        ote=_ote(),
        liquidity_pools=(_pool(), taken),
        judas_swings=(_judas(),),
        power_of_three=(_power_of_three(),),
        session_models=(_model(),),
        provenance=Provenance(source="test", tier=SourceTier.DERIVED),
        limitations=("No bars fell inside these kill zones: asia.",),
        computed_at=NOW,
    )
    payload = analysis.to_dict()

    assert payload["instrument_key"] == "RELIANCE"
    assert payload["exchange_timezone"] == NY
    assert payload["computed_at"] == NOW.isoformat()
    assert len(payload["sessions"]) == 1
    assert payload["daily_bias"]["concept"] == "daily_bias"
    assert payload["market_structure_shifts"][0]["concept"] == "market_structure_shift"
    assert payload["kill_zones"][0]["concept"] == "kill_zone"
    assert payload["ote"]["concept"] == "ote"
    assert payload["judas_swings"][0]["concept"] == "judas_swing"
    assert payload["power_of_three"][0]["concept"] == "power_of_three"
    assert payload["session_models"][0]["concept"] == "session_model"
    assert len(payload["liquidity_pools"]) == 2
    assert len(payload["resting_pools"]) == 1
    assert len(payload["taken_pools"]) == 1
    assert payload["provenance"]["tier"] == SourceTier.DERIVED.value
    assert payload["limitations"] == ["No bars fell inside these kill zones: asia."]
