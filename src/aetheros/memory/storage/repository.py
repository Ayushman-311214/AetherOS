"""
Repository: typed CRUD over the memory tables (spec Phase 4 -- MemoryRepository).

Owns the async boundary: every public method is a coroutine that runs the
synchronous :class:`SQLiteDatabase` calls in a worker thread via
:func:`asyncio.to_thread`, so the event loop never blocks on disk I/O. It is the
*only* place that knows how a :class:`Memory` maps onto rows -- the promoted
context columns, the normalised ``memory_tags`` / ``memory_entities`` side
tables, and the JSON-encoded blobs all live here, so the services above work in
domain objects exclusively.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from typing import Any

from ..domain.memory import Memory
from ..domain.query import MemoryQuery
from .database import SQLiteDatabase

# Metadata keys that are mirrored into indexed columns for fast filtering.
_CONTEXT_COLUMNS = (
    "session_id",
    "task_id",
    "episode_id",
    "instrument_id",
    "user_id",
    "application",
)


class MemoryRepository:
    """Persistence for :class:`Memory` records and their side tables."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        payload = {
            "id": row["id"],
            "memory_type": row["memory_type"],
            "veracity": row["veracity"],
            "content": row["content"],
            "data": json.loads(row["data"]),
            "source": json.loads(row["source"]),
            "confidence": row["confidence"],
            "importance": row["importance"],
            "scope": row["scope"],
            "status": row["status"],
            "evidence_count": row["evidence_count"],
            "access_count": row["access_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_accessed_at": row["last_accessed_at"],
            "expires_at": row["expires_at"],
            "version": row["version"],
            "tags": json.loads(row["tags"]),
            "entities": json.loads(row["entities"]),
            "metadata": json.loads(row["metadata"]),
        }
        return Memory.from_dict(payload)

    @staticmethod
    def _insert_params(memory: Memory) -> tuple[Any, ...]:
        d = memory.to_dict()
        ctx = memory.metadata
        return (
            d["id"],
            d["memory_type"],
            d["veracity"],
            d["content"],
            json.dumps(d["data"]),
            json.dumps(d["source"]),
            d["confidence"],
            d["importance"],
            d["scope"],
            d["status"],
            d["evidence_count"],
            d["access_count"],
            d["created_at"],
            d["updated_at"],
            d["last_accessed_at"],
            d["expires_at"],
            d["version"],
            json.dumps(d["tags"]),
            json.dumps(d["entities"]),
            json.dumps(d["metadata"]),
            ctx.get("session_id"),
            ctx.get("task_id"),
            ctx.get("episode_id"),
            ctx.get("instrument_id"),
            ctx.get("user_id"),
            ctx.get("application"),
        )

    _INSERT_SQL = """
        INSERT OR REPLACE INTO memory_items (
            id, memory_type, veracity, content, data, source,
            confidence, importance, scope, status, evidence_count, access_count,
            created_at, updated_at, last_accessed_at, expires_at, version,
            tags, entities, metadata,
            session_id, task_id, episode_id, instrument_id, user_id, application
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def _write_sync(self, memory: Memory) -> None:
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (self._INSERT_SQL, self._insert_params(memory)),
            ("DELETE FROM memory_tags WHERE memory_id = ?", (memory.id,)),
            ("DELETE FROM memory_entities WHERE memory_id = ?", (memory.id,)),
        ]
        for tag in dict.fromkeys(t.strip().lower() for t in memory.tags if t.strip()):
            statements.append(
                ("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?,?)",
                 (memory.id, tag))
            )
        for ent in dict.fromkeys(e.strip() for e in memory.entities if e.strip()):
            statements.append(
                ("INSERT OR IGNORE INTO memory_entities (memory_id, entity) VALUES (?,?)",
                 (memory.id, ent))
            )
        self._db.execute_script(statements)

    async def add(self, memory: Memory) -> None:
        await asyncio.to_thread(self._write_sync, memory)

    async def add_many(self, memories: list[Memory]) -> None:
        def _run() -> None:
            for m in memories:
                self._write_sync(m)

        await asyncio.to_thread(_run)

    async def update(self, memory: Memory) -> None:
        # INSERT OR REPLACE makes update identical to add; kept distinct so the
        # service layer reads cleanly and so a future optimistic-version guard
        # has one place to live.
        await asyncio.to_thread(self._write_sync, memory)

    async def delete(self, memory_id: str) -> None:
        def _run() -> None:
            self._db.execute("DELETE FROM memory_items WHERE id = ?", (memory_id,))

        await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get(self, memory_id: str) -> Memory | None:
        def _run() -> Memory | None:
            row = self._db.query_one(
                "SELECT * FROM memory_items WHERE id = ?", (memory_id,)
            )
            return self._row_to_memory(row) if row else None

        return await asyncio.to_thread(_run)

    async def exists(self, memory_id: str) -> bool:
        def _run() -> bool:
            row = self._db.query_one(
                "SELECT 1 FROM memory_items WHERE id = ?", (memory_id,)
            )
            return row is not None

        return await asyncio.to_thread(_run)

    async def count(self, *, include_deleted: bool = False) -> int:
        def _run() -> int:
            sql = "SELECT COUNT(*) AS n FROM memory_items"
            if not include_deleted:
                sql += " WHERE status != 'deleted'"
            row = self._db.query_one(sql)
            return int(row["n"]) if row else 0

        return await asyncio.to_thread(_run)

    async def type_distribution(self) -> dict[str, int]:
        """Count of live memories by type -- an observability signal (Phase 22)."""

        def _run() -> dict[str, int]:
            rows = self._db.query_all(
                "SELECT memory_type, COUNT(*) AS n FROM memory_items "
                "WHERE status != 'deleted' GROUP BY memory_type"
            )
            return {r["memory_type"]: int(r["n"]) for r in rows}

        return await asyncio.to_thread(_run)

    async def record_access(
        self, memory_id: str, *, context: dict[str, Any] | None = None
    ) -> None:
        """Bump access_count/last_accessed_at and append an access audit row."""

        def _run() -> None:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            self._db.execute_script(
                [
                    (
                        "UPDATE memory_items SET access_count = access_count + 1, "
                        "last_accessed_at = ? WHERE id = ?",
                        (now, memory_id),
                    ),
                    (
                        "INSERT INTO memory_access (memory_id, accessed_at, context) "
                        "VALUES (?,?,?)",
                        (memory_id, now, json.dumps(context or {})),
                    ),
                ]
            )

        await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Structured candidate generation (spec Phase 7 -- filtering stage)
    # ------------------------------------------------------------------

    async def candidates(self, query: MemoryQuery) -> list[Memory]:
        """
        Return the structurally-matching candidate pool for a query.

        This is deliberately *not* semantic -- it applies the hard filters
        (type, veracity, status, confidence floor, tags, entities, context) in
        SQL and hands an ordered, bounded pool to the retriever, which then does
        semantic + graph scoring. Keeping these two stages separate is what
        makes retrieval "SQL + vector + graph + metadata" rather than pure
        vector search (Rule 5).
        """

        def _run() -> list[Memory]:
            where: list[str] = []
            where_params: list[Any] = []

            if not query.include_archived:
                where.append("mi.status IN ('active', 'low_confidence', 'stale')")
            else:
                where.append("mi.status != 'deleted'")

            if query.memory_types:
                marks = ",".join("?" for _ in query.memory_types)
                where.append(f"mi.memory_type IN ({marks})")
                where_params.extend(t.value for t in query.memory_types)

            if query.veracities:
                marks = ",".join("?" for _ in query.veracities)
                where.append(f"mi.veracity IN ({marks})")
                where_params.extend(v.value for v in query.veracities)

            if query.min_confidence > 0:
                where.append("mi.confidence >= ?")
                where_params.append(query.min_confidence)

            for col in _CONTEXT_COLUMNS:
                if col in query.context and query.context[col] is not None:
                    where.append(f"mi.{col} = ?")
                    where_params.append(query.context[col])

            # Joins are emitted BEFORE the WHERE clause in the final SQL, so their
            # bind parameters must come first too (ordinal "?" binding).
            joins = ""
            join_params: list[Any] = []
            if query.tags:
                marks = ",".join("?" for _ in query.tags)
                joins += (
                    " JOIN memory_tags mt ON mt.memory_id = mi.id "
                    f"AND mt.tag IN ({marks})"
                )
                join_params.extend(t.strip().lower() for t in query.tags)

            if query.entities:
                marks = ",".join("?" for _ in query.entities)
                joins += (
                    " JOIN memory_entities me ON me.memory_id = mi.id "
                    f"AND me.entity IN ({marks})"
                )
                join_params.extend(query.entities)

            clause = (" WHERE " + " AND ".join(where)) if where else ""
            sql = (
                "SELECT DISTINCT mi.* FROM memory_items mi"
                + joins
                + clause
                + " ORDER BY mi.last_accessed_at IS NULL, mi.last_accessed_at DESC,"
                + " mi.created_at DESC"
                + " LIMIT ?"
            )
            params = [*join_params, *where_params, query.candidate_limit]
            rows = self._db.query_all(sql, params)
            return [self._row_to_memory(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def list_by(
        self,
        *,
        memory_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        def _run() -> list[Memory]:
            where: list[str] = []
            params: list[Any] = []
            if memory_type:
                where.append("memory_type = ?")
                params.append(memory_type)
            if status:
                where.append("status = ?")
                params.append(status)
            else:
                where.append("status != 'deleted'")
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            sql = (
                "SELECT * FROM memory_items" + clause
                + " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            return [self._row_to_memory(r) for r in self._db.query_all(sql, params)]

        return await asyncio.to_thread(_run)

    async def iter_all(self, *, include_deleted: bool = False) -> list[Memory]:
        """Every memory -- used by decay and consolidation sweeps."""

        def _run() -> list[Memory]:
            sql = "SELECT * FROM memory_items"
            if not include_deleted:
                sql += " WHERE status != 'deleted'"
            return [self._row_to_memory(r) for r in self._db.query_all(sql)]

        return await asyncio.to_thread(_run)

    async def clear(self) -> None:
        """Wipe every memory table (user 'clear all' / tests)."""

        def _run() -> None:
            for table in (
                "memory_access",
                "memory_tags",
                "memory_entities",
                "memory_embeddings",
                "memory_links",
                "memory_items",
            ):
                self._db.execute(f"DELETE FROM {table}")

        await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Memory-to-memory links (spec Phase 2 -- memory_links)
    # ------------------------------------------------------------------

    async def add_link(self, link: dict[str, Any]) -> None:
        def _run() -> None:
            self._db.execute(
                "INSERT OR REPLACE INTO memory_links "
                "(id, from_id, to_id, link_type, weight, metadata) VALUES (?,?,?,?,?,?)",
                (
                    link["id"],
                    link["from_id"],
                    link["to_id"],
                    link["link_type"],
                    link["weight"],
                    json.dumps(link.get("metadata", {})),
                ),
            )

        await asyncio.to_thread(_run)

    async def linked_ids(self, memory_id: str) -> list[tuple[str, str, float]]:
        """(neighbour_id, link_type, weight) for every link touching ``memory_id``."""

        def _run() -> list[tuple[str, str, float]]:
            rows = self._db.query_all(
                "SELECT from_id, to_id, link_type, weight FROM memory_links "
                "WHERE from_id = ? OR to_id = ?",
                (memory_id, memory_id),
            )
            out: list[tuple[str, str, float]] = []
            for r in rows:
                other = r["to_id"] if r["from_id"] == memory_id else r["from_id"]
                out.append((other, r["link_type"], float(r["weight"])))
            return out

        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Metadata lookups (used by the key/value provider adapter)
    # ------------------------------------------------------------------

    async def find_by_metadata(self, path: str, value: Any) -> list[Memory]:
        """Memories whose metadata JSON field ``path`` equals ``value``."""

        def _run() -> list[Memory]:
            rows = self._db.query_all(
                "SELECT * FROM memory_items "
                "WHERE json_extract(metadata, ?) = ? AND status != 'deleted' "
                "ORDER BY updated_at DESC",
                (f"$.{path}", value),
            )
            return [self._row_to_memory(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def list_metadata_values(self, path: str) -> list[str]:
        """Distinct non-null values of a metadata JSON field."""

        def _run() -> list[str]:
            rows = self._db.query_all(
                "SELECT DISTINCT json_extract(metadata, ?) AS v FROM memory_items "
                "WHERE v IS NOT NULL AND status != 'deleted'",
                (f"$.{path}",),
            )
            return [str(r["v"]) for r in rows if r["v"] is not None]

        return await asyncio.to_thread(_run)
