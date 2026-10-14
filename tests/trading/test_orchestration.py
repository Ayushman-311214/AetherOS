"""
OrchestrationService: the deterministic end-to-end trading-desk pipeline.

These are integration tests over the real services (analysis -> risk ->
optional backtest -> critic -> composed report), driven by the clearly-labelled
MockMarketDataProvider. They pin the spec's honesty contract at the pipeline
level (CLAUDE.md sections 5, 26, 27, 28, 61): synthetic data must degrade to a
NO_TRADE report that is not actionable, the report must never fabricate a
probability, and it must carry both the MOCK and the probability-deferred
limitations so the omissions are visible rather than silent. The orchestrator
composes -- it computes nothing itself, so every number traces to a sub-object.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import ReportRecommendation
from aetheros.trading.events import TradingReportGenerated
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.calendar_service import EventCalendarService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.divergence_service import DivergenceService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)
from aetheros.trading.services.news_service import NewsSentimentService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.anomaly_service import AnomalyService
from aetheros.trading.services.historical_analogue_service import (
    HistoricalAnalogueService,
)
from aetheros.trading.services.macro_service import MacroContextService
from aetheros.trading.services.multi_timeframe_service import MultiTimeframeService
from aetheros.trading.services.regime_service import RegimeService
from aetheros.trading.services.relative_strength_service import (
    RelativeStrengthService,
)
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


def _orchestrator(
    event_bus: EventBus | None = None,
    *,
    with_news: bool = False,
    with_calendar: bool = False,
    with_fundamentals: bool = False,
    with_regime: bool = False,
    with_relative_strength: bool = False,
    with_anomaly: bool = False,
    with_historical: bool = False,
    with_macro: bool = False,
    with_multi_timeframe: bool = False,
    with_divergence: bool = False,
    with_breakout: bool = False,
) -> OrchestrationService:
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )
    news = (
        NewsSentimentService(MockNewsProvider(), settings) if with_news else None
    )
    calendar = (
        EventCalendarService(MockCalendarProvider(), settings)
        if with_calendar
        else None
    )
    fundamentals = (
        FundamentalAnalysisService(MockFundamentalsProvider(), settings)
        if with_fundamentals
        else None
    )
    regime = RegimeService(settings) if with_regime else None
    relative_strength = (
        RelativeStrengthService(settings) if with_relative_strength else None
    )
    anomaly = AnomalyService(settings) if with_anomaly else None
    historical = HistoricalAnalogueService(settings) if with_historical else None
    macro = (
        MacroContextService(RegimeService(settings), settings)
        if with_macro
        else None
    )
    multi_timeframe = (
        MultiTimeframeService(settings) if with_multi_timeframe else None
    )
    divergence = DivergenceService(settings) if with_divergence else None
    breakout = BreakoutService(settings) if with_breakout else None
    return OrchestrationService(
        market_data,
        analysis,
        RiskService(settings),
        BacktestService(settings),
        CriticService(settings),
        settings,
        news=news,
        calendar=calendar,
        fundamentals=fundamentals,
        regime=regime,
        relative_strength=relative_strength,
        anomaly=anomaly,
        historical_analogue=historical,
        macro=macro,
        multi_timeframe=multi_timeframe,
        divergence=divergence,
        breakout=breakout,
        event_bus=event_bus,
    )


@pytest.mark.asyncio
async def test_report_is_no_trade_on_mock_data():
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)

    # Synthetic data can never earn an APPROVE: the honest recommendation is
    # NO_TRADE and the report is not actionable.
    assert report.recommendation is ReportRecommendation.NO_TRADE
    assert report.is_actionable is False


@pytest.mark.asyncio
async def test_report_never_fabricates_probability():
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()

    # The probability layer is not built yet; the field is deliberately null and
    # the omission is stated as a limitation rather than invented.
    assert payload["probability"] is None
    assert any("calibrated probability" in lim for lim in payload["limitations"])


@pytest.mark.asyncio
async def test_report_surfaces_mock_limitation():
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert any("MOCK" in lim for lim in payload["limitations"])


@pytest.mark.asyncio
async def test_report_has_full_section_27_shape():
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()

    for key in (
        "instrument",
        "timeframe",
        "last_price",
        "recommendation",
        "signal",
        "probability",
        "market_regime",
        "key_levels",
        "risk",
        "invalidation",
        "horizon",
        "evidence",
        "technical",
        "structure",
        "critique",
        "backtest",
        "news",
        "calendar",
        "fundamentals",
        "relative_strength",
        "anomaly",
        "historical_analogue",
        "macro",
        "multi_timeframe",
        "divergence",
        "breakout",
        "limitations",
        "provenance",
        "quality",
        "model",
    ):
        assert key in payload, f"missing report key: {key}"
    assert payload["model"]["pipeline"] == "deterministic-core/1.0"
    assert "supports" in payload["key_levels"]
    assert "resistances" in payload["key_levels"]
    # The critic's verdict drives the recommendation -- both must be present.
    assert "verdict" in payload["critique"]


@pytest.mark.asyncio
async def test_report_without_backtest_omits_it():
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert payload["backtest"] is None
    # The horizon still comes from configuration, not from a run.
    assert payload["horizon"]["bars"] == get_settings().TRADING_BACKTEST_HORIZON


@pytest.mark.asyncio
async def test_report_with_backtest_includes_it():
    report = await _orchestrator().generate_report(
        "AAPL", "1d", limit=120, run_backtest=True
    )
    payload = report.to_dict()

    assert payload["backtest"] is not None
    # Walk-forward on synthetic data can never be reliable.
    assert payload["backtest"]["is_reliable"] is False
    # The report's horizon now reflects the backtest's own horizon.
    assert payload["horizon"]["bars"] == report.backtest.horizon


@pytest.mark.asyncio
async def test_report_is_deterministic():
    p1 = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    p2 = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()

    assert p1["recommendation"] == p2["recommendation"]
    assert p1["signal"] == p2["signal"]
    assert p1["critique"]["verdict"] == p2["critique"]["verdict"]


@pytest.mark.asyncio
async def test_report_omits_news_when_layer_absent():
    # When no news service is wired, the report carries an explicit null "news"
    # section rather than fabricating a sentiment read.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "news" in payload
    assert payload["news"] is None


@pytest.mark.asyncio
async def test_report_fuses_news_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_news=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The news layer ran and is surfaced, but on synthetic feeds it can never be
    # reliable, and it must not lift the recommendation above the critic's
    # verdict: mock data stays NO_TRADE and not actionable.
    assert payload["news"] is not None
    assert payload["news"]["is_reliable"] is False
    assert payload["news"]["provenance"]["tier"] == "mock"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_with_news_adds_critic_check_never_failing():
    payload = (
        await _orchestrator(with_news=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    # The news_sentiment check is present and, on a mock/unreliable read, never
    # a hard FAIL -- sentiment is advisory and cannot single-handedly reject.
    assert checks["news_sentiment"] in ("warn", "skipped", "pass")
    assert checks["news_sentiment"] != "fail"
    # No calendar is wired in this helper, so the event_risk check is honestly
    # SKIPPED rather than silently passed.
    assert checks["event_risk"] == "skipped"
    received: list[TradingReportGenerated] = []
    bus = EventBus()
    await bus.subscribe(TradingReportGenerated, lambda e: received.append(e))

    report = await _orchestrator(bus).generate_report("AAPL", "1d", limit=120)

    assert len(received) == 1
    evt = received[0]
    assert evt.instrument_key == report.instrument.key
    assert evt.recommendation == report.recommendation.value
    assert evt.is_actionable is False


@pytest.mark.asyncio
async def test_report_omits_calendar_when_layer_absent():
    # With no calendar service wired, the report carries an explicit null
    # "calendar" section rather than fabricating scheduled events.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "calendar" in payload
    assert payload["calendar"] is None


@pytest.mark.asyncio
async def test_report_fuses_calendar_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_calendar=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The calendar layer ran and is surfaced, but a MOCK calendar can never be
    # reliable and must not veto: the event_risk check WARNs (never FAILs) and
    # the report still degrades to NO_TRADE on synthetic market data.
    assert payload["calendar"] is not None
    assert payload["calendar"]["is_reliable"] is False
    assert payload["calendar"]["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["event_risk"] == "warn"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_fundamentals_when_layer_absent():
    # With no fundamentals service wired, the report carries an explicit null
    # "fundamentals" section rather than fabricating a financial read.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "fundamentals" in payload
    assert payload["fundamentals"] is None


@pytest.mark.asyncio
async def test_report_fuses_fundamentals_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_fundamentals=True).generate_report(
            "AAPL", "1d", limit=120
        )
    ).to_dict()

    # The fundamentals layer ran and is surfaced, but a MOCK read can never be
    # reliable and must not veto: the fundamentals check is advisory (never a
    # hard FAIL) and the report still degrades to NO_TRADE on synthetic data.
    assert payload["fundamentals"] is not None
    assert payload["fundamentals"]["is_reliable"] is False
    assert payload["fundamentals"]["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "fundamentals" in checks
    assert checks["fundamentals"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_regime_when_layer_absent():
    # With no regime service wired, the report carries only the structure-derived
    # trend under "market_regime" and a null nested "regime" -- backward
    # compatible with reports built before the regime layer existed.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "market_regime" in payload
    assert "trend" in payload["market_regime"]
    assert "trend_strength" in payload["market_regime"]
    assert payload["market_regime"]["regime"] is None


@pytest.mark.asyncio
async def test_report_fuses_regime_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_regime=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The regime layer ran and is surfaced, but on synthetic feeds it can never
    # be reliable and must not veto: the market_regime check is advisory (never a
    # hard FAIL) and the report still degrades to NO_TRADE on mock market data.
    regime = payload["market_regime"]["regime"]
    assert regime is not None
    assert regime["is_reliable"] is False
    assert regime["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "market_regime" in checks
    assert checks["market_regime"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_relative_strength_when_layer_absent():
    # With no relative-strength service wired, the report carries an explicit
    # null "relative_strength" section rather than fabricating a sector read.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "relative_strength" in payload
    assert payload["relative_strength"] is None
    # The critic check is honestly SKIPPED rather than silently passed.
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["relative_strength"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_relative_strength_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_relative_strength=True).generate_report(
            "AAPL", "1d", limit=120
        )
    ).to_dict()

    # The relative-strength layer ran and is surfaced, but on synthetic feeds it
    # can never be reliable and must not veto: the relative_strength check is
    # advisory (never a hard FAIL) and the report still degrades to NO_TRADE on
    # mock market data. The benchmark series is fetched from the same MOCK
    # provider, so the read is honestly labelled mock/unreliable.
    rs = payload["relative_strength"]
    assert rs is not None
    assert rs["is_reliable"] is False
    assert rs["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "relative_strength" in checks
    assert checks["relative_strength"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_anomaly_when_layer_absent():
    # With no anomaly service wired, the report carries an explicit null
    # "anomaly" section rather than fabricating an outlier read.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "anomaly" in payload
    assert payload["anomaly"] is None
    # The critic check is honestly SKIPPED rather than silently passed.
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["anomaly"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_anomaly_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_anomaly=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The anomaly layer ran and is surfaced, but on synthetic feeds it can never
    # be reliable and must not veto: the anomaly check is advisory (never a hard
    # FAIL) and the report still degrades to NO_TRADE on mock market data.
    anomaly = payload["anomaly"]
    assert anomaly is not None
    assert anomaly["is_reliable"] is False
    assert anomaly["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "anomaly" in checks
    assert checks["anomaly"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_historical_analogue_when_layer_absent():
    # With no historical-analogue service wired, the report carries an explicit
    # null "historical_analogue" section rather than fabricating a tendency.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "historical_analogue" in payload
    assert payload["historical_analogue"] is None
    # The critic check is honestly SKIPPED rather than silently passed.
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["historical_analogue"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_historical_analogue_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_historical=True).generate_report(
            "AAPL", "1d", limit=300
        )
    ).to_dict()

    # The historical-analogue layer ran and is surfaced, but on synthetic feeds it
    # can never be reliable and must not veto: the historical_analogue check is
    # advisory (never a hard FAIL) and the report still degrades to NO_TRADE on
    # mock market data.
    hist = payload["historical_analogue"]
    assert hist is not None
    assert hist["is_reliable"] is False
    assert hist["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "historical_analogue" in checks
    assert checks["historical_analogue"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_macro_when_layer_absent():
    # With no macro service wired, the report carries an explicit null "macro"
    # section rather than fabricating a market backdrop.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "macro" in payload
    assert payload["macro"] is None
    # The critic check is honestly SKIPPED rather than silently passed.
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["macro_context"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_macro_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_macro=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The macro layer ran (fetching the benchmark from the same MOCK provider) and
    # is surfaced, but it can never be reliable on synthetic data and must not
    # veto: the macro_context check is advisory (never a hard FAIL) and the report
    # still degrades to NO_TRADE on mock market data.
    macro = payload["macro"]
    assert macro is not None
    assert macro["is_reliable"] is False
    assert macro["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "macro_context" in checks
    assert checks["macro_context"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_multi_timeframe_when_layer_absent():
    # With no multi-timeframe service wired, the report carries an explicit null
    # "multi_timeframe" section rather than fabricating a confirmation.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "multi_timeframe" in payload
    assert payload["multi_timeframe"] is None
    # The critic check is honestly SKIPPED rather than silently passed.
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["multi_timeframe"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_multi_timeframe_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_multi_timeframe=True).generate_report(
            "AAPL", "1d", limit=120
        )
    ).to_dict()

    # The multi-timeframe layer ran (a second higher-timeframe analysis on the
    # same MOCK provider) and is surfaced, but it can never be reliable on
    # synthetic data and must not veto: the multi_timeframe check is advisory
    # (never a hard FAIL) and the report still degrades to NO_TRADE.
    mtf = payload["multi_timeframe"]
    assert mtf is not None
    assert mtf["is_reliable"] is False
    assert mtf["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "multi_timeframe" in checks
    assert checks["multi_timeframe"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_divergence_when_layer_absent():
    # With no divergence service wired, the report carries an explicit null
    # "divergence" section rather than fabricating a momentum divergence.
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "divergence" in payload
    assert payload["divergence"] is None
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["divergence"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_divergence_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_divergence=True).generate_report(
            "AAPL", "1d", limit=120
        )
    ).to_dict()

    # The divergence layer ran and is surfaced, but it can never be reliable on
    # synthetic data and must not veto: the divergence check is advisory (never a
    # hard FAIL) and the report still degrades to NO_TRADE on mock market data.
    div = payload["divergence"]
    assert div is not None
    assert div["is_reliable"] is False
    assert div["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "divergence" in checks
    assert checks["divergence"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


@pytest.mark.asyncio
async def test_report_omits_breakout_when_layer_absent():
    payload = (await _orchestrator().generate_report("AAPL", "1d", limit=120)).to_dict()
    assert "breakout" in payload
    assert payload["breakout"] is None
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert checks["breakout"] == "skipped"


@pytest.mark.asyncio
async def test_report_fuses_breakout_as_advisory_but_stays_no_trade():
    payload = (
        await _orchestrator(with_breakout=True).generate_report("AAPL", "1d", limit=120)
    ).to_dict()

    # The breakout layer ran and is surfaced, but it can never be reliable on
    # synthetic data and must not veto: the breakout check is advisory (never a
    # hard FAIL) and the report still degrades to NO_TRADE on mock market data.
    brk = payload["breakout"]
    assert brk is not None
    assert brk["is_reliable"] is False
    assert brk["provenance"]["tier"] == "mock"
    checks = {c["name"]: c["status"] for c in payload["critique"]["checks"]}
    assert "breakout" in checks
    assert checks["breakout"] != "fail"
    assert payload["recommendation"] == ReportRecommendation.NO_TRADE.value
    assert payload["is_actionable"] is False


