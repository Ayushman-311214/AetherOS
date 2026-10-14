"""
WatchlistScanService: deterministic multi-instrument ranking.

These tests wire a real AnalysisService over a controllable provider (no
network) so the scan's *ranking and honesty* are pinned against known inputs
(CLAUDE.md sections 1, 26, 28): a strong directional name is actionable and
ranks ahead of a flat one; a symbol whose data cannot be fetched is an error row
(never dropped or fabricated), ranked last; and a MOCK feed is scanned but every
row is flagged not actionable / not reliable.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import SourceTier, Timeframe
from aetheros.trading.domain.market_data import MarketData, Quote
from aetheros.trading.errors import ProviderError
from aetheros.trading.providers.base import MarketDataProvider
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.scan_service import WatchlistScanService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)

from .conftest import make_market_data

_UP = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
_DOWN = [200.0 - i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
_FLAT = [100.0 + (0.2 if i % 2 else -0.2) for i in range(120)]


class _TrendProvider(MarketDataProvider):
    """Returns crafted PRIMARY candles per symbol; raises for named symbols."""

    name = "trend-test"
    tier = SourceTier.PRIMARY

    def __init__(self, series: dict[str, list[float]], *, fail: set[str] | None = None):
        self._series = series
        self._fail = set(fail or ())

    async def get_candles(self, instrument, timeframe, *, limit) -> MarketData:
        symbol = instrument.symbol
        if symbol in self._fail:
            raise ProviderError(f"synthetic fetch failure for {symbol}")
        return make_market_data(self._series[symbol], symbol=symbol)

    async def get_quote(self, instrument) -> Quote:  # pragma: no cover - unused
        raise NotImplementedError


def _analysis_service(provider) -> AnalysisService:
    settings = get_settings()
    return AnalysisService(
        MarketDataService(provider, settings),
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )


def _scan_service(provider) -> WatchlistScanService:
    return WatchlistScanService(_analysis_service(provider), get_settings())


@pytest.mark.asyncio
async def test_actionable_names_rank_ahead_and_errors_sink():
    provider = _TrendProvider(
        {"UP": _UP, "DOWN": _DOWN, "FLAT": _FLAT}, fail={"BOOM"}
    )
    result = await _scan_service(provider).scan(["UP", "DOWN", "FLAT", "BOOM"])

    assert result.requested == 4
    assert result.errored == 1
    assert result.analysed == 3

    # The errored row is present, flagged, and ranked last.
    assert result.entries[-1].symbol == "BOOM"
    assert result.entries[-1].errored is True
    assert result.entries[-1].is_actionable is False

    # Every actionable row precedes every non-actionable one, and the top row is
    # an actionable one (a strong trend earns actionability on non-mock data).
    flags = [e.is_actionable for e in result.entries]
    assert flags == sorted(flags, reverse=True)
    assert result.actionable >= 1
    assert result.entries[0].is_actionable is True
    by_symbol = {e.symbol: e for e in result.entries}
    assert by_symbol["UP"].is_actionable is True


@pytest.mark.asyncio
async def test_mock_feed_is_scanned_but_never_actionable():
    result = await WatchlistScanService(
        _analysis_service(MockMarketDataProvider()), get_settings()
    ).scan(["AAPL", "MSFT"])

    assert result.requested == 2
    assert result.errored == 0
    for e in result.entries:
        assert e.is_mock is True
        assert e.is_reliable is False
        assert e.is_actionable is False


@pytest.mark.asyncio
async def test_blank_and_duplicate_symbols_are_normalised():
    provider = _TrendProvider({"UP": _UP})
    result = await _scan_service(provider).scan(["UP", "  ", "UP", ""])

    # Blanks dropped, duplicate collapsed -> a single unique symbol scanned.
    assert result.requested == 1
    assert len(result.entries) == 1
    assert result.entries[0].symbol == "UP"


@pytest.mark.asyncio
async def test_scan_is_deterministic():
    provider = _TrendProvider({"UP": _UP, "DOWN": _DOWN, "FLAT": _FLAT})
    a = (await _scan_service(provider).scan(["UP", "DOWN", "FLAT"])).to_dict()
    b = (await _scan_service(provider).scan(["UP", "DOWN", "FLAT"])).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b
