"""
Trading decision: the structured, explainable decision record (Phase 20).

The decision layer consumes the deterministic report, the strategy panel's
evaluations and (optionally) the hybrid visual read, and produces one
structured decision: market view, setup, direction, confidence, supporting
and contradictory evidence, entry/stop/target/risk-reward/invalidation,
reasoning, uncertainty and provenance. It assembles; it computes nothing --
every number is lifted verbatim, the decision never exceeds its report, and
nothing here can reach a broker.

These tests run the real deterministic pipeline on the mock provider (no
network, no display): a MOCK run must decide NO_TRADE with the uncertainty
stated, the geometry must match the risk assessment verbatim, and the visual
note must stay a note -- never a number.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction
from aetheros.trading.domain.report import TradingReport
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.chart_service import ChartService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.decision_service import DecisionService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.explanation_service import ExplanationService
from aetheros.trading.services.hybrid_service import HybridContextService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.liquidity_service import LiquidityService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.services.visual_service import VisualObservationService


def _wiring():
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    structure = MarketStructureService()
    evidence = EvidenceService()
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        structure,
        evidence,
        settings,
    )
    risk = RiskService(settings)
    backtest = BacktestService(settings)
    critic = CriticService(settings)
    orchestrator = OrchestrationService(
        market_data, analysis, risk, backtest, critic, settings
    )
    smc = SMCService(structure)
    ict = ICTService(structure, smc)
    strategy = StrategyService(
        analysis,
        structure,
        smc=smc,
        ict=ict,
        breakout=BreakoutService(settings),
        backtest=backtest,
    )
    explanation = ExplanationService(settings)
    decision = DecisionService(orchestrator, market_data, strategy, explanation)
    hybrid = HybridContextService(
        orchestrator,
        market_data,
        ChartService(),
        VisualObservationService(),
        vision_factory=lambda: None,
    )
    context_service = LiquidityService()
    return decision, hybrid, orchestrator, strategy, explanation, context_service


async def _report(wiring) -> TradingReport:
    _decision, _hybrid, orchestrator, _strategy, _explanation, _liquidity = wiring
    return await orchestrator.generate_report("AAPL", "1d", limit=120)


# ==============================================================
# The full decide() path on mock data
# ==============================================================


@pytest.mark.asyncio
async def test_mock_run_decides_no_trade_with_stated_uncertainty():
    decision_service, _hybrid, _orch, _strategy, _explanation, _liquidity = _wiring()
    decision = await decision_service.decide("AAPL", timeframe="1d", limit=120)
    assert decision.recommendation.value == "no_trade"
    assert decision.is_actionable is False
    assert decision.uncertainty, "a NO_TRADE must say what is uncertain"
    assert decision.reasoning.strip()
    assert decision.invalidation.strip()
    assert decision.market_view.startswith(decision.instrument.key)


@pytest.mark.asyncio
async def test_geometry_is_lifted_verbatim_from_the_risk_assessment():
    wiring = _wiring()
    decision_service, _hybrid, _orch, _strategy, _explanation, _liquidity = wiring
    report = await _report(wiring)
    decision = await decision_service.decide("AAPL", timeframe="1d", limit=120)
    assert decision.entry == report.risk.entry
    assert decision.stop_loss == report.risk.stop_loss
    assert decision.take_profit == report.risk.target
    assert decision.risk_reward_ratio == report.risk.risk_reward_ratio
    assert decision.invalidation == report.risk.invalidation
    assert decision.direction is report.direction
    assert decision.confidence is report.confidence


@pytest.mark.asyncio
async def test_evidence_sides_match_the_explanation_ledger():
    wiring = _wiring()
    decision_service, _hybrid, _orch, _strategy, explanation, _liquidity = wiring
    report = await _report(wiring)
    ledger = explanation.explain(report)
    decision = await decision_service.decide("AAPL", timeframe="1d", limit=120)
    assert decision.supporting_weight == ledger.supporting_weight
    assert decision.contradictory_weight == ledger.opposing_weight
    assert decision.net_weight == ledger.net_weight
    assert len(decision.supporting) == len(ledger.supporting)
    assert len(decision.contradictory) == len(ledger.opposing)


@pytest.mark.asyncio
async def test_hybrid_visual_arrives_as_a_note_never_a_number():
    wiring = _wiring()
    decision_service, hybrid, _orch, _strategy, _explanation, _liquidity = wiring
    context = await hybrid.build("AAPL", "1d", limit=120, with_visual=False)
    decision = await decision_service.decide(
        "AAPL", timeframe="1d", limit=120, hybrid=context
    )
    assert decision.visual_note is not None
    assert "screenshot" in decision.visual_note.lower() or "visual" in decision.visual_note.lower()
    # The note changed nothing about the call: the decision still mirrors
    # the deterministic report it was built from.
    assert decision.recommendation.value == "no_trade"
    assert decision.is_actionable is False


# ==============================================================
# assemble(): pure unit coverage
# ==============================================================


@pytest.mark.asyncio
async def test_assemble_never_exceeds_its_report():
    wiring = _wiring()
    decision_service, _hybrid, _orch, _strategy, explanation, _liquidity = wiring
    report = await _report(wiring)
    ledger = explanation.explain(report)
    decision = DecisionService.assemble(report, ledger, None, [])
    assert decision.direction is report.direction
    assert decision.recommendation is report.recommendation
    assert decision.is_actionable is report.is_actionable
    assert decision.setup_id is None
    assert decision.strategy_id is None


@pytest.mark.asyncio
async def test_decide_picks_the_agreeing_setup():
    wiring = _wiring()
    decision_service, _hybrid, _orch, strategy, _explanation, _liquidity = wiring
    report = await _report(wiring)
    data = await wiring[2]._market_data.get_candles("AAPL", "1d", limit=120)
    comparison = await strategy.compare(data)
    decision = await decision_service.decide(
        "AAPL", timeframe="1d", limit=120, report=report,
        evaluations=list(comparison.evaluations),
    )
    firing = [e for e in comparison.evaluations if e.fired]
    if report.direction in (Direction.UP, Direction.DOWN):
        agreeing = [e for e in firing if e.direction is report.direction]
        if agreeing:
            assert decision.setup_id is not None
            assert decision.strategy_id is not None
        else:
            assert decision.setup_id is None
    else:
        assert decision.setup_id is None


@pytest.mark.asyncio
async def test_decision_validation_guards():
    wiring = _wiring()
    decision_service, _hybrid, _orch, _strategy, _explanation, _liquidity = wiring
    import dataclasses

    decision = await decision_service.decide("AAPL", timeframe="1d", limit=120)
    with pytest.raises(ValueError, match="market view"):
        dataclasses.replace(decision, market_view="  ")
    with pytest.raises(ValueError, match="reasoning"):
        dataclasses.replace(decision, reasoning="")
    with pytest.raises(ValueError, match="invalidation"):
        dataclasses.replace(decision, invalidation=" ")


@pytest.mark.asyncio
async def test_decision_to_dict_shape():
    wiring = _wiring()
    decision_service, _hybrid, _orch, _s, _e, _l = wiring
    decision = await decision_service.decide("AAPL", timeframe="1d", limit=120)
    payload = decision.to_dict()
    for key in (
        "market_view", "direction", "confidence", "supporting", "contradictory",
        "entry", "stop_loss", "take_profit", "risk_reward_ratio", "invalidation",
        "reasoning", "uncertainty", "provenance",
    ):
        assert key in payload
    assert "created_at" in payload
