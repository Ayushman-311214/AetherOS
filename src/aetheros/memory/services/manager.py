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
from ..domain.query import MemoryQuery, MemoryResult
from ..domain.trading import PredictionMemory, PredictionOutcomeMemory
from ..embeddings import build_embedding_provider
from ..events import MemoryForgotten, MemoryRetrieved
from ..graph.store import KnowledgeGraph
from ..storage.database import SQLiteDatabase
from ..storage.repository import MemoryRepository
from ..vector.index import VectorIndex
from .consolidator import MemoryConsolidator
from .lifecycle import MemoryLifecycle
from .policy import MemoryPolicyEngine
from .retriever import MemoryRetriever
from .scorer import MemoryScorer
from .validator import MemoryValidator
from .working_memory import WorkingMemory
from .writer import MemoryWriter
from ...core.logging import get_logger

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
        self._working = WorkingMemory(capacity=config.max_working_context)

        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        if self._started:
            return
        await asyncio.to_thread(self._db.connect)
        self._started = True
        logger.bind(
            db=str(self._config.database_path),
            embedder=self._embedder.name,
        ).info("Memory subsystem initialized.")

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
        """Persist a pre-built Memory, honouring the retention policy."""
        if not self._policy.should_remember(memory):
            logger.bind(memory_type=memory.memory_type.value).debug(
                "Policy declined to remember a trivial memory."
            )
            return memory
        return await self._writer.write(memory)

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
        record_access: bool = True,
    ) -> list[MemoryResult]:
        """Hybrid, explainable retrieval (spec Phase 7)."""
        q = query or MemoryQuery(
            text=text,
            limit=limit or self._config.retrieval_limit,
            memory_types=memory_types or [],
            tags=tags or [],
            entities=entities or [],
            context=context or {},
            min_confidence=min_confidence,
        )
        results = await self._retriever.retrieve(q)

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
        return results

    async def search(self, text: str, *, limit: int = 5) -> list[MemoryResult]:
        """Convenience alias for a plain semantic+lexical search."""
        return await self.retrieve(text, limit=limit)

    async def update(self, memory_id: str, **changes: Any) -> Memory:
        """
        Edit a stored memory (spec Phase 4 -- MemoryUpdater).

        Supported fields: content, confidence, importance, status, tags,
        entities, data, metadata. The version is bumped and the vector
        re-indexed by the writer.
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
        return await self._writer.update(memory)

    async def forget(self, memory_id: str, *, hard: bool = False) -> bool:
        """
        Forget a memory (spec Phase 15 -- user control).

        Soft by default: the memory is marked DELETED so it stops being
        retrieved but remains for audit. ``hard=True`` removes the row and its
        vector irreversibly -- used only on an explicit user request.
        """
        memory = await self._repo.get(memory_id)
        if memory is None:
            return False

        if hard:
            await self._vectors.delete(memory_id)
            await self._repo.delete(memory_id)
        else:
            memory.status = MemoryStatus.DELETED
            await self._repo.update(memory)

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
        self, *, min_importance: MemoryImportance = MemoryImportance.HIGH
    ) -> list[Memory]:
        """Persist keep-worthy working-memory items into long-term memory."""
        promoted: list[Memory] = []
        for memory in self._working.to_memories(min_importance=min_importance):
            promoted.append(await self.remember_memory(memory))
        return promoted

    # ------------------------------------------------------------------
    # Maintenance (spec Phases 12, 14)
    # ------------------------------------------------------------------

    async def consolidate(self) -> dict[str, int]:
        return await self._consolidator.consolidate()

    async def decay(self) -> dict[str, int]:
        return await self._lifecycle.decay_pass(self._repo)

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

    async def stats(self) -> dict[str, Any]:
        return {
            "enabled": self._config.enabled,
            "total": await self._repo.count(),
            "by_type": await self._repo.type_distribution(),
            "vectors": await self._vectors.count(),
            "graph": await self._graph.stats(),
            "working": len(self._working),
            "embedder": self._embedder.name,
            "embedding_dim": self._embedder.dimension,
            "schema_version": await asyncio.to_thread(self._db.schema_version),
        }

    async def clear(self) -> None:
        """Wipe all persisted memory (explicit user action / tests)."""
        await self._repo.clear()
        self._working.clear()
