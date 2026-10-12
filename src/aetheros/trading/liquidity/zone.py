"""
The canonical liquidity zone.

A :class:`LiquidityZone` is a band of prices where resting liquidity has
clustered persistently enough to be worth tracking across observations. Unlike
the SMC ``SMCZone`` (an order block / fair-value-gap detected off candle
geometry) this is a *book* zone: it is born from unusually large or clustered
resting liquidity, and it ages by what the book and the tape do to it over
time -- touches, sweeps, replenishments, weakening, invalidation.

The model is honest about two things the spec insists on:

* **Biggest is not automatically important.** A zone's ``liquidity_score`` is
  relative to the liquidity seen around it, and ``persistence_score`` rewards
  how *long* it has stood, not how large a single order was. A zone that formed
  on one fat order and vanished is a weak zone, and the scores say so.
* **Status is observed, never inferred.** ``touched`` / ``swept`` /
  ``invalidated`` record what price and the tape actually did to the zone; the
  model never claims a zone "will hold" or "will be swept".

Zones are produced by ``detection.ZoneDetector`` and maintained by
``zones.ZoneTracker``; both are pure functions of the stream they are fed.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(__import__("datetime").timezone.utc)


# Lifecycle status of a zone. ``active`` -> touched -> swept/invalidated are the
# honest transitions a tracked zone can take.
ZONE_ACTIVE = "active"
ZONE_TOUCHED = "touched"
ZONE_SWEPT = "swept"
ZONE_INVALIDATED = "invalidated"

_ZONE_STATUSES = frozenset(
    {ZONE_ACTIVE, ZONE_TOUCHED, ZONE_SWEPT, ZONE_INVALIDATED}
)


def _stable_zone_id(
    *, symbol: str, side: str, lower_price: float, upper_price: float
) -> str:
    """
    Content-addressed id for a zone.

    Keyed on the instrument, the side and the price band -- *not* on time -- so
    the same resting-liquidity cluster re-detected across snapshots resolves to
    the same zone identity, which is exactly what the tracker needs to count
    persistence, touches and sweeps against one stable zone (and what lets an
    emitted ``LiquidityZoneCreated`` dedupe).
    """
    payload = "|".join(
        (
            symbol,
            side,
            f"{lower_price:.8f}",
            f"{upper_price:.8f}",
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"lqz_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class LiquidityZone:
    """
    A band of resting liquidity worth tracking over time.

    ``side`` is which book side the zone sits on: ``"bid"`` (resting bids, a
    demand-side wall) or ``"ask"`` (resting asks, supply). ``lower_price`` /
    ``upper_price`` bound the band; both are validated finite and ordered so a
    zone can never be inverted. A single resting level is a degenerate zone with
    ``lower == upper`` -- a one-level wall is still a wall, so equal bounds are
    allowed (only a genuinely inverted band is rejected).
    """

    symbol: str
    side: str  # "bid" | "ask"
    lower_price: float
    upper_price: float

    # The two scores the spec wants kept distinct: how much liquidity it shows
    # relative to its surroundings (size is not importance) and how long it has
    # persisted (a flash-in-the-pan wall is a weak zone).
    liquidity_score: float = 0.0       # 0..1 relative resting size
    persistence_score: float = 0.0     # 0..1 how long it has stood

    # Lifecycle bookkeeping, all observed over the tracked stream.
    first_seen: datetime = field(default_factory=_utcnow)
    last_seen: datetime = field(default_factory=_utcnow)
    touch_count: int = 0          # observations where price sat inside the band
    sweep_count: int = 0          # times the zone was swept (consumed/cleared)
    replenishment_count: int = 0  # times liquidity reappeared after consumption
    status: str = ZONE_ACTIVE

    source: str = ""
    is_mock: bool = False
    id: str = ""

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("A liquidity zone requires a symbol.")
        if self.side not in ("bid", "ask"):
            raise ValueError("Liquidity zone side must be 'bid' or 'ask'.")
        if not math.isfinite(self.lower_price) or not math.isfinite(
            self.upper_price
        ):
            raise ValueError("Liquidity zone bounds must be finite.")
        if self.upper_price < self.lower_price:
            raise ValueError(
                "Liquidity zone upper bound cannot be below its lower bound."
            )
        for name in ("first_seen", "last_seen"):
            ts = getattr(self, name)
            if ts.tzinfo is None or ts.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware.")
        if self.last_seen < self.first_seen:
            raise ValueError("A zone's last_seen cannot precede its first_seen.")
        for name in (
            "liquidity_score",
            "persistence_score",
            "touch_count",
            "sweep_count",
            "replenishment_count",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative.")
        if self.status not in _ZONE_STATUSES:
            raise ValueError(f"Unknown liquidity-zone status '{self.status}'.")
        if not self.id:
            object.__setattr__(
                self,
                "id",
                _stable_zone_id(
                    symbol=self.symbol,
                    side=self.side,
                    lower_price=self.lower_price,
                    upper_price=self.upper_price,
                ),
            )

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    @property
    def midpoint(self) -> float:
        return (self.lower_price + self.upper_price) / 2.0

    @property
    def height(self) -> float:
        return self.upper_price - self.lower_price

    def contains(self, price: float) -> bool:
        return self.lower_price <= price <= self.upper_price

    def overlaps(self, other: LiquidityZone, *, gap: float = 0.0) -> bool:
        """Whether two zones touch or come within ``gap`` of each other."""
        return not (
            self.lower_price > other.upper_price + gap
            or other.lower_price > self.upper_price + gap
        )

    @property
    def is_active(self) -> bool:
        """Whether the zone is still standing (not swept/invalidated)."""
        return self.status in (ZONE_ACTIVE, ZONE_TOUCHED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "midpoint": self.midpoint,
            "liquidity_score": self.liquidity_score,
            "persistence_score": self.persistence_score,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "touch_count": self.touch_count,
            "sweep_count": self.sweep_count,
            "replenishment_count": self.replenishment_count,
            "status": self.status,
            "source": self.source,
            "is_mock": self.is_mock,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LiquidityZone:
        def _ts(value):
            return value if isinstance(value, datetime) else datetime.fromisoformat(value)
        return cls(
            id=data.get("id", ""),
            symbol=data["symbol"],
            side=data["side"],
            lower_price=data["lower_price"],
            upper_price=data["upper_price"],
            liquidity_score=data.get("liquidity_score", 0.0),
            persistence_score=data.get("persistence_score", 0.0),
            first_seen=_ts(data["first_seen"]),
            last_seen=_ts(data["last_seen"]),
            touch_count=data.get("touch_count", 0),
            sweep_count=data.get("sweep_count", 0),
            replenishment_count=data.get("replenishment_count", 0),
            status=data.get("status", ZONE_ACTIVE),
            source=data.get("source", ""),
            is_mock=data.get("is_mock", False),
        )
