"""
Paper trading / simulation (spec Phase 14).

Provides a virtual account, a replayed market, strategy testing over a real
historical series, and no financial risk.

The package holds the pure pieces -- the replay cursor, the exit rules, the
account book -- and leaves orchestration to
:class:`~aetheros.trading.services.simulation_service.SimulationService`. That
split is the one the rest of the trading core uses (``quant/``, ``news/``,
``ict/``, ``backtesting/`` beside a ``services/<concept>_service.py``), and it
is what keeps the exit rules testable in isolation from the services they run
inside.

**This is not a shortcut around the §9 path.** A simulated session reaches a
venue by exactly the route a live one would -- signal → risk → critic → gates →
:class:`ExecutionRequest` → :class:`ExecutionEngine` → broker -- and the venue
is the real :class:`PaperTradingProvider`. The only thing that changes is where
that venue reads its price: :class:`FeedPriceSource` replays the bar under the
cursor instead of the live tape. Fake money against real market data, replayed
bar by bar -- never fake market data (spec §10).
"""

from __future__ import annotations

from .account import DEFAULT_CURRENCY, DEFAULT_PORTFOLIO_ID, VirtualAccount
from .exit_rules import commission_for, exit_for, slipped_price
from .feed import FeedPriceSource, SimulationFeed

__all__ = [
    "DEFAULT_CURRENCY",
    "DEFAULT_PORTFOLIO_ID",
    "FeedPriceSource",
    "SimulationFeed",
    "VirtualAccount",
    "commission_for",
    "exit_for",
    "slipped_price",
]
