"""
The ``track-record`` CLI command: the recorded prediction-audit trail and its
evaluated track record, surfaced to a human without the LLM.

These are integration tests. They wire the real trading services -- including the
live ``PredictionStore`` the orchestrator records into and the
``PredictionTrackRecordService`` that scores it -- into the DI container, and
drive the command through the same ToolCommandService -> tool path the CLI uses
at runtime, then assert on the rendered text. They pin the spec's honesty
contract at the terminal boundary (CLAUDE.md sections 8, 27, 28, 29): an empty
history reads as "nothing to measure yet", a thin/MOCK-resolved sample renders
NOT reliable, and the aggregate always carries the "not a guarantee" reminder.
"""

from __future__ import annotations

import pytest

# Importing the module registers the @tool functions into the global registry.
import aetheros.trading.tools  # noqa: F401
from aetheros.cli.commands import CommandRegistry
from aetheros.cli.tool_commands import ToolCommandService
from aetheros.config.config_loader import get_settings
from aetheros.core.container import container
from aetheros.tools import tool_registry
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.calendar_service import EventCalendarService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.monitoring_service import MonitoringService
from aetheros.trading.services.monitoring_scheduler import MonitoringScheduler
from aetheros.trading.services.news_service import NewsSentimentService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.outcome_store import (
    InMemoryOutcomeStore,
    OutcomeStore,
)
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)
from aetheros.trading.services.prediction_evaluator import PredictionEvaluator
from aetheros.trading.services.prediction_store import (
    InMemoryPredictionStore,
    PredictionStore,
)
from aetheros.trading.services.probability_service import ProbabilityService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.services.track_record_service import (
    PredictionTrackRecordService,
)


@pytest.fixture(autouse=True)
def _wire_container():
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
    probability = ProbabilityService(settings)
    news = NewsSentimentService(MockNewsProvider(), settings)
    events = EventCalendarService(MockCalendarProvider(), settings)
    fundamentals = FundamentalAnalysisService(MockFundamentalsProvider(), settings)
    store = InMemoryPredictionStore()
    orchestrator = OrchestrationService(
        market_data,
        analysis,
        risk,
        backtest,
        critic,
        settings,
        probability=probability,
        news=news,
        calendar=events,
        fundamentals=fundamentals,
        prediction_store=store,
    )
    evaluator = PredictionEvaluator(settings, market_data=market_data)
    performance = PredictionPerformanceService(settings)
    track_record = PredictionTrackRecordService(store, evaluator, performance)
    outcome_store = InMemoryOutcomeStore()
    monitoring = MonitoringService(track_record, performance, outcome_store=outcome_store)
    scheduler = MonitoringScheduler(monitoring, settings)
    registrations = {
        MarketDataService: market_data,
        MarketStructureService: structure,
        EvidenceService: evidence,
        AnalysisService: analysis,
        RiskService: risk,
        BacktestService: backtest,
        CriticService: critic,
        ProbabilityService: probability,
        OrchestrationService: orchestrator,
        NewsSentimentService: news,
        EventCalendarService: events,
        FundamentalAnalysisService: fundamentals,
        PredictionStore: store,
        PredictionEvaluator: evaluator,
        PredictionPerformanceService: performance,
        PredictionTrackRecordService: track_record,
        MonitoringService: monitoring,
        MonitoringScheduler: scheduler,
        OutcomeStore: outcome_store,
    }
    for key, instance in registrations.items():
        container.register_singleton(key, (lambda i=instance: i))
    yield
    for key in registrations:
        container.remove(key)


@pytest.fixture
def commands() -> CommandRegistry:
    return CommandRegistry(ToolCommandService(tool_registry))


@pytest.mark.asyncio
async def test_track_record_empty_history_is_honest_not_an_error(commands):

    output = await commands._track_record_command([])

    # An empty audit trail is a valid "nothing to measure yet", never an error.
    assert "Prediction Track Record" in output
    assert "Sample size      : 0" in output
    assert "Reliable         : NO" in output
    assert "(none recorded this session)" in output


@pytest.mark.asyncio
async def test_monitor_empty_history_is_honest_not_an_error(commands):
    output = await commands._monitor_command([])

    # A sweep over an empty history is a valid quiet pass, never an error.
    assert "Monitoring Sweep" in output
    assert "Swept            : 0" in output
    assert "Reliable         : NO" in output
    assert "not a guarantee" in output


@pytest.mark.asyncio
async def test_monitor_sweeps_after_a_recorded_prediction(commands):
    # Record a prediction via analyze, then sweep: it is swept (resolved/pending/
    # unresolvable) but on MOCK data never a reliable track record.
    await commands._analyze(["AAPL", "1d"])
    output = await commands._monitor_command([])

    assert "Monitoring Sweep" in output
    assert "Swept            : 1" in output
    assert "Reliable         : NO" in output


@pytest.mark.asyncio
async def test_monitor_not_connected_without_service():
    commands = CommandRegistry(tool_service=None)
    output = await commands._monitor_command(["AAPL"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_monitor_loop_status_reports_disabled(commands):
    output = await commands._monitor_loop_command(["status"])
    assert "Monitoring Loop" in output
    assert "stopped" in output
    assert "disabled" in output


@pytest.mark.asyncio
async def test_monitor_loop_start_stays_off_when_disabled(commands):
    output = await commands._monitor_loop_command(["start"])
    # Disabled in config -> it reports it did not start.
    assert "did not start" in output


@pytest.mark.asyncio
async def test_monitor_loop_stop_is_safe_when_not_running(commands):
    output = await commands._monitor_loop_command(["stop"])
    assert "Monitoring Loop" in output
    assert "stopped" in output


@pytest.mark.asyncio
async def test_monitor_loop_unknown_action_shows_usage(commands):
    output = await commands._monitor_loop_command(["frobnicate"])
    assert "Usage: monitor-loop" in output


@pytest.mark.asyncio
async def test_monitor_loop_not_connected_without_service():
    commands = CommandRegistry(tool_service=None)
    output = await commands._monitor_loop_command(["status"])
    assert "NOT CONNECTED" in output
@pytest.mark.asyncio
async def test_track_record_lists_a_recorded_prediction(commands):
    # Producing a report records its section-8 prediction into the live store.
    await commands._analyze(["AAPL", "1d"])

    output = await commands._track_record_command([])

    # The recorded call now appears in the trail and in the aggregate sample.
    assert "Recorded (listed): 1" in output
    assert "Sample size      : 1" in output
    assert "AAPL" in output


@pytest.mark.asyncio
async def test_track_record_thin_mock_sample_is_not_reliable(commands):
    await commands._analyze(["AAPL", "1d"])

    output = await commands._track_record_command([])

    # One MOCK-resolved prediction is far below any reliable sample.
    assert "Reliable         : NO" in output
    assert "Limitations" in output


@pytest.mark.asyncio
async def test_track_record_carries_uncertainty_reminder(commands):
    output = await commands._track_record_command([])

    # The mandatory reminder that a track record is not a future guarantee.
    assert "not a guarantee" in output


@pytest.mark.asyncio
async def test_track_record_scopes_to_the_given_instrument_key(commands):
    output = await commands._track_record_command(["AAPL:NASDAQ"])

    # The scope label reflects the verbatim instrument key, never a guessed one.
    assert "Scope            : AAPL:NASDAQ" in output


@pytest.mark.asyncio
async def test_track_record_not_connected_without_service():
    commands = CommandRegistry(tool_service=None)

    output = await commands._track_record_command([])

    assert "NOT CONNECTED" in output
