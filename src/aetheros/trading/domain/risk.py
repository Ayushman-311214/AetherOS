"""
Risk-assessment value objects.

A :class:`RiskAssessment` turns a deterministic :class:`TradingAnalysis` into a
concrete, auditable trade plan: entry, a volatility- or structure-based stop, a
target, the resulting risk/reward, an optional position size, and an explicit
invalidation condition. It is deliberately NOT a recommendation to trade -- it
is the risk geometry a human (or a later decision/critic layer) needs to judge
whether a setup is worth taking, and it never fabricates a level it did not
derive (spec sections 5, 8, 28, 61). Nothing here requires an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Direction, RiskBand
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Deterministic risk geometry for one directional trade idea."""

    instrument: Instrument
    direction: Direction
    entry: float

    stop_loss: float | None
    stop_method: str  # "atr" | "structural" | "none"
    target: float | None
    target_method: str  # "structural" | "projected" | "none"
    targets: tuple[float, ...]  # laddered structural targets, if any

    risk_per_unit: float | None
    reward_per_unit: float | None
    risk_reward_ratio: float | None
    stop_distance_pct: float | None

    atr: float | None
    atr_pct: float | None
    volatility_risk: RiskBand
    overall_risk: RiskBand

    account_equity: float | None
    risk_pct: float | None
    risk_amount: float | None
    position_size: float | None
    position_notional: float | None

    invalidation: str
    rationale: tuple[str, ...]
    quality: DataQuality
    provenance: Provenance
    is_actionable: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "stop_method": self.stop_method,
            "target": self.target,
            "target_method": self.target_method,
            "targets": list(self.targets),
            "risk_per_unit": self.risk_per_unit,
            "reward_per_unit": self.reward_per_unit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "stop_distance_pct": self.stop_distance_pct,
            "atr": self.atr,
            "atr_pct": self.atr_pct,
            "volatility_risk": self.volatility_risk.value,
            "overall_risk": self.overall_risk.value,
            "account_equity": self.account_equity,
            "risk_pct": self.risk_pct,
            "risk_amount": self.risk_amount,
            "position_size": self.position_size,
            "position_notional": self.position_notional,
            "invalidation": self.invalidation,
            "rationale": list(self.rationale),
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "is_actionable": self.is_actionable,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
