"""
SQLite-backed vector index (spec Phase 5).

Vectors live in the ``memory_embeddings`` table as raw float32 bytes keyed by
memory id. Search is exact cosine similarity computed with numpy: because every
stored vector is L2-normalised at embed time, cosine reduces to a dot product,
and the whole candidate matrix is one ``X @ q`` call.

This is deliberately a brute-force index, not an ANN structure. The spec's
Rule 5 says vectors are *one* signal fed a structurally-filtered candidate pool
-- the retriever hands :meth:`search` the (bounded) ids that already passed the
SQL filters, so the matrix is small and an approximate index would add a
dependency and a correctness risk for no measurable win at this scale. The
``memory_id``-scoped interface keeps the door open to swapping in a real ANN
backend later without changing callers.
"""

from __future__ import annotations

import asyncio

import numpy as np

from ..embeddings.base import EmbeddingProvider
from ..storage.database import SQLiteDatabase
from .._clock import utcnow_iso


class VectorIndex:
    """Store, update, delete and cosine-search memory embeddings."""

    def __init__(self, db: SQLiteDatabase, provider: EmbeddingProvider) -> None:
        self._db = db
        self._provider = provider

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def index(self, memory_id: str, text: str) -> None:
        vector = await self._provider.embed(text)
        await asyncio.to_thread(self._store, memory_id, vector)

    async def index_many(self, items: list[tuple[str, str]]) -> None:
        texts = [t for _, t in items]
        vectors = await self._provider.embed_many(texts)

        def _run() -> None:
            for (memory_id, _), vector in zip(items, vectors):
                self._store(memory_id, vector)

        await asyncio.to_thread(_run)

    def _store(self, memory_id: str, vector: np.ndarray) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO memory_embeddings "
            "(memory_id, dim, vector, model, created_at) VALUES (?,?,?,?,?)",
            (
                memory_id,
                int(vector.shape[0]),
                vector.astype(np.float32).tobytes(),
                self._provider.name,
                utcnow_iso(),
            ),
        )

    async def delete(self, memory_id: str) -> None:
        def _run() -> None:
            self._db.execute(
                "DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,)
            )

        await asyncio.to_thread(_run)

    async def count(self) -> int:
        def _run() -> int:
            row = self._db.query_one("SELECT COUNT(*) AS n FROM memory_embeddings")
            return int(row["n"]) if row else 0

        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query_text: str,
        *,
        limit: int = 10,
        candidate_ids: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """
        Return ``(memory_id, cosine_similarity)`` for the best matches.

        ``candidate_ids`` restricts the search to a pre-filtered pool (the hybrid
        pipeline's normal path); ``None`` searches the whole index.
        """
        query_vec = await self._provider.embed(query_text)
        return await asyncio.to_thread(
            self._search_sync, query_vec, limit, candidate_ids
        )

    def _load_matrix(
        self, candidate_ids: list[str] | None
    ) -> tuple[list[str], np.ndarray]:
        if candidate_ids is not None:
            if not candidate_ids:
                return [], np.empty((0, 0), dtype=np.float32)
            marks = ",".join("?" for _ in candidate_ids)
            rows = self._db.query_all(
                f"SELECT memory_id, vector FROM memory_embeddings "
                f"WHERE memory_id IN ({marks})",
                candidate_ids,
            )
        else:
            rows = self._db.query_all(
                "SELECT memory_id, vector FROM memory_embeddings"
            )
        ids = [r["memory_id"] for r in rows]
        if not ids:
            return [], np.empty((0, 0), dtype=np.float32)
        matrix = np.vstack(
            [np.frombuffer(r["vector"], dtype=np.float32) for r in rows]
        )
        return ids, matrix

    def _search_sync(
        self,
        query_vec: np.ndarray,
        limit: int,
        candidate_ids: list[str] | None,
    ) -> list[tuple[str, float]]:
        ids, matrix = self._load_matrix(candidate_ids)
        if not ids:
            return []
        # Both sides are L2-normalised, so dot == cosine.
        scores = matrix @ query_vec.astype(np.float32)
        order = np.argsort(-scores)[:limit]
        return [(ids[i], float(scores[i])) for i in order]
