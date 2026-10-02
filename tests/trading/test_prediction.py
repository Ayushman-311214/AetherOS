"""
PredictionRecord: the auditable section-8 prediction contract.

These tests pin the honesty contract of the record itself (CLAUDE.md sections
8, 15, 19, 28): a record is built purely from a composed TradingReport, its id
is content-addressed and deterministic for the same report, it never fabricates
a probability the report withheld, and a NO_TRADE-on-mock call is preserved
verbatim rather than upgraded to a confident fact. It also round-trips through
``to_dict``/``from_dict`` without loss so a durable store can serialise it.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
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


@pytest.mark.asyncio
async def test_record_captures_section_8_contract():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    record = PredictionRecord.from_report(report)
    payload = record.to_dict()

    # Every section-8 contract field is present and traceable to the report.
    assert record.instrument_key == report.instrument.key
    assert record.timeframe == report.analysis.timeframe_value
    assert record.created_at == report.created_at
    assert record.horizon_bars == report.horizon
    assert record.recommendation == report.recommendation.value
    assert record.direction == report.direction.value
    assert record.confidence == report.confidence.value
    assert record.model_pipeline == report.pipeline_version
    assert record.invalidation == report.risk.invalidation
    assert record.id.startswith("pred_")
    for key in (
        "id",
        "instrument",
        "timeframe",
        "created_at",
        "horizon_bars",
        "recommendation",
        "is_actionable",
        "signal",
        "probability",
        "risk",
        "provenance",
        "model",
        "evidence_count",
        "limitations",
    ):
        assert key in payload, f"missing contract key: {key}"


@pytest.mark.asyncio
async def test_record_id_is_deterministic_for_the_same_report():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    # Rebuilding the record from the same report is a pure function: same id,
    # same dict. This is what makes a re-recorded prediction dedupe.
    first = PredictionRecord.from_report(report)
    second = PredictionRecord.from_report(report)

    assert first.id == second.id
    assert first.to_dict() == second.to_dict()


@pytest.mark.asyncio
async def test_record_preserves_mock_no_trade_verbatim():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    record = PredictionRecord.from_report(report)

    # A synthetic-data call is preserved as exactly what it was: NO_TRADE, not
    # actionable, on MOCK data -- never silently upgraded to a confident signal.
    assert record.recommendation == "no_trade"
    assert record.is_actionable is False
    assert record.is_mock is True
    assert record.source_tier == "mock"


@pytest.mark.asyncio
async def test_record_never_fabricates_probability_on_mock():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    record = PredictionRecord.from_report(report)

    # No calibrated probability survives the mock reliability gate, so the record
    # states its absence rather than inventing a number (mirrors the report).
    assert record.probability_reliable is False
    assert record.probability_up is None
    assert record.probability_down is None
    assert record.to_dict()["probability"] is None


@pytest.mark.asyncio
async def test_record_surfaces_report_limitations():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    record = PredictionRecord.from_report(report)

    # The MOCK limitation must reach the audit record, not just the live report.
    assert any("MOCK" in lim for lim in record.limitations)


@pytest.mark.asyncio
async def test_record_round_trips_through_dict():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    record = PredictionRecord.from_report(report)
    rebuilt = PredictionRecord.from_dict(record.to_dict())

    # A durable store serialises with to_dict and reconstructs with from_dict;
    # the round-trip must be lossless.
    assert rebuilt == record
