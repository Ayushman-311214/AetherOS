"""
MultiTimeframeService: deterministic base-vs-higher-timeframe confirmation.

Two layers of test. The classification rule is pinned directly (it is a pure
function of two directions). The integration cases build real
``TradingAnalysis`` objects from crafted candles via ``analyze_data`` (no
network) and assert the honesty contract (CLAUDE.md sections 5, 28): a base read
in the direction of the higher-timeframe trend is CONFIRMED and reliable with a
non-mock TREND evidence item; an opposing base read is a CONFLICT; and MOCK data
on either timeframe is never reliable.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Direction,
    EvidenceType,
    SourceTier,
    TimeframeAlignment,
)
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.multi_timeframe_service import MultiTimeframeService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.providers.mock_provider import MockMarketDataProvider

from .conftest import make_market_data

_UP = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]


def _mtf() -> MultiTimeframeService:
    return MultiTimeframeService(get_settings())


def _analysis_service() -> AnalysisService:
    settings = get_settings()
    return AnalysisService(
        MarketDataService(MockMarketDataProvider(), settings),
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )


async def _analyse(closes, *, tier: SourceTier = SourceTier.PRIMARY):
    data = make_market_data(closes, tier=tier)
    return await _analysis_service().analyze_data(data, emit=False)


# ---- the classification rule is a pure function of two directions ----


def test_classify_covers_every_alignment():
    c = MultiTimeframeService._classify
    assert c(Direction.UP, Direction.UP) is TimeframeAlignment.CONFIRMED
    assert c(Direction.DOWN, Direction.DOWN) is TimeframeAlignment.CONFIRMED
    assert c(Direction.UP, Direction.DOWN) is TimeframeAlignment.CONFLICT
    assert c(Direction.UP, Direction.SIDEWAYS) is TimeframeAlignment.NEUTRAL
    assert c(Direction.SIDEWAYS, Direction.UP) is TimeframeAlignment.NEUTRAL
    assert c(Direction.UP, Direction.UNKNOWN) is TimeframeAlignment.UNKNOWN
    assert c(Direction.UNKNOWN, Direction.UP) is TimeframeAlignment.UNKNOWN


# ---- integration over real analyses built from crafted candles ----


@pytest.mark.asyncio
async def test_higher_trend_confirms_base_and_is_reliable():
    base = await _analyse(_UP)
    higher = await _analyse(_UP)
    m = _mtf().analyze(base, higher)

    assert base.direction is Direction.UP and higher.direction is Direction.UP
    assert m.alignment is TimeframeAlignment.CONFIRMED
    assert m.direction is Direction.UP
    assert m.is_reliable is True
    assert m.evidence is not None
    assert m.evidence.type is EvidenceType.TREND
    assert m.evidence.assertion is Assertion.CALCULATED
    assert m.evidence.direction is Direction.UP
    assert m.evidence.is_reliable is True


@pytest.mark.asyncio
async def test_mock_data_is_never_reliable():
    base = await _analyse(_UP, tier=SourceTier.MOCK)
    higher = await _analyse(_UP)
    m = _mtf().analyze(base, higher)

    assert m.is_reliable is False
    assert any("MOCK" in lim for lim in m.limitations)


@pytest.mark.asyncio
async def test_is_deterministic():
    base = await _analyse(_UP)
    higher = await _analyse(_UP)
    a = _mtf().analyze(base, higher).to_dict()
    b = _mtf().analyze(base, higher).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
