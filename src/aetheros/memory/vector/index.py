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
import logging

import numpy as np

from ..embeddings.base import EmbeddingProvider
from ..storage.database import SQLiteDatabase
from .._clock import utcnow_iso

logger = logging.getLogger(__name__)

# Safety rail for the *unfiltered* whole-index scan. The production recall path
# always passes a SQL-bounded ``candidate_ids`` pool, so this only caps the
# admin/convenience ``search(candidate_ids=None)`` path -- it must never silently
# load an unbounded corpus into memory (contract: "Do not load every stored
# vector into application memory per query"). When more eligible vectors exist
# than this bound, the scan is capped to the most-recent ``max_scan`` and the
# recall limitation is disclosed via a logged warning.
DEFAULT_MAX_SCAN = 50_000


class VectorIndex:
    """Store, update, delete and cosine-search memory embeddings."""

    def __init__(
        self,
        db: SQLiteDatabase,
        provider: EmbeddingProvider,
        *,
        max_scan: int = DEFAULT_MAX_SCAN,
    ) -> None:
        self._db = db
        self._provider = provider
        self._max_scan = max(1, int(max_scan))

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
        # Guard before persisting: a real provider can emit a wrong-dimension,
        # empty or non-finite vector on a partial failure, and a bad row silently
        # poisons every future cosine score. ``dimension`` may be un-probed for a
        # lazy real provider, in which case we trust the vector's own length.
        try:
            expected = int(self._provider.dimension)
        except Exception:  # dimension not yet probed -- adopt the vector's length
            expected = int(vector.shape[0]) if vector.ndim == 1 else -1
        EmbeddingProvider.validate_vector(vector, expected_dim=expected)
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

    async def ids(self) -> list[str]:
        """All memory ids that currently have a vector (projection inventory)."""

        def _run() -> list[str]:
            rows = self._db.query_all("SELECT memory_id FROM memory_embeddings")
            return [r["memory_id"] for r in rows]

        return await asyncio.to_thread(_run)

    async def identities(self) -> dict[str, int]:
        """
        Count stored vectors grouped by embedding-space identity (``model``).

        Lets the manager detect a config/provider change that left vectors from
        a *different* embedding space in the index -- those are unsearchable
        under the active provider and need an explicit rebuild/migration.
        """

        def _run() -> dict[str, int]:
            rows = self._db.query_all(
                "SELECT model, COUNT(*) AS n FROM memory_embeddings GROUP BY model"
            )
            return {str(r["model"]): int(r["n"]) for r in rows}

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
        exclude_deleted: bool = True,
    ) -> list[tuple[str, float]]:
        """
        Return ``(memory_id, cosine_similarity)`` for the best matches.

        ``candidate_ids`` restricts the search to a pre-filtered pool (the hybrid
        pipeline's normal path); ``None`` scans the whole index. On the whole-index
        path ``exclude_deleted`` (default) joins ``memory_items`` so soft-deleted
        rows never leak into results -- the retriever's own pool is already
        status-filtered, so this protects the direct/admin caller. The scan is
        bounded by ``max_scan`` (see :data:`DEFAULT_MAX_SCAN`).
        """
        query_vec = await self._provider.embed(query_text)
        return await asyncio.to_thread(
            self._search_sync, query_vec, limit, candidate_ids, exclude_deleted
        )

    async def search_many(
        self,
        query_texts: list[str],
        *,
        limit: int = 10,
        candidate_ids: list[str] | None = None,
        exclude_deleted: bool = True,
    ) -> list[list[tuple[str, float]]]:
        """
        Batch form of :meth:`search`: one result list per query, in input order.

        The eligible matrix is loaded once and reused across all queries (one
        ``M @ Qᵀ`` instead of N scans), then top-k is taken per column.
        """
        if not query_texts:
            return []
        query_vecs = await self._provider.embed_batch(query_texts)

        def _run() -> list[list[tuple[str, float]]]:
            ids, matrix = self._load_matrix(candidate_ids, exclude_deleted)
            if not ids:
                return [[] for _ in query_vecs]
            q = np.vstack([v.astype(np.float32) for v in query_vecs])  # (N, dim)
            scores = matrix @ q.T  # (M, N); both sides L2-normalised => cosine
            out: list[list[tuple[str, float]]] = []
            for col in range(scores.shape[1]):
                col_scores = scores[:, col]
                order = np.argsort(-col_scores)[:limit]
                out.append([(ids[i], float(col_scores[i])) for i in order])
            return out

        return await asyncio.to_thread(_run)

    def _load_matrix(
        self, candidate_ids: list[str] | None, exclude_deleted: bool = True
    ) -> tuple[list[str], np.ndarray]:
        # Only ever compare vectors that live in the *same* embedding space as
        # the active provider. Cosine across two models (even equal-dimension
        # ones) is meaningless, so foreign-identity rows are filtered out here
        # rather than silently blended into the scores (contract §4.4).
        identity = self._provider.name
        if candidate_ids is not None:
            # The caller already resolved (and status-filtered) this pool; honour
            # it exactly, only adding the embedding-identity guard.
            if not candidate_ids:
                return [], np.empty((0, 0), dtype=np.float32)
            marks = ",".join("?" for _ in candidate_ids)
            rows = self._db.query_all(
                f"SELECT memory_id, vector FROM memory_embeddings "
                f"WHERE model = ? AND memory_id IN ({marks})",
                [identity, *candidate_ids],
            )
        else:
            # Whole-index scan. Exclude soft-deleted rows so a forgotten memory's
            # vector cannot leak through recall (contract: prevent deletion
            # leakage), and cap the scan so an unbounded corpus is never pulled
            # into memory. ``max_scan + 1`` lets us detect truncation.
            if exclude_deleted:
                sql = (
                    "SELECT e.memory_id AS memory_id, e.vector AS vector "
                    "FROM memory_embeddings e "
                    "JOIN memory_items m ON m.id = e.memory_id "
                    "WHERE e.model = ? AND m.status != 'deleted' "
                    "ORDER BY e.created_at DESC LIMIT ?"
                )
            else:
                sql = (
                    "SELECT memory_id, vector FROM memory_embeddings "
                    "WHERE model = ? ORDER BY created_at DESC LIMIT ?"
                )
            rows = self._db.query_all(sql, [identity, self._max_scan + 1])
            if len(rows) > self._max_scan:
                rows = rows[: self._max_scan]
                logger.warning(
                    "VectorIndex whole-index scan hit the %d-vector cap; results "
                    "cover only the most-recent vectors (recall may be partial). "
                    "Pass candidate_ids for an exact bounded search.",
                    self._max_scan,
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
        exclude_deleted: bool = True,
    ) -> list[tuple[str, float]]:
        ids, matrix = self._load_matrix(candidate_ids, exclude_deleted)
        if not ids:
            return []
        # Both sides are L2-normalised, so dot == cosine.
        scores = matrix @ query_vec.astype(np.float32)
        order = np.argsort(-scores)[:limit]
        return [(ids[i], float(scores[i])) for i in order]
