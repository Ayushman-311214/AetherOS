"""
Memory consolidator (spec Phase 12).

Turns redundancy into stable knowledge: near-duplicate memories of the same kind
are merged into one survivor that accumulates their evidence, and the duplicates
are archived (not deleted) with a link back to the survivor so history stays
auditable. This is the honest first rung of the spec's "many raw events ->
patterns -> stable memories" ladder; richer pattern mining (episodes -> learned
procedures, Phase 10) builds on these same primitives and is layered on top.
"""

from __future__ import annotations

import uuid

import numpy as np

from ..config import MemoryConfig
from ..domain.enums import MemoryStatus
from ..domain.memory import Memory
from ..events import MemoryConsolidated
from ..storage.database import SQLiteDatabase
from ..storage.repository import MemoryRepository


class MemoryConsolidator:
    """Deduplicate and merge redundant memories (spec Phase 12)."""

    def __init__(
        self,
        repository: MemoryRepository,
        db: SQLiteDatabase,
        config: MemoryConfig,
        *,
        event_bus=None,
    ) -> None:
        self._repo = repository
        self._db = db
        self._config = config
        self._bus = event_bus

    async def consolidate(self) -> dict[str, int]:
        if not self._config.consolidation_enabled:
            return {"merged": 0, "archived": 0, "promoted": 0}

        memories = [
            m
            for m in await self._repo.iter_all()
            if m.status is not MemoryStatus.ARCHIVED
        ]
        vectors = await self._load_vectors([m.id for m in memories])

        merged = 0
        # Group by type so a preference never merges with an episode.
        by_type: dict[str, list[Memory]] = {}
        for m in memories:
            by_type.setdefault(m.memory_type.value, []).append(m)

        for group in by_type.values():
            merged += await self._dedup_group(group, vectors)

        stats = {"merged": merged, "archived": merged, "promoted": 0}
        if self._bus is not None:
            await self._bus.publish(
                MemoryConsolidated(merged=merged, archived=merged, promoted=0)
            )
        return stats

    async def _dedup_group(
        self, group: list[Memory], vectors: dict[str, np.ndarray]
    ) -> int:
        """Merge near-duplicates within one type; return how many were merged."""
        # Survivors kept; later duplicates folded into the best earlier survivor.
        survivors: list[Memory] = []
        merged = 0
        threshold = self._config.dedup_threshold

        # Process most-evidenced / most-confident first so they become survivors.
        for memory in sorted(
            group, key=lambda m: (m.evidence_count, m.confidence), reverse=True
        ):
            duplicate_of = self._best_match(memory, survivors, vectors, threshold)
            if duplicate_of is None:
                survivors.append(memory)
                continue

            # Fold evidence into the survivor; archive this duplicate with a link.
            duplicate_of.evidence_count += memory.evidence_count
            duplicate_of.confidence = min(
                1.0, max(duplicate_of.confidence, memory.confidence) + 0.02
            )
            await self._repo.update(duplicate_of)

            memory.status = MemoryStatus.ARCHIVED
            await self._repo.update(memory)
            await self._repo.add_link(
                {
                    "id": uuid.uuid4().hex,
                    "from_id": memory.id,
                    "to_id": duplicate_of.id,
                    "link_type": "derived_from",
                    "weight": 1.0,
                    "metadata": {"reason": "consolidation_duplicate"},
                }
            )
            merged += 1
        return merged

    @staticmethod
    def _best_match(
        memory: Memory,
        survivors: list[Memory],
        vectors: dict[str, np.ndarray],
        threshold: float,
    ) -> Memory | None:
        content = memory.content.strip().lower()
        vec = vectors.get(memory.id)
        for survivor in survivors:
            # Exact-content duplicates always merge.
            if survivor.content.strip().lower() == content:
                return survivor
            sv = vectors.get(survivor.id)
            if vec is not None and sv is not None:
                if float(vec @ sv) >= threshold:
                    return survivor
        return None

    async def _load_vectors(self, ids: list[str]) -> dict[str, np.ndarray]:
        import asyncio

        def _run() -> dict[str, np.ndarray]:
            if not ids:
                return {}
            marks = ",".join("?" for _ in ids)
            rows = self._db.query_all(
                f"SELECT memory_id, vector FROM memory_embeddings "
                f"WHERE memory_id IN ({marks})",
                ids,
            )
            return {
                r["memory_id"]: np.frombuffer(r["vector"], dtype=np.float32)
                for r in rows
            }

        return await asyncio.to_thread(_run)
