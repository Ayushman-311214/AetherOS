"""
Backtest service -- the deterministic walk-forward evaluation engine.

Given a market-data series and a *signal* (any callable that maps a
:class:`MarketData` window to a :class:`Direction`), it walks the series one bar
at a time. At each bar ``t`` it feeds the signal only ``candles[: t + 1]`` -- so
the signal physically cannot see the future -- records the call, then scores it
against the realised return ``horizon`` bars later, which the engine computes
itself from the full series and never shows the signal. This construction is the
guarantee against look-ahead bias the spec demands (sections 7, 21).

The output is a categorical-signal scorecard: directional accuracy against the
empirical up-rate (the naive baseline to beat), coverage, and trade-return
statistics. It is NOT calibrated probability -- Brier/ROC-AUC/ECE need the
probability layer and are intentionally omitted rather than fabricated (section
6). A backtest over synthetic MOCK data is flagged ``is_reliable = False``: it
verifies the machinery, not a real edge (sections 53, 61).
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Union

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.backtest import BacktestResult, TradeOutcome
from ..domain.enums import Direction, SourceTier
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..events import BacktestCompleted

logger = get_logger("trading.backtest")

# A signal maps a data window to a directional call. It may be sync or async so
# the deterministic AnalysisService (async) and trivial test signals both fit.
SignalFn = Callable[[MarketData], Union[Direction, Awaitable[Direction]]]

# How many scored predictions to attach to the result for inspection.
_SAMPLE_CAP = 10


class BacktestService:
    """Deterministic, look-ahead-safe walk-forward backtester."""

    def __init__(
        self,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def run(
        self,
        data: MarketData,
        signal: SignalFn,
        *,
        horizon: int | None = None,
        warmup: int | None = None,
        flat_eps: float = 0.0,
        min_sample: int | None = None,
    ) -> BacktestResult:
        s = self._settings
        h = horizon if horizon is not None else s.TRADING_BACKTEST_HORIZON
        w = warmup if warmup is not None else s.TRADING_BACKTEST_WARMUP
        min_n = min_sample if min_sample is not None else s.TRADING_BACKTEST_MIN_SAMPLE

        result = await self._run(data, signal, h=h, w=w, flat_eps=flat_eps, min_n=min_n)
        await self._emit(result)
        return result

    # ------------------------------------------------------------------

    async def _run(
        self,
        data: MarketData,
        signal: SignalFn,
        *,
        h: int,
        w: int,
        flat_eps: float,
        min_n: int,
    ) -> BacktestResult:
        candles = data.candles
        n = len(candles)
        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Backtest ran on synthetic MOCK data; results verify the engine, "
                "not a real market edge."
            )
        if not data.quality.ok:
            limitations.append(
                f"Data quality is '{data.quality.status.value}': "
                + "; ".join(data.quality.issues)
            )

        provenance = Provenance(
            source=data.provenance.source,
            tier=SourceTier.MOCK if data.provenance.is_mock else SourceTier.DERIVED,
            detail="deterministic walk-forward backtest",
        )

        # The last bar we can score is n-1; the last bar we can *predict from* is
        # therefore n-1-h. Nothing before `warmup` is trusted.
        last_predict = n - h - 1
        if not data.quality.usable or last_predict < w:
            limitations.append(
                f"Not enough usable bars to backtest: need > warmup({w}) + "
                f"horizon({h}), have {n}."
            )
            return self._empty(data, provenance, h, w, n, tuple(limitations))

        outcomes: list[TradeOutcome] = []
        for t in range(w, last_predict + 1):
            entry = candles[t].close
            if entry <= 0:
                continue  # cannot form a return; skip rather than fabricate
            window = self._slice(data, t)
            predicted = await self._call(signal, window)
            exit_price = candles[t + h].close
            fwd = (exit_price - entry) / entry
            realized = self._classify(fwd, flat_eps)
            correct = (
                (predicted is realized)
                if predicted in (Direction.UP, Direction.DOWN)
                else None
            )
            outcomes.append(
                TradeOutcome(
                    index=t,
                    timestamp=candles[t].timestamp,
                    predicted=predicted,
                    entry_price=entry,
                    exit_price=exit_price,
                    forward_return=round(fwd, 8),
                    realized=realized,
                    correct=correct,
                )
            )

        return self._aggregate(
            data, provenance, h, w, n, outcomes, min_n, limitations
        )

    @staticmethod
    def _slice(data: MarketData, t: int) -> MarketData:
        """A window of exactly ``candles[: t + 1]`` -- the past, never the future."""
        return MarketData(
            instrument=data.instrument,
            timeframe=data.timeframe,
            candles=data.candles[: t + 1],
            provenance=data.provenance,
            quality=data.quality,
            retrieved_at=data.retrieved_at,
        )

    @staticmethod
    async def _call(signal: SignalFn, window: MarketData) -> Direction:
        result = signal(window)
        if inspect.isawaitable(result):
            result = await result
        return result

    @staticmethod
    def _classify(fwd: float, flat_eps: float) -> Direction:
        if fwd > flat_eps:
            return Direction.UP
        if fwd < -flat_eps:
            return Direction.DOWN
        return Direction.SIDEWAYS

    def _aggregate(
        self,
        data: MarketData,
        provenance: Provenance,
        h: int,
        w: int,
        n: int,
        outcomes: list[TradeOutcome],
        min_n: int,
        limitations: list[str],
    ) -> BacktestResult:
        evaluated = len(outcomes)
        calls = [o for o in outcomes if o.correct is not None]
        ups = [o for o in calls if o.predicted is Direction.UP]
        downs = [o for o in calls if o.predicted is Direction.DOWN]

        directional_calls = len(calls)
        hits = sum(1 for o in calls if o.correct)
        up_hits = sum(1 for o in ups if o.correct)
        down_hits = sum(1 for o in downs if o.correct)

        realized_up = sum(1 for o in outcomes if o.realized is Direction.UP)

        # Signed per-trade returns: long earns the forward return, short earns
        # its negation. Only directional calls trade.
        signed = [
            o.forward_return if o.predicted is Direction.UP else -o.forward_return
            for o in calls
        ]

        cumulative = round(sum(signed), 8) if signed else None
        avg_return = round(sum(signed) / len(signed), 8) if signed else None
        max_dd = self._max_drawdown(signed) if signed else None
        sharpe = self._sharpe(signed)

        if directional_calls == 0 and evaluated > 0:
            limitations.append(
                "Signal made no directional calls; accuracy is undefined."
            )

        # Honesty gate: mock data is never a reliable edge, and a thin sample is
        # statistically meaningless no matter how the headline number looks.
        is_reliable = (
            data.quality.usable
            and not data.provenance.is_mock
            and directional_calls >= min_n
        )
        if not data.provenance.is_mock and directional_calls < min_n:
            limitations.append(
                f"Only {directional_calls} directional calls (< {min_n}); "
                "sample too small to be reliable."
            )

        sample = tuple(outcomes[:_SAMPLE_CAP])

        return BacktestResult(
            instrument=data.instrument,
            timeframe=data.timeframe.value,
            horizon=h,
            warmup=w,
            total_bars=n,
            evaluated=evaluated,
            directional_calls=directional_calls,
            hits=hits,
            directional_accuracy=self._ratio(hits, directional_calls),
            up_calls=len(ups),
            up_hits=up_hits,
            up_accuracy=self._ratio(up_hits, len(ups)),
            down_calls=len(downs),
            down_hits=down_hits,
            down_accuracy=self._ratio(down_hits, len(downs)),
            coverage=self._ratio(directional_calls, evaluated),
            base_rate_up=self._ratio(realized_up, evaluated),
            avg_return_per_trade=avg_return,
            cumulative_return=cumulative,
            max_drawdown=max_dd,
            sharpe=sharpe,
            quality=data.quality,
            provenance=provenance,
            is_reliable=is_reliable,
            limitations=tuple(limitations),
            sample=sample,
        )

    def _empty(
        self,
        data: MarketData,
        provenance: Provenance,
        h: int,
        w: int,
        n: int,
        limitations: tuple[str, ...],
    ) -> BacktestResult:
        return BacktestResult(
            instrument=data.instrument,
            timeframe=data.timeframe.value,
            horizon=h,
            warmup=w,
            total_bars=n,
            evaluated=0,
            directional_calls=0,
            hits=0,
            directional_accuracy=None,
            up_calls=0,
            up_hits=0,
            up_accuracy=None,
            down_calls=0,
            down_hits=0,
            down_accuracy=None,
            coverage=None,
            base_rate_up=None,
            avg_return_per_trade=None,
            cumulative_return=None,
            max_drawdown=None,
            sharpe=None,
            quality=data.quality,
            provenance=provenance,
            is_reliable=False,
            limitations=limitations,
            sample=(),
        )

    @staticmethod
    def _ratio(num: int, den: int) -> float | None:
        return round(num / den, 6) if den > 0 else None

    @staticmethod
    def _max_drawdown(signed: list[float]) -> float:
        """Largest peak-to-trough drop on the additive equity curve (>= 0)."""
        equity = 0.0
        peak = 0.0
        worst = 0.0
        for r in signed:
            equity += r
            peak = max(peak, equity)
            worst = min(worst, equity - peak)
        return round(-worst, 8)

    @staticmethod
    def _sharpe(signed: list[float]) -> float | None:
        """Per-trade mean/std ratio. Not annualised; None when undefined."""
        if len(signed) < 2:
            return None
        mean = sum(signed) / len(signed)
        var = sum((r - mean) ** 2 for r in signed) / len(signed)
        std = var**0.5
        if std == 0:
            return None
        return round(mean / std, 6)

    async def _emit(self, result: BacktestResult) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                BacktestCompleted(
                    instrument_key=result.instrument.key,
                    timeframe=result.timeframe,
                    horizon=result.horizon,
                    evaluated=result.evaluated,
                    directional_accuracy=result.directional_accuracy,
                    base_rate_up=result.base_rate_up,
                    is_reliable=result.is_reliable,
                    source_tier=result.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish BacktestCompleted")
