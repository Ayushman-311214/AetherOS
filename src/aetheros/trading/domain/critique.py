"""
Critic / validation value objects.

A :class:`CriticReport` is the adversary's verdict on a proposed signal. The
critic exists to *challenge* the deterministic analysis, not to echo it: it runs
a fixed battery of checks -- is the evidence sufficient, do the indicators
actually agree with the fused direction, is the data real and fresh, is the
risk/reward acceptable, does the signal beat its historical baseline -- and
returns one of three verdicts (spec sections 5, 28).

The verdict is a deterministic function of the checks, never an LLM opinion and
never a probability. A weak-but-real case is ``REJECT``; a case with too little
sound input to judge at all is ``INSUFFICIENT_EVIDENCE`` -- the honest answer
the spec prefers over a fabricated approval (section 61). Checks the current
build cannot yet perform (calibration, upcoming-event risk) are reported
``SKIPPED``, never silently treated as passed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import CheckStatus, CriticVerdict, Direction
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CriticCheck:
    """One named check the critic ran, its outcome and a human-readable reason."""

    name: str
    status: CheckStatus
    detail: str

    @property
    def failed(self) -> bool:
        return self.status is CheckStatus.FAIL

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class CriticReport:
    """Deterministic go/no-go verdict on a proposed signal, with its reasoning."""

    instrument: Instrument
    direction: Direction
    verdict: CriticVerdict
    checks: tuple[CriticCheck, ...]
    reasons: tuple[str, ...]
    quality: DataQuality
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def approved(self) -> bool:
        """True only for an outright APPROVE -- never for REJECT/INSUFFICIENT."""
        return self.verdict is CriticVerdict.APPROVE

    @property
    def failed_checks(self) -> tuple[CriticCheck, ...]:
        return tuple(c for c in self.checks if c.failed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "verdict": self.verdict.value,
            "approved": self.approved,
            "checks": [c.to_dict() for c in self.checks],
            "reasons": list(self.reasons),
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
