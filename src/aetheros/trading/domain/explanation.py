"""
Signal-explanation value object.

An :class:`Explanation` answers the spec's "explain why a signal was generated"
requirement (CLAUDE.md section 1) over a finished :class:`TradingReport`. It
consolidates *every* piece of evidence the report gathered -- the core technical
/ structure / volume evidence AND the one evidence item each fused context layer
contributes (news, fundamentals, relative strength, anomaly, historical
analogue, macro, multi-timeframe, divergence) -- into a single, de-duplicated,
direction-grouped ledger, and summarises how the agreeing and opposing weight
nets out behind the recommendation.

It is pure synthesis of what the report already produced: it introduces no new
number and no new signal (sections 5, 28). Only *reliable* (usable, non-mock,
observed/calculated/detected) evidence contributes to the net weight; unreliable
and mock items are counted but never allowed to tip the explanation, so a
MOCK-data report explains itself as the NO_TRADE it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction, ReportRecommendation
from .instrument import Instrument


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class EvidenceReason:
    """One line of the consolidated ledger (a compact view of an Evidence item)."""

    detail: str
    type: str
    direction: Direction
    weight: float
    is_reliable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "detail": self.detail,
            "type": self.type,
            "direction": self.direction.value,
            "weight": self.weight,
            "is_reliable": self.is_reliable,
        }


@dataclass(frozen=True, slots=True)
class Explanation:
    """A deterministic, read-only explanation of a report's recommendation."""

    instrument: Instrument
    timeframe_value: str
    direction: Direction
    recommendation: ReportRecommendation
    confidence: Confidence
    is_actionable: bool
    supporting: tuple[EvidenceReason, ...]  # reliable evidence agreeing, strongest first
    opposing: tuple[EvidenceReason, ...]  # reliable evidence against, strongest first
    supporting_weight: float
    opposing_weight: float
    reliable_evidence_count: int
    total_evidence_count: int
    critic_reasons: tuple[str, ...]
    summary: str
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def net_weight(self) -> float:
        return round(self.supporting_weight - self.opposing_weight, 6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "direction": self.direction.value,
            "recommendation": self.recommendation.value,
            "confidence": self.confidence.value,
            "is_actionable": self.is_actionable,
            "summary": self.summary,
            "supporting": [r.to_dict() for r in self.supporting],
            "opposing": [r.to_dict() for r in self.opposing],
            "supporting_weight": self.supporting_weight,
            "opposing_weight": self.opposing_weight,
            "net_weight": self.net_weight,
            "reliable_evidence_count": self.reliable_evidence_count,
            "total_evidence_count": self.total_evidence_count,
            "critic_reasons": list(self.critic_reasons),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
