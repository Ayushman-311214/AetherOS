"""
The ``analyze`` CLI command: the deterministic trading pipeline surfaced to a
human without the LLM.

These are integration tests. They wire the real trading services into the DI
container and drive the command through the same ToolCommandService -> tool ->
OrchestrationService path the CLI uses at runtime, then assert on the rendered
text. They pin the spec's honesty contract at the terminal boundary (CLAUDE.md
sections 11, 27, 28, 61): a MOCK-data run must render NO_TRADE, must not be
actionable, must not print a fabricated probability, must surface its MOCK
limitation, and must carry the "estimates, not guarantees" reminder.
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
from aetheros.tools.executor import ToolExecutor
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.anomaly_service import AnomalyService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.ceo_service import TradingCEOService
from aetheros.trading.services.ceo_agent_service import CEOAgentService
from aetheros.trading.services.calendar_service import EventCalendarService
from aetheros.trading.services.historical_analogue_service import (
    HistoricalAnalogueService,
)
from aetheros.trading.services.macro_service import MacroContextService
from aetheros.trading.services.multi_timeframe_service import MultiTimeframeService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.divergence_service import DivergenceService
from aetheros.trading.services.explanation_service import ExplanationService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.news_service import NewsSentimentService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.portfolio_service import PortfolioRiskService
from aetheros.trading.services.probability_service import ProbabilityService
from aetheros.trading.services.regime_service import RegimeService
from aetheros.trading.services.relative_strength_service import (
    RelativeStrengthService,
)
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.scan_service import WatchlistScanService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
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
    relative_strength = RelativeStrengthService(settings)
    anomaly = AnomalyService(settings)
    historical = HistoricalAnalogueService(settings)
    regime = RegimeService(settings)
    macro = MacroContextService(regime, settings)
    scan = WatchlistScanService(analysis, settings)
    multi_timeframe = MultiTimeframeService(settings)
    divergence = DivergenceService(settings)
    breakout = BreakoutService(settings)
    portfolio = PortfolioRiskService(settings)
    explanation = ExplanationService(settings)
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
        relative_strength=relative_strength,
        anomaly=anomaly,
        historical_analogue=historical,
        macro=macro,
        multi_timeframe=multi_timeframe,
        divergence=divergence,
        breakout=breakout,
    )
    ceo = TradingCEOService(orchestrator, settings, llm=None)
    ceo_agent = CEOAgentService(ToolExecutor(tool_registry), settings, llm=None)
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
        RelativeStrengthService: relative_strength,
        AnomalyService: anomaly,
        HistoricalAnalogueService: historical,
        RegimeService: regime,
        MacroContextService: macro,
        WatchlistScanService: scan,
        MultiTimeframeService: multi_timeframe,
        DivergenceService: divergence,
        BreakoutService: breakout,
        PortfolioRiskService: portfolio,
        ExplanationService: explanation,
        TradingCEOService: ceo,
        CEOAgentService: ceo_agent,
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
async def test_analyze_renders_no_trade_on_mock(commands):
    output = await commands._analyze(["AAPL", "1d"])

    # The full pipeline must degrade honestly on synthetic data.
    assert "RECOMMENDATION   : NO_TRADE" in output
    assert "Actionable       : NO" in output


@pytest.mark.asyncio
async def test_analyze_never_fabricates_probability(commands):
    output = await commands._analyze(["AAPL"])

    # No calibrated probability survives the mock reliability gate, so the
    # section states its absence rather than inventing a number.
    assert "Probability" in output
    assert "Not available" in output
    assert "P(UP)" not in output


@pytest.mark.asyncio
async def test_analyze_surfaces_mock_limitation(commands):
    output = await commands._analyze(["AAPL"])

    assert "Limitations" in output
    assert "MOCK" in output


@pytest.mark.asyncio
async def test_analyze_carries_uncertainty_reminder(commands):
    output = await commands._analyze(["AAPL"])

    # The mandatory reminder that a probability is an estimate, not a guarantee.
    assert "not guarantees" in output


@pytest.mark.asyncio
async def test_analyze_renders_critic_verdict_and_checks(commands):
    output = await commands._analyze(["AAPL"])

    assert "Critic" in output
    assert "Verdict" in output
    # The section-27 shape is present, not just a bare signal.
    assert "Key levels" in output
    assert "Risk / reward" in output


@pytest.mark.asyncio
async def test_analyze_flags_advisory_layers_as_unreliable(commands):
    output = await commands._analyze(["AAPL"])

    # Advisory layers are surfaced but honestly labelled NOT reliable on mocks.
    assert "News/sentiment" in output
    assert "Event calendar" in output
    assert "Fundamentals" in output
    assert "NOT reliable" in output


@pytest.mark.asyncio
async def test_analyze_surfaces_the_newer_advisory_layers(commands):
    output = await commands._analyze(["AAPL"])

    # The relative-strength, anomaly and historical-analogue reads now reach the
    # report and must be surfaced to the human -- each labelled NOT reliable on a
    # MOCK run rather than silently dropped.
    assert "Relative strength" in output
    assert "Anomaly" in output
    assert "Historical" in output
    assert "Macro context" in output
    assert "Multi-timeframe" in output
    assert "Divergence" in output
    assert "Breakout" in output


@pytest.mark.asyncio
async def test_scan_ranks_a_watchlist(commands):
    output = await commands._scan_command(["AAPL", "MSFT", "NVDA", "1d"])

    # The ranked table renders each requested symbol and the honesty reminder;
    # on MOCK data nothing is actionable but every row is still shown.
    assert "Watchlist Scan" in output
    assert "AAPL" in output and "MSFT" in output and "NVDA" in output
    assert "Requested   : 3" in output
    assert "not advice" in output


@pytest.mark.asyncio
async def test_scan_without_symbols_shows_usage(commands):
    output = await commands._scan_command([])
    assert "Usage: scan" in output


@pytest.mark.asyncio
async def test_scan_not_connected_without_service():
    from aetheros.cli.commands import CommandRegistry

    commands = CommandRegistry(tool_service=None)
    output = await commands._scan_command(["AAPL"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_explain_renders_why_on_mock(commands):
    output = await commands._explain_command(["AAPL", "1d"])

    # The explanation surfaces the recommendation and the honest reminder; on
    # MOCK data it is NO_TRADE.
    assert "Why: AAPL" in output
    assert "NO_TRADE" in output
    assert "Reliable evidence" in output
    assert "not advice" in output


@pytest.mark.asyncio
async def test_explain_without_symbol_shows_usage(commands):
    output = await commands._explain_command([])
    assert "Usage: explain" in output


@pytest.mark.asyncio
async def test_brief_narrates_a_free_text_request(commands):
    output = await commands._brief_command(["analyze", "AAPL", "1d"])

    # No LLM wired -> deterministic narration; the recommendation is the report's.
    assert "CEO Brief: " in output
    assert "AAPL" in output
    assert "NO_TRADE" in output
    assert "not advice" in output


@pytest.mark.asyncio
async def test_brief_without_an_instrument_is_honest(commands):
    output = await commands._brief_command(["should", "i", "buy", "the", "stock"])
    # No instrument identified -> an honest message, not a fabricated brief.
    assert "Could not identify an instrument" in output


@pytest.mark.asyncio
async def test_brief_without_args_shows_usage(commands):
    output = await commands._brief_command([])
    assert "Usage: brief" in output


@pytest.mark.asyncio
async def test_investigate_without_llm_is_honest(commands):
    # No LLM wired -> the agentic investigation says it needs one rather than
    # fabricating a tool sequence.
    output = await commands._investigate_command(["is", "AAPL", "a", "buy"])
    assert "needs an LLM" in output


@pytest.mark.asyncio
async def test_investigate_without_args_shows_usage(commands):
    output = await commands._investigate_command([])
    assert "Usage: investigate" in output


@pytest.mark.asyncio
async def test_investigate_not_connected_without_service():
    from aetheros.cli.commands import CommandRegistry

    commands = CommandRegistry(tool_service=None)
    output = await commands._investigate_command(["AAPL"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_brief_not_connected_without_service():
    from aetheros.cli.commands import CommandRegistry

    commands = CommandRegistry(tool_service=None)
    output = await commands._brief_command(["AAPL"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_explain_not_connected_without_service():
    from aetheros.cli.commands import CommandRegistry

    commands = CommandRegistry(tool_service=None)
    output = await commands._explain_command(["AAPL"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_portfolio_renders_plan_on_mock(commands):
    output = await commands._portfolio_command(["AAPL", "MSFT", "100000"])

    # On MOCK data nothing is actionable, so the plan is an honest empty
    # allocation with the equity/budget shown and the advisory reminder.
    assert "Portfolio Risk" in output
    assert "Account equity" in output
    assert "no actionable candidates" in output
    assert "not a recommendation" in output


@pytest.mark.asyncio
async def test_portfolio_without_equity_shows_usage(commands):
    output = await commands._portfolio_command(["AAPL", "MSFT"])
    assert "Usage: portfolio" in output


@pytest.mark.asyncio
async def test_portfolio_not_connected_without_service():
    from aetheros.cli.commands import CommandRegistry

    commands = CommandRegistry(tool_service=None)
    output = await commands._portfolio_command(["AAPL", "100000"])
    assert "NOT CONNECTED" in output


@pytest.mark.asyncio
async def test_analyze_backtest_flag_includes_backtest(commands):
    output = await commands._analyze(["AAPL", "1d", "backtest"])

    assert "Backtest" in output


@pytest.mark.asyncio
async def test_analyze_without_symbol_shows_usage(commands):
    output = await commands._analyze([])

    assert "Usage: analyze" in output


@pytest.mark.asyncio
async def test_analyze_not_connected_without_service():
    commands = CommandRegistry(tool_service=None)

    output = await commands._analyze(["AAPL"])

    assert "NOT CONNECTED" in output
