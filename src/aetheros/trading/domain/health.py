"""
Trading-health value objects (spec Phase 2 -- trading health).

The desk needs one honest answer to *"may we trade right now?"* that folds in
everything Phase 2 can see: data quality, risk-limit state, broker
reachability, reconciliation drift, kill switches and persistence errors.
:class:`TradingHealth` is that answer -- a three-band verdict, never a
probability and never a guess.

* ``SAFE``     -- every input is present and inside its bounds.
* ``DEGRADED`` -- trading is possible but impaired: a degraded feed, a
  reconciliation mismatch, an approaching risk limit. Trade with care.
* ``BLOCKED``  -- a hard stop is in force: a kill switch is tripped, the data
  is unusable, or a hard input cannot be read at all.

The band is *derived*, never asserted: the service computes the worst signal
present and reports it. A health report that cannot see a required input does
not default to SAFE -- an unreadable broker or unknown data quality is itself
evidence of DEGRADED, and a tripped kill switch forces BLOCKED outright.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


class HealthBand(str, Enum):
    """The aggregate trading-health verdict."""

    SAFE = "safe"
    DEGRADED = "degraded"
    BLOCKED = "blocked"

    @property
    def severity(self) -> int:
        """Ordinal for worst-of aggregation."""
        return {HealthBand.SAFE: 0, HealthBand.DEGRADED: 1, HealthBand.BLOCKED: 2}[self]


@dataclass(frozen=True, slots=True)
class HealthSignal:
    """One input folded into the health verdict: a band and why."""

    source: str
    band: HealthBand
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "band": self.band.value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class TradingHealth:
    """
    The desk-level health verdict: the worst band across all inputs.

    ``signals`` is the full per-input breakdown so the verdict is auditable --
    a reader sees not just that the desk is DEGRADED but *which* inputs drove
    it there and which are still clean.
    """

    band: HealthBand
    signals: tuple[HealthSignal, ...]
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_safe(self) -> bool:
        return self.band is HealthBand.SAFE

    @property
    def reasons(self) -> tuple[str, ...]:
        """The details of every non-SAFE signal, worst first."""
        bad = [s for s in self.signals if s.band is not HealthBand.SAFE]
        bad.sort(key=lambda s: s.band.severity, reverse=True)
        return tuple(s.detail for s in bad)

    def to_dict(self) -> dict[str, Any]:
        return {
            "band": self.band.value,
            "is_safe": self.is_safe,
            "signals": [s.to_dict() for s in self.signals],
            "reasons": list(self.reasons),
            "created_at": self.created_at.isoformat(),
        }
