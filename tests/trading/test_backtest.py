"""
BacktestService: deterministic, look-ahead-safe walk-forward evaluation.

Every metric here is a fixed calculation from the candle series and the signal's
calls -- never a probability and never an LLM guess (spec sections 6, 7). The
central guarantee, pinned by ``test_no_lookahead``, is that the signal only ever
sees bars up to and including the bar it predicts from; the realised forward
return the engine scores against is never shown to it (spec section 21). A
backtest on synthetic MOCK data is never reliable, however good the numbers
(spec section 61).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    Direction,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.events import BacktestCompleted
from aetheros.trading.services.backtest_service import BacktestService

_BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _series(
    closes,
    *,
    tier: SourceTier = SourceTier.PRIMARY,
    status: DataQualityStatus = DataQualityStatus.OK,
) -> MarketData:
    """Build a valid OHLCV series from a list of closes for exact math."""
    candles = []
    prev = closes[0]
    for i, close in enumerate(closes):
        open_ = prev
        hi = max(open_, close) * 1.001
        lo = min(open_, close) * 0.999
        candles.append(
            Candle(
                timestamp=_BASE + timedelta(days=i),
                open=open_,
                high=hi,
                low=lo,
                close=close,
                volume=1_000_000.0,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse("TEST"),
        timeframe=Timeframe.D1,
        candles=tuple(candles),
        provenance=Provenance(source="test", tier=tier, detail="backtest fixture"),
        quality=DataQuality(status=status, issues=(), freshness_seconds=0.0),
    )


# closes crafted so the 1-bar-ahead outcome is known: UP at t=1,4,5,6; DOWN at 2,3.
_CLOSES = [10.0, 11.0, 12.0, 11.0, 10.0, 11.0, 12.0, 13.0]


async def _always_up(_window: MarketData) -> Direction:
    return Direction.UP


async def _always_down(_window: MarketData) -> Direction:
    return Direction.DOWN


def _svc(event_bus: EventBus | None = None) -> BacktestService:
    return BacktestService(get_settings(), event_bus=event_bus)


def _stable(result) -> dict:
    d = result.to_dict()
    d.pop("created_at", None)
    prov = dict(d.get("provenance") or {})
    prov.pop("retrieved_at", None)
    d["provenance"] = prov
    return d


@pytest.mark.asyncio
async def test_always_up_scorecard():
    data = _series(_CLOSES)
    r = await _svc().run(data, _always_up, horizon=1, warmup=1, min_sample=1)

    # t in [1..6] -> 6 predictions; realised UP at 1,4,5,6 (4), DOWN at 2,3 (2).
    assert r.evaluated == 6
    assert r.directional_calls == 6
    assert r.hits == 4
    assert r.directional_accuracy == pytest.approx(4 / 6)
    assert r.up_calls == 6
    assert r.up_hits == 4
    assert r.coverage == pytest.approx(1.0)
    assert r.base_rate_up == pytest.approx(4 / 6)
    assert r.cumulative_return > 0  # net-up series, always-long -> positive
    assert r.is_reliable is True


@pytest.mark.asyncio
async def test_short_signal_mirrors():
    data = _series(_CLOSES)
    r = await _svc().run(data, _always_down, horizon=1, warmup=1, min_sample=1)

    assert r.down_calls == 6
    assert r.down_hits == 2  # correct only where the move was down (t=2,3)
    assert r.directional_accuracy == pytest.approx(2 / 6)
    assert r.cumulative_return < 0  # shorting a net-up series loses


@pytest.mark.asyncio
async def test_no_lookahead():
    """The signal must only ever see bars up to the bar it predicts from."""
    data = _series(_CLOSES)
    seen: list[tuple[int, datetime]] = []

    async def _spy(window: MarketData) -> Direction:
        seen.append((window.count, window.candles[-1].timestamp))
        return Direction.UP

    await _svc().run(data, _spy, horizon=1, warmup=1, min_sample=1)

    # Call k predicts from bar t=1+k: it must see exactly t+1 bars, last == bar t.
    for k, (count, last_ts) in enumerate(seen):
        t = 1 + k
        assert count == t + 1
        assert last_ts == data.candles[t].timestamp
    # The signal never reaches the final `horizon` bars used only for scoring.
    max_index_seen = max(count - 1 for count, _ in seen)
    assert max_index_seen == len(_CLOSES) - 1 - 1  # n - horizon - 1


@pytest.mark.asyncio
async def test_mock_data_is_never_reliable():
    data = _series(_CLOSES, tier=SourceTier.MOCK)
    r = await _svc().run(data, _always_up, horizon=1, warmup=1, min_sample=1)

    assert r.directional_accuracy == pytest.approx(4 / 6)  # math still computed
    assert r.is_reliable is False  # but synthetic data proves no edge
    assert r.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in r.limitations)


@pytest.mark.asyncio
async def test_thin_sample_not_reliable():
    data = _series(_CLOSES)
    r = await _svc().run(data, _always_up, horizon=1, warmup=1, min_sample=100)
    assert r.is_reliable is False
    assert any("sample too small" in lim for lim in r.limitations)


@pytest.mark.asyncio
async def test_insufficient_bars_yields_empty():
    data = _series([10.0, 11.0, 12.0])
    r = await _svc().run(data, _always_up, horizon=1, warmup=5)
    assert r.evaluated == 0
    assert r.directional_accuracy is None
    assert r.is_reliable is False
    assert any("Not enough" in lim for lim in r.limitations)


@pytest.mark.asyncio
async def test_sideways_calls_reduce_coverage():
    data = _series(_CLOSES)

    async def _sometimes(window: MarketData) -> Direction:
        # No directional call on even-length windows.
        return Direction.SIDEWAYS if window.count % 2 == 0 else Direction.UP

    r = await _svc().run(data, _sometimes, horizon=1, warmup=1, min_sample=1)
    # UP only at t=2,4,6 (odd counts 3,5,7); the other three are SIDEWAYS.
    assert r.evaluated == 6
    assert r.directional_calls == 3
    assert r.coverage == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_deterministic():
    data = _series(_CLOSES)
    a = await _svc().run(data, _always_up, horizon=1, warmup=1, min_sample=1)
    b = await _svc().run(data, _always_up, horizon=1, warmup=1, min_sample=1)
    assert _stable(a) == _stable(b)


@pytest.mark.asyncio
async def test_publishes_backtest_completed():
    received: list[BacktestCompleted] = []
    bus = EventBus()
    await bus.subscribe(BacktestCompleted, lambda e: received.append(e))

    data = _series(_CLOSES)
    r = await _svc(bus).run(data, _always_up, horizon=1, warmup=1, min_sample=1)

    assert len(received) == 1
    assert received[0].evaluated == r.evaluated
    assert received[0].directional_accuracy == r.directional_accuracy
    assert received[0].is_reliable == r.is_reliable
