"""
Phase 11 -- failure and recovery memory tests.

Exercises the explicit failure lifecycle (``MemoryManager.failures``):
record, attempt appends, resolution, cause confirmation, alternative links
and retrieval. The suite pins the acceptance contract:

* failed recovery stays open; successful recovery closes with evidence
* multiple attempts accumulate in order; duplicates are a no-op
* suspected causes are quarantined until explicitly confirmed
* missing/late links (episode/procedure appearing after the failure)
* restart recovery (open failures listed after a fresh manager opens the
  same database; attempts/resolution resume on the fresh handle)
* safe logging (no credentials from exceptions/URLs/bodies/tool output)
* historical retrieval (resolved failures kept by default; filters work)
* no automatic procedure revision (linking an alternative never edits it)
* agent single-shot compatibility (``remember_failure`` rows read back)
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import pytest_asyncio

from aetheros.memory.domain import FailureRecord, OutcomeStatus
from aetheros.memory.services.manager import MemoryManager


@pytest_asyncio.fixture
async def file_manager(tmp_path: Path):
    """A manager on a real file database, so restart can be simulated."""
    from aetheros.memory.config import MemoryConfig

    cfg = MemoryConfig.for_memory_db(tmp_path / "failures.db", embedding_dim=64)
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        yield mgr
    finally:
        await mgr.shutdown()


# ----------------------------------------------------------------------
# Record + resolution
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_recovery_stays_open(manager) -> None:
    rec = manager.failures
    failure = await rec.record_failure(
        "timeout",
        "tool timed out after 30s",
        failure_id="fail-open",
        action="click_submit",
        observed_symptoms=["spinner never resolved", "no network response"],
        suspected_cause="backend is down",
        context={"task_id": "T1", "session_id": "S1"},
    )
    assert not failure.recovered
    assert failure.observed_symptoms == [
        "spinner never resolved",
        "no network response",
    ]
    # Suspected cause is stored but quarantined out of the summary.
    assert failure.suspected_cause == "backend is down"
    assert not failure.cause_confirmed

    await rec.record_attempt("fail-open", "retry_once", status=OutcomeStatus.FAILURE)
    updated = await rec.get_failure("fail-open")
    assert updated is not None
    assert not updated.recovered
    assert [a.action for a in updated.attempts] == ["retry_once"]
    assert updated.attempted_recovery == "retry_once"

    row = await manager.get("fail-open")
    assert row is not None
    # Quarantine: the unverified suspicion must not read as fact in retrieval.
    assert "backend is down" not in row.content
    assert "episode_id" not in row.metadata  # no episode attached
    assert row.metadata["task_id"] == "T1"
    assert row.metadata["session_id"] == "S1"
    assert "open" in row.tags


@pytest.mark.asyncio
async def test_successful_recovery_closes_with_evidence(manager) -> None:
    rec = manager.failures
    await rec.record_failure("stale_coordinates", "clicked empty space",
                             failure_id="fail-fixed", action="click_indicators")
    await rec.record_attempt("fail-fixed", "recapture_screen",
                             status=OutcomeStatus.FAILURE)
    resolved = await rec.resolve("fail-fixed", "vision-based grounding",
                                 detail="re-grounded then clicked")
    assert resolved.recovered
    assert resolved.successful_recovery == "vision-based grounding"
    assert resolved.recovery_status is OutcomeStatus.SUCCESS
    # The recovery is also in the attempt log, so it is attributable.
    assert "vision-based grounding" in [a.action for a in resolved.attempts]

    row = await manager.get("fail-fixed")
    assert row is not None
    assert "vision-based grounding" in row.content
    assert "recovered" in row.tags
    assert row.confidence == 0.85


@pytest.mark.asyncio
async def test_multiple_attempts_accumulate_in_order(manager) -> None:
    rec = manager.failures
    await rec.record_failure("flaky", "intermittent 500", failure_id="fail-multi")
    await rec.record_attempt("fail-multi", "retry_1", status=OutcomeStatus.FAILURE)
    await rec.record_attempt("fail-multi", "retry_2", status=OutcomeStatus.FAILURE)
    await rec.record_attempt("fail-multi", "fallback_path",
                             status=OutcomeStatus.SUCCESS)
    failure = await rec.get_failure("fail-multi")
    assert failure is not None
    assert [a.action for a in failure.attempts] == [
        "retry_1", "retry_2", "fallback_path",
    ]


@pytest.mark.asyncio
async def test_duplicate_delivery_is_noop(manager) -> None:
    rec = manager.failures
    first = await rec.record_failure("dupe", "boom", failure_id="fail-dupe")
    await rec.record_attempt("fail-dupe", "retry", status=OutcomeStatus.FAILURE,
                             detail="x")
    row_before = await manager.get("fail-dupe")
    assert row_before is not None
    # Redelivered record + redelivered attempt: neither writes.
    second = await rec.record_failure("dupe", "boom", failure_id="fail-dupe")
    assert second.id == first.id
    await rec.record_attempt("fail-dupe", "retry", status=OutcomeStatus.FAILURE,
                             detail="x")
    row_after = await manager.get("fail-dupe")
    assert row_after is not None
    assert row_after.version == row_before.version
    failure = await rec.get_failure("fail-dupe")
    assert failure is not None and len(failure.attempts) == 1


@pytest.mark.asyncio
async def test_repeated_resolve_writes_nothing(manager) -> None:
    rec = manager.failures
    await rec.record_failure("once", "boom", failure_id="fail-resolve-twice")
    await rec.resolve("fail-resolve-twice", "retry")
    row_before = await manager.get("fail-resolve-twice")
    assert row_before is not None
    await rec.resolve("fail-resolve-twice", "retry")
    row_after = await manager.get("fail-resolve-twice")
    assert row_after is not None
    assert row_after.version == row_before.version


# ----------------------------------------------------------------------
# Cause quarantine
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspected_cause_quarantined_until_confirmed(manager) -> None:
    rec = manager.failures
    await rec.record_failure("mystery", "exit code 1", failure_id="fail-cause",
                             suspected_cause="disk full")
    row = await manager.get("fail-cause")
    assert row is not None
    assert "disk full" not in row.content
    # ... but it is preserved in the payload (not lost).
    assert row.data["failure"]["suspected_cause"] == "disk full"

    confirmed = await rec.confirm_cause("fail-cause", "disk full")
    assert confirmed.cause_confirmed
    row2 = await manager.get("fail-cause")
    assert row2 is not None
    assert "disk full" in row2.content

    # Repeating the confirmation writes nothing.
    await rec.confirm_cause("fail-cause", "disk full")
    row3 = await manager.get("fail-cause")
    assert row3 is not None
    assert row3.version == row2.version


# ----------------------------------------------------------------------
# Links: episode / procedure / alternatives (missing + late)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_link_targets_skipped_not_failed(manager) -> None:
    rec = manager.failures
    failure = await rec.record_failure(
        "orphan", "no context", failure_id="fail-orphan",
        episode_id="no-such-episode", procedure_id="no-such-procedure",
    )
    assert failure.episode_id == "no-such-episode"
    assert failure.procedure_id == "no-such-procedure"
    # The failure recorded fine despite both targets missing.


@pytest.mark.asyncio
async def test_late_episode_link_attaches(manager) -> None:
    rec = manager.failures
    await rec.record_failure("late", "boom", failure_id="fail-late")
    ep = await manager.episodes.start_episode("late goal", episode_id="ep-late")
    await rec.link_episode("fail-late", ep.id)
    failure = await rec.get_failure("fail-late")
    assert failure is not None and failure.episode_id == ep.id
    neighbours = await manager._repo.linked_ids("fail-late")
    assert any(nid == ep.id for nid, _, _ in neighbours)
    # Idempotent: repeating changes nothing.
    links_before = list(neighbours)
    await rec.link_episode("fail-late", ep.id)
    assert list(await manager._repo.linked_ids("fail-late")) == links_before


@pytest.mark.asyncio
async def test_link_alternative_records_evidence_without_editing(manager) -> None:
    rec = manager.failures
    await rec.record_failure("needs-alt", "boom", failure_id="fail-alt")
    proc_mem = await manager.remember_procedure(
        __import__("aetheros.memory.domain", fromlist=["Procedure"]).Procedure(
            name="grounded_click", goal="click reliably", success_count=3,
        )
    )
    before = dict(proc_mem.data)
    await rec.link_alternative(
        "fail-alt", proc_mem.id,
        evidence={"episode_id": "ep-1", "successful_step": "vision_ground"},
    )
    alternatives = await rec.failure_alternatives("fail-alt")
    assert [a.id for a in alternatives] == [proc_mem.id]
    # The procedure itself was never revised by the link.
    after = await manager.get(proc_mem.id)
    assert after is not None and after.data == before
    # Repeating the link is a no-op.
    links_before = await manager._repo.linked_ids("fail-alt")
    await rec.link_alternative("fail-alt", proc_mem.id)
    assert await manager._repo.linked_ids("fail-alt") == links_before


@pytest.mark.asyncio
async def test_link_alternative_missing_target_raises(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    rec = manager.failures
    await rec.record_failure("alt-missing", "boom", failure_id="fail-alt-missing")
    with pytest.raises(MemoryNotFoundError):
        await rec.link_alternative("fail-alt-missing", "no-such-memory")


# ----------------------------------------------------------------------
# Retrieval: scope, filters, history, restart
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_filters_and_history(manager) -> None:
    rec = manager.failures
    await rec.record_failure("timeout", "t1", failure_id="fail-h1",
                             context={"session_id": "S1"})
    await rec.record_failure("timeout", "t2", failure_id="fail-h2")
    await rec.record_failure("auth", "a1", failure_id="fail-h3")
    await rec.resolve("fail-h1", "retry")

    by_type = await rec.list_failures(failure_type="timeout")
    assert {f.id for f in by_type} == {"fail-h1", "fail-h2"}
    open_only = await rec.list_failures(include_resolved=False)
    assert {f.id for f in open_only} == {"fail-h2", "fail-h3"}
    recovered = await rec.list_failures(recovered=True)
    assert [f.id for f in recovered] == ["fail-h1"]
    limited = await rec.list_failures(limit=1)
    assert len(limited) == 1


@pytest.mark.asyncio
async def test_get_failure_degrades_to_none(manager, make_memory) -> None:
    rec = manager.failures
    assert await rec.get_failure("missing") is None
    other = await manager.remember_memory(make_memory(content="just a preference"))
    assert await rec.get_failure(other.id) is None
    await rec.record_failure("doomed", "boom", failure_id="fail-doomed")
    await manager.forget("fail-doomed")
    assert await rec.get_failure("fail-doomed") is None


@pytest.mark.asyncio
async def test_restart_lists_open_and_resumes(file_manager) -> None:
    rec = file_manager.failures
    await rec.record_failure("interrupted", "boom", failure_id="fail-restart")
    await rec.record_attempt("fail-restart", "retry_1",
                             status=OutcomeStatus.FAILURE)
    await rec.record_failure("closed", "boom", failure_id="fail-done-restart")
    await rec.resolve("fail-done-restart", "retry")

    from aetheros.memory.services.manager import MemoryManager as MM

    mgr2 = MM(file_manager.config)
    await mgr2.initialize()
    try:
        open_failures = await mgr2.failures.list_open()
        assert [f.id for f in open_failures] == ["fail-restart"]
        # Work resumes on the fresh handle: attempt + resolve.
        await mgr2.failures.record_attempt("fail-restart", "retry_2",
                                           status=OutcomeStatus.SUCCESS)
        resolved = await mgr2.failures.resolve("fail-restart", "retry_2")
        assert resolved.recovered
        assert [a.action for a in resolved.attempts] == ["retry_1", "retry_2"]
        assert await mgr2.failures.list_open() == []
    finally:
        await mgr2.shutdown()


# ----------------------------------------------------------------------
# Safe logging: no credentials from errors/URLs/bodies/tool output
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_payloads_redacted_and_bounded(manager) -> None:
    rec = manager.failures
    long_body = "x" * 5000
    await rec.record_failure(
        "http_401",
        "POST https://api.example.com/v1/login failed 401: "
        "password=hunter2-secret api_key=AKIAIOSFODNN7EXAMPLE "
        f"body={long_body}",
        failure_id="fail-secrets",
        arguments={"password": "hunter2-secret", "username": "u"},
        observed_symptoms=["login failed with password=hunter2-secret"],
        context={"auth": "Bearer abcdefghijklmnopqrst"},
        environment={"token": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"},
    )
    row = await manager.get("fail-secrets")
    assert row is not None
    blob = str(row.data) + str(row.metadata) + row.content
    assert "hunter2-secret" not in blob
    assert "AKIAIOSFODNN7EXAMPLE" not in blob
    assert "abcdefghijklmnopqrst" not in blob
    assert "ghp_abcdefghijklmnopqrstuvwxyz1234567890" not in blob
    assert long_body not in blob  # bounded, not stored whole
    failure = await rec.get_failure("fail-secrets")
    assert failure is not None
    assert failure.context.get("failing_call", {}).get("password") == "[redacted]"


# ----------------------------------------------------------------------
# Disabled mode + agent single-shot compatibility
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_mode_persists_nothing(memory_config) -> None:
    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    record = await mgr.failures.record_failure("quiet", "boom",
                                               failure_id="fail-disabled")
    assert not record.recovered
    assert await mgr.failures.get_failure("fail-disabled") is None


@pytest.mark.asyncio
async def test_single_shot_failure_readable_via_recorder(manager) -> None:
    stored = await manager.remember_failure(
        FailureRecord(
            failure_type="stale_coordinates",
            error="window moved; clicked empty space",
            action="click_indicators_button",
            successful_recovery="vision-based grounding",
            recovery_status=OutcomeStatus.SUCCESS,
        )
    )
    read_back = await manager.failures.get_failure(stored.id)
    assert read_back is not None
    assert read_back.failure_type == "stale_coordinates"
    assert read_back.recovered
    # Agent deterministic ids round-trip too; the type is tagged, not in content.
    assert "stale_coordinates" in read_back.to_memory().tags


@pytest.mark.asyncio
async def test_failure_type_retrievable_by_search(manager) -> None:
    rec = manager.failures
    await rec.record_failure(
        "stale_coordinates", "window moved; clicked empty space",
        failure_id="fail-searchable", action="click_indicators_button",
    )
    await rec.resolve("fail-searchable", "vision-based grounding")
    results = await manager.retrieve("clicking indicators button failed coordinates")
    assert any(r.memory.id == "fail-searchable" for r in results)
    assert any("vision-based grounding" in r.memory.content for r in results)
