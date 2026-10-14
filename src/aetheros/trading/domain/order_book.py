"""
Order-book and trade-tick value objects.

Microstructure data sits beside (never inside) :class:`Candle` series: an
order book is a depth snapshot, a trade tick is an executed print. Both carry
Provenance so a consumer can always see which feed produced them, and both
are honest about shape -- levels are validated positive, crossed books are
rejected rather than silently accepted, and an empty book is a legitimate
result distinct from a failed fetch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .enums import Direction
from .instrument import Instrument
from .provenance import Provenance


def _positive(value: float, field_name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field_name} must be a finite positive number.")


def _aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    """One price level of a book side: price, resting amount, order count."""

    price: float
    amount: float
    count: int = 0

    def __post_init__(self) -> None:
        _positive(self.price, "OrderBookLevel price")
        _positive(self.amount, "OrderBookLevel amount")
        if self.count < 0:
            raise ValueError("OrderBookLevel count must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        return {"price": self.price, "amount": self.amount, "count": self.count}


@dataclass(frozen=True, slots=True)
class OrderBook:
    """A depth snapshot: bids (best first) and asks (best first)."""

    instrument: Instrument
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    timestamp: datetime
    provenance: Provenance

    def __post_init__(self) -> None:
        _aware(self.timestamp, "OrderBook timestamp")
        # Bids are ordered best-first (DESCENDING price); asks best-first
        # (ASCENDING price). Both conventions are what "best first" means on
        # each side of the book.
        for i in range(len(self.bids) - 1):
            if self.bids[i + 1].price >= self.bids[i].price:
                raise ValueError("bids must be ordered best-first (descending price).")
        for i in range(len(self.asks) - 1):
            if self.asks[i + 1].price <= self.asks[i].price:
                raise ValueError("asks must be ordered best-first (ascending price).")
        best_bid = self.bids[0].price if self.bids else None
        best_ask = self.asks[0].price if self.asks else None
        if best_bid is not None and best_ask is not None and best_bid >= best_ask:
            raise ValueError("Order book is crossed: best bid must be below best ask.")

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "timestamp": self.timestamp.isoformat(),
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class TradeTick:
    """One executed trade print."""

    instrument: Instrument
    price: float
    amount: float
    side: Direction
    timestamp: datetime
    tick_id: str | None = None
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _positive(self.price, "TradeTick price")
        _positive(self.amount, "TradeTick amount")
        if self.side not in (Direction.UP, Direction.DOWN):
            raise ValueError("TradeTick side must be UP (buy) or DOWN (sell).")
        _aware(self.timestamp, "TradeTick timestamp")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "price": self.price,
            "amount": self.amount,
            "side": self.side.value,
            "timestamp": self.timestamp.isoformat(),
            "tick_id": self.tick_id,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }
