"""
Backtest metrics (Phase 6).

Deterministic aggregation of resolved ``EnrichedOutcome``s into the spec's
metric set, plus the liquidity-specific rates. Pure functions over a sequence
of outcomes the caller already holds -- no I/O, no fitting. Where a metric has
no meaningful value (e.g. precision with no positive calls), it is ``None``
rather than a fabricated number -- the honest "not measurable" answer.

A thin or mock sample is reported, not hidden: ``is_reliable`` is False when
the scored count is below the configured floor or any outcome was resolved on
MOCK data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .outcome import EnrichedOutcome

#: A metric is only reported as reliable over at least this many scored outcomes.
MIN_SAMPLE = 10


def _r(v: float | None) -> float | None:
    return round(v, 6) if v is not None else None


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """The deterministic performance read over a batch of outcomes."""

    sample_size: int
    resolved: int
    pending: int
    unresolvable: int
    scored: int               # resolved directional outcomes

    # Directional measures (None when not measurable).
    accuracy: float | None          # hits / scored
    precision: float | None         # hits / calls-that-were-made (directional)
    recall: float | None            # hits / actual directional outcomes
    win_rate: float | None          # share of resolved calls that won
    loss_rate: float | None         # share of resolved calls that lost
    false_signal_rate: float | None # share of directional calls that were wrong

    # Return measures.
    expected_return: float | None   # mean realised return over resolved
    mean_mfe: float | None          # mean max favorable excursion
    mean_mae: float | None          # mean max adverse excursion
    profit_factor: float | None     # gross wins / gross losses (None if no losses)
    risk_reward_mean: float | None  # mean |reward| / |risk| where both defined

    # Level-interaction rates.
    target_hit_rate: float | None         # share of stated-target calls hit
    invalidation_hit_rate: float | None   # share of stated-invalidation calls hit
    zone_reaction_rate: float | None      # share of directional calls that resolved hit
    sweep_reversal_rate: float | None     # share of sweeps resolving as rejection
    sweep_continuation_rate: float | None # share of sweeps resolving as acceptance
    absorption_success_rate: float | None # share of absorbed zones that held
    replenishment_significance: float | None
    persistence_significance: float | None

    is_reliable: bool
    is_mock: bool
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "resolved": self.resolved,
            "pending": self.pending,
            "unresolvable": self.unresolvable,
            "scored": self.scored,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "false_signal_rate": self.false_signal_rate,
            "expected_return": self.expected_return,
            "mean_mfe": self.mean_mfe,
            "mean_mae": self.mean_mae,
            "profit_factor": self.profit_factor,
            "risk_reward_mean": self.risk_reward_mean,
            "target_hit_rate": self.target_hit_rate,
            "invalidation_hit_rate": self.invalidation_hit_rate,
            "zone_reaction_rate": self.zone_reaction_rate,
            "sweep_reversal_rate": self.sweep_reversal_rate,
            "sweep_continuation_rate": self.sweep_continuation_rate,
            "absorption_success_rate": self.absorption_success_rate,
            "replenishment_significance": self.replenishment_significance,
            "persistence_significance": self.persistence_significance,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
            "limitations": list(self.limitations),
        }


def _hits(outcomes: list[EnrichedOutcome]) -> list[bool]:
    return [o.is_correct for o in outcomes if o.is_correct is not None]


def evaluate(
    outcomes: list[EnrichedOutcome],
    *,
    min_sample: int = MIN_SAMPLE,
) -> BacktestMetrics:
    """
    Aggregate a batch of ``EnrichedOutcome``s into the metric set.

    Only RESOLVED outcomes enter the scored/return measures; PENDING and
    UNRESOLVABLE are tallied for transparency, never scored as hits or misses.
    """
    sample = len(outcomes)
    resolved = [o for o in outcomes if o.status == "resolved"]
    pending = sum(1 for o in outcomes if o.status == "pending")
    unresolvable = sum(1 for o in outcomes if o.status == "unresolvable")

    scored_outcomes = [o for o in resolved if o.is_correct is not None]
    scored = len(scored_outcomes)
    hits = sum(1 for o in scored_outcomes if o.is_correct)
    misses = scored - hits
    calls_made = sum(
        1 for o in scored_outcomes
        if o.direction.value in ("up", "down")
    )
    realized_dir = sum(
        1 for o in scored_outcomes
        if o.realized_direction is not None
        and o.realized_direction.value in ("up", "down")
    )

    accuracy = _r(hits / scored) if scored else None
    precision = _r(hits / calls_made) if calls_made else None
    recall = _r(hits / realized_dir) if realized_dir else None
    win_rate = _r(hits / len(resolved)) if resolved else None
    loss_rate = _r(misses / len(resolved)) if resolved else None
    false_rate = _r(misses / scored) if scored else None

    returns = [o.realized_return for o in resolved if o.realized_return is not None]
    expected = _r(sum(returns) / len(returns)) if returns else None
    mfes = [o.max_favorable_excursion for o in resolved if o.max_favorable_excursion is not None]
    maes = [o.max_adverse_excursion for o in resolved if o.max_adverse_excursion is not None]
    mean_mfe = _r(sum(mfes) / len(mfes)) if mfes else None
    mean_mae = _r(sum(maes) / len(maes)) if maes else None

    # Profit factor: gross wins / gross losses, signed returns.
    wins = sum(r for r in returns if r > 0)
    losses = abs(sum(r for r in returns if r < 0))
    profit_factor = (
        _r(wins / losses) if losses > 0
        else (float("inf") if wins > 0 else None)
    )

    # Risk/reward mean: |reward| / |risk| where both excursion magnitudes exist.
    rr_pairs = [
        abs(o.max_favorable_excursion) / abs(o.max_adverse_excursion)
        for o in resolved
        if o.max_favorable_excursion is not None
        and o.max_adverse_excursion is not None
        and o.max_adverse_excursion != 0
    ]
    rr_mean = _r(sum(rr_pairs) / len(rr_pairs)) if rr_pairs else None

    # Level-interaction rates.
    with_target = [o for o in resolved if o.target is not None]
    target_rate = (
        _r(sum(1 for o in with_target if o.target_hit) / len(with_target))
        if with_target else None
    )
    with_inv = [o for o in resolved if o.invalidation_price is not None]
    inv_rate = (
        _r(sum(1 for o in with_inv if o.invalidation_hit) / len(with_inv))
        if with_inv else None
    )

    # Liquidity-specific rates (see liquidity_metrics for the per-event detail;
    # here they're approximated over outcomes carrying the relevant flags).
    zone_rxn = _r(hits / scored) if scored else None  # = directional accuracy
    sweep_rev, sweep_cont, absorb = _liquidity_rates(resolved)
    replenish, persist = _significance(resolved)

    is_mock = any(o.is_mock for o in resolved)
    is_reliable = scored >= min_sample and not is_mock
    limitations = _limitations(
        sample_size=sample, resolved=len(resolved), scored=scored,
        min_sample=min_sample, is_mock=is_mock,
    )

    return BacktestMetrics(
        sample_size=sample,
        resolved=len(resolved),
        pending=pending,
        unresolvable=unresolvable,
        scored=scored,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        win_rate=win_rate,
        loss_rate=loss_rate,
        false_signal_rate=false_rate,
        expected_return=expected,
        mean_mfe=mean_mfe,
        mean_mae=mean_mae,
        profit_factor=profit_factor,
        risk_reward_mean=rr_mean,
        target_hit_rate=target_rate,
        invalidation_hit_rate=inv_rate,
        zone_reaction_rate=zone_rxn,
        sweep_reversal_rate=sweep_rev,
        sweep_continuation_rate=sweep_cont,
        absorption_success_rate=absorb,
        replenishment_significance=replenish,
        persistence_significance=persist,
        is_reliable=is_reliable,
        is_mock=is_mock,
        limitations=tuple(limitations),
    )


def _liquidity_rates(resolved):
    """
    Liquidity-specific rates read off outcomes that carry liquidity-event
    context in ``limitations`` (e.g. "sweep:rejection" / "sweep:acceptance" /
    "absorbed"). Returns ``(sweep_reversal, sweep_continuation, absorption)``;
    ``None`` when no such context exists -- the honest "not measured".
    """
    sweeps = [
        o for o in resolved
        if any("sweep:" in lim for lim in o.limitations)
    ]
    rev = (
        _r(sum(1 for o in sweeps if any("rejection" in lim for lim in o.limitations)) / len(sweeps))
        if sweeps else None
    )
    cont = (
        _r(sum(1 for o in sweeps if any("acceptance" in lim for lim in o.limitations)) / len(sweeps))
        if sweeps else None
    )
    absorbed = [
        o for o in resolved
        if any("absorbed" in lim for lim in o.limitations)
    ]
    absorb = (
        _r(sum(1 for o in absorbed if o.is_correct) / len(absorbed))
        if absorbed else None
    )
    return rev, cont, absorb


def _significance(resolved):
    """
    Replenishment / persistence significance: the directional-accuracy lift of
    outcomes that carried those contexts vs those that did not, in [-1,1].
    ``None`` when the context is absent -- honest "not measured".
    """
    def _lift(ctx_key: str) -> float | None:
        with_ctx = [
            o for o in resolved
            if o.is_correct is not None
            and any(ctx_key in lim for lim in o.limitations)
        ]
        without = [
            o for o in resolved
            if o.is_correct is not None
            and not any(ctx_key in lim for lim in o.limitations)
        ]
        if not with_ctx or not without:
            return None
        acc_w = sum(1 for o in with_ctx if o.is_correct) / len(with_ctx)
        acc_wo = sum(1 for o in without if o.is_correct) / len(without)
        return _r(acc_w - acc_wo)
    return _lift("replenished"), _lift("persistent")


def _limitations(*, sample_size, resolved, scored, min_sample, is_mock):
    lim: list[str] = []
    if sample_size == 0:
        lim.append("No outcomes supplied; nothing to measure.")
        return lim
    if resolved == 0:
        lim.append("No resolved outcomes; performance cannot be measured.")
    if scored == 0:
        lim.append("No scored directional outcomes.")
    elif scored < min_sample:
        lim.append(
            f"Only {scored} scored outcome(s), below the minimum of "
            f"{min_sample}; the aggregate is reported, not a reliable record."
        )
    if is_mock:
        lim.append(
            "Sample includes outcomes resolved on MOCK data; not a real "
            "track record."
        )
    return lim
