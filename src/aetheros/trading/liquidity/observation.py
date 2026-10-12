"""
The canonical liquidity observation.

A :class:`LiquidityObservation` is a point-in-time read of the resting and
aggressive liquidity an instrument showed in one order-book snapshot plus the
trade prints that arrived since the previous observation. It is the atomic unit
the analyzers, feature extractor and any future heatmap/dashboard consume.

Two things are kept strictly separate here, and it is the heart of the model:

* **Resting liquidity** -- ``bid_liquidity`` / ``ask_liquidity`` -- is what the
  book *displays*: the aggregated quantity sitting on each side. It is observed
  state, not a promise that the orders will stand.
* **Aggressive (executed) liquidity** -- ``executed_buy_volume`` /
  ``executed_sell_volume`` -- is what actually *printed*: buyer- and
  seller-initiated volume that crossed the spread in the window. It is the flow
  that can consume, absorb or be absorbed by the resting side.

``imbalance`` and ``net_flow`` are *derived* from those four numbers (never
asserted independently): imbalance compares the two resting sides, net_flow
compares the two executed sides. The distinction matters -- a book can be
bid-heavy while the tape sells, and reading one as the other is exactly the
error this model exists to prevent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _check_finite_nonnegative(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number.")


@dataclass(frozen=True, slots=True)
class LiquidityObservation:
    """
    A point-in-time read of resting + aggressive liquidity for one instrument.

    ``symbol`` is the instrument key (``EXCHANGE:SYMBOL`` or ``SYMBOL``).
    ``timestamp`` is the observation's own time -- the snapshot/print time, not
    the wall clock at construction -- so a replayed stream keeps its true times.
    ``price`` is the reference price for the observation (the book's mid, or the
    last trade price when no book was read).
    """

    symbol: str
    timestamp: datetime
    price: float

    # Resting liquidity observed on the book.
    bid_liquidity: float = 0.0
    ask_liquidity: float = 0.0

    # Aggressive liquidity actually printed in the observation window.
    executed_buy_volume: float = 0.0
    executed_sell_volume: float = 0.0

    # Where this observation came from (e.g. "ccxt", "yahoo", "mock"). Surfaced,
    # never inferred, so a consumer can never mistake a synthetic read for real.
    source: str = ""
    is_mock: bool = False

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("A liquidity observation requires a symbol.")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Liquidity observation timestamp must be tz-aware.")
        if not math.isfinite(self.price) or self.price <= 0:
            raise ValueError("Liquidity observation price must be finite and > 0.")
        _check_finite_nonnegative(self.bid_liquidity, "bid_liquidity")
        _check_finite_nonnegative(self.ask_liquidity, "ask_liquidity")
        _check_finite_nonnegative(self.executed_buy_volume, "executed_buy_volume")
        _check_finite_nonnegative(
            self.executed_sell_volume, "executed_sell_volume"
        )

    # ------------------------------------------------------------------
    # Derived quantities (computed, never stored -- cannot drift from source)
    # ------------------------------------------------------------------

    @property
    def total_liquidity(self) -> float:
        """Total resting liquidity displayed on both sides."""
        return self.bid_liquidity + self.ask_liquidity

    @property
    def imbalance(self) -> float:
        """
        Signed resting-liquidity imbalance in ``[-1, 1]``.

        ``(bid - ask) / (bid + ask)``: positive means the book is bid-heavy,
        negative ask-heavy, zero balanced (or no book at all). Computed from the
        two resting figures so it can never disagree with them.
        """
        total = self.total_liquidity
        if total <= 0:
            return 0.0
        return (self.bid_liquidity - self.ask_liquidity) / total

    @property
    def net_flow(self) -> float:
        """
        Signed executed flow in ``[-1, 1]``.

        ``(buy_prints - sell_prints) / (buy + sell)``: positive means the tape
        was buyer-initiated, negative seller-initiated, zero no flow. Computed
        from the executed figures -- this is *aggressive* liquidity, distinct
        from the resting ``imbalance`` above.
        """
        total = self.executed_buy_volume + self.executed_sell_volume
        if total <= 0:
            return 0.0
        return (self.executed_buy_volume - self.executed_sell_volume) / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "bid_liquidity": self.bid_liquidity,
            "ask_liquidity": self.ask_liquidity,
            "executed_buy_volume": self.executed_buy_volume,
            "executed_sell_volume": self.executed_sell_volume,
            "total_liquidity": self.total_liquidity,
            "imbalance": self.imbalance,
            "net_flow": self.net_flow,
            "source": self.source,
            "is_mock": self.is_mock,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LiquidityObservation:
        """Rebuild an observation from its ``to_dict`` form (audit read-back)."""
        ts = data["timestamp"]
        return cls(
            symbol=data["symbol"],
            timestamp=(
                ts if isinstance(ts, datetime) else datetime.fromisoformat(ts)
            ),
            price=data["price"],
            bid_liquidity=data.get("bid_liquidity", 0.0),
            ask_liquidity=data.get("ask_liquidity", 0.0),
            executed_buy_volume=data.get("executed_buy_volume", 0.0),
            executed_sell_volume=data.get("executed_sell_volume", 0.0),
            source=data.get("source", ""),
            is_mock=data.get("is_mock", False),
        )
