"""
Phase 9 — working (short-term) memory tests.

Exercises the ephemeral, session/task-scoped live context: session isolation,
TTL boundaries with a controllable clock, stale-observation rejection
(freshness/sequence), task-completion and session-end cleanup, bounded capacity,
disabled-mode promotion, explicit evidence selection, and compatibility with the
legacy single-session API the Agent/Desktop layers use.

The clock is injected (not the wall clock), so TTL boundaries are deterministic.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from aetheros.memory.domain import MemoryImportance
from aetheros.memory.services.manager import MemoryManager
from aetheros.memory.services.working_memory import WorkingMemory


class FakeClock:
    """A controllable monotone clock for deterministic TTL tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)


# ----------------------------------------------------------------------
# Session isolation
# ----------------------------------------------------------------------


def test_sessions_are_isolated() -> None:
    wm = WorkingMemory(capacity=10)
    wm.add("note", "alpha for A", session_id="A")
    wm.add("note", "beta for B", session_id="B")

    a = wm.items(session_id="A")
    b = wm.items(session_id="B")
    assert [i.content for i in a] == ["alpha for A"]
    assert [i.content for i in b] == ["beta for B"]
    # One session's items never appear in another.
    assert set(wm.sessions()) == {"A", "B"}


def test_end_session_only_clears_that_session() -> None:
    wm = WorkingMemory(capacity=10)
    wm.add("note", "a", session_id="A")
    wm.add("note", "b", session_id="B")
    removed = wm.end_session("A")
    assert removed == 1
    assert wm.items(session_id="A") == []
    assert [i.content for i in wm.items(session_id="B")] == ["b"]


# ----------------------------------------------------------------------
# TTL boundaries (controllable clock)
# ----------------------------------------------------------------------


def test_ttl_item_expires_exactly_at_boundary() -> None:
    clock = FakeClock()
    wm = WorkingMemory(capacity=10, clock=clock)
    wm.add("note", "ephemeral", ttl_seconds=10, session_id="S")

    clock.advance(9)
    assert len(wm.items(session_id="S")) == 1  # still alive before boundary

    clock.advance(1)  # now == expires_at -> expired (>= boundary)
    assert wm.items(session_id="S") == []
    assert wm.current_observation("x", session_id="S") is None


def test_sweep_expired_reclaims_items() -> None:
    clock = FakeClock()
    wm = WorkingMemory(capacity=10, clock=clock)
    wm.add("note", "short", ttl_seconds=5, session_id="S")
    wm.add("note", "long", ttl_seconds=100, session_id="S")
    clock.advance(10)
    removed = wm.sweep_expired()
    assert removed == 1
    assert [i.content for i in wm.items(session_id="S")] == ["long"]


def test_default_ttl_applies_when_item_ttl_unset() -> None:
    clock = FakeClock()
    wm = WorkingMemory(capacity=10, default_ttl_seconds=30, clock=clock)
    wm.add("note", "uses default ttl", session_id="S")
    clock.advance(31)
    assert wm.items(session_id="S") == []


def test_zero_ttl_means_no_expiry() -> None:
    clock = FakeClock()
    wm = WorkingMemory(capacity=10, clock=clock)
    wm.add("note", "permanent-ish", session_id="S")  # ttl defaults to none
    clock.advance(10_000)
    assert len(wm.items(session_id="S")) == 1


# ----------------------------------------------------------------------
# Freshness / sequence — stale updates cannot overwrite newer state
# ----------------------------------------------------------------------


def test_stale_sequence_observation_rejected() -> None:
    wm = WorkingMemory(capacity=10)
    r1 = wm.observe("price", "100", sequence=5, session_id="S")
    assert r1.accepted
    # A delayed observation with an older sequence arrives late.
    r2 = wm.observe("price", "99", sequence=3, session_id="S")
    assert not r2.accepted
    # The newer known state (sequence 5 -> "100") remains in effect.
    assert wm.current_observation("price", session_id="S").content == "100"


def test_newer_sequence_observation_accepted() -> None:
    wm = WorkingMemory(capacity=10)
    wm.observe("price", "100", sequence=5, session_id="S")
    r = wm.observe("price", "101", sequence=6, session_id="S")
    assert r.accepted
    assert wm.current_observation("price", session_id="S").content == "101"


def test_stale_timestamp_observation_rejected() -> None:
    wm = WorkingMemory(capacity=10)
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t_earlier = t0 - timedelta(seconds=5)
    wm.observe("regime", "trending", observed_at=t0, session_id="S")
    r = wm.observe("regime", "ranging", observed_at=t_earlier, session_id="S")
    assert not r.accepted
    assert wm.current_observation("regime", session_id="S").content == "trending"


def test_sequenced_observation_beats_unsequenced() -> None:
    wm = WorkingMemory(capacity=10)
    wm.observe("state", "seq-known", sequence=1, session_id="S")
    # An unsequenced update must not displace a sequenced (more authoritative) one.
    r = wm.observe("state", "no-seq", sequence=None, session_id="S")
    assert not r.accepted
    assert wm.current_observation("state", session_id="S").content == "seq-known"


def test_observations_are_session_scoped() -> None:
    wm = WorkingMemory(capacity=10)
    wm.observe("price", "100", sequence=1, session_id="A")
    wm.observe("price", "200", sequence=1, session_id="B")
    assert wm.current_observation("price", session_id="A").content == "100"
    assert wm.current_observation("price", session_id="B").content == "200"


# ----------------------------------------------------------------------
# Task completion cleanup
# ----------------------------------------------------------------------


def test_complete_task_purges_only_that_task() -> None:
    wm = WorkingMemory(capacity=10)
    wm.add("step", "task1-a", task_id="T1", session_id="S")
    wm.add("step", "task1-b", task_id="T1", session_id="S")
    wm.add("step", "task2-a", task_id="T2", session_id="S")
    removed = wm.complete_task("T1", session_id="S")
    assert removed == 2
    remaining = [i.content for i in wm.items(session_id="S")]
    assert remaining == ["task2-a"]


# ----------------------------------------------------------------------
# Bounded size
# ----------------------------------------------------------------------


def test_capacity_evicts_least_important_oldest() -> None:
    wm = WorkingMemory(capacity=3)
    wm.add("note", "trivial-old", importance=MemoryImportance.TRIVIAL, session_id="S")
    wm.add("note", "high-1", importance=MemoryImportance.HIGH, session_id="S")
    wm.add("note", "high-2", importance=MemoryImportance.HIGH, session_id="S")
    wm.add("note", "high-3", importance=MemoryImportance.HIGH, session_id="S")  # overflow
    contents = {i.content for i in wm.items(session_id="S")}
    assert len(contents) == 3
    assert "trivial-old" not in contents  # the lowest-importance oldest was evicted


def test_capacity_is_per_session() -> None:
    wm = WorkingMemory(capacity=2)
    for i in range(5):
        wm.add("n", f"A{i}", session_id="A")
    for i in range(5):
        wm.add("n", f"B{i}", session_id="B")
    assert len(wm.items(session_id="A")) == 2
    assert len(wm.items(session_id="B")) == 2


# ----------------------------------------------------------------------
# Explicit evidence selection for durable formation
# ----------------------------------------------------------------------


def test_only_evidence_promotes_marked_items(tmp_path) -> None:
    wm = WorkingMemory(capacity=10)
    chosen = wm.add("insight", "RELIANCE broke resistance", session_id="S")
    wm.add("chatter", "ignore me", session_id="S")
    assert wm.mark_evidence(chosen.id, session_id="S")

    mems = wm.to_memories(session_id="S", only_evidence=True)
    assert len(mems) == 1
    assert mems[0].content == "RELIANCE broke resistance"
    assert "promoted" in mems[0].tags


def test_importance_promotion_still_works() -> None:
    wm = WorkingMemory(capacity=10)
    wm.add("decision", "keep", importance=MemoryImportance.HIGH, session_id="S")
    wm.add("chatter", "drop", importance=MemoryImportance.TRIVIAL, session_id="S")
    mems = wm.to_memories(session_id="S", min_importance=MemoryImportance.HIGH)
    assert [m.content for m in mems] == ["keep"]


# ----------------------------------------------------------------------
# Manager integration + disabled mode + legacy API compatibility
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_promote_working_persists(manager) -> None:
    manager.working.add(
        "decision", "Chose vision grounding", importance=MemoryImportance.HIGH
    )
    promoted = await manager.promote_working()
    assert len(promoted) == 1
    assert "vision grounding" in promoted[0].content


@pytest.mark.asyncio
async def test_manager_promote_only_evidence(manager) -> None:
    item = manager.working.add("insight", "evidence item")
    manager.working.add("insight", "not evidence")
    manager.working.mark_evidence(item.id)
    promoted = await manager.promote_working(only_evidence=True)
    assert [p.content for p in promoted] == ["evidence item"]


@pytest.mark.asyncio
async def test_disabled_mode_promotion_is_noop(memory_config) -> None:
    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    # Working memory still accepts items (it is a pure in-process scratchpad)...
    mgr.working.add("note", "x", importance=MemoryImportance.CRITICAL)
    # ...but promotion persists nothing when the subsystem is disabled.
    promoted = await mgr.promote_working()
    assert promoted == []


def test_legacy_single_session_api_unchanged() -> None:
    # The Agent/Desktop callers use the default session implicitly.
    wm = WorkingMemory(capacity=10)
    item = wm.add("note", "legacy add")
    assert wm.update(item.id, content="updated", extra="x")
    assert wm.items()[0].content == "updated"
    assert wm.items()[0].data["extra"] == "x"
    assert wm.remove(item.id)
    assert wm.items() == []


def test_summarize_includes_observations_and_items() -> None:
    wm = WorkingMemory(capacity=10)
    wm.observe("price", "RELIANCE 2500", sequence=1, session_id="S")
    wm.add("plan", "watch for breakout", session_id="S")
    text = wm.summarize(session_id="S")
    assert "observation" in text
    assert "RELIANCE 2500" in text
    assert "watch for breakout" in text


def test_len_excludes_expired() -> None:
    clock = FakeClock()
    wm = WorkingMemory(capacity=10, clock=clock)
    wm.add("n", "a", ttl_seconds=5, session_id="S")
    wm.observe("k", "obs", ttl_seconds=5, session_id="S")
    assert len(wm) == 2
    clock.advance(6)
    assert len(wm) == 0
