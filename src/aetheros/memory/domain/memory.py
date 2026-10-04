"""
The central memory record and its provenance/link value objects.

:class:`Memory` is the one row every cognitive kind ultimately reduces to in the
``memory_items`` table (spec Phase 2). The specialised records -- Episode, Fact,
Procedure, Preference, FailureRecord, PredictionMemory -- are *views* that carry
their extra structure in dedicated tables and/or in ``Memory.data``; they all
own a backing :class:`Memory` so a single retrieval pipeline, scorer and vector
index serve every type (spec Rule-of-reuse, Phase 4/7).

Serialisation is deterministic and lossless: ``to_dict`` / ``from_dict`` round
-trip through plain JSON types so a memory survives SQLite, the event bus and a
tool result unchanged, and so provenance is never dropped on the way (Rule 8).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import (
    MemoryImportance,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    Veracity,
    confidence_band,
)


def utcnow() -> datetime:
    """Timezone-aware current UTC instant (the whole layer is tz-aware)."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """A fresh opaque memory id."""
    return uuid.uuid4().hex


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # ISO string
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass(slots=True)
class MemorySource:
    """
    Where a memory came from (spec Phase 3, Rule 8 -- preserve provenance).

    ``origin`` is a stable identifier for the producer (a tool name, an agent
    name, a document id, a model/version); ``reference`` is an in-source
    locator (a URL, a page number, a message id); ``detail`` carries anything
    else worth auditing without widening the schema.
    """

    source_type: SourceType = SourceType.SYSTEM
    origin: str = ""
    reference: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "origin": self.origin,
            "reference": self.reference,
            "detail": dict(self.detail),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemorySource:
        return cls(
            source_type=SourceType(data.get("source_type", SourceType.SYSTEM.value)),
            origin=data.get("origin", ""),
            reference=data.get("reference"),
            detail=dict(data.get("detail", {})),
        )


@dataclass(slots=True)
class MemoryLink:
    """
    A typed, weighted edge between two memories (spec Phase 2 -- memory_links).

    Distinct from a knowledge-graph relationship (which connects *entities*):
    a link connects two stored *memories*, e.g. a failure to its successful
    recovery, or a raw episode to the consolidated procedure derived from it.
    """

    from_id: str
    to_id: str
    link_type: str = "related_to"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "link_type": self.link_type,
            "weight": self.weight,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryLink:
        return cls(
            from_id=data["from_id"],
            to_id=data["to_id"],
            link_type=data.get("link_type", "related_to"),
            weight=float(data.get("weight", 1.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class Memory:
    """
    One stored memory -- the universal record (spec Phase 2/3).

    Mutable on purpose: the :class:`~aetheros.memory.services.updater` edits
    fields in place and bumps :attr:`version`, while
    :meth:`register_access` records reads for the recency/frequency scorer.
    The embedding itself is **not** stored here -- it lives in the vector index
    keyed by :attr:`id`, so the hot path (metadata filtering, ranking) never
    pays to carry a float array around.
    """

    # --- identity & kind --------------------------------------------------
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    id: str = field(default_factory=new_id)
    veracity: Veracity = Veracity.OBSERVATION

    # --- structured payload & provenance ---------------------------------
    data: dict[str, Any] = field(default_factory=dict)
    source: MemorySource = field(default_factory=MemorySource)

    # --- scoring signals --------------------------------------------------
    confidence: float = 0.5
    importance: MemoryImportance = MemoryImportance.NORMAL
    scope: MemoryScope = MemoryScope.LONG_TERM
    status: MemoryStatus = MemoryStatus.ACTIVE
    evidence_count: int = 1
    access_count: int = 0

    # --- time -------------------------------------------------------------
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None

    # --- bookkeeping ------------------------------------------------------
    version: int = 1
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)

    # Cross-cutting context (task_id, session_id, episode_id, instrument_id,
    # user_id, application, environment ...). Kept as a free dict so adding a
    # new context dimension never needs a schema change; the common ones are
    # also indexed as real columns by the repository.
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if not self.content or not str(self.content).strip():
            # Validation lives in MemoryValidator for the writer path; this is a
            # last-ditch guard so a blank record can never reach storage.
            raise ValueError("Memory.content must be a non-empty string.")

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    @property
    def confidence_band(self) -> str:
        return confidence_band(self.confidence)

    @property
    def is_permanent(self) -> bool:
        return self.scope is MemoryScope.PERMANENT

    def register_access(self, *, at: datetime | None = None) -> None:
        """Record that this memory was retrieved (feeds recency/frequency)."""
        self.access_count += 1
        self.last_accessed_at = at or utcnow()

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """
        Whether the memory has passed its TTL.

        PERMANENT memories never expire regardless of ``expires_at`` (spec
        Phase 14) -- the scope is the override.
        """
        if self.is_permanent or self.expires_at is None:
            return False
        return (now or utcnow()) >= self.expires_at

    def context(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "veracity": self.veracity.value,
            "content": self.content,
            "data": dict(self.data),
            "source": self.source.to_dict(),
            "confidence": self.confidence,
            "importance": int(self.importance),
            "scope": self.scope.value,
            "status": self.status.value,
            "evidence_count": self.evidence_count,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed_at": (
                self.last_accessed_at.isoformat() if self.last_accessed_at else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "version": self.version,
            "tags": list(self.tags),
            "entities": list(self.entities),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        return cls(
            id=data.get("id", new_id()),
            memory_type=MemoryType(data.get("memory_type", MemoryType.SEMANTIC.value)),
            veracity=Veracity(data.get("veracity", Veracity.OBSERVATION.value)),
            content=data["content"],
            data=dict(data.get("data", {})),
            source=MemorySource.from_dict(data.get("source", {})),
            confidence=float(data.get("confidence", 0.5)),
            importance=MemoryImportance(int(data.get("importance", MemoryImportance.NORMAL))),
            scope=MemoryScope(data.get("scope", MemoryScope.LONG_TERM.value)),
            status=MemoryStatus(data.get("status", MemoryStatus.ACTIVE.value)),
            evidence_count=int(data.get("evidence_count", 1)),
            access_count=int(data.get("access_count", 0)),
            created_at=_parse_dt(data.get("created_at")) or utcnow(),
            updated_at=_parse_dt(data.get("updated_at")) or utcnow(),
            last_accessed_at=_parse_dt(data.get("last_accessed_at")),
            expires_at=_parse_dt(data.get("expires_at")),
            version=int(data.get("version", 1)),
            tags=list(data.get("tags", [])),
            entities=list(data.get("entities", [])),
            metadata=dict(data.get("metadata", {})),
        )
