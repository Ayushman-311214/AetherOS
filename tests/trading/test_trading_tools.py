"""
Trading tools exercised through the real ToolRegistry + ToolExecutor.

These are integration tests: they go through the same path an agent would --
resolve the service from the DI container, validate arguments, invoke the tool
-- rather than calling the service directly. They also pin the spec's honesty
rule at the tool boundary: a MOCK result is labelled MOCK and never actionable
(CLAUDE.md sections 11, 61).
"""

from __future__ import annotations

import pytest

# Importing the module registers the @tool functions into the global registry.
import aetheros.trading.tools  # noqa: F401
from aetheros.config.config_loader import get_settings
from aetheros.core.container import container
from aetheros.tools import ToolExecutor, tool_registry
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.calendar_service import EventCalendarService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.divergence_service import DivergenceService
from aetheros.trading.services.explanation_service import ExplanationService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)
from aetheros.trading.services.news_service import NewsSentimentService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.portfolio_service import PortfolioRiskService
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)
from aetheros.trading.services.prediction_evaluator import PredictionEvaluator
from aetheros.trading.services.prediction_store import (
    InMemoryPredictionStore,
    PredictionStore,
)
from aetheros.trading.services.anomaly_service import AnomalyService
from aetheros.trading.services.historical_analogue_service import (
    HistoricalAnalogueService,
)
from aetheros.trading.services.macro_service import MacroContextService
from aetheros.trading.services.multi_timeframe_service import MultiTimeframeService
from aetheros.trading.services.probability_service import ProbabilityService
from aetheros.trading.services.scan_service import WatchlistScanService
from aetheros.trading.services.regime_service import RegimeService
from aetheros.trading.services.relative_strength_service import (
    RelativeStrengthService,
)
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.services.track_record_service import (
    PredictionTrackRecordService,
)
from aetheros.trading.services.monitoring_service import MonitoringService
from aetheros.trading.services.monitoring_scheduler import MonitoringScheduler
from aetheros.trading.services.calibration_history_service import (
    CalibrationHistoryService,
)
from aetheros.trading.services.ceo_service import TradingCEOService
from aetheros.trading.services.ceo_agent_service import CEOAgentService
from aetheros.trading.services.outcome_store import (
    InMemoryOutcomeStore,
    OutcomeStore,
)


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
    scan = WatchlistScanService(analysis, settings)
    multi_timeframe = MultiTimeframeService(settings)
    divergence = DivergenceService(settings)
    breakout = BreakoutService(settings)
    portfolio = PortfolioRiskService(settings)
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
        WatchlistScanService: scan,
        MultiTimeframeService: multi_timeframe,
        DivergenceService: divergence,
        BreakoutService: breakout,
        PortfolioRiskService: portfolio,
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
    ):
        assert tool_registry.exists(name)
    assert "trading.data" in tool_registry.categories()
    assert "trading.analysis" in tool_registry.categories()
    assert "trading.audit" in tool_registry.categories()


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
async def test_calculate_indicator_unknown_is_honest(executor):
    result = await executor.execute_safe(
        "calculate_indicator", {"symbol": "AAPL", "indicator": "nonsense"}
    )
    assert result.ok  # a bad indicator name is data, not a crash
    assert "error" in result.value
    assert "supported" in result.value


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



