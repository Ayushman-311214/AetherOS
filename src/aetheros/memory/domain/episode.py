"""
Episodic-memory value objects (spec Phase 9, lifecycle Phase 10).

An :class:`Episode` is a remembered experience: what happened, when, in what
environment, which :class:`ActionRecord` steps were taken, which
:class:`EpisodeObservation` notes were recorded, and the :class:`Outcome`.
Episodes are the raw material the consolidator mines into procedures and
failure patterns, so they record enough structure to replay and to learn from,
while remaining a plain serialisable record.

:class:`EpisodeObservation` is a point-in-time note (market state, screen
state): unlike a working-memory current-observation it is historical record,
so repeats accumulate rather than replace. ``relevant_memories`` names the
memories the episode drew on (linked as ``references`` edges at start time);
``provenance`` records the recording channel (agent run id, tool version)
without ever carrying secrets -- those are redacted before persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import (
    MemoryImportance,
    MemoryType,
    OutcomeStatus,
    SourceType,
    Veracity,
)
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ActionRecord:
    """One step taken within an episode (a tool call, an agent action)."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    result_summary: str = ""
    error: str | None = None
    duration_ms: float | None = None
    started_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": dict(self.arguments),
            "status": self.status.value,
            "result_summary": self.result_summary,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionRecord:
        started = data.get("started_at")
        return cls(
            name=data["name"],
            arguments=dict(data.get("arguments", {})),
            status=OutcomeStatus(data.get("status", OutcomeStatus.UNKNOWN.value)),
            result_summary=data.get("result_summary", ""),
            error=data.get("error"),
            duration_ms=data.get("duration_ms"),
            started_at=datetime.fromisoformat(started) if started else _utcnow(),
        )


@dataclass(slots=True)
class EpisodeObservation:
    """One timestamped note recorded within an episode (Phase 10).

    Unlike a working-memory current-observation (which a newer reading
    replaces), an episode observation is historical record: repeats accumulate
    in chronological order, and exact redeliveries (same key + timestamp) are
    deduplicated by the recorder rather than stored twice.
    """

    key: str
    content: str = ""
    observed_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "content": self.content,
            "observed_at": self.observed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeObservation:
        observed = data.get("observed_at")
        return cls(
            key=data["key"],
            content=data.get("content", ""),
            observed_at=datetime.fromisoformat(observed) if observed else _utcnow(),
        )


@dataclass(slots=True)
class Outcome:
    """The result of an episode or an action (spec Phase 9)."""

    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    detail: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "detail": self.detail,
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Outcome:
        return cls(
            status=OutcomeStatus(data.get("status", OutcomeStatus.UNKNOWN.value)),
            detail=data.get("detail", ""),
            metrics=dict(data.get("metrics", {})),
        )


@dataclass(slots=True)
class Episode:
    """A remembered task execution (spec Phase 9, lifecycle Phase 10)."""

    goal: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str | None = None
    session_id: str | None = None
    environment: dict[str, Any] = field(default_factory=dict)
    actions: list[ActionRecord] = field(default_factory=list)
    observations: list[EpisodeObservation] = field(default_factory=list)
    outcome: Outcome = field(default_factory=Outcome)
    lessons: list[str] = field(default_factory=list)
    relevant_memories: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=_utcnow)
    ended_at: datetime | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() * 1000.0

    @property
    def succeeded(self) -> bool:
        return self.outcome.status is OutcomeStatus.SUCCESS

    def summary(self) -> str:
        """One-line human description used as the backing memory's content."""
        verb = {
            OutcomeStatus.SUCCESS: "succeeded",
            OutcomeStatus.FAILURE: "failed",
            OutcomeStatus.PARTIAL: "partially completed",
        }.get(self.outcome.status, "ran")
        steps = ", ".join(a.name for a in self.actions) or "no recorded steps"
        return f"Episode '{self.goal}' {verb} via [{steps}]."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "environment": dict(self.environment),
            "actions": [a.to_dict() for a in self.actions],
            "observations": [o.to_dict() for o in self.observations],
            "outcome": self.outcome.to_dict(),
            "lessons": list(self.lessons),
            "relevant_memories": list(self.relevant_memories),
            "provenance": dict(self.provenance),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        started = data.get("started_at")
        ended = data.get("ended_at")
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            goal=data["goal"],
            task_id=data.get("task_id"),
            session_id=data.get("session_id"),
            environment=dict(data.get("environment", {})),
            actions=[ActionRecord.from_dict(a) for a in data.get("actions", [])],
            observations=[
                EpisodeObservation.from_dict(o) for o in data.get("observations", [])
            ],
            outcome=Outcome.from_dict(data.get("outcome", {})),
            lessons=list(data.get("lessons", [])),
            relevant_memories=list(data.get("relevant_memories", [])),
            provenance=dict(data.get("provenance", {})),
            started_at=datetime.fromisoformat(started) if started else _utcnow(),
            ended_at=datetime.fromisoformat(ended) if ended else None,
        )

    def to_memory(self) -> Memory:
        """
        Project the episode onto the universal :class:`Memory` record.

        The episode's full structure is preserved in ``data`` (so it can be
        rebuilt with :meth:`from_dict`), while ``content`` holds the searchable
        one-liner. A successful episode is slightly more important and more
        trusted than a failed one, but both are OBSERVATIONs -- never FACTs.
        """
        importance = (
            MemoryImportance.HIGH if self.succeeded else MemoryImportance.NORMAL
        )
        return Memory(
            id=self.id,
            content=self.summary(),
            memory_type=MemoryType.EPISODIC,
            veracity=Veracity.OBSERVATION,
            data={"episode": self.to_dict()},
            source=MemorySource(
                source_type=SourceType.AGENT,
                origin="episodic_memory",
                detail={
                    "goal": self.goal,
                    **{k: v for k, v in self.provenance.items() if v is not None},
                },
            ),
            confidence=0.9 if self.succeeded else 0.6,
            importance=importance,
            tags=["episode", self.outcome.status.value],
            entities=list(self.environment.get("entities", [])),
            metadata={
                k: v
                for k, v in {
                    "episode_id": self.id,
                    "task_id": self.task_id,
                    "session_id": self.session_id,
                    "application": self.environment.get("application"),
                }.items()
                if v is not None
            },
        )
