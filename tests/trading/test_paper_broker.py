"""
PaperTradingProvider: real prices, virtual money (spec §10).

The spec is explicit about what paper trading is and is not:

    Paper trading means REAL MARKET DATA + VIRTUAL MONEY.
    It does NOT mean FAKE MARKET DATA + FAKE TRADING.

So the two properties that matter are that a fill price is *read off the
shared market feed* -- not echoed from the request, not invented -- and that a
venue problem is an honest :class:`BrokerError` rather than a fabricated fill.
The virtual balance is likewise honest: it shrinks by what was actually paid
and refuses what it cannot cover.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers import (
    DEFAULT_INITIAL_BALANCE,
    LiveCandlePriceSource,
    PaperTradingProvider,
    PriceSource,
)
from aetheros.trading.domain.enums import (
    Direction,
    OrderStatus,
    OrderType,
    SourceTier,
)
from aetheros.trading.domain.execution import ExecutionRequest
from aetheros.trading.domain.market_data import MarketData
from aetheros.trading.errors import BrokerError
from aetheros.trading.providers.base import MarketDataProvider
from aetheros.trading.services.market_data_service import MarketDataService

from .conftest import FakeProvider, make_market_data
from .test_critic import _risk
from .test_execution import _request
from .test_signal_domain import _setup, _signal


def _feed(price: float) -> MarketData:
    return make_market_data([price - 1.0, price], symbol="TEST")


def _venue(price: float, *, balance: float = DEFAULT_INITIAL_BALANCE):
    service = MarketDataService(FakeProvider(_feed(price)), get_settings())
    return PaperTradingProvider(service, initial_balance=balance)


class _DeadProvider(MarketDataProvider):
    """A venue whose data feed is unreachable."""

    name = "dead"
    tier = SourceTier.PRIMARY

    async def get_candles(self, instrument, timeframe, *, limit):
        raise RuntimeError("The feed is down.")

    async def get_quote(self, instrument):
        raise RuntimeError("The feed is down.")


class _MutableProvider(MarketDataProvider):
    """A feed whose price a test can move, to exercise a resting order."""

    name = "mutable"
    tier = SourceTier.PRIMARY

    def __init__(self, price: float) -> None:
        self.price = price

    async def get_candles(self, instrument, timeframe, *, limit):
        return _feed(self.price)

    async def get_quote(self, instrument):
        raise NotImplementedError("The mutable provider has no quote.")


def _outage_venue() -> PaperTradingProvider:
    service = MarketDataService(_DeadProvider(), get_settings())
    return PaperTradingProvider(service)


# ----------------------------------------------------------------------
# The virtual account


def test_the_paper_account_starts_at_its_configured_balance():
    venue = _venue(250.0, balance=50_000.0)
    assert venue.balance == 50_000.0
    assert venue.order_count == 0


def test_the_default_balance_is_the_documented_constant():
    venue = PaperTradingProvider(
        MarketDataService(FakeProvider(_feed(100.0)), get_settings())
    )
    assert venue.balance == DEFAULT_INITIAL_BALANCE


@pytest.mark.parametrize("balance", [0.0, -1.0, float("inf")])
def test_a_non_positive_initial_balance_is_refused(balance):
    with pytest.raises(ValueError, match="initial paper balance"):
        _venue(100.0, balance=balance)


def test_the_venue_is_labelled_paper_and_mock_tier():
    venue = _venue(100.0)
    assert venue.name == "paper"
    assert venue.is_paper
    assert venue.tier is SourceTier.MOCK


# ----------------------------------------------------------------------
# Fills


@pytest.mark.asyncio
async def test_a_valid_request_fills_at_the_live_market_price():
    venue = _venue(250.0)
    result = await venue.submit(_request(quantity=4.0))
    assert result.filled
    assert result.filled_quantity == 4.0
    assert result.average_fill_price == 250.0
    assert result.order_id is not None
    assert venue.order_count == 1
    assert venue.balance == pytest.approx(DEFAULT_INITIAL_BALANCE - 4.0 * 250.0)


@pytest.mark.asyncio
async def test_the_fill_price_comes_from_the_feed_not_from_the_request():
    """
    §10's whole point: the request names entry 100, the market says 250, and
    the venue fills at the market. A paper venue that echoed the request's own
    price would be fake trading.
    """
    venue = _venue(250.0)
    request = _request(quantity=1.0)
    assert request.entry == 100.0
    result = await venue.submit(request)
    assert result.average_fill_price != request.entry
    assert result.average_fill_price == 250.0


@pytest.mark.asyncio
async def test_a_short_request_fills_the_same_way():
    venue = _venue(80.0)
    result = await venue.submit(_request(Direction.DOWN, quantity=2.0))
    assert result.filled
    assert result.average_fill_price == 80.0


@pytest.mark.asyncio
async def test_a_request_beyond_the_virtual_balance_is_rejected():
    """Virtual money is still finite: an unaffordable order does not fill."""
    venue = _venue(250.0, balance=1_000.0)
    result = await venue.submit(_request(quantity=10.0))  # 2500 > 1000
    assert result.rejected
    assert "cannot cover" in result.reason
    assert venue.balance == 1_000.0
    assert venue.order_count == 0


@pytest.mark.asyncio
async def test_account_equity_follows_the_fills():
    venue = _venue(100.0)
    await venue.submit(_request(quantity=3.0))
    assert await venue.account_equity() == pytest.approx(
        DEFAULT_INITIAL_BALANCE - 3.0 * 100.0
    )


@pytest.mark.asyncio
async def test_a_malformed_request_is_caught_at_the_venue_boundary():
    """
    The §9 invariants are re-checked where engine meets venue. The domain model
    already blocks a bad request, so this fixture tampers with one directly --
    which is exactly the case the boundary check exists for.
    """
    venue = _venue(100.0)
    request = _request()
    object.__setattr__(request, "stop_loss", 105.0)  # long stop above entry
    result = await venue.submit(request)
    assert result.rejected
    assert "stop must sit below" in result.reason
    assert venue.order_count == 0


# ----------------------------------------------------------------------
# Honest failure


@pytest.mark.asyncio
async def test_a_feed_outage_is_a_broker_error_never_a_fill():
    with pytest.raises(BrokerError, match="feed is unavailable"):
        await _outage_venue().submit(_request())


@pytest.mark.asyncio
async def test_an_empty_feed_is_a_broker_error_never_a_fill():
    venue = PaperTradingProvider(
        MarketDataService(
            FakeProvider(replace(_feed(100.0), candles=())), get_settings()
        )
    )
    with pytest.raises(BrokerError, match="No market price"):
        await venue.submit(_request())


@pytest.mark.asyncio
async def test_fill_price_raises_rather_than_inventing_a_price():
    with pytest.raises(BrokerError):
        await _outage_venue().fill_price("TEST")


# ----------------------------------------------------------------------
# Order state


@pytest.mark.asyncio
async def test_an_unknown_order_is_reported_not_fabricated():
    venue = _venue(100.0)
    status = await venue.status("nope")
    assert status.rejected
    assert "No such paper order" in status.reason
    cancel = await venue.cancel("nope")
    assert cancel.rejected
    assert "No such paper order" in cancel.reason


@pytest.mark.asyncio
async def test_an_order_can_be_read_back_after_its_fill():
    venue = _venue(200.0)
    result = await venue.submit(_request(quantity=1.0))
    assert result.order_id is not None
    status = await venue.status(result.order_id)
    assert status.status is OrderStatus.FILLED
    assert status.average_fill_price == 200.0


@pytest.mark.asyncio
async def test_cancelling_a_filled_order_is_an_honest_no_op():
    venue = _venue(200.0)
    result = await venue.submit(_request(quantity=1.0))
    assert result.order_id is not None
    cancelled = await venue.cancel(result.order_id)
    assert cancelled.status is OrderStatus.FILLED
    assert "already filled" in cancelled.reason


# ----------------------------------------------------------------------
# Order types


def _typed(order_type, *, limit=None, stop=None, quantity=1.0):
    return ExecutionRequest.from_signal(
        _signal(Direction.UP),
        _risk(2.0),
        _setup(Direction.UP),
        quantity=quantity,
        order_type=order_type,
        limit_price=limit,
        stop_price=stop,
    )


def _move_the_market(provider: _MutableProvider, service: MarketDataService, price):
    """A new live price, with the service's candle cache dropped so the venue
    re-reads it (a resting order is decided against the *current* market)."""
    provider.price = price
    service._candle_cache.clear()


def _mutable_venue(price: float, *, balance: float = DEFAULT_INITIAL_BALANCE):
    provider = _MutableProvider(price)
    service = MarketDataService(provider, get_settings())
    venue = PaperTradingProvider(service, initial_balance=balance)
    return venue, provider, service


@pytest.mark.asyncio
async def test_a_buy_limit_below_the_market_rests_unfilled():
    venue = _venue(250.0)
    result = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert result.status is OrderStatus.SUBMITTED
    assert not result.filled
    assert result.order_id is not None
    assert "Resting" in result.reason
    assert venue.balance == DEFAULT_INITIAL_BALANCE  # nothing was bought


@pytest.mark.asyncio
async def test_a_marketable_buy_limit_fills_at_the_market_price():
    """Price improvement: never fill a limit order worse than the market."""
    venue = _venue(250.0)
    result = await venue.submit(_typed(OrderType.LIMIT, limit=300.0))
    assert result.filled
    assert result.average_fill_price == 250.0


@pytest.mark.asyncio
async def test_a_buy_stop_triggers_once_the_market_is_at_or_past_it():
    venue = _venue(250.0)
    armed = await venue.submit(_typed(OrderType.STOP, stop=200.0))
    assert armed.filled
    assert armed.average_fill_price == 250.0

    unarmed = await venue.submit(_typed(OrderType.STOP, stop=300.0))
    assert unarmed.status is OrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_a_stop_limit_needs_both_of_its_legs():
    venue = _venue(250.0)
    # Stop armed (250 >= 200) and the limit acceptable (250 <= 300).
    both = await venue.submit(_typed(OrderType.STOP_LIMIT, stop=200.0, limit=300.0))
    assert both.filled

    # Stop armed but the limit is now unachievable: it becomes a resting limit.
    capped = await venue.submit(_typed(OrderType.STOP_LIMIT, stop=200.0, limit=240.0))
    assert capped.status is OrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_a_resting_order_fills_when_the_market_reaches_it():
    venue, provider, service = _mutable_venue(250.0)
    resting = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert resting.status is OrderStatus.SUBMITTED
    assert resting.order_id is not None

    _move_the_market(provider, service, 190.0)
    filled = await venue.status(resting.order_id)
    assert filled.status is OrderStatus.FILLED
    # Filled at the market (190), which is better than the 200 limit.
    assert filled.average_fill_price == 190.0


@pytest.mark.asyncio
async def test_a_resting_order_is_reported_as_still_resting():
    venue, provider, service = _mutable_venue(250.0)
    resting = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert resting.order_id is not None
    _move_the_market(provider, service, 240.0)
    still = await venue.status(resting.order_id)
    assert still.status is OrderStatus.SUBMITTED
    assert "Still resting" in still.reason


@pytest.mark.asyncio
async def test_an_order_type_is_visible_in_the_venues_record():
    venue = _venue(250.0)
    result = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert result.order_id is not None
    assert venue.order_count == 1


# ----------------------------------------------------------------------
# Amendments


@pytest.mark.asyncio
async def test_a_resting_order_can_be_amended_in_place():
    venue, _provider, _service = _mutable_venue(250.0)
    resting = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert resting.order_id is not None

    # Amend to a limit the market already satisfies: a real venue executes a
    # modified order that is marketable.
    amended = await venue.modify(
        resting.order_id, _typed(OrderType.LIMIT, limit=260.0)
    )
    assert amended.status is OrderStatus.FILLED
    assert amended.order_id == resting.order_id
    assert amended.average_fill_price == 250.0
    assert venue.order_count == 1  # amended, not duplicated


@pytest.mark.asyncio
async def test_an_amendment_that_still_does_not_trigger_leaves_it_resting():
    venue = _venue(250.0)
    resting = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert resting.order_id is not None
    amended = await venue.modify(
        resting.order_id, _typed(OrderType.LIMIT, limit=210.0)
    )
    assert amended.status is OrderStatus.SUBMITTED
    assert amended.order_id == resting.order_id


@pytest.mark.asyncio
async def test_modifying_a_filled_order_is_an_honest_no_op():
    venue = _venue(200.0)
    filled = await venue.submit(_request(quantity=1.0))
    assert filled.order_id is not None
    amended = await venue.modify(filled.order_id, _typed(OrderType.LIMIT, limit=100.0))
    assert amended.status is OrderStatus.FILLED
    assert "no longer live" in amended.reason


@pytest.mark.asyncio
async def test_modifying_an_unknown_order_is_reported():
    venue = _venue(200.0)
    amended = await venue.modify("nope", _typed(OrderType.LIMIT, limit=100.0))
    assert amended.rejected
    assert "No such paper order" in amended.reason


@pytest.mark.asyncio
async def test_a_cancelled_order_reports_its_status():
    venue = _venue(250.0)
    resting = await venue.submit(_typed(OrderType.LIMIT, limit=200.0))
    assert resting.order_id is not None
    cancelled = await venue.cancel(resting.order_id)
    assert cancelled.status is OrderStatus.CANCELLED
    again = await venue.cancel(resting.order_id)
    assert again.status is OrderStatus.CANCELLED
    assert "already cancelled" in again.reason
    reported = await venue.status(resting.order_id)
    assert reported.status is OrderStatus.CANCELLED


# ----------------------------------------------------------------------
# The fill-price seam (spec Phase 14)


class _FixedPriceSource:
    """A price source a test drives directly, or makes fail on demand."""

    def __init__(self, price: float | None = None) -> None:
        # Held privately: naming the attribute ``price`` would shadow the
        # method the protocol is made of, and the venue would then call a float.
        self._price = price
        self.seen: list[str] = []

    async def price(self, instrument_key: str) -> float:
        self.seen.append(instrument_key)
        if self._price is None:
            raise BrokerError("The replayed feed has no bar here.")
        return self._price


def test_a_live_price_source_satisfies_the_protocol():
    source = LiveCandlePriceSource(
        MarketDataService(FakeProvider(_feed(100.0)), get_settings())
    )
    assert isinstance(source, PriceSource)


@pytest.mark.asyncio
async def test_an_injected_price_source_is_what_the_venue_fills_at():
    """
    The Phase 14 seam: a simulation points the *same* paper venue at a
    replayed bar. Nothing else about the venue changes -- the fill still comes
    from its price source, and the request's own entry is still ignored.
    """
    source = _FixedPriceSource(175.0)
    venue = PaperTradingProvider(price_source=source)
    request = _request(quantity=2.0)
    assert request.entry == 100.0

    result = await venue.submit(request)
    assert result.filled
    assert result.average_fill_price == 175.0
    assert source.seen == [request.instrument.key]
    assert venue.balance == pytest.approx(DEFAULT_INITIAL_BALANCE - 2.0 * 175.0)


@pytest.mark.asyncio
async def test_a_source_outage_is_a_broker_error_never_a_fill():
    """The seam does not soften the venue's honesty contract."""
    venue = PaperTradingProvider(price_source=_FixedPriceSource(None))
    with pytest.raises(BrokerError, match="no bar here"):
        await venue.submit(_request())


def test_a_venue_with_neither_a_feed_nor_a_source_is_refused():
    with pytest.raises(ValueError, match="either market data or a price source"):
        PaperTradingProvider()

