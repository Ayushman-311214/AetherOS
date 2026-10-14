"""
Shared builders for trading tests.

These construct MarketData with *controlled* shapes (a clean uptrend, a
downtrend, a stale series) so the structure/technical/evidence tests assert
against known behaviour rather than the mock provider's random walk. All data
here is clearly synthetic and used only for deterministic assertions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from aetheros.trading.backtesting.metrics import trade_statistics
from aetheros.trading.domain.backtest import BacktestResult
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData, Quote
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.providers.base import MarketDataProvider


def _provenance(tier: SourceTier = SourceTier.PRIMARY) -> Provenance:
    return Provenance(source="test", tier=tier, detail="synthetic test fixture")


def make_market_data(
    closes: list[float],
    *,
    symbol: str = "TEST",
    timeframe: Timeframe = Timeframe.D1,
    tier: SourceTier = SourceTier.PRIMARY,
    end: datetime | None = None,
    quality: DataQuality | None = None,
    volume: float = 1_000_000.0,
) -> MarketData:
    """Build a MarketData from a close series with plausible OHLC/volume."""
    end = end or datetime.now(timezone.utc).replace(microsecond=0)
    step = timedelta(seconds=timeframe.seconds)
    n = len(closes)
    candles: list[Candle] = []
    prev = closes[0]
    for i, close in enumerate(closes):
        open_ = prev
        hi = max(open_, close) + 0.5
        lo = min(open_, close) - 0.5
        ts = end - step * (n - 1 - i)
        candles.append(
            Candle(
                timestamp=ts,
                open=open_,
                high=hi,
                low=lo,
                close=close,
                volume=volume,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse(symbol),
        timeframe=timeframe,
        candles=tuple(candles),
        provenance=_provenance(tier),
        quality=quality
        or DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
    )


def make_ohlc_market_data(
    ohlc: list[tuple[float, float, float, float]],
    *,
    symbol: str = "TEST",
    timeframe: Timeframe = Timeframe.D1,
    tier: SourceTier = SourceTier.PRIMARY,
    volume: float = 1_000_000.0,
    end: datetime | None = None,
    start: datetime | None = None,
    quality: DataQuality | None = None,
) -> MarketData:
    """
    Build a MarketData from explicit ``(open, high, low, close)`` bars.

    ``make_market_data`` synthesizes a fixed +-0.5 wick around a close series,
    which is fine for indicator maths but cannot express the precise wicks and
    closes that structure/SMC detection turns on (a sweep needs a wick beyond a
    level *with* a close back inside it). This helper hands over the OHLC
    verbatim so those cases can be written as exact, known-answer fixtures.

    Timestamps run *backwards* from ``end`` (the default) unless ``start`` is
    given, in which case bar ``i`` lands at ``start + i * interval`` and the
    series runs *forwards*. The session/time layer keys off wall-clock time, so
    ICT tests need bars placed at chosen instants -- most simply by passing a
    ``start`` already aligned to the session they mean to fill.
    """
    step = timedelta(seconds=timeframe.seconds)
    n = len(ohlc)
    if start is not None:
        timestamps = [start + step * i for i in range(n)]
    else:
        end = end or datetime.now(timezone.utc).replace(microsecond=0)
        timestamps = [end - step * (n - 1 - i) for i in range(n)]
    candles = tuple(
        Candle(
            timestamp=timestamp,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        for timestamp, (open_, high, low, close) in zip(timestamps, ohlc)
    )
    return MarketData(
        instrument=Instrument.parse(symbol),
        timeframe=timeframe,
        candles=candles,
        provenance=_provenance(tier),
        quality=quality
        or DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
    )


def make_backtest_result(
    returns: tuple[float, ...] = (),
    *,
    symbol: str = "TEST",
    timeframe: Timeframe = Timeframe.D1,
    horizon: int = 1,
    warmup: int = 0,
    calls: int | None = None,
    hits: int | None = None,
    evaluated: int = 20,
    base_rate_up: float | None = 0.5,
    reliable: bool = True,
    tier: SourceTier = SourceTier.DERIVED,
) -> BacktestResult:
    """
    A BacktestResult built around a set of signed trade returns.

    The walk-forward and comparison tests care about what a result *says*, not
    how it was produced -- they exercise the aggregation and ranking rules, and
    running a real backtest to feed them would make every one of those tests a
    slow integration test. The counts are derived from ``returns`` the same way
    the backtester derives them, so a fixture cannot quietly disagree with the
    engine about what a hit is.
    """
    statistics = trade_statistics(list(returns)) if returns else None
    directional = len(returns) if calls is None else calls
    hit_count = sum(1 for r in returns if r > 0) if hits is None else hits
    accuracy = round(hit_count / directional, 6) if directional else None
    return BacktestResult(
        instrument=Instrument.parse(symbol),
        timeframe=timeframe.value,
        horizon=horizon,
        warmup=warmup,
        total_bars=evaluated + warmup + horizon,
        evaluated=evaluated,
        directional_calls=directional,
        hits=hit_count,
        directional_accuracy=accuracy,
        up_calls=directional,
        up_hits=hit_count,
        up_accuracy=accuracy,
        down_calls=0,
        down_hits=0,
        down_accuracy=None,
        coverage=1.0 if evaluated else None,
        base_rate_up=base_rate_up,
        avg_return_per_trade=statistics.expectancy if statistics else None,
        cumulative_return=statistics.cumulative_return if statistics else None,
        max_drawdown=statistics.max_drawdown if statistics else None,
        sharpe=statistics.sharpe if statistics else None,
        quality=DataQuality(
            status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0
        ),
        provenance=_provenance(tier),
        is_reliable=reliable,
        statistics=statistics,
        returns=returns,
    )


def local_time(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    *,
    tz: str = "America/New_York",
) -> datetime:
    """An instant named in exchange-local wall-clock time.

    Session tests are written in the exchange's own clock ("08:30 New York"),
    not UTC, so this converts once at the edge and the test body reads in the
    timezone the rules are actually defined in. Daylight saving is resolved
    from the zone database, which is what makes the January/July tests differ.
    """
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))


@pytest.fixture
def uptrend_data() -> MarketData:
    # Steadily rising series with mild noise, enough bars for every indicator.
    closes = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
    return make_market_data(closes, symbol="UP")


@pytest.fixture
def downtrend_data() -> MarketData:
    closes = [200.0 - i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
    return make_market_data(closes, symbol="DOWN")


@pytest.fixture
def flat_data() -> MarketData:
    closes = [100.0 + (0.2 if i % 2 else -0.2) for i in range(120)]
    return make_market_data(closes, symbol="FLAT")


def make_invalid_market_data(*, symbol: str = "BAD") -> MarketData:
    """A series whose last candle carries structurally impossible OHLC.

    The Candle constructor rejects invalid bars outright, so the quality-
    assessment path (which must downgrade a broken series rather than crash)
    is exercised by bypassing the constructor for this one fixture candle.
    """
    data = make_market_data([100.0 + i for i in range(30)], symbol=symbol)
    bad = data.candles[-1]
    # Bypass __post_init__ validation for the fixture: a frozen slots dataclass
    # still allows object-level construction via __new__ + manual field binding.
    object.__setattr__  # noqa: B018 - document intent; helper below does the work
    broken = Candle.__new__(Candle)
    for name, value in (
        ("timestamp", bad.timestamp),
        ("open", bad.open),
        ("high", 1.0),  # high below low -> INVALID
        ("low", 100.0),
        ("close", bad.close),
        ("volume", bad.volume),
    ):
        object.__setattr__(broken, name, value)
    return MarketData(
        instrument=data.instrument,
        timeframe=data.timeframe,
        candles=data.candles[:-1] + (broken,),
        provenance=data.provenance,
        quality=data.quality,
    )


class FakeProvider(MarketDataProvider):
    """
    A controllable, clearly-synthetic provider for service tests.

    Unlike the mock provider it is stamped PRIMARY so quality-assessment tests
    are not dominated by the mock penalty; it simply hands back whatever
    MarketData/Quote the test built and counts how often it was called (so
    cache behaviour is observable).
    """

    name = "fake"
    tier = SourceTier.PRIMARY

    def __init__(self, data: MarketData, *, quote: Quote | None = None) -> None:
        self._data = data
        self._quote = quote
        self.candle_calls = 0
        self.quote_calls = 0

    async def get_candles(self, instrument, timeframe, *, limit) -> MarketData:
        self.candle_calls += 1
        return self._data

    async def get_quote(self, instrument) -> Quote:
        self.quote_calls += 1
        if self._quote is None:
            raise NotImplementedError("FakeProvider was not given a quote.")
        return self._quote
