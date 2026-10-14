"""
Paper-trading simulation service (spec Phase 14).

Replays a historical series bar by bar through the *real* pipeline and reports
what happened to a virtual account. Each bar, in order:

1. **Exits first.** Every open position is tested against the bar's range, so
   the book is flat or not before anything new is considered -- the same
   ordering a real session has.
2. **Then signal.** :meth:`SignalService.evaluate_data` runs the panel over the
   past-only slice the feed exposes: strategy → risk geometry → critic → gates.
   Nothing here re-implements that sequence; the service composes layers that
   already exist, exactly as the live path does.
3. **Then size.** A fired signal is sized by :class:`PortfolioRiskService` from
   the account's *current* equity, so the position a strategy would have taken
   is the position the risk engine would have allowed at the time.
4. **Then admit.** The request goes through :meth:`ExecutionEngine.validate`
   against a live :class:`AccountSnapshot` before it goes anywhere -- §9's
   policy and risk approval, not a formality.
5. **Then execute.** A fresh :class:`ExecutionEngine` over a freshly capitalised
   paper venue submits it, and the venue's price source is the replay cursor.
   The venue is the real one and the §9 chain is unbroken; only the price it
   reads and the cash behind it come from the run.

Nothing in this module can reach a live venue: it builds the venue itself, from
a replay-backed price source, and the only order path is
:class:`ExecutionEngine` → that venue. A simulated session therefore cannot
send an order anywhere a live one could.

**The venue is capitalised per order, from the account's own cash.** The paper
venue debits a fill and never credits one -- it records orders, and a closed
round trip is a book it does not keep -- so its running balance only ever
falls. Capitalised once for the whole run it would refuse every entry after
the first few on nothing but bookkeeping, and a simulation of a strategy that
traded would report an empty run. It is therefore built for each order with
the cash the account actually holds at that moment, which is exactly what its
affordability check is for. :class:`VirtualAccount` owns the cash; it is the
only ledger here that survives a round trip.


**No event is published, and that is deliberate.** A replayed fill is not a
state change; it is history being re-read. Publishing ``OrderSubmitted`` for
one would let any live subscriber -- alerting, monitoring, a future execution
path -- react to an order that never happened, which is the fiction §28
forbids. A simulation's only output is the report it returns.

What the report keeps apart: signals the strategy wanted (``signals_fired``),
entries suppressed by the one-position rule (``entries_skipped``), requests the
risk gate refused (``admissions_refused``), orders the venue rejected
(``orders_rejected``), and orders that filled. A run that was mostly refused
must not look like a run that mostly declined to act.
"""

from __future__ import annotations

from collections.abc import Callable

from ...config.settings import Settings
from ...core.logging import get_logger
from ..backtesting.metrics import max_drawdown, sharpe_ratio, trade_statistics
from ..brokers.base import BrokerProvider
from ..brokers.paper_provider import PaperTradingProvider
from ..brokers.price_source import PriceSource
from ..domain.enums import Direction, SourceTier
from ..domain.execution import ExecutionRequest
from ..domain.market_data import MarketData
from ..domain.portfolio import PortfolioCandidate
from ..domain.provenance import Provenance
from ..domain.signal import SignalCandidate
from ..domain.simulation import SimulatedTrade, SimulationExitReason, SimulationReport
from ..errors import InsufficientDataError
from ..execution.engine import ExecutionEngine
from ..risk.limits_service import RiskLimitsService
from ..simulation.account import VirtualAccount
from ..simulation.exit_rules import commission_for, exit_for, slipped_price
from ..simulation.feed import FeedPriceSource, SimulationFeed
from .portfolio_service import PortfolioRiskService
from .signal_service import SignalService
from .strategy_service import DEFAULT_MIN_BARS as MIN_STRATEGY_BARS

logger = get_logger("trading.simulation")

#: Builds a venue bound to a replay cursor and a cash balance.
#:
#: The venue is built per *order*, not per run: its price source is the run's
#: cursor (so it must not be shared) and its balance is the account's cash at
#: that moment (so it must not be stale). The injected default is the real
#: paper venue, so a simulation has no path to anything but virtual money -- a
#: caller may pass a different factory, but it will be asked to fill at a
#: replayed bar, so a live venue is not a useful argument here.
VenueFactory = Callable[[PriceSource, float], BrokerProvider]


#: The fill model, stated in every report. These are not caveats bolted on at
#: the end -- they are what a reader needs to interpret the numbers, and
#: section 7 requires them to be visible rather than implicit.
_FILL_MODEL: tuple[str, ...] = (
    "A signal is decided on the close of bar t and filled at that same close; "
    "no intrabar entry is modelled.",
    "Open positions are tested against each bar's high and low from bar t+1 "
    "onward, so a position cannot be resolved on the bar that opened it.",
    "When one bar's range contains both the stop and the target the position "
    "closes at the stop and is recorded as 'ambiguous' -- the true order of "
    "events inside a bar is unknowable from bar data.",
    "Stops and targets are the signal's own geometry: no trailing stop, no "
    "partial exit and no scaling in.",
    "At most one position is held at a time.",
    "Nothing is opened on the final bar: an entry that could only be resolved "
    "by the series ending is not a trade the series can test.",
)


def _paper_venue(price_source: PriceSource, balance: float) -> BrokerProvider:
    """The default venue: the real paper provider, replaying a series."""
    return PaperTradingProvider(price_source=price_source, initial_balance=balance)


class SimulationService:
    """
    Replays a strategy over a historical series against a virtual account.

    Built from the same services the live path uses, so a simulation can only
    ever be as honest as the pipeline it replays.
    """

    def __init__(
        self,
        signal: SignalService,
        portfolio: PortfolioRiskService,
        risk_limits: RiskLimitsService,
        settings: Settings,
        *,
        venue_factory: VenueFactory | None = None,
    ) -> None:
        self._signal = signal
        self._portfolio = portfolio
        self._risk_limits = risk_limits
        self._settings = settings
        self._venue_factory: VenueFactory = venue_factory or _paper_venue

    # ------------------------------------------------------------------

    async def run(
        self,
        data: MarketData,
        strategy_id: str,
        *,
        warmup: int | None = None,
        initial_balance: float | None = None,
        commission_bps: float | None = None,
        slippage_bps: float | None = None,
    ) -> SimulationReport:
        """
        Replay ``data`` with ``strategy_id`` and return what happened.

        ``warmup`` bars are skipped before anything is decided: a strategy
        evaluated on a dozen bars is not being tested, it is being asked to
        guess. It defaults to the strategy layer's own minimum window rather
        than to a number invented here.
        """
        settings = self._settings
        bars = len(data.candles)
        if warmup is not None and (warmup < 0 or warmup >= bars):
            # An explicit warmup the series cannot hold is a caller bug, and a
            # clamp would hide it by silently evaluating somewhere else.
            raise ValueError(
                f"A simulation needs a warmup inside the series: got {warmup} "
                f"for {bars} bar(s)."
            )
        # A series with nothing left after the warmup is too short to decide
        # anything on. That is reported as an empty run with a limitation --
        # the §28 "not enough evidence" answer -- rather than raised, because
        # a thin series is a fact about the data, not a defect in the call.
        too_short = warmup is None and bars <= MIN_STRATEGY_BARS
        start = (
            bars
            if too_short
            else (MIN_STRATEGY_BARS if warmup is None else warmup)
        )
        balance = (
            settings.TRADING_SIM_INITIAL_BALANCE
            if initial_balance is None
            else initial_balance
        )
        commission_bps = (
            settings.TRADING_SIM_COMMISSION_BPS
            if commission_bps is None
            else commission_bps
        )
        slippage_bps = (
            settings.TRADING_SIM_SLIPPAGE_BPS
            if slippage_bps is None
            else slippage_bps
        )
        if commission_bps < 0 or slippage_bps < 0:
            raise ValueError("Simulated costs cannot be negative.")

        feed = SimulationFeed(data)
        if not too_short:
            feed.seek(start)
        account = VirtualAccount(data.instrument, initial_balance=balance)
        # One price source for the whole run -- it reads the cursor, and the
        # cursor is the run. The venue wrapped around it is rebuilt per order
        # (see _engine_for): a replayed fill must not reach a live subscriber as
        # a real one, so no engine here is ever given an event bus.
        source = FeedPriceSource(feed)

        equity_curve: list[float] = []
        signals_fired = 0
        orders_filled = 0
        orders_rejected = 0
        admissions_refused = 0
        entries_skipped = 0
        exit_counts: dict[SimulationExitReason, int] = {}

        while not too_short:
            candle = feed.bar()
            timestamp = candle.timestamp
            mark = feed.price()

            resolved = self._close_open_position(
                account,
                feed,
                commission_bps=commission_bps,
                slippage_bps=slippage_bps,
            )
            if resolved is not None:
                exit_counts[resolved.reason] = exit_counts.get(resolved.reason, 0) + 1

            candidates = await self._fired_candidates(feed, strategy_id, account, mark)
            signals_fired += len(candidates)

            for candidate in candidates:
                if feed.exhausted:
                    # A position opened on the final bar could only ever be
                    # force-closed on that same bar -- an entry the series
                    # cannot test, with a guaranteed synthetic exit. Counting
                    # it as skipped is the honest treatment.
                    entries_skipped += 1
                    continue
                if account.is_open:
                    entries_skipped += 1
                    continue
                request = self._request_for(candidate, account, mark)
                if request is None:
                    entries_skipped += 1
                    continue
                engine = self._engine_for(source, account, settings)
                if engine is None:
                    # No cash left to capitalise a venue with, so there is no
                    # order to place. Counted as a refusal rather than
                    # attempted: placing it would mean inventing money.
                    admissions_refused += 1
                    continue

                snapshot = account.snapshot(
                    mark,
                    captured_at=timestamp,
                    realized_today=account.realized_on(timestamp.date()),
                )
                verdict = await engine.validate(request, account_snapshot=snapshot)
                if not verdict.ok:
                    admissions_refused += 1
                    continue

                result = await engine.submit(request, validate=False)
                if not result.filled or result.average_fill_price is None:
                    orders_rejected += 1
                    continue

                fill_price = slipped_price(
                    result.average_fill_price,
                    buying=request.direction is Direction.UP,
                    slippage_bps=slippage_bps,
                )
                account.open(
                    direction=request.direction,
                    quantity=result.filled_quantity,
                    price=fill_price,
                    commission=commission_for(
                        result.filled_quantity * fill_price,
                        commission_bps=commission_bps,
                    ),
                    bar_index=feed.cursor,
                    timestamp=timestamp,
                    stop_loss=request.stop_loss,
                    take_profit=request.take_profit,
                )
                orders_filled += 1

            equity_curve.append(account.equity(mark))

            if feed.exhausted:
                break
            feed.advance()

        # A series that ends with the book open closes it at the last close and
        # says so, rather than presenting an unrealised position as a result.
        forced = self._force_close(
            account,
            feed,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        if forced is not None:
            exit_counts[SimulationExitReason.FORCED_END] = (
                exit_counts.get(SimulationExitReason.FORCED_END, 0) + 1
            )

        final_mark = feed.price()
        trades = account.closed_trades
        returns = [trade.return_pct for trade in trades]
        is_reliable, limitations = self._gate(
            data,
            trades=trades,
            forced=forced is not None,
            too_short=too_short,
            signals_fired=signals_fired,
            admissions_refused=admissions_refused,
            orders_rejected=orders_rejected,
            entries_skipped=entries_skipped,
        )

        return SimulationReport(
            instrument=data.instrument,
            timeframe=data.timeframe.value,
            strategy_id=strategy_id,
            bars=bars,
            warmup=start,
            initial_equity=balance,
            final_equity=account.equity(final_mark),
            realized_pnl=round(account.realized_pnl, 8),
            unrealised_pnl=round(account.unrealised_pnl(final_mark), 8),
            commission_paid=round(account.commission_paid, 8),
            max_drawdown=max_drawdown(returns) if returns else 0.0,
            sharpe=sharpe_ratio(returns),
            statistics=trade_statistics(returns) if returns else None,
            trades=trades,
            equity_curve=tuple(equity_curve),
            signals_fired=signals_fired,
            orders_filled=orders_filled,
            orders_rejected=orders_rejected,
            admissions_refused=admissions_refused,
            entries_skipped=entries_skipped,
            exit_counts=tuple(
                (reason.value, exit_counts[reason])
                for reason in SimulationExitReason
                if reason in exit_counts
            ),
            assumptions=_FILL_MODEL
            + self._cost_assumptions(commission_bps, slippage_bps),
            provenance=self._provenance(data),
            quality=data.quality,
            is_reliable=is_reliable,
            limitations=limitations,
        )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    async def _fired_candidates(
        self,
        feed: SimulationFeed,
        strategy_id: str,
        account: VirtualAccount,
        mark: float,
    ) -> tuple[SignalCandidate, ...]:
        """
        The signals this bar's context produced, or none if it could not be read.

        A window too short for the strategy layer is an expected absence during
        warmup, not a failure: the bar is skipped and the run continues.
        """
        try:
            evaluation = await self._signal.evaluate_data(
                feed.visible(),
                account_equity=account.equity(mark),
                strategy_ids=[strategy_id],
            )
        except InsufficientDataError:
            return ()
        return tuple(c for c in evaluation.candidates if c.signal is not None)

    def _request_for(
        self,
        candidate: SignalCandidate,
        account: VirtualAccount,
        mark: float,
    ) -> ExecutionRequest | None:
        """
        The executable request for one fired candidate, or ``None``.

        ``None`` is the honest "this could not become a trade": a candidate
        that kept no setup, or that has no stop to size against, or whose risk
        budget cannot buy one whole share at that stop distance. The caller
        counts it rather than rounding it up into a trade the account never
        made.
        """
        setup = candidate.setup
        signal = candidate.signal
        stop = candidate.risk.stop_loss
        if setup is None or signal is None or stop is None:
            return None

        plan = self._portfolio.allocate(
            [
                PortfolioCandidate(
                    instrument_key=candidate.risk.instrument.key,
                    direction=candidate.risk.direction,
                    entry=candidate.risk.entry,
                    stop=stop,
                    risk_per_share=abs(candidate.risk.entry - stop),
                )
            ],
            account_equity=account.equity(mark),
        )
        sized = [p for p in plan.positions if p.included and p.shares > 0]
        if not sized:
            return None
        return ExecutionRequest.from_signal(
            signal, candidate.risk, setup, quantity=sized[0].shares
        )

    def _engine_for(
        self,
        source: PriceSource,
        account: VirtualAccount,
        settings: Settings,
    ) -> ExecutionEngine | None:
        """
        An execution engine over a venue capitalised with the account's cash.

        The venue is rebuilt per order because its balance would otherwise be a
        ledger that only falls: the paper venue debits a fill and never credits
        one, so a venue capitalised once would refuse every entry after the
        first few for no reason but its own bookkeeping. Capitalising it from
        :attr:`VirtualAccount.cash` makes the affordability check mean what it
        says -- can this account pay for this order right now -- because the
        account is the book that a closed round trip actually returns to.

        ``None`` when the account has no cash to capitalise with. A venue needs
        a positive balance, and there is no honest way to build one from no
        money: the caller records the refusal.

        No event bus is passed. A replayed fill is history being re-read, not a
        state change, and publishing ``OrderSubmitted`` for one would let a
        live subscriber react to an order that never happened.
        """
        if account.cash <= 0:
            return None
        venue = self._venue_factory(source, account.cash)
        return ExecutionEngine(venue, self._risk_limits, settings)

    def _close_open_position(
        self,
        account: VirtualAccount,
        feed: SimulationFeed,
        *,
        commission_bps: float,
        slippage_bps: float,
    ) -> SimulatedTrade | None:
        """Close the open position if this bar's range resolved it."""
        position = account.position
        if position is None:
            return None
        decision = exit_for(position, feed.bar())
        if decision is None:
            return None
        level, reason = decision
        return self._record_close(
            account,
            feed,
            level=level,
            reason=reason,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )

    def _force_close(
        self,
        account: VirtualAccount,
        feed: SimulationFeed,
        *,
        commission_bps: float,
        slippage_bps: float,
    ) -> SimulatedTrade | None:
        """Close whatever is still open at the final bar's close."""
        if not account.is_open:
            return None
        return self._record_close(
            account,
            feed,
            level=feed.price(),
            reason=SimulationExitReason.FORCED_END,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )

    def _record_close(
        self,
        account: VirtualAccount,
        feed: SimulationFeed,
        *,
        level: float,
        reason: SimulationExitReason,
        commission_bps: float,
        slippage_bps: float,
    ) -> SimulatedTrade:
        """Apply adverse slippage and commission to a close, then bank it."""
        position = account.position
        if position is None:
            raise ValueError("No position is open to close.")
        exit_price = slipped_price(
            level,
            buying=position.direction is Direction.DOWN,
            slippage_bps=slippage_bps,
        )
        return account.close(
            price=exit_price,
            reason=reason,
            commission=commission_for(
                position.quantity * exit_price, commission_bps=commission_bps
            ),
            bar_index=feed.cursor,
            timestamp=feed.bar().timestamp,
        )

    # ------------------------------------------------------------------

    def _gate(
        self,
        data: MarketData,
        *,
        trades: tuple[SimulatedTrade, ...],
        forced: bool,
        too_short: bool,
        signals_fired: int,
        admissions_refused: int,
        orders_rejected: int,
        entries_skipped: int,
    ) -> tuple[bool, tuple[str, ...]]:
        """
        Whether the run is evidence, and what disqualified it if not.

        Mirrors the walk-forward report's gate: a simulation is evidence about
        the *engine* until the sample is real, clean and thick enough to be
        evidence about an edge. A reliable run carries no limitations, and the
        report model enforces that rather than trusting this method to.
        """
        limitations: list[str] = []

        if too_short:
            return False, (
                f"The series holds {len(data.candles)} bar(s) and the strategy "
                f"layer needs {MIN_STRATEGY_BARS} bars before it will read "
                "anything, so no bar was evaluated: this run produced no result "
                "at all, only an insufficient sample."
            ,)

        if data.provenance.is_mock:
            limitations.append(
                "The series is synthetic (MOCK): the run exercises the "
                "simulation engine, not a real market edge."
            )
        if not data.quality.usable:
            limitations.append(
                f"Data quality is '{data.quality.status.value}': the series is "
                "not fit to draw a conclusion from."
            )

        minimum = self._settings.TRADING_SIM_MIN_TRADES
        if len(trades) < minimum:
            limitations.append(
                f"Only {len(trades)} closed trade(s) (< {minimum}); a sample "
                "this thin cannot distinguish a strategy from chance."
            )
        if not trades:
            limitations.append(
                "No trade was taken over the replayed series "
                f"({signals_fired} signal(s) fired, {admissions_refused} "
                f"refused by the risk gate, {orders_rejected} rejected by the "
                f"venue, {entries_skipped} suppressed by the one-position "
                "rule). This is a result, not a failure."
            )
        if forced:
            limitations.append(
                "The series ended with a position open, so it was closed at the "
                "final bar's close: that exit is the data ending, not a rule "
                "firing, and its P&L is not a decision the strategy made."
            )

        return (not limitations), tuple(limitations)

    @staticmethod
    def _cost_assumptions(
        commission_bps: float, slippage_bps: float
    ) -> tuple[str, ...]:
        """Name the cost model in force -- including when it is free."""
        commission = (
            f"Commission is {commission_bps:g} bps of notional per leg"
        )
        if commission_bps == 0:
            commission += " (zero: no trading cost is modelled)."
        slippage = f"Slippage is {slippage_bps:g} bps against the order per fill"
        if slippage_bps == 0:
            slippage += " (zero: every fill is at the ideal price)."
        return (commission, slippage)

    @staticmethod
    def _provenance(data: MarketData) -> Provenance:
        # ``retrieved_at`` is taken from the replayed series, not the wall clock:
        # a simulation reruns *that* data, so stamping the fetch time again would
        # both misreport when the underlying candles were actually retrieved and
        # make two identical runs differ by nothing but the clock. Carrying the
        # source's own timestamp keeps the report reproducible (§7).
        return Provenance(
            source=data.provenance.source,
            tier=SourceTier.MOCK if data.provenance.is_mock else SourceTier.DERIVED,
            retrieved_at=data.retrieved_at,
            detail="paper-trading simulation over a replayed series",
        )
