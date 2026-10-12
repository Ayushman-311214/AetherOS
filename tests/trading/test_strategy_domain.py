"""
Strategy-layer value objects: validation and serialisation.

These are the guards that keep the strategy layer honest at the model level --
a setup that is not directional, that places its invalidation on the wrong side
of its entry, or that cannot explain itself is rejected at construction rather
than travelling downstream as a plausible-looking object. Nothing here needs a
service; the models are pure.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import (
    Confidence,
    DataQualityStatus,
    Direction,
    OptimizationObjective,
    SourceTier,
    StrategyCategory,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.strategy import (
    ParameterCandidate,
    ParameterSearch,
    StrategyComparison,
    StrategyEvaluation,
    StrategyRuleMatch,
    StrategySetup,
)

CATEGORY = StrategyCategory.TREND_FOLLOWING


def _quality() -> DataQuality:
    return DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0)


def _provenance() -> Provenance:
    return Provenance(source="test", tier=SourceTier.PRIMARY, detail="fixture")


def _rules(*, satisfied: bool = True) -> tuple[StrategyRuleMatch, ...]:
    return (
        StrategyRuleMatch(
            rule="structure is directional",
            satisfied=satisfied,
            detail="Structure reads 'uptrend'.",
        ),
        StrategyRuleMatch(
            rule="trend is established (ADX)",
            satisfied=satisfied,
            detail="ADX 31.0 against a minimum of 20.0.",
            value=31.0,
            threshold=20.0,
        ),
    )


def make_setup(
    *,
    direction: Direction = Direction.UP,
    entry: float = 100.0,
    invalidation: float = 98.0,
    strategy_id: str = "trend_following",
) -> StrategySetup:
    return StrategySetup(
        instrument=Instrument.parse("TEST"),
        strategy_id=strategy_id,
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        direction=direction,
        confidence=Confidence.MEDIUM,
        entry_reference=entry,
        invalidation_level=invalidation,
        rules=_rules(),
        evidence=(),
        reasoning="Structure is up and momentum agrees.",
        quality=_quality(),
        provenance=_provenance(),
    )


# ----------------------------------------------------------------------
# StrategyRuleMatch


def test_rule_match_requires_a_name_and_a_detail():
    with pytest.raises(ValueError):
        StrategyRuleMatch(rule="  ", satisfied=True, detail="Something happened.")
    with pytest.raises(ValueError):
        StrategyRuleMatch(rule="a rule", satisfied=True, detail="")


def test_rule_match_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        StrategyRuleMatch(
            rule="a rule", satisfied=False, detail="Value was not a number.",
            value=float("nan"),
        )
    with pytest.raises(ValueError):
        StrategyRuleMatch(
            rule="a rule", satisfied=False, detail="Threshold was not a number.",
            threshold=float("inf"),
        )


def test_rule_match_serialises_satisfied_and_failed_alike():
    payload = StrategyRuleMatch(
        rule="trend is established (ADX)",
        satisfied=False,
        detail="ADX 12.0 against a minimum of 20.0.",
        value=12.0,
        threshold=20.0,
    ).to_dict()
    assert payload == {
        "rule": "trend is established (ADX)",
        "satisfied": False,
        "detail": "ADX 12.0 against a minimum of 20.0.",
        "value": 12.0,
        "threshold": 20.0,
    }


# ----------------------------------------------------------------------
# StrategySetup


def test_setup_rejects_a_non_directional_side():
    """There is no SIDEWAYS setup; a missing edge is the absence of a setup."""
    for direction in (Direction.SIDEWAYS, Direction.UNKNOWN):
        with pytest.raises(ValueError, match="must be directional"):
            make_setup(direction=direction)


def test_bullish_setup_invalidation_must_sit_below_entry():
    with pytest.raises(ValueError, match="must sit below its entry"):
        make_setup(direction=Direction.UP, entry=100.0, invalidation=101.0)


def test_bearish_setup_invalidation_must_sit_above_entry():
    with pytest.raises(ValueError, match="must sit above its entry"):
        make_setup(direction=Direction.DOWN, entry=100.0, invalidation=99.0)


def test_setup_rejects_a_non_positive_price():
    with pytest.raises(ValueError, match="finite positive price"):
        make_setup(entry=0.0)


def test_setup_requires_reasoning():
    with pytest.raises(ValueError, match="explain itself"):
        StrategySetup(
            instrument=Instrument.parse("TEST"),
            strategy_id="trend_following",
            strategy_name="Trend Following",
            category=CATEGORY,
            timeframe="1d",
            direction=Direction.UP,
            confidence=Confidence.MEDIUM,
            entry_reference=100.0,
            invalidation_level=98.0,
            rules=_rules(),
            evidence=(),
            reasoning="   ",
            quality=_quality(),
            provenance=_provenance(),
        )


def test_setup_requires_at_least_one_satisfied_rule():
    with pytest.raises(ValueError, match="at least one satisfied rule"):
        StrategySetup(
            instrument=Instrument.parse("TEST"),
            strategy_id="trend_following",
            strategy_name="Trend Following",
            category=CATEGORY,
            timeframe="1d",
            direction=Direction.UP,
            confidence=Confidence.MEDIUM,
            entry_reference=100.0,
            invalidation_level=98.0,
            rules=_rules(satisfied=False),
            evidence=(),
            reasoning="Nothing held, but a setup was built anyway.",
            quality=_quality(),
            provenance=_provenance(),
        )


def test_setup_id_is_content_addressed_and_stable():
    first = make_setup()
    second = make_setup()
    assert first.setup_id == second.setup_id
    assert first.setup_id.startswith("su_")

    # Same reading at a different price is a *different* setup: the id must
    # distinguish them, or the audit trail would merge two distinct events.
    moved = make_setup(entry=101.0, invalidation=98.0)
    assert moved.setup_id != first.setup_id


def test_setup_risk_distance_and_satisfied_rules():
    setup = make_setup(entry=100.0, invalidation=98.5)
    assert setup.risk_distance == pytest.approx(1.5)
    assert len(setup.satisfied_rules) == 2

    # A mixed rule set: the first rule failed, the second held. The failed
    # rule is retained in ``rules`` and excluded from the satisfied view --
    # never dropped.
    mixed = StrategySetup(
        instrument=Instrument.parse("TEST"),
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        direction=Direction.UP,
        confidence=Confidence.LOW,
        entry_reference=100.0,
        invalidation_level=98.0,
        rules=(
            StrategyRuleMatch(
                rule="structure is directional",
                satisfied=False,
                detail="Structure reads 'range'.",
            ),
            _rules()[1],
        ),
        evidence=(),
        reasoning="Only the ADX rule held from this set.",
        quality=_quality(),
        provenance=_provenance(),
    )
    assert len(mixed.rules) == 2
    assert len(mixed.satisfied_rules) == 1


def test_setup_to_dict_exposes_the_geometry_and_the_rules():
    payload = make_setup().to_dict()
    assert payload["direction"] == "up"
    assert payload["entry_reference"] == 100.0
    assert payload["invalidation_level"] == 98.0
    assert payload["risk_distance"] == pytest.approx(2.0)
    assert len(payload["rules"]) == 2
    # Deliberately absent: a setup carries no stop, target, size or ratio.
    for forbidden in ("stop_loss", "take_profit", "quantity", "risk_reward"):
        assert forbidden not in payload


# ----------------------------------------------------------------------
# StrategyEvaluation


def test_evaluation_without_a_setup_is_unknown_and_not_a_failure():
    evaluation = StrategyEvaluation(
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        # A failed rule set -- evaluations are allowed to hold them without
        # any of them being satisfied.
        rules=_rules(satisfied=False),
        limitations=("Trend Following: no setup -- unmet conditions: structural conviction.",),
    )
    assert not evaluation.fired
    assert evaluation.direction is Direction.UNKNOWN
    assert len(evaluation.failed_rules) == 2


def test_evaluation_rejects_a_setup_from_another_strategy():
    with pytest.raises(ValueError, match="must come from that strategy"):
        StrategyEvaluation(
            strategy_id="mean_reversion",
            strategy_name="Mean Reversion",
            category=StrategyCategory.MEAN_REVERSION,
            timeframe="1d",
            setup=make_setup(strategy_id="trend_following"),
        )


def test_evaluation_to_dict_reports_fired_and_direction():
    evaluation = StrategyEvaluation(
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        setup=make_setup(),
    )
    payload = evaluation.to_dict()
    assert payload["fired"] is True
    assert payload["direction"] == "up"
    assert payload["setup"]["strategy_id"] == "trend_following"


# ----------------------------------------------------------------------
# StrategyComparison


def _comparison(**overrides) -> StrategyComparison:
    evaluations = overrides.pop(
        "evaluations",
        (
            StrategyEvaluation(
                strategy_id="trend_following",
                strategy_name="Trend Following",
                category=CATEGORY,
                timeframe="1d",
                setup=make_setup(),
            ),
        ),
    )
    defaults = dict(
        instrument_key="TEST",
        timeframe="1d",
        evaluations=evaluations,
        consensus=Direction.UP,
        agreement=1.0,
        bullish=1,
        bearish=0,
        dissenting=(),
        provenance=_provenance(),
    )
    defaults.update(overrides)
    return StrategyComparison(**defaults)


def test_comparison_reports_setups_and_consensus():
    comparison = _comparison()
    assert comparison.setup_count == 1
    assert comparison.consensus is Direction.UP
    assert comparison.is_unanimous


def test_a_single_firing_strategy_is_not_a_unanimous_panel():
    """One opinion is not a panel verdict, however many strategies were asked."""
    quiet = StrategyEvaluation(
        strategy_id="mean_reversion",
        strategy_name="Mean Reversion",
        category=StrategyCategory.MEAN_REVERSION,
        timeframe="1d",
        rules=_rules(satisfied=False),
    )
    comparison = _comparison(evaluations=(*_comparison().evaluations, quiet))
    assert comparison.setup_count == 1
    assert not comparison.is_unanimous


def test_split_panel_has_no_consensus_and_lists_every_side():
    up = StrategyEvaluation(
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        setup=make_setup(),
    )
    down = StrategyEvaluation(
        strategy_id="smc",
        strategy_name="SMC Structure",
        category=StrategyCategory.SMC,
        timeframe="1d",
        setup=make_setup(
            direction=Direction.DOWN, entry=100.0, invalidation=102.0, strategy_id="smc"
        ),
    )
    comparison = _comparison(
        evaluations=(up, down),
        consensus=Direction.UNKNOWN,
        agreement=None,
        bullish=1,
        bearish=1,
        dissenting=("trend_following", "smc"),
    )
    assert not comparison.is_unanimous
    assert comparison.consensus is Direction.UNKNOWN
    assert comparison.agreement is None
    assert set(comparison.dissenting) == {"trend_following", "smc"}


def test_comparison_validates_counts_and_agreement():
    with pytest.raises(ValueError, match="cannot be negative"):
        _comparison(bullish=-1)
    with pytest.raises(ValueError, match="within 0 and 1"):
        _comparison(agreement=1.5)


# ----------------------------------------------------------------------
# Parameter search


def _candidate(
    *, score: float | None, reliable: bool, baseline: bool = False, **params
) -> ParameterCandidate:
    return ParameterCandidate(
        strategy_id="trend_following",
        parameters=tuple(params.items()) or (("min_adx", 20.0),),
        score=score,
        directional_accuracy=score,
        cumulative_return=0.05,
        max_drawdown=0.02,
        sharpe=1.1,
        directional_calls=48,
        is_reliable=reliable,
        is_baseline=baseline,
    )


def test_candidate_rejects_duplicate_or_empty_parameter_keys():
    with pytest.raises(ValueError, match="unique"):
        ParameterCandidate(
            strategy_id="trend_following",
            parameters=(("min_adx", 20.0), ("min_adx", 25.0)),
            score=0.5,
            directional_accuracy=0.5,
            cumulative_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
            directional_calls=10,
            is_reliable=True,
        )


def test_search_requires_candidates_from_its_own_strategy():
    with pytest.raises(ValueError, match="baseline must come from that strategy"):
        ParameterSearch(
            strategy_id="trend_following",
            objective=OptimizationObjective.DIRECTIONAL_ACCURACY,
            baseline=ParameterCandidate(
                strategy_id="smc",
                parameters=(("min_adx", 20.0),),
                score=0.5,
                directional_accuracy=0.5,
                cumulative_return=0.0,
                max_drawdown=0.0,
                sharpe=0.0,
                directional_calls=10,
                is_reliable=True,
            ),
            candidates=(),
            best=None,
            provenance=_provenance(),
        )


def _search(best: ParameterCandidate | None, baseline: ParameterCandidate) -> ParameterSearch:
    return ParameterSearch(
        strategy_id="trend_following",
        objective=OptimizationObjective.DIRECTIONAL_ACCURACY,
        baseline=baseline,
        candidates=(baseline,) + ((best,) if best is not None else ()),
        best=best,
        provenance=_provenance(),
    )


def test_search_without_a_reliable_winner_is_not_an_improvement():
    baseline = _candidate(score=0.55, reliable=True, baseline=True)
    assert not _search(None, baseline).improved
    assert _search(None, baseline).best is None


def test_search_improvement_requires_a_higher_score():
    baseline = _candidate(score=0.55, reliable=True, baseline=True)
    assert _search(_candidate(score=0.61, reliable=True), baseline).improved
    assert not _search(_candidate(score=0.55, reliable=True), baseline).improved
    assert not _search(_candidate(score=0.40, reliable=True), baseline).improved


def test_ranking_puts_reliable_candidates_first():
    baseline = _candidate(score=0.90, reliable=False, baseline=True)
    strong = _candidate(score=0.55, reliable=True)
    search = _search(strong, baseline)
    ranked = search.ranked()
    assert ranked[0] is strong
    assert ranked[-1] is baseline


def test_optimization_objectives_match_the_backtest_metrics():
    assert {member.value for member in OptimizationObjective} == {
        "directional_accuracy",
        "cumulative_return",
        "sharpe",
    }
