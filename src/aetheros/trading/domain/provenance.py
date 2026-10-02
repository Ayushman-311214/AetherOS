"""
Provenance and data-quality value objects.

Every important trading observation must answer: where did this come from, when,
and how good is it? These two small immutable records carry that answer through
the whole pipeline (spec sections 12, 24, 47).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import DataQualityStatus, SourceTier


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a piece of evidence or data originated."""

    source: str
    tier: SourceTier
    retrieved_at: datetime = field(default_factory=_utcnow)
    detail: str | None = None

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tier": self.tier.value,
            "retrieved_at": self.retrieved_at.isoformat(),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class DataQuality:
    """
    An honest assessment of the data underlying an analysis.

    ``issues`` is never silently empty when something is wrong: a stale or
    partial dataset carries a human-readable reason so the limitation reaches
    the final report rather than being hidden.
    """

    status: DataQualityStatus
    issues: tuple[str, ...] = ()
    freshness_seconds: float | None = None

    @property
    def ok(self) -> bool:
        return self.status is DataQualityStatus.OK

    @property
    def usable(self) -> bool:
        """Whether analysis can proceed at all (anything but MISSING/INVALID)."""
        return self.status not in (
            DataQualityStatus.MISSING,
            DataQualityStatus.INVALID,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "issues": list(self.issues),
            "freshness_seconds": self.freshness_seconds,
        }
