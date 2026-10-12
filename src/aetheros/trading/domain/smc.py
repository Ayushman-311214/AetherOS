"""
Smart Money Concepts (SMC) value objects.

These describe *where* the market left a footprint and *what price did about
it*: a break of structure (BOS) or change of character (CHoCH), the order
block or fair value gap a move originated from, a liquidity sweep, an
equal-highs/lows pool, and the premium/discount read of the active dealing
range.

Three honesty rules run through every object here (CLAUDE.md sections 5, 28):

- A detection is never asserted without the reason it was derived from --
  each carries ``evidence`` (the deterministic facts that triggered it) and a
  ``confidence`` band, which is a *label*, never a probability.
- Zones stay honest about what price did next: ``mitigated`` records that
  price traded back into the zone, ``invalidated`` that price closed through
  its far edge. Neither is guessed.
- Nothing here is a prediction or a trade decision. SMC detects and describes;
  the strategy/signal/decision layers (Phases 7+) are what interpret it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import (
    Confidence,
    Direction,
    LiquidityEventKind,
    SMCZoneKind,
    StructureBreakType,
    TrendState,
)
from .provenance import Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class StructureBreak:
    """
    A BOS or CHoCH: price closed through a previously confirmed swing point.

    ``broken_level`` is the swing price that gave way, ``broken_index`` the bar
    that swing sat on, and ``break_price`` the close that confirmed the break.
    ``trend_before`` records the structure read *at the moment of the break*,
    which is what makes BOS (with the trend) distinguishable from CHoCH
    (against it) after the fact.
    """

    kind: StructureBreakType
    direction: Direction
    index: int
    timestamp: datetime
    timeframe: str
    broken_level: float
    broken_index: int
    break_price: float
    trend_before: TrendState
    confidence: Confidence
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.broken_level <= 0 or self.break_price <= 0:
            raise ValueError("Structure break prices must be positive.")
        if not math.isfinite(self.broken_level) or not math.isfinite(self.break_price):
            raise ValueError("Structure break prices must be finite.")
        if self.broken_index >= self.index:
            raise ValueError("A break can only reference an earlier swing point.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "direction": self.direction.value,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "broken_level": self.broken_level,
            "broken_index": self.broken_index,
            "break_price": self.break_price,
            "trend_before": self.trend_before.value,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class SMCZone:
    """
    A price zone: an order block or a fair value gap.

    ``direction`` is the side the zone is expected to act from -- UP for a
    demand zone (bullish order block / bullish gap), DOWN for supply. The zone
    is the closed interval ``[bottom, top]``; both bounds are validated so a
    zone can never be inverted or non-finite.
    """

    kind: SMCZoneKind
    direction: Direction
    top: float
    bottom: float
    index: int
    timestamp: datetime
    timeframe: str
    mitigated: bool = False
    invalidated: bool = False
    mitigation_index: int | None = None
    confidence: Confidence = Confidence.LOW
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.top) or not math.isfinite(self.bottom):
            raise ValueError("Zone bounds must be finite.")
        if self.top <= self.bottom:
            raise ValueError("Zone top must be strictly above its bottom.")
        if self.mitigation_index is not None and self.mitigation_index < self.index:
            raise ValueError("A zone cannot be mitigated before it forms.")
        if self.mitigated and self.mitigation_index is None:
            raise ValueError("A mitigated zone must record the bar that did it.")
        if self.invalidated and not self.mitigated:
            raise ValueError("A zone cannot be invalidated without being touched.")

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def midpoint(self) -> float:
        return (self.top + self.bottom) / 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "direction": self.direction.value,
            "top": self.top,
            "bottom": self.bottom,
            "height": self.height,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "mitigated": self.mitigated,
            "invalidated": self.invalidated,
            "mitigation_index": self.mitigation_index,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class LiquidityEvent:
    """
    A liquidity sweep, or an equal-highs / equal-lows pool.

    For a sweep, ``level`` is the swing price that was taken and ``extreme``
    the wick that took it. For an equal-highs/lows pool, ``level`` is the mean
    of the clustered prices and ``extreme`` the outermost one.
    """

    kind: LiquidityEventKind
    direction: Direction
    level: float
    extreme: float
    index: int
    timestamp: datetime
    timeframe: str
    confidence: Confidence
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.level <= 0 or self.extreme <= 0:
            raise ValueError("Liquidity levels must be positive.")
        if not math.isfinite(self.level) or not math.isfinite(self.extreme):
            raise ValueError("Liquidity levels must be finite.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "direction": self.direction.value,
            "level": self.level,
            "extreme": self.extreme,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class DealingRange:
    """
    The active range between the most recent confirmed swing high and low.

    ``price_ratio`` is 0 at the range low and 1 at the range high, so the
    premium/discount read is a pure position within the range rather than a
    directional call. The ratio is deliberately *not* clamped: price outside
    the range is real information and must stay visible.
    """

    high: float
    low: float
    equilibrium: float
    position: str  # "premium" | "discount" | "equilibrium"
    price_ratio: float
    high_index: int
    low_index: int

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value) for value in (self.high, self.low, self.price_ratio)
        ):
            raise ValueError("Dealing-range values must be finite.")
        if self.high <= self.low:
            raise ValueError("Dealing-range high must be strictly above its low.")
        if self.position not in ("premium", "discount", "equilibrium"):
            raise ValueError(f"Unknown range position '{self.position}'.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "high": self.high,
            "low": self.low,
            "equilibrium": self.equilibrium,
            "position": self.position,
            "price_ratio": self.price_ratio,
            "high_index": self.high_index,
            "low_index": self.low_index,
        }


@dataclass(frozen=True, slots=True)
class SMCAnalysis:
    """The complete deterministic SMC read for one instrument/timeframe."""

    instrument_key: str
    timeframe: str
    last_price: float
    trend: TrendState = TrendState.UNKNOWN
    breaks: tuple[StructureBreak, ...] = ()
    zones: tuple[SMCZone, ...] = ()
    liquidity: tuple[LiquidityEvent, ...] = ()
    dealing_range: DealingRange | None = None
    provenance: Provenance | None = None
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=_utcnow)

    @property
    def mitigation_blocks(self) -> tuple[SMCZone, ...]:
        """
        Order blocks price has returned to and respected, but not closed through.

        The spec lists "Mitigation Blocks" as a concept; this is that concept
        expressed as a *view* over the detected zones rather than a second,
        shakier detector -- a mitigation block is an order block that has been
        mitigated and is still valid.
        """
        return tuple(
            zone
            for zone in self.zones
            if zone.kind is SMCZoneKind.ORDER_BLOCK
            and zone.mitigated
            and not zone.invalidated
        )

    @property
    def fair_value_gaps(self) -> tuple[SMCZone, ...]:
        return tuple(
            zone for zone in self.zones if zone.kind is SMCZoneKind.FAIR_VALUE_GAP
        )

    @property
    def order_blocks(self) -> tuple[SMCZone, ...]:
        return tuple(
            zone for zone in self.zones if zone.kind is SMCZoneKind.ORDER_BLOCK
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "last_price": self.last_price,
            "trend": self.trend.value,
            "breaks": [b.to_dict() for b in self.breaks],
            "zones": [z.to_dict() for z in self.zones],
            "liquidity": [event.to_dict() for event in self.liquidity],
            "dealing_range": (
                self.dealing_range.to_dict() if self.dealing_range else None
            ),
            # Derived views, so a caller does not have to re-filter.
            "mitigation_blocks": [z.to_dict() for z in self.mitigation_blocks],
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }
