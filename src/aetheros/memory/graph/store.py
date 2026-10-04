"""
Knowledge-graph store over SQLite (spec Phase 6).

Entities and relationships persist in their own tables (see schema.py); this
class is the typed, deduplicating API over them, plus traversal. Graph
*traversal* (paths, N-hop neighbourhoods) is done with :mod:`networkx`, built on
demand from the currently-active relationships -- the spec explicitly says not
to introduce a dedicated graph database "unless there is a demonstrated
architectural need", and at an interactive agent's scale an in-memory networkx
view rebuilt per traversal is simpler and fast enough.

Two integrity rules the spec calls for (Phase 13):

* Entities deduplicate on :pyattr:`Entity.key` (type + normalised name), so the
  same real thing is one node, with evidence accumulating on it.
* Relationships are *superseded*, not deleted: a contradicting edge closes the
  old one's temporal validity (``valid_to``) rather than erasing history.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import networkx as nx

from ..domain.semantic import Entity, Relationship
from ..storage.database import SQLiteDatabase
from .._clock import utcnow, utcnow_iso


class KnowledgeGraph:
    """Deduplicating entity/relationship store with networkx traversal."""

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
    # Traversal (networkx over the active edge set)
    # ------------------------------------------------------------------

    async def _active_graph(self) -> nx.DiGraph:
        rels = await self.find_relationships(active_only=True)

        def _build() -> nx.DiGraph:
            g = nx.DiGraph()
            for rel in rels:
                g.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relation=rel.relation,
                    weight=rel.weight,
                )
            return g

        return await asyncio.to_thread(_build)

    async def find_related_entities(
        self, name: str, *, entity_type: str = "concept", max_hops: int = 2
    ) -> list[Entity]:
        """Entities reachable from ``name`` within ``max_hops`` (undirected)."""
        start = await self.find_entity(name, entity_type=entity_type)
        if start is None:
            return []
        graph = (await self._active_graph()).to_undirected()
        if start.id not in graph:
            return []
        reachable = nx.single_source_shortest_path_length(
            graph, start.id, cutoff=max_hops
        )
        out: list[Entity] = []
        for node_id, hops in sorted(reachable.items(), key=lambda kv: kv[1]):
            if node_id == start.id:
                continue
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
    ) -> list[Entity]:
        """Shortest path of entities between two names (undirected), or []."""
        src = await self.find_entity(source_name, entity_type=source_type)
        dst = await self.find_entity(target_name, entity_type=target_type)
        if src is None or dst is None:
            return []
        graph = (await self._active_graph()).to_undirected()
        if src.id not in graph or dst.id not in graph:
            return []
        try:
            node_ids = nx.shortest_path(graph, src.id, dst.id)
        except nx.NetworkXNoPath:
            return []
        path: list[Entity] = []
        for node_id in node_ids:
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
