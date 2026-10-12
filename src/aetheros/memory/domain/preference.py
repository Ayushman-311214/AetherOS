"""
Preference and failure/recovery memory records (spec Phase 1 types 5 & 6).

A :class:`Preference` tracks a stable choice the user or system holds, keeping
the spec's required distinctions (explicit vs inferred vs temporary, with
confidence, source and last-confirmation). A :class:`FailureRecord` remembers
what went wrong and -- crucially -- how it was recovered, so future planning can
retrieve the working alternative instead of repeating the failure (Phase 11).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import (
    MemoryImportance,
    MemoryType,
    OutcomeStatus,
    PreferenceKind,
    SourceType,
    Veracity,
)
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Preference:
    """A user/system preference (spec Phase 1 type 5, Phase 13 example)."""

    subject: str
    value: str
    kind: PreferenceKind = PreferenceKind.INFERRED
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    confidence: float = 0.5
    evidence_count: int = 1
    last_confirmed_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @property
    def veracity(self) -> Veracity:
        # An explicit preference is user input; an inferred one is an assumption
        # until confirmed -- never asserted as a FACT.
        if self.kind is PreferenceKind.EXPLICIT:
            return Veracity.USER_INPUT
        return Veracity.ASSUMPTION

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "value": self.value,
            "kind": self.kind.value,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "last_confirmed_at": (
                self.last_confirmed_at.isoformat() if self.last_confirmed_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        source_type = (
            SourceType.USER
            if self.kind is PreferenceKind.EXPLICIT
            else SourceType.INFERENCE
        )
        veracity = (
            Veracity.USER_INPUT
            if self.kind is PreferenceKind.EXPLICIT
            else Veracity.ASSUMPTION
        )
        importance = (
            MemoryImportance.HIGH
            if self.kind is PreferenceKind.EXPLICIT
            else MemoryImportance.NORMAL
        )
        return Memory(
            id=self.id,
            content=f"User prefers {self.value} for {self.subject}.",
            memory_type=MemoryType.PREFERENCE,
            veracity=veracity,
            data={"preference": self.to_dict()},
            source=MemorySource(source_type=source_type, origin="preference_memory"),
            confidence=self.confidence,
            importance=importance,
            evidence_count=self.evidence_count,
            tags=["preference", self.subject.lower(), self.kind.value],
            entities=[self.subject, self.value],
        )


@dataclass(slots=True)
class RecoveryAttempt:
    """One recorded recovery try against a failure (Phase 11).

    An attempt is observed fact: the action taken, when, and whether it
    worked. A *reason* for the failure is never stored here -- suspected
    causes live on :class:`FailureRecord` under quarantine until confirmed.
    """

    action: str
    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    detail: str = ""
    attempted_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status.value,
            "detail": self.detail,
            "attempted_at": self.attempted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecoveryAttempt:
        attempted = data.get("attempted_at")
        return cls(
            action=data["action"],
            status=OutcomeStatus(data.get("status", OutcomeStatus.UNKNOWN.value)),
            detail=data.get("detail", ""),
            attempted_at=datetime.fromisoformat(attempted) if attempted else _utcnow(),
        )


@dataclass(slots=True)
class FailureRecord:
    """A remembered failure and its recovery (spec Phase 11).

    Epistemic discipline: ``observed_symptoms`` are facts (what was seen);
    ``suspected_cause`` is an unverified hypothesis and is quarantined --
    excluded from the searchable summary until ``cause_confirmed`` is set by
    an explicit confirmation call. A suspected cause must never read as a
    confirmed fact in retrieval.
    """

    failure_type: str
    error: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    observed_symptoms: list[str] = field(default_factory=list)
    suspected_cause: str = ""
    cause_confirmed: bool = False
    attempts: list[RecoveryAttempt] = field(default_factory=list)
    attempted_recovery: str = ""
    successful_recovery: str = ""
    recovery_status: OutcomeStatus = OutcomeStatus.UNKNOWN
    frequency: int = 1
    episode_id: str | None = None
    procedure_id: str | None = None
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def recovered(self) -> bool:
        return bool(self.successful_recovery)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "failure_type": self.failure_type,
            "error": self.error,
            "action": self.action,
            "context": dict(self.context),
            "environment": dict(self.environment),
            "observed_symptoms": list(self.observed_symptoms),
            "suspected_cause": self.suspected_cause,
            "cause_confirmed": self.cause_confirmed,
            "attempts": [a.to_dict() for a in self.attempts],
            "attempted_recovery": self.attempted_recovery,
            "successful_recovery": self.successful_recovery,
            "recovery_status": self.recovery_status.value,
            "frequency": self.frequency,
            "episode_id": self.episode_id,
            "procedure_id": self.procedure_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureRecord:
        created = data.get("created_at")
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            failure_type=data["failure_type"],
            error=data.get("error", ""),
            action=data.get("action", ""),
            context=dict(data.get("context", {})),
            environment=dict(data.get("environment", {})),
            observed_symptoms=list(data.get("observed_symptoms", [])),
            suspected_cause=data.get("suspected_cause", ""),
            cause_confirmed=bool(data.get("cause_confirmed", False)),
            attempts=[
                RecoveryAttempt.from_dict(a) for a in data.get("attempts", [])
            ],
            attempted_recovery=data.get("attempted_recovery", ""),
            successful_recovery=data.get("successful_recovery", ""),
            recovery_status=OutcomeStatus(
                data.get("recovery_status", OutcomeStatus.UNKNOWN.value)
            ),
            frequency=int(data.get("frequency", 1)),
            episode_id=data.get("episode_id"),
            procedure_id=data.get("procedure_id"),
            created_at=datetime.fromisoformat(created) if created else _utcnow(),
        )

    def to_memory(self) -> Memory:
        recovery = (
            f" Recovered via: {self.successful_recovery}."
            if self.recovered
            else " No successful recovery recorded."
        )
        # Quarantine: a suspected cause is NEVER part of the searchable
        # summary until explicitly confirmed. Unverified suspicion must not
        # read as fact in retrieval.
        cause_note = (
            f" Confirmed cause: {self.suspected_cause}."
            if self.cause_confirmed and self.suspected_cause
            else ""
        )
        return Memory(
            id=self.id,
            content=(
                f"Action '{self.action or self.failure_type}' failed: "
                f"{self.error}.{recovery}{cause_note}"
            ),
            memory_type=MemoryType.FAILURE,
            veracity=Veracity.OBSERVATION,
            data={"failure": self.to_dict()},
            source=MemorySource(source_type=SourceType.OBSERVATION, origin="failure_memory"),
            # A recovered failure is more valuable (it carries the fix) and more
            # trusted than one that is still open.
            confidence=0.85 if self.recovered else 0.6,
            importance=MemoryImportance.HIGH if self.recovered else MemoryImportance.NORMAL,
            evidence_count=self.frequency,
            tags=["failure", self.failure_type, "recovered" if self.recovered else "open"],
            metadata={
                k: v
                for k, v in {
                    "episode_id": self.episode_id,
                    "task_id": self.context.get("task_id"),
                    "session_id": self.context.get("session_id"),
                }.items()
                if v is not None
            },
        )
