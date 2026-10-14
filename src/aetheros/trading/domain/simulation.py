"""
Simulation-layer value objects (spec Phase 14, paper trading).

A simulation answers one question -- "what would this strategy have done to a
virtual account over this history?" -- and these objects are its answer. They
are deliberately *not* performance claims: the report carries the same
``is_reliable`` gate and ``limitations`` list the walk-forward report does,
because a simulated run is evidence about the engine that played it, and only
conditionally evidence about an edge.

Two boundaries are drawn here:

**A simulated trade is not a recommendation.** It records what a rule set did
under a stated fill model; the fill model is named in the report's
``assumptions`` rather than left implicit, since §7 forbids unrealistic
transaction assumptions passing silently.

**A reliable report cannot carry limitations.** ``is_reliable`` and a non-empty
``limitations`` are made contradictory by the model itself: if there is a
caveat, the run is not trustworthy, and allowing both would let a caller
report a flawed run as clean.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .backtest import TradeStatistics
from .enums import Direction
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SimulationExitReason(str, Enum):
    """
    Why a simulated position closed.

    ``AMBIGUOUS`` is the honest one: the bar's range contained both the stop
    and the target, so the true order of events inside the bar is unknowable
    from daily data. Such a trade is closed at the *stop* -- see
    :mod:`aetheros.trading.simulation.exit_rules` -- and labelled, rather than
    quietly resolved in whichever direction flatters the result.
    """

    TARGET = "target"
    STOP = "stop"
    AMBIGUOUS = "ambiguous"
    FORCED_END = "forced_end"


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    """
    One round trip taken by the simulation, with its costs kept apart.

    ``realized_pnl`` is the gross result the :class:`Position` model defines
    (``(exit - entry) * quantity`` signed by side) and ``commission_paid`` is
    what the round trip cost, so the two are never conflated: ``net_pnl`` is
    their difference and is what the account actually gained. Reporting only
    the net figure would hide the cost; reporting only the gross one would
    overstate the result.
    """

    position_id: str
    instrument_key: str
    direction: Direction
    quantity: float
    entry_price: float
    entry_bar: int
    exit_price: float
    exit_bar: int
    reason: SimulationExitReason
    realized_pnl: float
    commission_paid: float

    def __post_init__(self) -> None:
        if not self.position_id.strip():
            raise ValueError("A simulated trade requires a position id.")
        if not self.instrument_key.strip():
            raise ValueError("A simulated trade requires an instrument.")
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError("A simulated trade must be long or short.")
        if not math.isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError("A simulated trade's quantity must be positive.")
        for label, value in (
            ("entry_price", self.entry_price),
            ("exit_price", self.exit_price),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"A simulated trade's {label} must be positive.")
        if self.entry_bar < 0 or self.exit_bar < 0:
            raise ValueError("A simulated trade's bar indices cannot be negative.")
        if self.exit_bar <= self.entry_bar:
            raise ValueError(
                "A simulated trade must exit after the bar that opened it: a "
                "position cannot be resolved on the bar that created it."
            )
        if not math.isfinite(self.realized_pnl):
            raise ValueError("A simulated trade's P&L must be finite.")
        if not math.isfinite(self.commission_paid) or self.commission_paid < 0:
            raise ValueError("A simulated trade's commission cannot be negative.")

    @property
    def net_pnl(self) -> float:
        """What the round trip actually added to the account."""
        return self.realized_pnl - self.commission_paid

    @property
    def notional(self) -> float:
        """The capital the position controlled at entry."""
        return self.quantity * self.entry_price

    @property
    def return_pct(self) -> float:
        """Net P&L as a share of entry notional -- the trade's own return."""
        return self.net_pnl / self.notional if self.notional > 0 else 0.0

    @property
    def forced(self) -> bool:
        """Whether the series ended before the exit rule resolved."""
        return self.reason is SimulationExitReason.FORCED_END

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "instrument_key": self.instrument_key,
            "direction": self.direction.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_bar": self.entry_bar,
            "exit_price": self.exit_price,
            "exit_bar": self.exit_bar,
            "reason": self.reason.value,
            "realized_pnl": self.realized_pnl,
            "commission_paid": self.commission_paid,
            "net_pnl": self.net_pnl,
            "return_pct": self.return_pct,
            "forced": self.forced,
        }


@dataclass(frozen=True, slots=True)
class SimulationReport:
    """
    What a replayed session did to a virtual account.

    The counters are kept separately and on purpose: ``signals_fired`` is what
    the strategy wanted, ``orders_filled`` is what the venue did,
    ``orders_rejected`` is what the §9 gate or the venue refused, and
    ``entries_skipped`` is what the one-position-at-a-time rule suppressed.
    Collapsing them into "trades" would make a run that was mostly refused
    look identical to one that mostly declined to act.

    ``realized_pnl`` is gross and ``commission_paid`` rides alongside, exactly
    as on :class:`SimulatedTrade`, so the summary reconciles without summing
    hundreds of trades by hand: ``realized_pnl - commission_paid`` is what the
    equity actually moved by, and ``total_return`` is that same movement as a
    share of the starting balance.
    """

    instrument: Instrument
    timeframe: str
    strategy_id: str
    bars: int
    warmup: int
    initial_equity: float
    final_equity: float
    realized_pnl: float
    unrealised_pnl: float
    commission_paid: float
    max_drawdown: float
    sharpe: float | None
    statistics: TradeStatistics | None
    trades: tuple[SimulatedTrade, ...]
    equity_curve: tuple[float, ...]
    signals_fired: int
    orders_filled: int
    orders_rejected: int
    admissions_refused: int
    entries_skipped: int
    exit_counts: tuple[tuple[str, int], ...]
    assumptions: tuple[str, ...]
    provenance: Provenance
    quality: DataQuality
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.instrument.key.strip():
            raise ValueError("A simulation report requires an instrument.")
        if not self.timeframe.strip() or not self.strategy_id.strip():
            raise ValueError("A simulation report requires a timeframe and strategy.")
        if self.bars < 1:
            raise ValueError("A simulation report must cover at least one bar.")
        if self.warmup < 0 or self.warmup > self.bars:
            raise ValueError("A simulation report's warmup must lie within its bars.")
        if not math.isfinite(self.initial_equity) or self.initial_equity <= 0:
            raise ValueError("A simulation report's initial equity must be positive.")
        for label, value in (
            ("final_equity", self.final_equity),
            ("realized_pnl", self.realized_pnl),
            ("unrealised_pnl", self.unrealised_pnl),
            ("max_drawdown", self.max_drawdown),
        ):
            if not math.isfinite(value):
                raise ValueError(f"A simulation report's {label} must be finite.")
        if any(not math.isfinite(point) for point in self.equity_curve):
            raise ValueError("A simulation report's equity curve must be finite.")
        if not math.isfinite(self.commission_paid) or self.commission_paid < 0:
            raise ValueError("A simulation report's commission cannot be negative.")
        for label, count in (
            ("signals_fired", self.signals_fired),
            ("orders_filled", self.orders_filled),
            ("orders_rejected", self.orders_rejected),
            ("admissions_refused", self.admissions_refused),
            ("entries_skipped", self.entries_skipped),
        ):
            if count < 0:
                raise ValueError(f"A simulation report's {label} cannot be negative.")
        for trade in self.trades:
            if trade.instrument_key != self.instrument.key:
                raise ValueError(
                    "A simulation report's trades must describe its instrument."
                )
            if trade.exit_bar > self.bars:
                raise ValueError(
                    "A simulation report's trades cannot exit past its last bar."
                )
        if self.is_reliable and self.limitations:
            raise ValueError(
                "A reliable simulation report cannot carry limitations: a caveat "
                "means the run is not trustworthy, and reporting both would let "
                "a flawed run be presented as a clean one."
            )

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def total_return(self) -> float:
        """The account's return over the session, net of costs."""
        return (self.final_equity - self.initial_equity) / self.initial_equity

    @property
    def exit_breakdown(self) -> dict[str, int]:
        """How many positions closed for each reason, including zeroes."""
        counts = dict(self.exit_counts)
        return {
            reason.value: counts.get(reason.value, 0)
            for reason in SimulationExitReason
        }

    @property
    def net_returns(self) -> tuple[float, ...]:
        """The per-trade net returns the metrics were computed from."""
        return tuple(trade.return_pct for trade in self.trades)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "strategy_id": self.strategy_id,
            "bars": self.bars,
            "warmup": self.warmup,
            "initial_equity": self.initial_equity,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "realized_pnl": self.realized_pnl,
            "unrealised_pnl": self.unrealised_pnl,
            "commission_paid": self.commission_paid,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "trade_count": self.trade_count,
            "trades": [trade.to_dict() for trade in self.trades],
            "equity_curve": list(self.equity_curve),
            "signals_fired": self.signals_fired,
            "orders_filled": self.orders_filled,
            "orders_rejected": self.orders_rejected,
            "admissions_refused": self.admissions_refused,
            "entries_skipped": self.entries_skipped,
            "exits": self.exit_breakdown,
            "assumptions": list(self.assumptions),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
