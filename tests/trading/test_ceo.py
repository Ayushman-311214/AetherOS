"""
TradingCEOService: the LLM narration layer over the deterministic core.

These tests pin the spec's division of labour (CLAUDE.md sections 2, 3, 10, 28):
the deterministic report decides, the LLM only narrates. A fake, deterministic
LLMProvider stands in for a real one (no network): the brief embeds the report
verbatim as the source of truth, copies the recommendation/direction off it (not
off the prose), falls back to a deterministic summary when no LLM is wired or the
call fails, and narrates a MOCK run honestly as NO_TRADE.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.ceo_service import TradingCEOService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


class _FakeLLM:
    """A deterministic, offline stand-in for an LLMProvider.

    It records the messages it was handed (so tests can assert the report was
    passed in) and returns a fixed narrative. ``mode`` can force a failure or an
    empty response to exercise the deterministic fallback.
    """

    def __init__(self, mode: str = "ok") -> None:
        self._mode = mode
        self.calls: list[list[dict[str, Any]]] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-1"

    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        self.calls.append(messages)
        if self._mode == "raise":
            raise RuntimeError("llm unavailable")
        if self._mode == "empty":
            return "   "
        return "NARRATIVE: the report says what it says."


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


def _service(llm=None) -> TradingCEOService:
    return TradingCEOService(_orchestrator(), get_settings(), llm=llm)


@pytest.mark.asyncio
async def test_brief_embeds_the_report_and_narrates_via_llm():
    llm = _FakeLLM()
    brief = await _service(llm).brief("AAPL", "1d", limit=120)

    # The LLM was handed the deterministic report, and the brief embeds it.
    assert llm.calls, "the LLM should have been called"
    assert "report" in brief.to_dict()
    assert brief.report["recommendation"] == brief.recommendation
    assert brief.narrative.startswith("NARRATIVE:")
    assert brief.narrated_by == "fake:fake-1"


@pytest.mark.asyncio
async def test_recommendation_comes_from_the_report_not_the_prose():
    # On MOCK data the deterministic core says NO_TRADE; the brief must reflect
    # that regardless of what the narration says.
    brief = await _service(_FakeLLM()).brief("AAPL", "1d", limit=120)
    assert brief.recommendation == "no_trade"
    assert brief.is_actionable is False


@pytest.mark.asyncio
async def test_no_llm_falls_back_to_a_deterministic_summary():
    brief = await _service(llm=None).brief("AAPL", "1d", limit=120)
    assert brief.narrated_by == "deterministic-fallback"
    assert "NO_TRADE" in brief.narrative
    assert "not advice" in brief.narrative


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_the_deterministic_summary():
    brief = await _service(_FakeLLM(mode="raise")).brief("AAPL", "1d", limit=120)
    assert brief.narrated_by == "deterministic-fallback"
    assert brief.recommendation == "no_trade"


@pytest.mark.asyncio
async def test_empty_llm_response_degrades_to_the_deterministic_summary():
    brief = await _service(_FakeLLM(mode="empty")).brief("AAPL", "1d", limit=120)
    assert brief.narrated_by == "deterministic-fallback"


# ---- free-text interpretation (respond) ----


def test_heuristic_interpret_extracts_ticker_and_timeframe():
    svc = _service(llm=None)
    assert svc._interpret_heuristically("AAPL 1d") == ("AAPL", "1d")
    # Timeframe words map; stopwords are not mistaken for a ticker.
    assert svc._interpret_heuristically("should I look at MSFT weekly") == (
        "MSFT",
        "1wk",
    )
    # SYM:EXCH is preserved (upper-cased).
    sym, tf = svc._interpret_heuristically("brief reliance:nse")
    assert sym == "RELIANCE:NSE"


def test_heuristic_interpret_finds_no_instrument_in_a_bare_question():
    svc = _service(llm=None)
    sym, tf = svc._interpret_heuristically("should i buy the stock today")
    assert sym is None
    assert tf == "1d"


@pytest.mark.asyncio
async def test_respond_briefs_the_identified_instrument():
    brief = await _service(llm=None).respond("analyze AAPL 1d")
    assert brief.instrument_key.endswith("AAPL")
    assert brief.recommendation == "no_trade"  # MOCK data


@pytest.mark.asyncio
async def test_respond_raises_when_no_instrument_identified():
    with pytest.raises(ValueError):
        await _service(llm=None).respond("should i buy the stock today")
