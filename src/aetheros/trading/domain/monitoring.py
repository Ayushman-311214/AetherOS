"""
Monitoring-sweep value object.

A :class:`MonitoringReport` is the result of one bounded "Observe Result ->
Evaluate" pass over the recorded predictions (CLAUDE.md sections 16, 29): the
outstanding predictions resolved against the freshest market data, partitioned
by status, together with the aggregate track record over them. It is the single-
pass primitive a scheduler would call repeatedly -- it is NOT itself a running
background loop, and it still stores nothing beyond what the underlying store
already holds (durable outcome accumulation is the next step).

Every number traces to the per-outcome evaluator and the aggregator it composes;
PENDING/UNRESOLVABLE outcomes are surfaced and a thin or MOCK sample is reported
but never announced as an earned track record (sections 6, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .outcome import PredictionOutcome
from .performance import PredictionPerformance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MonitoringReport:
    """One bounded monitoring sweep: resolved outcomes + their aggregate."""

    swept: int  # predictions pulled and resolved this pass
    resolved: int
    pending: int
    unresolvable: int
    outcomes: tuple[PredictionOutcome, ...]
    performance: PredictionPerformance
    instrument_key: str | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "swept": self.swept,
            "resolved": self.resolved,
            "pending": self.pending,
            "unresolvable": self.unresolvable,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "performance": self.performance.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
