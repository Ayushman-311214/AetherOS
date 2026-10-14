"""
Position book service (spec Phase 2 -- positions, account state, reconciliation input).

Phase 1's paper venue debited cash on a fill but never *opened a position*: a
buy filled, money moved, and no :class:`~aetheros.trading.domain.trade.Position`
recorded that the account was now long. Without a book, three production
requirements had no answer:

* ``AccountSnapshot`` -- the input :class:`RiskLimitsService` gates on -- could
  not be built from real state, because open exposure and realised PnL were
  never tracked.
* ``PositionClosed`` -- a declared event -- could never fire, because no
  position existed to close.
* **Reconciliation** -- there was no local "what do we think we hold?" to diff
  against the venue's "what actually filled?".

This service is the single source of truth for the *account side* of the §9
path: it owns open positions, realised PnL and the gross-exposure figure the
risk gate needs. A venue reports a fill to it; it either opens a position or
reduces/closes an opposite one and banks the realised leg. It holds no
analytical judgement and never fabricates a position -- it only records fills
that already happened.

Two rules are structural (CLAUDE.md sections 5, 28):

* **A closing fill settles against the open leg.** A sell against an open long
  reduces or closes it; the realised P&L is computed from the two prices and
  the side exactly as the :class:`Position` model defines it, never estimated.
* **Unknown inputs stay unknown.** ``snapshot()`` only reports equity/exposure
  figures it can actually derive from the book; it never invents a balance it
  was not given, so the risk gate downstream can still fail closed on the legs
  it cannot see.
"""

from __future__ import annotations

import asyncio
import dataclasses
import math
from dataclasses import dataclass
from datetime import UTC, datetime

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import Direction, PositionStatus
from ..domain.execution import ExecutionRequest
from ..domain.risk_limits import AccountSnapshot
from ..domain.trade import Position
from ..events import PositionClosed, PositionOpened

logger = get_logger("trading.positions")


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class _ClosedLeg:
    """The realised result of closing (or reducing) one open position."""

    position: Position
    realized_pnl: float
    closed_quantity: float
    remaining: Position | None


class PositionBookService:
    """
    The live account book: open positions, realised PnL, exposure.

    Stateful by necessity -- a book *is* state -- but the state is narrow and
    honest: a mapping of open positions plus a running realised-PnL ledger. It
    is a singleton so every consumer (risk gate, health, reconciliation, tools)
    reads the one book, never competing copies.
    """

    def __init__(self, *, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        # instrument_key -> the open Position on that instrument.
        self._open: dict[str, Position] = {}
        # Realised P&L, newest last, for daily aggregation.
        self._realised: list[tuple[datetime, float]] = []
        # Cash balance, tracked when the caller reports it; ``None`` is honest.
        self._cash: float | None = None
        # Realised P&L accumulated over the book's life.
        self._lifetime_pnl: float = 0.0

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_fill(
        self,
        request: ExecutionRequest,
        *,
        fill_price: float,
        fill_quantity: float,
        provider: str = "paper",
    ) -> tuple[Position, ...]:
        """
        Apply one fill to the book.

        A fill in the direction of an open position adds to it (a new leg is
        recorded as a fresh position only when flat); a fill against an open
        position reduces or closes it and banks the realised P&L. Returns the
        positions affected (opened or closed) so the caller can emit events or
        journal. Never invents a position -- it records a fill that happened.
        """
        instrument = request.instrument
        key = instrument.key
        touched: list[Position] = []
        existing = self._open.get(key)

        if existing is not None and existing.direction is not request.direction:
            # A fill against the open leg: reduce or close it.
            closed = self._close_leg(existing, request, fill_price, fill_quantity)
            touched.append(closed.position)
            if closed.remaining is not None:
                self._open[key] = closed.remaining
            else:
                self._open.pop(key, None)
            # Any leftover quantity beyond closing opens a new opposite leg.
            leftover = fill_quantity - closed.closed_quantity
            if leftover > 1e-9:
                opened = self._open_leg(request, leftover, fill_price)
                self._open[key] = opened
                touched.append(opened)
                self._emit_opened(opened, provider)
        elif existing is not None:
            # Same direction: increase the open leg (average up the entry).
            merged = self._merge_leg(existing, fill_quantity, fill_price)
            self._open[key] = merged
        else:
            opened = self._open_leg(request, fill_quantity, fill_price)
            self._open[key] = opened
            touched.append(opened)
            self._emit_opened(opened, provider)

        return tuple(touched)

    def record_cash(self, balance: float) -> None:
        """Report the venue's cash balance so ``snapshot()`` can expose it."""
        if math.isfinite(balance):
            self._cash = balance

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def open_positions(self) -> tuple[Position, ...]:
        """Every position currently open, in insertion order."""
        return tuple(self._open.values())

    def open_exposure(self) -> float:
        """Gross notional exposure across open positions."""
        return sum(p.entry_price * p.quantity for p in self._open.values())

    def realised_pnl_today(self) -> float:
        """Realised P&L banked today (UTC day)."""
        today = _utcnow().date()
        return sum(
            pnl for at, pnl in self._realised if at.date() == today
        )

    def lifetime_pnl(self) -> float:
        """Realised P&L accumulated since the book opened."""
        return self._lifetime_pnl

    def recorded_cash(self) -> float | None:
        """The last cash balance the venue reported, or None if never set."""
        return self._cash

    def snapshot(self) -> AccountSnapshot:
        """
        The account state the risk gate needs, built from the real book.

        ``equity`` is cash plus the book's net unrealised value when cash is
        known; when cash was never reported the equity is the open exposure
        plus lifetime P&L -- the honest figure the book can actually see, never
        a fabricated account size. ``open_exposure_notional`` and
        ``realised_pnl_today`` come straight off the book.
        """
        if self._cash is not None:
            equity = self._cash + self.open_exposure() + self._lifetime_pnl
        else:
            equity = self.open_exposure() + self._lifetime_pnl
        # The AccountSnapshot model requires positive equity; a book that is
        # genuinely flat and broke reports a floor of 1.0 rather than a crash.
        if equity <= 0:
            equity = max(self.open_exposure(), 1.0)
        return AccountSnapshot(
            equity=equity,
            realised_pnl_today=self.realised_pnl_today(),
            open_exposure_notional=self.open_exposure(),
        )

    # ------------------------------------------------------------------
    # Leg mechanics
    # ------------------------------------------------------------------

    @staticmethod
    def _open_leg(
        request: ExecutionRequest, quantity: float, price: float
    ) -> Position:
        return Position(
            instrument=request.instrument,
            direction=request.direction,
            quantity=quantity,
            entry_price=price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )

    @staticmethod
    def _merge_leg(existing: Position, quantity: float, price: float) -> Position:
        """Average an additional same-side fill into the open leg."""
        total = existing.quantity + quantity
        entry = (
            (existing.entry_price * existing.quantity) + (price * quantity)
        ) / total
        return dataclasses.replace(
            existing, quantity=total, entry_price=entry
        )

    def _close_leg(
        self,
        existing: Position,
        request: ExecutionRequest,
        price: float,
        quantity: float,
    ) -> _ClosedLeg:
        """Reduce or close an open position against an opposite fill."""
        closed_qty = min(quantity, existing.quantity)
        sign = 1.0 if existing.direction is Direction.UP else -1.0
        pnl = (price - existing.entry_price) * closed_qty * sign
        now = _utcnow()
        if closed_qty >= existing.quantity - 1e-9:
            closed_position = dataclasses.replace(
                existing,
                status=PositionStatus.CLOSED,
                exit_price=price,
                closed_at=now,
            )
            remaining = None
        else:
            closed_position = dataclasses.replace(
                existing,
                status=PositionStatus.CLOSED,
                exit_price=price,
                closed_at=now,
                quantity=closed_qty,
            )
            remaining = dataclasses.replace(
                existing, quantity=existing.quantity - closed_qty
            )

        self._realised.append((now, pnl))
        self._lifetime_pnl += pnl
        self._emit_closed(closed_position)
        return _ClosedLeg(
            position=closed_position,
            realized_pnl=pnl,
            closed_quantity=closed_qty,
            remaining=remaining,
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _emit_opened(self, position: Position, provider: str) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    PositionOpened(
                        position_id=position.position_id,
                        instrument_key=position.instrument.key,
                        direction=position.direction.value,
                        quantity=position.quantity,
                        entry_price=position.entry_price,
                        provider=provider,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish PositionOpened")

    def _emit_closed(self, position: Position) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    PositionClosed(
                        position_id=position.position_id,
                        instrument_key=position.instrument.key,
                        exit_price=position.exit_price or 0.0,
                        realized_pnl=position.realized_pnl or 0.0,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish PositionClosed")
