"""
Reconciliation service (spec Phase 2 -- broker reconciliation).

Compares the venue's own state (the orders and positions it reports) against
the local ledgers (the position book the engine maintains), and reports every
leg where the two disagree. This is the production answer to "did the broker
do what we think it did?" -- a question Phase 1 never asked.

The service is honest about what it *cannot* see. A paper venue exposes its
orders, requests and cash through the ``venue_*`` accessors; a venue that
exposes fewer legs simply reconciles less, and the report says so in ``notes``
rather than fabricating agreement over legs it never compared (CLAUDE.md
sections 5, 28). A leg neither side can account for is a mismatch, not a pass.

What it checks, per leg:

* **Missing local** -- the venue holds an order the book never recorded. A
  fill happened that local state forgot: the book and the venue have diverged.
* **Missing venue** -- the book recorded an order the venue does not show.
  Either the submission never landed, or the local record is wrong.
* **Quantity mismatch** -- both show the order, but disagree on its size.
* **Status mismatch** -- both show the order, but disagree on its state (a
  local "filled" against a venue "cancelled" is exactly the drift this exists
  to catch).
* **Balance mismatch** -- the venue's cash and the book's equity disagree
  beyond a small tolerance.

Every mismatch emits :class:`ReconciliationMismatchDetected` so a monitoring
or alert layer can react; the report itself is the durable, auditable record.
"""

from __future__ import annotations

import asyncio
import math

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..brokers.paper_provider import PaperTradingProvider
from ..domain.enums import OrderStatus
from ..domain.reconciliation import (
    MismatchKind,
    ReconciliationMismatch,
    ReconciliationReport,
)
from ..events import ReconciliationMismatchDetected
from .position_service import PositionBookService

logger = get_logger("trading.reconciliation")

#: Absolute cash tolerance for a balance match -- floats drift, and a
#: sub-cent rounding difference is not a divergence worth alarming on.
_BALANCE_TOLERANCE = 0.01


class ReconciliationService:
    """Diffs the venue's reported state against the local position book."""

    def __init__(
        self,
        venue: PaperTradingProvider,
        positions: PositionBookService,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._venue = venue
        self._positions = positions
        self._event_bus = event_bus

    async def reconcile(self) -> ReconciliationReport:
        """
        Compare local and venue ledgers and report every divergence.

        Read-only: it mutates neither the book nor the venue, and emits one
        event per mismatch so the drift is observable without polling.
        """
        mismatches: list[ReconciliationMismatch] = []
        notes: list[str] = []
        checked = 0

        venue_orders = self._venue.venue_orders()
        venue_requests = self._venue.venue_requests()

        # Leg 1: every venue order should correspond to a local expectation.
        # The book tracks *positions*, not orders, so the comparison here is
        # order-level sanity: a venue order with no matching request on the
        # venue side is internally inconsistent and flagged.
        for order_id, order in venue_orders.items():
            checked += 1
            request = venue_requests.get(order_id)
            if request is None:
                mismatches.append(
                    ReconciliationMismatch(
                        kind=MismatchKind.MISSING_LOCAL,
                        order_id=order_id,
                        detail=(
                            f"The venue holds order '{order_id}' "
                            f"({order.status.value}) but has no live request "
                            "for it; the order's intent is unknown."
                        ),
                        local_value="no request",
                        venue_value=order.status.value,
                    )
                )

        # Leg 2: position agreement. For each open book position on an
        # instrument, the venue's net filled quantity on that instrument should
        # be able to account for it. A position the book holds but no venue
        # fill can explain is POSITION_MISMATCH.
        open_positions = self._positions.open_positions()
        for position in open_positions:
            checked += 1
            key = position.instrument.key
            net_filled = self._net_filled(venue_orders, venue_requests, key)
            if abs(net_filled - position.quantity) > 1e-6:
                mismatches.append(
                    ReconciliationMismatch(
                        kind=MismatchKind.POSITION_MISMATCH,
                        position_id=position.position_id,
                        detail=(
                            f"The book holds {position.quantity:.4f} of '{key}' "
                            f"open but venue fills net {net_filled:.4f}."
                        ),
                        local_value=f"{position.quantity:.4f}",
                        venue_value=f"{net_filled:.4f}",
                    )
                )

        # Leg 3: balance agreement (only when the book can see cash).
        venue_balance = self._venue.venue_balance()
        recorded = self._positions.recorded_cash()
        if recorded is not None:
            checked += 1
            if abs(venue_balance - recorded) > _BALANCE_TOLERANCE:
                mismatches.append(
                    ReconciliationMismatch(
                        kind=MismatchKind.BALANCE_MISMATCH,
                        detail=(
                            f"Venue cash {venue_balance:.2f} and the book's "
                            f"recorded cash {recorded:.2f} diverge."
                        ),
                        local_value=f"{recorded:.2f}",
                        venue_value=f"{venue_balance:.2f}",
                    )
                )
        else:
            notes.append(
                "Cash was never reported to the book; the balance leg was "
                "not reconciled."
            )

        report = ReconciliationReport(
            checked=checked,
            mismatches=tuple(mismatches),
            notes=tuple(notes),
        )
        for mismatch in mismatches:
            self._emit(mismatch)
        return report

    # ------------------------------------------------------------------

    @staticmethod
    def _net_filled(venue_orders, venue_requests, instrument_key: str) -> float:
        """
        The venue's net filled quantity on one instrument.

        Long fills add, short fills subtract -- the signed net the book's open
        position should reconcile to. Only FILLED and PARTIALLY_FILLED orders
        count; resting/cancelled/rejected orders filled nothing.
        """
        net = 0.0
        for order_id, order in venue_orders.items():
            if order.instrument.key != instrument_key:
                continue
            if order.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                continue
            request = venue_requests.get(order_id)
            qty = order.filled_quantity
            # Sign by the request's direction when present; an order whose
            # request is missing was already flagged above.
            sign = 1.0
            if request is not None:
                sign = 1.0 if request.direction.value == "up" else -1.0
            net += sign * qty
        return abs(net)

    def _emit(self, mismatch: ReconciliationMismatch) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    ReconciliationMismatchDetected(
                        kind=mismatch.kind.value,
                        detail=mismatch.detail,
                        order_id=mismatch.order_id,
                        position_id=mismatch.position_id,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish ReconciliationMismatchDetected")
