"""
Mean-reversion strategy (spec Phase 7).

The mirror of the trend strategy, and gated on the same measurement from the
other side: this one only fires when the market is measurably *not* trending
(ADX below a ceiling, structure not directional), because fading a real trend is
the classic way a mean-reversion rule destroys an account. The trend strategy's
``min_adx`` floor and this strategy's ``max_adx`` ceiling are the two halves of
one regime classification, not two unrelated thresholds.

Within a range, the read is a stretch away from the mean that is large relative
to volatility. The stretch is measured in ATR -- an RSI of 25 in a quiet market
and an RSI of 25 in a violent one are not the same trade -- and the direction is
taken from *which* extreme was reached, never assumed.

No target is proposed. "Revert to the mean" names where price might travel, but
turning that into a target price, a risk/reward ratio and a position size is
:class:`RiskService`'s deterministic job from the same analysis.
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

#: RSI distance from 50 that counts as a full-weight stretch for evidence
#: weighting. Scales weight only -- never a probability.
_FULL_RSI_STRETCH = 30.0

#: Distance beyond a Bollinger band, in ATR, treated as a full-weight breach.
_FULL_BAND_BREACH = 0.5


@dataclass(frozen=True, slots=True)
class MeanReversionStrategy(RuleBasedStrategy):
    """
    Fades an over-extended move inside a market that is not trending.

    ``max_adx`` caps how trending the market may be, ``oversold``/``overbought``
    are the RSI extremes, ``min_stretch_atr`` how far from the mean price must
    sit relative to ATR for the stretch to be worth trading, and
    ``atr_invalidation_multiple`` how far behind the entry the volatility
    fallback for the invalidation level sits.
    """

    max_adx: float = 25.0
    oversold: float = 30.0
    overbought: float = 70.0
    min_stretch_atr: float = 1.0
    atr_invalidation_multiple: float = 1.5

    strategy_id: ClassVar[str] = "mean_reversion"
    name: ClassVar[str] = "Mean Reversion"
    category: ClassVar[StrategyCategory] = StrategyCategory.MEAN_REVERSION
    description: ClassVar[str] = (
        "Fades a volatility-scaled stretch away from the mean in a non-trending market."
    )

    def __post_init__(self) -> None:
        if self.max_adx < 0:
            raise ValueError("max_adx cannot be negative.")
        if not 0.0 < self.oversold < 50.0:
            raise ValueError("oversold must lie strictly between 0 and 50.")
        if not 50.0 < self.overbought < 100.0:
            raise ValueError("overbought must lie strictly between 50 and 100.")
        if self.min_stretch_atr <= 0:
            raise ValueError("min_stretch_atr must be positive.")
        if self.atr_invalidation_multiple <= 0:
            raise ValueError("atr_invalidation_multiple must be positive.")

    # ------------------------------------------------------------------

    @staticmethod
    def _mean_level(context: StrategyContext) -> float | None:
        """The mean price is reverting *to*: the Bollinger middle, else the slow SMA."""
        technical = context.analysis.technical
        if technical.bollinger is not None:
            return technical.bollinger.middle
        return technical.sma_slow

    def _direction(self, context: StrategyContext) -> Direction:
        """
        Which extreme price reached, or UNKNOWN.

        Either witness counts: RSI at its extreme, or price beyond a Bollinger
        band. Requiring both would silently discard the (common) case where one
        is unavailable, and requiring only one is honest as long as the rule
        reports which.
        """
        rsi = context.rsi
        bollinger = context.analysis.technical.bollinger
        entry = context.last_price
        if (rsi is not None and rsi <= self.oversold) or (
            bollinger is not None and entry <= bollinger.lower
        ):
            return Direction.UP
        if (rsi is not None and rsi >= self.overbought) or (
            bollinger is not None and entry >= bollinger.upper
        ):
            return Direction.DOWN
        return Direction.UNKNOWN

    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        direction = self._direction(context)
        entry = context.last_price
        rsi = context.rsi
        adx = context.adx
        atr = context.atr
        bollinger = context.analysis.technical.bollinger
        mean = self._mean_level(context)
        trend = context.trend

        stretch = (
            abs(entry - mean) / atr
            if mean is not None and atr is not None and atr > 0
            else None
        )
        at_extreme = rsi is not None and (
            (direction is Direction.UP and rsi <= self.oversold)
            or (direction is Direction.DOWN and rsi >= self.overbought)
        )
        beyond_band = bollinger is not None and (
            (direction is Direction.UP and entry <= bollinger.lower)
            or (direction is Direction.DOWN and entry >= bollinger.upper)
        )
        # Fading an uptrend by selling is the failure mode this rule prevents.
        against_trend = (trend is TrendState.UPTREND and direction is Direction.DOWN) or (
            trend is TrendState.DOWNTREND and direction is Direction.UP
        )

        return (
            StrategyRuleMatch(
                rule="market is not trending",
                satisfied=adx is not None and adx <= self.max_adx,
                detail=(
                    f"ADX {adx:.1f} against a ceiling of {self.max_adx:.1f}."
                    if adx is not None
                    else "ADX is unavailable; the regime cannot be judged."
                ),
                value=adx,
                threshold=self.max_adx,
            ),
            StrategyRuleMatch(
                rule="price is stretched to an extreme",
                satisfied=direction is not Direction.UNKNOWN
                and (at_extreme or beyond_band),
                detail=(
                    f"RSI {rsi:.1f} with the {self.oversold:.0f}/"
                    f"{self.overbought:.0f} band"
                    + (
                        f"; price {entry:.4f} against bands "
                        f"[{bollinger.lower:.4f}, {bollinger.upper:.4f}]."
                        if bollinger is not None
                        else "; no Bollinger reading."
                    )
                    if rsi is not None
                    else "RSI is unavailable and there is no Bollinger reading."
                ),
                value=rsi,
                threshold=(
                    self.oversold
                    if direction is Direction.UP
                    else self.overbought
                ),
            ),
            StrategyRuleMatch(
                rule="the dominant trend is not being faded",
                satisfied=not against_trend,
                detail=(
                    f"Structure reads '{trend.value}'; a "
                    f"{direction.value} fade is "
                    f"{'against' if against_trend else 'not against'} it."
                ),
            ),
            StrategyRuleMatch(
                rule="stretch is meaningful versus volatility",
                satisfied=stretch is not None and stretch >= self.min_stretch_atr,
                detail=(
                    f"Price sits {stretch:.2f} ATR from the mean, against a "
                    f"minimum of {self.min_stretch_atr:.2f}."
                    if stretch is not None
                    else "No mean or ATR available; the stretch cannot be measured."
                ),
                value=stretch,
                threshold=self.min_stretch_atr,
            ),
        )

    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        direction = self._direction(context)
        if direction is Direction.UNKNOWN or not all(rule.satisfied for rule in rules):
            return None

        entry = context.last_price
        invalidation = structural_invalidation(
            context, direction, atr_multiple=self.atr_invalidation_multiple
        )
        if invalidation is None:
            return None
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
        rsi = context.rsi
        bollinger = context.analysis.technical.bollinger
        mean = self._mean_level(context)
        adx = context.adx
        items: list[Evidence] = []
        if rsi is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.MOMENTUM,
                    direction=direction,
                    detail=(
                        f"RSI {rsi:.1f} is at the "
                        f"{'oversold' if direction is Direction.UP else 'overbought'} "
                        "extreme of a non-trending market."
                    ),
                    weight=min(1.0, abs(rsi - 50.0) / _FULL_RSI_STRETCH),
                    data={
                        "rsi": rsi,
                        "oversold": self.oversold,
                        "overbought": self.overbought,
                    },
                )
            )
        if bollinger is not None:
            edge = bollinger.lower if direction is Direction.UP else bollinger.upper
            atr = context.atr
            breach = (
                abs(context.last_price - edge) / atr
                if atr is not None and atr > 0
                else None
            )
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.VOLATILITY,
                    direction=direction,
                    detail=(
                        f"Price {context.last_price:.4f} is beyond the "
                        f"{'lower' if direction is Direction.UP else 'upper'} "
                        f"Bollinger band at {edge:.4f} "
                        f"(middle {bollinger.middle:.4f}, "
                        f"width {bollinger.width:.4f})."
                    ),
                    weight=(
                        min(1.0, breach / _FULL_BAND_BREACH)
                        if breach is not None
                        else 0.0
                    ),
                    data={
                        "band_lower": bollinger.lower,
                        "band_middle": bollinger.middle,
                        "band_upper": bollinger.upper,
                        "band_width": bollinger.width,
                        "breach_atr": breach,
                    },
                )
            )
        if mean is not None and adx is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.REGIME,
                    direction=Direction.UNKNOWN,
                    detail=(
                        f"ADX {adx:.1f} is below the {self.max_adx:.1f} ceiling, so "
                        "the market is read as ranging rather than trending."
                    ),
                    weight=min(1.0, max(0.0, (self.max_adx - adx) / self.max_adx)),
                    data={"adx": adx, "max_adx": self.max_adx, "mean": mean},
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
        mean = self._mean_level(context)
        side = "below" if direction is Direction.UP else "above"
        extreme = "oversold" if direction is Direction.UP else "overbought"
        location = (
            f"structural level at {invalidation:.4f}"
            if source == STRUCTURAL
            else f"volatility (ATR) level at {invalidation:.4f}"
        )
        mean_text = f"{mean:.4f}" if mean is not None else "an unavailable mean"
        adx = context.adx
        regime = (
            f"ADX {adx:.1f} against the {self.max_adx:.1f} ceiling"
            if adx is not None
            else "ADX unavailable"
        )
        return (
            f"Market is ranging ({regime}) and price {context.last_price:.4f} "
            f"is {extreme} relative to the mean at {mean_text}. "
            f"The thesis is void {side} the {location}."
        )
