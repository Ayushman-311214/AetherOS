"""
Reconciliation value objects (spec Phase 2 -- broker reconciliation).

Production trading must be able to answer: *does what the venue shows match
what the engine believes it sent?* Phase 1 never asked the question -- the
engine submitted, the venue filled, and nothing compared the two ledgers. A
lost fill, a duplicated order, a quantity the venue recorded differently, or a
position the book thinks is open but the venue never saw would all pass
silently.

These models are the result of asking it. A :class:`ReconciliationReport` is
the honest verdict of one diff: clean only when every leg agreed. Each
:class:`ReconciliationMismatch` names the *kind* of divergence, the leg it
concerns, and the two values that disagreed -- so an auditor reads exactly
what drifted rather than a bare "mismatch" flag.

The service never fabricates agreement: a leg it cannot account for is a
mismatch, not a pass. ``is_clean`` is derived, never set -- a report with any
mismatch is not clean by construction, so a caller cannot assert a clean book
over a drifting one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MismatchKind(str, Enum):
    """The category of divergence one reconciliation leg found."""

    MISSING_LOCAL = "missing_local"  # venue has it; local never recorded it
    MISSING_VENUE = "missing_venue"  # local sent it; the venue does not show it
    QUANTITY_MISMATCH = "quantity_mismatch"  # both show it, different quantity
    STATUS_MISMATCH = "status_mismatch"  # both show it, different state
    POSITION_MISMATCH = "position_mismatch"  # open-position divergence
    BALANCE_MISMATCH = "balance_mismatch"  # cash/equity divergence
    UNEXPECTED_FILL = "unexpected_fill"  # a fill neither side expected


@dataclass(frozen=True, slots=True)
class ReconciliationMismatch:
    """One leg where local intent and venue reality diverged."""

    kind: MismatchKind
    detail: str
    order_id: str = ""
    position_id: str = ""
    local_value: str = ""
    venue_value: str = ""

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ValueError("A reconciliation mismatch must describe itself.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "detail": self.detail,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "local_value": self.local_value,
            "venue_value": self.venue_value,
        }


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """
    The verdict of one local-vs-venue diff.

    ``checked`` counts the legs compared; ``mismatches`` lists every leg that
    disagreed. ``is_clean`` is the derived conjunction -- the report cannot be
    declared clean while carrying a mismatch.
    """

    checked: int
    mismatches: tuple[ReconciliationMismatch, ...] = ()
    notes: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.checked < 0:
            raise ValueError("A reconciliation report's checked count cannot be negative.")

    @property
    def is_clean(self) -> bool:
        """Whether every compared leg agreed."""
        return not self.mismatches

    @property
    def mismatch_count(self) -> int:
        return len(self.mismatches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "is_clean": self.is_clean,
            "mismatch_count": self.mismatch_count,
            "mismatches": [m.to_dict() for m in self.mismatches],
            "notes": list(self.notes),
            "created_at": self.created_at.isoformat(),
        }
