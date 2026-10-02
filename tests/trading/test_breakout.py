"""
BreakoutService: deterministic channel-breakout detection.

The channel/volume maths is pinned on crafted candle series (no network): a
monotonic riser breaks out above its prior channel, a faller breaks down, and a
range-bound tape sits inside. The honesty contract is pinned too (CLAUDE.md
sections 5, 28): mock data is never reliable, too-thin data is UNKNOWN with no
fabricated numbers, and an inside-channel close is a determinate reliable "no
breakout" read.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    DataQualityStatus,
    Direction,
    EvidenceType,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.services.breakout_service import BreakoutService

from .conftest import make_market_data

_RISING = [100.0 + i * 1.0 for i in range(60)]
_FALLING = [200.0 - i * 1.0 for i in range(60)]
_RANGE = [100.0 + (3.0 if i % 2 else -3.0) for i in range(60)]


def _service() -> BreakoutService:
    return BreakoutService(get_settings())


def _with_last_volume(
    closes: list[float], last_volume: float, *, base_volume: float = 1_000_000.0
) -> MarketData:
    """Build PRIMARY MarketData with a controllable final-bar volume."""
    end = datetime.now(timezone.utc).replace(microsecond=0)
    step = timedelta(seconds=Timeframe.D1.seconds)
    n = len(closes)
    candles: list[Candle] = []
    prev = closes[0]
    for i, close in enumerate(closes):
        open_ = prev
        vol = last_volume if i == n - 1 else base_volume
        candles.append(
            Candle(
                timestamp=end - step * (n - 1 - i),
                open=open_,
                high=max(open_, close) + 0.5,
                low=min(open_, close) - 0.5,
                close=close,
                volume=vol,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse("BRK"),
        timeframe=Timeframe.D1,
        candles=tuple(candles),
        provenance=Provenance(source="test", tier=SourceTier.PRIMARY, detail="synthetic"),
        quality=DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
    )


def test_rising_series_breaks_out_up():
    a = _service().analyze(make_market_data(_RISING, symbol="UP"))
    assert a.direction is Direction.UP
    assert a.has_breakout is True
    assert a.is_reliable is True
    assert a.last_close > a.channel_high
    assert a.evidence is not None
    assert a.evidence.type is EvidenceType.MARKET_STRUCTURE
    assert a.evidence.assertion is Assertion.DETECTED
    assert a.evidence.direction is Direction.UP


def test_falling_series_breaks_down():
    a = _service().analyze(make_market_data(_FALLING, symbol="DN"))
    assert a.direction is Direction.DOWN
    assert a.has_breakout is True
    assert a.last_close < a.channel_low


def test_range_bound_series_has_no_breakout():
    a = _service().analyze(make_market_data(_RANGE, symbol="RNG"))
    assert a.direction is Direction.SIDEWAYS
    assert a.has_breakout is False
    assert a.is_reliable is True  # a determinate "no breakout" is reliable
    assert a.evidence is None


def test_volume_confirmation_flag():
    # A rising breakout with a big final-bar volume is volume-confirmed; with a
    # tiny one it is not. Same price path, so only volume differs.
    confirmed = _service().analyze(_with_last_volume(_RISING, 5_000_000.0))
    unconfirmed = _service().analyze(_with_last_volume(_RISING, 100_000.0))
    assert confirmed.direction is Direction.UP
    assert confirmed.volume_confirmed is True
    assert unconfirmed.volume_confirmed is False
    # Confirmation never lowers the weight.
    assert confirmed.evidence.weight >= unconfirmed.evidence.weight


def test_mock_data_is_never_reliable():
    a = _service().analyze(make_market_data(_RISING, symbol="MK", tier=SourceTier.MOCK))
    assert a.is_reliable is False
    assert any("MOCK" in lim for lim in a.limitations)


def test_thin_data_is_unknown_not_fabricated():
    a = _service().analyze(make_market_data([100.0 + i for i in range(10)], symbol="THIN"))
    assert a.direction is Direction.UNKNOWN
    assert a.is_reliable is False
    assert a.has_breakout is False
    assert a.channel_high is None
    assert a.evidence is None


def test_is_deterministic():
    md = make_market_data(_RISING, symbol="UP")
    a = _service().analyze(md).to_dict()
    b = _service().analyze(md).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
