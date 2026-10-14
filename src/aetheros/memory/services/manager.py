"""
MemoryManager -- the high-level memory API (spec Phase 4).

The one object the rest of AetherOS talks to. It composes the storage,
embedding/vector, graph, scoring, policy, writer, retriever, consolidator,
lifecycle and working-memory pieces behind a small verb surface
(remember / retrieve / search / update / forget / link / get) plus typed
helpers for episodes, preferences, failures, procedures and trading history.
Nothing above this layer needs to know SQLite, vectors or networkx exist.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from ...core.errors.memory_error import MemoryError
from ...core.logging import get_logger
from ..config import MemoryConfig
from ..domain.enums import (
    MemoryImportance,
    MemoryStatus,
    MemoryType,
    SourceType,
    Veracity,
)
from ..domain.episode import Episode
from ..domain.memory import Memory, MemorySource
from ..domain.preference import FailureRecord, Preference
from ..domain.procedure import Procedure
from ..domain.query import MemoryQuery, MemoryResult, RetrievalReport
from ..domain.trading import PredictionMemory, PredictionOutcomeMemory
from ..embeddings import HashingEmbeddingProvider, build_embedding_provider
from ..events import MemoryForgotten, MemoryRetrieved
from ..graph.store import KnowledgeGraph
from ..storage.database import SQLiteDatabase
from ..storage.repository import MemoryRepository
from ..vector.index import VectorIndex
from .confidence import ConfidenceUpdater
from .consolidator import MemoryConsolidator
from .controls import UserControls
from .episodes import EpisodeRecorder
from .failures import FailureRecorder
from .ingestion import DocumentIngestion
from .lifecycle import MemoryLifecycle
from .policy import MemoryPolicyEngine
from .results import WriteResult
from .retriever import MemoryRetriever
from .scorer import MemoryScorer
from .trading_history import TradingHistoryAdapter
from .validator import MemoryValidator
from .working_memory import WorkingMemory
from .writer import MemoryWriter

logger = get_logger("memory.manager")


class MemoryManager:
    """Compose the memory subsystem and expose its high-level API."""

    def __init__(self, config: MemoryConfig, *, event_bus=None) -> None:
        self._config = config
        self._bus = event_bus

        self._db = SQLiteDatabase(config.database_path)
        self._repo = MemoryRepository(self._db)
        self._embedder = build_embedding_provider(config)
        self._vectors = VectorIndex(self._db, self._embedder)
        self._graph = KnowledgeGraph(self._db)
        self._scorer = MemoryScorer(config)
        self._policy = MemoryPolicyEngine()
        self._validator = MemoryValidator()
        self._writer = MemoryWriter(
            self._repo,
            self._vectors,
            self._graph,
            validator=self._validator,
            policy=self._policy,
            event_bus=event_bus,
        )
        self._retriever = MemoryRetriever(
            self._repo, self._vectors, self._graph, self._scorer, config
        )
        self._consolidator = MemoryConsolidator(
            self._repo, self._db, config, event_bus=event_bus
        )
        self._lifecycle = MemoryLifecycle(config)
        self._working = WorkingMemory(
            capacity=config.max_working_context,
            default_ttl_seconds=config.working_ttl_seconds,
        )
        self._episodes = EpisodeRecorder(
            self, self._repo, max_actions=config.episode_max_actions
        )
        self._failures = FailureRecorder(self, self._repo)
        self._confidence = ConfidenceUpdater(self)
        self._controls = UserControls(self)
        self._trading_history = TradingHistoryAdapter(self, self._repo)
        self._documents = DocumentIngestion(self)

        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        if self._started:
            return
        await asyncio.to_thread(self._db.connect)
        await self._ensure_embedder_ready()
        await self._check_embedding_identity()
        self._started = True
        logger.bind(
            db=str(self._config.database_path),
            embedder=self._embedder.name,
        ).info("Memory subsystem initialized.")

    async def _ensure_embedder_ready(self) -> None:
        """
        Validate a real embedder for real before serving traffic.

        A provider exposing ``ensure_ready`` (the Ollama provider) must prove the
        daemon is reachable, the model exists, it can actually embed, and the
        dimension is stable. If that fails we honour the configured policy:
        strict (default) raises and fails startup -- never silently degrade a
        requested real provider to lexical hashing; opt-in degrade
        (MEMORY_EMBEDDING_FALLBACK) swaps to the hashing embedder *loudly*.
        """
        ensure = getattr(self._embedder, "ensure_ready", None)
        if ensure is None:
            return
        try:
            dim = await ensure()
            logger.bind(embedder=self._embedder.name, dimension=dim).info(
                "Real embedding provider validated."
            )
        except Exception as exc:
            if not self._config.embedding_fallback_to_hashing:
                raise
            logger.bind(embedder=self._embedder.name, error=str(exc)).warning(
                "Embedding provider '%s' is unavailable; MEMORY_EMBEDDING_FALLBACK "
                "is on, degrading to the hashing embedder. Retrieval is "
                "lexical-grade, NOT semantic.",
                self._embedder.name,
            )
            self._embedder = HashingEmbeddingProvider(dimension=self._config.embedding_dim)
            self._vectors = VectorIndex(self._db, self._embedder)
            self._writer._vectors = self._vectors
            self._retriever._vectors = self._vectors

    async def _check_embedding_identity(self) -> None:
        """
        Warn loudly if the index holds vectors from a *different* embedding space.

        An equal dimension does not make two models compatible, so search already
        filters to the active identity (vector index §4.4). Vectors under a
        foreign identity are unsearchable now and need an explicit rebuild
        (`reembed_all`) -- surface that rather than letting recall silently miss.
        """
        try:
            identities = await self._vectors.identities()
        except Exception:  # pragma: no cover - defensive, never block startup
            return
        active = self._embedder.name
        foreign = {name: n for name, n in identities.items() if name and name != active}
        if foreign:
            logger.bind(active=active, foreign=foreign).warning(
                "Vector index holds %d embedding(s) from other spaces (%s) that "
                "are unsearchable under '%s'. Run `reembed_all()` to migrate, or "
                "point MEMORY_* back at the original embedder.",
                sum(foreign.values()),
                ", ".join(sorted(foreign)),
                active,
            )

    async def shutdown(self) -> None:
        if not self._started:
            return
        await asyncio.to_thread(self._db.close)
        self._started = False
        logger.info("Memory subsystem shut down.")

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._db.schema_version)
            return self._db.is_connected
        except Exception:  # pragma: no cover - defensive
            return False

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def working(self) -> WorkingMemory:
        return self._working

    @property
    def episodes(self) -> EpisodeRecorder:
        """Explicit episode lifecycle (Phase 10 -- start/append/finalize)."""
        return self._episodes

    @property
    def failures(self) -> FailureRecorder:
        """Explicit failure/recovery lifecycle (Phase 11)."""
        return self._failures

    @property
    def confidence(self) -> ConfidenceUpdater:
        """Documented confidence updates (Phase 13)."""
        return self._confidence

    @property
    def controls(self) -> UserControls:
        """Scope-enforced user administration (Phase 15)."""
        return self._controls

    @property
    def trading_history(self) -> TradingHistoryAdapter:
        """Trading-history ingestion + as-of retrieval (Phase 16)."""
        return self._trading_history

    @property
    def documents(self) -> DocumentIngestion:
        """Document/knowledge ingestion + source administration (Phase 17)."""
        return self._documents

    @property
    def graph(self) -> KnowledgeGraph:
        return self._graph

    @property
    def config(self) -> MemoryConfig:
        return self._config

    # ------------------------------------------------------------------
    # Core verbs
    # ------------------------------------------------------------------

    async def remember(
        self,
        content: str,
        *,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        veracity: Veracity = Veracity.OBSERVATION,
        source_type: SourceType = SourceType.SYSTEM,
        origin: str = "memory",
        confidence: float = 0.6,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Create and persist a memory from primitive fields (spec Phase 4)."""
        memory = Memory(
            content=content,
            memory_type=memory_type,
            veracity=veracity,
            source=MemorySource(source_type=source_type, origin=origin),
            confidence=confidence,
            importance=importance,
            tags=tags or [],
            entities=entities or [],
            data=data or {},
            metadata=metadata or {},
        )
        return await self.remember_memory(memory)

    async def remember_memory(self, memory: Memory) -> Memory:
        """Persist a pre-built Memory, honouring the retention policy.

        Legacy verb: returns the :class:`Memory` and raises on storage failure.
        A returned object is **not** proof of persistence -- a policy decline
        returns the unsaved object unchanged. Callers needing an explicit,
        five-state outcome should use :meth:`store` instead.
        """
        if not self._config.enabled:
            # Disabled mode: never raise, never pretend to persist (Rule:
            # "Never return success for a write that did not persist.").
            logger.debug("Memory disabled; remember_memory is a no-op.")
            return memory
        if not self._policy.should_remember(memory):
            logger.bind(memory_type=memory.memory_type.value).debug(
                "Policy declined to remember a trivial memory."
            )
            return memory
        return await self._writer.write(memory)

    async def store(
        self, memory: Memory, *, idempotency_key: str | None = None
    ) -> WriteResult:
        """Durable write with an explicit, truthful outcome (spec Phase 4).

        Distinguishes STORED / SKIPPED (policy or idempotent hit) / FAILED /
        UNAVAILABLE. An ``idempotency_key`` (deduplicated via the memory id, or a
        caller-supplied key stamped into metadata) makes a retried write a safe
        no-op rather than a duplicate row.
        """
        if not self._config.enabled:
            return WriteResult.unavailable("Memory subsystem is disabled.")
        if not self._started:
            return WriteResult.unavailable("Memory subsystem is not initialized.")

        # Idempotency: an id (or explicit key) already present => skip, don't dupe.
        if idempotency_key is not None:
            memory.metadata.setdefault("idempotency_key", idempotency_key)
            existing = await self._repo.find_by_metadata(
                "idempotency_key", idempotency_key
            )
            if existing:
                return WriteResult.skipped(existing[0], "idempotency_key already stored")
        if await self._repo.exists(memory.id):
            current = await self._repo.get(memory.id)
            return WriteResult.skipped(current or memory, "memory id already stored")

        if not self._policy.should_remember(memory):
            return WriteResult.skipped(memory, "declined by retention policy")

        try:
            stored = await self._writer.write(memory)
        except Exception as exc:  # storage/embedding failure -- report, don't hide
            logger.bind(error=str(exc)).warning("Durable memory write failed.")
            return WriteResult.failed(str(exc), memory=memory)
        return WriteResult.stored(stored)

    async def get(self, memory_id: str) -> Memory | None:
        return await self._repo.get(memory_id)

    async def retrieve(
        self,
        text: str = "",
        *,
        query: MemoryQuery | None = None,
        limit: int | None = None,
        memory_types: list[MemoryType] | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        context: dict[str, Any] | None = None,
        min_confidence: float = 0.0,
        max_tokens: int = 0,
        max_chars: int = 0,
        max_per_type: int = 0,
        max_age_days: float = 0.0,
        record_access: bool = True,
    ) -> list[MemoryResult]:
        """Hybrid, explainable retrieval (spec Phase 8)."""
        report = await self.retrieve_report(
            text,
            query=query,
            limit=limit,
            memory_types=memory_types,
            tags=tags,
            entities=entities,
            context=context,
            min_confidence=min_confidence,
            max_tokens=max_tokens,
            max_chars=max_chars,
            max_per_type=max_per_type,
            max_age_days=max_age_days,
            record_access=record_access,
        )
        return report.results

    async def retrieve_report(
        self,
        text: str = "",
        *,
        query: MemoryQuery | None = None,
        limit: int | None = None,
        memory_types: list[MemoryType] | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        context: dict[str, Any] | None = None,
        min_confidence: float = 0.0,
        max_tokens: int = 0,
        max_chars: int = 0,
        max_per_type: int = 0,
        max_age_days: float = 0.0,
        record_access: bool = True,
    ) -> RetrievalReport:
        """Full retrieval with degradation + budget disclosure (spec Phase 8)."""
        if not self._config.enabled or not self._started:
            # Optional recall degrades safely when the subsystem is off.
            return RetrievalReport(degraded_sources=["subsystem_unavailable"])
        q = query or MemoryQuery(
            text=text,
            limit=limit or self._config.retrieval_limit,
            memory_types=memory_types or [],
            tags=tags or [],
            entities=entities or [],
            context=context or {},
            min_confidence=min_confidence,
            max_tokens=max_tokens,
            max_chars=max_chars,
            max_per_type=max_per_type,
            max_age_days=max_age_days,
        )
        report = await self._retriever.retrieve_report(q)
        results = report.results

        if record_access:
            for result in results:
                await self._repo.record_access(
                    result.memory.id, context={"query": q.text}
                )

        if self._bus is not None:
            await self._bus.publish(
                MemoryRetrieved(
                    query=q.text,
                    result_count=len(results),
                    top_score=results[0].score if results else 0.0,
                )
            )
        return report

    async def search(self, text: str, *, limit: int = 5) -> list[MemoryResult]:
        """Convenience alias for a plain semantic+lexical search."""
        return await self.retrieve(text, limit=limit)

    async def update(
        self, memory_id: str, *, expected_version: int | None = None, **changes: Any
    ) -> Memory:
        """
        Edit a stored memory (spec Phase 4 -- MemoryUpdater).

        Supported fields: content, confidence, importance, status, tags,
        entities, data, metadata. The version is bumped and the vector
        re-indexed.

        Pass ``expected_version`` for an optimistic-concurrency guard: the write
        is applied only if the stored row is still at that version, else a
        :class:`MemoryConflictError` is raised (a lost race -- re-read and retry).
        Without it the last writer wins, preserving the historical behaviour.
        """
        memory = await self._repo.get(memory_id)
        if memory is None:
            from ...core.errors.memory_error import MemoryNotFoundError

            raise MemoryNotFoundError(f"No memory with id {memory_id!r}.")

        if "content" in changes:
            memory.content = str(changes["content"])
        if "confidence" in changes:
            memory.confidence = max(0.0, min(1.0, float(changes["confidence"])))
        if "importance" in changes:
            memory.importance = MemoryImportance(int(changes["importance"]))
        if "status" in changes:
            memory.status = MemoryStatus(changes["status"])
        if "tags" in changes:
            memory.tags = list(changes["tags"])
        if "entities" in changes:
            memory.entities = list(changes["entities"])
        if "data" in changes:
            memory.data.update(dict(changes["data"]))
        if "metadata" in changes:
            memory.metadata.update(dict(changes["metadata"]))

        from .._clock import utcnow

        memory.updated_at = utcnow()

        if expected_version is None:
            return await self._writer.update(memory)

        return await self._update_guarded(memory, expected_version)

    async def _update_guarded(self, memory: Memory, expected_version: int) -> Memory:
        """Validate, version-guard the DB write, then re-index. Raises on a race."""
        from ...core.errors.memory_error import MemoryConflictError

        self._validator.validate(memory)
        memory.version += 1
        won = await self._repo.update_guarded(memory, expected_version)
        if not won:
            raise MemoryConflictError(
                f"Memory {memory.id!r} changed since version {expected_version}; "
                "update rejected.",
                hint="Re-read the memory and reapply your change.",
            )
        await self._writer.reindex(memory)
        await self._writer._publish(memory)
        return memory

    async def forget(self, memory_id: str, *, hard: bool = False) -> bool:
        """
        Forget a memory (spec Phase 15 -- user control).

        Soft by default: the memory is marked DELETED so it stops being
        retrieved but remains for audit, and its vector is deleted up front
        so exclusion is immediate even if a downstream filter were bypassed
        (defense in depth -- recall already filters DELETED authoritatively).
        ``hard=True`` is coordinated erasure: the row, its vector, every
        link touching it (both directions), and every graph evidence
        pointer to it are removed irreversibly -- used only on an explicit
        user request. Soft deletion alone is not erasure (spec Phase 14/15):
        backups, if any, are deployment policy outside this contract.
        """
        memory = await self._repo.get(memory_id)
        if memory is None:
            return False

        if hard:
            await self._vectors.delete(memory_id)
            await self._repo.delete_links(memory_id)
            await self._graph.scrub_memory(memory_id)
            await self._repo.delete(memory_id)
        else:
            memory.status = MemoryStatus.DELETED
            await self._repo.update(memory)
            # Immediate exclusion: drop the vector now rather than waiting
            # for a repair sweep (the FK cascade on update usually does
            # this already; the explicit delete makes it certain). Never
            # fails the forget: a missing vector is fine.
            try:
                await self._vectors.delete(memory_id)
            except Exception as exc:
                logger.bind(memory_id=memory_id, error=str(exc)).debug(
                    "Vector delete on soft-forget skipped."
                )

        if self._bus is not None:
            await self._bus.publish(MemoryForgotten(memory_id=memory_id, hard=hard))
        return True

    async def link(
        self,
        from_id: str,
        to_id: str,
        *,
        link_type: str = "related_to",
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a typed memory-to-memory link (spec Phase 4 -- link)."""
        await self._repo.add_link(
            {
                "id": uuid.uuid4().hex,
                "from_id": from_id,
                "to_id": to_id,
                "link_type": link_type,
                "weight": weight,
                "metadata": metadata or {},
            }
        )

    # ------------------------------------------------------------------
    # Typed helpers (spec Phases 9, 10, 11, 16)
    # ------------------------------------------------------------------

    async def remember_episode(self, episode: Episode) -> Memory:
        return await self.remember_memory(episode.to_memory())

    async def remember_preference(self, preference: Preference) -> Memory:
        return await self.remember_memory(preference.to_memory())

    async def remember_failure(self, failure: FailureRecord) -> Memory:
        return await self.remember_memory(failure.to_memory())

    async def remember_procedure(self, procedure: Procedure) -> Memory:
        return await self.remember_memory(procedure.to_memory())

    async def remember_prediction(self, prediction: PredictionMemory) -> Memory:
        """Store a produced prediction as immutable trading history (Phase 16)."""
        return await self.remember_memory(prediction.to_memory())

    async def remember_prediction_outcome(
        self, outcome: PredictionOutcomeMemory
    ) -> Memory:
        """
        Store a realised outcome and link it to its prediction (Phase 16).

        The original prediction is never modified (Rule 4); the outcome is a
        separate record joined by a ``has_outcome`` link.
        """
        memory = await self.remember_memory(outcome.to_memory())
        if await self._repo.exists(outcome.prediction_id):
            await self.link(
                outcome.prediction_id,
                memory.id,
                link_type="has_outcome",
            )
        return memory

    async def promote_working(
        self,
        *,
        min_importance: MemoryImportance = MemoryImportance.HIGH,
        session_id: str | None = None,
        only_evidence: bool = False,
    ) -> list[Memory]:
        """Persist keep-worthy working-memory items into long-term memory.

        With ``only_evidence=True`` only items explicitly marked as evidence are
        promoted (explicit selection for durable formation). A no-op when the
        subsystem is disabled -- ``remember_memory`` will not persist.
        """
        if not self._config.enabled:
            return []
        promoted: list[Memory] = []
        candidates = self._working.to_memories(
            min_importance=min_importance,
            session_id=session_id,
            only_evidence=only_evidence,
        )
        for memory in candidates:
            promoted.append(await self.remember_memory(memory))
        return promoted

    # ------------------------------------------------------------------
    # Maintenance (spec Phases 12, 14)
    # ------------------------------------------------------------------

    async def consolidate(
        self, *, batch_size: int = 500, max_batches: int = 0
    ) -> dict[str, int]:
        """Bounded, restartable, idempotent consolidation (spec Phase 12)."""
        return await self._consolidator.consolidate(
            batch_size=batch_size, max_batches=max_batches
        )

    async def decay(
        self,
        *,
        now=None,
        batch_size: int = 500,
        max_batches: int = 0,
    ) -> dict[str, int]:
        """Bounded, restartable, idempotent decay pass (spec Phase 14)."""
        return await self._lifecycle.decay_pass(
            self._repo,
            self._vectors,
            now=now,
            batch_size=batch_size,
            max_batches=max_batches,
        )

    async def reactivate(self, memory_id: str) -> Memory:
        """Return an ARCHIVED/EXPIRED/STALE/DECAYED/LOW_CONFIDENCE row to ACTIVE.

        Explicit reactivation for rows that evaluation alone will not
        restore (ARCHIVED/EXPIRED have no recency path back). The vector
        projection is rebuilt so recall serves the row again. Refuses
        DELETED rows (explicit user restore territory) and missing ids.
        STALE/DECAYED rows normally reactivate automatically on next access
        (fresh recency re-evaluates to ACTIVE); this verb is for when an
        operator wants it now.
        """
        from ...core.errors.memory_error import (
            MemoryNotFoundError,
            MemoryValidationError,
        )

        memory = await self._repo.get(memory_id)
        if memory is None:
            raise MemoryNotFoundError(f"No memory with id {memory_id!r}.")
        if memory.status is MemoryStatus.DELETED:
            raise MemoryValidationError(
                f"Memory {memory_id!r} is soft-deleted; lifecycle reactivation "
                "does not restore user-deleted rows.",
                hint="Restore it through the user-controls path instead.",
            )
        if memory.status is MemoryStatus.ACTIVE:
            return memory
        from .._clock import utcnow

        memory.status = MemoryStatus.ACTIVE
        memory.updated_at = utcnow()
        updated = await self._writer.update(memory)
        return updated

    # ------------------------------------------------------------------
    # Graph passthroughs (spec Phase 6)
    # ------------------------------------------------------------------

    async def related_entities(self, name: str, *, max_hops: int = 2):
        return await self._graph.find_related_entities(name, max_hops=max_hops)

    async def find_path(self, source: str, target: str):
        return await self._graph.find_path(source, target)

    # ------------------------------------------------------------------
    # Observability (spec Phase 22)
    # ------------------------------------------------------------------

    async def verify_projection(self) -> dict[str, Any]:
        """Report vector-projection drift vs the authoritative store (Phase 4)."""
        return await self._writer.verify_projection()

    async def repair_projection(self) -> dict[str, int]:
        """Rebuild the vector projection to match the authoritative store (Phase 4)."""
        return await self._writer.repair_projection()

    async def embedding_identities(self) -> dict[str, int]:
        """Stored vector counts grouped by embedding-space identity (Phase 5)."""
        return await self._vectors.identities()

    async def reembed_all(self) -> dict[str, int]:
        """
        Re-embed every live memory under the *active* embedder (Phase 5 migration).

        The explicit, authorized path for an incompatible embedding-space change
        (new provider/model/dimension). It drops the old vectors and rebuilds the
        projection from the authoritative store, so the index ends up wholly in
        the active identity -- never a silent mix. Returns the counts.
        """
        if not self._started:
            raise MemoryError(message="Memory subsystem is not initialized.")
        live = await self._repo.iter_all(include_deleted=False)
        reembedded = 0
        for memory in live:
            await self._vectors.delete(memory.id)
            await self._writer.reindex(memory)
            reembedded += 1
        # Drop any remaining foreign/orphan vectors so the space is uniform.
        removed = 0
        live_ids = {m.id for m in live}
        for vector_id in await self._vectors.ids():
            if vector_id not in live_ids:
                await self._vectors.delete(vector_id)
                removed += 1
        logger.bind(embedder=self._embedder.name, reembedded=reembedded).info(
            "Re-embedded all memories under the active embedding space."
        )
        return {"reembedded": reembedded, "removed": removed}

    async def stats(self) -> dict[str, Any]:
        return {
            "enabled": self._config.enabled,
            "total": await self._repo.count(),
            "by_type": await self._repo.type_distribution(),
            "vectors": await self._vectors.count(),
            "graph": await self._graph.stats(),
            "working": len(self._working),
            "embedder": self._embedder.name,
            "embedding_dim": self._embedding_dim_or_none(),
            "schema_version": await asyncio.to_thread(self._db.schema_version),
        }

    def _embedding_dim_or_none(self) -> int | None:
        """Dimension if known; ``None`` for a real provider not yet probed."""
        try:
            return self._embedder.dimension
        except Exception:
            return None

    async def clear(self) -> None:
        """Wipe all persisted memory (explicit user action / tests)."""
        await self._repo.clear()
        self._working.clear()
