"""
Trading-CEO brief value object.

A :class:`CEOBrief` is the natural-language layer the spec's Trading CEO sits on
top of the deterministic core to produce (CLAUDE.md sections 4, 5, 10): a plain
narration of a finished :class:`TradingReport`. The narration is *grounded* -- it
restates the deterministic report, it does not compute. The report dict is
embedded verbatim as the single source of truth, so every number the brief
mentions is auditable against it, and the LLM is never the source of a price,
probability or signal (sections 2, 3, 10, 28).

``narrated_by`` records who wrote the prose: a provider/model id when an LLM was
used, or ``"deterministic-fallback"`` when none was wired or the call failed --
in which case the brief is a templated summary of the report, never a fabricated
one. Either way the recommendation, direction and actionability are copied
straight off the deterministic report, not from the narration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CEOBrief:
    """A grounded natural-language narration of a deterministic trading report."""

    instrument_key: str
    timeframe: str
    recommendation: str
    direction: str
    is_actionable: bool
    narrative: str
    narrated_by: str  # "<provider>:<model>" or "deterministic-fallback"
    report: dict[str, Any]  # the full deterministic report, source of truth
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "recommendation": self.recommendation,
            "direction": self.direction,
            "is_actionable": self.is_actionable,
            "narrative": self.narrative,
            "narrated_by": self.narrated_by,
            "report": self.report,
            "created_at": self.created_at.isoformat(),
        }
