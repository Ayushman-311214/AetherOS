"""
Breakout strategy (spec Phase 7).

A channel break is already detected, measured and weighted by
:class:`BreakoutService`; this strategy's job is to decide whether *this* break
is one worth describing a setup around, and it does that by adding the two
things the detector deliberately does not know about: whether the break is
fighting the prevailing structure, and whether price has already run so far past
the edge that the entry is a chase.

The invalidation level is the broken edge itself, which is the one price that
gives the pattern its meaning -- a break that closes back inside the channel has
failed, and saying so is more useful than an ATR band picked independently of
the pattern. Because the edge is a real level rather than a volatility proxy,
this strategy always has a defensible invalidation and never falls back.

The breakout detector's own :class:`Evidence` object is reused rather than
rebuilt, so the claim that reaches the signal layer is byte-identical to the one
the detector published.
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
from .base import SUPPORTING_WEIGHT, RuleBasedStrategy
from .context import StrategyContext


@dataclass(frozen=True, slots=True)
class BreakoutStrategy(RuleBasedStrategy):
    """
    Trades a volume-confirmed channel break that is not already extended.

    ``require_volume`` makes volume confirmation mandatory rather than merely
    down-weighting the read, and ``max_extension_atr`` caps how far past the
    broken edge price may already be.
    """

    require_volume: bool = True
    max_extension_atr: float = 2.0

    strategy_id: ClassVar[str] = "breakout"
    name: ClassVar[str] = "Breakout"
    category: ClassVar[StrategyCategory] = StrategyCategory.BREAKOUT
    description: ClassVar[str] = (
        "Trades a confirmed break of the prior channel, from close to the edge."
    )
    requires_breakout: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.max_extension_atr <= 0:
            raise ValueError("max_extension_atr must be positive.")

    # ------------------------------------------------------------------

    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        read = context.breakout
        if read is None:  # guarded by ``blockers``; kept for type narrowing
            return ()

        direction = read.direction
        entry = read.last_close if read.last_close is not None else context.last_price
        edge = read.channel_high if direction is Direction.UP else read.channel_low
        atr = context.atr
        extension = (
            abs(entry - edge) / atr if edge is not None and atr is not None and atr > 0
            else None
        )
        # A break *against* the prevailing structure is the failed-breakout case.
        against_trend = (context.trend is TrendState.UPTREND and direction is Direction.DOWN) or (
            context.trend is TrendState.DOWNTREND and direction is Direction.UP
        )

        return (
            StrategyRuleMatch(
                rule="a channel broke",
                satisfied=read.has_breakout,
                detail=(
                    f"Last close {entry:.4f} against the {read.lookback}-bar "
                    f"channel [{read.channel_low}, {read.channel_high}]."
                    if read.channel_low is not None and read.channel_high is not None
                    else "No channel was measured for this series."
                ),
                value=entry,
                threshold=edge,
            ),
            StrategyRuleMatch(
                rule="the break is confirmed by volume",
                satisfied=read.volume_confirmed or not self.require_volume,
                detail=(
                    (
                        f"Break volume is {read.volume_ratio:.2f}x average."
                        if read.volume_ratio is not None
                        else "Average volume could not be measured."
                    )
                    + (
                        ""
                        if self.require_volume
                        else " Volume confirmation is not required by configuration."
                    )
                ),
                value=read.volume_ratio,
                threshold=None,
            ),
            StrategyRuleMatch(
                rule="the break is not against the dominant trend",
                satisfied=not against_trend,
                detail=(
                    f"Structure reads '{context.trend.value}'; the "
                    f"{direction.value} break is "
                    f"{'against' if against_trend else 'not against'} it."
                ),
            ),
            StrategyRuleMatch(
                rule="entry is close to the broken edge",
                satisfied=(
                    extension is not None and extension <= self.max_extension_atr
                ),
                detail=(
                    f"Price sits {extension:.2f} ATR beyond the broken edge, "
                    f"against a maximum of {self.max_extension_atr:.2f}."
                    if extension is not None
                    else "No ATR available; the distance beyond the edge is unknown."
                ),
                value=extension,
                threshold=self.max_extension_atr,
            ),
        )

    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        read = context.breakout
        if read is None or not read.has_breakout:
            return None
        if not all(rule.satisfied for rule in rules):
            return None

        direction = read.direction
        if direction not in (Direction.UP, Direction.DOWN):
            return None
        edge = read.channel_high if direction is Direction.UP else read.channel_low
        if edge is None or edge <= 0:
            return None
        entry = read.last_close if read.last_close is not None else context.last_price
        if direction is Direction.UP and edge >= entry:
            return None
        if direction is Direction.DOWN and edge <= entry:
            return None

        return StrategySetup(
            instrument=context.instrument,
            strategy_id=self.strategy_id,
            strategy_name=self.name,
            category=self.category,
            timeframe=context.timeframe,
            direction=direction,
            confidence=self.confidence_from(rules),
            entry_reference=entry,
            invalidation_level=round(edge, 8),
            rules=rules,
            evidence=self._evidence(context),
            reasoning=self._reasoning(context, direction, edge),
            quality=context.quality,
            provenance=context.provenance,
            limitations=context.limitations,
        )

    # ------------------------------------------------------------------

    def _evidence(self, context: StrategyContext) -> tuple[Evidence, ...]:
        """The detector's own claim, plus the structure read it was judged against."""
        read = context.breakout
        if read is None:
            return ()
        items: list[Evidence] = []
        if read.evidence is not None:
            items.append(read.evidence)
        items.append(
            self.evidence(
                context,
                etype=EvidenceType.MARKET_STRUCTURE,
                direction=read.direction,
                detail=(
                    f"The {read.direction.value} break was judged against a "
                    f"structure read of '{context.trend.value}'."
                ),
                weight=SUPPORTING_WEIGHT,
                data={
                    "trend": context.trend.value,
                    "trend_strength": context.trend_strength,
                    "channel_high": read.channel_high,
                    "channel_low": read.channel_low,
                },
            )
        )
        return tuple(items)

    def _reasoning(
        self, context: StrategyContext, direction: Direction, edge: float
    ) -> str:
        read = context.breakout
        volume = (
            f"{read.volume_ratio:.2f}x average volume"
            if read is not None and read.volume_ratio is not None
            else "unmeasured volume"
        )
        side = "below" if direction is Direction.UP else "above"
        return (
            f"Price broke the {read.lookback if read else 0}-bar channel "
            f"{'high' if direction is Direction.UP else 'low'} at {edge:.4f} on "
            f"{volume}, without opposing the '{context.trend.value}' structure. "
            f"The thesis is void {side} the broken edge at {edge:.4f}, which is "
            "where the break would have failed."
        )
