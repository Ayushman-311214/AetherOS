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
