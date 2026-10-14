"""Trading analytics value objects (spec Phase 22)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..domain.backtest import TradeStatistics


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DimensionBreakdown:
    """One slice of performance (a strategy, a symbol, a timeframe, a month)."""

    dimension: str  # "strategy" | "symbol" | "timeframe" | "month"
    key: str
    trades: int
    wins: int
    losses: int
    win_rate: float | None
    net_pnl: float
    average_rr: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "key": self.key,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "net_pnl": self.net_pnl,
            "average_rr": self.average_rr,
        }


@dataclass(frozen=True, slots=True)
class JournalAnalytics:
    """
    Performance measured from actual journal entries (spec Phase 22).

    Win rate, profit factor, expectancy, Sharpe and drawdown are the shared
    :class:`TradeStatistics` computed over per-trade net P/L -- the same
    arithmetic the backtest path uses, so replayed and live books reconcile.
    Average R:R is the mean of the entries' *planned* risk/reward ratios (the
    geometry the trade was given), reported separately from what the trade
    actually made: a 1:3 plan that lost is still a 1:3 plan. Monthly return is
    summed net P/L bucketed by the entry's recorded month.

    ``is_reliable`` is False with explicit limitations whenever the sample is
    thin, mock, or missing the fields a metric needs (open entries never
    enter P/L maths; entries without a planned ratio never enter average R:R).
    """

    trades: int
    closed_trades: int
    open_trades: int
    statistics: TradeStatistics | None
    average_rr: float | None
    average_rr_sample: int
    monthly_return: tuple[tuple[str, float], ...]
    breakdowns: tuple[DimensionBreakdown, ...]
    mock_trades: int
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trades": self.trades,
            "closed_trades": self.closed_trades,
            "open_trades": self.open_trades,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "average_rr": self.average_rr,
            "average_rr_sample": self.average_rr_sample,
            "monthly_return": [
                {"month": month, "net_pnl": pnl}
                for month, pnl in self.monthly_return
            ],
            "breakdowns": [b.to_dict() for b in self.breakdowns],
            "mock_trades": self.mock_trades,
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }
