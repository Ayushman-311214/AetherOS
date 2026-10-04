"""
Hybrid, explainable retrieval engine (spec Phase 7 -- the heart of recall).

Implements the pipeline the spec draws out: query -> structured candidate
generation (SQL filters) -> semantic vector search over that pool -> graph
expansion -> multi-signal scoring -> threshold -> dedup -> rank -> assemble.
Crucially it is *hybrid*: vectors are one signal over a SQL-filtered pool that
is also expanded through the knowledge graph and the memory-link graph, so a
query like "how did we add RSI to TradingView last time?" can surface the linked
episode/procedure, not merely the most lexically similar sentence (Rule 5).

Every returned memory carries a :class:`RetrievalExplanation` (Rule 6).
"""

from __future__ import annotations

import re

from ..config import MemoryConfig
from ..domain.memory import Memory
from ..domain.query import MemoryQuery, MemoryResult
from ..graph.store import KnowledgeGraph
from ..storage.repository import MemoryRepository
from ..vector.index import VectorIndex
from .scorer import MemoryScorer

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class MemoryRetriever:
    """Assemble ranked, explained memories for a query."""

    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: VectorIndex,
        graph: KnowledgeGraph,
        scorer: MemoryScorer,
        config: MemoryConfig,
    ) -> None:
        self._repo = repository
        self._vectors = vector_index
        self._graph = graph
        self._scorer = scorer
        self._config = config

    async def retrieve(self, query: MemoryQuery) -> list[MemoryResult]:
        # 1. Structured candidate generation.
        candidates = await self._repo.candidates(query)
        by_id: dict[str, Memory] = {m.id: m for m in candidates}
        graph_boost: dict[str, float] = {}

        # 2. Graph expansion -- pull in memories reachable via entity / link
        #    relationships, flagged with a boost so proximity counts in scoring.
        if query.expand_hops > 0:
            await self._expand_via_entities(query, by_id, graph_boost)
            await self._expand_via_links(candidates, by_id, graph_boost)

        if not by_id:
            return []

        # 3. Semantic search over the (expanded) candidate pool.
        semantic: dict[str, float] = {}
        if query.text.strip():
            hits = await self._vectors.search(
                query.text,
                limit=len(by_id),
                candidate_ids=list(by_id.keys()),
            )
            semantic = {mid: score for mid, score in hits}

        # 4-6. Score, threshold, collect.
        query_tokens = set(_TOKEN_RE.findall(query.text.lower()))
        results: list[MemoryResult] = []
        for mid, memory in by_id.items():
            exp = self._scorer.score(
                query,
                memory,
                semantic=semantic.get(mid, 0.0),
                graph_boost=graph_boost.get(mid, 0.0),
                query_tokens=query_tokens,
            )
            if memory.confidence < query.min_confidence:
                continue
            if exp.score < max(query.min_similarity, self._config.similarity_threshold):
                continue
            results.append(MemoryResult(memory=memory, explanation=exp))

        # 7. Dedup near-identical content, keeping the higher score.
        results = self._dedup(results)

        # 8. Rank and trim.
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: query.limit]

    # ------------------------------------------------------------------
    # Graph expansion
    # ------------------------------------------------------------------

    async def _expand_via_entities(
        self,
        query: MemoryQuery,
        by_id: dict[str, Memory],
        graph_boost: dict[str, float],
    ) -> None:
        """Memories referencing the query's entities (and their graph neighbours)."""
        seed_entities = list(query.entities)
        for name in list(seed_entities):
            related = await self._graph.find_related_entities(
                name, max_hops=query.expand_hops
            )
            seed_entities.extend(e.name for e in related[:10])

        if not seed_entities:
            return

        probe = MemoryQuery(
            entities=list(dict.fromkeys(seed_entities)),
            candidate_limit=query.candidate_limit,
            include_archived=query.include_archived,
        )
        for memory in await self._repo.candidates(probe):
            if memory.id not in by_id:
                by_id[memory.id] = memory
            # Direct entity reference boosts more than a graph-neighbour hit.
            direct = bool(set(memory.entities) & set(query.entities))
            graph_boost[memory.id] = max(
                graph_boost.get(memory.id, 0.0), 1.0 if direct else 0.5
            )

    async def _expand_via_links(
        self,
        candidates: list[Memory],
        by_id: dict[str, Memory],
        graph_boost: dict[str, float],
    ) -> None:
        """Memories joined to a candidate by a typed memory_link (e.g. recovery)."""
        for memory in candidates[:10]:
            for other_id, _link_type, weight in await self._repo.linked_ids(memory.id):
                if other_id not in by_id:
                    linked = await self._repo.get(other_id)
                    if linked is None or linked.status.value == "deleted":
                        continue
                    by_id[other_id] = linked
                graph_boost[other_id] = max(
                    graph_boost.get(other_id, 0.0), min(1.0, 0.6 * weight)
                )

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup(results: list[MemoryResult]) -> list[MemoryResult]:
        seen: dict[str, MemoryResult] = {}
        for result in results:
            key = result.memory.content.strip().lower()
            existing = seen.get(key)
            if existing is None or result.score > existing.score:
                seen[key] = result
        return list(seen.values())
