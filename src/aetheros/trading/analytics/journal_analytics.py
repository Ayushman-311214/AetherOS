"""
Journal analytics service (spec Phase 22).

Measures trading performance from actual journal entries -- the records a
paper trade already produced (Phase 21). It computes nothing about the market:
it reads the net P/L, planned risk/reward and recorded month each entry
already carries, and aggregates them with the shared
:func:`~aetheros.trading.backtesting.metrics.trade_statistics` arithmetic so a
journal book and a backtest book report the same numbers from the same inputs.

Honesty rules, all structural (CLAUDE.md sections 6, 22, 28):

* **Only closed entries have a result.** An open entry (``exit_price is None``)
  carries no P/L, so it never enters win rate, profit factor, Sharpe or the
  monthly buckets -- it is counted and reported, never graded.
* **Planned R:R is reported separately from realised P/L.** Average R:R is the
  mean of the *planned* ratios the trades were given; an entry without one
  (a replayed trade, which does not retain geometry) is excluded from that
  mean and the exclusion is counted, not hidden.
* **A thin or mock book is not a track record.** Fewer than
  ``TRADING_PERF_MIN_SAMPLE`` closed trades, or any mock entry, yields
  ``is_reliable = False`` with an explicit limitation. An empty book is a
  valid summary, never an error.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from ...config.settings import Settings
from ...core.logging import get_logger
from ..backtesting.metrics import trade_statistics
from ..domain.journal import JournalEntry
from .performance import DimensionBreakdown, JournalAnalytics

logger = get_logger("trading.analytics")

_RR_PLACES = 4
_PNL_PLACES = 6


def _mean(values: Sequence[float], places: int) -> float | None:
    return round(sum(values) / len(values), places) if values else None


class JournalAnalyticsService:
    """Deterministic aggregator of journal entries. Pure, stateless."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summarize(self, entries: Sequence[JournalEntry]) -> JournalAnalytics:
        """
        Aggregate ``entries`` into an auditable :class:`JournalAnalytics`.

        A ``None`` sequence is a programming error and raises via ``len``; an
        empty or thin book is not -- it yields a valid summary flagged not
        reliable, because "not enough trades yet" is the honest answer.
        """
        total = len(entries)
        closed = [e for e in entries if e.exit_price is not None]
        open_entries = total - len(closed)
        mock_trades = sum(1 for e in entries if e.is_mock)

        limitations: list[str] = []

        # Win rate / profit factor / Sharpe / drawdown over realised net P/L.
        net_returns = [e.net_pnl for e in closed if e.net_pnl is not None]
        statistics = trade_statistics(net_returns) if net_returns else None

        # Average *planned* risk/reward, over the entries that carried one.
        planned_rr = [
            e.risk_reward_ratio for e in entries if e.risk_reward_ratio is not None
        ]
        average_rr = _mean(planned_rr, _RR_PLACES)
        if len(planned_rr) < total:
            missing = total - len(planned_rr)
            limitations.append(
                f"{missing} of {total} entr{'y' if total == 1 else 'ies'} carried "
                "no planned risk/reward and are excluded from average R:R."
            )

        monthly_return = self._monthly_return(closed)
        breakdowns = self._breakdowns(closed)

        if open_entries:
            limitations.append(
                f"{open_entries} open entr"
                f"{'y' if open_entries == 1 else 'ies'} carry no result and "
                "are excluded from all P/L metrics."
            )

        min_sample = self._settings.TRADING_PERF_MIN_SAMPLE
        is_reliable = True
        if mock_trades:
            is_reliable = False
            limitations.append(
                f"{mock_trades} entr{'y' if mock_trades == 1 else 'ies'} were "
                "recorded on mock data; this is not a real track record."
            )
        if len(closed) < min_sample:
            is_reliable = False
            limitations.append(
                f"Only {len(closed)} closed trade(s); at least {min_sample} are "
                "needed before performance is treated as reliable."
            )

        return JournalAnalytics(
            trades=total,
            closed_trades=len(closed),
            open_trades=open_entries,
            statistics=statistics,
            average_rr=average_rr,
            average_rr_sample=len(planned_rr),
            monthly_return=monthly_return,
            breakdowns=breakdowns,
            mock_trades=mock_trades,
            is_reliable=is_reliable,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    def _monthly_return(
        self, closed: Sequence[JournalEntry]
    ) -> tuple[tuple[str, float], ...]:
        """Summed net P/L per calendar month the entry was recorded in."""
        buckets: dict[str, float] = defaultdict(float)
        for entry in closed:
            if entry.net_pnl is None:
                continue
            month = entry.recorded_at.strftime("%Y-%m")
            buckets[month] += entry.net_pnl
        return tuple(
            (month, round(buckets[month], _PNL_PLACES)) for month in sorted(buckets)
        )

    def _breakdowns(
        self, closed: Sequence[JournalEntry]
    ) -> tuple[DimensionBreakdown, ...]:
        """
        Performance sliced by strategy, symbol and timeframe.

        Market and broker dimensions the spec also names are not carried on a
        journal entry today; slicing by a field that is not recorded would
        fabricate a breakdown, so only the dimensions the record actually
        holds are produced.
        """
        result: list[DimensionBreakdown] = []
        for dimension, getter in (
            ("strategy", lambda e: e.strategy_id),
            ("symbol", lambda e: e.instrument_key),
            ("timeframe", lambda e: e.timeframe or "unknown"),
        ):
            groups: dict[str, list[JournalEntry]] = defaultdict(list)
            for entry in closed:
                groups[getter(entry)].append(entry)
            for key in sorted(groups):
                result.append(self._slice(dimension, key, groups[key]))
        return tuple(result)

    def _slice(
        self, dimension: str, key: str, members: Sequence[JournalEntry]
    ) -> DimensionBreakdown:
        pnls = [e.net_pnl for e in members if e.net_pnl is not None]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        net_pnl = round(sum(pnls), _PNL_PLACES)
        win_rate = round(wins / len(pnls), _RR_PLACES) if pnls else None
        planned_rr = [
            e.risk_reward_ratio for e in members if e.risk_reward_ratio is not None
        ]
        return DimensionBreakdown(
            dimension=dimension,
            key=key,
            trades=len(members),
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            net_pnl=net_pnl,
            average_rr=_mean(planned_rr, _RR_PLACES),
        )
