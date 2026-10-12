"""
The strategy contract (spec Phase 7).

A strategy is a named, deterministic interpretation of a
:class:`StrategyContext`: a fixed set of conditions, evaluated against reads
that already exist, that either describes a directional setup or does not. It
fetches nothing, computes no indicators, detects no structure, and -- most
importantly -- **places no stop, target or size**. That geometry belongs to
:class:`~aetheros.trading.services.risk_service.RiskService`, which derives it
deterministically from the same analysis; a strategy that invented its own stop
would be a second risk engine quietly disagreeing with the first.

The contract is deliberately one method wide. :meth:`RuleBasedStrategy.rules`
reports *every* condition it examined with the value it observed and the
threshold it compared against, satisfied or not -- the failed ones included,
because a "why did this not fire?" is as much a part of an auditable system as a
"why did it?" (CLAUDE.md section 28). :meth:`RuleBasedStrategy.build` turns a
satisfied rule set into a setup, or returns None to decline.

Strategies are frozen dataclasses, so their parameters are inspectable
(:attr:`parameters`) and a variant is a :meth:`with_parameters` call. That is
what makes the phase's "optimize parameters" a deterministic search over an
explicit, finite set rather than a rewrite of the strategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import fields, replace
from typing import Any, ClassVar, Protocol, Self, runtime_checkable

from ..domain.enums import (
    Assertion,
    Confidence,
    Direction,
    EvidenceType,
    StrategyCategory,
)
from ..domain.evidence import Evidence
from ..domain.strategy import (
    StrategyEvaluation,
    StrategyRuleMatch,
    StrategySetup,
)
from .context import StrategyContext

#: Evidence weight per confidence band. Shared across strategies so two of them
#: cannot weight the *same* detection differently -- the band is a property of
#: how strong the claim is, never a probability the market follows it.
CONFIDENCE_WEIGHTS: dict[Confidence, float] = {
    Confidence.LOW: 0.4,
    Confidence.MEDIUM: 0.6,
    Confidence.HIGH: 0.8,
}

#: A claim that is real but not independently decisive -- context that supports
#: a setup without defining it (a fair value gap beside an order block, a
#: structure read a break was judged against).
SUPPORTING_WEIGHT = 0.5

#: A claim that is present but weak -- a pattern that is measured yet marginal,
#: recorded so the evidence set is complete rather than because it carries much.
WEAK_CLAIM_WEIGHT = 0.3

#: A claim that is strong but not banded -- a measured condition that clearly
#: holds, where no Confidence label applies.
STRONG_CLAIM_WEIGHT = 0.7


@runtime_checkable
class TradingStrategy(Protocol):
    """
    What the registry, the service and the optimizer require of a strategy.

    Deliberately a protocol rather than a base class: a strategy only has to
    *be* these things, so a caller may supply their own without inheriting from
    anything here. :class:`RuleBasedStrategy` is the provided implementation of
    the contract, not the only permitted one.
    """

    @property
    def strategy_id(self) -> str:
        """Stable identifier, unique within a registry."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    def category(self) -> StrategyCategory:
        """Which family the strategy belongs to (spec's example list)."""
        ...

    @property
    def description(self) -> str:
        """What the strategy looks for, in one sentence."""
        ...

    @property
    def parameters(self) -> tuple[tuple[str, Any], ...]:
        """The configured parameters, as ordered pairs."""
        ...

    def evaluate(self, context: StrategyContext) -> StrategyEvaluation:
        """Evaluate the context, returning a setup or an explained nothing."""
        ...


class RuleBasedStrategy(ABC):
    """
    A strategy expressed as named rules plus a builder.

    Subclasses declare ``strategy_id``/``name``/``category``/``description`` as
    class variables and their tunable parameters as dataclass fields, so
    :attr:`parameters` and :meth:`with_parameters` come for free and the
    optimizer can enumerate variants without knowing anything about the strategy.
    """

    #: Stable identifier, unique within a registry.
    strategy_id: ClassVar[str] = ""
    #: Human-readable name.
    name: ClassVar[str] = ""
    #: Which family the strategy belongs to.
    category: ClassVar[StrategyCategory] = StrategyCategory.CUSTOM
    #: What the strategy looks for, in one sentence.
    description: ClassVar[str] = ""
    #: Whether the strategy cannot run at all without an ICT read.
    requires_ict: ClassVar[bool] = False
    #: Whether the strategy cannot run at all without a breakout read.
    requires_breakout: ClassVar[bool] = False

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    @property
    def parameters(self) -> tuple[tuple[str, Any], ...]:
        """Every dataclass field, in declaration order -- the tunable surface."""
        return tuple((f.name, getattr(self, f.name)) for f in fields(self))

    def with_parameters(self, **overrides: Any) -> Self:
        """
        A copy of this strategy with some parameters replaced.

        Unknown names are rejected rather than ignored: a silently dropped
        parameter would make an optimization run report a result for a
        configuration it never actually evaluated.
        """
        known = {name for name, _ in self.parameters}
        unknown = sorted(set(overrides) - known)
        if unknown:
            raise ValueError(
                f"Unknown parameter(s) for strategy '{self.strategy_id}': "
                f"{', '.join(unknown)}. Known: {', '.join(sorted(known))}."
            )
        return replace(self, **overrides)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, context: StrategyContext) -> StrategyEvaluation:
        """
        Run the strategy over ``context``.

        The sequence is fixed and the same for every strategy: check the inputs
        it needs exist at all, evaluate every rule, then build. A strategy that
        could not run reports why instead of returning a vacuous "no setup" --
        the difference between "I looked and there was nothing" and "I could not
        look" matters to anything downstream.
        """
        blockers = self.blockers(context)
        if blockers:
            return StrategyEvaluation(
                strategy_id=self.strategy_id,
                strategy_name=self.name,
                category=self.category,
                timeframe=context.timeframe,
                rules=(),
                setup=None,
                limitations=blockers,
            )

        rules = self.rules(context)
        setup = self.build(context, rules)
        return StrategyEvaluation(
            strategy_id=self.strategy_id,
            strategy_name=self.name,
            category=self.category,
            timeframe=context.timeframe,
            rules=rules,
            setup=setup,
            limitations=() if setup else (self._decline_reason(rules),),
        )

    def blockers(self, context: StrategyContext) -> tuple[str, ...]:
        """
        Why the strategy cannot run at all, or an empty tuple when it can.

        The default covers the declared input requirements. Override to add
        strategy-specific preconditions (data unusable, a read empty in a way
        that makes evaluation meaningless).
        """
        reasons: list[str] = []
        if self.requires_ict and context.ict is None:
            reasons.append(
                f"{self.name} needs an ICT read, and none could be computed for "
                "this series."
            )
        if self.requires_breakout and context.breakout is None:
            reasons.append(
                f"{self.name} needs a breakout read, and none could be computed "
                "for this series."
            )
        return tuple(reasons)

    def _decline_reason(self, rules: tuple[StrategyRuleMatch, ...]) -> str:
        """A short, specific account of why no setup was built."""
        unmet = [rule.rule for rule in rules if not rule.satisfied]
        if unmet:
            return f"{self.name}: no setup -- unmet conditions: {', '.join(unmet)}."
        return (
            f"{self.name}: every condition held but no setup was warranted "
            "on this context."
        )

    @abstractmethod
    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        """
        Every condition this strategy examined, satisfied or not.

        Values and thresholds are reported alongside the verdict so the rule is
        checkable by hand, and rules are named in the strategy's own vocabulary
        so the account reads as the strategy's reasoning rather than as a dump.
        """

    @abstractmethod
    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        """
        The setup these rules describe, or None when they do not describe one.

        Returning None is an ordinary, honest outcome. Implementations must not
        relax a condition to manufacture a setup, and must never invent a
        SIDEWAYS direction -- the absence of a setup is the absence of an edge.
        """

    # ------------------------------------------------------------------
    # Helpers for implementations
    # ------------------------------------------------------------------

    def evidence(
        self,
        context: StrategyContext,
        *,
        etype: EvidenceType,
        direction: Direction,
        detail: str,
        weight: float,
        data: dict[str, Any] | None = None,
    ) -> Evidence:
        """
        Build one :class:`Evidence` claim from this strategy's read.

        Every claim is DETECTED -- derived from the deterministic reads rather
        than observed raw -- and carries the context's own provenance and
        quality, so a setup built on degraded data can never present its
        evidence as clean.
        """
        return Evidence(
            instrument_key=context.instrument.key,
            type=etype,
            assertion=Assertion.DETECTED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=Confidence.from_score(weight),
            provenance=context.provenance,
            quality=context.quality,
            data=data or {},
        )

    @staticmethod
    def confidence_from(rules: tuple[StrategyRuleMatch, ...]) -> Confidence:
        """
        Confidence from how completely the rule set agreed.

        A share of satisfied rules, never a probability: it says how well this
        context matched the strategy's own definition of the pattern, not how
        likely the market is to follow it. The two must not be conflated
        (CLAUDE.md section 3).
        """
        if not rules:
            return Confidence.LOW
        share = sum(1 for rule in rules if rule.satisfied) / len(rules)
        return Confidence.from_score(share)

    @staticmethod
    def satisfied(rules: tuple[StrategyRuleMatch, ...], rule: str) -> bool:
        """Whether a named rule held -- for the builder's own branching."""
        for match in rules:
            if match.rule == rule:
                return match.satisfied
        raise KeyError(f"No rule named '{rule}' was evaluated.")
