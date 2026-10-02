"""
MacroContextService: deterministic broad-market risk-posture read.

These tests are fully deterministic and never touch the network: they hand the
service crafted benchmark ``MarketData`` (the service composes RegimeService and
does no I/O). They assert the honesty rules (CLAUDE.md sections 2, 5, 27, 28): a
trending-up benchmark reads RISK_ON (UP) and is reliable with a non-mock
``MACRO`` evidence item, a trending-down benchmark reads RISK_OFF (DOWN), and
MOCK / too-thin benchmark data yields an UNKNOWN, never-reliable posture with no
fabricated read -- deterministically.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Direction,
    EvidenceType,
    MarketPosture,
    SourceTier,
)
from aetheros.trading.services.macro_service import MacroContextService
from aetheros.trading.services.regime_service import RegimeService

from .conftest import make_market_data

# Clean, mildly-noisy trends with enough bars for the regime warm-up.
_RISING = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
_FALLING = [200.0 - i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]


def _service() -> MacroContextService:
    settings = get_settings()
    return MacroContextService(RegimeService(settings), settings)


@pytest.mark.asyncio
async def test_trending_up_benchmark_is_risk_on_and_reliable():
    m = await _service().analyze(make_market_data(_RISING, symbol="SPY"))

    assert m.posture is MarketPosture.RISK_ON
    assert m.direction is Direction.UP
    assert m.is_reliable is True
    # Surfaced as a non-mock, CALCULATED MACRO evidence item.
    assert m.evidence is not None
    assert m.evidence.type is EvidenceType.MACRO
    assert m.evidence.assertion is Assertion.CALCULATED
    assert m.evidence.direction is Direction.UP
    assert m.evidence.is_reliable is True


@pytest.mark.asyncio
async def test_trending_down_benchmark_is_risk_off():
    m = await _service().analyze(make_market_data(_FALLING, symbol="SPY"))

    assert m.posture is MarketPosture.RISK_OFF
    assert m.direction is Direction.DOWN
    assert m.is_reliable is True


@pytest.mark.asyncio
async def test_mock_benchmark_is_never_reliable():
    m = await _service().analyze(
        make_market_data(_RISING, symbol="MOCKSPY", tier=SourceTier.MOCK)
    )

    # The posture is still classified, but a MOCK benchmark can never be leaned on.
    assert m.posture is MarketPosture.RISK_ON
    assert m.is_reliable is False
    assert any("MOCK" in lim for lim in m.limitations)


@pytest.mark.asyncio
async def test_thin_benchmark_is_unknown_not_fabricated():
    m = await _service().analyze(
        make_market_data([100.0 + i for i in range(20)], symbol="SPY")
    )

    assert m.posture is MarketPosture.UNKNOWN
    assert m.direction is Direction.UNKNOWN
    assert m.is_reliable is False
    assert m.evidence is None


@pytest.mark.asyncio
async def test_is_deterministic():
    md = make_market_data(_RISING, symbol="SPY")
    a = (await _service().analyze(md)).to_dict()
    b = (await _service().analyze(md)).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
