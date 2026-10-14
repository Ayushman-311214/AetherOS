"""
Procedural-memory records: learned, reusable procedures (spec Phase 10).

A :class:`Procedure` is a workflow the system has distilled from repeated
successful episodes. It is deliberately *evidence-gated*: the spec is explicit
that "procedures must not automatically become trusted merely because they
succeeded once", so a procedure tracks ``success_count`` / ``failure_count`` and
derives a confidence from them rather than asserting one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import MemoryImportance, MemoryType, SourceType, Veracity
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ProcedureStep:
    """One step in a procedure (spec Phase 10)."""

    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    verification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "arguments": dict(self.arguments),
            "description": self.description,
            "verification": self.verification,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcedureStep:
        return cls(
            action=data["action"],
            arguments=dict(data.get("arguments", {})),
            description=data.get("description", ""),
            verification=data.get("verification", ""),
        )


@dataclass(slots=True)
class Procedure:
    """A learned, reusable procedure (spec Phase 10)."""

    name: str
    goal: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    preconditions: list[str] = field(default_factory=list)
    steps: list[ProcedureStep] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_outcomes: list[str] = field(default_factory=list)
    verification: str = ""
    fallbacks: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    last_success_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def total_uses(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_uses if self.total_uses else 0.0

    @property
    def confidence(self) -> float:
        """
        Confidence from evidence, not assertion (spec Phase 10/13).

        A Wilson-style shrink toward 0.5 so a single success does not read as
        certainty: with no evidence it is 0.5, and it approaches the raw success
        rate only as the sample grows.
        """
        n = self.total_uses
        if n == 0:
            return 0.5
        # Pull the raw rate toward 0.5 with a pseudo-count of 2 on each side.
        return (self.success_count + 1.0) / (n + 2.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "preconditions": list(self.preconditions),
            "steps": [s.to_dict() for s in self.steps],
            "parameters": dict(self.parameters),
            "expected_outcomes": list(self.expected_outcomes),
            "verification": self.verification,
            "fallbacks": list(self.fallbacks),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_success_at": (
                self.last_success_at.isoformat() if self.last_success_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Procedure:
        ls = data.get("last_success_at")
        created = data.get("created_at")
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data["name"],
            goal=data["goal"],
            preconditions=list(data.get("preconditions", [])),
            steps=[ProcedureStep.from_dict(s) for s in data.get("steps", [])],
            parameters=dict(data.get("parameters", {})),
            expected_outcomes=list(data.get("expected_outcomes", [])),
            verification=data.get("verification", ""),
            fallbacks=list(data.get("fallbacks", [])),
            success_count=int(data.get("success_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            last_success_at=datetime.fromisoformat(ls) if ls else None,
            created_at=datetime.fromisoformat(created) if created else _utcnow(),
        )

    def to_memory(self) -> Memory:
        return Memory(
            id=self.id,
            content=f"Procedure '{self.name}': {self.goal}.",
            memory_type=MemoryType.PROCEDURAL,
            veracity=Veracity.OBSERVATION,
            data={"procedure": self.to_dict()},
            source=MemorySource(
                source_type=SourceType.CONSOLIDATION, origin="procedural_memory"
            ),
            confidence=self.confidence,
            importance=MemoryImportance.HIGH,
            evidence_count=max(1, self.total_uses),
            tags=["procedure", self.name.lower()],
        )
