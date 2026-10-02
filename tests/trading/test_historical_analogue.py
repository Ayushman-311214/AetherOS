"""
HistoricalAnalogueService: deterministic nearest-analogue forward-outcome read.

These tests are fully deterministic and never touch the network: they hand the
service crafted ``MarketData`` (the RegimeService / AnomalyService pattern -- the
service takes one candle series and does no I/O). They assert the honesty rules
(CLAUDE.md sections 1, 7, 15, 27, 28): on a persistently rising tape the closest
past analogues all rose, so the read leans UP and is reliable with a non-mock
``HISTORICAL`` evidence item; a falling tape leans DOWN; and MOCK / too-thin
history yields an UNKNOWN, never-reliable read with no fabricated numbers -- all
deterministically, and look-ahead-safe (analogues are only past bars whose
forward outcome is fully realised).
"""

from __future__ import annotations

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.services.historical_analogue_service import (
    HistoricalAnalogueService,
)

from .conftest import make_market_data

# Long, mildly-noisy trends: >= 300 bars so there are plenty of labelled
# analogues past the indicator warm-up and the forward horizon.
_RISING = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(300)]
_FALLING = [400.0 - i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(300)]


def _service() -> HistoricalAnalogueService:
    return HistoricalAnalogueService(get_settings())


def test_rising_tape_leans_up_and_reliable():
    a = _service().analyze(make_market_data(_RISING, symbol="RISE"))

    assert a.direction is Direction.UP
    assert a.is_reliable is True
    assert a.up_rate is not None and a.up_rate > 0.6
    assert a.mean_forward_return is not None and a.mean_forward_return > 0
    assert a.neighbors == get_settings().TRADING_HIST_NEIGHBORS
    # Surfaced as a non-mock, CALCULATED HISTORICAL evidence item.
    assert a.evidence is not None
    assert a.evidence.type is EvidenceType.HISTORICAL
    assert a.evidence.assertion is Assertion.CALCULATED
    assert a.evidence.direction is Direction.UP
    assert a.evidence.is_reliable is True


def test_falling_tape_leans_down():
    a = _service().analyze(make_market_data(_FALLING, symbol="FALL"))

    assert a.direction is Direction.DOWN
    assert a.is_reliable is True
    assert a.up_rate is not None and a.up_rate < 0.4
    assert a.mean_forward_return is not None and a.mean_forward_return < 0


def test_mock_data_is_never_reliable():
    a = _service().analyze(make_market_data(_RISING, symbol="MOCKRISE", tier=SourceTier.MOCK))

    # The analogue lean is still computed, but a MOCK series can never be leaned on.
    assert a.direction is Direction.UP
    assert a.is_reliable is False
    assert any("MOCK" in lim for lim in a.limitations)


def test_thin_history_is_unknown_not_fabricated():
    a = _service().analyze(make_market_data([100.0 + i for i in range(45)], symbol="THIN"))

    assert a.direction is Direction.UNKNOWN
    assert a.is_reliable is False
    assert a.up_rate is None
    assert a.mean_forward_return is None
    assert a.evidence is None
    assert any("analogues" in lim for lim in a.limitations)


def test_horizon_override_is_respected():
    a = _service().analyze(make_market_data(_RISING, symbol="RISE"), horizon=10)
    assert a.horizon == 10


def test_is_deterministic():
    md = make_market_data(_RISING, symbol="RISE")
    a = _service().analyze(md).to_dict()
    b = _service().analyze(md).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
