"""
Canonical liquidity features.

A flat, named, bounded feature vector distilled from the latest observation,
the live zones and the recent event history -- the contract a heatmap, a signal
layer or a backtester consumes. Every feature is deterministic from the inputs,
documented, and confined to a stated range so nothing downstream has to guess a
scale.

These are *descriptors of liquidity behaviour*, never directional signals or
probabilities. ``0.0`` / ``None`` are honest "no reading" values, not fabricated
neutral scores.

Thresholds and weights are named constants with a stated rationale in
``analyzers.py`` -- nothing here invents a magic number; the few mappings are
linear and documented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .observation import LiquidityObservation
from .zone import LiquidityZone

#: Zone-to-price distance is reported in basis points, capped here so a zone on
#: the other side of the book doesn't dominate the vector.
_DISTANCE_CAP_BPS = 500.0


@dataclass(frozen=True, slots=True)
class LiquidityFeatures:
    """
    The canonical liquidity feature vector for one observation step.

    ``symbol`` / ``timestamp`` identify the step the features describe.
    ``is_mock`` and ``observations_seen`` carry the honesty/quality context a
    consumer needs to know how much weight to give the read.
    """

    symbol: str
    timestamp: str
    observations_seen: int
    is_mock: bool = False

    # Distance (basis points, +toward nearest zone) to the nearest active zone
    # on each book side. ``None`` when no zone exists on that side yet.
    nearest_bid_zone_distance: float | None = None
    nearest_ask_zone_distance: float | None = None

    # Resting-liquidity scores of the nearest zones on each side (0..1), and the
    # whole-book imbalance (-1..1). Mirrors the zone/observation, never invented.
    bid_liquidity_score: float = 0.0
    ask_liquidity_score: float = 0.0
    liquidity_imbalance: float = 0.0

    # Sweep pressure on each side over the feature window (0..1): how often the
    # tape swept the asks (up) vs the bids (down), normalised to observations.
    sweep_up_score: float = 0.0
    sweep_down_score: float = 0.0

    # Absorption strength on each side (0..1) from the latest absorption read.
    absorption_bid_score: float = 0.0
    absorption_ask_score: float = 0.0

    # Replenishment strength across active zones (0..1): how persistently walls
    # refill after being eaten.
    replenishment_score: float = 0.0

    # Liquidity velocity (0..1): how fast resting liquidity is being turned over
    # -- consumed+removed volume relative to displayed liquidity. High velocity
    # is a churning, contested book; low is a resting, stacked one.
    liquidity_velocity: float = 0.0

    # Persistence of the strongest active zone (0..1): how long the most durable
    # wall has stood.
    persistence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "observations_seen": self.observations_seen,
            "is_mock": self.is_mock,
            "nearest_bid_zone_distance": self.nearest_bid_zone_distance,
            "nearest_ask_zone_distance": self.nearest_ask_zone_distance,
            "bid_liquidity_score": self.bid_liquidity_score,
            "ask_liquidity_score": self.ask_liquidity_score,
            "liquidity_imbalance": self.liquidity_imbalance,
            "sweep_up_score": self.sweep_up_score,
            "sweep_down_score": self.sweep_down_score,
            "absorption_bid_score": self.absorption_bid_score,
            "absorption_ask_score": self.absorption_ask_score,
            "replenishment_score": self.replenishment_score,
            "liquidity_velocity": self.liquidity_velocity,
            "persistence_score": self.persistence_score,
        }


def _bps_distance(price: float, zone: LiquidityZone) -> float:
    """Signed basis-points distance from ``price`` to a zone's nearest edge."""
    if price > zone.upper_price:
        gap = price - zone.upper_price
    elif price < zone.lower_price:
        gap = price - zone.lower_price
    else:
        gap = 0.0
    ref = zone.midpoint if zone.midpoint > 0 else price
    return round((gap / ref) * 10_000.0, 2) if ref > 0 else 0.0


def extract_features(
    observation: LiquidityObservation,
    zones: tuple[LiquidityZone, ...],
    *,
    observations_seen: int,
    sweep_up_count: int = 0,
    sweep_down_count: int = 0,
    absorption_bid: float = 0.0,
    absorption_ask: float = 0.0,
    replenishment_score: float = 0.0,
    consumed_volume: float = 0.0,
    removed_volume: float = 0.0,
) -> LiquidityFeatures:
    """
    Distill one observation step into the canonical feature vector.

    The caller (the service) supplies the running counters the features are
    normalised against, because counts are genuinely *between-step* state.
    Everything else derives from the observation and the live zones.
    """
    price = observation.price
    bid_zones = [z for z in zones if z.side == "bid" and z.is_active]
    ask_zones = [z for z in zones if z.side == "ask" and z.is_active]

    def _nearest(zs):
        if not zs:
            return None
        return min(zs, key=lambda z: abs(z.midpoint - price))

    bid_zone = _nearest(bid_zones)
    ask_zone = _nearest(ask_zones)

    bid_dist = (
        min(_bps_distance(price, bid_zone), _DISTANCE_CAP_BPS)
        if bid_zone else None
    )
    ask_dist = (
        min(_bps_distance(price, ask_zone), _DISTANCE_CAP_BPS)
        if ask_zone else None
    )

    n = max(1, observations_seen)
    sweep_up = min(1.0, sweep_up_count / n)
    sweep_down = min(1.0, sweep_down_count / n)

    displayed = observation.total_liquidity
    velocity = (
        min(1.0, (consumed_volume + removed_volume) / displayed)
        if displayed > 0 else 0.0
    )

    persistence = max(
        (z.persistence_score for z in zones if z.is_active), default=0.0
    )

    return LiquidityFeatures(
        symbol=observation.symbol,
        timestamp=observation.timestamp.isoformat(),
        observations_seen=observations_seen,
        is_mock=observation.is_mock,
        nearest_bid_zone_distance=bid_dist,
        nearest_ask_zone_distance=ask_dist,
        bid_liquidity_score=bid_zone.liquidity_score if bid_zone else 0.0,
        ask_liquidity_score=ask_zone.liquidity_score if ask_zone else 0.0,
        liquidity_imbalance=observation.imbalance,
        sweep_up_score=round(sweep_up, 4),
        sweep_down_score=round(sweep_down, 4),
        absorption_bid_score=absorption_bid,
        absorption_ask_score=absorption_ask,
        replenishment_score=replenishment_score,
        liquidity_velocity=round(velocity, 4),
        persistence_score=persistence,
    )
