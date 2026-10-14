"""
SMC strategy (spec Phase 7).

Smart Money Concepts already detects the footprints -- order blocks, fair value
gaps, breaks of structure, the premium/discount read of the dealing range. This
strategy is the interpretation layer on top: it fires when those footprints
agree on one side and price is entering from the correct half of the range.

The single most important rule here is the discount/premium gate, and it is the
reason this is not simply "an order block exists". Buying demand in *premium*
is buying the expensive half of the range, which is the opposite of what the
concept describes; the dealing range's own ``position`` label is reused rather
than a second threshold computed here, so the strategy and the SMC read can
never disagree about where equilibrium is.

The invalidation level is the far edge of the order block the setup rests on --
the price at which that zone has been closed through and no longer exists. Only
when no usable zone is left does it fall back to the volatility level, and it
says which it used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..domain.enums import (
    Confidence,
    Direction,
    EvidenceType,
    SMCZoneKind,
    StrategyCategory,
    TrendState,
)
from ..domain.evidence import Evidence
from ..domain.smc import SMCZone
from ..domain.strategy import StrategyRuleMatch, StrategySetup
from .base import (
    CONFIDENCE_WEIGHTS,
    SUPPORTING_WEIGHT,
    RuleBasedStrategy,
)
from .context import StrategyContext
from .levels import (
    STRUCTURAL,
    invalidation_source,
    structural_invalidation,
)


@dataclass(frozen=True, slots=True)
class SMCStrategy(RuleBasedStrategy):
    """
    Trades from a live order block in the trend direction, from discount/premium.

    ``require_fair_value_gap`` makes displacement evidence mandatory rather than
    optional, and ``atr_invalidation_multiple`` sets the volatility fallback used
    only when no order block supplies a usable edge.
    """

    require_fair_value_gap: bool = False
    atr_invalidation_multiple: float = 1.5

    strategy_id: ClassVar[str] = "smc"
    name: ClassVar[str] = "SMC Structure"
    category: ClassVar[StrategyCategory] = StrategyCategory.SMC
    description: ClassVar[str] = (
        "Trades from a live order block in the trend direction, entered from discount/premium."
    )

    def __post_init__(self) -> None:
        if self.atr_invalidation_multiple <= 0:
            raise ValueError("atr_invalidation_multiple must be positive.")

    # ------------------------------------------------------------------

    @staticmethod
    def _direction(context: StrategyContext) -> Direction:
        if context.smc.trend is TrendState.UPTREND:
            return Direction.UP
        if context.smc.trend is TrendState.DOWNTREND:
            return Direction.DOWN
        return Direction.UNKNOWN

    @staticmethod
    def _live_zone(context: StrategyContext, direction: Direction) -> SMCZone | None:
        """
        The nearest order block on the invalidating side that is still valid.

        "Nearest" means the highest far edge still below price for a bullish
        zone, and the lowest still above it for a bearish one -- the same
        nearest-structure principle the swing-level fallback uses. A zone price
        has closed through is excluded: it has been invalidated and is no longer
        a level, whatever its label says.
        """
        entry = context.last_price
        if direction is Direction.UP:
            candidates = [
                zone
                for zone in context.smc.zones
                if zone.kind is SMCZoneKind.ORDER_BLOCK
                and zone.direction is Direction.UP
                and not zone.invalidated
                and zone.bottom < entry
            ]
            return max(candidates, key=lambda z: z.bottom) if candidates else None
        if direction is Direction.DOWN:
            candidates = [
                zone
                for zone in context.smc.zones
                if zone.kind is SMCZoneKind.ORDER_BLOCK
                and zone.direction is Direction.DOWN
                and not zone.invalidated
                and zone.top > entry
            ]
            return min(candidates, key=lambda z: z.top) if candidates else None
        return None

    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        smc = context.smc
        direction = self._direction(context)
        zone = self._live_zone(context, direction)
        dealing_range = smc.dealing_range
        position = dealing_range.position if dealing_range is not None else None

        in_discount = position is not None and (
            (direction is Direction.UP and position == "discount")
            or (direction is Direction.DOWN and position == "premium")
        )
        fair_value_gaps = [
            gap for gap in smc.fair_value_gaps if gap.direction is direction
        ]
        last_break = smc.breaks[-1] if smc.breaks else None

        return (
            StrategyRuleMatch(
                rule="structure is directional",
                satisfied=direction is not Direction.UNKNOWN,
                detail=(
                    f"Structure reads '{smc.trend.value}'; an SMC trade needs an "
                    "uptrend or a downtrend."
                ),
            ),
            StrategyRuleMatch(
                rule="a live order block supports the side",
                satisfied=zone is not None,
                detail=(
                    f"Nearest {direction.value} order block spans "
                    f"[{zone.bottom:.4f}, {zone.top:.4f}] at bar {zone.index}."
                    if zone is not None
                    else f"No uninvalidated {direction.value} order block sits on "
                    "the invalidating side of price."
                ),
                value=zone.bottom if zone is not None else None,
                threshold=None,
            ),
            StrategyRuleMatch(
                rule="price is in discount/premium",
                satisfied=in_discount,
                detail=(
                    f"Dealing range reads '{position}' at ratio "
                    f"{dealing_range.price_ratio:.3f}."
                    if dealing_range is not None
                    else "No dealing range was established for this series."
                ),
                value=dealing_range.price_ratio if dealing_range is not None else None,
                threshold=0.5,
            ),
            StrategyRuleMatch(
                rule="displacement left a fair value gap",
                satisfied=bool(fair_value_gaps) or not self.require_fair_value_gap,
                detail=(
                    f"{len(fair_value_gaps)} {direction.value} fair value gap(s) "
                    "were left behind."
                    + (
                        ""
                        if self.require_fair_value_gap
                        else " A gap is not required by configuration."
                    )
                ),
                value=float(len(fair_value_gaps)),
                threshold=1.0 if self.require_fair_value_gap else 0.0,
            ),
            StrategyRuleMatch(
                rule="the latest structure break agrees",
                satisfied=last_break is not None
                and last_break.direction is direction,
                detail=(
                    f"Latest structure break is {last_break.kind.value} "
                    f"{last_break.direction.value} through "
                    f"{last_break.broken_level:.4f}."
                    if last_break is not None
                    else "No structure break was detected."
                ),
                value=last_break.broken_level if last_break is not None else None,
                threshold=None,
            ),
        )

    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        direction = self._direction(context)
        if direction is Direction.UNKNOWN or not all(rule.satisfied for rule in rules):
            return None

        entry = context.last_price
        zone = self._live_zone(context, direction)
        if zone is not None:
            invalidation = round(
                zone.bottom if direction is Direction.UP else zone.top, 8
            )
            source = STRUCTURAL
        else:
            invalidation = structural_invalidation(
                context, direction, atr_multiple=self.atr_invalidation_multiple
            )
            source = invalidation_source(context, direction) if invalidation else ""

        if invalidation is None:
            return None
        if direction is Direction.UP and invalidation >= entry:
            return None
        if direction is Direction.DOWN and invalidation <= entry:
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
            invalidation_level=invalidation,
            rules=rules,
            evidence=self._evidence(context, direction, zone),
            reasoning=self._reasoning(context, direction, zone, invalidation, source),
            quality=context.quality,
            provenance=context.provenance,
            limitations=context.limitations,
        )

    # ------------------------------------------------------------------

    def _evidence(
        self,
        context: StrategyContext,
        direction: Direction,
        zone: SMCZone | None,
    ) -> tuple[Evidence, ...]:
        smc = context.smc
        items: list[Evidence] = []
        if zone is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.MARKET_STRUCTURE,
                    direction=direction,
                    detail=(
                        f"{direction.value.capitalize()} order block "
                        f"[{zone.bottom:.4f}, {zone.top:.4f}] formed at bar "
                        f"{zone.index}"
                        + (", since mitigated." if zone.mitigated else ", unmitigated.")
                    ),
                    weight=CONFIDENCE_WEIGHTS[zone.confidence],
                    data={
                        "zone_kind": zone.kind.value,
                        "zone_top": zone.top,
                        "zone_bottom": zone.bottom,
                        "zone_index": zone.index,
                        "mitigated": zone.mitigated,
                    },
                )
            )
        for gap in smc.fair_value_gaps:
            if gap.direction is not direction:
                continue
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.MARKET_STRUCTURE,
                    direction=direction,
                    detail=(
                        f"Fair value gap [{gap.bottom:.4f}, {gap.top:.4f}] left at "
                        f"bar {gap.index} supports the {direction.value} side."
                    ),
                    weight=SUPPORTING_WEIGHT,
                    data={
                        "zone_kind": gap.kind.value,
                        "zone_top": gap.top,
                        "zone_bottom": gap.bottom,
                        "zone_index": gap.index,
                    },
                )
            )
        if smc.dealing_range is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.MARKET_STRUCTURE,
                    direction=direction,
                    detail=(
                        f"Price sits at ratio {smc.dealing_range.price_ratio:.3f} of "
                        f"the dealing range [{smc.dealing_range.low:.4f}, "
                        f"{smc.dealing_range.high:.4f}], read as "
                        f"'{smc.dealing_range.position}'."
                    ),
                    weight=CONFIDENCE_WEIGHTS[Confidence.MEDIUM],
                    data={
                        "range_high": smc.dealing_range.high,
                        "range_low": smc.dealing_range.low,
                        "range_position": smc.dealing_range.position,
                        "price_ratio": smc.dealing_range.price_ratio,
                    },
                )
            )
        return tuple(items)

    def _reasoning(
        self,
        context: StrategyContext,
        direction: Direction,
        zone: SMCZone | None,
        invalidation: float,
        source: str,
    ) -> str:
        range_text = (
            f"{context.smc.dealing_range.position} "
            f"({context.smc.dealing_range.price_ratio:.3f} of the range)"
            if context.smc.dealing_range is not None
            else "an unmeasured range"
        )
        zone_text = (
            f"a {direction.value} order block [{zone.bottom:.4f}, {zone.top:.4f}]"
            if zone is not None
            else "no live order block"
        )
        location = (
            f"order block edge at {invalidation:.4f}"
            if source == STRUCTURAL
            else f"volatility (ATR) level at {invalidation:.4f}"
        )
        return (
            f"Structure reads '{context.smc.trend.value}' with price in {range_text} "
            f"and {zone_text} on the invalidating side. "
            f"The thesis is void beyond the {location}."
        )
