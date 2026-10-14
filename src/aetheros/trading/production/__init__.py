"""Production trading-lifecycle services (spec Phase 2).

These services own the live, stateful side of the §9 path that Phase 1 left
implicit: the position book, the signal lifecycle, kill switches, venue
reconciliation and the aggregate trading-health verdict. They live in their
own package (not ``services/``) because the execution engine sits upstream of
the services package's own ``__init__`` -- importing them from ``services``
would close an import cycle.

Everything here reuses the shared EventBus, the domain value objects and the
existing provider seams; none of it fabricates data, fills or health.
"""

from __future__ import annotations

from .health_service import TradingHealthService
from .kill_switch_service import KillSwitchService
from .lifecycle_service import SignalLifecycleService
from .position_service import PositionBookService
from .reconciliation_service import ReconciliationService

__all__ = [
    "KillSwitchService",
    "PositionBookService",
    "ReconciliationService",
    "SignalLifecycleService",
    "TradingHealthService",
]
