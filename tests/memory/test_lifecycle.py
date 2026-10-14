"""
Phase 14 -- decay, retention and lifecycle tests.

Exercises the hardened ``MemoryLifecycle`` via ``manager.decay()`` /
``manager.reactivate()`` with a controllable clock:

* time boundaries (STALE / DECAYED / ARCHIVED at 3/6/9 half-lives)
* high-importance exemptions (CRITICAL never auto-archives)
* trading-history protection (TRADING / PREDICTION skip the neglect chain)
* expired working memory (Phase 9 sweep still owns working memory)
* archived retrieval policy (excluded by default, included with flag,
  deleted never served)
* deleted-record exclusion (decay never touches DELETED)
* interrupted jobs (bounded batches resume; re-runs are idempotent)
* repeated execution (evaluate is a fixed point)
* concurrent-update safety (version-guarded transitions skip, never clobber)
* projection propagation (vectors follow status; verify/repair agree)
* reactivation (explicit verb + automatic via fresh access)
* confidence/status separation (decay never writes confidence)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aetheros.memory.domain import (
    MemoryImportance,
    MemoryStatus,
    PredictionMemory,
    Veracity,
)


def _t0() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


async def _age(manager, memory_id: str, *, days: float, now: datetime) -> None:
    """Backdate every touch timestamp so the row reads ``days`` old."""
    row = await manager.get(memory_id)
    assert row is not None
    stamp = now - timedelta(days=days)
    row.created_at = stamp
    row.updated_at = stamp
    row.last_accessed_at = stamp
    await manager._repo.update(row)


# ----------------------------------------------------------------------
# Time boundaries (controllable clock, default 30-day half-life)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neglect_chain_boundaries(manager) -> None:
    fresh = await manager.remember("Fresh note.")
    stale = await manager.remember("Stale note.")
    decayed = await manager.remember("Decayed note.")
    archived = await manager.remember("Archived note.")
    now = _t0()
    await _age(manager, stale.id, days=100, now=now)  # past 90d -> STALE
    await _age(manager, decayed.id, days=200, now=now)  # past 180d -> DECAYED
    await _age(manager, archived.id, days=300, now=now)  # past 270d -> ARCHIVED

    stats = await manager.decay(now=now)
    assert stats.get("stale", 0) >= 1
    assert stats.get("decayed", 0) >= 1
    assert stats.get("archived", 0) >= 1
    assert (await manager.get(fresh.id)).status is MemoryStatus.ACTIVE
    assert (await manager.get(stale.id)).status is MemoryStatus.STALE
    assert (await manager.get(decayed.id)).status is MemoryStatus.DECAYED
    assert (await manager.get(archived.id)).status is MemoryStatus.ARCHIVED


@pytest.mark.asyncio
async def test_boundary_exactness(manager) -> None:
    from aetheros.memory.services.lifecycle import MemoryLifecycle

    lc = MemoryLifecycle(manager.config)
    m = await manager.remember("Boundary note.")
    row = await manager.get(m.id)
    assert row is not None
    # Boundaries are relative to the row's own touch time: evaluate around
    # the 3/6/9 half-life marks (default 30-day half-life).
    ref = row.updated_at
    assert lc.evaluate(row, now=ref + timedelta(days=89)) is MemoryStatus.ACTIVE
    assert lc.evaluate(row, now=ref + timedelta(days=91)) is MemoryStatus.STALE
    assert lc.evaluate(row, now=ref + timedelta(days=179)) is MemoryStatus.STALE
    assert lc.evaluate(row, now=ref + timedelta(days=181)) is MemoryStatus.DECAYED
    assert lc.evaluate(row, now=ref + timedelta(days=269)) is MemoryStatus.DECAYED
    assert lc.evaluate(row, now=ref + timedelta(days=271)) is MemoryStatus.ARCHIVED


@pytest.mark.asyncio
async def test_ttl_expiry_beats_neglect_chain(manager) -> None:
    m = await manager.remember("Short-lived note.")
    row = await manager.get(m.id)
    assert row is not None
    row.expires_at = _t0() - timedelta(seconds=1)
    await manager._repo.update(row)
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.EXPIRED


# ----------------------------------------------------------------------
# Exemptions: importance, trading history, permanent scope
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_critical_never_auto_archives(manager) -> None:
    from aetheros.memory.domain import MemoryScope

    # Layer 1 (policy): CRITICAL importance is stamped PERMANENT at write
    # time, so ordinary neglect never demotes it at all.
    m = await manager.remember(
        "Critical standing order.", importance=MemoryImportance.CRITICAL
    )
    row = await manager.get(m.id)
    assert row is not None
    assert row.scope is MemoryScope.PERMANENT
    await _age(manager, m.id, days=1000, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ACTIVE

    # Layer 2 (lifecycle veto): a CRITICAL row explicitly scoped LONG_TERM
    # still shows neglect as DECAYED, but the archive step requires a human.
    row2 = await manager.get(m.id)
    assert row2 is not None
    row2.scope = MemoryScope.LONG_TERM
    await manager._repo.update(row2)
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.DECAYED


@pytest.mark.asyncio
async def test_trading_history_protected_from_decay(manager) -> None:
    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    await _age(manager, pred.id, days=1000, now=_t0())
    stats = await manager.decay(now=_t0())
    assert (await manager.get(pred.id)).status is MemoryStatus.ACTIVE
    assert stats.get("archived", 0) == 0

    # A bare PREDICTION-veracity row is protected too.
    m = await manager.remember("Model says UP.", veracity=Veracity.PREDICTION)
    await _age(manager, m.id, days=1000, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ACTIVE

    # But an explicitly-set TTL still expires protected history.
    row = await manager.get(pred.id)
    assert row is not None
    row.expires_at = _t0() - timedelta(seconds=1)
    await manager._repo.update(row)
    await manager.decay(now=_t0())
    assert (await manager.get(pred.id)).status is MemoryStatus.EXPIRED


@pytest.mark.asyncio
async def test_low_confidence_flag_independent_of_age(manager) -> None:
    m = await manager.remember("Shaky note.", confidence=0.1)
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.LOW_CONFIDENCE


# ----------------------------------------------------------------------
# Archived retrieval policy + deleted exclusion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archived_excluded_by_default(manager) -> None:
    m = await manager.remember("Fading note about the Zorblax project.")
    await _age(manager, m.id, days=300, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ARCHIVED

    from aetheros.memory.domain import MemoryQuery

    default = await manager.retrieve(
        "Zorblax project", query=MemoryQuery(text="Zorblax project")
    )
    assert all(r.memory.id != m.id for r in default)
    with_archived = await manager.retrieve(
        "Zorblax project",
        query=MemoryQuery(text="Zorblax project", include_archived=True),
    )
    assert any(r.memory.id == m.id for r in with_archived)


@pytest.mark.asyncio
async def test_decayed_stays_recallable_but_ranks_last(manager) -> None:
    old = await manager.remember("Decayed Zorblax note.")
    new = await manager.remember("Fresh Zorblax note.")
    await _age(manager, old.id, days=200, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(old.id)).status is MemoryStatus.DECAYED
    results = await manager.retrieve("Zorblax note")
    ids = [r.memory.id for r in results]
    assert old.id in ids and new.id in ids
    assert ids.index(new.id) < ids.index(old.id)


@pytest.mark.asyncio
async def test_decay_never_touches_deleted(manager) -> None:
    m = await manager.remember("Doomed note.")
    await manager.forget(m.id)
    await _age(manager, m.id, days=1000, now=_t0())
    stats = await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.DELETED
    assert stats.get("deleted", 0) in (0, None)


@pytest.mark.asyncio
async def test_deleted_never_served_even_with_flag(manager) -> None:
    from aetheros.memory.domain import MemoryQuery

    m = await manager.remember("Gone Zorblax note.")
    await manager.forget(m.id)
    results = await manager.retrieve(
        "Zorblax", query=MemoryQuery(text="Zorblax", include_archived=True)
    )
    assert all(r.memory.id != m.id for r in results)


# ----------------------------------------------------------------------
# Batches, interruption, idempotency, conflicts
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bounded_batches_and_resume(manager) -> None:
    for i in range(6):
        m = await manager.remember(f"Batch note {i} about topic {i}.")
        await _age(manager, m.id, days=300, now=_t0())
    first = await manager.decay(now=_t0(), batch_size=2, max_batches=1)
    assert first.get("batches") == 1
    rest = await manager.decay(now=_t0(), batch_size=10)
    assert rest.get("archived", 0) >= 1
    # Third run: fixed point, nothing new.
    third = await manager.decay(now=_t0())
    assert third.get("archived", 0) == 0
    assert third.get("stale", 0) == 0
    assert third.get("decayed", 0) == 0


@pytest.mark.asyncio
async def test_concurrent_update_wins_over_decay(manager) -> None:
    m = await manager.remember("Contested note.")
    await _age(manager, m.id, days=300, now=_t0())
    row = await manager.get(m.id)
    assert row is not None
    stale_version = row.version
    # A concurrent writer edits first...
    await manager.update(m.id, content="Edited by a human.")
    # ...then decay evaluates the STALE snapshot it read earlier. Simulate
    # by driving the guarded write with the old version directly.
    from aetheros.memory.services.lifecycle import MemoryLifecycle

    lc = MemoryLifecycle(manager.config)
    fresh = await manager.get(m.id)
    assert fresh is not None
    assert fresh.version == stale_version + 1
    # The transition helper skips (never clobbers) on a lost race.
    fresh.status = MemoryStatus.ARCHIVED
    fresh.version += 1
    won = await manager._repo.update_guarded(fresh, stale_version)
    assert not won
    # Human content survived; a later pass re-evaluates the fresh row.
    assert (await manager.get(m.id)).content == "Edited by a human."
    _ = lc


@pytest.mark.asyncio
async def test_skipped_conflict_counted(manager, monkeypatch) -> None:
    m = await manager.remember("Conflicted note.")
    await _age(manager, m.id, days=300, now=_t0())
    real_guarded = manager._repo.update_guarded

    async def always_lose(memory, expected_version):
        _ = memory, expected_version
        return False

    monkeypatch.setattr(manager._repo, "update_guarded", always_lose)
    stats = await manager.decay(now=_t0())
    assert stats.get("skipped_conflict", 0) >= 1
    monkeypatch.setattr(manager._repo, "update_guarded", real_guarded)


# ----------------------------------------------------------------------
# Projection propagation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_drops_vector_and_verify_agrees(manager) -> None:
    m = await manager.remember("Fading vector note.")
    assert await manager._vectors.ids() != []
    await _age(manager, m.id, days=300, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ARCHIVED
    # No stale vector lingering for a non-recallable row...
    assert m.id not in await manager._vectors.ids()
    # ...and the projection checker agrees (no phantom "missing" drift).
    report = await manager.verify_projection()
    assert m.id not in report["missing"]
    assert m.id not in report["orphan"]
    assert report["consistent"]


@pytest.mark.asyncio
async def test_recallable_transition_keeps_vector(manager) -> None:
    m = await manager.remember("Stale-but-served note.")
    await _age(manager, m.id, days=100, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.STALE
    # INSERT OR REPLACE would otherwise drop it via FK cascade: the pass
    # re-indexes recallable rows on the same pass.
    assert m.id in await manager._vectors.ids()


# ----------------------------------------------------------------------
# Reactivation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_reactivate_restores_and_reindexes(manager) -> None:
    m = await manager.remember("Revived note.")
    await _age(manager, m.id, days=300, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ARCHIVED
    assert m.id not in await manager._vectors.ids()

    revived = await manager.reactivate(m.id)
    assert revived.status is MemoryStatus.ACTIVE
    assert m.id in await manager._vectors.ids()
    results = await manager.retrieve("Revived note")
    assert any(r.memory.id == m.id for r in results)


@pytest.mark.asyncio
async def test_reactivate_refuses_deleted_and_missing(manager) -> None:
    from aetheros.core.errors.memory_error import (
        MemoryNotFoundError,
        MemoryValidationError,
    )

    with pytest.raises(MemoryNotFoundError):
        await manager.reactivate("no-such-id")
    m = await manager.remember("Deleted note.")
    await manager.forget(m.id)
    with pytest.raises(MemoryValidationError):
        await manager.reactivate(m.id)


@pytest.mark.asyncio
async def test_access_reactivates_stale_automatically(manager) -> None:
    m = await manager.remember("Touched stale note.")
    await _age(manager, m.id, days=100, now=_t0())
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.STALE
    # Fresh access restores recency; the next pass re-evaluates to ACTIVE
    # with no explicit verb (evaluate is a pure function of state).
    row = await manager.get(m.id)
    assert row is not None
    row.register_access(at=_t0())
    await manager._repo.update(row)
    await manager.decay(now=_t0())
    assert (await manager.get(m.id)).status is MemoryStatus.ACTIVE


# ----------------------------------------------------------------------
# Separation: decay never writes confidence; working memory untouched
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_never_writes_confidence(manager) -> None:
    m = await manager.remember("Confident old note.", confidence=0.8)
    await _age(manager, m.id, days=300, now=_t0())
    await manager.decay(now=_t0())
    row = await manager.get(m.id)
    assert row is not None
    assert row.confidence == pytest.approx(0.8)  # status moved, number didn't
    assert row.status is MemoryStatus.ARCHIVED


@pytest.mark.asyncio
async def test_working_memory_expiry_untouched_by_decay(manager) -> None:
    manager.working.add("scratch", "ephemeral", session_id="S")
    stats = await manager.decay(now=_t0())
    # Decay governs durable rows only; working memory is Phase 9's domain.
    assert len(manager.working.items(session_id="S")) == 1
    assert stats.get("batches", 0) >= 0


@pytest.mark.asyncio
async def test_disabled_decay_is_noop(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    disabled = replace(memory_config, enabled=False, decay_enabled=True)
    mgr = MemoryManager(disabled)
    assert await mgr.decay() == {}
