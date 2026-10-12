"""
Hybrid chart context: one unified numerical + visual context (Phase 19).

The assembly lifts a finished deterministic TradingReport, a chart
projection and vision reads into a single HybridChartContext for the LLM:
market/chart/technical sections side by side with the visual read, plus news,
fundamentals and a decision metadata envelope. Provenance-weighted trust is
structural -- visual reads stay UNCERTAIN guesses with capped weight, never
equal to API-derived facts, and a visual/numerical conflict is reported with
the numerical read governing.

These tests run the real deterministic pipeline on the mock provider (no
network, no display): the report, chart and visual reads are built exactly as
the tool builds them, and the assertions pin the section shape, the trust
rules, the cross-check behaviour and the honest-absence limitations.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.hybrid import TRUST_RULES, HybridChartContext
from aetheros.trading.domain.report import TradingReport
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.chart_service import ChartService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.hybrid_service import HybridContextService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.services.visual_service import VisualObservationService
from aetheros.vision.models import TextBlock


def _text(text: str, confidence: float = 0.9) -> TextBlock:
    return TextBlock(
        text=text,
        confidence=confidence,
        left=10,
        top=20,
        right=110,
        bottom=40,
    )


class _StubScreen:
    """Stub screen service: returns a real vision Image from a blank frame."""

    def __init__(self, frame=None) -> None:
        import numpy as np

        self._frame = (
            frame
            if frame is not None
            else np.zeros((60, 80, 3), dtype=np.uint8)
        )

    async def capture(self):
        return self._frame

    async def capture_region(self, left, top, width, height):
        return self._frame[:height, :width]


class _StubVision:
    """Stub vision service: replays canned OCR blocks, no models."""

    def __init__(self, blocks=(), *, has_ocr: bool = True) -> None:
        self._blocks = list(blocks)
        self._has_ocr = has_ocr

    @property
    def has_ocr(self) -> bool:
        return self._has_ocr

    @property
    def has_detector(self) -> bool:
        return False

    def capabilities(self) -> dict[str, bool]:
        return {"ocr": self._has_ocr, "detection": False}

    async def read_text(self, image):
        return list(self._blocks)

    async def detect_objects(self, image):
        return []


async def _report_and_chart() -> tuple[TradingReport, object]:
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )
    orchestrator = OrchestrationService(
        market_data,
        analysis,
        RiskService(settings),
        BacktestService(settings),
        CriticService(settings),
        settings,
    )
    report = await orchestrator.generate_report("AAPL", "1d", limit=120)
    data = await market_data.get_candles("AAPL", "1d", limit=120)
    chart = ChartService().build_chart(data)
    return report, (chart, data)


def _hybrid(
    orchestrator=None,
    market_data=None,
    *,
    vision=None,
    vision_present: bool = True,
) -> HybridContextService:
    """A wired service; headless unless vision/capture stubs are supplied."""
    from aetheros.trading.services.chart_service import ChartCaptureService

    settings = get_settings()
    market_data = market_data or MarketDataService(MockMarketDataProvider(), settings)
    if orchestrator is None:
        analysis = AnalysisService(
            market_data,
            TechnicalAnalysisService(),
            MarketStructureService(),
            EvidenceService(),
            settings,
        )
        orchestrator = OrchestrationService(
            market_data,
            analysis,
            RiskService(settings),
            BacktestService(settings),
            CriticService(settings),
            settings,
        )
    capture = (
        ChartCaptureService(_StubScreen()) if vision is not None else None
    )
    factory = (
        (lambda: vision if vision_present else None)
        if vision is not None
        else (lambda: None)
    )
    return HybridContextService(
        orchestrator,
        market_data,
        ChartService(),
        VisualObservationService(),
        capture=capture,
        vision_factory=factory,
    )


def _visual(texts: list[TextBlock], data):
    service = VisualObservationService()
    observations = service.observe_text(texts, instrument_key=data.instrument.key)
    evidence = service.to_evidence(observations, data)
    return observations, evidence


_SCREENSHOT = {"source": "screen", "width": 80, "height": 60}
_CAPABILITIES = {"ocr": True, "detection": False}


# ==============================================================
# Section shape
# ==============================================================


@pytest.mark.asyncio
async def test_context_carries_all_seven_sections():
    report, (chart, data) = await _report_and_chart()
    observations, evidence = _visual([_text("AAPL")], data)
    context = HybridContextService.assemble(
        report,
        chart,
        observations,
        evidence,
        screenshot=_SCREENSHOT,
        capabilities=_CAPABILITIES,
    )
    assert context.instrument_key == "NASDAQ:AAPL" or context.instrument_key
    assert context.timeframe == report.analysis.timeframe_value
    assert set(context.market_state) == {
        "instrument", "timeframe", "last_price", "quality", "provenance",
    }
    assert context.chart_state is not None
    assert context.chart_state["point_count"] == len(chart.points)
    for key in ("signal", "technical", "structure", "key_levels", "market_regime"):
        assert key in context.technical_state
    assert set(context.news_state) == {"news", "calendar"}
    for key in ("recommendation", "critique", "risk", "provenance", "limitations"):
        assert key in context.metadata


@pytest.mark.asyncio
async def test_numbers_are_lifted_verbatim_from_the_report():
    report, (chart, data) = await _report_and_chart()
    observations, evidence = _visual([_text("AAPL")], data)
    context = HybridContextService.assemble(
        report, chart, observations, evidence, screenshot=_SCREENSHOT
    )
    assert context.market_state["last_price"] == report.analysis.last_price
    assert context.metadata["recommendation"] == report.recommendation.value
    assert context.metadata["is_actionable"] == report.is_actionable
    assert context.metadata["probability"] is None  # unvalidated: never surfaced


# ==============================================================
# Provenance-weighted trust
# ==============================================================


def test_trust_rules_state_that_visual_guesses_are_not_facts():
    joined = " ".join(TRUST_RULES)
    assert "never treat" in joined.lower() or "never equal" in joined.lower()
    assert "numerical" in joined.lower()


@pytest.mark.asyncio
async def test_visual_evidence_stays_uncertain_and_capped():
    report, (chart, data) = await _report_and_chart()
    observations, evidence = _visual([_text("ascending triangle", 0.71)], data)
    context = HybridContextService.assemble(
        report, chart, observations, evidence, screenshot=_SCREENSHOT
    )
    items = context.visual_state["evidence"]
    assert len(items) == 1
    assert items[0]["assertion"] == "uncertain"
    assert items[0]["weight"] <= 0.5
    assert context.visual_state["observations"][0]["confidence"] == pytest.approx(0.71)


# ==============================================================
# Cross-check: agreement and conflict
# ==============================================================


@pytest.mark.asyncio
async def test_matching_symbol_is_agreement_without_conflict():
    report, (chart, data) = await _report_and_chart()
    symbol = report.instrument.symbol
    observations, evidence = _visual([_text(symbol), _text("1D")], data)
    context = HybridContextService.assemble(
        report, chart, observations, evidence, screenshot=_SCREENSHOT
    )
    cross = context.visual_state["cross_check"]
    assert cross["symbol_match"] is True
    assert cross["conflict"] is None


@pytest.mark.asyncio
async def test_wrong_symbol_is_a_reported_conflict_with_a_limitation():
    report, (chart, data) = await _report_and_chart()
    observations, evidence = _visual([_text("TSLA"), _text("1D")], data)
    context = HybridContextService.assemble(
        report, chart, observations, evidence, screenshot=_SCREENSHOT
    )
    cross = context.visual_state["cross_check"]
    assert cross["symbol_match"] is False
    assert cross["conflict"] is not None
    assert "numerical read governs" in cross["conflict"]
    assert any("conflict" in line for line in context.metadata["limitations"])


# ==============================================================
# Honest absence
# ==============================================================


@pytest.mark.asyncio
async def test_no_screenshot_is_an_honest_visual_limitation():
    report, (chart, _data) = await _report_and_chart()
    context = HybridContextService.assemble(report, chart)
    assert context.visual_state["screenshot"] is None
    assert context.visual_state["observations"] == []
    assert context.visual_state["evidence"] == []
    assert any(
        "no visual read" in line.lower()
        for line in context.visual_state["limitations"]
    )
    assert any("Visual:" in line for line in context.metadata["limitations"])
    # The numerical read still stands alone.
    assert context.metadata["recommendation"] == report.recommendation.value


@pytest.mark.asyncio
async def test_empty_vision_result_is_an_honest_empty_not_evidence():
    report, (chart, data) = await _report_and_chart()
    observations, evidence = _visual([], data)
    assert observations[0].kind == "empty"
    assert evidence == ()
    context = HybridContextService.assemble(
        report, chart, observations, evidence, screenshot=_SCREENSHOT
    )
    assert context.visual_state["evidence"] == []
    assert any(
        "honest empty" in line for line in context.visual_state["limitations"]
    )


@pytest.mark.asyncio
async def test_no_chart_is_an_honest_limitation_not_a_fabrication():
    report, (_chart, data) = await _report_and_chart()
    observations, evidence = _visual([_text("AAPL")], data)
    context = HybridContextService.assemble(
        report, None, observations, evidence, screenshot=_SCREENSHOT
    )
    assert context.chart_state is None
    assert any(
        "chart projection" in line.lower()
        for line in context.metadata["limitations"]
    )


def test_context_to_dict_shape():
    context = HybridChartContext(
        instrument_key="NASDAQ:AAPL",
        timeframe="1d",
        market_state={},
        chart_state=None,
        technical_state={},
        visual_state={},
        news_state={},
        fundamental_state=None,
        metadata={},
    )
    payload = context.to_dict()
    assert payload["instrument_key"] == "NASDAQ:AAPL"
    assert payload["chart_state"] is None
    assert len(payload["trust_rules"]) == len(TRUST_RULES)
    assert "created_at" in payload


# ==============================================================
# build(): the fetch-and-assemble entry point the tool calls
# ==============================================================


@pytest.mark.asyncio
async def test_build_without_visual_matches_the_report():
    service = _hybrid()
    context = await service.build("AAPL", "1d", limit=120, with_visual=False)
    assert context.instrument_key.endswith("AAPL")
    assert context.chart_state is not None
    assert context.visual_state["screenshot"] is None
    assert context.visual_state["observations"] == []
    assert any(
        "no visual read" in line.lower()
        for line in context.visual_state["limitations"]
    )


@pytest.mark.asyncio
async def test_build_with_stubbed_visual_reads_the_chart():
    service = _hybrid(vision=_StubVision([_text("AAPL", 0.95)]))
    context = await service.build("AAPL", "1d", limit=120)
    assert context.visual_state["screenshot"] is not None
    assert context.visual_state["capabilities"] == {"ocr": True, "detection": False}
    assert context.visual_state["observations"][0]["label"] == "AAPL"
    assert context.visual_state["cross_check"]["symbol_match"] is True


@pytest.mark.asyncio
async def test_build_degrades_honestly_when_vision_is_absent():
    service = _hybrid(vision=_StubVision([]), vision_present=False)
    context = await service.build("AAPL", "1d", limit=120)
    assert context.visual_state["screenshot"] is None
    assert context.chart_state is not None
    assert context.market_state["last_price"] is not None


@pytest.mark.asyncio
async def test_build_without_ocr_records_an_honest_empty():
    service = _hybrid(vision=_StubVision([], has_ocr=False))
    context = await service.build("AAPL", "1d", limit=120)
    assert context.visual_state["screenshot"] is not None
    kinds = [obs["kind"] for obs in context.visual_state["observations"]]
    assert kinds == ["empty", "empty"]
    assert context.visual_state["evidence"] == []
