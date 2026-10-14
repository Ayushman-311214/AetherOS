"""
Risk service -- the deterministic risk engine.

Given a :class:`TradingAnalysis` (the evidence-grounded situation report from
the numerical core), it derives a concrete trade plan: a volatility- or
structure-based stop, a target, the resulting risk/reward, an optional position
size for a given account risk budget, and an explicit invalidation condition.

Every number is a deterministic calculation from inputs already present in the
analysis -- ATR, support/resistance levels, the fused direction -- never an LLM
guess and never a probability (spec section 5: "the risk engine should use
deterministic calculations whenever possible"). When the analysis has no
directional bias, or the inputs needed for a stop are missing, it says so and
returns a plan flagged not-actionable rather than manufacturing a level. Mock or
unusable analysis is never actionable, exactly as for the analysis itself.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.analysis import TradingAnalysis
from ..domain.enums import Direction, RiskBand, SourceTier
from ..domain.provenance import Provenance
from ..domain.risk import RiskAssessment
from ..domain.structure import Level
from ..events import RiskAssessed

logger = get_logger("trading.risk")

# A rank so overall risk can be taken as the stronger of several signals.
_RANK = {RiskBand.UNKNOWN: 0, RiskBand.LOW: 1, RiskBand.MEDIUM: 2, RiskBand.HIGH: 3}


def _stronger(a: RiskBand, b: RiskBand) -> RiskBand:
    return a if _RANK[a] >= _RANK[b] else b


class RiskService:
    """Deterministic risk geometry for a directional trade idea."""

    def __init__(
        self,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def assess(
        self,
        analysis: TradingAnalysis,
        *,
        direction: Direction | None = None,
        account_equity: float | None = None,
        risk_pct: float | None = None,
    ) -> RiskAssessment:
        assessment = self._assess(
            analysis,
            direction=direction,
            account_equity=account_equity,
            risk_pct=risk_pct,
        )
        await self._emit(assessment)
        return assessment

    # ------------------------------------------------------------------

    def _assess(
        self,
        analysis: TradingAnalysis,
        *,
        direction: Direction | None,
        account_equity: float | None,
        risk_pct: float | None,
    ) -> RiskAssessment:
        s = self._settings
        atr_mult = s.TRADING_RISK_ATR_STOP_MULT
        min_reward = s.TRADING_RISK_MIN_REWARD
        pct = risk_pct if risk_pct is not None else s.TRADING_RISK_ACCOUNT_PCT

        d = direction or analysis.direction
        entry = analysis.last_price
        atr = analysis.technical.atr
        atr_pct = (atr / entry) if (atr is not None and entry > 0) else None
        volatility_risk = RiskBand.from_atr_pct(atr_pct)

        limitations = list(analysis.limitations)
        rationale: list[str] = []

        provenance = Provenance(
            source=analysis.provenance.source,
            tier=(
                SourceTier.MOCK
                if analysis.provenance.is_mock
                else SourceTier.DERIVED
            ),
            detail="deterministic risk assessment",
        )

        # No side -> no trade geometry. This is an honest, common outcome, not
        # an error: SIDEWAYS/UNKNOWN analyses simply have nothing to risk-plan.
        if d not in (Direction.UP, Direction.DOWN):
            rationale.append(
                f"Direction is '{d.value}': a risk plan needs a defined long or "
                "short side, so no stop or target was computed."
            )
            limitations.append("No directional bias; risk geometry not computed.")
            return RiskAssessment(
                instrument=analysis.instrument,
                direction=d,
                entry=entry,
                stop_loss=None,
                stop_method="none",
                target=None,
                target_method="none",
                targets=(),
                risk_per_unit=None,
                reward_per_unit=None,
                risk_reward_ratio=None,
                stop_distance_pct=None,
                atr=atr,
                atr_pct=atr_pct,
                volatility_risk=volatility_risk,
                overall_risk=_stronger(volatility_risk, RiskBand.MEDIUM),
                account_equity=account_equity,
                risk_pct=pct,
                risk_amount=None,
                position_size=None,
                position_notional=None,
                invalidation=(
                    "No stop level could be established; thesis has no defined "
                    "invalidation."
                ),
                rationale=tuple(rationale),
                quality=analysis.quality,
                provenance=provenance,
                is_actionable=False,
                limitations=tuple(limitations),
            )

        is_long = d is Direction.UP

        # ---- Stop ----------------------------------------------------
        stop_loss, stop_method = self._stop(analysis, entry, atr, atr_mult, is_long)
        if stop_method == "atr":
            rationale.append(
                f"Stop from {atr_mult:g}x ATR ({atr:.4g}) "
                f"{'below' if is_long else 'above'} entry."
            )
        elif stop_method == "structural":
            rationale.append(
                f"Stop at the nearest {'support' if is_long else 'resistance'} "
                "level (no ATR available)."
            )
        else:
            limitations.append(
                "No ATR or structural level available to place a stop."
            )
            rationale.append("No stop could be derived from the available inputs.")

        risk_per_unit = (
            abs(entry - stop_loss) if stop_loss is not None else None
        )
        stop_distance_pct = (
            (risk_per_unit / entry) if (risk_per_unit and entry > 0) else None
        )

        # ---- Target(s) ----------------------------------------------
        target, target_method, targets = self._target(
            analysis, entry, risk_per_unit, min_reward, is_long
        )
        if target_method == "structural":
            rationale.append(
                f"Target at the nearest {'resistance' if is_long else 'support'} "
                "level; further levels laddered."
            )
        elif target_method == "projected":
            rationale.append(
                f"Target projected at {min_reward:g}R (no structural "
                f"{'resistance above' if is_long else 'support below'} entry)."
            )
            limitations.append(
                "Target is projected from risk/reward, not a measured level."
            )

        reward_per_unit = (
            abs(target - entry) if target is not None else None
        )
        rr = (
            round(reward_per_unit / risk_per_unit, 4)
            if (reward_per_unit is not None and risk_per_unit and risk_per_unit > 0)
            else None
        )
        if rr is not None:
            rationale.append(f"Risk/reward ratio {rr:g} : 1.")
            if rr < min_reward:
                rationale.append(
                    f"R:R {rr:g} is below the {min_reward:g} minimum; the reward "
                    "does not justify the risk on this setup alone."
                )

        # ---- Position sizing ----------------------------------------
        risk_amount, position_size, position_notional = self._sizing(
            account_equity, pct, risk_per_unit, entry
        )
        if account_equity is None:
            limitations.append(
                "No account equity supplied; position size not computed."
            )
        elif position_size is not None:
            rationale.append(
                f"Risking {pct:g}% of {account_equity:g} = {risk_amount:.4g} "
                f"sizes the position at {position_size:.4g} units."
            )

        # ---- Overall risk -------------------------------------------
        overall = volatility_risk if volatility_risk is not RiskBand.UNKNOWN else RiskBand.MEDIUM
        if analysis.provenance.is_mock or not analysis.quality.ok:
            overall = overall.escalate()
            rationale.append("Risk escalated: data is mock or not fully clean.")
        if rr is not None and rr < 1.0:
            overall = overall.escalate()
        if stop_loss is None or rr is None:
            overall = _stronger(overall, RiskBand.MEDIUM)

        # ---- Invalidation -------------------------------------------
        if stop_loss is not None:
            invalidation = (
                f"Close {'below' if is_long else 'above'} {stop_loss:.4g} "
                f"invalidates the {'long' if is_long else 'short'} thesis."
            )
        else:
            invalidation = (
                "No stop level could be established; thesis has no defined "
                "invalidation."
            )

        # Actionable only if the *analysis* was actionable AND we have real
        # geometry (a stop and a positive reward for the risk). Mock/unusable
        # analysis is already non-actionable, so this can never dress up
        # synthetic data as a tradable plan (spec section 61).
        is_actionable = bool(
            analysis.is_actionable
            and stop_loss is not None
            and rr is not None
            and rr > 0
        )

        return RiskAssessment(
            instrument=analysis.instrument,
            direction=d,
            entry=entry,
            stop_loss=stop_loss,
            stop_method=stop_method,
            target=target,
            target_method=target_method,
            targets=targets,
            risk_per_unit=risk_per_unit,
            reward_per_unit=reward_per_unit,
            risk_reward_ratio=rr,
            stop_distance_pct=stop_distance_pct,
            atr=atr,
            atr_pct=atr_pct,
            volatility_risk=volatility_risk,
            overall_risk=overall,
            account_equity=account_equity,
            risk_pct=pct,
            risk_amount=risk_amount,
            position_size=position_size,
            position_notional=position_notional,
            invalidation=invalidation,
            rationale=tuple(rationale),
            quality=analysis.quality,
            provenance=provenance,
            is_actionable=is_actionable,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _stop(
        analysis: TradingAnalysis,
        entry: float,
        atr: float | None,
        atr_mult: float,
        is_long: bool,
    ) -> tuple[float | None, str]:
        if atr is not None and atr > 0:
            stop = entry - atr_mult * atr if is_long else entry + atr_mult * atr
            return round(stop, 6), "atr"
        # Structural fallback: nearest level on the protective side.
        levels = analysis.structure.supports if is_long else analysis.structure.resistances
        candidate = RiskService._nearest_level(levels, entry, below=is_long)
        if candidate is not None:
            return round(candidate.price, 6), "structural"
        return None, "none"

    @staticmethod
    def _target(
        analysis: TradingAnalysis,
        entry: float,
        risk_per_unit: float | None,
        min_reward: float,
        is_long: bool,
    ) -> tuple[float | None, str, tuple[float, ...]]:
        # Structural targets: levels on the profit side, ordered by proximity.
        levels = analysis.structure.resistances if is_long else analysis.structure.supports
        on_side = [
            lvl
            for lvl in levels
            if (lvl.price > entry if is_long else lvl.price < entry)
        ]
        on_side.sort(key=lambda lvl: abs(lvl.price - entry))
        if on_side:
            ladder = tuple(round(lvl.price, 6) for lvl in on_side)
            return ladder[0], "structural", ladder
        # No structural level ahead: project from R:R if we have a risk unit.
        if risk_per_unit is not None and risk_per_unit > 0:
            projected = (
                entry + min_reward * risk_per_unit
                if is_long
                else entry - min_reward * risk_per_unit
            )
            return round(projected, 6), "projected", ()
        return None, "none", ()

    @staticmethod
    def _nearest_level(
        levels: tuple[Level, ...], entry: float, *, below: bool
    ) -> Level | None:
        side = [
            lvl for lvl in levels if (lvl.price < entry if below else lvl.price > entry)
        ]
        if not side:
            return None
        return min(side, key=lambda lvl: abs(lvl.price - entry))

    @staticmethod
    def _sizing(
        account_equity: float | None,
        pct: float,
        risk_per_unit: float | None,
        entry: float,
    ) -> tuple[float | None, float | None, float | None]:
        if (
            account_equity is None
            or account_equity <= 0
            or risk_per_unit is None
            or risk_per_unit <= 0
        ):
            return None, None, None
        risk_amount = account_equity * pct / 100.0
        position_size = risk_amount / risk_per_unit
        position_notional = position_size * entry
        return (
            round(risk_amount, 6),
            round(position_size, 6),
            round(position_notional, 6),
        )

    async def _emit(self, assessment: RiskAssessment) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                RiskAssessed(
                    instrument_key=assessment.instrument.key,
                    direction=assessment.direction.value,
                    entry=assessment.entry,
                    stop_loss=assessment.stop_loss,
                    risk_reward_ratio=assessment.risk_reward_ratio,
                    overall_risk=assessment.overall_risk.value,
                    is_actionable=assessment.is_actionable,
                    source_tier=assessment.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish RiskAssessed")
