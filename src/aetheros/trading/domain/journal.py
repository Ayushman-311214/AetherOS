"""
Trading-journal value objects (spec Phase 21).

A journal entry is the traceable record of one paper trade: what the market
showed, what the pipeline decided, what the venue did, and what resulted. It
invents nothing -- every field is read off the objects the trade already passed
through (the signal, the risk assessment, the simulated round trip, the run's
provenance). The journal describes; it never decides.

Two entry paths cover the full Market Evidence -> ... -> Journal trace:

* :meth:`JournalEntry.from_trade` -- the *exit* side: a settled simulated
  round trip becomes a complete entry (prices, P/L, exit reason verbatim).
* :meth:`JournalEntry.from_request` -- the *entry* side: a validated
  execution request (the §9 record: entry, stop, target, risk/reward,
  strategy, reasoning, evidence) becomes the entry's opening record before
  the outcome is known. P/L fields are ``None`` until the trade closes;
  :meth:`JournalEntry.close` fills them from the exit facts.

Post-trade reflection is a human annotation, never a fabrication:
:meth:`JournalEntry.annotate` returns an annotated copy carrying ``emotion``
and ``lesson``; the service never invents either.

An entry is immutable and JSON-serialisable via ``to_dict()``, like every other
domain object. Persistence (a durable store behind a port) is a later concern;
this phase delivers the record shape and the service that builds it from a
simulation report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import Direction
from .provenance import Provenance
from .simulation import SimulatedTrade, SimulationExitReason


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """
    One paper trade, traced from signal to result.

    ``entry_id`` is content-addressed over the trade's identity (position id +
    instrument + entry/exit bars) so rebuilding a journal from the same report
    dedupes rather than duplicating. ``entry_reason`` / ``exit_reason`` are the
    human-readable judgements the pipeline already recorded (strategy setup
    reasoning, exit-rule label) -- never invented here.
    """

    entry_id: str
    instrument_key: str
    strategy_id: str
    direction: Direction
    quantity: float
    entry_price: float
    entry_bar: int
    exit_price: float | None
    exit_bar: int | None
    exit_reason: SimulationExitReason | None
    realized_pnl: float | None
    commission_paid: float
    net_pnl: float | None
    return_pct: float | None
    entry_reason: str = ""
    timeframe: str = ""
    is_mock: bool = False
    provenance: Provenance | None = None
    # Risk geometry, recorded when known (the §9 record carries it; the
    # simulation replay does not retain it, so replayed entries leave it None
    # rather than reconstructing it).
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_reward_ratio: float | None = None
    # Post-trade human reflection -- set only via annotate(), never invented.
    emotion: str | None = None
    lesson: str | None = None
    # Chart-screenshot metadata captured alongside the trade, if any.
    screenshot: dict[str, Any] | None = None
    # Content ids of the evidence the entry-side decision rested on -- the
    # trace link back to Market Evidence -> Analysis -> Signal. Ids only, so
    # the evidence itself keeps its single source of truth.
    evidence_ids: tuple[str, ...] = ()
    recorded_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def from_trade(
        cls,
        trade: SimulatedTrade,
        *,
        strategy_id: str,
        timeframe: str = "",
        entry_reason: str = "",
        is_mock: bool = False,
        provenance: Provenance | None = None,
    ) -> JournalEntry:
        """Build an entry from a simulated round trip and its run context."""
        seed = "|".join(
            (
                trade.position_id,
                trade.instrument_key,
                str(trade.entry_bar),
                str(trade.exit_bar),
            )
        )
        entry_id = "jrnl_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return cls(
            entry_id=entry_id,
            instrument_key=trade.instrument_key,
            strategy_id=strategy_id,
            direction=trade.direction,
            quantity=trade.quantity,
            entry_price=trade.entry_price,
            entry_bar=trade.entry_bar,
            exit_price=trade.exit_price,
            exit_bar=trade.exit_bar,
            exit_reason=trade.reason,
            realized_pnl=trade.realized_pnl,
            commission_paid=trade.commission_paid,
            net_pnl=trade.net_pnl,
            return_pct=trade.return_pct,
            entry_reason=entry_reason,
            timeframe=timeframe,
            is_mock=is_mock,
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "instrument_key": self.instrument_key,
            "strategy_id": self.strategy_id,
            "direction": self.direction.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_bar": self.entry_bar,
            "exit_price": self.exit_price,
            "exit_bar": self.exit_bar,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "realized_pnl": self.realized_pnl,
            "commission_paid": self.commission_paid,
            "net_pnl": self.net_pnl,
            "return_pct": self.return_pct,
            "entry_reason": self.entry_reason,
            "timeframe": self.timeframe,
            "is_mock": self.is_mock,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "emotion": self.emotion,
            "lesson": self.lesson,
            "screenshot": self.screenshot,
            "evidence_ids": list(self.evidence_ids),
            "recorded_at": self.recorded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JournalEntry:
        """
        Rebuild an entry from its :meth:`to_dict` form (durable read-back).

        The inverse of :meth:`to_dict`; a store serialises with the former and
        reconstructs with this, so a recorded trade round-trips without loss --
        including its content-addressed ``entry_id``, which the store never
        recomputes and this never second-guesses. Enum fields are parsed back
        to their types; a missing optional stays absent rather than defaulting
        to a fabricated value.
        """
        exit_reason = data.get("exit_reason")
        provenance = data.get("provenance")
        recorded_at = data["recorded_at"]
        return cls(
            entry_id=data["entry_id"],
            instrument_key=data["instrument_key"],
            strategy_id=data["strategy_id"],
            direction=Direction(data["direction"]),
            quantity=data["quantity"],
            entry_price=data["entry_price"],
            entry_bar=data["entry_bar"],
            exit_price=data.get("exit_price"),
            exit_bar=data.get("exit_bar"),
            exit_reason=(
                SimulationExitReason(exit_reason) if exit_reason is not None else None
            ),
            realized_pnl=data.get("realized_pnl"),
            commission_paid=data.get("commission_paid", 0.0),
            net_pnl=data.get("net_pnl"),
            return_pct=data.get("return_pct"),
            entry_reason=data.get("entry_reason", ""),
            timeframe=data.get("timeframe", ""),
            is_mock=data.get("is_mock", False),
            provenance=(
                Provenance.from_dict(provenance) if provenance is not None else None
            ),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            risk_reward_ratio=data.get("risk_reward_ratio"),
            emotion=data.get("emotion"),
            lesson=data.get("lesson"),
            screenshot=data.get("screenshot"),
            evidence_ids=tuple(data.get("evidence_ids", ())),
            recorded_at=(
                recorded_at
                if isinstance(recorded_at, datetime)
                else datetime.fromisoformat(recorded_at)
            ),
        )

    @classmethod
    def from_request(
        cls,
        request: Any,
        *,
        entry_bar: int = 0,
        timeframe: str = "",
        is_mock: bool = False,
        provenance: Provenance | None = None,
        screenshot: dict[str, Any] | None = None,
    ) -> JournalEntry:
        """
        Open an entry from a validated execution request (the §9 record).

        This is the entry side of a live paper trade: the pipeline's decision
        context (entry, stop, target, risk/reward, strategy, reasoning) is
        captured before the outcome is known, so the Market Evidence ->
        ... -> Journal trace starts where the decision was made. P/L and exit
        stay ``None`` until :meth:`close` fills them from the exit facts --
        never estimated here.
        """
        seed = "|".join(
            (
                request.signal_id,
                request.instrument.key,
                f"{request.entry:g}",
                str(entry_bar),
            )
        )
        entry_id = "jrnl_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return cls(
            entry_id=entry_id,
            instrument_key=request.instrument.key,
            strategy_id=request.strategy_id,
            direction=request.direction,
            quantity=request.quantity,
            entry_price=request.entry,
            entry_bar=entry_bar,
            exit_price=None,
            exit_bar=None,
            exit_reason=None,
            realized_pnl=None,
            commission_paid=0.0,
            net_pnl=None,
            return_pct=None,
            entry_reason=request.reasoning,
            timeframe=timeframe,
            is_mock=is_mock,
            provenance=provenance,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            risk_reward_ratio=request.risk_reward_ratio,
            screenshot=screenshot,
            evidence_ids=tuple(item.id for item in request.evidence),
        )

    def close(
        self,
        *,
        exit_price: float,
        exit_bar: int,
        exit_reason: SimulationExitReason,
        commission_paid: float = 0.0,
    ) -> JournalEntry:
        """
        Settle an open entry with the exit facts.

        Returns a new entry; the open record is untouched. P/L is derived
        from the two prices and the side exactly as the position model
        defines it, minus commission -- the same arithmetic the simulation
        settles with, so replayed and live closes reconcile.
        """
        import dataclasses

        if self.exit_price is not None:
            raise ValueError("This journal entry is already closed.")
        if exit_bar <= self.entry_bar:
            raise ValueError("A trade must exit after the bar that opened it.")
        signed = exit_price - self.entry_price
        if self.direction is Direction.DOWN:
            signed = -signed
        realized = signed * self.quantity
        net = realized - commission_paid
        basis = self.entry_price * self.quantity
        return_pct = (net / basis * 100.0) if basis > 0 else 0.0
        return dataclasses.replace(
            self,
            exit_price=exit_price,
            exit_bar=exit_bar,
            exit_reason=exit_reason,
            realized_pnl=realized,
            commission_paid=commission_paid,
            net_pnl=net,
            return_pct=return_pct,
        )

    def annotate(
        self, *, emotion: str | None = None, lesson: str | None = None
    ) -> JournalEntry:
        """
        Attach post-trade human reflection to an entry.

        Returns a new entry; the record is untouched. Empty strings are
        treated as absent -- an unannotated entry says nothing rather than
        recording a blank lesson.
        """
        import dataclasses

        return dataclasses.replace(
            self,
            emotion=(emotion.strip() or None) if emotion is not None else self.emotion,
            lesson=(lesson.strip() or None) if lesson is not None else self.lesson,
        )
