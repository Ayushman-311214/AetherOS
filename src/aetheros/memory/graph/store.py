"""
Knowledge-graph store over SQLite (spec Phase 6).

Entities and relationships persist in their own tables (see schema.py); this
class is the typed, deduplicating API over them, plus traversal. Graph
*traversal* (paths, N-hop neighbourhoods) is a bounded breadth-first walk done
directly in SQL, one hop at a time over the currently-active edge set -- the
spec explicitly says not to introduce a dedicated graph database "unless there
is a demonstrated architectural need". Per-hop SQL (backed by the partial
active-edge indexes in migration 2) keeps each walk bounded in depth, fan-out,
result count and wall-clock time, and never materialises the whole graph.

Two integrity rules the spec calls for (Phase 13):

* Entities deduplicate on :pyattr:`Entity.key` (type + normalised name), so the
  same real thing is one node, with evidence accumulating on it.
* Relationships are *superseded*, not deleted: a contradicting edge closes the
  old one's temporal validity (``valid_to``) rather than erasing history.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, replace
from typing import Any

from ...core.errors.memory_error import MemoryValidationError
from .._clock import utcnow_iso
from ..domain.semantic import Entity, Relationship
from ..storage.database import SQLiteDatabase


@dataclass(frozen=True, slots=True)
class TraversalBounds:
    """Explicit limits for a graph walk (Phase 7).

    Unbounded traversal of an evolving graph is a latency and memory hazard, so
    every walk carries these. Defaults are sized for an interactive agent, not a
    bulk analytics job.
    """

    max_hops: int = 2
    max_fanout: int = 64
    max_results: int = 256
    time_limit_s: float = 1.0

    def __post_init__(self) -> None:
        if self.max_hops < 0:
            raise ValueError("max_hops must be >= 0")
        if self.max_fanout < 1:
            raise ValueError("max_fanout must be >= 1")
        if self.max_results < 1:
            raise ValueError("max_results must be >= 1")
        if self.time_limit_s <= 0:
            raise ValueError("time_limit_s must be > 0")

    def with_hops(self, max_hops: int) -> TraversalBounds:
        """Return a copy with ``max_hops`` overridden (back-compat shim)."""
        return replace(self, max_hops=max_hops)


class KnowledgeGraph:
    """Deduplicating entity/relationship store with bounded SQL traversal."""

    def __init__(self, db: SQLiteDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    async def upsert_entity(self, entity: Entity) -> Entity:
        """Insert, or merge into an existing entity with the same key."""

        def _run() -> Entity:
            existing = self._db.query_one(
                "SELECT * FROM entities WHERE key = ?", (entity.key,)
            )
            if existing is None:
                self._db.execute(
                    "INSERT INTO entities "
                    "(id, key, name, entity_type, attributes, aliases, confidence, "
                    "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        entity.id,
                        entity.key,
                        entity.name,
                        entity.entity_type,
                        json.dumps(entity.attributes),
                        json.dumps(entity.aliases),
                        entity.confidence,
                        entity.created_at.isoformat(),
                        entity.updated_at.isoformat(),
                    ),
                )
                return entity

            merged = Entity.from_dict(
                {
                    "id": existing["id"],
                    "name": existing["name"],
                    "entity_type": existing["entity_type"],
                    "attributes": {
                        **json.loads(existing["attributes"]),
                        **entity.attributes,
                    },
                    "aliases": sorted(
                        set(json.loads(existing["aliases"])) | set(entity.aliases)
                    ),
                    # More corroboration -> a little more confidence, capped.
                    "confidence": min(
                        1.0, float(existing["confidence"]) + 0.05
                    ),
                    "created_at": existing["created_at"],
                    "updated_at": utcnow_iso(),
                }
            )
            self._db.execute(
                "UPDATE entities SET name=?, entity_type=?, attributes=?, aliases=?, "
                "confidence=?, updated_at=? WHERE id=?",
                (
                    merged.name,
                    merged.entity_type,
                    json.dumps(merged.attributes),
                    json.dumps(merged.aliases),
                    merged.confidence,
                    merged.updated_at.isoformat(),
                    merged.id,
                ),
            )
            return merged

        return await asyncio.to_thread(_run)

    async def get_entity(self, entity_id: str) -> Entity | None:
        def _run() -> Entity | None:
            row = self._db.query_one(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            )
            return self._row_to_entity(row) if row else None

        return await asyncio.to_thread(_run)

    async def find_entity(
        self, name: str, *, entity_type: str = "concept"
    ) -> Entity | None:
        key = f"{entity_type}:{name.strip().lower()}"

        def _run() -> Entity | None:
            row = self._db.query_one("SELECT * FROM entities WHERE key = ?", (key,))
            if row:
                return self._row_to_entity(row)
            # Fall back to a name match across types (callers often omit type).
            row = self._db.query_one(
                "SELECT * FROM entities WHERE lower(name) = ? LIMIT 1",
                (name.strip().lower(),),
            )
            return self._row_to_entity(row) if row else None

        return await asyncio.to_thread(_run)

    @staticmethod
    def _row_to_entity(row: Any) -> Entity:
        return Entity.from_dict(
            {
                "id": row["id"],
                "name": row["name"],
                "entity_type": row["entity_type"],
                "attributes": json.loads(row["attributes"]),
                "aliases": json.loads(row["aliases"]),
                "confidence": row["confidence"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    @staticmethod
    def _row_to_relationship(row: Any) -> Relationship:
        return Relationship.from_dict(
            {
                "id": row["id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "relation": row["relation"],
                "weight": row["weight"],
                "confidence": row["confidence"],
                "evidence_count": row["evidence_count"],
                "evidence_memory_ids": json.loads(row["evidence_memory_ids"]),
                "attributes": json.loads(row["attributes"]),
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
            }
        )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    async def add_relationship(self, rel: Relationship) -> Relationship:
        """
        Add an edge, or reinforce an existing active one.

        If an active relationship with the same (source, target, relation)
        already exists, its evidence/weight/confidence grow instead of creating
        a duplicate (spec Phase 12 -- merge, don't accumulate dupes).
        """

        def _run() -> Relationship:
            # Invalid-reference guard (Phase 7): an edge may only join entities
            # that actually exist, so traversal never dangles into a missing
            # node. Checked inside the same thread as the write.
            for role, node_id in (("source", rel.source_id), ("target", rel.target_id)):
                if self._db.query_one(
                    "SELECT 1 FROM entities WHERE id = ?", (node_id,)
                ) is None:
                    raise MemoryValidationError(
                        f"Relationship {role} entity does not exist: {node_id}",
                        hint="Upsert both endpoints before adding an edge.",
                    )
            existing = self._db.query_one(
                "SELECT * FROM relationships WHERE source_id=? AND target_id=? "
                "AND relation=? AND valid_to IS NULL",
                (rel.source_id, rel.target_id, rel.relation),
            )
            if existing is None:
                self._db.execute(
                    "INSERT INTO relationships "
                    "(id, source_id, target_id, relation, weight, confidence, "
                    "evidence_count, evidence_memory_ids, attributes, valid_from, "
                    "valid_to) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        rel.id,
                        rel.source_id,
                        rel.target_id,
                        rel.relation,
                        rel.weight,
                        rel.confidence,
                        rel.evidence_count,
                        json.dumps(rel.evidence_memory_ids),
                        json.dumps(rel.attributes),
                        rel.valid_from.isoformat(),
                        None,
                    ),
                )
                return rel

            prior = self._row_to_relationship(existing)
            prior.evidence_count += rel.evidence_count
            prior.weight += rel.weight
            prior.confidence = min(1.0, prior.confidence + 0.05)
            prior.evidence_memory_ids = sorted(
                set(prior.evidence_memory_ids) | set(rel.evidence_memory_ids)
            )
            self._db.execute(
                "UPDATE relationships SET weight=?, confidence=?, evidence_count=?, "
                "evidence_memory_ids=? WHERE id=?",
                (
                    prior.weight,
                    prior.confidence,
                    prior.evidence_count,
                    json.dumps(prior.evidence_memory_ids),
                    prior.id,
                ),
            )
            return prior

        return await asyncio.to_thread(_run)

    async def supersede_relationship(self, rel_id: str) -> None:
        """Close an edge's temporal validity (contradiction, not deletion)."""

        def _run() -> None:
            self._db.execute(
                "UPDATE relationships SET valid_to=? WHERE id=? AND valid_to IS NULL",
                (utcnow_iso(), rel_id),
            )

        await asyncio.to_thread(_run)

    async def scrub_memory(self, memory_id: str) -> int:
        """Remove one memory id from every edge's evidence list (Phase 15).

        Coordinated hard-erasure support: the erased row's *content* must
        not remain reachable through graph evidence pointers. Edges
        themselves stay (graph topology is shared knowledge accumulated
        from many memories, not the erased row's property); only the
        pointer to the erased content is removed. Returns how many edges
        were scrubbed.
        """

        def _run() -> int:
            rows = self._db.query_all(
                "SELECT id, evidence_memory_ids FROM relationships"
            )
            scrubbed = 0
            for r in rows:
                try:
                    ids = json.loads(r["evidence_memory_ids"])
                except (ValueError, TypeError):
                    continue
                if memory_id not in ids:
                    continue
                kept = [i for i in ids if i != memory_id]
                self._db.execute(
                    "UPDATE relationships SET evidence_memory_ids=? WHERE id=?",
                    (json.dumps(kept), r["id"]),
                )
                scrubbed += 1
            return scrubbed

        return await asyncio.to_thread(_run)

    async def find_relationships(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        relation: str | None = None,
        active_only: bool = True,
    ) -> list[Relationship]:
        def _run() -> list[Relationship]:
            where: list[str] = []
            params: list[Any] = []
            if source_id:
                where.append("source_id = ?")
                params.append(source_id)
            if target_id:
                where.append("target_id = ?")
                params.append(target_id)
            if relation:
                where.append("relation = ?")
                params.append(relation)
            if active_only:
                where.append("valid_to IS NULL")
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            rows = self._db.query_all(
                "SELECT * FROM relationships" + clause, params
            )
            return [self._row_to_relationship(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def neighbors(
        self, entity_id: str, *, relation: str | None = None
    ) -> list[tuple[Relationship, Entity]]:
        """Directly-connected entities (either direction) and the joining edge."""
        rels = await self.find_relationships(source_id=entity_id, relation=relation)
        incoming = await self.find_relationships(target_id=entity_id, relation=relation)
        out: list[tuple[Relationship, Entity]] = []
        for rel in [*rels, *incoming]:
            other_id = rel.target_id if rel.source_id == entity_id else rel.source_id
            other = await self.get_entity(other_id)
            if other is not None:
                out.append((rel, other))
        return out

    # ------------------------------------------------------------------
    # Traversal (bounded, per-hop over the active edge set)
    # ------------------------------------------------------------------

    def _active_neighbor_ids_sync(
        self, node_id: str, relation: str | None
    ) -> list[str]:
        """One hop: ids of entities joined to ``node_id`` by an *active* edge
        (either direction). Uses the partial active-edge indexes (migration 2)
        so a hop is an index SEARCH, not a scan over superseded history."""
        rel_clause = " AND relation = ?" if relation else ""
        params: tuple[Any, ...] = (node_id,) if not relation else (node_id, relation)
        out_rows = self._db.query_all(
            "SELECT target_id AS other FROM relationships "
            "WHERE source_id = ? AND valid_to IS NULL" + rel_clause,
            params,
        )
        in_rows = self._db.query_all(
            "SELECT source_id AS other FROM relationships "
            "WHERE target_id = ? AND valid_to IS NULL" + rel_clause,
            params,
        )
        # dict.fromkeys keeps first-seen order and drops duplicate/parallel edges.
        return list(dict.fromkeys(r["other"] for r in (*out_rows, *in_rows)))

    def _bounded_bfs_sync(
        self,
        start_id: str,
        bounds: TraversalBounds,
        relation: str | None,
        goal_id: str | None,
    ) -> tuple[dict[str, int], dict[str, str]]:
        """
        Breadth-first walk of the active graph from ``start_id``, honouring every
        bound. Returns ``(hops_by_id, parent_by_id)``.

        Cycle-safe: a ``visited`` set means each node is expanded once. Bounded by
        ``max_hops`` (depth), ``max_fanout`` (neighbours expanded per node),
        ``max_results`` (total nodes discovered) and ``time_limit_s`` (wall clock,
        checked each dequeue). Stops early if ``goal_id`` is reached.
        """
        deadline = time.monotonic() + bounds.time_limit_s
        hops: dict[str, int] = {start_id: 0}
        parent: dict[str, str] = {}
        queue: deque[str] = deque([start_id])
        while queue:
            if time.monotonic() > deadline:
                break
            node = queue.popleft()
            depth = hops[node]
            if node == goal_id:
                break
            if depth >= bounds.max_hops:
                continue
            neighbours = self._active_neighbor_ids_sync(node, relation)
            for other in neighbours[: bounds.max_fanout]:
                if other in hops:
                    continue
                hops[other] = depth + 1
                parent[other] = node
                if other == goal_id:
                    return hops, parent
                # -1 for the start node, which is never a "result".
                if len(hops) - 1 >= bounds.max_results:
                    return hops, parent
                queue.append(other)
        return hops, parent

    async def find_related_entities(
        self,
        name: str,
        *,
        entity_type: str = "concept",
        max_hops: int = 2,
        relation: str | None = None,
        bounds: TraversalBounds | None = None,
    ) -> list[Entity]:
        """Entities reachable from ``name`` within the bounds, nearest first.

        ``max_hops`` is honoured for backwards compatibility; any explicit
        ``bounds`` takes precedence for the remaining limits (fan-out, result
        count, time)."""
        start = await self.find_entity(name, entity_type=entity_type)
        if start is None:
            return []
        bounds = (bounds or TraversalBounds()).with_hops(max_hops)
        hops, _ = await asyncio.to_thread(
            self._bounded_bfs_sync, start.id, bounds, relation, None
        )
        ordered = sorted(
            (nid for nid in hops if nid != start.id), key=lambda nid: hops[nid]
        )
        out: list[Entity] = []
        for node_id in ordered:
            ent = await self.get_entity(node_id)
            if ent is not None:
                out.append(ent)
        return out

    async def find_path(
        self,
        source_name: str,
        target_name: str,
        *,
        source_type: str = "concept",
        target_type: str = "concept",
        relation: str | None = None,
        bounds: TraversalBounds | None = None,
    ) -> list[Entity]:
        """Shortest active-edge path of entities between two names, or ``[]``.

        Bounded BFS: a path longer than ``bounds.max_hops`` (or one the bounds
        stop short of) returns ``[]`` rather than scanning the whole graph."""
        src = await self.find_entity(source_name, entity_type=source_type)
        dst = await self.find_entity(target_name, entity_type=target_type)
        if src is None or dst is None:
            return []
        if src.id == dst.id:
            return [src]
        bounds = bounds or TraversalBounds()
        hops, parent = await asyncio.to_thread(
            self._bounded_bfs_sync, src.id, bounds, relation, dst.id
        )
        if dst.id not in parent and dst.id != src.id:
            return []
        # Reconstruct source -> target by walking parents back from the goal.
        chain: list[str] = [dst.id]
        while chain[-1] != src.id:
            chain.append(parent[chain[-1]])
        chain.reverse()
        path: list[Entity] = []
        for node_id in chain:
            ent = await self.get_entity(node_id)
            if ent is not None:
                path.append(ent)
        return path

    async def stats(self) -> dict[str, int]:
        def _run() -> dict[str, int]:
            e = self._db.query_one("SELECT COUNT(*) AS n FROM entities")
            r = self._db.query_one(
                "SELECT COUNT(*) AS n FROM relationships WHERE valid_to IS NULL"
            )
            return {
                "entities": int(e["n"]) if e else 0,
                "relationships": int(r["n"]) if r else 0,
            }

        return await asyncio.to_thread(_run)
