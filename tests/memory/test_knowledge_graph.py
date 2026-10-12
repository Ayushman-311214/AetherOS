"""
Phase 7 — knowledge-graph store tests.

These exercise the *real* persisted graph: entities/relationships in SQLite via
the on-disk `SQLiteDatabase`, directed+temporal edges, dedup/supersede, the
invalid-reference guard, and bounded BFS traversal (depth, fan-out, result
count, cycles, time limit). No mocks: every assertion runs against actual rows.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from aetheros.core.errors.memory_error import MemoryValidationError
from aetheros.memory.domain.semantic import Entity, Relationship
from aetheros.memory.graph.store import KnowledgeGraph, TraversalBounds
from aetheros.memory.storage import SQLiteDatabase

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def graph(database: SQLiteDatabase) -> AsyncIterator[KnowledgeGraph]:
    yield KnowledgeGraph(database)


async def _node(graph: KnowledgeGraph, name: str, **kw) -> Entity:
    return await graph.upsert_entity(Entity(name=name, **kw))


async def _edge(
    graph: KnowledgeGraph, a: Entity, b: Entity, relation: str = "related_to", **kw
) -> Relationship:
    return await graph.add_relationship(
        Relationship(source_id=a.id, target_id=b.id, relation=relation, **kw)
    )


# ---------------------------------------------------------------------------
# Entities: persistence, dedup, provenance
# ---------------------------------------------------------------------------


async def test_entity_upsert_dedups_on_key(graph: KnowledgeGraph) -> None:
    first = await _node(graph, "TradingView", attributes={"vendor": "TV"})
    again = await _node(graph, "tradingview", aliases=["TV"])  # same key (lowercased)
    assert again.id == first.id
    stats = await graph.stats()
    assert stats["entities"] == 1
    stored = await graph.get_entity(first.id)
    assert stored is not None
    assert "TV" in stored.aliases
    assert stored.attributes["vendor"] == "TV"  # merged, not lost


async def test_entity_persists_across_reopen(tmp_path) -> None:
    path = str(tmp_path / "graph.db")
    db = SQLiteDatabase(path)
    db.connect()
    g = KnowledgeGraph(db)
    ent = await _node(g, "RELIANCE", entity_type="instrument")
    db.close()

    db2 = SQLiteDatabase(path)
    db2.connect()
    try:
        g2 = KnowledgeGraph(db2)
        found = await g2.find_entity("RELIANCE", entity_type="instrument")
        assert found is not None
        assert found.id == ent.id
    finally:
        db2.close()


# ---------------------------------------------------------------------------
# Relationships: direction, dedup, supersede, invalid refs
# ---------------------------------------------------------------------------


async def test_relationship_invalid_reference_rejected(graph: KnowledgeGraph) -> None:
    real = await _node(graph, "user")
    with pytest.raises(MemoryValidationError):
        await graph.add_relationship(
            Relationship(source_id=real.id, target_id="does-not-exist")
        )
    with pytest.raises(MemoryValidationError):
        await graph.add_relationship(
            Relationship(source_id="ghost", target_id=real.id)
        )


async def test_duplicate_edge_reinforces_not_duplicates(graph: KnowledgeGraph) -> None:
    a = await _node(graph, "user")
    b = await _node(graph, "TradingView")
    r1 = await _edge(graph, a, b, "uses", evidence_memory_ids=["m1"])
    r2 = await _edge(graph, a, b, "uses", evidence_memory_ids=["m2"])
    assert r1.id == r2.id  # same edge, reinforced
    assert r2.evidence_count == 2
    assert set(r2.evidence_memory_ids) == {"m1", "m2"}
    active = await graph.find_relationships(source_id=a.id, relation="uses")
    assert len(active) == 1


async def test_edge_direction_is_respected(graph: KnowledgeGraph) -> None:
    a = await _node(graph, "A")
    b = await _node(graph, "B")
    await _edge(graph, a, b, "contains")
    assert len(await graph.find_relationships(source_id=a.id)) == 1
    assert len(await graph.find_relationships(target_id=a.id)) == 0
    assert len(await graph.find_relationships(target_id=b.id)) == 1
    # Different relation between the same pair is a distinct edge.
    await _edge(graph, a, b, "uses")
    assert len(await graph.find_relationships(source_id=a.id)) == 2


async def test_supersede_closes_temporal_validity(graph: KnowledgeGraph) -> None:
    a = await _node(graph, "user")
    chrome = await _node(graph, "Chrome")
    rel = await _edge(graph, a, chrome, "prefers")
    await graph.supersede_relationship(rel.id)
    assert await graph.find_relationships(source_id=a.id, active_only=True) == []
    # History is retained, not deleted.
    all_edges = await graph.find_relationships(source_id=a.id, active_only=False)
    assert len(all_edges) == 1
    assert all_edges[0].valid_to is not None


async def test_superseded_edge_excluded_from_traversal(graph: KnowledgeGraph) -> None:
    a = await _node(graph, "user")
    b = await _node(graph, "Chrome")
    rel = await _edge(graph, a, b, "prefers")
    assert [e.name for e in await graph.find_related_entities("user")] == ["Chrome"]
    await graph.supersede_relationship(rel.id)
    assert await graph.find_related_entities("user") == []
    assert await graph.find_path("user", "Chrome") == []


# ---------------------------------------------------------------------------
# Traversal: reachability, paths, direction-agnostic
# ---------------------------------------------------------------------------


async def test_find_related_and_path(graph: KnowledgeGraph) -> None:
    user = await _node(graph, "user")
    tv = await _node(graph, "TradingView")
    rsi = await _node(graph, "RSI")
    await _edge(graph, user, tv, "uses")
    await _edge(graph, tv, rsi, "contains")

    related = {e.name for e in await graph.find_related_entities("user", max_hops=2)}
    assert related == {"TradingView", "RSI"}

    path = [e.name for e in await graph.find_path("user", "RSI")]
    assert path == ["user", "TradingView", "RSI"]


async def test_find_path_same_node_and_missing(graph: KnowledgeGraph) -> None:
    await _node(graph, "A")
    await _node(graph, "B")  # unconnected
    assert [e.name for e in await graph.find_path("A", "A")] == ["A"]
    assert await graph.find_path("A", "B") == []  # no edge
    assert await graph.find_path("A", "nope") == []  # unknown target


# ---------------------------------------------------------------------------
# Bounds: depth, fan-out, result count, cycles, time
# ---------------------------------------------------------------------------


async def test_max_hops_bounds_reachability(graph: KnowledgeGraph) -> None:
    # chain: n0 - n1 - n2 - n3
    nodes = [await _node(graph, f"n{i}") for i in range(4)]
    for x, y in zip(nodes, nodes[1:], strict=False):
        await _edge(graph, x, y)
    one = {e.name for e in await graph.find_related_entities("n0", max_hops=1)}
    assert one == {"n1"}
    two = {e.name for e in await graph.find_related_entities("n0", max_hops=2)}
    assert two == {"n1", "n2"}


async def test_find_path_respects_hop_bound(graph: KnowledgeGraph) -> None:
    nodes = [await _node(graph, f"n{i}") for i in range(4)]
    for x, y in zip(nodes, nodes[1:], strict=False):
        await _edge(graph, x, y)
    # n0 -> n3 is 3 hops; a 2-hop bound must not find it.
    tight = TraversalBounds(max_hops=2)
    assert await graph.find_path("n0", "n3", bounds=tight) == []
    loose = TraversalBounds(max_hops=3)
    assert [e.name for e in await graph.find_path("n0", "n3", bounds=loose)] == [
        "n0", "n1", "n2", "n3",
    ]


async def test_max_results_bound(graph: KnowledgeGraph) -> None:
    hub = await _node(graph, "hub")
    for i in range(10):
        leaf = await _node(graph, f"leaf{i}")
        await _edge(graph, hub, leaf)
    bounds = TraversalBounds(max_hops=1, max_results=3)
    found = await graph.find_related_entities("hub", bounds=bounds)
    assert len(found) == 3


async def test_max_fanout_bound(graph: KnowledgeGraph) -> None:
    hub = await _node(graph, "hub")
    for i in range(10):
        leaf = await _node(graph, f"leaf{i}")
        await _edge(graph, hub, leaf)
    bounds = TraversalBounds(max_hops=1, max_fanout=4, max_results=256)
    found = await graph.find_related_entities("hub", bounds=bounds)
    assert len(found) == 4  # only 4 of the hub's 10 neighbours expanded


async def test_cycle_is_handled(graph: KnowledgeGraph) -> None:
    a = await _node(graph, "A")
    b = await _node(graph, "B")
    c = await _node(graph, "C")
    await _edge(graph, a, b)
    await _edge(graph, b, c)
    await _edge(graph, c, a)  # closes the cycle
    related = {e.name for e in await graph.find_related_entities("A", max_hops=5)}
    assert related == {"B", "C"}  # terminates, each node once
    assert [e.name for e in await graph.find_path("A", "C")] == ["A", "C"]  # direct


async def test_time_limit_stops_traversal(graph: KnowledgeGraph) -> None:
    nodes = [await _node(graph, f"n{i}") for i in range(6)]
    for x, y in zip(nodes, nodes[1:], strict=False):
        await _edge(graph, x, y)
    # An already-expired budget yields no expansion beyond the start node.
    bounds = TraversalBounds(max_hops=5, time_limit_s=1e-9)
    time.sleep(0.001)
    found = await graph.find_related_entities("n0", bounds=bounds)
    assert found == []


async def test_relation_filtered_traversal(graph: KnowledgeGraph) -> None:
    user = await _node(graph, "user")
    tv = await _node(graph, "TradingView")
    chrome = await _node(graph, "Chrome")
    await _edge(graph, user, tv, "uses")
    await _edge(graph, user, chrome, "prefers")
    uses = {e.name for e in await graph.find_related_entities("user", relation="uses")}
    assert uses == {"TradingView"}


async def test_bounds_validation() -> None:
    with pytest.raises(ValueError):
        TraversalBounds(max_fanout=0)
    with pytest.raises(ValueError):
        TraversalBounds(time_limit_s=0)
    with pytest.raises(ValueError):
        TraversalBounds(max_hops=-1)


# ---------------------------------------------------------------------------
# Isolation between distinct DBs (scope boundary)
# ---------------------------------------------------------------------------


async def test_separate_databases_are_isolated(tmp_path) -> None:
    db_a = SQLiteDatabase(str(tmp_path / "a.db"))
    db_b = SQLiteDatabase(str(tmp_path / "b.db"))
    db_a.connect()
    db_b.connect()
    try:
        ga, gb = KnowledgeGraph(db_a), KnowledgeGraph(db_b)
        await _node(ga, "secret-a")
        assert await gb.find_entity("secret-a") is None
        assert (await gb.stats())["entities"] == 0
    finally:
        db_a.close()
        db_b.close()
