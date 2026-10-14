"""
Position book service (spec Phase 2 -- live account state).

The book is the single source of truth for what the account actually holds:
open positions, realised PnL and the exposure the risk gate consumes. These
tests pin its honest arithmetic:

- a fill opens a position; an opposite fill closes it and banks realised P&L;
- a same-side fill averages up the open leg rather than duplicating it;
- ``snapshot()`` reports equity, exposure and today's PnL the book can see --
  never a fabricated balance.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, PositionStatus
from aetheros.trading.domain.execution import ExecutionRequest
from aetheros.trading.production import PositionBookService

from .test_critic import _risk
from .test_execution import _request
from .test_signal_domain import _setup, _signal


def _buy(quantity: float = 10.0) -> ExecutionRequest:
    return _request(Direction.UP, quantity=quantity)


def _sell(quantity: float = 10.0) -> ExecutionRequest:
    return _request(Direction.DOWN, quantity=quantity)


def test_a_fill_opens_a_position():
    book = PositionBookService()
    touched = book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    assert len(book.open_positions()) == 1
    position = book.open_positions()[0]
    assert position.direction is Direction.UP
    assert position.quantity == 5.0
    assert position.entry_price == 100.0
    assert position.status is PositionStatus.OPEN
    assert touched and touched[0] is position


def test_an_opposite_fill_closes_the_position_and_banks_pnl():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    book.record_fill(_sell(5.0), fill_price=110.0, fill_quantity=5.0)
    assert book.open_positions() == ()
    assert book.lifetime_pnl() == pytest.approx(50.0)


def test_a_losing_close_banks_a_negative_pnl():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    book.record_fill(_sell(5.0), fill_price=95.0, fill_quantity=5.0)
    assert book.lifetime_pnl() == pytest.approx(-25.0)


def test_a_partial_close_keeps_the_remainder_open():
    book = PositionBookService()
    book.record_fill(_buy(10.0), fill_price=100.0, fill_quantity=10.0)
    book.record_fill(_sell(4.0), fill_price=110.0, fill_quantity=4.0)
    remaining = book.open_positions()
    assert len(remaining) == 1
    assert remaining[0].quantity == pytest.approx(6.0)
    assert book.lifetime_pnl() == pytest.approx(40.0)


def test_an_oversized_opposite_fill_closes_and_opens_the_reverse():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    # Selling 8 against a long of 5 closes the long and opens a short of 3.
    book.record_fill(_sell(8.0), fill_price=110.0, fill_quantity=8.0)
    open_now = book.open_positions()
    assert len(open_now) == 1
    assert open_now[0].direction is Direction.DOWN
    assert open_now[0].quantity == pytest.approx(3.0)
    assert book.lifetime_pnl() == pytest.approx(50.0)


def test_a_same_side_fill_averages_the_open_leg():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    book.record_fill(_buy(5.0), fill_price=120.0, fill_quantity=5.0)
    open_now = book.open_positions()
    assert len(open_now) == 1
    assert open_now[0].quantity == pytest.approx(10.0)
    assert open_now[0].entry_price == pytest.approx(110.0)


def test_open_exposure_is_the_gross_notional():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    assert book.open_exposure() == pytest.approx(500.0)


def test_snapshot_reports_exposure_and_pnl_honestly():
    book = PositionBookService()
    book.record_cash(10_000.0)
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    snap = book.snapshot()
    assert snap.open_exposure_notional == pytest.approx(500.0)
    assert snap.realised_pnl_today == pytest.approx(0.0)
    assert snap.equity > 0


def test_snapshot_includes_realised_pnl_today_after_a_close():
    book = PositionBookService()
    book.record_fill(_buy(5.0), fill_price=100.0, fill_quantity=5.0)
    book.record_fill(_sell(5.0), fill_price=110.0, fill_quantity=5.0)
    snap = book.snapshot()
    assert snap.realised_pnl_today == pytest.approx(50.0)
