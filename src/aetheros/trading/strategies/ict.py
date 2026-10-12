"""
ICT strategy (spec Phase 7).

The ICT engine already answers *when* things happened -- daily bias, market
structure shift, kill zones, OTE, liquidity pools, Judas swings, Power of Three,
session models. This strategy is the first consumer that puts them together into
a single read, and it is deliberately the strictest of the five: ICT is a
time-based framework, so a setup is only described when the bias, the
displacement and the *time of day* agree.

That strictness is the point. The engine can detect a market structure shift at
any hour; this strategy asks whether it happened in a kill zone, whether price
has retraced into the optimal trade entry band, and whether there is resting
liquidity on the far side for the move to reach. When any of those is missing it
declines and says which -- which is a far more useful output than a setup that
quietly ignored the parts of the framework that did not fit.

The invalidation level is the level the shift broke, because a close back
through it means the displacement was reversed and the premise is gone. The OTE
band's far edge is the second choice, and an ATR band the last resort.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..domain.enums import (
    Direction,
    EvidenceType,
    StrategyCategory,
)
from ..domain.evidence import Evidence
from ..domain.ict import ICTAnalysis, MarketStructureShift
from ..domain.strategy import StrategyRuleMatch, StrategySetup
from .base import (
    CONFIDENCE_WEIGHTS,
    STRONG_CLAIM_WEIGHT,
    SUPPORTING_WEIGHT,
    WEAK_CLAIM_WEIGHT,
    RuleBasedStrategy,
)
from .context import StrategyContext
from .levels import (
    STRUCTURAL,
    invalidation_source,
    structural_invalidation,
)

#: Displacement, in ATR, treated as a full-weight shifted move for evidence
#: weighting. Scales weight only -- never a probability.
_FULL_DISPLACEMENT_ATR = 2.0


@dataclass(frozen=True, slots=True)
class ICTStrategy(RuleBasedStrategy):
    """
    Trades a kill-zone market structure shift, entered from the OTE band.

    ``require_kill_zone`` and ``require_ote`` are the two gates that make this
    the time-aware strategy rather than a second structure strategy;
    ``atr_invalidation_multiple`` sets the volatility fallback used only when
    neither the shift's level nor the OTE band can supply one.
    """

    require_kill_zone: bool = True
    require_ote: bool = True
    atr_invalidation_multiple: float = 1.5

    strategy_id: ClassVar[str] = "ict"
    name: ClassVar[str] = "ICT Kill Zone"
    category: ClassVar[StrategyCategory] = StrategyCategory.ICT
    description: ClassVar[str] = (
        "Trades a kill-zone market structure shift, entered from the OTE band."
    )
    requires_ict: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if self.atr_invalidation_multiple <= 0:
            raise ValueError("atr_invalidation_multiple must be positive.")

    # ------------------------------------------------------------------

    @staticmethod
    def _direction(ict: ICTAnalysis) -> Direction:
        """The side the daily bias points to; UNKNOWN without a readable bias."""
        bias = ict.daily_bias
        if bias is None or bias.direction not in (Direction.UP, Direction.DOWN):
            return Direction.UNKNOWN
        return bias.direction

    @staticmethod
    def _shift(
        ict: ICTAnalysis, direction: Direction
    ) -> MarketStructureShift | None:
        """The most recent market structure shift on the given side."""
        matching = [
            shift
            for shift in ict.market_structure_shifts
            if shift.direction is direction
        ]
        return max(matching, key=lambda s: s.index) if matching else None

    @staticmethod
    def _in_kill_zone(ict: ICTAnalysis, shift: MarketStructureShift | None) -> bool:
        if shift is None:
            return False
        return any(
            zone.first_index <= shift.index <= zone.last_index for zone in ict.kill_zones
        )

    def rules(self, context: StrategyContext) -> tuple[StrategyRuleMatch, ...]:
        ict = context.ict
        if ict is None:  # guarded by ``blockers``; kept for type narrowing
            return ()

        direction = self._direction(ict)
        bias = ict.daily_bias
        shift = self._shift(ict, direction)
        in_zone = self._in_kill_zone(ict, shift)
        ote = ict.ote
        ote_in_band = (
            ote is not None and ote.direction is direction and ote.in_zone
        )
        resting = [pool for pool in ict.resting_pools if pool.direction is direction]

        return (
            StrategyRuleMatch(
                rule="the daily bias is directional",
                satisfied=direction is not Direction.UNKNOWN,
                detail=(
                    f"Daily bias reads '{bias.direction.value}' from the completed "
                    f"day {bias.prior_day_date.isoformat()} "
                    f"(price at ratio {bias.price_ratio:.3f})."
                    if bias is not None
                    else "No prior day could be read, so there is no daily bias."
                ),
                value=bias.price_ratio if bias is not None else None,
                threshold=None,
            ),
            StrategyRuleMatch(
                rule="a market structure shift confirms the bias",
                satisfied=shift is not None,
                detail=(
                    f"Displaced shift at bar {shift.index} through "
                    f"{shift.broken_level:.4f} (displacement {shift.displacement:.2f} ATR"
                    + (", leaving a fair value gap)." if shift.left_fair_value_gap else ").")
                    if shift is not None
                    else f"No {direction.value} market structure shift was detected."
                ),
                value=shift.displacement if shift is not None else None,
                threshold=None,
            ),
            StrategyRuleMatch(
                rule="the shift occurred inside a kill zone",
                satisfied=in_zone or not self.require_kill_zone,
                detail=(
                    (
                        f"The shift at bar {shift.index} falls inside a measured "
                        "kill zone."
                        if in_zone
                        else f"The shift at bar {shift.index} falls inside no "
                        "measured kill zone."
                    )
                    if shift is not None
                    else "There is no shift to place in time."
                )
                + (
                    ""
                    if self.require_kill_zone
                    else " Kill-zone timing is not required by configuration."
                ),
            ),
            StrategyRuleMatch(
                rule="price is inside the optimal trade entry band",
                satisfied=ote_in_band or not self.require_ote,
                detail=(
                    f"OTE band [{ote.band_bottom:.4f}, {ote.band_top:.4f}] with "
                    f"retracement {ote.retracement_ratio:.3f}."
                    if ote is not None
                    else "No impulse leg was available to measure an OTE band."
                )
                + (
                    ""
                    if self.require_ote
                    else " The OTE band is not required by configuration."
                ),
                value=ote.retracement_ratio if ote is not None else None,
                threshold=None,
            ),
            StrategyRuleMatch(
                rule="liquidity rests on the far side",
                satisfied=bool(resting),
                detail=(
                    f"{len(resting)} resting {direction.value}-side liquidity "
                    "pool(s) lie beyond price."
                ),
                value=float(len(resting)),
                threshold=1.0,
            ),
        )

    def build(
        self, context: StrategyContext, rules: tuple[StrategyRuleMatch, ...]
    ) -> StrategySetup | None:
        ict = context.ict
        if ict is None or not all(rule.satisfied for rule in rules):
            return None

        direction = self._direction(ict)
        if direction is Direction.UNKNOWN:
            return None

        entry = context.last_price
        invalidation, source = self._invalidation(context, direction)
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
            evidence=self._evidence(context, direction),
            reasoning=self._reasoning(context, direction, invalidation, source),
            quality=context.quality,
            provenance=context.provenance,
            limitations=context.limitations,
        )

    # ------------------------------------------------------------------

    def _invalidation(
        self, context: StrategyContext, direction: Direction
    ) -> tuple[float | None, str]:
        """
        The level that voids the thesis, preferring the more structural source.

        The shift's broken level comes first because that is the price the
        displacement had to clear; the OTE band's far edge is the entry zone's
        own boundary; an ATR band is the last resort and is labelled as one.
        """
        ict = context.ict
        entry = context.last_price
        if ict is None:
            return None, ""

        shift = self._shift(ict, direction)
        candidates = []
        if shift is not None:
            candidates.append((shift.broken_level, STRUCTURAL))
        if ict.ote is not None and ict.ote.direction is direction:
            candidates.append(
                (
                    ict.ote.band_bottom
                    if direction is Direction.UP
                    else ict.ote.band_top,
                    STRUCTURAL,
                )
            )
        for level, source in candidates:
            if level <= 0:
                continue
            if direction is Direction.UP and level < entry:
                return round(level, 8), source
            if direction is Direction.DOWN and level > entry:
                return round(level, 8), source

        fallback = structural_invalidation(
            context, direction, atr_multiple=self.atr_invalidation_multiple
        )
        if fallback is None:
            return None, ""
        return fallback, invalidation_source(context, direction)

    def _evidence(
        self, context: StrategyContext, direction: Direction
    ) -> tuple[Evidence, ...]:
        ict = context.ict
        if ict is None:
            return ()
        items: list[Evidence] = []
        bias = ict.daily_bias
        if bias is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.ICT,
                    direction=direction,
                    detail=(
                        f"Daily bias '{bias.direction.value}' from the completed day "
                        f"{bias.prior_day_date.isoformat()} "
                        f"[{bias.prior_day_low:.4f}, {bias.prior_day_high:.4f}], "
                        f"price at ratio {bias.price_ratio:.3f} ({bias.position})."
                    ),
                    weight=CONFIDENCE_WEIGHTS[bias.confidence],
                    data={
                        "prior_day_low": bias.prior_day_low,
                        "prior_day_high": bias.prior_day_high,
                        "price_ratio": bias.price_ratio,
                        "position": bias.position,
                    },
                )
            )
        shift = self._shift(ict, direction)
        if shift is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.ICT,
                    direction=direction,
                    detail=(
                        f"Market structure shift at bar {shift.index} through "
                        f"{shift.broken_level:.4f} with displacement "
                        f"{shift.displacement:.2f} ATR from a prior "
                        f"'{shift.prior_trend.value}' read."
                    ),
                    weight=min(1.0, shift.displacement / _FULL_DISPLACEMENT_ATR)
                    if shift.displacement > 0
                    else WEAK_CLAIM_WEIGHT,
                    data={
                        "broken_level": shift.broken_level,
                        "break_index": shift.index,
                        "displacement": shift.displacement,
                        "left_fair_value_gap": shift.left_fair_value_gap,
                    },
                )
            )
        if ict.ote is not None:
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.ICT,
                    direction=direction,
                    detail=(
                        f"OTE band [{ict.ote.band_bottom:.4f}, "
                        f"{ict.ote.band_top:.4f}] inside the leg "
                        f"[{ict.ote.leg_low:.4f}, {ict.ote.leg_high:.4f}], "
                        f"retracement {ict.ote.retracement_ratio:.3f}."
                    ),
                    weight=STRONG_CLAIM_WEIGHT if ict.ote.in_zone else WEAK_CLAIM_WEIGHT,
                    data={
                        "leg_low": ict.ote.leg_low,
                        "leg_high": ict.ote.leg_high,
                        "band_bottom": ict.ote.band_bottom,
                        "band_top": ict.ote.band_top,
                        "in_zone": ict.ote.in_zone,
                    },
                )
            )
        resting = [pool for pool in ict.resting_pools if pool.direction is direction]
        if resting:
            nearest = (
                min(pool.level for pool in resting)
                if direction is Direction.UP
                else max(pool.level for pool in resting)
            )
            items.append(
                self.evidence(
                    context,
                    etype=EvidenceType.ICT,
                    direction=direction,
                    detail=(
                        f"{len(resting)} resting {direction.value}-side liquidity "
                        f"pool(s); the nearest sits at {nearest:.4f}."
                    ),
                    weight=SUPPORTING_WEIGHT,
                    data={"pool_count": len(resting), "nearest_pool": nearest},
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
        ict = context.ict
        bias = ict.daily_bias if ict else None
        bias_text = (
            f"Daily bias is {bias.direction.value} from the completed day "
            f"{bias.prior_day_date.isoformat()}"
            if bias is not None
            else "No daily bias was readable"
        )
        zone_text = (
            "inside a measured kill zone"
            if ict is not None and self._in_kill_zone(ict, self._shift(ict, direction))
            else "outside every measured kill zone"
        )
        side = "below" if direction is Direction.UP else "above"
        return (
            f"{bias_text}; a {direction.value} market structure shift occurred "
            f"{zone_text}, price has retraced into the optimal trade entry band, "
            f"and resting liquidity lies beyond. The thesis is void {side} the "
            f"{source} level at {invalidation:.4f}."
        )
