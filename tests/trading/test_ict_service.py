"""
ICTService: the assembled, session-aware ICT read.

The detectors themselves are pinned by ``test_ict_detectors.py`` and the time
layer by ``test_ict_sessions.py``; what is checked here is the *assembly* -- that
the service builds one shared context, reports the whole read, labels mock and
degraded data honestly, and refuses to analyse a series too short to mean
anything.

The candle series is generated (a deterministic zig-zag), because the assertions
here are about shape and honesty rather than about the value of any one
detection. What must not be generated is the *time*: the series starts at an
explicit exchange-local instant so it genuinely spans the sessions the service
is meant to find.
"""

from __future__ import annotations

import math

import pytest

from aetheros.trading.domain.enums import (
    DataQualityStatus,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.provenance import DataQuality
from aetheros.trading.errors import InsufficientDataError
from aetheros.trading.ict.sessions import DEFAULT_EXCHANGE_TIMEZONE, SessionCatalogue
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.smc_service import SMCService

from .conftest import local_time, make_market_data, make_ohlc_market_data

H1 = Timeframe.H1

#: 20:00 exchange-local on 14 January -- the Asian session's open, so the series
#: begins exactly on a session boundary.
START = local_time(2026, 1, 14, 20)


def _series(count: int) -> list[float]:
    """A deterministic zig-zag with a gentle upward drift."""
    return [100.0 + i * 0.35 + 3.0 * math.sin(i / 3.0) for i in range(count)]


def _path(
    prices: list[float], *, wick: float = 0.5
) -> list[tuple[float, float, float, float]]:
    """A price path as explicit OHLC: each bar opens at the previous close."""
    bars: list[tuple[float, float, float, float]] = []
    prev = prices[0]
    for price in prices:
        bars.append((prev, max(prev, price) + wick, min(prev, price) - wick, price))
        prev = price
    return bars


def _market_data(**overrides):
    params = {
        "ohlc": _path(_series(52)),
        "timeframe": H1,
        "start": START,
    }
    params.update(overrides)
    return make_ohlc_market_data(**params)


def _stable(analysis) -> dict:
    """The serialised read with the two wall-clock fields removed."""
    payload = analysis.to_dict()
    payload.pop("computed_at", None)
    provenance = dict(payload.get("provenance") or {})
    provenance.pop("retrieved_at", None)
    payload["provenance"] = provenance
    return payload


# ----------------------------------------------------------------------
# The full read
# ----------------------------------------------------------------------


def test_analyze_returns_the_whole_ict_read() -> None:
    analysis = ICTService().analyze(_market_data())

    assert analysis.instrument_key == "TEST"
    assert analysis.timeframe == "1h"
    assert analysis.exchange_timezone == DEFAULT_EXCHANGE_TIMEZONE
    assert analysis.last_price == pytest.approx(_series(52)[-1])

    # 52 hourly bars from 20:00 span three exchange-local days and seven
    # session occurrences (three Asian, two London, two New York), so there is
    # a completed prior day to read a bias from and sessions to measure.
    assert len(analysis.sessions) == 7
    assert analysis.daily_bias is not None
    assert analysis.daily_bias.prior_day_date.isoformat() == "2026-01-15"
    assert analysis.kill_zones
    assert analysis.liquidity_pools
    assert analysis.session_models
    assert analysis.provenance is not None
    assert analysis.provenance.tier is SourceTier.DERIVED


def test_the_sessions_are_the_ones_the_candles_actually_fell_into() -> None:
    analysis = ICTService().analyze(_market_data())

    for window in analysis.sessions:
        assert window.candle_count >= 1
        assert window.low <= window.open <= window.high
        assert window.low <= window.close <= window.high

    starts = [window.start_at for window in analysis.sessions]
    assert starts == sorted(starts)
    # The first bars open the Asian session at the series' own start instant.
    assert starts[0] == START


def test_kill_zone_measurements_are_bounded_and_traceable() -> None:
    analysis = ICTService().analyze(_market_data())

    for zone in analysis.kill_zones:
        assert 0.0 <= zone.range_share <= 1.0
        assert zone.candle_count >= 1
        assert zone.first_index <= zone.last_index
        assert zone.evidence  # a measurement is never reported without its reason


def test_a_read_is_reproducible() -> None:
    service = ICTService()
    data = _market_data()
    assert _stable(service.analyze(data)) == _stable(service.analyze(data))


def test_to_dict_serialises_the_detections_and_the_derived_views() -> None:
    payload = ICTService().analyze(_market_data()).to_dict()

    assert payload["instrument_key"] == "TEST"
    assert payload["daily_bias"]["concept"] == "daily_bias"
    assert payload["sessions"]
    assert payload["kill_zones"]
    assert payload["liquidity_pools"] is not None
    # The pool views are exposed, and they partition the pools they come from.
    assert len(payload["resting_pools"]) + len(payload["taken_pools"]) == len(
        payload["liquidity_pools"]
    )
    assert payload["provenance"]["tier"] == SourceTier.DERIVED.value


# ----------------------------------------------------------------------
# Honest labelling of the inputs
# ----------------------------------------------------------------------


def test_mock_data_is_labelled_and_still_analysed() -> None:
    analysis = ICTService().analyze(_market_data(tier=SourceTier.MOCK))

    assert analysis.provenance is not None
    assert analysis.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in limitation for limitation in analysis.limitations)
    # The tier is a caveat, not a reason to stop describing the market.
    assert analysis.sessions
    assert analysis.kill_zones


def test_degraded_quality_is_recorded_as_a_limitation() -> None:
    analysis = ICTService().analyze(
        _market_data(
            quality=DataQuality(
                status=DataQualityStatus.INVALID,
                issues=("the last bar has a high below its low",),
                freshness_seconds=0.0,
            )
        )
    )

    assert any("invalid" in limitation for limitation in analysis.limitations)


def test_session_models_compare_each_session_with_its_predecessor() -> None:
    analysis = ICTService().analyze(_market_data())

    # One model per session after the first, in order, each naming the session
    # it was measured against.
    assert len(analysis.session_models) == len(analysis.sessions) - 1
    for model, (previous, window) in zip(
        analysis.session_models,
        zip(analysis.sessions, analysis.sessions[1:], strict=False),
        strict=False,
    ):
        assert model.session is window.session
        assert model.previous_session is previous.session
        assert model.timestamp == window.end_at
        assert model.evidence


def test_a_window_with_no_session_is_reported_honestly() -> None:
    """
    17:00-19:45 exchange-local belongs to no session in the default table, so
    the time-based concepts cannot be evaluated. The read says so -- once per
    concept that could not run -- instead of inventing a session or forcing a
    pattern, and the single exchange-local day leaves no prior day for a bias.
    """
    data = make_ohlc_market_data(
        _path(_series(12)),
        timeframe=Timeframe.M15,
        start=local_time(2026, 1, 15, 17),
    )
    analysis = ICTService(smc=SMCService(min_bars=5), min_bars=12).analyze(data)

    assert analysis.sessions == ()
    assert analysis.daily_bias is None
    assert analysis.judas_swings == ()
    assert analysis.power_of_three == ()
    assert analysis.session_models == ()

    joined = " ".join(analysis.limitations)
    for reason in (
        "No session occurrence",
        "two exchange-local days",
        "No bars fell inside these kill zones",
        "a Judas swing needs a prior session",
        "no session-to-session relationship to model",
    ):
        assert reason in joined, f"expected the read to state: {reason}"


# ----------------------------------------------------------------------
# Configuration and refusal
# ----------------------------------------------------------------------


def test_thin_series_raises_insufficient_data() -> None:
    data = make_market_data([100.0 + i for i in range(10)], timeframe=Timeframe.D1)
    with pytest.raises(InsufficientDataError):
        ICTService().analyze(data)


def test_the_exchange_timezone_is_configurable() -> None:
    tokyo = SessionCatalogue(timezone="Asia/Tokyo")
    service = ICTService(session_catalogue=tokyo)

    assert service.catalogue is tokyo
    assert service.analyze(_market_data()).exchange_timezone == "Asia/Tokyo"


def test_invalid_arguments_are_rejected() -> None:
    with pytest.raises(ValueError, match="OTE ratios"):
        ICTService(ote_low_ratio=0.9, ote_high_ratio=0.8)
    with pytest.raises(ValueError, match="displacement_body_multiple"):
        ICTService(displacement_body_multiple=0.0)
    with pytest.raises(ValueError, match="opening_window_minutes"):
        ICTService(opening_window_minutes=0)
    with pytest.raises(ValueError, match="accumulation_max_share"):
        ICTService(accumulation_max_share=1.0)
    with pytest.raises(ValueError, match="min_bars"):
        ICTService(min_bars=4)
