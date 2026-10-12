"""
Phase 12 -- consolidation and contradictions tests.

Exercises the hardened ``MemoryConsolidator`` via ``manager.consolidate()``:

* exact duplicates merge (evidence folds, original archived with a link)
* legitimate repeated observations stay separate (never merged)
* temporal facts: a newer OBSERVATION of the same subject supersedes
* contradictory sources link (``contradicts``) but never merge
* original evidence preserved (archived rows intact, links auditable)
* interrupted jobs resume idempotently (re-run links/merges nothing new)
* scope isolation (session vs long-term never merge)
* trading-history protection (predictions/episodes/failures/trading rows
  never near-merge by similarity)
* ambiguous candidates stay separate (with a ``related_to`` link, not a merge)
* similarity is never contradiction (low-similarity rows don't contradict)
"""

from __future__ import annotations

import pytest

from aetheros.memory.domain import (
    MemoryStatus,
    MemoryType,
    Veracity,
)


async def _remember(manager, content, **kw):
    return await manager.remember(content, **kw)


async def _links(manager, memory_id):
    return await manager._repo.linked_ids(memory_id)


# ----------------------------------------------------------------------
# Exact duplicates
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_duplicates_merge_with_evidence(manager) -> None:
    a = await _remember(manager, "User prefers the Brave browser.")
    b = await _remember(manager, "User prefers the Brave browser.")
    assert a.id != b.id

    stats = await manager.consolidate()
    assert stats["merged"] >= 1
    assert stats["archived"] >= 1

    survivors = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE and "Brave" in m.content
    ]
    assert len(survivors) == 1
    assert survivors[0].evidence_count >= 2
    # Provenance: the survivor cites what it absorbed.
    assert b.id in survivors[0].metadata.get("merged_from", []) or (
        a.id in survivors[0].metadata.get("merged_from", [])
    )
    # The archived original is intact with a link back.
    archived = await manager.get(b.id if survivors[0].id == a.id else a.id)
    assert archived is not None
    assert archived.status is MemoryStatus.ARCHIVED
    assert archived.metadata.get("archived_reason") == "consolidation_duplicate"
    neighbours = await _links(manager, archived.id)
    assert any(nid == survivors[0].id for nid, _, _ in neighbours)


@pytest.mark.asyncio
async def test_consolidation_is_idempotent(manager) -> None:
    await _remember(manager, "User prefers the Brave browser.")
    await _remember(manager, "User prefers the Brave browser.")
    first = await manager.consolidate()
    assert first["merged"] >= 1
    second = await manager.consolidate()
    assert second["merged"] == 0
    assert second["contradictions"] == 0
    assert second["superseded"] == 0
    assert second["related"] == 0


# ----------------------------------------------------------------------
# Legitimate repeated observations stay separate
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_observations_never_merge(manager) -> None:
    # Two distinct readings, same instrument, different values/times.
    await manager.remember(
        "RELIANCE last price 2500.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.OBSERVATION,
        entities=["RELIANCE"],
    )
    await manager.remember(
        "RELIANCE last price 2510.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.OBSERVATION,
        entities=["RELIANCE"],
    )
    stats = await manager.consolidate()
    assert stats["merged"] == 0
    live = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE and "RELIANCE last price" in m.content
    ]
    assert len(live) == 2


# ----------------------------------------------------------------------
# Temporal facts: supersession
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_newer_assertion_supersedes_older_with_contradiction_link(
    manager,
) -> None:
    from datetime import timedelta

    # Authoritative assertions (FACT), not measurement history: the newer
    # state description replaces the older one, and the disagreement is
    # linked so the audit trail shows both.
    old = await manager.remember(
        "NIFTY regime ranging.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.FACT,
        entities=["NIFTY"],
    )
    new = await manager.remember(
        "NIFTY regime trending.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.FACT,
        entities=["NIFTY"],
    )
    # Force a timestamp gap (same-process writes can share a timestamp).
    new_row = await manager.get(new.id)
    assert new_row is not None
    new_row.created_at = (await manager.get(old.id)).created_at + timedelta(seconds=5)
    await manager._repo.update(new_row)

    stats = await manager.consolidate()
    assert stats["superseded"] >= 1
    assert stats["contradictions"] >= 1  # disagreement recorded too
    old_row = await manager.get(old.id)
    assert old_row is not None
    assert old_row.status is MemoryStatus.ARCHIVED
    assert old_row.metadata.get("archived_reason") == "consolidation_superseded"
    assert old_row.metadata.get("superseded_by") == new.id
    neighbours = await _links(manager, old.id)
    assert any(
        nid == new.id and ltype == "supersedes" for nid, ltype, _ in neighbours
    )
    # The newer reading stays live.
    assert (await manager.get(new.id)).status is MemoryStatus.ACTIVE


@pytest.mark.asyncio
async def test_equal_timestamps_stay_separate(manager) -> None:
    a = await manager.remember(
        "NIFTY regime ranging.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.OBSERVATION,
        entities=["NIFTY"],
    )
    b = await manager.remember(
        "NIFTY regime trending.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.OBSERVATION,
        entities=["NIFTY"],
    )
    # Pin identical timestamps: ambiguous, must not supersede.
    rb = await manager.get(b.id)
    ra = await manager.get(a.id)
    assert rb is not None and ra is not None
    rb.created_at = ra.created_at
    await manager._repo.update(rb)
    stats = await manager.consolidate()
    assert stats["superseded"] == 0
    assert (await manager.get(a.id)).status is MemoryStatus.ACTIVE
    assert (await manager.get(b.id)).status is MemoryStatus.ACTIVE


# ----------------------------------------------------------------------
# Contradictions: linked, never merged
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contradictory_sources_link_and_supersede(manager) -> None:
    from datetime import timedelta

    old = await manager.remember(
        "User prefers the Brave browser.",
        memory_type=MemoryType.PREFERENCE,
        veracity=Veracity.USER_INPUT,
        entities=["Brave"],
    )
    new = await manager.remember(
        "User no longer prefers the Brave browser.",
        memory_type=MemoryType.PREFERENCE,
        veracity=Veracity.USER_INPUT,
        entities=["Brave"],
    )
    # Pin the temporal order (same-process writes can share a timestamp,
    # and equal timestamps must stay separate).
    new_row = await manager.get(new.id)
    old_row = await manager.get(old.id)
    assert new_row is not None and old_row is not None
    new_row.created_at = old_row.created_at + timedelta(seconds=5)
    await manager._repo.update(new_row)

    stats = await manager.consolidate()
    assert stats["merged"] == 0
    assert stats["contradictions"] >= 1
    assert stats["superseded"] >= 1
    # The newer preference is live; the older is archived but preserved,
    # with both the disagreement and the succession linked.
    assert (await manager.get(new.id)).status is MemoryStatus.ACTIVE
    archived_old = await manager.get(old.id)
    assert archived_old is not None
    assert archived_old.status is MemoryStatus.ARCHIVED
    neighbours = await _links(manager, old.id)
    assert any(
        nid == new.id and ltype == "contradicts" for nid, ltype, _ in neighbours
    )
    assert any(
        nid == new.id and ltype == "supersedes" for nid, ltype, _ in neighbours
    )


@pytest.mark.asyncio
async def test_low_similarity_is_never_contradiction(manager) -> None:
    await manager.remember(
        "User prefers the Brave browser.",
        memory_type=MemoryType.PREFERENCE,
        entities=["Brave"],
    )
    await manager.remember(
        "RELIANCE broke resistance at 2500.",
        memory_type=MemoryType.SEMANTIC,
        entities=["RELIANCE"],
    )
    stats = await manager.consolidate()
    assert stats["contradictions"] == 0
    assert stats["merged"] == 0


# ----------------------------------------------------------------------
# Scope isolation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scope_isolation_no_cross_scope_merge(manager) -> None:
    from aetheros.memory.domain import MemoryScope

    a = await manager.remember("Watch RELIANCE breakout.")
    # Same text, different scope: retag one as session-scoped.
    b = await manager.remember("Watch RELIANCE breakout.")
    rb = await manager.get(b.id)
    assert rb is not None
    rb.scope = MemoryScope.SESSION
    await manager._repo.update(rb)
    assert (await manager.get(a.id)).scope is not MemoryScope.SESSION

    stats = await manager.consolidate()
    assert stats["merged"] == 0
    assert (await manager.get(a.id)).status is MemoryStatus.ACTIVE
    assert (await manager.get(b.id)).status is MemoryStatus.ACTIVE


# ----------------------------------------------------------------------
# Trading-history protection
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predictions_never_merge(manager) -> None:
    from aetheros.memory.domain import PredictionMemory

    p1 = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    p2 = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    assert p1.id != p2.id
    stats = await manager.consolidate()
    assert stats["merged"] == 0
    assert (await manager.get(p1.id)).status is MemoryStatus.ACTIVE
    assert (await manager.get(p2.id)).status is MemoryStatus.ACTIVE


@pytest.mark.asyncio
async def test_episodes_and_failures_never_near_merge(manager) -> None:
    ep1 = await manager.episodes.start_episode("Scan RELIANCE", episode_id="ep-c1")
    ep2 = await manager.episodes.start_episode("Scan RELIANCE", episode_id="ep-c2")
    assert ep1.id != ep2.id
    f1 = await manager.failures.record_failure("timeout", "t1", failure_id="f-c1")
    f2 = await manager.failures.record_failure("timeout", "t1", failure_id="f-c2")
    assert f1.id != f2.id
    stats = await manager.consolidate()
    assert stats["merged"] == 0
    for mid in ("ep-c1", "ep-c2", "f-c1", "f-c2"):
        assert (await manager.get(mid)).status is MemoryStatus.ACTIVE


@pytest.mark.asyncio
async def test_distinct_entities_never_merge_on_prose(manager) -> None:
    await manager.remember(
        "Price broke above resistance.",
        memory_type=MemoryType.SEMANTIC,
        entities=["RELIANCE"],
    )
    await manager.remember(
        "Price broke above resistance.",
        memory_type=MemoryType.SEMANTIC,
        entities=["INFY"],
    )
    stats = await manager.consolidate()
    # Same prose, disjoint entities: near-merge guard refuses; ambiguous
    # link is allowed but no merge and no archive.
    assert stats["merged"] == 0
    live = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE
        and "broke above resistance" in m.content
    ]
    assert len(live) == 2


# ----------------------------------------------------------------------
# Ambiguity: separate with a link
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ambiguous_candidates_stay_separate(manager) -> None:
    await manager.remember(
        "User prefers the Brave browser for research.",
        memory_type=MemoryType.PREFERENCE,
        entities=["Brave"],
    )
    await manager.remember(
        "User prefers the Brave browser for trading.",
        memory_type=MemoryType.PREFERENCE,
        entities=["Brave"],
    )
    stats = await manager.consolidate()
    assert stats["merged"] == 0
    live = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE and "Brave" in m.content
    ]
    assert len(live) == 2


# ----------------------------------------------------------------------
# Bounded batches + interruption
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bounded_batches_cover_all_rows(manager) -> None:
    for i in range(6):
        await _remember(manager, f"Unique note number {i} about topic {i}.")
    stats = await manager.consolidate(batch_size=2)
    assert stats["batches"] >= 3
    # Unique notes: nothing merged, but every batch ran.
    assert stats["merged"] == 0


@pytest.mark.asyncio
async def test_interrupted_job_resumes_idempotently(manager) -> None:
    await _remember(manager, "User prefers the Brave browser.")
    await _remember(manager, "User prefers the Brave browser.")
    first = await manager.consolidate(batch_size=1, max_batches=1)
    assert first["batches"] == 1
    # Resume the rest: the second batch finishes the job...
    second = await manager.consolidate(batch_size=10)
    # ...and a third run finds nothing new (idempotent).
    third = await manager.consolidate()
    assert third["merged"] == 0
    assert third["contradictions"] == 0
    assert third["superseded"] == 0
    survivors = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE and "Brave" in m.content
    ]
    assert len(survivors) == 1
    _ = second


# ----------------------------------------------------------------------
# Disabled mode
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_consolidation_is_noop(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    disabled = replace(memory_config, enabled=False, consolidation_enabled=True)
    mgr = MemoryManager(disabled)
    stats = await mgr.consolidate()
    assert stats == {
        "merged": 0, "archived": 0, "promoted": 0, "contradictions": 0,
        "superseded": 0, "related": 0, "skipped_protected": 0, "batches": 0,
    }


@pytest.mark.asyncio
async def test_consolidation_flag_off_is_noop(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    off = replace(memory_config, consolidation_enabled=False)
    mgr = MemoryManager(off)
    await mgr.initialize()
    try:
        await mgr.remember("User prefers the Brave browser.")
        await mgr.remember("User prefers the Brave browser.")
        stats = await mgr.consolidate()
        assert stats["merged"] == 0
        assert stats["batches"] == 0
    finally:
        await mgr.shutdown()
