"""
RelativeStrengthService: deterministic instrument-vs-benchmark strength.

These tests are fully deterministic and never touch the network: they hand the
service crafted ``MarketData`` (the RegimeService pattern -- the service takes
two return series and does no I/O), so the "positive sector strength" read the
spec's example reports cite (CLAUDE.md sections 2, 5, 27) is pinned against known
inputs. They assert the things that matter under the honesty rules (sections 9,
15, 28): a clear outperformer is UP and a laggard is DOWN, a matching series is
SIDEWAYS, the read is a non-mock ``MARKET_CONTEXT`` evidence item when reliable,
and MOCK / unusable / too-thin data on *either* series yields an UNKNOWN,
never-reliable read with no fabricated numbers -- deterministically.
"""

from __future__ import annotations

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.services.relative_strength_service import (
    RelativeStrengthService,
)

from .conftest import make_market_data

# Strongly rising vs mildly rising close series (>= 80 bars so the default
# 60-bar window is fully covered).
_STRONG = [100.0 + i for i in range(80)]
_MILD = [100.0 + i * 0.1 for i in range(80)]


def _service() -> RelativeStrengthService:
    return RelativeStrengthService(get_settings())


def test_clear_outperformer_is_up_and_reliable():
    inst = make_market_data(_STRONG, symbol="LEAD")
    bench = make_market_data(_MILD, symbol="SPY")
    rs = _service().analyze(inst, bench)

    assert rs.direction is Direction.UP
    assert rs.is_reliable is True
    assert rs.benchmark_key == "SPY"
    assert rs.relative_return is not None and rs.relative_return > 0
    # The read is exposed as a non-mock, calculated MARKET_CONTEXT evidence item.
    assert rs.evidence is not None
    assert rs.evidence.type is EvidenceType.MARKET_CONTEXT
    assert rs.evidence.assertion is Assertion.CALCULATED
    assert rs.evidence.direction is Direction.UP
    assert rs.evidence.is_reliable is True


def test_clear_laggard_is_down():
    inst = make_market_data(_MILD, symbol="LAG")
    bench = make_market_data(_STRONG, symbol="SPY")
    rs = _service().analyze(inst, bench)

    assert rs.direction is Direction.DOWN
    assert rs.is_reliable is True
    assert rs.relative_return is not None and rs.relative_return < 0


def test_matching_series_is_sideways_and_reliable():
    # Identical performance -> zero excess -> in-line, a determinate reliable read.
    inst = make_market_data(_STRONG, symbol="TWIN")
    bench = make_market_data(list(_STRONG), symbol="SPY")
    rs = _service().analyze(inst, bench)

    assert rs.direction is Direction.SIDEWAYS
    assert rs.is_reliable is True
    assert rs.relative_return == 0.0


def test_mock_instrument_is_never_reliable():
    inst = make_market_data(_STRONG, symbol="MOCKLEAD", tier=SourceTier.MOCK)
    bench = make_market_data(_MILD, symbol="SPY")
    rs = _service().analyze(inst, bench)

    # The lean is still computed, but a MOCK series can never be leaned on.
    assert rs.direction is Direction.UP
    assert rs.is_reliable is False
    assert any("MOCK" in lim for lim in rs.limitations)


def test_mock_benchmark_makes_a_real_instrument_unreliable():
    inst = make_market_data(_STRONG, symbol="REAL")
    bench = make_market_data(_MILD, symbol="MOCKSPY", tier=SourceTier.MOCK)
    rs = _service().analyze(inst, bench)

    assert rs.provenance.tier is SourceTier.PRIMARY
    assert rs.is_reliable is False  # a mock benchmark poisons the comparison
    assert any("MOCK" in lim for lim in rs.limitations)


def test_thin_data_is_unknown_not_fabricated():
    inst = make_market_data([100.0 + i for i in range(10)], symbol="THIN")
    bench = make_market_data(_MILD, symbol="SPY")
    rs = _service().analyze(inst, bench)

    assert rs.direction is Direction.UNKNOWN
    assert rs.is_reliable is False
    assert rs.relative_return is None
    assert rs.evidence is None
    assert any("aligned candles" in lim for lim in rs.limitations)


def test_window_aligns_to_the_shorter_series():
    # A 25-bar benchmark caps the window even though the instrument has 80 bars.
    inst = make_market_data(_STRONG, symbol="LONG")
    bench = make_market_data(_MILD[:25], symbol="SPY")
    rs = _service().analyze(inst, bench)
    assert rs.lookback == 25


def test_lookback_override_is_respected():
    inst = make_market_data(_STRONG, symbol="LEAD")
    bench = make_market_data(_MILD, symbol="SPY")
    rs = _service().analyze(inst, bench, lookback=30)
    assert rs.lookback == 30


def test_is_deterministic():
    inst = make_market_data(_STRONG, symbol="LEAD")
    bench = make_market_data(_MILD, symbol="SPY")
    a = _service().analyze(inst, bench).to_dict()
    b = _service().analyze(inst, bench).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
