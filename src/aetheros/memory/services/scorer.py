"""
Multi-signal memory scorer (spec Phase 4 -- MemoryScorer; Rule 5 & 6).

Retrieval ranking is deliberately **not** pure vector similarity. The scorer
blends eight signals into one explainable score and records each component on
the :class:`RetrievalExplanation`, so every ranked memory can answer "why was I
retrieved?". Weights are module constants (not magic numbers scattered in the
retriever) and the blend is a plain weighted mean of normalised [0,1] signals,
so the result is itself in [0,1] and reproducible.
"""

from __future__ import annotations

import math
import re

from ..config import MemoryConfig
from ..domain.enums import SourceType
from ..domain.memory import Memory
from ..domain.query import MemoryQuery, RetrievalExplanation
from .._clock import utcnow

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Blend weights. They sum to 1.0 so the final score stays in [0, 1]. Semantic
# and lexical dominate (what the query is *about*); the rest are priors that
# break ties and surface durable, trusted, context-relevant memories.
_WEIGHTS = {
    "semantic": 0.34,
    "lexical": 0.16,
    "recency": 0.12,
    "importance": 0.10,
    "confidence": 0.10,
    "frequency": 0.06,
    "task_relevance": 0.08,
    "source_reliability": 0.04,
}

# Source reliability prior (spec Phase 13 -- "source reliability"). Direct user
# statements and real observations outrank inferences and model output.
_SOURCE_RELIABILITY = {
    SourceType.USER: 1.0,
    SourceType.OBSERVATION: 0.9,
    SourceType.TOOL: 0.85,
    SourceType.SYSTEM: 0.8,
    SourceType.VISION: 0.75,
    SourceType.DOCUMENT: 0.7,
    SourceType.AGENT: 0.65,
    SourceType.CONSOLIDATION: 0.6,
    SourceType.EXTERNAL: 0.55,
    SourceType.INFERENCE: 0.5,
    SourceType.PREDICTION: 0.5,
    SourceType.MODEL: 0.45,
}

_CONTEXT_KEYS = ("session_id", "task_id", "episode_id", "instrument_id", "user_id")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class MemoryScorer:
    """Blend retrieval signals into one explainable, reproducible score."""

    def __init__(self, config: MemoryConfig) -> None:
        self._halflife_days = config.decay_halflife_days

    def recency(self, memory: Memory) -> float:
        """Exponential recency decay on the most recent touch (spec Phase 13)."""
        reference = memory.last_accessed_at or memory.updated_at or memory.created_at
        age_days = max(0.0, (utcnow() - reference).total_seconds() / 86400.0)
        return float(math.pow(0.5, age_days / self._halflife_days))

    @staticmethod
    def frequency(memory: Memory) -> float:
        """Saturating access-frequency signal (diminishing returns)."""
        return 1.0 - math.exp(-memory.access_count / 5.0)

    @staticmethod
    def source_reliability(memory: Memory) -> float:
        return _SOURCE_RELIABILITY.get(memory.source.source_type, 0.5)

    @staticmethod
    def lexical(query_tokens: set[str], memory: Memory) -> float:
        if not query_tokens:
            return 0.0
        content_tokens = _tokens(memory.content)
        if not content_tokens:
            return 0.0
        overlap = query_tokens & content_tokens
        # Overlap coefficient (relative to the query) rather than Jaccard, so a
        # long memory is not penalised for also containing other words.
        return len(overlap) / len(query_tokens)

    @staticmethod
    def task_relevance(query: MemoryQuery, memory: Memory) -> float:
        """Share of query context keys the memory matches (spec Phase 7)."""
        wanted = {k: v for k, v in query.context.items() if k in _CONTEXT_KEYS and v}
        if not wanted:
            return 0.0
        matched = sum(
            1 for k, v in wanted.items() if memory.metadata.get(k) == v
        )
        return matched / len(wanted)

    def score(
        self,
        query: MemoryQuery,
        memory: Memory,
        *,
        semantic: float,
        graph_boost: float = 0.0,
        query_tokens: set[str] | None = None,
    ) -> RetrievalExplanation:
        qt = query_tokens if query_tokens is not None else _tokens(query.text)
        semantic_n = max(0.0, min(1.0, semantic))

        exp = RetrievalExplanation(
            semantic=semantic_n,
            lexical=self.lexical(qt, memory),
            recency=self.recency(memory),
            importance=memory.importance.normalized,
            confidence=memory.confidence,
            frequency=self.frequency(memory),
            task_relevance=self.task_relevance(query, memory),
            source_reliability=self.source_reliability(memory),
            graph_boost=max(0.0, min(1.0, graph_boost)),
        )

        base = (
            _WEIGHTS["semantic"] * exp.semantic
            + _WEIGHTS["lexical"] * exp.lexical
            + _WEIGHTS["recency"] * exp.recency
            + _WEIGHTS["importance"] * exp.importance
            + _WEIGHTS["confidence"] * exp.confidence
            + _WEIGHTS["frequency"] * exp.frequency
            + _WEIGHTS["task_relevance"] * exp.task_relevance
            + _WEIGHTS["source_reliability"] * exp.source_reliability
        )
        # Graph proximity is an additive boost (a memory reached via a known
        # relationship is more relevant than its text alone implies), capped so
        # the score stays in [0, 1].
        exp.score = min(1.0, base + 0.1 * exp.graph_boost)
        exp.reasons = self._reasons(exp)
        return exp

    @staticmethod
    def _reasons(exp: RetrievalExplanation) -> list[str]:
        reasons: list[str] = []
        if exp.semantic >= 0.5:
            reasons.append(f"semantically similar ({exp.semantic:.2f})")
        if exp.lexical >= 0.5:
            reasons.append(f"shares query terms ({exp.lexical:.2f})")
        if exp.task_relevance > 0:
            reasons.append(f"matches current context ({exp.task_relevance:.2f})")
        if exp.graph_boost > 0:
            reasons.append("linked via the knowledge graph")
        if exp.recency >= 0.6:
            reasons.append("recently relevant")
        if exp.confidence >= 0.75:
            reasons.append(f"high confidence ({exp.confidence:.2f})")
        if exp.importance >= 0.75:
            reasons.append("marked important")
        return reasons or ["weak match on the blended signals"]
