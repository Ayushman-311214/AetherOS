"""
Trading tools exercised through the real ToolRegistry + ToolExecutor.

These are integration tests: they go through the same path an agent would --
resolve the service from the DI container, validate arguments, invoke the tool
-- rather than calling the service directly. They also pin the spec's honesty
rule at the tool boundary: a MOCK result is labelled MOCK and never actionable
(CLAUDE.md sections 11, 61).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

# Importing the module registers the @tool functions into the global registry.
import aetheros.trading.tools  # noqa: F401
from aetheros.config.config_loader import get_settings
from aetheros.core.container import container
from aetheros.tools import ToolExecutor, tool_registry
from aetheros.trading.alerts import (
    AlertRouter,
    AlertService,
    CollectingDeliveryProvider,
)
from aetheros.trading.analytics import JournalAnalyticsService
from aetheros.trading.brokers import PaperTradingProvider
from aetheros.trading.domain.enums import SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Quote
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.risk.limits_service import RiskLimitsService
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.anomaly_service import AnomalyService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.calendar_service import EventCalendarService
from aetheros.trading.services.calibration_history_service import (
    CalibrationHistoryService,
)
from aetheros.trading.services.ceo_agent_service import CEOAgentService
from aetheros.trading.services.ceo_service import TradingCEOService
from aetheros.trading.services.chart_service import ChartService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.decision_service import DecisionService
from aetheros.trading.services.divergence_service import DivergenceService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.explanation_service import ExplanationService
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService
from aetheros.trading.services.historical_analogue_service import (
    HistoricalAnalogueService,
)
from aetheros.trading.services.hybrid_service import HybridContextService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.journal_service import JournalService
from aetheros.trading.services.journal_store import (
    InMemoryJournalStore,
    JournalStore,
)
from aetheros.trading.services.liquidity_service import LiquidityService
from aetheros.trading.services.macro_service import MacroContextService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)
from aetheros.trading.services.monitoring_scheduler import MonitoringScheduler
from aetheros.trading.services.monitoring_service import MonitoringService
from aetheros.trading.services.multi_timeframe_service import MultiTimeframeService
from aetheros.trading.services.news_service import NewsSentimentService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.outcome_store import (
    InMemoryOutcomeStore,
    OutcomeStore,
)
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)
from aetheros.trading.services.portfolio_service import PortfolioRiskService
from aetheros.trading.services.prediction_evaluator import PredictionEvaluator
from aetheros.trading.services.prediction_store import (
    InMemoryPredictionStore,
    PredictionStore,
)
from aetheros.trading.services.probability_service import ProbabilityService
from aetheros.trading.services.regime_service import RegimeService
from aetheros.trading.services.relative_strength_service import (
    RelativeStrengthService,
)
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.scan_service import WatchlistScanService
from aetheros.trading.services.signal_service import SignalService
from aetheros.trading.services.simulation_service import SimulationService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.services.track_record_service import (
    PredictionTrackRecordService,
)
from aetheros.trading.services.visual_service import VisualObservationService
from aetheros.trading.services.walk_forward_service import WalkForwardService


@pytest.fixture(autouse=True)
def _wire_container():
    settings = get_settings()
    provider = MockMarketDataProvider()
    market_data = MarketDataService(provider, settings)
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
    regime = RegimeService(settings)
    relative_strength = RelativeStrengthService(settings)
    anomaly = AnomalyService(settings)
    historical = HistoricalAnalogueService(settings)
    macro = MacroContextService(regime, settings)
    liquidity = LiquidityService()
    smc = SMCService(structure)
    ict = ICTService(structure, smc)
    scan = WatchlistScanService(analysis, settings)
    multi_timeframe = MultiTimeframeService(settings)
    divergence = DivergenceService(settings)
    breakout = BreakoutService(settings)
    strategy = StrategyService(
        analysis,
        structure,
        smc=smc,
        ict=ict,
        breakout=breakout,
        backtest=backtest,
    )
    signals = SignalService(
        strategy,
        risk,
        critic,
        market_data,
        settings,
    )
    walk_forward = WalkForwardService(backtest, strategy, settings)
    portfolio = PortfolioRiskService(settings)
    # The paper-trading block, wired as the bootstrapper wires it. The venue is
    # registered even though simulate_strategy does not resolve it -- the
    # simulation builds its own venue per order over the replay cursor -- so
    # that this container matches the real one for anything that does.
    risk_limits = RiskLimitsService(settings)
    paper_venue = PaperTradingProvider(market_data)
    simulation = SimulationService(signals, portfolio, risk_limits, settings)
    journal = JournalService()
    journal_store = InMemoryJournalStore()
    journal_analytics = JournalAnalyticsService(settings)
    # Alerts, wired as the bootstrapper wires them but with a collecting
    # provider so a raised alert can be asserted without touching a log or OS
    # toast. event_bus=None keeps it a pure direct-raise surface for the tools.
    alert_router = AlertRouter()
    alert_collector = CollectingDeliveryProvider()
    alert_router.register(alert_collector)
    alerts = AlertService(alert_router, settings, event_bus=None)
    visual = VisualObservationService()
    explanation = ExplanationService(settings)
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
    calibration_history = CalibrationHistoryService(settings, outcome_store=outcome_store)
    ceo = TradingCEOService(orchestrator, settings, llm=None)
    ceo_agent = CEOAgentService(ToolExecutor(tool_registry), settings, llm=None)
    chart = ChartService()
    decision = DecisionService(orchestrator, market_data, strategy, explanation)
    hybrid = HybridContextService(
        orchestrator, market_data, chart, visual, vision_factory=lambda: None
    )
    registrations = {
        MarketDataService: market_data,
        MarketStructureService: structure,
        EvidenceService: evidence,
        AnalysisService: analysis,
        RiskService: risk,
        BacktestService: backtest,
        CriticService: critic,
        ProbabilityService: probability,
        RegimeService: regime,
        RelativeStrengthService: relative_strength,
        AnomalyService: anomaly,
        HistoricalAnalogueService: historical,
        MacroContextService: macro,
        LiquidityService: liquidity,
        SMCService: smc,
        ICTService: ict,
        StrategyService: strategy,
        SignalService: signals,
        WalkForwardService: walk_forward,
        WatchlistScanService: scan,
        MultiTimeframeService: multi_timeframe,
        DivergenceService: divergence,
        BreakoutService: breakout,
        PortfolioRiskService: portfolio,
        RiskLimitsService: risk_limits,
        PaperTradingProvider: paper_venue,
        SimulationService: simulation,
        JournalService: journal,
        JournalStore: journal_store,
        JournalAnalyticsService: journal_analytics,
        AlertService: alerts,
        VisualObservationService: visual,
        ExplanationService: explanation,
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
        CalibrationHistoryService: calibration_history,
        TradingCEOService: ceo,
        CEOAgentService: ceo_agent,
        ChartService: chart,
        HybridContextService: hybrid,
        DecisionService: decision,
    }
    for key, instance in registrations.items():
        container.register_singleton(key, (lambda i=instance: i))
    yield
    for key in registrations:
        container.remove(key)


@pytest.fixture
def executor():
    # timeout_seconds=None: deterministic tests must not race a wall-clock budget.
    return ToolExecutor(tool_registry, timeout_seconds=None)


def test_trading_tools_are_registered():
    for name in (
        "get_market_quote",
        "get_market_candles",
        "calculate_indicator",
        "analyze_market_structure",
        "get_support_resistance",
        "get_volume_analysis",
        "analyze_liquidity",
        "analyze_smc",
        "analyze_ict",
        "list_strategies",
        "evaluate_strategies",
        "optimize_strategy",
        "generate_signals",
        "detect_market_regime",
        "analyze_relative_strength",
        "detect_anomalies",
        "find_historical_analogues",
        "analyze_macro_context",
        "scan_watchlist",
        "size_portfolio",
        "analyze_multi_timeframe",
        "detect_divergence",
        "detect_breakout",
        "analyze_instrument",
        "assess_risk",
        "backtest_signal",
        "walk_forward_backtest",
        "compare_strategy_backtests",
        "critique_signal",
        "estimate_probability",
        "generate_trading_report",
        "explain_signal",
        "brief_instrument",
        "ask_ceo",
        "investigate_ceo",
        "analyze_news_sentiment",
        "get_market_events",
        "analyze_fundamentals",
        "list_predictions",
        "evaluate_track_record",
        "run_monitoring_pass",
        "list_outcomes",
        "evaluate_outcome_history",
        "audit_calibration",
        "recalibrate_probability",
        "start_monitoring_loop",
        "stop_monitoring_loop",
        "monitoring_loop_status",
        "build_chart_data",
        "synchronize_charts",
        "capture_chart_screenshot",
        "observe_chart",
        "build_hybrid_context",
        "decide",
        "simulate_strategy",
        "journal_performance",
        "list_alerts",
        "watch_price",
    ):
        assert tool_registry.exists(name)
    assert "trading.data" in tool_registry.categories()
    assert "trading.analysis" in tool_registry.categories()
    assert "trading.audit" in tool_registry.categories()
    assert "trading.simulation" in tool_registry.categories()
    assert "trading.analytics" in tool_registry.categories()


@pytest.mark.asyncio
async def test_get_market_quote_tool(executor):
    result = await executor.execute_safe("get_market_quote", {"symbol": "AAPL"})
    assert result.ok, result.error
    assert result.value["price"] > 0
    assert result.value["provenance"]["tier"] == "mock"


@pytest.mark.asyncio
async def test_get_market_candles_tool(executor):
    result = await executor.execute_safe(
        "get_market_candles", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    assert result.ok, result.error
    assert result.value["count"] == 120
    assert "quality" in result.value


@pytest.mark.asyncio
async def test_calculate_indicator_rsi(executor):
    result = await executor.execute_safe(
        "calculate_indicator",
        {"symbol": "AAPL", "indicator": "rsi", "limit": 120},
    )
    assert result.ok, result.error
    value = result.value["value"]
    assert value is None or 0.0 <= value <= 100.0


@pytest.mark.asyncio
async def test_calculate_indicator_supertrend(executor):
    result = await executor.execute_safe(
        "calculate_indicator",
        {"symbol": "AAPL", "indicator": "supertrend", "period": 10, "limit": 200},
    )
    assert result.ok, result.error
    assert result.value["period"] == 10
    value = result.value["value"]
    assert set(value) == {"direction", "line", "stop"}
    # Direction is either a flipped side or an honest None on a thin series.
    assert value["direction"] in ("up", "down", None)


@pytest.mark.asyncio
async def test_calculate_indicator_volume_profile(executor):
    result = await executor.execute_safe(
        "calculate_indicator",
        {"symbol": "AAPL", "indicator": "volume_profile", "period": 12, "limit": 200},
    )
    assert result.ok, result.error
    assert result.value["bins"] == 12
    value = result.value["value"]
    assert value is not None
    assert len(value["bin_edges"]) == 13  # bins + 1 edges
    assert len(value["bin_volumes"]) == 12
    assert value["value_area_low"] <= value["poc"] <= value["value_area_high"]


@pytest.mark.asyncio
async def test_calculate_indicator_unknown_is_honest(executor):
    result = await executor.execute_safe(
        "calculate_indicator", {"symbol": "AAPL", "indicator": "nonsense"}
    )
    assert result.ok  # a bad indicator name is data, not a crash
    assert "error" in result.value
    assert "supported" in result.value
    # The runtime-registered extension point is advertised alongside the built-ins.
    assert "supertrend" in result.value["supported"]
    assert "volume_profile" in result.value["supported"]


@pytest.mark.asyncio
async def test_analyze_instrument_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_instrument", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["is_actionable"] is False  # mock data is never actionable
    assert any("MOCK" in lim for lim in payload["limitations"])
    assert payload["provenance"]["tier"] == "mock"


@pytest.mark.asyncio
async def test_analyze_market_structure_tool(executor):
    result = await executor.execute_safe(
        "analyze_market_structure", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    assert "trend" in result.value["structure"]


@pytest.mark.asyncio
async def test_support_resistance_tool(executor):
    result = await executor.execute_safe(
        "get_support_resistance", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    assert "supports" in result.value
    assert "resistances" in result.value


@pytest.mark.asyncio
async def test_volume_analysis_tool(executor):
    result = await executor.execute_safe(
        "get_volume_analysis", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    assert result.value["volume"] is not None


@pytest.mark.asyncio
async def test_analyze_liquidity_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_liquidity", {"symbol": "AAPL", "limit": 200}
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["provenance"]["tier"] == "mock"
    liquidity = payload["liquidity"]
    # The structured read is present, with honest nulls where the mock
    # series cannot support a field -- never a fabricated number.
    assert liquidity["participation"] in ("high", "average", "low", "unknown")
    assert any("MOCK" in lim for lim in liquidity["limitations"])
    # A liquidity read is situational context; it carries no probability.
    assert "probability" not in liquidity


@pytest.mark.asyncio
async def test_analyze_smc_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_smc", {"symbol": "AAPL", "limit": 200}
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["provenance"]["tier"] == "mock"

    smc = payload["smc"]
    # The structured read is present and self-describing: detections are only
    # ever derived from the candles, so the shape is stable even when a
    # synthetic random walk yields few of them.
    assert set(smc) >= {
        "instrument_key",
        "timeframe",
        "last_price",
        "trend",
        "breaks",
        "zones",
        "liquidity",
        "dealing_range",
        "mitigation_blocks",
        "provenance",
        "limitations",
    }
    assert smc["provenance"]["tier"] == "mock"
    assert any("MOCK" in lim for lim in smc["limitations"])
    # SMC detects and describes; it never produces a trade decision or a
    # probability, and the derived views are consistent with the zones.
    assert "probability" not in smc
    assert len(smc["mitigation_blocks"]) <= len(smc["zones"])


@pytest.mark.asyncio
async def test_analyze_ict_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_ict", {"symbol": "AAPL", "limit": 200}
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["provenance"]["tier"] == "mock"
    assert "quality" in payload

    ict = payload["ict"]
    # The structured read is present and self-describing: every concept has a
    # slot, and absence is reported as an empty tuple rather than being omitted.
    assert set(ict) >= {
        "instrument_key",
        "timeframe",
        "last_price",
        "exchange_timezone",
        "sessions",
        "daily_bias",
        "market_structure_shifts",
        "kill_zones",
        "ote",
        "liquidity_pools",
        "judas_swings",
        "power_of_three",
        "session_models",
        "resting_pools",
        "taken_pools",
        "provenance",
        "limitations",
    }
    assert ict["provenance"]["tier"] == "mock"
    assert any("MOCK" in lim for lim in ict["limitations"])
    # ICT detects and describes a session-aware market structure; it carries no
    # probability and no trade decision, and its derived views stay consistent.
    assert "probability" not in ict
    assert len(ict["resting_pools"]) + len(ict["taken_pools"]) == len(
        ict["liquidity_pools"]
    )


@pytest.mark.asyncio
async def test_list_strategies_tool_names_the_built_in_panel(executor):
    result = await executor.execute_safe("list_strategies", {})
    assert result.ok, result.error
    strategies = result.value["strategies"]
    assert {s["strategy_id"] for s in strategies} == {
        "breakout",
        "ict",
        "mean_reversion",
        "smc",
        "trend_following",
    }
    for entry in strategies:
        # Each entry is self-describing: what it looks for and the tunable
        # thresholds it actually applies (never indicator periods).
        assert entry["name"].strip()
        assert entry["category"].strip()
        assert entry["description"].strip()
        assert isinstance(entry["parameters"], dict)
        assert not (
            {"sma_period", "ema_period", "rsi_period", "atr_period", "lookback"}
            & set(entry["parameters"])
        )


@pytest.mark.asyncio
async def test_evaluate_strategies_tool_compares_a_panel(executor):
    result = await executor.execute_safe(
        "evaluate_strategies",
        {"symbol": "AAPL", "limit": 200, "strategies": ["trend_following", "mean_reversion"]},
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["provenance"]["tier"] == "mock"

    comparison = payload["comparison"]
    # The panel verdict shape: every strategy evaluated, consensus reported
    # alongside disagreement rather than averaged away.
    assert {item["strategy_id"] for item in comparison["evaluations"]} == {
        "trend_following",
        "mean_reversion",
    }
    assert comparison["consensus"] in ("up", "down", "sideways", "unknown")
    assert comparison["setup_count"] == comparison["bullish"] + comparison["bearish"]
    assert isinstance(comparison["dissenting"], list)
    assert comparison["provenance"]["tier"] == "mock"
    for item in comparison["evaluations"]:
        assert isinstance(item["rules"], list)
        assert isinstance(item["limitations"], list)


@pytest.mark.asyncio
async def test_optimize_strategy_tool_crowns_no_winner_on_mock(executor):
    result = await executor.execute_safe(
        "optimize_strategy",
        {
            "symbol": "AAPL",
            "strategy": "trend_following",
            "parameters": {"min_adx": [10.0, 30.0]},
            "limit": 80,
        },
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["provenance"]["tier"] == "mock"

    search = payload["search"]
    # Synthetic data verifies the machinery, never a real edge: no reliable
    # winner is crowned, the configured baseline is still measured, and the
    # result says why instead of presenting an empty search as a verdict.
    assert search["best"] is None
    assert search["improved"] is False
    assert search["baseline"]["is_baseline"] is True
    # Neither grid point resolves to the configured min_adx=20, so the baseline
    # is measured separately alongside the two combinations.
    assert len(search["candidates"]) == 3
    assert any("reliable" in line for line in search["limitations"])


@pytest.mark.asyncio
async def test_generate_signals_tool_produces_nothing_on_mock(executor):
    result = await executor.execute_safe(
        "generate_signals",
        {"symbol": "AAPL", "limit": 120},
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["provenance"]["tier"] == "mock"

    signals = payload["signals"]
    # The §9/§28 honesty gate at the tool boundary: mock data verifies the
    # machinery and never proposes a trade, and every declined candidate
    # names the gate that stopped it.
    assert signals["signal_count"] == 0
    assert signals["signals"] == []
    for candidate in signals["candidates"]:
        assert candidate["fired"] is False
        assert candidate["rejections"]
    # Declined strategies are accounted for in limitations.
    assert signals["limitations"]


@pytest.mark.asyncio
async def test_detect_market_regime_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "detect_market_regime", {"symbol": "AAPL", "limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # A regime read on synthetic data can never be reliable, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    # The §5 shape is present: a classified regime, its implied direction and the
    # deterministic inputs it was derived from.
    assert payload["regime"] in (
        "trending_up",
        "trending_down",
        "ranging",
        "volatile",
        "unknown",
    )
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "adx" in payload
    assert "atr_pct" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_analyze_relative_strength_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_relative_strength", {"symbol": "AAPL", "limit": 200}
    )
    assert result.ok, result.error
    payload = result.value
    # A relative-strength read on synthetic data (both series MOCK) is never
    # reliable, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert payload["benchmark_provenance"]["tier"] == "mock"
    # The read carries its benchmark, a determinate lean vocabulary and the
    # excess-return inputs it was derived from.
    assert payload["benchmark"]  # defaulted from settings when none passed
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "relative_return" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_analyze_relative_strength_tool_accepts_explicit_benchmark(executor):
    result = await executor.execute_safe(
        "analyze_relative_strength",
        {"symbol": "AAPL", "benchmark": "QQQ", "limit": 200},
    )
    assert result.ok, result.error
    assert result.value["benchmark"] == "QQQ"


@pytest.mark.asyncio
async def test_detect_anomalies_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "detect_anomalies", {"symbol": "AAPL", "limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # An anomaly read on synthetic data can never be reliable, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    # The shape is present: a boolean flag, the z-scores it was derived from and a
    # determinate lean vocabulary.
    assert isinstance(payload["is_anomalous"], bool)
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "return_z" in payload
    assert "volume_z" in payload
    assert "gap_z" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_find_historical_analogues_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "find_historical_analogues", {"symbol": "AAPL", "limit": 400}
    )
    assert result.ok, result.error
    payload = result.value
    # An analogue read on synthetic data can never be reliable, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    # The shape is present: the analogue outcome stats and a determinate lean vocab.
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "up_rate" in payload
    assert "mean_forward_return" in payload
    assert "sample_size" in payload
    assert "horizon" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_analyze_macro_context_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_macro_context", {"limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # A macro read on synthetic benchmark data can never be reliable; tier honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    # The shape is present: a posture, the regime it derived from, a lean vocab.
    assert payload["posture"] in ("risk_on", "risk_off", "neutral", "unknown")
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert payload["benchmark"]  # defaulted from settings when none passed
    assert "regime" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_scan_watchlist_tool_ranks_a_mock_watchlist(executor):
    result = await executor.execute_safe(
        "scan_watchlist", {"symbols": "AAPL, MSFT, NVDA"}
    )
    assert result.ok, result.error
    payload = result.value
    # All three requested symbols are scanned; on MOCK data none is actionable.
    assert payload["requested"] == 3
    assert payload["errored"] == 0
    assert len(payload["entries"]) == 3
    for entry in payload["entries"]:
        assert entry["is_actionable"] is False
        assert entry["is_reliable"] is False
    assert payload["actionable"] == 0


@pytest.mark.asyncio
async def test_size_portfolio_tool_is_honest_on_mock(executor):
    result = await executor.execute_safe(
        "size_portfolio",
        {"symbols": "AAPL, MSFT", "account_equity": 100000.0},
    )
    assert result.ok, result.error
    payload = result.value
    # On MOCK data no symbol produces an actionable trade, so the basket is empty
    # but the plan is still a valid, honest zero-risk allocation (never fabricated).
    assert payload["requested"] == 0
    assert payload["included"] == 0
    assert payload["total_risk"] == 0.0
    assert payload["gross_exposure"] == 0.0
    assert payload["within_risk_budget"] is True
    assert payload["within_exposure_cap"] is True
    assert "account_equity" in payload
    assert "total_risk_budget" in payload


@pytest.mark.asyncio
async def test_analyze_multi_timeframe_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_multi_timeframe", {"symbol": "AAPL", "limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # A multi-timeframe read on synthetic data can never be reliable; tier honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    # The shape is present: both timeframes, both directions and an alignment vocab.
    assert payload["alignment"] in ("confirmed", "conflict", "neutral", "unknown")
    assert payload["base_direction"] in ("up", "down", "sideways", "unknown")
    assert payload["higher_direction"] in ("up", "down", "sideways", "unknown")
    assert payload["higher_timeframe"]
    assert "quality" in payload


@pytest.mark.asyncio
async def test_detect_divergence_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "detect_divergence", {"symbol": "AAPL", "limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # A divergence read on synthetic data can never be reliable; tier honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert isinstance(payload["has_divergence"], bool)
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "oscillator" in payload
    assert "pivot_count" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_detect_breakout_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "detect_breakout", {"symbol": "AAPL", "limit": 300}
    )
    assert result.ok, result.error
    payload = result.value
    # A breakout read on synthetic data can never be reliable; tier honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert isinstance(payload["has_breakout"], bool)
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert "channel_high" in payload
    assert "channel_low" in payload
    assert "volume_confirmed" in payload
    assert "quality" in payload


@pytest.mark.asyncio
async def test_assess_risk_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "assess_risk", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # Mock data is never actionable, and provenance stays honest.
    assert payload["is_actionable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert "invalidation" in payload
    assert "overall_risk" in payload


@pytest.mark.asyncio
async def test_assess_risk_tool_position_sizing(executor):
    result = await executor.execute_safe(
        "assess_risk",
        {"symbol": "AAPL", "limit": 120, "direction": "up", "account_equity": 10000},
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["direction"] == "up"
    # A defined side + equity should size a position (unless no stop was found).
    if payload["stop_loss"] is not None:
        assert payload["risk_amount"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_assess_risk_tool_rejects_bad_direction(executor):
    result = await executor.execute_safe(
        "assess_risk", {"symbol": "AAPL", "direction": "sideways-ish"}
    )
    assert result.ok  # a bad direction is data, not a crash
    assert "error" in result.value
    assert "supported" in result.value


@pytest.mark.asyncio
async def test_backtest_signal_tool_is_never_reliable_on_mock(executor):
    # A short warmup keeps the walk-forward run fast while still producing calls.
    result = await executor.execute_safe(
        "backtest_signal",
        {"symbol": "AAPL", "limit": 120, "horizon": 5, "warmup": 50},
    )
    assert result.ok, result.error
    payload = result.value
    # The engine still computes the scorecard, but synthetic data proves no edge.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert payload["total_bars"] == 120
    assert payload["evaluated"] >= 1
    assert any("MOCK" in lim for lim in payload["limitations"])


@pytest.mark.asyncio
async def test_walk_forward_backtest_tool_is_never_reliable_on_mock(executor):
    # Small, explicit windows keep the run fast and make the fold geometry exact.
    result = await executor.execute_safe(
        "walk_forward_backtest",
        {
            "symbol": "AAPL",
            "strategy": "trend_following",
            "parameters": {"min_adx": [10.0, 30.0]},
            "limit": 120,
            "horizon": 5,
            "warmup": 20,
            "train_bars": 40,
            "test_bars": 20,
        },
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["provenance"]["tier"] == "mock"
    assert "quality" in payload

    report = payload["walk_forward"]
    # Synthetic data proves no edge, however tidy the folds look.
    assert report["is_reliable"] is False
    assert any("MOCK" in lim for lim in report["limitations"])
    # The embargo is the horizon: a training bar's label reaches `horizon` bars
    # forward, so anything less would let it reach into the test window.
    assert report["embargo_bars"] == 5
    assert len(report["folds"]) == 2
    for fold in report["folds"]:
        window = fold["window"]
        assert window["test_start"] == window["train_end"] + 5
        # Each fold records what it selected alongside what it measured, so a
        # dropped fold and an unselected one are distinguishable.
        assert "selection" in fold
        assert "in_sample" in fold


@pytest.mark.asyncio
async def test_compare_strategy_backtests_tool_crowns_no_winner_on_mock(executor):
    result = await executor.execute_safe(
        "compare_strategy_backtests",
        {
            "symbol": "AAPL",
            "strategies": ["trend_following", "mean_reversion"],
            "limit": 120,
            "horizon": 5,
            "warmup": 50,
        },
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["symbol"] == "AAPL"
    assert payload["provenance"]["tier"] == "mock"

    comparison = payload["comparison"]
    # Synthetic data verifies the ranking machinery, never a real edge: an
    # unreliable leader is not crowned, and the reason is stated.
    assert comparison["best"] is None
    assert comparison["is_conclusive"] is False
    assert {entry["label"] for entry in comparison["entries"]} == {
        "trend_following",
        "mean_reversion",
    }
    assert any("MOCK" in lim for lim in comparison["limitations"])


@pytest.mark.asyncio
async def test_compare_strategy_backtests_tool_rejects_an_unknown_strategy(executor):
    result = await executor.execute_safe(
        "compare_strategy_backtests",
        {"symbol": "AAPL", "strategies": ["trend_following", "nonsense"]},
    )
    # A bad strategy name is data, not a crash -- and it is named, with the
    # registered panel offered as the way out.
    assert not result.ok
    assert "nonsense" in (result.error or "")


@pytest.mark.asyncio
async def test_critique_signal_tool_is_insufficient_on_mock(executor):
    result = await executor.execute_safe(
        "critique_signal", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # Synthetic data can never be APPROVEd: the honest verdict is insufficient.
    assert payload["verdict"] == "insufficient_evidence"
    assert payload["approved"] is False
    assert payload["provenance"]["tier"] in ("mock", "derived")
    # The data_source check must FAIL on MOCK rather than being skipped.
    checks = {c["name"]: c["status"] for c in payload["checks"]}
    assert checks["data_source"] == "fail"
    assert checks["probability_calibration"] == "skipped"
    assert checks["event_risk"] == "skipped"


@pytest.mark.asyncio
async def test_estimate_probability_tool_is_never_reliable_on_mock(executor):
    result = await executor.execute_safe(
        "estimate_probability",
        {"symbol": "AAPL", "limit": 400, "horizon": 5},
    )
    assert result.ok, result.error
    payload = result.value
    # A number may still be returned so its reason is visible, but synthetic
    # data can never yield a reliable, actionable probability.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] in ("mock", "derived")
    assert payload["horizon"] == 5
    # p_up/p_down are still well-formed probabilities in [0, 1].
    prob = payload["probability"]
    assert 0.0 <= prob["up"] <= 1.0
    assert 0.0 <= prob["down"] <= 1.0
    assert any("MOCK" in lim for lim in payload["limitations"])


@pytest.mark.asyncio
async def test_generate_trading_report_tool_is_no_trade_on_mock(executor):
    result = await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # The full pipeline must degrade honestly on synthetic data: no trade,
    # not actionable, and -- crucially -- no fabricated probability.
    assert payload["recommendation"] == "no_trade"
    assert payload["is_actionable"] is False
    assert payload["probability"] is None
    assert payload["model"]["pipeline"] == "deterministic-core/1.0"
    # Both honesty limitations must surface in the composed report.
    assert any("MOCK" in lim for lim in payload["limitations"])
    assert any("calibrated probability" in lim for lim in payload["limitations"])
    # The §27 report shape is present, not just a signal.
    assert "key_levels" in payload
    assert "critique" in payload
    assert payload["backtest"] is None  # run_backtest defaults to False
    # News/sentiment is now fused into the report as advisory context, labelled
    # MOCK and never reliable -- and the critic gains a news_sentiment check.
    assert payload["news"] is not None
    assert payload["news"]["is_reliable"] is False
    assert payload["news"]["provenance"]["tier"] == "mock"
    # The event/economic calendar is fused too, labelled MOCK and never reliable;
    # on a MOCK calendar the critic's event_risk check only WARNs (a synthetic
    # calendar must never veto), so the report still degrades to no_trade above.
    assert payload["calendar"] is not None
    assert payload["calendar"]["is_reliable"] is False
    assert payload["calendar"]["provenance"]["tier"] == "mock"
    # Fundamentals are fused too, labelled MOCK and never reliable; on a MOCK
    # read the critic's fundamentals check only WARNs (a synthetic fundamental
    # view must never veto a signal), so the report still degrades to no_trade.
    assert payload["fundamentals"] is not None
    assert payload["fundamentals"]["is_reliable"] is False
    assert payload["fundamentals"]["provenance"]["tier"] == "mock"
    critique_checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "news_sentiment" in critique_checks
    assert critique_checks["event_risk"] == "warn"
    assert "fundamentals" in critique_checks
    assert critique_checks["fundamentals"] != "fail"


@pytest.mark.asyncio
async def test_explain_signal_tool_explains_mock_as_no_trade(executor):
    result = await executor.execute_safe(
        "explain_signal", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # The explanation mirrors the report: a MOCK run is NO_TRADE, not actionable,
    # and no mock evidence is allowed to move the net weight.
    assert payload["recommendation"] == "no_trade"
    assert payload["is_actionable"] is False
    assert payload["reliable_evidence_count"] == 0
    assert payload["supporting"] == []
    assert payload["opposing"] == []
    assert payload["net_weight"] == 0.0
    assert "summary" in payload and payload["summary"]


@pytest.mark.asyncio
async def test_brief_instrument_tool_narrates_mock_as_no_trade(executor):
    result = await executor.execute_safe(
        "brief_instrument", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # No LLM is wired in the test container, so the brief uses the deterministic
    # fallback -- and the recommendation comes from the report, not the prose.
    assert payload["recommendation"] == "no_trade"
    assert payload["is_actionable"] is False
    assert payload["narrated_by"] == "deterministic-fallback"
    assert "report" in payload and payload["report"]["recommendation"] == "no_trade"


@pytest.mark.asyncio
async def test_ask_ceo_tool_interprets_free_text(executor):
    ok = await executor.execute_safe("ask_ceo", {"request": "analyze AAPL 1d"})
    assert ok.ok, ok.error
    assert ok.value["instrument_key"].endswith("AAPL")
    assert ok.value["recommendation"] == "no_trade"

    # A request naming no instrument is an honest error, not a fabricated brief.
    none = await executor.execute_safe(
        "ask_ceo", {"request": "should i buy the stock today"}
    )
    assert none.ok, none.error
    assert "error" in none.value


@pytest.mark.asyncio
async def test_investigate_ceo_tool_is_honest_without_an_llm(executor):
    # No LLM is wired in the test container, so an agentic investigation returns
    # an honest "needs an LLM" result rather than fabricating a tool sequence.
    result = await executor.execute_safe("investigate_ceo", {"request": "look at AAPL"})
    assert result.ok, result.error
    payload = result.value
    assert payload["stopped_reason"] == "no_llm"
    assert payload["grounded"] is False
    assert "needs an LLM" in payload["answer"]


@pytest.mark.asyncio
async def test_generate_trading_report_tool_rejects_bad_direction(executor):
    result = await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "direction": "moon"}
    )
    assert result.ok  # a bad direction is data, not a crash
    assert "error" in result.value
    assert "supported" in result.value


@pytest.mark.asyncio
async def test_analyze_news_sentiment_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "analyze_news_sentiment", {"symbol": "AAPL", "limit": 12}
    )
    assert result.ok, result.error
    payload = result.value
    # Synthetic headlines can never yield a reliable read, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert any("MOCK" in lim for lim in payload["limitations"])
    # The §9 shape is present: a directional read, counts, items and evidence.
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert payload["counts"]["total"] == len(payload["items"])
    assert "evidence" in payload


@pytest.mark.asyncio
async def test_get_market_events_tool_is_labelled_mock(executor):
    result = await executor.execute_safe(
        "get_market_events", {"symbol": "AAPL", "horizon_days": 7}
    )
    assert result.ok, result.error
    payload = result.value
    # Synthetic events can never present a reliable calendar, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert any("MOCK" in lim for lim in payload["limitations"])
    # The §5 shape is present: horizon, high-impact flag, next event, event list.
    assert payload["horizon_days"] == 7
    assert "has_high_impact" in payload
    assert isinstance(payload["events"], list)
    assert payload["event_count"] == len(payload["events"])


@pytest.mark.asyncio
async def test_analyze_fundamentals_tool_is_labelled_mock(executor):
    result = await executor.execute_safe("analyze_fundamentals", {"symbol": "AAPL"})
    assert result.ok, result.error
    payload = result.value
    # Synthetic financials can never yield a reliable read, and the tier is honest.
    assert payload["is_reliable"] is False
    assert payload["provenance"]["tier"] == "mock"
    assert any("MOCK" in lim for lim in payload["limitations"])
    # The §9 shape is present: a directional health lean, factors, snapshot,
    # evidence and a scored/reported metric count.
    assert payload["direction"] in ("up", "down", "sideways", "unknown")
    assert isinstance(payload["factors"], list)
    assert "snapshot" in payload
    assert "evidence" in payload
    assert payload["scored_metric_count"] == len(payload["factors"])


# --------------------------------------------------------------------------- #
# Audit surface: recorded predictions and their track record                   #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_predictions_surfaces_the_recorded_audit_trail(executor):
    # An empty audit trail is an honest empty list, never an error.
    empty = await executor.execute_safe("list_predictions", {})
    assert empty.ok, empty.error
    assert empty.value["count"] == 0
    assert empty.value["predictions"] == []

    # Producing a report records its section-8 prediction into the live store.
    report = await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    assert report.ok, report.error

    listed = await executor.execute_safe("list_predictions", {})
    assert listed.ok, listed.error
    assert listed.value["count"] == 1
    recorded = listed.value["predictions"][0]
    assert recorded["instrument"]["symbol"] == report.value["instrument"]["symbol"]
    assert recorded["recommendation"] == report.value["recommendation"]


@pytest.mark.asyncio
async def test_list_journal_surfaces_the_persisted_trade_trail(executor):
    # An empty journal store is an honest empty list, never an error.
    empty = await executor.execute_safe("list_journal", {})
    assert empty.ok, empty.error
    assert empty.value["count"] == 0
    assert empty.value["entries"] == []

    # simulate_strategy persists whatever settled. On MOCK data nothing trades,
    # so the trail stays empty -- the tool must not fabricate a row to look busy.
    sim = await executor.execute_safe(
        "simulate_strategy",
        {"symbol": "AAPL", "strategy": "trend_following", "limit": 60, "warmup": 25},
    )
    assert sim.ok, sim.error
    assert sim.value["journal"]["entry_count"] == 0

    still_empty = await executor.execute_safe("list_journal", {})
    assert still_empty.ok, still_empty.error
    assert still_empty.value["count"] == 0


@pytest.mark.asyncio
async def test_evaluate_track_record_tool_is_honest_on_a_thin_sample(executor):
    # Nothing recorded yet -> a valid "nothing to measure" summary, not an error.
    empty = await executor.execute_safe("evaluate_track_record", {})
    assert empty.ok, empty.error
    assert empty.value["sample_size"] == 0
    assert empty.value["is_reliable"] is False

    # Record one prediction, then evaluate the track record over it.
    await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    result = await executor.execute_safe("evaluate_track_record", {})
    assert result.ok, result.error
    payload = result.value
    # One just-created prediction is far below any reliable sample; the aggregate
    # is reported but never dressed up as a track record.
    assert payload["sample_size"] == 1
    assert payload["is_reliable"] is False
    assert "counts" in payload
    assert payload["limitations"]


@pytest.mark.asyncio
async def test_run_monitoring_pass_tool_is_honest(executor):
    # Empty history -> a valid quiet sweep, not an error.
    empty = await executor.execute_safe("run_monitoring_pass", {})
    assert empty.ok, empty.error
    assert empty.value["swept"] == 0
    assert empty.value["performance"]["is_reliable"] is False

    # Record one prediction, then sweep. On MOCK data the just-recorded prediction
    # resolves PENDING/UNRESOLVABLE (no future candles yet) -> swept but never a
    # reliable track record.
    await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    result = await executor.execute_safe("run_monitoring_pass", {})
    assert result.ok, result.error
    payload = result.value
    assert payload["swept"] == 1
    assert payload["resolved"] + payload["pending"] + payload["unresolvable"] == 1
    assert payload["performance"]["is_reliable"] is False


@pytest.mark.asyncio
async def test_outcome_history_tools_read_the_accumulated_store(executor):
    # Empty store -> honest empty history, not an error.
    listed = await executor.execute_safe("list_outcomes", {})
    assert listed.ok, listed.error
    assert listed.value["count"] == 0

    hist = await executor.execute_safe("evaluate_outcome_history", {})
    assert hist.ok, hist.error
    assert hist.value["sample_size"] == 0
    assert hist.value["is_reliable"] is False

    # A monitoring sweep after one recorded prediction accumulates an outcome into
    # the durable store, which the history tools then read back.
    await executor.execute_safe(
        "generate_trading_report", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    await executor.execute_safe("run_monitoring_pass", {})
    listed2 = await executor.execute_safe("list_outcomes", {})
    assert listed2.ok, listed2.error
    assert listed2.value["count"] == 1


@pytest.mark.asyncio
async def test_audit_calibration_tool_is_honest_on_empty_history(executor):
    result = await executor.execute_safe("audit_calibration", {})
    assert result.ok, result.error
    payload = result.value
    # Nothing accumulated -> an honest "cannot measure yet", not an error and no
    # fabricated correction.
    assert payload["sample_size"] == 0
    assert payload["bias"] == "unknown"
    assert payload["proposed_correction"] is None
    assert payload["is_reliable"] is False


@pytest.mark.asyncio
async def test_recalibrate_probability_tool_leaves_mock_unchanged(executor):
    result = await executor.execute_safe(
        "recalibrate_probability", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    # No accumulated history + MOCK estimate -> the correction is untrusted and
    # the probability is left exactly as-is (never manufactured).
    assert payload["applied"] is False
    assert payload["correction"]["trusted"] is False
    assert payload["corrected_p_up"] == payload["raw_p_up"]


@pytest.mark.asyncio
async def test_monitoring_loop_tools_report_disabled_state(executor):
    # Default config: the loop is disabled, so status reports not running /
    # disabled and start keeps it off.
    status = await executor.execute_safe("monitoring_loop_status", {})
    assert status.ok, status.error
    assert status.value["running"] is False
    assert status.value["enabled"] is False

    started = await executor.execute_safe("start_monitoring_loop", {})
    assert started.ok, started.error
    assert started.value["started"] is False
    assert started.value["running"] is False

    stopped = await executor.execute_safe("stop_monitoring_loop", {})
    assert stopped.ok, stopped.error
    assert stopped.value["stopped"] is True
    assert stopped.value["running"] is False





# ==============================================================
# Chart engine tools (Phase 3)
# ==============================================================


@pytest.mark.asyncio
async def test_build_chart_data_tool_projects_series(executor):
    result = await executor.execute_safe(
        "build_chart_data", {"symbol": "AAPL", "timeframe": "1d", "limit": 120}
    )
    assert result.ok, result.error
    value = result.value
    assert value["instrument"]["symbol"] == "AAPL"
    assert value["timeframe"] == "1d"
    assert value["point_count"] == 120
    assert "recent_points" in value
    assert "price_low" in value and "price_high" in value
    assert "quality" in value


@pytest.mark.asyncio
async def test_synchronize_charts_tool_aligns_symbols(executor):
    result = await executor.execute_safe(
        "synchronize_charts", {"symbols": "AAPL, MSFT", "timeframe": "1d", "limit": 120}
    )
    assert result.ok, result.error
    value = result.value
    assert value["requested"] == 2
    assert value["aligned"] == 2
    assert set(value["charts"]) == {"AAPL", "MSFT"}
    for entry in value["charts"].values():
        assert entry["synced"] is True
        assert entry["chart"]["point_count"] == 120
        assert entry["window"] is not None


@pytest.mark.asyncio
async def test_synchronize_charts_tool_rejects_too_many_symbols(executor):
    symbols = ", ".join(f"S{i}" for i in range(9))
    result = await executor.execute_safe(
        "synchronize_charts", {"symbols": symbols, "timeframe": "1d"}
    )
    assert result.ok
    assert "error" in result.value


@pytest.mark.asyncio
async def test_capture_chart_screenshot_reports_headless_honestly(executor):
    # No ScreenService is registered in this wiring: the tool must say so
    # rather than fabricate a frame.
    result = await executor.execute_safe("capture_chart_screenshot", {})
    assert result.ok
    assert "error" in result.value
    assert "unavailable" in result.value["error"]


@pytest.mark.asyncio
async def test_observe_chart_reports_missing_vision_honestly(executor):
    # Neither ScreenService nor VisionService is registered in this wiring:
    # the tool must degrade honestly rather than fabricate observations.
    result = await executor.execute_safe("observe_chart", {"symbol": "AAPL"})
    assert result.ok
    assert "error" in result.value
    assert "unavailable" in result.value["error"]


@pytest.mark.asyncio
async def test_build_hybrid_context_unifies_numbers_without_visual(executor):
    # Headless wiring (no capture service): the numerical sections are all
    # present and the visual read degrades to honest limitations.
    result = await executor.execute_safe(
        "build_hybrid_context", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    assert payload["market_state"]["last_price"] is not None
    assert payload["chart_state"] is not None
    assert "signal" in payload["technical_state"]
    assert payload["visual_state"]["screenshot"] is None
    assert any("Visual:" in line for line in payload["metadata"]["limitations"])
    assert len(payload["trust_rules"]) > 0
    assert payload["metadata"]["recommendation"] == "no_trade"


@pytest.mark.asyncio
async def test_build_hybrid_context_skips_visual_when_asked(executor):
    result = await executor.execute_safe(
        "build_hybrid_context",
        {"symbol": "AAPL", "limit": 120, "with_visual": False},
    )
    assert result.ok, result.error
    assert result.value["visual_state"]["observations"] == []
    assert result.value["metadata"]["recommendation"] == "no_trade"


@pytest.mark.asyncio
async def test_brief_instrument_tool_accepts_the_visual_flag(executor):
    result = await executor.execute_safe(
        "brief_instrument",
        {"symbol": "AAPL", "limit": 120, "with_visual": True},
    )
    assert result.ok, result.error
    # No LLM and no hybrid-with-vision in the test container: the brief still
    # narrates the report deterministically rather than failing.
    assert result.value["recommendation"] == "no_trade"
    assert result.value["narrated_by"] == "deterministic-fallback"


@pytest.mark.asyncio
async def test_decide_tool_produces_a_structured_no_trade(executor):
    result = await executor.execute_safe(
        "decide", {"symbol": "AAPL", "limit": 120}
    )
    assert result.ok, result.error
    payload = result.value
    for key in (
        "market_view", "direction", "confidence", "supporting", "contradictory",
        "entry", "stop_loss", "take_profit", "risk_reward_ratio", "invalidation",
        "reasoning", "uncertainty", "provenance", "trust",
    ):
        assert key in payload
    assert payload["recommendation"] == "no_trade"
    assert payload["is_actionable"] is False
    assert payload["uncertainty"], "a NO_TRADE must state its uncertainty"
    assert "no_execution" in payload["trust"]


@pytest.mark.asyncio
async def test_decide_tool_accepts_the_visual_flag(executor):
    result = await executor.execute_safe(
        "decide", {"symbol": "AAPL", "limit": 120, "with_visual": True}
    )
    assert result.ok, result.error
    # Headless wiring: no screenshot, but the decision still lands with a
    # visual note saying so.
    assert result.value["recommendation"] == "no_trade"
    assert result.value["visual_note"] is not None


# ==============================================================
# Paper-trading simulation tool (Phase 14)
# ==============================================================


@pytest.mark.asyncio
async def test_simulate_strategy_tool_labels_a_mock_run_unreliable(executor):
    # This wiring runs on MockMarketDataProvider, so the run must come back
    # unreliable and say why. A simulation over synthetic bars exercises the
    # engine; presenting it as a result would be the exact dishonesty the
    # spec's MOCK rules forbid, and this assertion is the phase's point.
    result = await executor.execute_safe(
        "simulate_strategy",
        {
            "symbol": "AAPL",
            "strategy": "trend_following",
            "timeframe": "1d",
            "limit": 60,
            "warmup": 25,
        },
    )
    assert result.ok, result.error
    value = result.value
    assert value["symbol"] == "AAPL"
    assert value["timeframe"] == "1d"

    report = value["simulation"]
    assert report["is_reliable"] is False
    assert report["provenance"]["tier"] == "mock"
    assert any("MOCK" in line for line in report["limitations"])
    assert report["bars"] == 60
    assert report["warmup"] == 25
    # The virtual account starts from the configured balance, not a default
    # invented at the tool boundary.
    assert report["initial_equity"] == get_settings().TRADING_SIM_INITIAL_BALANCE
    # One mark per evaluated bar, and every counter the report is allowed to
    # carry is present even when the run traded nothing.
    assert len(report["equity_curve"]) == 60 - 25
    assert report["trade_count"] == 0
    assert report["trades"] == []
    assert set(report["exits"]) == {
        "target",
        "stop",
        "ambiguous",
        "forced_end",
    }
    # The journal section mirrors the run: no trades, no entries.
    journal = value["journal"]
    assert journal["entry_count"] == 0
    assert journal["entries"] == []


@pytest.mark.asyncio
async def test_simulate_strategy_tool_states_its_cost_model(executor):
    # §7: the run's transaction assumptions travel with the result rather than
    # being left for the reader to guess -- including when they are zero.
    result = await executor.execute_safe(
        "simulate_strategy",
        {
            "symbol": "AAPL",
            "strategy": "trend_following",
            "limit": 60,
            "warmup": 25,
            "commission_bps": 5.0,
        },
    )
    assert result.ok, result.error
    assumptions = " ".join(result.value["simulation"]["assumptions"])

    assert "no intrabar entry is modelled" in assumptions
    assert "from bar t+1 onward" in assumptions
    assert "Commission is 5 bps" in assumptions
    # Slippage was not overridden, so it keeps its configured default -- and is
    # named either way.
    assert "Slippage is" in assumptions


@pytest.mark.asyncio
async def test_simulate_strategy_tool_refuses_an_unknown_strategy(executor):
    result = await executor.execute_safe(
        "simulate_strategy", {"symbol": "AAPL", "strategy": "not_a_strategy"}
    )
    assert not result.ok
    assert "not_a_strategy" in (result.error or "")


# ==============================================================
# Journal analytics tool (Phase 22)
# ==============================================================


@pytest.mark.asyncio
async def test_journal_performance_tool_labels_a_mock_book_unreliable(executor):
    # Same MOCK wiring: a journal built from a mock paper-trade run is not a
    # track record, and the analytics must say so rather than report numbers.
    result = await executor.execute_safe(
        "journal_performance",
        {
            "symbol": "AAPL",
            "strategy": "trend_following",
            "timeframe": "1d",
            "limit": 60,
            "warmup": 25,
        },
    )
    assert result.ok, result.error
    value = result.value
    assert value["symbol"] == "AAPL"
    assert value["strategy"] == "trend_following"
    analytics = value["analytics"]
    assert analytics["is_reliable"] is False
    # The book is empty or thin on mock bars; either way it is flagged, and
    # the shape the UI consumes is present.
    assert "trades" in analytics
    assert "closed_trades" in analytics
    assert "open_trades" in analytics
    assert isinstance(analytics["monthly_return"], list)
    assert isinstance(analytics["breakdowns"], list)
    assert isinstance(analytics["limitations"], list)
    assert analytics["limitations"]


@pytest.mark.asyncio
async def test_journal_performance_tool_refuses_an_unknown_strategy(executor):
    result = await executor.execute_safe(
        "journal_performance", {"symbol": "AAPL", "strategy": "not_a_strategy"}
    )
    assert not result.ok
    assert "not_a_strategy" in (result.error or "")


# ==============================================================
# Alerts (Phase 25 -- Trading reachable through the tool surface)
# ==============================================================


@pytest.mark.asyncio
async def test_list_alerts_tool_is_empty_and_honest_before_anything_fires(executor):
    result = await executor.execute_safe("list_alerts", {})
    assert result.ok, result.error
    value = result.value
    assert value["count"] == 0
    assert value["alerts"] == []
    # The channel wired by the fixture is reported, so the UI knows where an
    # alert would go.
    assert "desktop" in value["channels"]


@pytest.mark.asyncio
async def test_watch_price_tool_does_not_fire_when_threshold_not_crossed(executor):
    # The mock quote sits at ~144.85; a threshold far above it is not crossed.
    result = await executor.execute_safe(
        "watch_price", {"symbol": "AAPL", "threshold": 10_000.0, "direction": "above"}
    )
    assert result.ok, result.error
    value = result.value
    assert value["crossed"] is False
    assert value["fired"] is False
    assert value["alert"] is None
    assert value["deliveries"] == []


@pytest.mark.asyncio
async def test_watch_price_tool_refuses_to_fire_on_a_mock_quote(executor):
    # The threshold IS crossed (price ~144.85 is above 100), but the quote is
    # MOCK-tier, so a synthetic number must never raise a real alert.
    result = await executor.execute_safe(
        "watch_price", {"symbol": "AAPL", "threshold": 100.0, "direction": "above"}
    )
    assert result.ok, result.error
    value = result.value
    assert value["crossed"] is True
    assert value["fired"] is False
    assert value["alert"] is None
    assert "MOCK" in value["reason"]
    assert value["provenance"]["tier"] == "mock"
    # Nothing reached the alert engine.
    alerts = await executor.execute_safe("list_alerts", {})
    assert alerts.value["count"] == 0


@pytest.mark.asyncio
async def test_watch_price_tool_rejects_an_unknown_direction(executor):
    result = await executor.execute_safe(
        "watch_price", {"symbol": "AAPL", "threshold": 100.0, "direction": "sideways"}
    )
    assert not result.ok
    assert "sideways" in (result.error or "")


@pytest.mark.asyncio
async def test_watch_price_tool_fires_on_a_live_crossing_and_list_alerts_sees_it():
    # A dedicated non-mock wiring: a PRIMARY-tier quote that has crossed the
    # threshold must raise exactly one alert, route it, and surface it to
    # list_alerts. Wired here (not in the autouse MOCK fixture) because the
    # whole point is a reliable, non-mock source.
    from .conftest import FakeProvider, make_market_data

    settings = get_settings()
    data = make_market_data([100.0 + i for i in range(30)], symbol="AAPL")
    quote = Quote(
        instrument=Instrument.parse("AAPL"),
        price=150.0,
        timestamp=datetime.now(UTC),
        provenance=Provenance(source="fake", tier=SourceTier.PRIMARY),
    )
    provider = FakeProvider(data, quote=quote)
    market_data = MarketDataService(provider, settings)
    router = AlertRouter()
    collector = CollectingDeliveryProvider()
    router.register(collector)
    alerts = AlertService(router, settings, event_bus=None)

    container.register_singleton(MarketDataService, lambda: market_data)
    container.register_singleton(AlertService, lambda: alerts)
    try:
        executor = ToolExecutor(tool_registry, timeout_seconds=None)
        result = await executor.execute_safe(
            "watch_price",
            {"symbol": "AAPL", "threshold": 140.0, "direction": "above"},
        )
        assert result.ok, result.error
        value = result.value
        assert value["crossed"] is True
        assert value["fired"] is True
        assert value["alert"] is not None
        assert value["alert"]["kind"] == "price"
        assert value["provenance"]["tier"] == "primary"
        # Routed to the one wired channel, and delivered.
        assert value["deliveries"]
        assert all(d["delivered"] for d in value["deliveries"])
        # The engine kept it, and list_alerts surfaces exactly it.
        assert len(collector.alerts) == 1
        listed = await executor.execute_safe("list_alerts", {})
        assert listed.value["count"] == 1
        assert listed.value["alerts"][0]["kind"] == "price"
    finally:
        container.remove(MarketDataService)
        container.remove(AlertService)
