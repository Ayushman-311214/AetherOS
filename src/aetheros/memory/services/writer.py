"""
Memory writer (spec Phase 4 -- MemoryWriter).

The single create/update path. It validates (epistemic rules), applies retention
policy, persists the row, indexes the vector, and reflects any referenced
entities into the knowledge graph -- then announces the write on the event bus.
Centralising this is what keeps "every memory is validated, scoped, embedded and
graphed" true no matter which caller (a tool, the agent, the trading
integration) produced it.
"""

from __future__ import annotations

from typing import Any

from ..domain.enums import RelationType
from ..domain.memory import Memory
from ..domain.semantic import Entity, Relationship
from ..events import MemoryStored
from ..graph.store import KnowledgeGraph
from ..storage.repository import MemoryRepository
from ..vector.index import VectorIndex
from .policy import MemoryPolicyEngine
from .validator import MemoryValidator


class MemoryWriter:
    """Validate, scope, persist, embed and graph a memory."""

    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: VectorIndex,
        graph: KnowledgeGraph,
        *,
        validator: MemoryValidator | None = None,
        policy: MemoryPolicyEngine | None = None,
        event_bus=None,
    ) -> None:
        self._repo = repository
        self._vectors = vector_index
        self._graph = graph
        self._validator = validator or MemoryValidator()
        self._policy = policy or MemoryPolicyEngine()
        self._bus = event_bus

    async def write(self, memory: Memory, *, apply_policy: bool = True) -> Memory:
        self._validator.validate(memory)
        if apply_policy:
            self._policy.apply(memory)

        await self._repo.add(memory)
        await self._vectors.index(memory.id, self._embedding_text(memory))
        await self._reflect_entities(memory)

        await self._publish(memory)
        return memory

    async def update(self, memory: Memory) -> Memory:
        """Persist an edited memory and re-index its vector."""
        self._validator.validate(memory)
        memory.version += 1
        await self._repo.update(memory)
        await self._vectors.index(memory.id, self._embedding_text(memory))
        await self._publish(memory)
        return memory

    # ------------------------------------------------------------------
    # Projection consistency / repair (spec Phase 4 -- "establish the
    # consistency and repair seam for later vector/graph projections")
    # ------------------------------------------------------------------

    async def reindex(self, memory: Memory) -> None:
        """Rebuild the vector projection for one memory from the authoritative row.

        Structured storage is the source of truth; the vector index is a
        derived projection. This recomputes that projection without touching the
        authoritative row -- the primitive used by projection repair.
        """
        await self._vectors.index(memory.id, self._embedding_text(memory))

    async def verify_projection(self) -> dict[str, Any]:
        """Report drift between the authoritative store and the vector projection.

        Does not pretend a distributed transaction exists: it compares the two
        independent stores and returns what repair would do. ``missing`` =
        recallable memories with no vector; ``orphan`` = vectors whose memory
        is gone, soft-deleted, archived or expired (which must not leak
        through recall). Only recallable statuses require vectors (spec
        Phase 14 -- the lifecycle deletes vectors when rows leave recall).
        """
        from ..domain.enums import RECALLABLE_STATUSES

        live = await self._repo.iter_all(include_deleted=False)
        needy_ids = {m.id for m in live if m.status in RECALLABLE_STATUSES}
        vector_ids = set(await self._vectors.ids())
        missing = sorted(needy_ids - vector_ids)
        orphan = sorted(vector_ids - needy_ids)
        return {
            "memories": len(needy_ids),
            "vectors": len(vector_ids),
            "missing": missing,
            "orphan": orphan,
            "consistent": not missing and not orphan,
        }

    async def repair_projection(self) -> dict[str, int]:
        """Make the vector projection consistent with the authoritative store.

        Re-embeds every recallable memory missing a vector and deletes vectors
        whose memory is gone, soft-deleted, archived or expired. Idempotent:
        a second run reports zeros.
        """
        report = await self.verify_projection()
        by_id = {m.id: m for m in await self._repo.iter_all(include_deleted=False)}
        reindexed = 0
        for memory_id in report["missing"]:
            memory = by_id.get(memory_id)
            if memory is not None:
                await self._vectors.index(memory_id, self._embedding_text(memory))
                reindexed += 1
        removed = 0
        for memory_id in report["orphan"]:
            await self._vectors.delete(memory_id)
            removed += 1
        return {"reindexed": reindexed, "removed": removed}

    @staticmethod
    def _embedding_text(memory: Memory) -> str:
        """Text fed to the embedder: content plus tags/entities for recall."""
        extras = " ".join([*memory.tags, *memory.entities])
        return f"{memory.content} {extras}".strip()

    async def _reflect_entities(self, memory: Memory) -> None:
        """
        Mirror the memory's entities into the graph (spec Phase 6).

        Each referenced entity becomes/updates a node carrying the memory as
        evidence, and co-referenced entities are connected RELATED_TO so the
        graph grows automatically from ordinary writes. Richer, typed edges
        (prefers / used_for) are added explicitly by higher layers.
        """
        if not memory.entities:
            return
        stored: list[Entity] = []
        for name in memory.entities:
            ent = await self._graph.upsert_entity(
                Entity(name=name, confidence=memory.confidence)
            )
            stored.append(ent)
        for left, right in zip(stored, stored[1:]):
            await self._graph.add_relationship(
                Relationship(
                    source_id=left.id,
                    target_id=right.id,
                    relation=RelationType.RELATED_TO.value,
                    confidence=memory.confidence,
                    evidence_memory_ids=[memory.id],
                )
            )

    async def _publish(self, memory: Memory) -> None:
        if self._bus is None:
            return
        await self._bus.publish(
            MemoryStored(
                memory_id=memory.id,
                memory_type=memory.memory_type.value,
                veracity=memory.veracity.value,
                confidence=memory.confidence,
                source_type=memory.source.source_type.value,
            )
        )
