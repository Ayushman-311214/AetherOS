"""
Backtest value objects.

A :class:`BacktestResult` is the deterministic product of a walk-forward
evaluation: at each historical bar a signal is computed from *only* the bars up
to and including that bar, and its call is scored against the realised forward
return ``horizon`` bars later. Nothing here is fitted, guessed, or produced by
an LLM -- it is honest, reproducible measurement (spec sections 6, 7, 21).

Crucially, a backtest on synthetic (MOCK) data proves nothing about a real
market edge, so such a result carries ``is_reliable = False`` no matter how good
the numbers look. The metrics here are for a *categorical* directional signal
(accuracy vs. an empirical base rate, plus trade-return statistics); calibrated
probabilistic metrics (Brier score, ROC-AUC, expected calibration error) belong
to the later probability layer and are deliberately absent, not silently faked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Direction
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    """One walk-forward prediction scored against its realised forward return."""

    index: int
    timestamp: datetime
    predicted: Direction
    entry_price: float
    exit_price: float
    forward_return: float
    realized: Direction
    correct: bool | None  # None when the prediction had no directional call

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "predicted": self.predicted.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "forward_return": self.forward_return,
            "realized": self.realized.value,
            "correct": self.correct,
        }


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Deterministic, reproducible walk-forward evaluation of a signal."""

    instrument: Instrument
    timeframe: str
    horizon: int
    warmup: int

    total_bars: int
    evaluated: int  # bars with a resolvable forward window

    directional_calls: int  # UP/DOWN predictions among the evaluated bars
    hits: int
    directional_accuracy: float | None

    up_calls: int
    up_hits: int
    up_accuracy: float | None
    down_calls: int
    down_hits: int
    down_accuracy: float | None

    coverage: float | None  # directional_calls / evaluated
    base_rate_up: float | None  # empirical P(forward move up) -- the naive baseline

    avg_return_per_trade: float | None  # signed per directional call
    cumulative_return: float | None  # additive equity curve of signed returns
    max_drawdown: float | None
    sharpe: float | None  # per-trade mean/std, NOT annualised

    quality: DataQuality
    provenance: Provenance
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    sample: tuple[TradeOutcome, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "warmup": self.warmup,
            "total_bars": self.total_bars,
            "evaluated": self.evaluated,
            "directional_calls": self.directional_calls,
            "hits": self.hits,
            "directional_accuracy": self.directional_accuracy,
            "up_calls": self.up_calls,
            "up_hits": self.up_hits,
            "up_accuracy": self.up_accuracy,
            "down_calls": self.down_calls,
            "down_hits": self.down_hits,
            "down_accuracy": self.down_accuracy,
            "coverage": self.coverage,
            "base_rate_up": self.base_rate_up,
            "avg_return_per_trade": self.avg_return_per_trade,
            "cumulative_return": self.cumulative_return,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "sample": [o.to_dict() for o in self.sample],
            "created_at": self.created_at.isoformat(),
        }
