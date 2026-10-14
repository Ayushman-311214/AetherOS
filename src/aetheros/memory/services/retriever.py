"""
Hybrid, explainable retrieval engine (spec Phase 8 -- the heart of recall).

Pipeline (spec Phase 7/8): query -> structured candidate generation (SQL
filters) -> vector candidates over that pool -> graph expansion (entity +
memory-link) -> uniform constraint filtering -> multi-signal scoring ->
threshold -> dedup -> rank -> budgeted context selection. It is *hybrid*:
vectors are one signal over a SQL-filtered pool that is also expanded through
the knowledge graph and the memory-link graph, so a query like "how did we add
RSI to TradingView last time?" surfaces the linked episode/procedure, not merely
the most lexically similar sentence (Rule 5).

Three Phase-8 invariants are enforced here:

* **Filter isolation.** Scope, deletion, validity, age and confidence
  constraints are applied *uniformly* to every candidate -- structured, vector,
  or graph-expanded -- by one predicate (:meth:`_passes`). Graph/link expansion
  can therefore never smuggle in a candidate that the structured filters would
  have rejected.
* **Safe degradation.** An optional source that fails (e.g. the vector index is
  unreachable) is skipped and recorded in :attr:`RetrievalReport.degraded_sources`;
  recall quality drops but the call does not raise.
* **Honest budgeting.** ``limit`` (max memories), ``max_per_type``, ``max_age``,
  ``max_chars`` and ``max_tokens`` are enforced at final selection, and the
  report discloses how many candidates each stage dropped. Token counting is
  *conservative* (a character heuristic, not a model tokenizer).

Every returned memory carries a :class:`RetrievalExplanation` with its actual
component scores, provenance and reasons (Rule 6).
"""

from __future__ import annotations

import math
import re

from .._clock import utcnow
from ..config import MemoryConfig
from ..domain.enums import RECALLABLE_STATUSES
from ..domain.memory import Memory
from ..domain.query import MemoryQuery, MemoryResult, RetrievalReport
from ..graph.store import KnowledgeGraph
from ..storage.repository import MemoryRepository
from ..vector.index import VectorIndex
from .scorer import MemoryScorer

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Statuses visible to ordinary recall. Shared with the repository's SQL
# filter, the lifecycle and the projection checks (domain.enums) so every
# stage agrees on what "recallable" means. DECAYED stays recallable
# (deeply neglected but not yet archived -- its weak recency score
# naturally ranks it last); ARCHIVED/EXPIRED need include_archived;
# DELETED is never served.
_ACTIVE_STATUSES = frozenset(s.value for s in RECALLABLE_STATUSES)

# Context dimensions matched as hard equality filters (mirrors the repository's
# indexed context columns). A query context value under one of these keys must
# match the memory's metadata for every candidate source.
_CONTEXT_FILTER_KEYS = (
    "session_id",
    "task_id",
    "episode_id",
    "instrument_id",
    "user_id",
    "application",
)

# Conservative token heuristic. We deliberately *over*-estimate tokens relative
# to a real BPE tokenizer (~4 chars/token for English) by dividing by 3, so a
# ``max_tokens`` budget is never silently exceeded. This is NOT exact; the report
# flags ``token_count_exact=False``.
_CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    """Conservative (over-estimating) token count for a piece of context."""
    return math.ceil(len(text) / _CHARS_PER_TOKEN)


class MemoryRetriever:
    """Assemble ranked, explained, budgeted memories for a query."""

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
        """Back-compatible entry point: the ranked, budgeted results only."""
        return (await self.retrieve_report(query)).results

    async def retrieve_report(self, query: MemoryQuery) -> RetrievalReport:
        """Full retrieval with degradation and budget disclosure (spec Phase 8)."""
        report = RetrievalReport()

        # 1. Structured candidate generation (authoritative SQL filters).
        candidates = await self._repo.candidates(query)
        by_id: dict[str, Memory] = {}
        provenance: dict[str, set[str]] = {}
        for memory in candidates:
            by_id[memory.id] = memory
            provenance.setdefault(memory.id, set()).add("structured")

        graph_boost: dict[str, float] = {}

        # 2. Graph expansion -- entity neighbourhood + typed memory links. Each
        #    newly surfaced memory is tagged with provenance and a boost.
        if query.expand_hops > 0:
            try:
                await self._expand_via_entities(query, by_id, graph_boost, provenance)
            except Exception as exc:  # optional source: degrade, do not raise.
                report.degraded_sources.append(f"graph_entity:{type(exc).__name__}")
            try:
                await self._expand_via_links(candidates, by_id, graph_boost, provenance)
            except Exception as exc:
                report.degraded_sources.append(f"graph_link:{type(exc).__name__}")

        # 3. Uniform constraint filtering across EVERY source (filter isolation).
        #    A graph/link-expanded candidate must satisfy exactly the same scope,
        #    status, validity, age and confidence constraints as a structured one.
        filtered: dict[str, Memory] = {}
        for mid, memory in by_id.items():
            if self._passes(memory, query):
                filtered[mid] = memory
            else:
                report.dropped_by_filter += 1
        by_id = filtered
        report.candidates_considered = len(by_id)

        if not by_id:
            return report

        # 4. Semantic search over the filtered candidate pool (optional source).
        semantic: dict[str, float] = {}
        if query.text.strip():
            try:
                hits = await self._vectors.search(
                    query.text,
                    limit=len(by_id),
                    candidate_ids=list(by_id.keys()),
                )
                semantic = {mid: score for mid, score in hits}
                for mid in semantic:
                    provenance.setdefault(mid, set()).add("vector")
            except Exception as exc:  # vector index down -> lexical/graph only.
                report.degraded_sources.append(f"vector:{type(exc).__name__}")

        # 5-6. Score, threshold.
        query_tokens = set(_TOKEN_RE.findall(query.text.lower()))
        threshold = max(query.min_similarity, self._config.similarity_threshold)
        scored: list[MemoryResult] = []
        for mid, memory in by_id.items():
            exp = self._scorer.score(
                query,
                memory,
                semantic=semantic.get(mid, 0.0),
                graph_boost=graph_boost.get(mid, 0.0),
                query_tokens=query_tokens,
            )
            exp.sources = sorted(provenance.get(mid, set()))
            if exp.score < threshold:
                report.dropped_by_threshold += 1
                continue
            scored.append(MemoryResult(memory=memory, explanation=exp))

        # 7. Dedup near-identical content, keeping the higher score.
        scored = self._dedup(scored)

        # 8. Rank, then budgeted selection (limit / per-type / char / token).
        scored.sort(key=lambda r: r.score, reverse=True)
        report.results, report.dropped_by_budget = self._apply_budget(scored, query)
        report.token_count_exact = False
        return report

    # ------------------------------------------------------------------
    # Uniform constraint predicate (filter isolation)
    # ------------------------------------------------------------------

    def _passes(self, memory: Memory, query: MemoryQuery) -> bool:
        """Every constraint the structured SQL applies, checked in-memory.

        Applied to candidates from *all* sources so graph/link expansion cannot
        bypass scope, deletion, validity, age or confidence constraints.
        """
        status = memory.status.value
        if query.include_archived:
            if status == "deleted":
                return False
        elif status not in _ACTIVE_STATUSES:
            return False

        if query.memory_types and memory.memory_type not in query.memory_types:
            return False
        if query.veracities and memory.veracity not in query.veracities:
            return False
        if query.min_confidence > 0 and memory.confidence < query.min_confidence:
            return False

        for key in _CONTEXT_FILTER_KEYS:
            want = query.context.get(key)
            if want is not None and memory.metadata.get(key) != want:
                return False

        if query.tags:
            wanted = {t.strip().lower() for t in query.tags}
            have = {t.strip().lower() for t in memory.tags}
            if not (wanted & have):
                return False

        if query.max_age_days > 0:
            age_days = (utcnow() - memory.created_at).total_seconds() / 86400.0
            if age_days > query.max_age_days:
                return False

        return True

    # ------------------------------------------------------------------
    # Budgeted context selection
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_budget(
        ranked: list[MemoryResult], query: MemoryQuery
    ) -> tuple[list[MemoryResult], int]:
        """Greedily take the top memories honouring every budget bound.

        Bounds: ``limit`` (max memories), ``max_per_type``, ``max_chars`` and
        ``max_tokens`` (conservative). A memory that would overflow a bound is
        skipped (not truncated), so each returned memory is whole. Returns the
        selected results and the count dropped purely by the budget.
        """
        selected: list[MemoryResult] = []
        per_type: dict[str, int] = {}
        used_chars = 0
        used_tokens = 0
        dropped = 0
        for result in ranked:
            if len(selected) >= query.limit:
                dropped += 1
                continue

            mtype = result.memory.memory_type.value
            if query.max_per_type and per_type.get(mtype, 0) >= query.max_per_type:
                dropped += 1
                continue

            content = result.memory.content
            chars = len(content)
            tokens = estimate_tokens(content)
            if query.max_chars and used_chars + chars > query.max_chars:
                dropped += 1
                continue
            if query.max_tokens and used_tokens + tokens > query.max_tokens:
                dropped += 1
                continue

            selected.append(result)
            per_type[mtype] = per_type.get(mtype, 0) + 1
            used_chars += chars
            used_tokens += tokens

        return selected, dropped

    # ------------------------------------------------------------------
    # Graph expansion
    # ------------------------------------------------------------------

    async def _expand_via_entities(
        self,
        query: MemoryQuery,
        by_id: dict[str, Memory],
        graph_boost: dict[str, float],
        provenance: dict[str, set[str]],
    ) -> None:
        """Memories referencing the query's entities (and their graph neighbours).

        The probe inherits the query's hard filters (type, veracity, confidence,
        context, archived, candidate_limit) and overrides only the entity set, so
        expansion never widens the structured constraint surface.
        """
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
            memory_types=list(query.memory_types),
            veracities=list(query.veracities),
            tags=list(query.tags),
            context=dict(query.context),
            min_confidence=query.min_confidence,
            include_archived=query.include_archived,
            candidate_limit=query.candidate_limit,
            expand_hops=0,
        )
        for memory in await self._repo.candidates(probe):
            if memory.id not in by_id:
                by_id[memory.id] = memory
            provenance.setdefault(memory.id, set()).add("graph_entity")
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
        provenance: dict[str, set[str]],
    ) -> None:
        """Memories joined to a candidate by a typed memory_link (e.g. recovery).

        Linked memories are added to the pool with provenance; the uniform
        :meth:`_passes` filter (run after expansion) then enforces scope/validity
        so a link cannot smuggle in a filtered-out memory.
        """
        for memory in candidates[:10]:
            for other_id, _link_type, weight in await self._repo.linked_ids(memory.id):
                if other_id not in by_id:
                    linked = await self._repo.get(other_id)
                    if linked is None:
                        continue
                    by_id[other_id] = linked
                provenance.setdefault(other_id, set()).add("graph_link")
                graph_boost[other_id] = max(
                    graph_boost.get(other_id, 0.0), min(1.0, 0.6 * weight)
                )

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup(results: list[MemoryResult]) -> list[MemoryResult]:
        """Collapse identical content, keeping the higher score and merging
        provenance so an explanation still shows every source that found it."""
        seen: dict[str, MemoryResult] = {}
        for result in results:
            key = result.memory.content.strip().lower()
            existing = seen.get(key)
            if existing is None:
                seen[key] = result
                continue
            merged = sorted(
                set(existing.explanation.sources) | set(result.explanation.sources)
            )
            winner = result if result.score > existing.score else existing
            winner.explanation.sources = merged
            seen[key] = winner
        return list(seen.values())
