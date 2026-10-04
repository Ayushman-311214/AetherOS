"""
Query, result and explanation value objects for retrieval (spec Phase 7).

The retriever takes a :class:`MemoryQuery` and returns ranked
:class:`MemoryResult` objects, each of which carries a
:class:`RetrievalExplanation` answering the spec's hard requirement (Rule 6):
*"for each important retrieved memory, the system should be able to explain why
it was retrieved"*. The explanation is structured, not a prose blob, so a tool
or the CLI can render the exact per-signal contribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import MemoryType, Veracity
from .memory import Memory


@dataclass(slots=True)
class MemoryQuery:
    """
    A retrieval request (spec Phase 7 -- query understanding stage input).

    ``text`` drives semantic + lexical matching; the remaining fields are
    hard/soft filters that keep retrieval from being "purely vector
    similarity" (Rule 5). ``context`` matches against indexed metadata columns
    (session_id, task_id, instrument_id ...), implementing the task/context
    boundary the security section (Phase 26) requires.
    """

    text: str = ""
    memory_types: list[MemoryType] = field(default_factory=list)
    veracities: list[Veracity] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    limit: int = 5
    min_confidence: float = 0.0
    min_similarity: float = 0.0
    include_archived: bool = False
    # Graph expansion: pull in memories linked to the semantic hits (spec
    # Phase 7 "graph expansion"). 0 disables it.
    expand_hops: int = 1
    # Candidate pool size before scoring/ranking trims to ``limit``.
    candidate_limit: int = 50

    def __post_init__(self) -> None:
        self.limit = max(1, int(self.limit))
        self.candidate_limit = max(self.limit, int(self.candidate_limit))


@dataclass(slots=True)
class RetrievalExplanation:
    """
    Per-memory, per-signal justification for a retrieval (Rule 6, Phase 7).

    Each component is on [0, 1]; ``score`` is their weighted blend (the value
    the result was ranked by). ``reasons`` holds short human lines so the
    explanation reads naturally without the caller re-deriving it.
    """

    score: float = 0.0
    semantic: float = 0.0
    lexical: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    confidence: float = 0.0
    frequency: float = 0.0
    task_relevance: float = 0.0
    source_reliability: float = 0.0
    graph_boost: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "semantic": round(self.semantic, 4),
            "lexical": round(self.lexical, 4),
            "recency": round(self.recency, 4),
            "importance": round(self.importance, 4),
            "confidence": round(self.confidence, 4),
            "frequency": round(self.frequency, 4),
            "task_relevance": round(self.task_relevance, 4),
            "source_reliability": round(self.source_reliability, 4),
            "graph_boost": round(self.graph_boost, 4),
            "reasons": list(self.reasons),
        }


@dataclass(slots=True)
class MemoryResult:
    """A retrieved memory paired with its ranking explanation."""

    memory: Memory
    explanation: RetrievalExplanation = field(default_factory=RetrievalExplanation)

    @property
    def score(self) -> float:
        return self.explanation.score

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory": self.memory.to_dict(),
            "explanation": self.explanation.to_dict(),
        }
