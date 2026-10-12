"""
OrderBook / TradeTick value objects: shape invariants (Phase 2).

These pin the honesty rules for microstructure data: levels are positive,
books are ordered best-first and never crossed, ticks carry a side and an
aware timestamp -- and malformed inputs are rejected rather than repaired.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.order_book import (
    OrderBook,
    OrderBookLevel,
    TradeTick,
)
from aetheros.trading.domain.provenance import Provenance

UTC = timezone.utc


def _prov() -> Provenance:
    return Provenance(source="test", tier=SourceTier.PRIMARY, detail="fixture")


_BTC = Instrument("BTC")


def _book(bids, asks, instrument=_BTC) -> OrderBook:
    return OrderBook(
        instrument=instrument,
        bids=tuple(OrderBookLevel(price=p, amount=a) for p, a in bids),
        asks=tuple(OrderBookLevel(price=p, amount=a) for p, a in asks),
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        provenance=_prov(),
    )


class TestOrderBookLevel:
    def test_positive_price_and_amount(self) -> None:
        level = OrderBookLevel(price=100.0, amount=1.5, count=3)
        assert level.to_dict() == {"price": 100.0, "amount": 1.5, "count": 3}

    @pytest.mark.parametrize(
        "price,amount",
        [(0.0, 1.0), (-1.0, 1.0), (float("nan"), 1.0), (100.0, 0.0), (100.0, -1.0)],
    )
    def test_non_positive_or_non_finite_rejected(self, price, amount) -> None:
        with pytest.raises(ValueError):
            OrderBookLevel(price=price, amount=amount)

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValueError):
            OrderBookLevel(price=100.0, amount=1.0, count=-1)


class TestOrderBook:
    def test_spread_and_mid(self) -> None:
        book = _book([(99.0, 2.0), (98.0, 3.0)], [(101.0, 1.0), (102.0, 4.0)])
        assert book.best_bid == 99.0
        assert book.best_ask == 101.0
        assert book.spread == pytest.approx(2.0)
        assert book.mid_price == pytest.approx(100.0)
        payload = book.to_dict()
        assert payload["instrument"]["symbol"] == "BTC"
        assert len(payload["bids"]) == 2

    def test_empty_book_is_valid_with_no_best(self) -> None:
        book = _book([], [])
        assert book.best_bid is None
        assert book.spread is None
        assert book.mid_price is None

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            OrderBook(
                instrument=Instrument("BTC"),
                bids=(),
                asks=(),
                timestamp=datetime(2025, 1, 1),
                provenance=_prov(),
            )

    def test_unordered_bids_rejected(self) -> None:
        # bids must descend from best; ascending is a malformed book.
        with pytest.raises(ValueError, match="bids"):
            _book([(98.0, 1.0), (99.0, 1.0)], [])

    def test_unordered_asks_rejected(self) -> None:
        # asks must ascend from best.
        with pytest.raises(ValueError, match="asks"):
            _book([], [(102.0, 1.0), (101.0, 1.0)])

    def test_duplicate_price_levels_rejected(self) -> None:
        # Equal consecutive prices are ambiguous, not a real book.
        with pytest.raises(ValueError):
            _book([(99.0, 1.0), (99.0, 2.0)], [])
        with pytest.raises(ValueError):
            _book([], [(101.0, 1.0), (101.0, 2.0)])

    def test_crossed_book_rejected(self) -> None:
        # best bid at or above best ask is a crossed/locked market.
        with pytest.raises(ValueError, match="crossed"):
            _book([(101.0, 1.0)], [(101.0, 1.0)])


class TestTradeTick:
    def _tick(self, **overrides) -> TradeTick:
        kwargs = dict(
            instrument=Instrument("BTC"),
            price=100.0,
            amount=0.5,
            side=Direction.UP,
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            tick_id="t-1",
            provenance=_prov(),
        )
        kwargs.update(overrides)
        return TradeTick(**kwargs)

    def test_valid_tick_serialises(self) -> None:
        tick = self._tick()
        payload = tick.to_dict()
        assert payload["side"] == "up"
        assert payload["tick_id"] == "t-1"

    def test_negative_side_rejected(self) -> None:
        with pytest.raises(ValueError, match="UP"):
            self._tick(side=Direction.SIDEWAYS)

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            self._tick(timestamp=datetime(2025, 1, 1))

    def test_non_positive_price_or_amount_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._tick(price=0.0)
        with pytest.raises(ValueError):
            self._tick(amount=-1.0)
