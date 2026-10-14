"""
Phase 15 -- user memory controls tests.

Exercises ``MemoryManager.controls`` (``UserControls``) plus the hardened
``forget`` path, coordinated erasure, tools and CLI surface:

* authorization (own scope reads/writes/export/stats)
* cross-scope denial (read/correct/forget/erase/export reveal nothing)
* correction precedence (latest wins, version bumped, history retained)
* export fidelity (every row round-trips through Memory.from_dict; no
  vectors/SQL/paths)
* disabled writes/recall (global master switch + session/user gates)
* deleted data exclusion (recall, export default, vectors)
* pending-job behavior (maintenance verbs report honestly when disabled)
* trading-history guard (refuse without flag; allow with flag)
* coordinated hard erase (row + vector + links + graph evidence gone)
* no raw storage internals exposed (tools/CLI return plain dicts/strings)
"""

from __future__ import annotations

import pytest

from aetheros.memory.domain import (
    Memory,
    MemorySource,
    MemoryStatus,
    Veracity,
)


async def _scoped(manager, content, *, user_id=None, session_id=None, **kw):
    m = await manager.remember(content, **kw)
    row = await manager.get(m.id)
    assert row is not None
    meta = dict(row.metadata)
    if user_id is not None:
        meta["user_id"] = user_id
    if session_id is not None:
        meta["session_id"] = session_id
    if meta != row.metadata:
        row.metadata = meta
        await manager._repo.update(row)
    return await manager.get(m.id)


# ----------------------------------------------------------------------
# Authorization + cross-scope denial
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_own_scope_inspect_and_list(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    m = await _scoped(manager, "Aarav's browser choice.", user_id="aarav")
    seen = await manager.controls.inspect(m.id, user_id="aarav")
    assert seen["id"] == m.id
    listed = await manager.controls.list_scope(user_id="aarav")
    assert {r["id"] for r in listed} == {m.id}
    # Operator-global view (no scope) sees everything.
    assert any(r["id"] == m.id for r in await manager.controls.list_scope())
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.inspect("missing-id", user_id="aarav")


@pytest.mark.asyncio
async def test_cross_scope_denial_reveals_nothing(manager) -> None:
    from aetheros.core.errors.memory_error import (
        MemoryNotFoundError,
        MemoryValidationError,
    )

    a = await _scoped(manager, "Aarav's secret note.", user_id="aarav")
    b = await _scoped(manager, "Blair's secret note.", user_id="blair")

    # Reads.
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.inspect(a.id, user_id="blair")
    blair_listed = await manager.controls.list_scope(user_id="blair")
    assert {r["id"] for r in blair_listed} == {b.id}
    # Writes (disabled-scope error takes precedence only when disabled;
    # otherwise scope denial).
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.correct(a.id, "hijacked", user_id="blair")
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.forget(a.id, user_id="blair")
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.erase(a.id, user_id="blair")
    # Export in Blair's scope contains no Aarav row.
    export = await manager.controls.export_scope(user_id="blair")
    assert {m["id"] for m in export["memories"]} == {b.id}
    _ = MemoryValidationError  # (used below for history-guard tests)


@pytest.mark.asyncio
async def test_session_scoping(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    m = await _scoped(manager, "Session note.", user_id="u", session_id="s1")
    assert (await manager.controls.inspect(m.id, user_id="u", session_id="s1"))[
        "id"
    ] == m.id
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.inspect(m.id, user_id="u", session_id="s2")
    # Unscoped legacy rows belong to the operator: visible in any session.
    plain = await manager.remember("Legacy unscoped note.")
    assert (
        await manager.controls.inspect(plain.id, user_id="u", session_id="s9")
    )["id"] == plain.id


# ----------------------------------------------------------------------
# Correction precedence + history
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correction_precedence_and_history(manager) -> None:
    from aetheros.memory.domain import Preference, PreferenceKind

    m = await manager.remember_preference(
        Preference(subject="browser", value="Brave", kind=PreferenceKind.EXPLICIT)
    )
    v0 = m.version
    r1 = await manager.controls.correct(m.id, "User prefers Firefox.")
    assert r1["applied"] and r1["version"] == v0 + 1
    r2 = await manager.controls.correct(m.id, "User prefers Arc.")
    assert r2["applied"] and r2["version"] == v0 + 2
    row = await manager.get(m.id)
    assert row is not None
    assert row.content == "User prefers Arc."  # latest wins
    history = await manager.confidence.history(m.id)
    rules = [e["rule"] for e in history]
    assert rules.count("correct") == 2  # both retained, attributable


@pytest.mark.asyncio
async def test_correct_refuses_immutable_history(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    with pytest.raises(MemoryValidationError):
        await manager.controls.correct(pred.id, "rewritten")


# ----------------------------------------------------------------------
# Soft forget: immediate exclusion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_forget_excludes_immediately(manager) -> None:
    m = await manager.remember("Forgettable Zorblax note.")
    assert m.id in await manager._vectors.ids()
    result = await manager.controls.forget(m.id)
    assert result["forgotten"] and not result["hard"]
    row = await manager.get(m.id)
    assert row is not None and row.status is MemoryStatus.DELETED
    # Vector gone now (not waiting for a sweep)...
    assert m.id not in await manager._vectors.ids()
    # ...recall clean (authoritative filter)...
    assert all(
        r.memory.id != m.id for r in await manager.retrieve("Zorblax")
    )
    # ...and default export/listings skip it.
    export = await manager.controls.export_scope()
    assert all(x["id"] != m.id for x in export["memories"])
    assert all(
        r["id"] != m.id for r in await manager.controls.list_scope()
    )
    # Audit read still possible with the explicit flag.
    seen = await manager.controls.inspect(m.id, include_deleted=True)
    assert seen["id"] == m.id


@pytest.mark.asyncio
async def test_forget_missing_reads_as_absent(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    with pytest.raises(MemoryNotFoundError):
        await manager.controls.forget("no-such-id")
    with pytest.raises(MemoryNotFoundError):
        await manager.controls.erase("no-such-id")


# ----------------------------------------------------------------------
# Coordinated hard erase
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_erase_is_coordinated(manager) -> None:
    a = await manager.remember(
        "Erasable note about Zorblax.", entities=["Zorblax", "Research"]
    )
    b = await manager.remember("Neighbour note about Zorblax.")
    await manager.link(a.id, b.id, link_type="related_to")
    assert await manager._repo.linked_ids(a.id)
    # Graph evidence pointer exists (writer links co-referenced entity
    # pairs with this memory as evidence).
    holders = [
        rel
        for rel in await manager.graph.find_relationships(active_only=False)
        if a.id in rel.evidence_memory_ids
    ]
    assert holders, "expected a graph edge citing the erasable row"

    result = await manager.controls.erase(a.id)
    assert result["erased"]
    assert result["links_removed"] >= 1
    # Row gone, vector gone, links gone, evidence pointers gone.
    assert await manager.get(a.id) is None
    assert a.id not in await manager._vectors.ids()
    assert await manager._repo.linked_ids(a.id) == []
    assert await manager._repo.linked_ids(b.id) == []
    for rel in await manager.graph.find_relationships(active_only=False):
        assert a.id not in rel.evidence_memory_ids
    # Neighbour untouched.
    assert (await manager.get(b.id)) is not None
    assert all(
        r.memory.id != a.id for r in await manager.retrieve("Zorblax")
    )


@pytest.mark.asyncio
async def test_history_guard_and_explicit_override(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    # Ordinary forget/erase stop at the guard (documented policy).
    with pytest.raises(MemoryValidationError):
        await manager.controls.forget(pred.id)
    with pytest.raises(MemoryValidationError):
        await manager.controls.erase(pred.id)
    assert (await manager.get(pred.id)) is not None
    # Explicit, open override proceeds with full coordination.
    result = await manager.controls.erase(pred.id, allow_history=True)
    assert result["erased"]
    assert await manager.get(pred.id) is None


# ----------------------------------------------------------------------
# Export fidelity + no internals
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_fidelity_round_trip(manager) -> None:
    m = await manager.remember("Exportable fact.", entities=["Zorblax"])
    await manager.confidence.confirm(m.id, source="s1")
    n = await manager.remember("Second fact.")
    await manager.link(m.id, n.id, link_type="related_to")

    export = await manager.controls.export_scope()
    assert export["format_version"] == 1
    assert {x["id"] for x in export["memories"]} == {m.id, n.id}
    # Every row round-trips (fidelity).
    for payload in export["memories"]:
        assert Memory.from_dict(payload).to_dict()["id"] == payload["id"]
    # Links exported with the pair.
    assert any(
        link["from_id"] == m.id and link["to_id"] == n.id
        for link in export["links"]
    )
    # Confidence history travels with the row.
    by_id = {x["id"]: x for x in export["memories"]}
    assert any(
        e["rule"] == "confirm"
        for e in by_id[m.id]["metadata"].get("confidence_history", [])
    )
    # No raw internals: no vectors, SQL, file paths, connections.
    blob = str(export)
    assert "vector" not in blob.lower()
    assert ".db" not in blob and "sqlite" not in blob.lower()
    assert "SELECT" not in blob


@pytest.mark.asyncio
async def test_stats_scope_counts(manager) -> None:
    await _scoped(manager, "U1 note one.", user_id="u1")
    await _scoped(manager, "U1 note two.", user_id="u1")
    await _scoped(manager, "U2 note.", user_id="u2")
    s1 = await manager.controls.stats_scope(user_id="u1")
    assert s1["total"] == 2
    assert s1["by_status"].get("active", 0) == 2
    s2 = await manager.controls.stats_scope(user_id="u2")
    assert s2["total"] == 1
    # No content in stats.
    assert "U1 note one" not in str(s1)


# ----------------------------------------------------------------------
# Disable: global vs session/user
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_disable_writes_and_recall(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager
    from aetheros.memory.services.results import WriteStatus

    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    await mgr.initialize()
    try:
        assert mgr.controls.is_disabled()
        assert mgr.controls.is_disabled(user_id="u", session_id="s")
        # Writes report honestly; recall degrades; maintenance is zeroed.
        result = await mgr.store(Memory(content="x", source=MemorySource()))
        assert result.status is WriteStatus.UNAVAILABLE
        assert (await mgr.retrieve("x")) == []
        assert await mgr.consolidate() == {
            "merged": 0, "archived": 0, "promoted": 0, "contradictions": 0,
            "superseded": 0, "related": 0, "skipped_protected": 0, "batches": 0,
        }
        assert await mgr.decay() == {}
        # Absence is checked before the disabled gate (one denial shape,
        # no existence oracle); the gate itself is pinned by the
        # session-disable tests with live rows.
        from aetheros.core.errors.memory_error import MemoryNotFoundError

        with pytest.raises(MemoryNotFoundError):
            await mgr.controls.correct("any-id", "new")
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_session_disable_purges_working_and_gates_writes(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError

    manager.working.add("scratch", "ephemeral", session_id="S-off")
    m = await _scoped(manager, "Session note.", user_id="u", session_id="S-off")
    assert not manager.controls.is_disabled(session_id="S-off")

    result = await manager.controls.disable_session("S-off")
    assert result["disabled"] and result["working_purged"] >= 1
    assert manager.controls.is_disabled(session_id="S-off")
    assert not manager.controls.is_disabled(session_id="S-other")
    # Working context gone now...
    assert manager.working.items(session_id="S-off") == []
    # ...scoped writes refused...
    with pytest.raises(MemoryValidationError):
        await manager.controls.correct(m.id, "edit", session_id="S-off")
    with pytest.raises(MemoryValidationError):
        await manager.controls.forget(m.id, session_id="S-off")
    # ...but reads still serve the durable store (inspection stays available).
    assert (await manager.controls.inspect(m.id, session_id="S-off"))["id"] == m.id
    # Re-enable restores writes.
    await manager.controls.enable_session("S-off")
    assert not manager.controls.is_disabled(session_id="S-off")


@pytest.mark.asyncio
async def test_user_disable_gate(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError

    m = await _scoped(manager, "User note.", user_id="u-off")
    await manager.controls.disable_user("u-off")
    assert manager.controls.is_disabled(user_id="u-off")
    with pytest.raises(MemoryValidationError):
        await manager.controls.erase(m.id, user_id="u-off")
    await manager.controls.enable_user("u-off")
    assert not manager.controls.is_disabled(user_id="u-off")


# ----------------------------------------------------------------------
# Pending-job behavior when disabled
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_maintenance_verbs_zeroed_when_disabled(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    await mgr.initialize()
    try:
        # No queues exist in this subsystem (all verbs caller-invoked), so
        # "pending jobs" can only mean the maintenance verbs: they report
        # honest zeroed reports instead of pretending to run.
        assert await mgr.consolidate() == {
            "merged": 0, "archived": 0, "promoted": 0, "contradictions": 0,
            "superseded": 0, "related": 0, "skipped_protected": 0, "batches": 0,
        }
        assert await mgr.decay() == {}
        assert (await mgr.retrieve("anything")) == []
    finally:
        await mgr.shutdown()


# ----------------------------------------------------------------------
# Tools + CLI surface (no raw internals)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tools_round_trip_without_internals(manager) -> None:
    from aetheros.core.container import container
    from aetheros.memory import tools as memtools
    from aetheros.memory.services.manager import MemoryManager

    container.register_singleton(MemoryManager, lambda: manager)
    try:
        created = await memtools.remember("Tool-created Zorblax fact.")
        assert created["ok"] and "memory_id" in created
        mid = created["memory_id"]
        shown = await memtools.get_memory(mid)
        assert shown["ok"] and shown["memory"]["id"] == mid
        corrected = await memtools.correct_memory(mid, "Tool-corrected fact.")
        assert corrected["ok"] and corrected["applied"]
        # update_memory content path routes through correction (history kept).
        updated = await memtools.update_memory(mid, content="Tool-updated fact.")
        assert updated["ok"] and updated["version"] >= corrected["version"] + 1
        exported = await memtools.export_memories()
        assert exported["ok"] and any(
            m["id"] == mid for m in exported["memories"]
        )
        forgotten = await memtools.forget_memory(mid)
        assert forgotten["ok"] and forgotten["forgotten"]
        # Every tool payload is plain data (no domain objects, no repo handles).
        import json

        json.dumps({**created, **shown, **corrected, **exported, **forgotten})
    finally:
        container.remove(MemoryManager)


@pytest.mark.asyncio
async def test_cli_memory_verbs(manager, monkeypatch) -> None:
    from aetheros.cli.commands import CommandRegistry
    from aetheros.core.container import container
    from aetheros.memory.services.manager import MemoryManager

    monkeypatch.setattr(container, "has", lambda cls: cls is MemoryManager)
    monkeypatch.setattr(container, "resolve", lambda cls: manager)
    cli = CommandRegistry()
    m = await manager.remember("CLI Zorblax fact.", veracity=Veracity.USER_INPUT)
    assert "CLI Zorblax fact" in await cli._memory_command(["show", m.id])
    assert "Corrected" in await cli._memory_command(["correct", m.id, "CLI fixed."])
    assert "CLI fixed" in await cli._memory_command(["show", m.id])
    export_text = await cli._memory_command(["export"])
    assert m.id in export_text
    assert "hard-deleted" in await cli._memory_command(["erase", m.id])
    assert "No memory" in await cli._memory_command(["show", m.id])
    assert "Unknown memory subcommand" in await cli._memory_command(["frobnicate"])
