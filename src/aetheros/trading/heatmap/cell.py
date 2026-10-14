"""
The canonical heatmap cell.

A :class:`HeatmapCell` is one (time-bucket, price-bucket) bin of the grid. It
aggregates whatever the stream contributed inside that bin: the resting
liquidity the book showed there, the aggressive flow that printed there, and
the behavioural signals the liquidity engine attributed to it (persistence,
consumption, replenishment, sweep, absorption, pressure).

Two honesty rules run through it:

* **Measured vs derived are kept separable.** The resting/executed volumes are
  *measured* (they came straight off the book/prints); the behavioural scores
  are *derived* (the engine computed them). A consumer must never read a
  derived score as a raw fact, and ``is_mock`` marks a cell built on synthetic
  data so it can never be drawn as real.
* **None of it is a decision.** ``pressure_score``, ``sweep_score`` and the
  rest are descriptive quantities. ``None``/``0.0`` are honest "no reading"
  values, not fabricated neutral fills -- a cell with nothing is shown as
  nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def _nn(value: float, name: str) -> float:
    """Non-negative finite check; returns the value."""
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number.")
    return value


@dataclass(frozen=True, slots=True)
class HeatmapCell:
    """
    One time x price bin of aggregated liquidity behaviour.

    ``timestamp`` is the bucket's *start* time (the bin the values fell into,
    not the wall clock); ``price`` is the bucket's lower price bound. The two
    resolution fields let a consumer reconstruct the bin's extent.
    """

    timestamp: str          # ISO; bin start time
    price: float            # bin lower price bound

    # Resting liquidity shown inside the bin (measured).
    bid_intensity: float = 0.0
    ask_intensity: float = 0.0

    # Aggressive flow printed inside the bin (measured).
    executed_buy_volume: float = 0.0
    executed_sell_volume: float = 0.0

    # Behavioural scores the engine attributed to the bin (derived, 0..1).
    persistence: float = 0.0
    consumption: float = 0.0
    replenishment: float = 0.0
    sweep_score: float = 0.0
    absorption_score: float = 0.0
    pressure_score: float = 0.0

    # Binning + honesty context.
    time_span_seconds: float = 0.0
    price_span: float = 0.0
    sample_count: int = 0   # observations that fed this cell
    is_mock: bool = False

    def __post_init__(self) -> None:
        if not self.timestamp.strip():
            raise ValueError("A heatmap cell requires a timestamp.")
        if not math.isfinite(self.price) or self.price < 0:
            raise ValueError("Heatmap cell price must be finite and >= 0.")
        _nn(self.bid_intensity, "bid_intensity")
        _nn(self.ask_intensity, "ask_intensity")
        _nn(self.executed_buy_volume, "executed_buy_volume")
        _nn(self.executed_sell_volume, "executed_sell_volume")
        for name in (
            "persistence",
            "consumption",
            "replenishment",
            "sweep_score",
            "absorption_score",
            "pressure_score",
        ):
            v = getattr(self, name)
            if not math.isfinite(v) or v < 0 or v > 1.0:
                raise ValueError(f"{name} must be in [0, 1].")
        if self.sample_count < 0:
            raise ValueError("sample_count cannot be negative.")

    # ------------------------------------------------------------------
    # Derived quantities (computed, never stored -- cannot drift)
    # ------------------------------------------------------------------

    @property
    def total_intensity(self) -> float:
        """Total resting liquidity in the bin (bid + ask)."""
        return self.bid_intensity + self.ask_intensity

    @property
    def net_flow(self) -> float:
        """
        Signed executed flow in ``[-1, 1]``.

        ``(buy - sell) / (buy + sell)``: positive is buyer-initiated. Computed
        from the measured volumes so it can never disagree with them.
        """
        total = self.executed_buy_volume + self.executed_sell_volume
        if total <= 0:
            return 0.0
        return (self.executed_buy_volume - self.executed_sell_volume) / total

    @property
    def imbalance(self) -> float:
        """
        Signed resting imbalance in ``[-1, 1]``.

        ``(bid - ask) / (bid + ask)``: the resting-liquidity balance, distinct
        from the executed ``net_flow``.
        """
        total = self.total_intensity
        if total <= 0:
            return 0.0
        return (self.bid_intensity - self.ask_intensity) / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "price": self.price,
            "bid_intensity": self.bid_intensity,
            "ask_intensity": self.ask_intensity,
            "total_intensity": self.total_intensity,
            "executed_buy_volume": self.executed_buy_volume,
            "executed_sell_volume": self.executed_sell_volume,
            "net_flow": self.net_flow,
            "imbalance": self.imbalance,
            "persistence": self.persistence,
            "consumption": self.consumption,
            "replenishment": self.replenishment,
            "sweep_score": self.sweep_score,
            "absorption_score": self.absorption_score,
            "pressure_score": self.pressure_score,
            "time_span_seconds": self.time_span_seconds,
            "price_span": self.price_span,
            "sample_count": self.sample_count,
            "is_mock": self.is_mock,
        }
