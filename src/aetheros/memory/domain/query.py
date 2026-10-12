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

    # Context-assembly budget (spec Phase 8). All default to 0 == unbounded, so
    # an existing caller that sets none of them keeps the prior behaviour (only
    # ``limit`` and ``min_confidence`` bind). ``max_age_days`` is a validity
    # cutoff: memories created longer ago than this are excluded from every
    # candidate source. Token counting against ``max_tokens`` is *conservative*
    # (a character/word heuristic, not a model tokenizer) -- see the retriever.
    max_tokens: int = 0
    max_chars: int = 0
    max_per_type: int = 0
    max_age_days: float = 0.0

    def __post_init__(self) -> None:
        self.limit = max(1, int(self.limit))
        self.candidate_limit = max(self.limit, int(self.candidate_limit))
        self.max_tokens = max(0, int(self.max_tokens))
        self.max_chars = max(0, int(self.max_chars))
        self.max_per_type = max(0, int(self.max_per_type))
        self.max_age_days = max(0.0, float(self.max_age_days))


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
    # Provenance (spec Phase 8): which candidate source(s) surfaced this memory
    # -- e.g. {"structured", "vector", "graph_entity", "graph_link"}. Lets a
    # caller see *how* a memory was found, not just how it scored.
    sources: list[str] = field(default_factory=list)

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
            "sources": list(self.sources),
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


@dataclass(slots=True)
class RetrievalReport:
    """
    The full, honest outcome of one retrieval (spec Phase 8).

    ``results`` is the ranked, budgeted context. The remaining fields disclose
    *how healthy* the retrieval was so a caller never mistakes a degraded recall
    for a complete one: ``degraded_sources`` names any candidate source that
    failed and was skipped (e.g. the vector index was unreachable), and the
    counters explain why candidates were dropped by the context budget. Optional
    recall degrades safely -- a failed source lowers quality, it does not raise.
    """

    results: list[MemoryResult] = field(default_factory=list)
    degraded_sources: list[str] = field(default_factory=list)
    candidates_considered: int = 0
    dropped_by_filter: int = 0
    dropped_by_threshold: int = 0
    dropped_by_budget: int = 0
    token_count_exact: bool = False

    @property
    def degraded(self) -> bool:
        return bool(self.degraded_sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "degraded": self.degraded,
            "degraded_sources": list(self.degraded_sources),
            "candidates_considered": self.candidates_considered,
            "dropped_by_filter": self.dropped_by_filter,
            "dropped_by_threshold": self.dropped_by_threshold,
            "dropped_by_budget": self.dropped_by_budget,
            "token_count_exact": self.token_count_exact,
        }
