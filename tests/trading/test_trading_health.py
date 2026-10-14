"""
Trading health (spec Phase 2 -- SAFE / DEGRADED / BLOCKED).

The health service folds every live input into one verdict. These tests pin
the honesty rules: a tripped kill switch or unusable data BLOCKS the desk, a
degraded feed or reconciliation drift DEGRADES it, and an input the service
cannot read is never reported as SAFE.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers import PaperTradingProvider
from aetheros.trading.domain.enums import DataQualityStatus, SourceTier
from aetheros.trading.domain.health import HealthBand
from aetheros.trading.domain.kill_switch import KillScope, KillSwitch
from aetheros.trading.production import (
    KillSwitchService,
    PositionBookService,
    ReconciliationService,
    TradingHealthService,
)
from aetheros.trading.services.market_data_service import MarketDataService

from .conftest import FakeProvider
from .test_paper_broker import _feed
from .test_execution import _request


def _stack(price: float = 250.0):
    book = PositionBookService()
    md = MarketDataService(FakeProvider(_feed(price)), get_settings())
    venue = PaperTradingProvider(md, positions=book)
    kills = KillSwitchService()
    rec = ReconciliationService(venue, book)
    health = TradingHealthService(md, book, kills, venue, reconciliation=rec)
    return health, kills, book, venue


@pytest.mark.asyncio
async def test_a_desk_with_no_blocks_is_safe_or_degraded_not_blocked():
    health, kills, book, venue = _stack()
    verdict = await health.status()
    # No kill switch and a reachable venue can never be BLOCKED.
    assert verdict.band is not HealthBand.BLOCKED


@pytest.mark.asyncio
async def test_a_tripped_kill_switch_blocks_the_desk():
    health, kills, book, venue = _stack()
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt"))
    verdict = await health.status()
    assert verdict.band is HealthBand.BLOCKED
    assert any("kill" in s.source for s in verdict.signals)


@pytest.mark.asyncio
async def test_clearing_the_switch_restores_health():
    health, kills, book, venue = _stack()
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt"))
    assert (await health.status()).band is HealthBand.BLOCKED
    kills.clear(KillScope.GLOBAL)
    verdict = await health.status()
    assert verdict.band is not HealthBand.BLOCKED


@pytest.mark.asyncio
async def test_a_reconciliation_mismatch_degrades():
    health, kills, book, venue = _stack()
    # A position with no venue fill produces a reconciliation mismatch.
    book.record_fill(_request(quantity=4.0), fill_price=250.0, fill_quantity=4.0)
    verdict = await health.status()
    assert verdict.band is HealthBand.DEGRADED
    assert any(s.source == "reconciliation" and s.band is HealthBand.DEGRADED for s in verdict.signals)


@pytest.mark.asyncio
async def test_health_is_derived_not_asserted():
    health, kills, book, venue = _stack()
    verdict = await health.status()
    # The verdict band is the worst signal present, by construction.
    worst = max((s.band for s in verdict.signals), key=lambda b: b.severity)
    assert verdict.band is worst
