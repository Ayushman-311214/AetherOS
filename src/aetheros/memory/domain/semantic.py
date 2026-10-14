"""
Semantic-memory value objects: entities and the relationships between them.

These are the nodes and edges of the knowledge graph (spec Phase 6). An
:class:`Entity` is a stable thing the system knows about (a person, an
application, an instrument, a UI element); a :class:`Relationship` is a typed,
evidenced, time-aware edge between two of them. Both carry confidence and
provenance so the graph never asserts an unqualified truth (Rule 8, Phase 13).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import RelationType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Entity:
    """A node in the knowledge graph (spec Phase 6)."""

    name: str
    entity_type: str = "concept"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attributes: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    confidence: float = 0.6
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Entity.name must be non-empty.")
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @property
    def key(self) -> str:
        """Canonical lookup key: type + normalised name (graph dedup)."""
        return f"{self.entity_type}:{self.name.strip().lower()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": dict(self.attributes),
            "aliases": list(self.aliases),
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        created = data.get("created_at")
        updated = data.get("updated_at")
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data["name"],
            entity_type=data.get("entity_type", "concept"),
            attributes=dict(data.get("attributes", {})),
            aliases=list(data.get("aliases", [])),
            confidence=float(data.get("confidence", 0.6)),
            created_at=datetime.fromisoformat(created) if created else _utcnow(),
            updated_at=datetime.fromisoformat(updated) if updated else _utcnow(),
        )


@dataclass(slots=True)
class Relationship:
    """
    A typed edge between two entities (spec Phase 6).

    ``valid_from`` / ``valid_to`` give temporal validity so a superseded fact
    ("user preferred Chrome") can be closed rather than deleted when a newer one
    arrives, keeping history auditable (Phase 13 -- contradictory memories are
    not blindly overwritten).
    """

    source_id: str
    target_id: str
    relation: str = RelationType.RELATED_TO.value
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    weight: float = 1.0
    confidence: float = 0.6
    evidence_count: int = 1
    evidence_memory_ids: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    valid_from: datetime = field(default_factory=_utcnow)
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @property
    def is_active(self) -> bool:
        return self.valid_to is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "evidence_memory_ids": list(self.evidence_memory_ids),
            "attributes": dict(self.attributes),
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        vf = data.get("valid_from")
        vt = data.get("valid_to")
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation=data.get("relation", RelationType.RELATED_TO.value),
            weight=float(data.get("weight", 1.0)),
            confidence=float(data.get("confidence", 0.6)),
            evidence_count=int(data.get("evidence_count", 1)),
            evidence_memory_ids=list(data.get("evidence_memory_ids", [])),
            attributes=dict(data.get("attributes", {})),
            valid_from=datetime.fromisoformat(vf) if vf else _utcnow(),
            valid_to=datetime.fromisoformat(vt) if vt else None,
        )
