"""
Market-regime detection: deterministic trending / ranging / volatile reads.

These pin the honesty contract of the regime layer (CLAUDE.md sections 5, 8,
22, 28): a clean uptrend/downtrend is TRENDING_UP/DOWN, a flat choppy tape is
RANGING, a wide-swinging tape is VOLATILE, and mock / too-thin data is never
dressed up as a confident regime -- it is UNKNOWN or explicitly not reliable.
The read is deterministic (same candles -> same regime), serialises via
``to_dict``, and emits ``MarketRegimeDetected`` only when a bus is wired.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Confidence,
    Direction,
    MarketRegime,
    SourceTier,
)
from aetheros.trading.domain.regime import RegimeAnalysis
from aetheros.trading.events import MarketRegimeDetected
from aetheros.trading.services.regime_service import RegimeService

from .conftest import make_market_data


def _service(**kwargs) -> RegimeService:
    return RegimeService(get_settings(), **kwargs)


class _FakeBus:
    """Records published events; duck-typed stand-in for the EventBus."""

    def __init__(self) -> None:
        self.published: list = []

    async def publish(self, event) -> None:
        self.published.append(event)


# --------------------------------------------------------------------------- #
# Classification                                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_clean_uptrend_is_trending_up(uptrend_data):
    result = await _service().detect(uptrend_data)

    assert result.regime is MarketRegime.TRENDING_UP
    assert result.direction is Direction.UP
    assert result.is_reliable is True
    assert result.adx is not None and result.adx > 0
    assert result.trend_strength is not None


@pytest.mark.asyncio
async def test_clean_downtrend_is_trending_down(downtrend_data):
    result = await _service().detect(downtrend_data)

    assert result.regime is MarketRegime.TRENDING_DOWN
    assert result.direction is Direction.DOWN
    assert result.is_reliable is True


@pytest.mark.asyncio
async def test_noisy_stationary_tape_is_ranging():
    # Irregular noise around a flat level: no persistent trend (low ADX) and
    # modest range -- the textbook range-bound / choppy regime. (A perfectly
    # regular sawtooth would fool ADX; a real range is noisy, so this fixture
    # uses seeded noise for a deterministic-yet-honest ranging read.)
    import numpy as np

    rng = np.random.default_rng(0)
    closes = (100.0 + rng.normal(0.0, 0.6, size=120)).tolist()
    data = make_market_data(closes, symbol="RANGE")

    result = await _service().detect(data)

    assert result.regime is MarketRegime.RANGING
    assert result.direction is Direction.SIDEWAYS
    assert result.confidence is Confidence.LOW


@pytest.mark.asyncio
async def test_wide_swinging_tape_is_volatile():
    # Alternating ~8% swings: ATR dwarfs the 3% threshold, so the regime is
    # VOLATILE regardless of how the trend maths reads.
    closes = [100.0 + (4.0 if i % 2 else -4.0) for i in range(60)]
    data = make_market_data(closes, symbol="VOL")

    result = await _service().detect(data)

    assert result.regime is MarketRegime.VOLATILE
    assert result.atr_pct is not None and result.atr_pct >= 0.03
    assert result.direction is Direction.UNKNOWN


# --------------------------------------------------------------------------- #
# Honesty: mock and insufficient data                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_mock_data_is_classified_but_never_reliable():
    closes = [100.0 + i * 0.8 for i in range(120)]
    data = make_market_data(closes, symbol="MOCKUP", tier=SourceTier.MOCK)

    result = await _service().detect(data)

    # Machinery still runs on mock data, but the read can never be reliable and
    # the MOCK provenance is surfaced as a limitation, not hidden.
    assert result.is_reliable is False
    assert any("MOCK" in lim for lim in result.limitations)


@pytest.mark.asyncio
async def test_too_thin_series_is_unknown():
    data = make_market_data([100.0 + i for i in range(10)], symbol="THIN")

    result = await _service().detect(data)

    assert result.regime is MarketRegime.UNKNOWN
    assert result.direction is Direction.UNKNOWN
    assert result.is_reliable is False
    assert any("candles" in lim for lim in result.limitations)


@pytest.mark.asyncio
async def test_unknown_regime_carries_no_fabricated_numbers():
    data = make_market_data([100.0, 101.0, 102.0], symbol="TINY")

    result = await _service().detect(data)

    assert result.regime is MarketRegime.UNKNOWN
    assert result.adx is None
    assert result.trend_strength is None
    assert result.atr_pct is None
    assert result.realized_volatility is None


# --------------------------------------------------------------------------- #
# Determinism, serialisation and event emission                               #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_regime_read_is_deterministic(uptrend_data):
    first = await _service().detect(uptrend_data)
    second = await _service().detect(uptrend_data)

    # The classification is a pure function of the candles; only the wall-clock
    # created_at stamp differs between runs.
    a = first.to_dict()
    b = second.to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b


@pytest.mark.asyncio
async def test_to_dict_exposes_the_full_contract(uptrend_data):
    result = await _service().detect(uptrend_data)
    payload = result.to_dict()

    for key in (
        "instrument",
        "timeframe",
        "regime",
        "direction",
        "adx",
        "trend_strength",
        "atr_pct",
        "realized_volatility",
        "confidence",
        "is_reliable",
        "observation",
        "quality",
        "provenance",
        "limitations",
        "created_at",
    ):
        assert key in payload, f"missing contract key: {key}"
    assert payload["regime"] == result.regime.value
    assert payload["is_reliable"] is result.is_reliable


@pytest.mark.asyncio
async def test_detect_emits_event_when_bus_wired(uptrend_data):
    bus = _FakeBus()
    result = await _service(event_bus=bus).detect(uptrend_data)

    assert len(bus.published) == 1
    event = bus.published[0]
    assert isinstance(event, MarketRegimeDetected)
    assert event.regime == result.regime.value
    assert event.instrument_key == result.instrument.key
    assert event.is_reliable is result.is_reliable


@pytest.mark.asyncio
async def test_detect_without_bus_is_a_no_op(uptrend_data):
    # No bus wired: the read is produced exactly the same, nothing emitted.
    result = await _service().detect(uptrend_data)
    assert result.regime is MarketRegime.TRENDING_UP
