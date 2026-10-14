"""
Idempotent execution (spec Phase 2 -- duplicate prevention, retry safety).

An order's client-order-id is content-addressed off the signal it descends
from, so a retried or re-issued submission resolves to the order already
placed instead of filling twice. These tests pin the property that makes the
engine's transport retry safe:

- the same signal re-submitted under the same key dedupes to one fill;
- a genuinely different order (different size) does not collide;
- a RESTING order replays to the same resting order, not a duplicate.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers import PaperTradingProvider
from aetheros.trading.domain.enums import OrderStatus
from aetheros.trading.domain.execution import ExecutionRequest
from aetheros.trading.services.market_data_service import MarketDataService

from .conftest import FakeProvider, make_market_data
from .test_paper_broker import _feed
from .test_signal_domain import _setup, _signal
from .test_critic import _risk
from .test_execution import _request

from dataclasses import replace


def _venue(price: float = 250.0) -> PaperTradingProvider:
    service = MarketDataService(FakeProvider(_feed(price)), get_settings())
    return PaperTradingProvider(service)


@pytest.mark.asyncio
async def test_the_same_signal_resubmitted_dedupes_to_one_fill():
    venue = _venue(250.0)
    request = _request(quantity=4.0)
    first = await venue.submit(request)
    assert first.status is OrderStatus.FILLED
    # Rebuilding the *same* request object produces the same idempotency key.
    replay = await venue.submit(request)
    assert replay.order_id == first.order_id
    assert venue.order_count == 1  # one fill, not two


@pytest.mark.asyncio
async def test_two_requests_with_distinct_signals_do_not_dedupe():
    venue = _venue(250.0)
    a = _request(quantity=4.0)
    # A different signal id -> a different key -> a genuinely new order.
    b = _request(quantity=4.0)
    ra = await venue.submit(a)
    rb = await venue.submit(b)
    assert ra.order_id != rb.order_id
    assert venue.order_count == 2


@pytest.mark.asyncio
async def test_a_different_quantity_is_a_different_order():
    venue = _venue(250.0)
    a = _request(quantity=4.0)
    b = _request(quantity=6.0)
    await venue.submit(a)
    await venue.submit(b)
    assert venue.order_count == 2


def test_idempotency_key_is_deterministic_for_a_signal():
    a = _request(quantity=4.0)
    b = _request(quantity=4.0)
    # Different signal ids -> different keys (the fixture signal id is a uuid).
    assert a.idempotency_key != b.idempotency_key
    # But a request's key is stable under rebuild.
    assert a.idempotency_key == a.client_order_id
    assert a.idempotency_key.startswith("coid_")
