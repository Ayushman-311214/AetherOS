"""
ExplanationService: deterministic, read-only "why" over a trading report.

These are integration tests over the real orchestrated pipeline on the
clearly-labelled MockMarketDataProvider, so the explanation is pinned against a
real report (CLAUDE.md sections 1, 27, 28): a MOCK-data report must explain
itself as the NO_TRADE it is, must count evidence but let no mock item move the
net weight, must never be actionable, and the explanation must be a pure
synthesis -- its direction/recommendation read straight off the report.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, ReportRecommendation
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.explanation_service import ExplanationService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


def _orchestrator() -> OrchestrationService:
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )
    return OrchestrationService(
        market_data,
        analysis,
        RiskService(settings),
        BacktestService(settings),
        CriticService(settings),
        settings,
    )


def _service() -> ExplanationService:
    return ExplanationService(get_settings())


async def _explain(symbol: str = "AAPL"):
    report = await _orchestrator().generate_report(symbol, "1d", limit=120)
    return _service().explain(report), report


@pytest.mark.asyncio
async def test_mock_report_explains_itself_as_no_trade():
    explanation, report = await _explain()

    # Pure synthesis -- the explanation mirrors the report it was built from.
    assert explanation.recommendation is ReportRecommendation.NO_TRADE
    assert explanation.recommendation is report.recommendation
    assert explanation.direction is report.direction
    assert explanation.is_actionable is False
    assert "NO_TRADE" in explanation.summary


@pytest.mark.asyncio
async def test_mock_evidence_never_moves_the_net_weight():
    explanation, _ = await _explain()

    # Evidence is counted, but on MOCK data none of it is reliable, so nothing is
    # placed for/against and the net weight is exactly zero (never fabricated).
    assert explanation.total_evidence_count >= 0
    assert explanation.reliable_evidence_count == 0
    assert explanation.supporting == ()
    assert explanation.opposing == ()
    assert explanation.supporting_weight == 0.0
    assert explanation.opposing_weight == 0.0
    assert explanation.net_weight == 0.0


@pytest.mark.asyncio
async def test_to_dict_shape_is_complete():
    explanation, _ = await _explain()
    payload = explanation.to_dict()

    for key in (
        "instrument",
        "timeframe",
        "direction",
        "recommendation",
        "confidence",
        "is_actionable",
        "summary",
        "supporting",
        "opposing",
        "supporting_weight",
        "opposing_weight",
        "net_weight",
        "reliable_evidence_count",
        "total_evidence_count",
        "critic_reasons",
        "limitations",
    ):
        assert key in payload, f"missing explanation key: {key}"


@pytest.mark.asyncio
async def test_is_deterministic():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)
    a = _service().explain(report).to_dict()
    b = _service().explain(report).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b
