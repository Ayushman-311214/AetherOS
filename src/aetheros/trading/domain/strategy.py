"""
Strategy-layer value objects (spec Phase 7).

The strategy layer *interprets* the deterministic reads that the analysis, SMC
and ICT layers produce: "structure is up, price is in discount, a bullish order
block is unmitigated" becomes an auditable directional **setup**, carrying the
named rules that fired and the evidence behind them.

Two boundaries are drawn deliberately here and enforced by the models:

**A setup is not risk geometry.** Entry, stop, target, position size and the
risk/reward ratio are derived deterministically by :class:`RiskService` from the
same analysis. A strategy that invented its own stop would be a second,
contradictory risk engine, so :class:`StrategySetup` carries only the
*structural* level that voids the thesis -- never a stop, a target or a size.

**A setup is not a signal and not an order.** ``TradeSignal`` is the evidence-
backed proposed *action* the signal layer emits; a setup is the reading that
action is built from. Nothing here can reach a broker.

A setup is always directional. The honest "no trade" outcome is the *absence*
of a setup, carried by :class:`StrategyEvaluation` with the failed rules still
recorded -- never a SIDEWAYS setup manufactured to fill the slot (sections 28,
33).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import (
    Confidence,
    Direction,
    OptimizationObjective,
    StrategyCategory,
)
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _stable_setup_id(
    *,
    instrument_key: str,
    strategy_id: str,
    timeframe: str,
    direction: str,
    entry_reference: float,
    invalidation_level: float,
) -> str:
    """
    Content-addressed id: the same setup computed twice gets the same id.

    Deliberately excludes the wall clock but *includes* the prices, because a
    setup read at a different entry or invalidation is a different setup --
    that is the property an audit trail needs, and it mirrors the stable ids
    :class:`Evidence` uses.
    """
    payload = "|".join(
        (
            instrument_key,
            strategy_id,
            timeframe,
            direction,
            f"{entry_reference:.8f}",
            f"{invalidation_level:.8f}",
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"su_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class StrategyRuleMatch:
    """
    One named condition a strategy evaluated, and what it actually observed.

    Failed rules are recorded alongside satisfied ones rather than dropped:
    hiding the conditions that did *not* hold is exactly the evidence
    manipulation section 28 forbids, and it is what makes a setup explainable
    ("why was this generated?" / "why was this not?").
    """

    rule: str
    satisfied: bool
    detail: str
    value: float | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        if not self.rule.strip():
            raise ValueError("A strategy rule needs a name.")
        if not self.detail.strip():
            raise ValueError("A strategy rule needs a description of what it saw.")
        for label, value in (("value", self.value), ("threshold", self.threshold)):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"A strategy rule's {label} must be finite.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "satisfied": self.satisfied,
            "detail": self.detail,
            "value": self.value,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class StrategySetup:
    """
    A directional, evidence-backed reading from one strategy.

    It states *which side* and *why*, the price it was read at, and the
    structural level that would prove it wrong. It states no stop, no target and
    no size -- those are :class:`RiskService`'s deterministic output, and
    duplicating them here would be a second risk engine disagreeing with the
    first.
    """

    instrument: Instrument
    strategy_id: str
    strategy_name: str
    category: StrategyCategory
    timeframe: str
    direction: Direction  # UP or DOWN only; there is no SIDEWAYS setup
    confidence: Confidence
    entry_reference: float
    invalidation_level: float
    rules: tuple[StrategyRuleMatch, ...]
    evidence: tuple[Evidence, ...]
    reasoning: str
    quality: DataQuality
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)
    setup_id: str = ""

    def __post_init__(self) -> None:
        if not self.instrument.key.strip():
            raise ValueError("A setup requires an instrument.")
        if not self.strategy_id.strip() or not self.strategy_name.strip():
            raise ValueError("A setup requires a strategy id and name.")
        if not self.timeframe.strip():
            raise ValueError("A setup requires a timeframe.")
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError(
                "A setup must be directional (UP or DOWN); no setup is the "
                "honest answer when there is no edge."
            )
        for label, value in (
            ("entry_reference", self.entry_reference),
            ("invalidation_level", self.invalidation_level),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"A setup's {label} must be a finite positive price.")
        if self.direction is Direction.UP:
            if self.invalidation_level >= self.entry_reference:
                raise ValueError(
                    "A bullish setup's invalidation must sit below its entry."
                )
        elif self.invalidation_level <= self.entry_reference:
            raise ValueError(
                "A bearish setup's invalidation must sit above its entry."
            )
        if not self.reasoning.strip():
            raise ValueError("A setup must explain itself.")
        if not any(rule.satisfied for rule in self.rules):
            raise ValueError("A setup must record at least one satisfied rule.")
        if not self.setup_id:
            object.__setattr__(
                self,
                "setup_id",
                _stable_setup_id(
                    instrument_key=self.instrument.key,
                    strategy_id=self.strategy_id,
                    timeframe=self.timeframe,
                    direction=self.direction.value,
                    entry_reference=self.entry_reference,
                    invalidation_level=self.invalidation_level,
                ),
            )

    @property
    def risk_distance(self) -> float:
        """How far price must travel to invalidate the thesis, per unit."""
        return abs(self.entry_reference - self.invalidation_level)

    @property
    def satisfied_rules(self) -> tuple[StrategyRuleMatch, ...]:
        return tuple(rule for rule in self.rules if rule.satisfied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "setup_id": self.setup_id,
            "instrument": self.instrument.to_dict(),
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "category": self.category.value,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "entry_reference": self.entry_reference,
            "invalidation_level": self.invalidation_level,
            "risk_distance": self.risk_distance,
            "rules": [rule.to_dict() for rule in self.rules],
            "evidence": [item.to_dict() for item in self.evidence],
            "reasoning": self.reasoning,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    """
    What one strategy made of one context -- a setup, or an explained nothing.

    ``setup is None`` is a first-class, useful result: the rules are still
    reported, so "this strategy found no setup, because breadth was 14 (< 20)"
    is as auditable as a firing. A strategy that could not evaluate at all says
    so in ``limitations`` rather than returning an empty success.
    """

    strategy_id: str
    strategy_name: str
    category: StrategyCategory
    timeframe: str
    rules: tuple[StrategyRuleMatch, ...] = ()
    setup: StrategySetup | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.strategy_id.strip() or not self.strategy_name.strip():
            raise ValueError("An evaluation requires a strategy id and name.")
        if not self.timeframe.strip():
            raise ValueError("An evaluation requires a timeframe.")
        if self.setup is not None and self.setup.strategy_id != self.strategy_id:
            raise ValueError("An evaluation's setup must come from that strategy.")

    @property
    def fired(self) -> bool:
        return self.setup is not None

    @property
    def direction(self) -> Direction:
        """The side this strategy took, or UNKNOWN when it found no setup."""
        return self.setup.direction if self.setup else Direction.UNKNOWN

    @property
    def failed_rules(self) -> tuple[StrategyRuleMatch, ...]:
        return tuple(rule for rule in self.rules if not rule.satisfied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "category": self.category.value,
            "timeframe": self.timeframe,
            "fired": self.fired,
            "direction": self.direction.value,
            "rules": [rule.to_dict() for rule in self.rules],
            "setup": self.setup.to_dict() if self.setup else None,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class StrategyComparison:
    """
    Several strategies' evaluations of the *same* context, compared.

    Disagreement is reported, never averaged away: ``consensus`` is UNKNOWN
    whenever the firing strategies split, and every dissenting id is listed. A
    comparison over zero firing strategies is a valid, honest result -- it means
    no strategy found a setup, which is the system's "insufficient evidence".
    """

    instrument_key: str
    timeframe: str
    evaluations: tuple[StrategyEvaluation, ...]
    consensus: Direction
    agreement: float | None  # share of *firing* setups on the consensus side
    bullish: int
    bearish: int
    dissenting: tuple[str, ...]
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.instrument_key.strip() or not self.timeframe.strip():
            raise ValueError("A comparison requires an instrument and timeframe.")
        if self.bullish < 0 or self.bearish < 0:
            raise ValueError("A comparison's counts cannot be negative.")
        if self.agreement is not None and not 0.0 <= self.agreement <= 1.0:
            raise ValueError("A comparison's agreement must lie within 0 and 1.")

    @property
    def firing(self) -> tuple[StrategyEvaluation, ...]:
        return tuple(item for item in self.evaluations if item.fired)

    @property
    def setup_count(self) -> int:
        return len(self.firing)

    @property
    def is_unanimous(self) -> bool:
        """
        Whether every strategy in the panel took a side, and the same side.

        Deliberately requires *all* of them to have fired. One strategy firing
        alone has no dissenters, and calling that "unanimous" would dress a
        single opinion up as a panel verdict -- the opposite of what this whole
        object exists to distinguish.
        """
        return (
            self.consensus is not Direction.UNKNOWN
            and not self.dissenting
            and self.setup_count == len(self.evaluations)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "evaluations": [item.to_dict() for item in self.evaluations],
            "setup_count": self.setup_count,
            "consensus": self.consensus.value,
            "agreement": self.agreement,
            "bullish": self.bullish,
            "bearish": self.bearish,
            "dissenting": list(self.dissenting),
            "is_unanimous": self.is_unanimous,
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ParameterCandidate:
    """One parameter set's measured performance over a walk-forward backtest."""

    strategy_id: str
    parameters: tuple[tuple[str, Any], ...]
    score: float | None
    directional_accuracy: float | None
    cumulative_return: float | None
    max_drawdown: float | None
    sharpe: float | None
    directional_calls: int
    is_reliable: bool
    is_baseline: bool = False

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("A parameter candidate requires a strategy id.")
        keys = [key for key, _ in self.parameters]
        if any(not key.strip() for key in keys) or len(keys) != len(set(keys)):
            raise ValueError("Parameter keys must be non-empty and unique.")
        if self.directional_calls < 0:
            raise ValueError("directional_calls cannot be negative.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "parameters": dict(self.parameters),
            "score": self.score,
            "directional_accuracy": self.directional_accuracy,
            "cumulative_return": self.cumulative_return,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "directional_calls": self.directional_calls,
            "is_reliable": self.is_reliable,
            "is_baseline": self.is_baseline,
        }


@dataclass(frozen=True, slots=True)
class ParameterSearch:
    """
    The result of a deterministic parameter search over one strategy.

    ``best`` is the highest-scoring *reliable* candidate, or None when none
    qualified -- a search that produced no trustworthy winner says so rather
    than crowning the luckiest parameter set on a thin or mock sample. The
    strategy's configured defaults are always included as ``baseline`` so an
    "optimised" set can be judged against what it replaced.
    """

    strategy_id: str
    objective: OptimizationObjective
    baseline: ParameterCandidate
    candidates: tuple[ParameterCandidate, ...]
    best: ParameterCandidate | None
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("A parameter search requires a strategy id.")
        if self.baseline.strategy_id != self.strategy_id:
            raise ValueError("A search's baseline must come from that strategy.")
        if any(c.strategy_id != self.strategy_id for c in self.candidates):
            raise ValueError("A search's candidates must come from that strategy.")

    @property
    def improved(self) -> bool:
        """Whether a reliable winner beat the configured baseline."""
        if self.best is None:
            return False
        if self.baseline.score is None or self.best.score is None:
            return False
        return self.best.score > self.baseline.score

    def ranked(self) -> tuple[ParameterCandidate, ...]:
        """Candidates best-first on the objective, unreliable ones last."""
        return tuple(
            sorted(
                self.candidates,
                key=lambda c: (
                    not c.is_reliable,
                    -(c.score if c.score is not None else float("-inf")),
                ),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "objective": self.objective.value,
            "baseline": self.baseline.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
            "best": self.best.to_dict() if self.best else None,
            "improved": self.improved,
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
