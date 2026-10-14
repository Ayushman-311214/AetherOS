"""
Paper trading (spec Phase 9 broker layer).

Paper trading is REAL MARKET DATA + VIRTUAL MONEY (spec §10): this provider
fills orders at *live market prices* -- read through the same
:class:`MarketDataService` the analysis pipeline uses -- against a virtual
account balance it tracks in memory. It never fabricates a price and never
touches a real venue.

The virtual account is deliberately small and honest:

- equity starts from a configurable initial balance and moves only by
  realised fills (a position-manager layer will close positions against
  prices later; this phase records the fills);
- every request is validated against the §9 record *again* at the broker
  (side/geometry invariants), because the boundary between engine and venue
  is exactly where a malformed order must be caught;
- a fill is recorded as an :class:`Order` with ``FILLED`` status and its
  price, so the paper trail is the same shape a live venue would return.

**Order types.** A MARKET order fills on arrival at the live price. A LIMIT,
STOP or STOP_LIMIT order rests until its trigger is met, and the trigger is
evaluated against the live price -- at submission, and again whenever the
order is polled or modified, exactly as a real venue fills a resting order
between polls. An untriggered order is reported as ``SUBMITTED`` with no
fill: a venue that filled it anyway would be inventing a trade.

The trigger rules are fixed and direction-aware (a BUY limit rests *below*
the market, a BUY stop *above* it, and so on); the fill price is the trigger
price or the market price, whichever is better for the order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

from ...core.logging import get_logger
from ..domain.enums import Direction, OrderStatus, OrderType, SourceTier
from ..domain.execution import ExecutionRequest, ExecutionResult
from ..domain.trade import Order
from .base import BrokerProvider
from .price_source import LiveCandlePriceSource, PriceSource

if TYPE_CHECKING:
    # Only used for the ``market_data`` annotation; importing it at runtime
    # pulls in ``services/__init__`` which re-imports this module (a cycle).
    # The instance is only ever passed to ``LiveCandlePriceSource``.
    from ..services.market_data_service import MarketDataService
    # The position book the venue reports fills to; imported lazily to avoid
    # the same services/ cycle ``market_data`` already dodges.
    from ..production.position_service import PositionBookService

logger = get_logger("trading.brokers.paper")

#: Starting virtual balance, in account currency units.
DEFAULT_INITIAL_BALANCE = 100_000.0


def _new_order_id() -> str:
    """A venue-assigned order id, matching the Order model's own convention."""
    return str(uuid4())


@dataclass(slots=True)
class _PaperAccount:
    """The virtual account: balance, executed orders and their live requests."""

    balance: float
    orders: dict[str, Order] = field(default_factory=dict)
    requests: dict[str, ExecutionRequest] = field(default_factory=dict)
    # Client-order-id -> broker order-id: the idempotency ledger. A repeated
    # submission under one key resolves to the order already placed, so a
    # retried or re-issued request can never double-fill (spec Phase 2).
    idempotency: dict[str, str] = field(default_factory=dict)

    def equity(self) -> float:
        """Cash balance (positions are recorded, not yet marked to market)."""
        return self.balance


class PaperTradingProvider(BrokerProvider):
    """
    Fills fully-specified requests at live market prices with virtual money.
    """

    name = "paper"
    tier = SourceTier.MOCK  # virtual money; prices are live via the feed

    def __init__(
        self,
        market_data: MarketDataService | None = None,
        *,
        initial_balance: float = DEFAULT_INITIAL_BALANCE,
        price_source: PriceSource | None = None,
        positions: PositionBookService | None = None,
    ) -> None:
        if not math.isfinite(initial_balance) or initial_balance <= 0:
            raise ValueError("The initial paper balance must be positive.")
        # The default is the live tape -- exactly the behaviour this venue had
        # before the seam existed. A simulation injects a replay-backed source
        # instead, so the *same venue* can fill a replayed bar without any
        # change to its order handling, cash accounting or §9 re-validation.
        if price_source is None:
            if market_data is None:
                raise ValueError(
                    "A paper venue needs either market data or a price source."
                )
            price_source = LiveCandlePriceSource(market_data)
        self._price_source = price_source
        # The position book is optional: a standalone venue (unit tests, a
        # bare replay) keeps the pre-book behaviour when none is injected, so
        # wiring stays additive and nothing is forced to track positions it did
        # not ask for. When wired, fills are reported so positions/AccountSnapshot
        # exist. The book is seeded with the starting balance so ``snapshot()``
        # can report an equity the venue genuinely starts with.
        self._positions = positions
        if self._positions is not None:
            self._positions.record_cash(initial_balance)
        self._account = _PaperAccount(balance=initial_balance)

    @property
    def balance(self) -> float:
        """The virtual cash balance right now."""
        return self._account.balance

    @property
    def order_count(self) -> int:
        """How many orders the venue has accepted (resting or filled)."""
        return len(self._account.orders)

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        # §9 geometry, re-validated at the venue boundary: a malformed
        # request is rejected here, whatever the layers above did.
        rejection = self._geometry_problem(request)
        if rejection is not None:
            return self._reject(request, rejection)

        # Idempotent submission (spec Phase 2): a request that arrives under a
        # client-order-id the venue has already seen resolves to the order it
        # placed, never a second fill. This is what makes the engine's retry
        # safe -- a retried transport fault cannot double-execute the order.
        prior = self._account.idempotency.get(request.idempotency_key)
        if prior is not None:
            existing = self._account.orders.get(prior)
            if existing is not None:
                return self._report(
                    existing,
                    "Idempotent replay: the client-order-id was already "
                    "submitted; returning the order it placed.",
                )

        # A price outage is a venue outage: the request is neither filled nor
        # rejected, it failed to reach the market. BrokerError propagates so the
        # execution engine's retry policy can decide what to do about it.
        price = await self._fill_price(request.instrument.key)

        trigger = self._trigger_price(request, price)
        if trigger is None:
            return self._rest(request, price)

        order = self._open_order(request, status=OrderStatus.SUBMITTED)
        self._account.orders[order.order_id] = order
        self._account.requests[order.order_id] = request
        self._account.idempotency[request.idempotency_key] = order.order_id
        return await self._settle(order, trigger)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def cancel(self, order_id: str) -> ExecutionResult:
        order = self._account.orders.get(order_id)
        if order is None:
            return self._unknown(order_id, "cancel")
        if order.status is OrderStatus.FILLED:
            return self._report(
                order, "The order is already filled; there is nothing to cancel."
            )
        if order.status is OrderStatus.CANCELLED:
            return self._report(order, "The order was already cancelled.")
        cancelled = self._replace_status(order, OrderStatus.CANCELLED, fill=None)
        self._account.orders[order_id] = cancelled
        logger.info("Paper cancel: %s", order_id)
        return self._report(cancelled, "Cancelled at the venue's request.")

    async def modify(
        self, order_id: str, request: ExecutionRequest
    ) -> ExecutionResult:
        order = self._account.orders.get(order_id)
        if order is None:
            return self._unknown(order_id, "modify")
        if order.status is not OrderStatus.SUBMITTED:
            return self._report(
                order,
                "The order is no longer live, so its terms cannot be modified.",
            )
        rejection = self._geometry_problem(request)
        if rejection is not None:
            return self._reject(request, rejection)

        # The terms are replaced in place: same identity, new trigger. A real
        # venue then executes a modified order that is already marketable.
        updated = self._open_order(
            request, status=OrderStatus.SUBMITTED, order_id=order_id
        )
        self._account.orders[order_id] = updated
        self._account.requests[order_id] = request

        price = await self._fill_price(request.instrument.key)
        trigger = self._trigger_price(request, price)
        if trigger is None:
            return self._rest(request, price, order_id=order_id)
        # The amended order was replaced in place, so a rejection here must not
        # discard it -- it stays live with its (unaffordable) new terms.
        return await self._settle(updated, trigger, discard_on_reject=False)

    async def status(self, order_id: str) -> ExecutionResult:
        order = self._account.orders.get(order_id)
        if order is None:
            return self._unknown(order_id, "status")
        if order.status is not OrderStatus.SUBMITTED:
            return self._report(order, "The order's current state.")

        # A resting order is re-tested against the live market, because that is
        # how a resting order does -- or does not -- become a fill.
        request = self._account.requests[order_id]
        price = await self._fill_price(request.instrument.key)
        trigger = self._trigger_price(request, price)
        if trigger is None:
            return self._report(order, "Still resting; the trigger is not met.")
        return await self._settle(order, trigger)

    async def fill_price(self, instrument_key: str) -> float:
        return await self._fill_price(instrument_key)

    async def account_equity(self) -> float:
        return self._account.equity()

    # ------------------------------------------------------------------
    # Reconciliation reads (spec Phase 2)
    # ------------------------------------------------------------------

    def venue_orders(self) -> dict[str, Order]:
        """A read view of the orders the venue is tracking, by broker order id."""
        return dict(self._account.orders)

    def venue_requests(self) -> dict[str, ExecutionRequest]:
        """The live request behind each tracked order, by broker order id."""
        return dict(self._account.requests)

    def venue_balance(self) -> float:
        """The venue's own cash figure, for balance reconciliation."""
        return self._account.balance

    # ------------------------------------------------------------------
    # Order-type semantics
    # ------------------------------------------------------------------

    @staticmethod
    def _trigger_price(request: ExecutionRequest, price: float) -> float | None:
        """
        The price an order would fill at right now, or None if it must rest.

        Fixed, direction-aware rules:

        - **BUY limit** fills at or below its limit; **SELL limit** at or above.
        - **BUY stop** fills at or above its stop; **SELL stop** at or below.
        - **Stop-limit** needs both legs met, and fills at the limit (the
          conservative price: the stop armed it, the limit caps it).
        - The fill price is the trigger price or the market price, whichever is
          better for the order, so a paper fill never prices worse than a real
          one would.
        """
        otype = request.order_type
        if otype is OrderType.MARKET:
            return price
        if otype is OrderType.LIMIT:
            assert request.limit_price is not None
            if request.direction is Direction.UP and price <= request.limit_price:
                return min(price, request.limit_price)
            if request.direction is Direction.DOWN and price >= request.limit_price:
                return max(price, request.limit_price)
            return None
        if otype is OrderType.STOP:
            assert request.stop_price is not None
            if request.direction is Direction.UP and price >= request.stop_price:
                return max(price, request.stop_price)
            if request.direction is Direction.DOWN and price <= request.stop_price:
                return min(price, request.stop_price)
            return None
        # STOP_LIMIT -- the stop arms it, the limit caps it, and it then
        # behaves exactly like the limit order it has become.
        assert request.limit_price is not None and request.stop_price is not None
        if request.direction is Direction.UP:
            armed = price >= request.stop_price
            acceptable = price <= request.limit_price
            return price if armed and acceptable else None
        armed = price <= request.stop_price
        acceptable = price >= request.limit_price
        return price if armed and acceptable else None

    @staticmethod
    def _geometry_problem(request: ExecutionRequest) -> str | None:
        """The §9 side/geometry invariants, re-checked at the venue boundary."""
        if request.direction is Direction.UP and request.stop_loss >= request.entry:
            return "Long stop must sit below entry."
        if request.direction is Direction.DOWN and request.stop_loss <= request.entry:
            return "Short stop must sit above entry."
        if request.direction is Direction.UP and request.take_profit <= request.entry:
            return "Long target must sit above entry."
        if request.direction is Direction.DOWN and request.take_profit >= request.entry:
            return "Short target must sit below entry."
        return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _open_order(
        request: ExecutionRequest,
        *,
        status: OrderStatus,
        order_id: str | None = None,
    ) -> Order:
        return Order(
            instrument=request.instrument,
            direction=request.direction,
            quantity=request.quantity,
            order_type=request.order_type,
            status=status,
            order_id=order_id or _new_order_id(),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )

    async def _settle(
        self, order: Order, price: float, *, discard_on_reject: bool = True
    ) -> ExecutionResult:
        """Fill a triggered order, or reject it if the virtual money runs out."""
        request = self._account.requests[order.order_id]
        cost = price * order.quantity
        if cost > self._account.balance:
            # Not a transport fault: the account cannot cover it. The venue
            # says so, and the order does not rest pending a miracle.
            if discard_on_reject:
                self._account.orders.pop(order.order_id, None)
                self._account.requests.pop(order.order_id, None)
            return self._reject(
                request,
                f"Virtual balance {self._account.balance:.2f} cannot cover "
                f"{order.quantity:.4f} at {price:.4f} ({cost:.2f}).",
            )

        filled = self._replace_status(
            order, OrderStatus.FILLED, fill=(order.quantity, price)
        )
        self._account.orders[order.order_id] = filled
        self._account.balance -= cost
        # Report the fill to the position book so an open/close is recorded and
        # the account snapshot reflects it. Reporting is a side effect on the
        # wired book; with no book wired the venue behaves exactly as before.
        if self._positions is not None:
            self._positions.record_fill(
                request,
                fill_price=price,
                fill_quantity=filled.quantity,
                provider=self.name,
            )
            self._positions.record_cash(self._account.balance)
        logger.info(
            "Paper fill: %s %s %.4f %s @ %.4f",
            filled.order_id,
            request.direction.value,
            filled.quantity,
            request.instrument.key,
            price,
        )
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.FILLED,
            reason=f"Filled at the live market price {price:.4f}.",
            order_id=filled.order_id,
            filled_quantity=filled.quantity,
            average_fill_price=price,
        )

    @staticmethod
    def _replace_status(
        order: Order,
        status: OrderStatus,
        *,
        fill: tuple[float, float] | None,
    ) -> Order:
        """Rebuild an order in a new lifecycle state (the model is frozen)."""
        filled_quantity, fill_price = fill if fill is not None else (0.0, None)
        return Order(
            instrument=order.instrument,
            direction=order.direction,
            quantity=order.quantity,
            order_type=order.order_type,
            status=status,
            order_id=order.order_id,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=filled_quantity,
            average_fill_price=fill_price,
            created_at=order.created_at,
        )

    def _rest(
        self,
        request: ExecutionRequest,
        price: float,
        *,
        order_id: str | None = None,
    ) -> ExecutionResult:
        """Record an untriggered order at the venue, unfilled and honest."""
        order = self._open_order(
            request, status=OrderStatus.SUBMITTED, order_id=order_id
        )
        self._account.orders[order.order_id] = order
        self._account.requests[order.order_id] = request
        # Index the resting order under its client-order-id too, so a repeat
        # submission of the same request resolves to it rather than resting a
        # duplicate working order.
        self._account.idempotency[request.idempotency_key] = order.order_id
        reason = (
            f"Resting at the venue: {request.order_type.value} terms are not met "
            f"at the live price {price:.4f}."
        )
        logger.info("Paper rest: %s -- %s", order.order_id, reason)
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.SUBMITTED,
            reason=reason,
            order_id=order.order_id,
        )

    @staticmethod
    def _report(order: Order, reason: str) -> ExecutionResult:
        """Report an order's state without changing it."""
        return ExecutionResult(
            request_id=f"{order.status.value}:{order.order_id}",
            status=order.status,
            reason=reason,
            order_id=order.order_id,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
        )

    @staticmethod
    def _unknown(order_id: str, action: str) -> ExecutionResult:
        return ExecutionResult(
            request_id=f"{action}:{order_id}",
            status=OrderStatus.REJECTED,
            reason=f"No such paper order '{order_id}'.",
            order_id=order_id,
        )

    @staticmethod
    def _reject(request: ExecutionRequest, reason: str) -> ExecutionResult:
        logger.warning("Paper reject: %s -- %s", request.request_id, reason)
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.REJECTED,
            reason=reason,
        )

    async def _fill_price(self, instrument_key: str) -> float:
        """
        The price for a fill, read from this venue's price source.

        The source owns the read and the error contract; by default it is the
        live feed (see :mod:`aetheros.trading.brokers.price_source`), and a
        simulation swaps in the replayed bar. Raises :class:`BrokerError` when
        no price can be read -- the honest venue outage, never a fabricated
        fill.
        """
        return await self._price_source.price(instrument_key)
