"""
The broker interface (spec Phase 9).

Every broker -- Interactive Brokers, Binance, Bybit, Alpaca, MetaTrader
(future), paper trading -- implements this one interface. The contract is
deliberately narrow and strict:

- :meth:`BrokerProvider.submit` accepts an :class:`ExecutionRequest`, never
  a bare signal or an under-specified order. The §9 path's final gate is
  structural: nothing without instrument, side, quantity, entry, stop, target
  and reason can be submitted at all.
- Market, limit, stop and stop-limit orders are all expressible: the request
  carries the order type and its trigger price(s), and the venue decides when
  the trigger is met. A resting order that has not triggered is reported as
  such -- SUBMITTED, with no fill -- never filled to look busy.
- A broker **must raise** :class:`BrokerError` on failure and **never
  fabricate** a fill. An empty/unusable account state is an honest error, not
  a zero fill.
- :meth:`~BrokerProvider.name`/``tier`` mirror the market-data provider
  convention so provenance can label every executed trade with the venue it
  ran on.

Live venue connectors are deliberately NOT built in this phase: the concrete
implementation here is :class:`~aetheros.trading.brokers.paper_provider
.PaperTradingProvider`, which is real-market-priced paper trading -- virtual
money against live prices, per the spec's paper-trading definition (§10:
paper is REAL MARKET DATA + VIRTUAL MONEY, never fake data). A live broker is
a later phase behind this same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.enums import SourceTier
from ..domain.execution import ExecutionRequest, ExecutionResult


class BrokerProvider(ABC):
    """The common interface every broker implements (spec: "every broker
    implements a common interface")."""

    #: Unique, stable name ("paper", "ibkr", "binance", ...).
    name: str = "unknown"

    #: Provenance tier of this venue: paper trading is MOCK-tier *money* but
    #: its *prices* come from the real market feed the caller supplies.
    tier: SourceTier = SourceTier.MOCK

    @property
    def is_paper(self) -> bool:
        """Whether money here is virtual (never a real venue)."""
        return self.tier is SourceTier.MOCK

    @abstractmethod
    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Submit one fully-specified request.

        Implementations must raise :class:`BrokerError` on transport or venue
        failure -- never return a fabricated fill -- and must reject
        over-limit or under-specified requests with
        ``OrderStatus.REJECTED`` and a reason rather than executing them.
        """

    @abstractmethod
    async def cancel(self, order_id: str) -> ExecutionResult:
        """
        Cancel an open order.

        Cancelling an already-terminal order (filled, cancelled, rejected) is
        an honest no-op with that status reported, never an error.

        :raises BrokerError: when the venue cannot be reached at all.
        """

    @abstractmethod
    async def modify(
        self, order_id: str, request: ExecutionRequest
    ) -> ExecutionResult:
        """
        Replace the terms of a resting order, keeping its identity.

        Only a live (non-terminal) order can be modified. Modifying an order
        that has already filled or been cancelled is an honest no-op that
        reports the terminal status, never a silent re-open.

        :raises BrokerError: when the venue cannot be reached at all.
        """

    @abstractmethod
    async def status(self, order_id: str) -> ExecutionResult:
        """
        The current state of one order.

        An unknown order id is an honest REJECTED-with-reason result (it
        cannot be executing), never a fabricated state.
        """

    @abstractmethod
    async def fill_price(self, instrument_key: str) -> float:
        """
        The current execution price for one instrument.

        Paper brokers read this off the real market-data feed; live brokers
        read it off the venue. A venue without a price for the instrument
        must raise :class:`BrokerError` rather than inventing one.
        """

    @abstractmethod
    async def account_equity(self) -> float:
        """
        The account's current equity at this venue.

        Virtual (paper) or real (live), this is the number the account-level
        risk limits gate on. An unreachable account is a
        :class:`BrokerError`, never a zero.
        """
