"""
Journal analytics: performance measured from actual journal entries (Phase 22).

The service describes a book; it never trades it. Every number is read off the
entries a paper trade already produced, and the honesty rules are the point of
the tests: open trades carry no result, planned R:R is reported apart from
realised P/L, and a thin or mock book is flagged, not dressed up.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.analytics import JournalAnalyticsService
from aetheros.trading.domain.enums import Direction
from aetheros.trading.domain.journal import JournalEntry
from aetheros.trading.domain.provenance import Provenance, SourceTier
from aetheros.trading.domain.simulation import SimulatedTrade, SimulationExitReason


def _service() -> JournalAnalyticsService:
    return JournalAnalyticsService(get_settings())


def _trade(**overrides) -> SimulatedTrade:
    fields: dict = {
        "position_id": "sim-TEST-10-1",
        "instrument_key": "TEST",
        "direction": Direction.UP,
        "quantity": 10.0,
        "entry_price": 100.0,
        "entry_bar": 10,
        "exit_price": 105.0,
        "exit_bar": 15,
        "reason": SimulationExitReason.TARGET,
        "realized_pnl": 50.0,
        "commission_paid": 1.0,
    }
    fields.update(overrides)
    return SimulatedTrade(**fields)


def _closed(
    *,
    strategy: str = "trend_following",
    symbol: str = "TEST",
    timeframe: str = "1d",
    net: float = 49.0,
    is_mock: bool = False,
) -> JournalEntry:
    """A closed entry with a chosen net P/L, built via from_trade."""
    # Pick exit so (exit - entry) * qty - commission == net.
    commission = 1.0
    exit_price = 100.0 + (net + commission) / 10.0
    trade = _trade(
        instrument_key=symbol,
        exit_price=exit_price,
        realized_pnl=(exit_price - 100.0) * 10.0,
        commission_paid=commission,
    )
    return JournalEntry.from_trade(
        trade,
        strategy_id=strategy,
        timeframe=timeframe,
        is_mock=is_mock,
        provenance=Provenance(source="test", tier=SourceTier.DERIVED),
    )


def _open_with_rr(rr: float = 3.0) -> JournalEntry:
    """An open entry carrying a planned risk/reward but no outcome."""
    from tests.trading.test_execution import _request

    request = _request()
    assert request.risk_reward_ratio is not None
    # Override the planned ratio deterministically.
    import dataclasses

    request = dataclasses.replace(request, risk_reward_ratio=rr)
    return JournalEntry.from_request(request, entry_bar=10, timeframe="1d")


# ==============================================================
# Empty / thin / mock honesty
# ==============================================================


def test_empty_book_is_a_valid_unreliable_summary() -> None:
    report = _service().summarize([])
    assert report.trades == 0
    assert report.closed_trades == 0
    assert report.statistics is None
    assert report.is_reliable is False
    assert report.monthly_return == ()
    assert report.breakdowns == ()


def test_thin_book_is_reported_but_not_reliable() -> None:
    report = _service().summarize([_closed(net=10.0), _closed(net=-5.0)])
    assert report.closed_trades == 2
    assert report.statistics is not None
    assert report.statistics.trades == 2
    assert report.is_reliable is False
    assert any("closed trade" in lim for lim in report.limitations)


def test_mock_entries_make_the_book_unreliable() -> None:
    entries = [_closed(net=10.0, is_mock=True)]
    report = _service().summarize(entries)
    assert report.mock_trades == 1
    assert report.is_reliable is False
    assert any("mock data" in lim for lim in report.limitations)


# ==============================================================
# Core metrics from real closed trades
# ==============================================================


def test_win_rate_and_statistics_come_from_net_pnl() -> None:
    entries = [_closed(net=20.0), _closed(net=30.0), _closed(net=-10.0)]
    report = _service().summarize(entries)
    stats = report.statistics
    assert stats is not None
    assert stats.trades == 3
    assert stats.wins == 2
    assert stats.losses == 1
    assert stats.win_rate == pytest.approx(2 / 3, abs=1e-4)
    # Expectancy is the mean signed net return.
    assert stats.expectancy == pytest.approx((20.0 + 30.0 - 10.0) / 3, abs=1e-3)


def test_open_trades_never_enter_pnl_metrics() -> None:
    entries = [_closed(net=20.0), _open_with_rr(3.0)]
    report = _service().summarize(entries)
    assert report.trades == 2
    assert report.closed_trades == 1
    assert report.open_trades == 1
    # Only the one closed trade is graded.
    assert report.statistics is not None
    assert report.statistics.trades == 1
    assert any("open entr" in lim for lim in report.limitations)


# ==============================================================
# Planned R:R reported apart from realised P/L
# ==============================================================


def test_average_rr_uses_planned_geometry_only() -> None:
    # Two open entries carry planned R:R; the closed from_trade entry does not.
    entries = [_open_with_rr(2.0), _open_with_rr(4.0), _closed(net=10.0)]
    report = _service().summarize(entries)
    assert report.average_rr == pytest.approx(3.0)
    assert report.average_rr_sample == 2
    assert any("no planned risk/reward" in lim for lim in report.limitations)


def test_average_rr_is_none_when_nothing_carried_a_plan() -> None:
    report = _service().summarize([_closed(net=10.0), _closed(net=-5.0)])
    assert report.average_rr is None
    assert report.average_rr_sample == 0


# ==============================================================
# Breakdowns + monthly return
# ==============================================================


def test_breakdowns_slice_by_strategy_symbol_and_timeframe() -> None:
    entries = [
        _closed(strategy="trend_following", symbol="AAA", net=10.0),
        _closed(strategy="trend_following", symbol="BBB", net=-5.0),
        _closed(strategy="mean_reversion", symbol="AAA", net=20.0),
    ]
    report = _service().summarize(entries)
    dims = {b.dimension for b in report.breakdowns}
    assert dims == {"strategy", "symbol", "timeframe"}

    by_strategy = {
        b.key: b for b in report.breakdowns if b.dimension == "strategy"
    }
    assert by_strategy["trend_following"].trades == 2
    assert by_strategy["mean_reversion"].trades == 1
    assert by_strategy["mean_reversion"].net_pnl == pytest.approx(20.0)

    by_symbol = {b.key: b for b in report.breakdowns if b.dimension == "symbol"}
    assert by_symbol["AAA"].trades == 2
    assert by_symbol["AAA"].wins == 2


def test_monthly_return_buckets_net_pnl_by_recorded_month() -> None:
    report = _service().summarize([_closed(net=10.0), _closed(net=5.0)])
    assert len(report.monthly_return) == 1
    _, pnl = report.monthly_return[0]
    assert pnl == pytest.approx(15.0)


def test_to_dict_is_json_shaped() -> None:
    report = _service().summarize([_closed(net=10.0), _open_with_rr(3.0)])
    payload = report.to_dict()
    assert payload["trades"] == 2
    assert payload["closed_trades"] == 1
    assert payload["open_trades"] == 1
    assert isinstance(payload["monthly_return"], list)
    assert isinstance(payload["breakdowns"], list)
    assert payload["is_reliable"] is False
    assert isinstance(payload["limitations"], list)
