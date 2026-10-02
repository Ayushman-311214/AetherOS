"""
The Prediction Contract value object (spec sections 8, 19, 28).

A :class:`PredictionRecord` is the auditable, content-addressed snapshot of a
single composed :class:`~aetheros.trading.domain.report.TradingReport` at the
moment it was produced. Section 8 requires every prediction to carry a fixed,
inspectable contract -- instrument, timestamp, horizon, direction, probability,
confidence, evidence, risk, invalidation, model version and data version -- so a
past prediction can always be reconstructed and, later, checked against what
actually happened. This record IS that contract, flattened to a small immutable
value object that a store can persist and an audit tool can read back.

Two honesty rules are structural here, exactly as in the report it derives from:

* **No fabricated probability.** ``probability_up`` / ``probability_down`` are
  populated only when the report surfaced a *reliable* calibrated estimate; a
  MOCK or thin read leaves them ``None`` with ``probability_reliable = False``.
  The record never invents a number the report itself refused to state
  (sections 2, 3, 6, 61).
* **A prediction is never stored as a fact.** The record keeps ``recommendation``,
  ``is_actionable`` and the data ``source_tier``/``is_mock`` verbatim, so a
  NO_TRADE on synthetic data is preserved as exactly that -- a non-actionable
  decision on mock data -- and can never later read as a confident call
  (sections 15, 28).

The record computes nothing: every field traces to the report it was built from.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # avoid a runtime import cycle; the record only reads the report
    from .report import TradingReport

_ID_PREFIX = "pred_"


def _stable_id(
    *,
    instrument_key: str,
    timeframe: str,
    created_at: datetime,
    recommendation: str,
    direction: str,
    model: str,
) -> str:
    """
    Content-addressed id for one prediction (spec section 8).

    Keyed on the full prediction *timestamp* (not just the date): two reports
    for the same instrument at different moments are genuinely distinct
    predictions and must not collide, while rebuilding the record from the same
    report is deterministic and yields the same id.
    """
    payload = "|".join(
        (
            instrument_key,
            timeframe.strip().lower(),
            created_at.isoformat(),
            recommendation.strip().lower(),
            direction.strip().lower(),
            model.strip().lower(),
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"{_ID_PREFIX}{digest[:16]}"


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """The auditable section-8 contract for one produced trading report."""

    # Identity / instrument
    id: str
    instrument_key: str
    symbol: str
    exchange: str | None
    asset_class: str
    name: str | None

    # When / what horizon
    timeframe: str
    created_at: datetime
    horizon_bars: int

    # The call itself (verbatim from the report -- never upgraded to a fact)
    recommendation: str
    is_actionable: bool
    direction: str
    confidence: str
    directional_score: float

    # Probability: populated only from a *reliable* calibrated estimate
    probability_reliable: bool
    probability_up: float | None
    probability_down: float | None

    # Risk geometry & the condition that would invalidate the call
    risk_reward_ratio: float | None
    overall_risk: str | None
    invalidation: str

    # Provenance -- the "data version" half of the contract
    source_tier: str
    is_mock: bool

    # Model version + how much evidence stood behind the call
    model_pipeline: str
    evidence_count: int

    limitations: tuple[str, ...] = ()

    @property
    def is_mock_prediction(self) -> bool:
        """A prediction resting on mock data can never be treated as reliable."""
        return self.is_mock

    @classmethod
    def from_report(cls, report: "TradingReport") -> "PredictionRecord":
        """
        Flatten a composed :class:`TradingReport` into its section-8 contract.

        Reads only from the report and its sub-objects -- it invents nothing, and
        it mirrors the report's own honesty gate on probability: a value is
        carried through only when the estimate passed its reliability gate.
        """
        instrument = report.instrument

        prob = report.probability
        prob_reliable = prob is not None and prob.is_reliable
        prob_up: float | None = None
        prob_down: float | None = None
        if prob_reliable:
            probabilities = prob.to_dict().get("probability") or {}
            prob_up = probabilities.get("up")
            prob_down = probabilities.get("down")

        risk_dict = report.risk.to_dict()

        return cls(
            id=_stable_id(
                instrument_key=instrument.key,
                timeframe=report.analysis.timeframe_value,
                created_at=report.created_at,
                recommendation=report.recommendation.value,
                direction=report.direction.value,
                model=report.pipeline_version,
            ),
            instrument_key=instrument.key,
            symbol=instrument.symbol,
            exchange=instrument.exchange,
            asset_class=instrument.asset_class,
            name=instrument.name,
            timeframe=report.analysis.timeframe_value,
            created_at=report.created_at,
            horizon_bars=report.horizon,
            recommendation=report.recommendation.value,
            is_actionable=report.is_actionable,
            direction=report.direction.value,
            confidence=report.confidence.value,
            directional_score=report.analysis.directional_score,
            probability_reliable=prob_reliable,
            probability_up=prob_up,
            probability_down=prob_down,
            risk_reward_ratio=risk_dict.get("risk_reward_ratio"),
            overall_risk=risk_dict.get("overall_risk"),
            invalidation=report.risk.invalidation,
            source_tier=report.provenance.tier.value,
            is_mock=report.provenance.is_mock,
            model_pipeline=report.pipeline_version,
            evidence_count=len(report.analysis.evidence),
            limitations=tuple(report.limitations),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument": {
                "key": self.instrument_key,
                "symbol": self.symbol,
                "exchange": self.exchange,
                "asset_class": self.asset_class,
                "name": self.name,
            },
            "timeframe": self.timeframe,
            "created_at": self.created_at.isoformat(),
            "horizon_bars": self.horizon_bars,
            "recommendation": self.recommendation,
            "is_actionable": self.is_actionable,
            "signal": {
                "direction": self.direction,
                "confidence": self.confidence,
                "directional_score": self.directional_score,
            },
            "probability": (
                {"up": self.probability_up, "down": self.probability_down}
                if self.probability_reliable
                else None
            ),
            "probability_reliable": self.probability_reliable,
            "risk": {
                "risk_reward_ratio": self.risk_reward_ratio,
                "overall_risk": self.overall_risk,
                "invalidation": self.invalidation,
            },
            "provenance": {"tier": self.source_tier, "is_mock": self.is_mock},
            "model": {"pipeline": self.model_pipeline},
            "evidence_count": self.evidence_count,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionRecord":
        """
        Rebuild a record from its ``to_dict`` form (audit read-back).

        The inverse of :meth:`to_dict`; a persistent store serialises with the
        former and reconstructs with this, so a written prediction round-trips
        without loss.
        """
        instrument = data["instrument"]
        signal = data["signal"]
        probability = data.get("probability") or {}
        risk = data["risk"]
        provenance = data["provenance"]
        created_at = data["created_at"]
        return cls(
            id=data["id"],
            instrument_key=instrument["key"],
            symbol=instrument["symbol"],
            exchange=instrument.get("exchange"),
            asset_class=instrument.get("asset_class", "equity"),
            name=instrument.get("name"),
            timeframe=data["timeframe"],
            created_at=(
                created_at
                if isinstance(created_at, datetime)
                else datetime.fromisoformat(created_at)
            ),
            horizon_bars=data["horizon_bars"],
            recommendation=data["recommendation"],
            is_actionable=data["is_actionable"],
            direction=signal["direction"],
            confidence=signal["confidence"],
            directional_score=signal["directional_score"],
            probability_reliable=data.get("probability_reliable", False),
            probability_up=probability.get("up"),
            probability_down=probability.get("down"),
            risk_reward_ratio=risk.get("risk_reward_ratio"),
            overall_risk=risk.get("overall_risk"),
            invalidation=risk.get("invalidation", ""),
            source_tier=provenance["tier"],
            is_mock=provenance["is_mock"],
            model_pipeline=data["model"]["pipeline"],
            evidence_count=data.get("evidence_count", 0),
            limitations=tuple(data.get("limitations", ())),
        )
