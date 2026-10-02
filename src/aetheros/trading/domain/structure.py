"""
Market-structure value objects.

These describe *what the price action is doing* rather than a single indicator:
swing points, support/resistance levels, the prevailing trend, and structural
signals such as a breakout. Every detection carries a confidence and the
evidence it was derived from -- the code never asserts a pattern exists without
a reason (spec section 8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import Confidence, Direction, StructureSignalType, TrendState


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    timestamp: datetime
    price: float
    kind: str  # "high" | "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "kind": self.kind,
        }


@dataclass(frozen=True, slots=True)
class Level:
    """A support or resistance level clustered from swing points."""

    price: float
    kind: str  # "support" | "resistance"
    touches: int
    confidence: Confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "kind": self.kind,
            "touches": self.touches,
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True, slots=True)
class StructureSignal:
    type: StructureSignalType
    direction: Direction
    confidence: Confidence
    reference_price: float
    observation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "reference_price": self.reference_price,
            "observation": self.observation,
        }


@dataclass(frozen=True, slots=True)
class MarketStructure:
    trend: TrendState
    trend_strength: float  # 0..1, derived, never a probability
    swings: tuple[SwingPoint, ...]
    supports: tuple[Level, ...]
    resistances: tuple[Level, ...]
    signals: tuple[StructureSignal, ...]
    higher_highs: bool
    higher_lows: bool
    lower_highs: bool
    lower_lows: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend": self.trend.value,
            "trend_strength": self.trend_strength,
            "swings": [s.to_dict() for s in self.swings],
            "supports": [lvl.to_dict() for lvl in self.supports],
            "resistances": [lvl.to_dict() for lvl in self.resistances],
            "signals": [sig.to_dict() for sig in self.signals],
            "pattern": {
                "higher_highs": self.higher_highs,
                "higher_lows": self.higher_lows,
                "lower_highs": self.lower_highs,
                "lower_lows": self.lower_lows,
            },
        }
