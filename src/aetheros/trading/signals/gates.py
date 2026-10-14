"""
Signal gates (spec Phase 8).

The signal engine's job is *deciding when not to propose*. Every fired signal
passes through the same fixed gate sequence, and every gate that stops a
candidate names itself in ``rejections`` -- a candidate that failed three
gates says which three, in order, so the trail reads as an audit log rather
than a bare None.

The gates are deliberately deterministic and enumerable:

1. **Side agreement** -- the risk geometry and the setup must describe the
   same trade. A bullish setup with bearish risk geometry is a wiring bug,
   not a signal, and is rejected rather than "resolved".
2. **Actionability** -- mock or unusable data never produces a proposal.
3. **Critic verdict** -- the adversary must have approved. A REJECT or
   INSUFFICIENT_EVIDENCE critique is a hard stop; the signal engine never
   overrules the critic, because a signal "more confident than the adversary
   that judged it" is exactly the overconfidence section 3 forbids.
4. **Risk/reward** -- the assessment must carry a finite, positive ratio and
   meet the configured minimum. No ratio (no measurable stop or target) is
   an honest decline, not a zero.

The reasoning string a fired signal carries is composed from the *actual*
inputs -- setup reasoning, stop and target with their methods, the risk band,
the critic's verdict -- never a template that could survive empty inputs.
"""

from __future__ import annotations

from ..domain.critique import CriticReport
from ..domain.enums import CriticVerdict, Direction, RiskBand, TradeAction
from ..domain.evidence import Evidence
from ..domain.risk import RiskAssessment
from ..domain.strategy import StrategySetup
from ..domain.trade import TradeSignal

#: Divider between the composed reasoning clauses.
_REASONING_JOIN = " "

#: How a gate's rejection is worded in the candidate's trail.
_REJECT_PREFIX = "Gate"


def _action(direction: Direction) -> TradeAction:
    """The entry action a directional proposal maps to."""
    return TradeAction.BUY if direction is Direction.UP else TradeAction.SELL


def _side_agrees(setup: StrategySetup, risk: RiskAssessment) -> bool:
    return setup.direction is risk.direction


def _risk_reward_ok(
    risk: RiskAssessment, *, min_reward: float
) -> tuple[bool, str | None]:
    """Whether the assessment carries an acceptable risk/reward ratio."""
    if risk.risk_reward_ratio is None:
        return False, (
            f"{_REJECT_PREFIX} risk_reward: no measurable stop/target pair, so no "
            "ratio exists; a proposal without risk geometry is not made."
        )
    if risk.risk_reward_ratio < min_reward:
        return False, (
            f"{_REJECT_PREFIX} risk_reward: ratio {risk.risk_reward_ratio:.2f} "
            f"below the configured minimum {min_reward:.2f}."
        )
    return True, None


def _side_clause(risk: RiskAssessment) -> str:
    side = "long" if risk.direction is Direction.UP else "short"
    return f"Proposing {side} {risk.instrument.symbol} at {risk.entry:.4f}."


def _geometry_clause(risk: RiskAssessment) -> str:
    stop = (
        f"stop {risk.stop_loss:.4f} ({risk.stop_method})"
        if risk.stop_loss is not None
        else "no stop"
    )
    if risk.target is not None:
        target = f"target {risk.target:.4f} ({risk.target_method})"
    else:
        target = "no target"
    ratio = (
        f"{risk.risk_reward_ratio:.2f}:1"
        if risk.risk_reward_ratio is not None
        else "ratio unmeasured"
    )
    return f"Geometry: {stop}, {target}, risk/reward {ratio}."


def _critique_clause(critique: CriticReport) -> str:
    return f"Critic verdict: {critique.verdict.value}."


def _compose_reasoning(
    setup: StrategySetup, risk: RiskAssessment, critique: CriticReport
) -> str:
    """The signal's own account of itself, from its actual inputs."""
    clauses = [
        _side_clause(risk),
        f"{setup.reasoning}",
        _geometry_clause(risk),
        _critique_clause(critique),
    ]
    return _REASONING_JOIN.join(clause for clause in clauses if clause.strip())


def _evidence(
    setup: StrategySetup, risk: RiskAssessment
) -> tuple[Evidence, ...]:
    """
    The signal's supporting evidence: the setup's own claims.

    The risk geometry is deliberately excluded -- a stop level is a property
    of the proposal, not a claim about the market, and dressing a risk level
    up as evidence repeats the conflation the strategy layer already refuses.
    """
    return setup.evidence


def _risk_band(risk: RiskAssessment) -> RiskBand:
    return risk.overall_risk


def evaluate_candidate(
    setup: StrategySetup,
    risk: RiskAssessment,
    critique: CriticReport,
    *,
    min_reward: float,
) -> tuple[TradeSignal | None, tuple[str, ...]]:
    """
    Run the gate sequence for one candidate.

    Returns ``(signal, rejections)``: the proposed :class:`TradeSignal` and no
    rejections when every gate passed, or ``None`` plus the ordered reasons
    for each gate that stopped it.
    """
    if not _side_agrees(setup, risk):
        return None, (
            f"{_REJECT_PREFIX} side: the setup reads {setup.direction.value} "
            f"while the risk geometry reads {risk.direction.value}; these must "
            "describe the same trade.",
        )

    if not risk.is_actionable:
        return None, (
            f"{_REJECT_PREFIX} actionable: the risk assessment is not actionable "
            "(mock, unusable, or absent geometry); no proposal is made from it.",
        )

    if critique.verdict is not CriticVerdict.APPROVE:
        return None, (
            f"{_REJECT_PREFIX} critic: verdict {critique.verdict.value}, and the "
            "signal engine never overrules the adversary that judged the setup.",
        )

    ok, reason = _risk_reward_ok(risk, min_reward=min_reward)
    if not ok:
        assert reason is not None
        return None, (reason,)

    signal = TradeSignal(
        instrument=risk.instrument,
        action=_action(risk.direction),
        direction=risk.direction,
        confidence=setup.confidence,
        risk=_risk_band(risk),
        reasoning=_compose_reasoning(setup, risk, critique),
        evidence=_evidence(setup, risk),
        entry=risk.entry,
        stop_loss=risk.stop_loss,
        take_profit=risk.target,
        strategy_id=setup.strategy_id,
    )
    return signal, ()
