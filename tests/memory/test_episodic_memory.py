"""
Phase 10 -- episodic memory foundation tests.

Exercises the explicit episode lifecycle (``MemoryManager.episodes``):
start, action/observation append, failure/recovery links, finalization and
retrieval. The suite pins the acceptance contract:

* persistence + chronological reconstruction (incl. late/out-of-order events)
* idempotency (duplicate start / duplicate appends / repeated finalization
  never duplicate episodes)
* restart recovery (incomplete episodes listed after a fresh manager opens
  the same database)
* incomplete episodes (started-but-unfinalized state is visible and resumable)
* scope isolation (task/session listings never cross)
* retention bounds (per-episode action cap, counted; bounded list methods)
* redaction (sensitive tool inputs/results never persist in the clear)
* disabled mode (honest no-persist, no phantom success)
* single-shot compatibility (the agent integration's ``remember_episode``
  path records episodes the recorder can read back)
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio

from aetheros.memory.domain import Episode, MemoryType, OutcomeStatus
from aetheros.memory.services.manager import MemoryManager


def _t0() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def file_manager(tmp_path: Path):
    """A manager on a real file database, so restart can be simulated."""
    from aetheros.memory.config import MemoryConfig

    cfg = MemoryConfig.for_memory_db(tmp_path / "episodes.db", embedding_dim=64)
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        yield mgr
    finally:
        await mgr.shutdown()


# ----------------------------------------------------------------------
# Lifecycle: start -> append -> finalize
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_lifecycle_persists_everything(manager) -> None:
    rec = manager.episodes
    ep = await rec.start_episode(
        "Open TradingView and add RSI",
        episode_id="ep-lifecycle",
        task_id="T1",
        session_id="S1",
        environment={"application": "Chrome", "entities": ["TradingView", "RSI"]},
        relevant_memories=[],
        provenance={"agent_run_id": "run-1", "tool_version": "1.0"},
        started_at=_t0(),
    )
    assert ep.ended_at is None
    assert ep.outcome.status is OutcomeStatus.UNKNOWN

    await rec.record_action(
        "ep-lifecycle",
        "open_browser",
        status=OutcomeStatus.SUCCESS,
        arguments={"url": "https://tradingview.com"},
        result_summary="browser opened",
        duration_ms=120.0,
        started_at=_t0() + timedelta(seconds=1),
    )
    await rec.record_observation(
        "ep-lifecycle",
        "market_state",
        "RELIANCE 2500, trending",
        observed_at=_t0() + timedelta(seconds=2),
    )
    final = await rec.finalize_episode(
        "ep-lifecycle",
        OutcomeStatus.SUCCESS,
        detail="RSI added",
        metrics={"steps": 1},
        lessons=["RSI lives under Indicators"],
    )

    assert final.ended_at is not None
    assert final.outcome.status is OutcomeStatus.SUCCESS
    assert final.outcome.detail == "RSI added"
    assert final.outcome.metrics == {"steps": 1}
    assert final.lessons == ["RSI lives under Indicators"]
    assert final.duration_ms is not None and final.duration_ms >= 0
    assert [a.name for a in final.actions] == ["open_browser"]
    assert [o.key for o in final.observations] == ["market_state"]
    assert final.relevant_memories == []
    assert final.provenance == {"agent_run_id": "run-1", "tool_version": "1.0"}
    assert final.task_id == "T1" and final.session_id == "S1"

    # The stored content is attributable: rebuilt from the stored steps.
    row = await manager.get("ep-lifecycle")
    assert row is not None
    assert "open_browser" in row.content
    assert row.data["episode"]["outcome"]["status"] == "success"
    assert row.metadata["episode_id"] == "ep-lifecycle"
    assert row.metadata["task_id"] == "T1"
    assert row.metadata["session_id"] == "S1"


@pytest.mark.asyncio
async def test_out_of_order_appends_reconstruct_chronologically(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("out-of-order", episode_id="ep-ooo", started_at=_t0())
    # Late arrival first, then the earlier step.
    await rec.record_action(
        "ep-ooo", "second", started_at=_t0() + timedelta(seconds=10)
    )
    await rec.record_action("ep-ooo", "first", started_at=_t0() + timedelta(seconds=1))
    ep = await rec.get_episode("ep-ooo")
    assert ep is not None
    assert [a.name for a in ep.actions] == ["first", "second"]


@pytest.mark.asyncio
async def test_late_append_after_finalize_keeps_outcome(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("late-evidence", episode_id="ep-late", started_at=_t0())
    await rec.finalize_episode("ep-late", OutcomeStatus.SUCCESS, detail="done")
    before = (await rec.get_episode("ep-late")).ended_at
    await rec.record_action("ep-late", "posthoc_note", started_at=_t0())
    ep = await rec.get_episode("ep-late")
    assert ep is not None
    assert ep.outcome.status is OutcomeStatus.SUCCESS
    assert ep.ended_at == before  # late evidence never re-opens the episode
    assert any(a.name == "posthoc_note" for a in ep.actions)


# ----------------------------------------------------------------------
# Idempotency: duplicates, redeliveries, repeated finalization
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_start_returns_existing_without_duplicating(
    manager,
) -> None:
    rec = manager.episodes
    first = await rec.start_episode(
        "same goal", episode_id="ep-dupe", task_id="T", session_id="S"
    )
    await rec.record_action("ep-dupe", "step", started_at=_t0())
    second = await rec.start_episode(
        "same goal", episode_id="ep-dupe", task_id="T", session_id="S"
    )
    assert second.id == first.id
    # The retried start did not wipe the recorded step.
    assert [a.name for a in second.actions] == ["step"]
    rows = await manager._repo.list_by(memory_type="episodic", limit=100)
    assert [r.id for r in rows].count("ep-dupe") == 1


@pytest.mark.asyncio
async def test_duplicate_action_delivery_is_noop(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("redelivery", episode_id="ep-redeliver")
    stamp = _t0()
    await rec.record_action("ep-redeliver", "click", started_at=stamp)
    row_before = await manager.get("ep-redeliver")
    assert row_before is not None
    # Exact redelivery: same name + timestamp.
    await rec.record_action("ep-redeliver", "click", started_at=stamp)
    row_after = await manager.get("ep-redeliver")
    assert row_after is not None
    assert row_after.version == row_before.version  # no write happened
    ep = await rec.get_episode("ep-redeliver")
    assert ep is not None and len(ep.actions) == 1


@pytest.mark.asyncio
async def test_duplicate_observation_delivery_is_noop(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("redelivery-obs", episode_id="ep-redeliver-obs")
    stamp = _t0()
    await rec.record_observation("ep-redeliver-obs", "price", "100", observed_at=stamp)
    await rec.record_observation("ep-redeliver-obs", "price", "100", observed_at=stamp)
    ep = await rec.get_episode("ep-redeliver-obs")
    assert ep is not None and len(ep.observations) == 1


@pytest.mark.asyncio
async def test_repeated_finalization_writes_nothing(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("final-twice", episode_id="ep-final-twice")
    await rec.finalize_episode("ep-final-twice", OutcomeStatus.SUCCESS, detail="done")
    row_before = await manager.get("ep-final-twice")
    assert row_before is not None
    await rec.finalize_episode("ep-final-twice", OutcomeStatus.SUCCESS, detail="done")
    row_after = await manager.get("ep-final-twice")
    assert row_after is not None
    assert row_after.version == row_before.version


@pytest.mark.asyncio
async def test_refinalize_with_different_status_updates_single_row(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("regrade", episode_id="ep-regrade")
    await rec.finalize_episode("ep-regrade", OutcomeStatus.PARTIAL, detail="half")
    await rec.finalize_episode("ep-regrade", OutcomeStatus.FAILURE, detail="actually bad")
    ep = await rec.get_episode("ep-regrade")
    assert ep is not None
    assert ep.outcome.status is OutcomeStatus.FAILURE
    assert ep.outcome.detail == "actually bad"
    rows = await manager._repo.list_by(memory_type="episodic", limit=100)
    assert [r.id for r in rows].count("ep-regrade") == 1


@pytest.mark.asyncio
async def test_finalize_lessons_deduplicated(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("lessons", episode_id="ep-lessons")
    await rec.finalize_episode(
        "ep-lessons", OutcomeStatus.SUCCESS, lessons=["check volume", "check volume"]
    )
    ep = await rec.get_episode("ep-lessons")
    assert ep is not None and ep.lessons == ["check volume"]


# ----------------------------------------------------------------------
# Failure / recovery links
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_failure_links_and_lists(manager, make_memory) -> None:
    rec = manager.episodes
    await rec.start_episode("with-failure", episode_id="ep-fail")
    failure = make_memory(
        content="Action 'click' failed: window moved.",
        memory_type=MemoryType.FAILURE,
    )
    stored_failure = await manager.remember_memory(failure)
    await rec.attach_failure("ep-fail", stored_failure.id)

    failures = await rec.episode_failures("ep-fail")
    assert [f.id for f in failures] == [stored_failure.id]
    neighbours = await manager._repo.linked_ids(stored_failure.id)
    assert any(nid == "ep-fail" for nid, _, _ in neighbours)

    # A repeated attach is a no-op -- no duplicate link rows.
    links_before = list(await manager._repo.linked_ids(stored_failure.id))
    await rec.attach_failure("ep-fail", stored_failure.id)
    assert list(await manager._repo.linked_ids(stored_failure.id)) == links_before


@pytest.mark.asyncio
async def test_attach_failure_missing_episode_or_failure_raises(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    rec = manager.episodes
    with pytest.raises(MemoryNotFoundError):
        await rec.attach_failure("no-such-episode", "no-such-failure")
    await rec.start_episode("lonely", episode_id="ep-lonely")
    with pytest.raises(MemoryNotFoundError):
        await rec.attach_failure("ep-lonely", "no-such-failure")


# ----------------------------------------------------------------------
# Retrieval: scope isolation, status filter, incomplete listing
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scope_isolation(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("a1", episode_id="ep-a1", task_id="TA", session_id="SA")
    await rec.start_episode("a2", episode_id="ep-a2", task_id="TA", session_id="SA")
    await rec.start_episode("b1", episode_id="ep-b1", task_id="TB", session_id="SB")

    by_task = await rec.list_episodes(task_id="TA")
    assert {e.id for e in by_task} == {"ep-a1", "ep-a2"}
    by_session = await rec.list_episodes(session_id="SB")
    assert [e.id for e in by_session] == ["ep-b1"]
    # One session's episodes never appear in another's listing.
    other = await rec.list_episodes(session_id="SA")
    assert "ep-b1" not in {e.id for e in other}


@pytest.mark.asyncio
async def test_status_filter_and_incomplete_toggle(manager) -> None:
    rec = manager.episodes
    await rec.start_episode("open", episode_id="ep-open")
    await rec.start_episode("shut", episode_id="ep-shut")
    await rec.finalize_episode("ep-shut", OutcomeStatus.FAILURE)

    failed = await rec.list_episodes(status=OutcomeStatus.FAILURE)
    assert {e.id for e in failed} == {"ep-shut"}
    complete_only = await rec.list_episodes(include_incomplete=False)
    assert {e.id for e in complete_only} == {"ep-shut"}
    all_eps = await rec.list_episodes()
    assert {"ep-open", "ep-shut"} <= {e.id for e in all_eps}


@pytest.mark.asyncio
async def test_get_episode_degrades_to_none(manager, make_memory) -> None:
    rec = manager.episodes
    assert await rec.get_episode("missing") is None
    # A non-episode row reads as absent, never raises.
    other = await manager.remember_memory(make_memory(content="just a preference"))
    assert await rec.get_episode(other.id) is None
    # Soft-deleted episodes are invisible.
    await rec.start_episode("doomed", episode_id="ep-doomed")
    await manager.forget("ep-doomed")
    assert await rec.get_episode("ep-doomed") is None


# ----------------------------------------------------------------------
# Restart: incomplete episodes survive, work resumes
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restart_lists_incomplete_and_resumes(file_manager) -> None:
    rec = file_manager.episodes
    await rec.start_episode("interrupted", episode_id="ep-restart", task_id="TR")
    await rec.record_action("ep-restart", "step-one", started_at=_t0())
    await rec.start_episode("finished", episode_id="ep-done-restart")
    await rec.finalize_episode("ep-done-restart", OutcomeStatus.SUCCESS)

    from aetheros.memory.services.manager import MemoryManager as MM

    cfg = file_manager.config
    mgr2 = MM(cfg)
    await mgr2.initialize()
    try:
        incomplete = await mgr2.episodes.list_incomplete()
        assert [e.id for e in incomplete] == ["ep-restart"]
        # Work resumes on the fresh handle: append + finalize.
        await mgr2.episodes.record_action(
            "ep-restart", "step-two", started_at=_t0() + timedelta(seconds=5)
        )
        final = await mgr2.episodes.finalize_episode(
            "ep-restart", OutcomeStatus.SUCCESS
        )
        assert [a.name for a in final.actions] == ["step-one", "step-two"]
        assert await mgr2.episodes.list_incomplete() == []
    finally:
        await mgr2.shutdown()


# ----------------------------------------------------------------------
# Retention bounds
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_cap_drops_oldest_and_counts(memory_config, tmp_path) -> None:

    cfg = replace(memory_config, episode_max_actions=3)
    assert cfg.episode_max_actions == 3
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        await mgr.episodes.start_episode("capped", episode_id="ep-cap")
        for i in range(5):
            await mgr.episodes.record_action(
                "ep-cap", f"step-{i}", started_at=_t0() + timedelta(seconds=i)
            )
        ep = await mgr.episodes.get_episode("ep-cap")
        assert ep is not None
        assert [a.name for a in ep.actions] == ["step-2", "step-3", "step-4"]
        row = await mgr.get("ep-cap")
        assert row is not None
        assert row.metadata.get("truncated_actions") == 2
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_list_limit_is_bounded(manager) -> None:
    rec = manager.episodes
    for i in range(5):
        await rec.start_episode(f"goal-{i}", episode_id=f"ep-bound-{i}")
    listed = await rec.list_episodes(limit=2)
    assert len(listed) == 2


# ----------------------------------------------------------------------
# Redaction: sensitive tool inputs/results never persist in the clear
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sensitive_arguments_and_summaries_redacted(manager) -> None:
    rec = manager.episodes
    await rec.start_episode(
        "login flow",
        episode_id="ep-redact",
        environment={"api_key": "AKIAIOSFODNN7EXAMPLE", "browser": "Chrome"},
        provenance={"auth": "Bearer abcdefghijklmnopqrst"},
    )
    await rec.record_action(
        "ep-redact",
        "type_text",
        arguments={"password": "hunter2-secret", "field": "login"},
        result_summary="typed password=hunter2-secret into the box",
        error="login failed for password=hunter2-secret",
    )
    row = await manager.get("ep-redact")
    assert row is not None
    blob = (
        str(row.data)
        + str(row.metadata)
        + str(row.source.detail)
        + row.content
    )
    assert "hunter2-secret" not in blob
    assert "AKIAIOSFODNN7EXAMPLE" not in blob
    assert "abcdefghijklmnopqrst" not in blob
    ep = await rec.get_episode("ep-redact")
    assert ep is not None
    assert ep.actions[0].arguments.get("password") == "[redacted]"


@pytest.mark.asyncio
async def test_secret_in_goal_is_scrubbed_and_labelled(manager) -> None:
    rec = manager.episodes
    ep = await rec.start_episode(
        "check account password=hunter2-secret now", episode_id="ep-goal-secret"
    )
    assert "hunter2-secret" not in ep.goal
    assert "redacted_secret_kinds" in ep.provenance
    row = await manager.get("ep-goal-secret")
    assert row is not None and "hunter2-secret" not in str(row.data)


# ----------------------------------------------------------------------
# Disabled mode: honest no-persist
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_mode_persists_nothing(memory_config) -> None:
    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    ep = await mgr.episodes.start_episode("disabled", episode_id="ep-disabled")
    assert ep.ended_at is None
    # No row exists -- the caller can recognise the unsaved episode.
    assert await mgr.episodes.get_episode("ep-disabled") is None


# ----------------------------------------------------------------------
# Compatibility: single-shot agent recording reads back through the recorder
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_shot_episode_readable_via_recorder(manager) -> None:
    episode = Episode(
        goal="Open TradingView and add RSI",
        environment={"application": "Chrome", "entities": ["TradingView", "RSI"]},
    )
    stored = await manager.remember_episode(episode)
    assert stored.id == episode.id
    read_back = await manager.episodes.get_episode(episode.id)
    assert read_back is not None
    assert read_back.goal == episode.goal
    assert read_back.session_id is None
