"""
The virtual account (spec Phase 14, "virtual account").

This is the "manager later" that :class:`Position` and :class:`Portfolio` were
written for: it opens and closes positions against replayed bars, marks them to
market, and reports where the account stands. Nothing else in the codebase held
positions, which is why :class:`AccountSnapshot`'s own docstring has been
promising one since Phase 9.

**Cash is owned here, and only here.** The paper venue keeps no running ledger
that could disagree with this one: the simulation capitalises it from
:attr:`VirtualAccount.cash` at each order, so the venue's affordability check
asks *this* account's question instead of keeping a second answer. That
matters, because the venue's own balance only ever falls -- it debits a fill
and has no book for a closed round trip -- so a venue holding its own money
would stop trading while the account was still perfectly solvent. A test pins
the round trip instead: what a closed trade returns to cash is its exit
proceeds less the costs of both legs.

Equity is ``cash + the signed market value of open positions`` -- not
``cash + unrealised``, which would forget that a bought position's cost has
already left the cash balance and count the gain twice.
"""

from __future__ import annotations

import math
from datetime import date, datetime

from ..domain.enums import Direction, PositionStatus
from ..domain.instrument import Instrument
from ..domain.risk_limits import AccountSnapshot
from ..domain.simulation import SimulatedTrade, SimulationExitReason
from ..domain.trade import Portfolio, Position

#: The virtual account's reporting currency.
DEFAULT_CURRENCY = "USD"

#: The portfolio id reported for a simulated account.
DEFAULT_PORTFOLIO_ID = "paper-simulation"


def _sign(direction: Direction) -> float:
    """+1 for a long, -1 for a short."""
    return 1.0 if direction is Direction.UP else -1.0


class VirtualAccount:
    """
    A cash balance plus at most one open position, marked to market.

    One position at a time is a deliberate simplification: this phase replays a
    single strategy on a single instrument, and a book that could pyramid would
    need an exit policy the strategies were never tested against. The
    one-at-a-time rule lives in the simulation loop; the account simply models
    what it is given.
    """

    def __init__(
        self,
        instrument: Instrument,
        *,
        initial_balance: float,
        currency: str = DEFAULT_CURRENCY,
        portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    ) -> None:
        if not math.isfinite(initial_balance) or initial_balance <= 0:
            raise ValueError("A virtual account needs a positive starting balance.")
        if not currency.strip() or not portfolio_id.strip():
            raise ValueError("A virtual account needs a currency and portfolio id.")
        self._instrument = instrument
        self._initial_balance = initial_balance
        self._currency = currency
        self._portfolio_id = portfolio_id
        self._cash = initial_balance
        self._position: Position | None = None
        self._entry_bar: int = 0
        self._sequence = 0
        self._closed: list[SimulatedTrade] = []
        self._gross_realized = 0.0
        self._commission_paid = 0.0
        self._open_commissions: dict[str, float] = {}
        self._realized_by_day: dict[date, float] = {}

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def instrument(self) -> Instrument:
        return self._instrument

    @property
    def initial_balance(self) -> float:
        return self._initial_balance

    @property
    def cash(self) -> float:
        """Uninvested cash. Moves only by fills and their costs."""
        return self._cash

    @property
    def position(self) -> Position | None:
        """The open position, or ``None``."""
        return self._position

    @property
    def is_open(self) -> bool:
        return self._position is not None

    @property
    def closed_trades(self) -> tuple[SimulatedTrade, ...]:
        """Every round trip the account has completed, in order."""
        return tuple(self._closed)

    @property
    def realized_pnl(self) -> float:
        """Gross realised P&L over closed trades, before costs."""
        return self._gross_realized

    @property
    def commission_paid(self) -> float:
        """Every commission the account has paid, both legs."""
        return self._commission_paid

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def open(
        self,
        *,
        direction: Direction,
        quantity: float,
        price: float,
        commission: float,
        bar_index: int,
        timestamp: datetime,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> Position:
        """
        Record a fill that opens a position, and move the cash for it.

        A long pays for the position and a short receives for it; both pay the
        commission. This is the only place the account's cash can rise on an
        opening fill, and it rises only for a short -- which is exactly what a
        short is.
        """
        if self._position is not None:
            raise ValueError(
                "This virtual account already holds a position; close it first."
            )
        if not math.isfinite(quantity) or quantity <= 0:
            raise ValueError("A position needs a positive quantity.")
        if not math.isfinite(price) or price <= 0:
            raise ValueError("A position needs a positive fill price.")
        if not math.isfinite(commission) or commission < 0:
            raise ValueError("A commission cannot be negative.")

        notional = quantity * price
        self._cash -= _sign(direction) * notional + commission
        self._commission_paid += commission
        self._sequence += 1
        self._entry_bar = bar_index

        position = Position(
            instrument=self._instrument,
            direction=direction,
            quantity=quantity,
            entry_price=price,
            status=PositionStatus.OPEN,
            position_id=f"sim-{self._instrument.key}-{bar_index}-{self._sequence}",
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=timestamp,
        )
        self._position = position
        self._open_commissions[position.position_id] = commission
        return position

    def close(
        self,
        *,
        price: float,
        reason: SimulationExitReason,
        commission: float,
        bar_index: int,
        timestamp: datetime,
    ) -> SimulatedTrade:
        """
        Record a fill that closes the open position, and return the round trip.

        The gross P&L is the :class:`Position` model's own definition, so the
        account and the domain model can never disagree about what a trade
        made; the costs ride alongside rather than inside it.
        """
        position = self._position
        if position is None:
            raise ValueError("This virtual account holds no position to close.")
        if not math.isfinite(price) or price <= 0:
            raise ValueError("A position needs a positive exit price.")
        if not math.isfinite(commission) or commission < 0:
            raise ValueError("A commission cannot be negative.")
        if bar_index <= self._entry_bar:
            raise ValueError(
                "A position cannot close on or before the bar that opened it."
            )

        notional = position.quantity * price
        self._cash += _sign(position.direction) * notional - commission
        self._commission_paid += commission

        closed = Position(
            instrument=position.instrument,
            direction=position.direction,
            quantity=position.quantity,
            entry_price=position.entry_price,
            status=PositionStatus.CLOSED,
            position_id=position.position_id,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            exit_price=price,
            opened_at=position.opened_at,
            closed_at=timestamp,
        )
        gross = closed.realized_pnl
        assert gross is not None  # CLOSED positions always realise a number
        self._gross_realized += gross

        trade = SimulatedTrade(
            position_id=closed.position_id,
            instrument_key=closed.instrument.key,
            direction=closed.direction,
            quantity=closed.quantity,
            entry_price=closed.entry_price,
            entry_bar=self._entry_bar,
            exit_price=price,
            exit_bar=bar_index,
            reason=reason,
            realized_pnl=gross,
            # Both legs: the commission paid to open was banked when it was
            # paid, so the trade's own cost is its entry and exit fees.
            commission_paid=commission + self._entry_commission(position),
        )
        self._closed.append(trade)
        self._position = None
        day = timestamp.date()
        self._realized_by_day[day] = self._realized_by_day.get(day, 0.0) + trade.net_pnl
        return trade

    def realized_on(self, day: date) -> float:
        """
        Net realised P&L for one simulated calendar day.

        This is the honest measurement of "realised P&L today" that
        :class:`AccountSnapshot` asks for, in simulated time rather than wall
        time -- a replay of last year's bars must measure last year's days, not
        the afternoon the simulation was run.
        """
        return self._realized_by_day.get(day, 0.0)

    def _entry_commission(self, position: Position) -> float:
        """
        The commission already paid to open ``position``.

        Recorded at open time so a trade's costs are complete; the account
        keeps the running total separately for the equity reconciliation.
        """
        return self._open_commissions.pop(position.position_id, 0.0)

    # ------------------------------------------------------------------
    # Marking
    # ------------------------------------------------------------------

    def unrealised_pnl(self, mark: float) -> float:
        """The open position's P&L at ``mark``, or 0.0 when flat."""
        if self._position is None:
            return 0.0
        return (
            (mark - self._position.entry_price)
            * self._position.quantity
            * _sign(self._position.direction)
        )

    def open_exposure(self, mark: float) -> float:
        """The notional the open position controls at ``mark``."""
        if self._position is None:
            return 0.0
        return abs(self._position.quantity * mark)

    def equity(self, mark: float) -> float:
        """
        Cash plus the signed market value of the open position.

        A bought position has already left the cash balance, so its full
        market value -- not merely its gain -- is what the account holds.
        """
        if self._position is None:
            return self._cash
        return self._cash + _sign(self._position.direction) * (
            self._position.quantity * mark
        )

    def portfolio(self, mark: float, *, timestamp: datetime) -> Portfolio:
        """The account as a :class:`Portfolio` snapshot."""
        equity = self.equity(mark)
        if equity < 0 or self._cash < 0:
            raise ValueError(
                "The virtual account is insolvent at this mark; a Portfolio "
                "cannot report a negative balance."
            )
        return Portfolio(
            portfolio_id=self._portfolio_id,
            currency=self._currency,
            cash_balance=self._cash,
            equity=equity,
            positions=(self._position,) if self._position else (),
            updated_at=timestamp,
        )

    def snapshot(
        self,
        mark: float,
        *,
        captured_at: datetime,
        realized_today: float | None = None,
    ) -> AccountSnapshot:
        """
        The account state the risk-limit gate consumes.

        ``realized_today`` is the caller's measurement of the current
        simulated session's realised P&L; passing ``None`` for it is the
        documented unknown that the limit checks fail closed on, so a
        simulation that has not measured it cannot accidentally pass a daily
        loss limit.
        """
        return AccountSnapshot(
            equity=self.equity(mark),
            realised_pnl_today=realized_today,
            open_exposure_notional=self.open_exposure(mark),
            captured_at=captured_at,
        )
