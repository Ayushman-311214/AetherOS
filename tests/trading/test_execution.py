"""
The execution engine and its request record (spec Phase 9, §9).

Two contracts are pinned here, and they are the reason this phase exists:

- **nothing under-specified can be submitted.** :class:`ExecutionRequest`
  cannot be constructed without every field the financial-safety contract
  names, and the engine's only accepted input is that record -- there is no
  path from free text (an LLM's, a caller's) to a venue.
- **retry is bounded and honest.** A transport fault is retried at most
  ``max_retries`` times and then raised as :class:`ExecutionError`, because
  the request's fate is unknown and saying so is the only truthful answer. A
  venue's REJECTED decision is never retried -- that would be trying to wear
  the venue down.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.brokers.base import BrokerProvider
from aetheros.trading.domain.enums import (
    Direction,
    OrderStatus,
    OrderType,
    SourceTier,
    TradeAction,
)
from aetheros.trading.domain.execution import ExecutionRequest, ExecutionResult
from aetheros.trading.domain.risk_limits import AccountSnapshot
from aetheros.trading.errors import BrokerError, ExecutionError
from aetheros.trading.events import OrderSubmitted
from aetheros.trading.execution import ExecutionEngine
from aetheros.trading.risk import RiskLimitsService

from .test_critic import _risk
from .test_signal_domain import _setup, _signal


def _request(direction: Direction = Direction.UP, *, quantity: float = 10.0):
    """A long request built from the same fixtures the signal tests use, so the
    engine is exercised on the objects the pipeline actually produces.

    The shared ``_risk`` fixture leaves ``risk_pct`` unset, but the real
    ``RiskService`` always stamps a per-trade risk (defaulting to the configured
    account pct), so we fill a concrete in-cap value here. That keeps these
    tests focused on the risk-limits/retry path rather than the Phase 26 policy
    gate, which fails closed on an unknown per-trade risk and has its own suite.
    """
    risk = replace(_risk(2.0, direction=direction), risk_pct=1.0)
    return ExecutionRequest.from_signal(
        _signal(direction),
        risk,
        _setup(direction),
        quantity=quantity,
    )


def _healthy_snapshot() -> AccountSnapshot:
    return AccountSnapshot(
        equity=100_000.0, realised_pnl_today=0.0, open_exposure_notional=10_000.0
    )


def _breached_snapshot() -> AccountSnapshot:
    return AccountSnapshot(
        equity=100_000.0, realised_pnl_today=-5_000.0, open_exposure_notional=10_000.0
    )


class _StubBroker(BrokerProvider):
    """A venue that records what it was asked and can be made to misbehave."""

    name = "stub"
    # A paper-tier test venue: under the default PAPER trading mode the policy
    # gate permits it, so these tests exercise the risk/retry path (what this
    # file is about) rather than tripping the Phase 26 policy gate, which has
    # its own suite.
    tier = SourceTier.MOCK

    def __init__(
        self,
        *,
        transport_failures: int = 0,
        reject: bool = False,
        cancel_fault: bool = False,
    ) -> None:
        self.transport_failures = transport_failures
        self.reject = reject
        self.cancel_fault = cancel_fault
        self.submitted: list[ExecutionRequest] = []
        self.modified: list[tuple[str, ExecutionRequest]] = []

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        self.submitted.append(request)
        if len(self.submitted) <= self.transport_failures:
            raise BrokerError("The venue is unreachable.")
        if self.reject:
            return ExecutionResult(
                request_id=request.request_id,
                status=OrderStatus.REJECTED,
                reason="The venue declined the order.",
            )
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.FILLED,
            reason="Filled by the stub venue.",
            order_id=f"ord_{len(self.submitted)}",
            filled_quantity=request.quantity,
            average_fill_price=request.entry,
        )

    async def cancel(self, order_id: str) -> ExecutionResult:
        if self.cancel_fault:
            raise BrokerError("The venue is unreachable.")
        return ExecutionResult(
            request_id="cancel", status=OrderStatus.CANCELLED, reason="Cancelled.",
            order_id=order_id,
        )

    async def modify(
        self, order_id: str, request: ExecutionRequest
    ) -> ExecutionResult:
        if self.cancel_fault:
            raise BrokerError("The venue is unreachable.")
        self.modified.append((order_id, request))
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.SUBMITTED,
            reason="Terms amended; the order rests.",
            order_id=order_id,
        )

    async def status(self, order_id: str) -> ExecutionResult:
        if self.cancel_fault:
            raise BrokerError("The venue is unreachable.")
        return ExecutionResult(
            request_id="status", status=OrderStatus.FILLED,
            reason="Filled.", order_id=order_id,
        )

    async def fill_price(self, instrument_key: str) -> float:
        return 100.0

    async def account_equity(self) -> float:
        return 100_000.0


def _engine(broker: BrokerProvider, **kwargs) -> ExecutionEngine:
    return ExecutionEngine(
        broker,
        RiskLimitsService(get_settings()),
        get_settings(),
        **kwargs,
    )


# ----------------------------------------------------------------------
# The §9 request record


def test_a_request_carries_every_field_the_safety_contract_names():
    payload = _request().to_dict()
    for field in (
        "instrument",
        "direction",
        "quantity",
        "entry",
        "stop_loss",
        "take_profit",
        "risk",
        "risk_reward_ratio",
        "strategy_id",
        "reasoning",
        "evidence",
        "signal_id",
    ):
        assert field in payload, field


def test_from_signal_copies_the_signals_geometry_and_pedigree():
    signal = _signal(Direction.UP)
    request = ExecutionRequest.from_signal(
        signal, _risk(2.0), _setup(Direction.UP), quantity=5.0
    )
    assert request.entry == signal.entry
    assert request.stop_loss == signal.stop_loss
    assert request.take_profit == signal.take_profit
    assert request.strategy_id == signal.strategy_id
    assert request.signal_id == signal.signal_id
    assert request.reasoning == signal.reasoning
    assert request.evidence == signal.evidence
    # The quantity is the one thing the signal layer deliberately never carried.
    assert request.quantity == 5.0


def test_a_long_stop_at_or_above_entry_is_rejected():
    with pytest.raises(ValueError, match="stop must sit below"):
        replace(_request(), stop_loss=100.0)


def test_a_short_stop_at_or_below_entry_is_rejected():
    with pytest.raises(ValueError, match="stop must sit above"):
        replace(_request(Direction.DOWN), stop_loss=100.0)


def test_a_long_target_below_entry_is_rejected():
    with pytest.raises(ValueError, match="target must sit above"):
        replace(_request(), take_profit=99.0)


def test_a_short_target_above_entry_is_rejected():
    with pytest.raises(ValueError, match="target must sit below"):
        replace(_request(Direction.DOWN), take_profit=101.0)


@pytest.mark.parametrize("quantity", [0.0, -1.0, float("nan")])
def test_a_quantity_must_be_positive_and_finite(quantity):
    with pytest.raises(ValueError, match="quantity"):
        replace(_request(), quantity=quantity)


def test_a_request_must_keep_its_reason():
    with pytest.raises(ValueError, match="reasoning"):
        replace(_request(), reasoning="   ")


def test_a_request_must_name_a_strategy():
    with pytest.raises(ValueError, match="strategy"):
        replace(_request(), strategy_id="")


def test_a_non_directional_request_is_rejected():
    with pytest.raises(ValueError, match="directional"):
        replace(_request(), direction=Direction.SIDEWAYS)


def test_from_signal_refuses_a_setup_from_another_strategy():
    stranger = replace(_setup(Direction.UP), strategy_id="mean_reversion")
    with pytest.raises(ValueError, match="one strategy"):
        ExecutionRequest.from_signal(_signal(), _risk(2.0), stranger, quantity=1.0)


def test_from_signal_refuses_a_setup_on_the_other_side():
    with pytest.raises(ValueError, match="share a side"):
        ExecutionRequest.from_signal(
            _signal(Direction.UP),
            _risk(2.0),
            _setup(Direction.DOWN),
            quantity=1.0,
        )


def test_from_signal_refuses_risk_geometry_from_another_side():
    with pytest.raises(ValueError, match="risk assessment"):
        ExecutionRequest.from_signal(
            _signal(Direction.UP),
            _risk(2.0, direction=Direction.DOWN),
            _setup(Direction.UP),
            quantity=1.0,
        )


def test_from_signal_refuses_a_signal_without_a_target():
    with pytest.raises(ValueError, match="target"):
        ExecutionRequest.from_signal(
            replace(_signal(), take_profit=None),
            _risk(2.0),
            _setup(Direction.UP),
            quantity=1.0,
        )


# ----------------------------------------------------------------------
# Validation


@pytest.mark.asyncio
async def test_validation_without_a_snapshot_says_what_it_did_not_check():
    report = await _engine(_StubBroker()).validate(_request())
    assert report.ok
    assert report.risk_limits is None
    assert "not checked" in report.reason


@pytest.mark.asyncio
async def test_validation_refuses_a_breached_account_by_name():
    report = await _engine(_StubBroker()).validate(
        _request(), account_snapshot=_breached_snapshot()
    )
    assert not report.ok
    assert report.risk_limits is not None
    assert not report.risk_limits.allowed
    assert "daily loss limit" in report.reason


@pytest.mark.asyncio
async def test_validation_passes_an_account_inside_its_limits():
    report = await _engine(_StubBroker()).validate(
        _request(), account_snapshot=_healthy_snapshot()
    )
    assert report.ok
    assert report.risk_limits.allowed


# ----------------------------------------------------------------------
# Submission


@pytest.mark.asyncio
async def test_a_valid_request_fills_through_a_healthy_venue():
    broker = _StubBroker()
    result = await _engine(broker).submit(
        _request(quantity=7.0), account_snapshot=_healthy_snapshot()
    )
    assert result.filled
    assert result.filled_quantity == 7.0
    assert result.average_fill_price == 100.0
    assert result.order_id == "ord_1"
    assert len(broker.submitted) == 1


@pytest.mark.asyncio
async def test_a_breached_account_never_reaches_the_venue():
    broker = _StubBroker()
    result = await _engine(broker).submit(
        _request(), account_snapshot=_breached_snapshot()
    )
    assert result.rejected
    assert "daily loss limit" in result.reason
    assert broker.submitted == []


@pytest.mark.asyncio
async def test_skipping_validation_is_the_callers_explicit_choice():
    broker = _StubBroker()
    result = await _engine(broker).submit(
        _request(), account_snapshot=_breached_snapshot(), validate=False
    )
    assert result.filled
    assert len(broker.submitted) == 1


@pytest.mark.asyncio
async def test_a_transport_fault_is_retried_then_succeeds():
    broker = _StubBroker(transport_failures=1)
    engine = _engine(broker, max_retries=2, retry_backoff_seconds=0.0)
    result = await engine.submit(_request())
    assert result.filled
    assert len(broker.submitted) == 2


@pytest.mark.asyncio
async def test_the_retry_budget_is_finite_and_reported_when_exhausted():
    broker = _StubBroker(transport_failures=99)
    engine = _engine(broker, max_retries=2, retry_backoff_seconds=0.0)
    with pytest.raises(ExecutionError, match="fate is unknown"):
        await engine.submit(_request())
    # One initial attempt plus two retries -- no more, no less.
    assert len(broker.submitted) == 3


@pytest.mark.asyncio
async def test_a_venue_rejection_is_returned_not_retried():
    """Wearing the venue down is not a strategy."""
    broker = _StubBroker(reject=True)
    engine = _engine(broker, max_retries=3, retry_backoff_seconds=0.0)
    result = await engine.submit(_request())
    assert result.rejected
    assert "declined the order" in result.reason
    assert len(broker.submitted) == 1


@pytest.mark.asyncio
async def test_an_order_submitted_event_carries_the_venues_identifiers():
    bus = EventBus()
    received: list[OrderSubmitted] = []
    await bus.subscribe(OrderSubmitted, lambda event: received.append(event))
    broker = _StubBroker()
    await _engine(broker, event_bus=bus).submit(
        _request(quantity=3.0), account_snapshot=_healthy_snapshot()
    )
    assert len(received) == 1
    assert received[0].order_id == "ord_1"
    assert received[0].provider == "stub"
    assert received[0].quantity == 3.0
    assert received[0].direction == Direction.UP.value


@pytest.mark.asyncio
async def test_nothing_is_announced_for_an_order_no_venue_saw():
    bus = EventBus()
    received: list[OrderSubmitted] = []
    await bus.subscribe(OrderSubmitted, lambda event: received.append(event))
    await _engine(_StubBroker(), event_bus=bus).submit(
        _request(), account_snapshot=_breached_snapshot()
    )
    assert received == []


@pytest.mark.asyncio
async def test_a_venue_outage_during_cancel_is_an_execution_error():
    with pytest.raises(ExecutionError, match="Could not cancel"):
        await _engine(_StubBroker(cancel_fault=True)).cancel("ord_1")


@pytest.mark.asyncio
async def test_a_venue_outage_during_status_is_an_execution_error():
    with pytest.raises(ExecutionError, match="Could not read"):
        await _engine(_StubBroker(cancel_fault=True)).status("ord_1")


@pytest.mark.asyncio
async def test_cancel_and_status_pass_through_a_healthy_venue():
    engine = _engine(_StubBroker())
    assert (await engine.cancel("ord_1")).status is OrderStatus.CANCELLED
    assert (await engine.status("ord_1")).status is OrderStatus.FILLED


def test_a_negative_retry_budget_is_refused():
    with pytest.raises(ValueError, match="max_retries"):
        _engine(_StubBroker(), max_retries=-1)
    with pytest.raises(ValueError, match="retry_backoff_seconds"):
        _engine(_StubBroker(), retry_backoff_seconds=-0.1)


def test_the_execution_result_never_claims_an_unknown_fill():
    result = ExecutionResult(
        request_id="req_1", status=OrderStatus.REJECTED, reason="Declined."
    )
    assert not result.filled
    assert result.rejected
    assert result.average_fill_price is None
    assert result.filled_quantity == 0.0


def test_the_signal_action_matches_the_requests_side():
    """A SELL signal can only ever produce a DOWN request."""
    request = _request(Direction.DOWN)
    assert request.direction is Direction.DOWN
    assert _signal(Direction.DOWN).action is TradeAction.SELL


# ----------------------------------------------------------------------
# Order types (the Execution Engine "supports" list)


def _typed(order_type: OrderType, *, limit=None, stop=None) -> ExecutionRequest:
    return ExecutionRequest.from_signal(
        _signal(Direction.UP),
        replace(_risk(2.0), risk_pct=1.0),
        _setup(Direction.UP),
        quantity=1.0,
        order_type=order_type,
        limit_price=limit,
        stop_price=stop,
    )


def test_a_market_request_is_the_default_and_carries_no_trigger_price():
    request = _request()
    assert request.order_type is OrderType.MARKET
    assert not request.is_resting
    assert request.limit_price is None and request.stop_price is None


def test_a_limit_request_must_carry_its_limit_price():
    resting = _typed(OrderType.LIMIT, limit=99.0)
    assert resting.is_resting
    with pytest.raises(ValueError, match="requires a limit price"):
        _typed(OrderType.LIMIT)


def test_a_stop_request_must_carry_its_stop_price():
    assert _typed(OrderType.STOP, stop=101.0).stop_price == 101.0
    with pytest.raises(ValueError, match="requires a stop price"):
        _typed(OrderType.STOP)


def test_a_stop_limit_request_needs_both_prices():
    both = _typed(OrderType.STOP_LIMIT, stop=101.0, limit=102.0)
    assert both.is_resting
    with pytest.raises(ValueError, match="requires a stop price"):
        _typed(OrderType.STOP_LIMIT, limit=102.0)
    with pytest.raises(ValueError, match="requires a limit price"):
        _typed(OrderType.STOP_LIMIT, stop=101.0)


def test_a_market_request_cannot_state_a_trigger_the_venue_will_not_read():
    with pytest.raises(ValueError, match="cannot carry a limit or stop price"):
        replace(_request(), limit_price=99.0)


@pytest.mark.parametrize("price", [0.0, -1.0, float("inf")])
def test_a_trigger_price_must_be_positive_and_finite(price):
    with pytest.raises(ValueError, match="limit_price"):
        _typed(OrderType.LIMIT, limit=price)


# ----------------------------------------------------------------------
# Amendments


@pytest.mark.asyncio
async def test_an_amendment_reaches_the_venue_under_the_same_gate():
    broker = _StubBroker()
    result = await _engine(broker).modify(
        "ord_1", _typed(OrderType.LIMIT, limit=99.0),
        account_snapshot=_healthy_snapshot(),
    )
    assert result.status is OrderStatus.SUBMITTED
    assert [order_id for order_id, _ in broker.modified] == ["ord_1"]


@pytest.mark.asyncio
async def test_an_amendment_is_refused_when_the_account_is_over_its_limits():
    broker = _StubBroker()
    result = await _engine(broker).modify(
        "ord_1", _typed(OrderType.LIMIT, limit=99.0),
        account_snapshot=_breached_snapshot(),
    )
    assert result.rejected
    assert "daily loss limit" in result.reason
    assert result.order_id == "ord_1"
    assert broker.modified == []


@pytest.mark.asyncio
async def test_a_venue_outage_during_an_amendment_is_an_execution_error():
    with pytest.raises(ExecutionError, match="Could not modify"):
        await _engine(_StubBroker(cancel_fault=True)).modify(
            "ord_1", _typed(OrderType.LIMIT, limit=99.0)
        )


@pytest.mark.asyncio
async def test_the_submitted_event_names_the_order_type():
    bus = EventBus()
    received: list[OrderSubmitted] = []
    await bus.subscribe(OrderSubmitted, lambda event: received.append(event))
    await _engine(_StubBroker(), event_bus=bus).submit(
        _typed(OrderType.LIMIT, limit=99.0), account_snapshot=_healthy_snapshot()
    )
    assert len(received) == 1
    assert received[0].order_type == OrderType.LIMIT.value

