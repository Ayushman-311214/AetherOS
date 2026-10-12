"""
The execution package (spec Phase 9).

:class:`ExecutionEngine` is the validate → submit → retry path to a broker.
Its only accepted input is a fully populated
:class:`~aetheros.trading.domain.execution.ExecutionRequest` -- built from a
fired :class:`~aetheros.trading.domain.trade.TradeSignal` via
``ExecutionRequest.from_signal`` -- so no LLM output and no under-specified
order can ever reach a venue through this module (§9: LLM/Strategy →
Decision → Policy → Risk → **Execution Validation** → Broker).
"""

from __future__ import annotations

from .engine import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    ExecutionEngine,
    ValidationReport,
)

__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "ExecutionEngine",
    "ValidationReport",
]
