"""
AnalysisService: the deterministic end-to-end orchestrator.

Fusion is a transparent weighted vote, never an LLM guess and never a
calibrated probability. When data is mock, unusable or evidence is empty, the
service must say so and refuse to manufacture a signal (spec sections 28, 61).
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction
from aetheros.trading.events import AnalysisCompleted
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.runtime.events.event_bus import EventBus

from .conftest import FakeProvider, make_invalid_market_data


def _analysis_service(provider, event_bus=None):
    settings = get_settings()
    market_data = MarketDataService(provider, settings, event_bus=event_bus)
    return AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
        event_bus=event_bus,
    )


@pytest.mark.asyncio
async def test_mock_analysis_is_labelled_and_not_actionable():
    svc = _analysis_service(MockMarketDataProvider())
    analysis = await svc.analyze("AAPL", "1d", limit=120)

    assert analysis.provenance.is_mock
    assert analysis.is_actionable is False
    assert any("MOCK" in lim for lim in analysis.limitations)
    assert len(analysis.evidence) > 0


@pytest.mark.asyncio
async def test_mock_analysis_is_deterministic():
    svc = _analysis_service(MockMarketDataProvider())
    a = await svc.analyze("AAPL", "1d", limit=120)
    b = await svc.analyze("AAPL", "1d", limit=120)

    # Content-addressed, wall-clock-independent facts must be reproducible.
    assert a.direction is b.direction
    assert a.directional_score == b.directional_score
    assert [e.id for e in a.evidence] == [e.id for e in b.evidence]


@pytest.mark.asyncio
async def test_score_within_bounds_and_direction_consistent():
    svc = _analysis_service(MockMarketDataProvider())
    analysis = await svc.analyze("MSFT", "1d", limit=120)

    assert -1.0 <= analysis.directional_score <= 1.0
    if analysis.directional_score > 0.15:
        assert analysis.direction is Direction.UP
    elif analysis.directional_score < -0.15:
        assert analysis.direction is Direction.DOWN


@pytest.mark.asyncio
async def test_unusable_data_yields_unknown_direction():
    svc = _analysis_service(FakeProvider(make_invalid_market_data()))
    analysis = await svc.analyze("AAPL", "1d", limit=30)

    # INVALID data must not be turned into a directional signal.
    assert analysis.direction is Direction.UNKNOWN
    assert analysis.is_actionable is False
    assert not analysis.quality.usable


@pytest.mark.asyncio
async def test_publishes_analysis_completed():
    received: list[AnalysisCompleted] = []
    bus = EventBus()
    await bus.subscribe(AnalysisCompleted, lambda e: received.append(e))

    svc = _analysis_service(MockMarketDataProvider(), event_bus=bus)
    analysis = await svc.analyze("AAPL", "1d", limit=120)

    assert len(received) == 1
    assert received[0].direction == analysis.direction.value
    assert received[0].evidence_count == len(analysis.evidence)
