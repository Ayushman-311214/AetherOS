"""
Trading-decision value object (spec Phase 20).

A :class:`TradingDecision` is the structured, explainable product of the
decision layer: market view, setup, direction, confidence, supporting and
contradictory evidence, entry/stop/target/risk-reward/invalidation, reasoning,
uncertainty and provenance -- the spec's full decision record in one place.

It assembles; it computes nothing. The market view, direction, confidence and
recommendation are read straight off the deterministic report; the geometry
(entry, stop, target, risk/reward, invalidation) is read straight off the
report's risk assessment; the setup is the strategy reading the decision was
built from; supporting/contradictory evidence is the explanation ledger. A
decision can never be more confident than its report, and it can never reach
a broker: it is a *record* the policy/execution layers may judge, not an
instruction (the LLM reasons over it; execution stays deterministic and
policy-controlled).

The honest no-decision is first-class: when the evidence does not resolve to
a tradable side, the decision records ``direction=UNKNOWN`` with the reasons
and uncertainty stated, never a fabricated side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import Confidence, Direction, ReportRecommendation
from .explanation import EvidenceReason
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TradingDecision:
    """One structured, explainable trading decision for an instrument."""

    instrument: Instrument
    timeframe_value: str
    # The market backdrop the decision sits inside (regime/trend language).
    market_view: str
    # The strategy reading the decision was built from (id + name), if any.
    strategy_id: str | None
    strategy_name: str | None
    setup_id: str | None
    direction: Direction
    confidence: Confidence
    recommendation: ReportRecommendation
    is_actionable: bool
    supporting: tuple[EvidenceReason, ...]
    contradictory: tuple[EvidenceReason, ...]
    supporting_weight: float
    contradictory_weight: float
    net_weight: float
    # Deterministic risk geometry, lifted verbatim from the risk assessment.
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_reward_ratio: float | None
    invalidation: str
    reasoning: str
    # What could still be wrong, in plain language.
    uncertainty: tuple[str, ...]
    critic_reasons: tuple[str, ...]
    provenance: Provenance
    quality: DataQuality
    limitations: tuple[str, ...] = ()
    visual_note: str | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.market_view.strip():
            raise ValueError("A decision requires a market view.")
        if not self.reasoning.strip():
            raise ValueError("A decision requires its reasoning.")
        if not self.invalidation.strip():
            raise ValueError("A decision requires an invalidation condition.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "market_view": self.market_view,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "setup_id": self.setup_id,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "recommendation": self.recommendation.value,
            "is_actionable": self.is_actionable,
            "supporting": [r.to_dict() for r in self.supporting],
            "contradictory": [r.to_dict() for r in self.contradictory],
            "supporting_weight": self.supporting_weight,
            "contradictory_weight": self.contradictory_weight,
            "net_weight": self.net_weight,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "invalidation": self.invalidation,
            "reasoning": self.reasoning,
            "uncertainty": list(self.uncertainty),
            "critic_reasons": list(self.critic_reasons),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "limitations": list(self.limitations),
            "visual_note": self.visual_note,
            "created_at": self.created_at.isoformat(),
        }
