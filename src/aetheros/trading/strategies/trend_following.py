"""
Trend-following strategy (spec Phase 7).

The classic continuation read: structure is trending, the trend is measurably
strong, price is on the trend's side of its own average, momentum agrees, and
the entry is not so extended that the trade is chasing.

"Not extended" is the condition that distinguishes this from a naive
"trend is up, buy" rule, and it is measured in ATR rather than asserted -- a
trend can be entirely real and still be a poor entry after a vertical run.

Every read comes from the analysis layer's own indicators; nothing is
recomputed here. That is why the tunable parameters are *thresholds* rather
than indicator periods: the snapshot was computed with the configured periods,
and a strategy that claimed a different SMA length would be reporting a
parameter it never actually applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..domain.enums import (
    Direction,
    EvidenceType,
    StrategyCategory,
    TrendState,
)
from ..domain.evidence import Evidence
from ..domain.strategy import StrategyRuleMatch, StrategySetup
from .base import RuleBasedStrategy
from .context import StrategyContext
from .levels import (
    STRUCTURAL,
    invalidation_source,
    structural_invalidation,
)

#: ADX at which a trend is treated as fully established for *weighting* an
#: evidence item. Scales weight only -- never a probability.
_FULL_ADX = 40.0

#: MACD histogram, as a fraction of price, treated as full momentum weight.
_FULL_MOMENTUM_HISTOGRAM = 0.005


@dataclass(frozen=True, slots=True)
class TrendFollowingStrategy(RuleBasedStrategy):
    """
    Trades with a confirmed trend from a non-extended entry.

    ``min_adx`` and ``min_trend_strength`` gate how established the trend must
    be, ``max_extension_atr`` how far price may already have run from its
    average, and ``atr_invalidation_multiple`` how far behind the entry the
    volatility fallback for the invalidation level sits.
    """

    min_adx: float = 20.0
    min_trend_strength: float = 0.5
    max_extension_atr: float = 3.0
    atr_invalidation_multiple: float = 1.5

    strategy_id: ClassVar[str] = "trend_following"
    name: ClassVar[str] = "Trend Following"
    category: ClassVar[StrategyCategory] = StrategyCategory.TREND_FOLLOWING
    description: ClassVar[str] = (
        "Trades with a confirmed, strong trend from a non-extended entry."
    )

    def __post_init__(self) -> None:
        if self.min_adx < 0:
            raise ValueError("min_adx cannot be negative.")
        if not 0.0 <= self.min_trend_strength <= 1.0:
            raise ValueError("min_trend_strength must lie within 0 and 1.")
        if self.max_extension_atr <= 0:
            raise ValueError("max_extension_atr must be positive.")
        if self.atr_invalidation_multiple <= 0:
            raise ValueError("atr_invalidation_multiple must be positive.")

    # ------------------------------------------------------------------

    @staticmethod
    def _trend_direction(context: StrategyContext) -> Direction:
        """The side structure points to, or UNKNOWN when it is not trending."""
        if context.trend is TrendState.UPTREND:
            return Direction.UP
        if context.trend is TrendState.DOWNTREND:
            return Direction.DOWN
        return Direction.UNKNOWN

    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        direction = self._trend_direction(context)
        entry = context.last_price
        technical = context.analysis.technical
        adx = context.adx
        atr = context.atr
        macd = technical.macd
        reference = (
            technical.sma_fast if technical.sma_fast is not None else technical.sma_slow
        )

        extension = (
            abs(entry - reference) / atr
            if reference is not None and atr is not None and atr > 0
            else None
        )
        on_trend_side = reference is not None and (
            (direction is Direction.UP and entry > reference)
            or (direction is Direction.DOWN and entry < reference)
        )
        momentum_agrees = macd is not None and (
            (direction is Direction.UP and macd.histogram > 0)
            or (direction is Direction.DOWN and macd.histogram < 0)
        )

        return (
            StrategyRuleMatch(
                rule="directional structure",
                satisfied=direction is not Direction.UNKNOWN,
                detail=(
                    f"Structure reads '{context.trend.value}'; a trend trade "
                    "needs an uptrend or a downtrend."
                ),
            ),
            StrategyRuleMatch(
                rule="trend is established (ADX)",
                satisfied=adx is not None and adx >= self.min_adx,
                detail=(
                    f"ADX {adx:.1f} against a minimum of {self.min_adx:.1f}."
                    if adx is not None
                    else "ADX is unavailable; trend strength cannot be judged."
                ),
                value=adx,
                threshold=self.min_adx,
            ),
            StrategyRuleMatch(
                rule="structural conviction",
                satisfied=context.trend_strength >= self.min_trend_strength,
                detail=(
                    f"Trend strength {context.trend_strength:.2f} against a "
                    f"minimum of {self.min_trend_strength:.2f}."
                ),
                value=context.trend_strength,
                threshold=self.min_trend_strength,
            ),
            StrategyRuleMatch(
                rule="price on the trend side of the fast average",
                satisfied=on_trend_side,
                detail=(
                    f"Price {entry:.4f} against the reference average "
                    f"{reference:.4f}."
                    if reference is not None
                    else "No fast or slow moving average is available."
                ),
                value=entry,
                threshold=reference,
            ),
            StrategyRuleMatch(
                rule="entry is not over-extended",
                satisfied=(
                    extension is not None and extension <= self.max_extension_atr
                ),
                detail=(
                    f"Price sits {extension:.2f} ATR from the reference average, "
                    f"against a maximum of {self.max_extension_atr:.2f}."
                    if extension is not None
                    else "No ATR or moving average; extension cannot be measured."
                ),
                value=extension,
                threshold=self.max_extension_atr,
            ),
            StrategyRuleMatch(
                rule="momentum agrees",
                satisfied=momentum_agrees,
                detail=(
                    f"MACD histogram {macd.histogram:.6f}; the trend side needs "
                    f"a {'positive' if direction is Direction.UP else 'negative'} "
                    "reading."
                    if macd is not None
                    else "No MACD reading is available."
                ),
                value=macd.histogram if macd is not None else None,
                threshold=0.0,
            ),
        )

    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        direction = self._trend_direction(context)
        if direction is Direction.UNKNOWN or not all(rule.satisfied for rule in rules):
            return None

        entry = context.last_price
        invalidation = structural_invalidation(
            context, direction, atr_multiple=self.atr_invalidation_multiple
        )
        if invalidation is None:
            return None
        # The domain model enforces this too; checking here means a misconfigured
        # ATR multiple yields no setup rather than an exception mid-evaluation.
        if direction is Direction.UP and invalidation >= entry:
            return None
        if direction is Direction.DOWN and invalidation <= entry:
            return None

        source = invalidation_source(context, direction)
        return StrategySetup(
            instrument=context.instrument,
            strategy_id=self.strategy_id,
            strategy_name=self.name,
            category=self.category,
            timeframe=context.timeframe,
            direction=direction,
            confidence=self.confidence_from(rules),
            entry_reference=entry,
            invalidation_level=invalidation,
            rules=rules,
            evidence=self._evidence(context, direction),
            reasoning=self._reasoning(context, direction, invalidation, source),
            quality=context.quality,
            provenance=context.provenance,
            limitations=context.limitations,
        )

    # ------------------------------------------------------------------

    def _evidence(
        self, context: StrategyContext, direction: Direction
    ) -> tuple[Evidence, ...]:
        """
        The market claims behind the setup -- trend and momentum.

        The invalidation level is deliberately *not* evidence: it is a property
        of the setup, not a claim about the market, and dressing a risk level up
        as a directional signal is exactly the kind of conflation section 3
        forbids.
        """
        technical = context.analysis.technical
        entry = context.last_price
        adx = context.adx
        items = [
            self.evidence(
                context,
                etype=EvidenceType.TREND,
                direction=direction,
                detail=(
                    f"Structure reads '{context.trend.value}' with strength "
                    f"{context.trend_strength:.2f}"
                    + (f" and ADX {adx:.1f}." if adx is not None else ".")
                ),
                weight=min(1.0, context.trend_strength),
                data={
                    "trend": context.trend.value,
                    "trend_strength": context.trend_strength,
                    "adx": adx,
                },
            )
        ]
        if adx is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.TECHNICAL,
                    direction=direction,
                    detail=(
                        f"ADX {adx:.1f} is above the strategy's "
                        f"{self.min_adx:.1f} floor for an established trend."
                    ),
                    weight=min(1.0, adx / _FULL_ADX),
                    data={"adx": adx, "min_adx": self.min_adx},
                )
            )
        macd = technical.macd
        if macd is not None:
            relative = abs(macd.histogram) / entry if entry > 0 else 0.0
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.MOMENTUM,
                    direction=direction,
                    detail=(
                        f"MACD histogram {macd.histogram:.6f} "
                        f"({relative * 100:.2f}% of price) is on the "
                        f"{direction.value} side of its signal line."
                    ),
                    weight=min(1.0, relative / _FULL_MOMENTUM_HISTOGRAM),
                    data={
                        "macd": macd.macd,
                        "signal": macd.signal,
                        "histogram": macd.histogram,
                    },
                )
            )
        return tuple(items)

    def _reasoning(
        self,
        context: StrategyContext,
        direction: Direction,
        invalidation: float,
        source: str,
    ) -> str:
        adx = context.adx
        strength = (
            f"Structure reads '{context.trend.value}' "
            f"(strength {context.trend_strength:.2f}"
        )
        strength += f", ADX {adx:.1f})" if adx is not None else ")"
        location = (
            f"structural level at {invalidation:.4f}"
            if source == STRUCTURAL
            else f"volatility (ATR) level at {invalidation:.4f}"
        )
        side = "below" if direction is Direction.UP else "above"
        return (
            f"{strength}; price {context.last_price:.4f} sits on the "
            f"{direction.value} side of its reference average, is not extended "
            f"beyond {self.max_extension_atr:.2f} ATR, and momentum agrees. "
            f"The thesis is void {side} the {location}."
        )
