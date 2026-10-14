# PHASE 11 — FAILURE AND RECOVERY MEMORY

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–10 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/failures.py` (new),
    `.../services/manager.py`, `.../services/__init__.py`,
    `.../domain/preference.py`, `.../domain/__init__.py`,
    `tests/memory/test_failure_memory.py` (new), `docs/memory.md`,
    `docs/memory/*`.
  - **Shared (Core)**: none. No Trading/Agent/Planner/Desktop/Vision file
    modified.

## Scope

Persist failures with observed symptoms, context, attempted actions, error
category, related episode/procedure, recovery attempts and results —
distinguishing observed facts from inferred causes (an unverified suspected
cause must never become a confirmed fact). Link successful alternatives with
source evidence. No automatic procedure revision. Bound and redact error
payloads (never persist credentials). Integrate with the verified existing
failure/recovery contracts (agent deterministic ids, `derived_from` /
`failure_in_episode` links, `MemoryStored` announcements). No second bus.

## Existing implementation reused

- `FailureRecord` + `to_memory()` projection + `manager.remember_failure`
  verb + agent `_record_failures` (deterministic ids, recovery inference,
  episode links) — extended, not replaced.
- `EpisodeRecorder` lifecycle shape (`_mutate` read-modify-write,
  `_row_to_*` rebuild, idempotent link-after-write) — mirrored for failures.
- `redact_text` / `redact_keys` / `safe_preview`, `WriteResult` five-state
  outcomes, version-guarded `manager.update`, `linked_ids` expansion — all
  reused as-is.
- The only failure-adjacent event class in the repo is voice-owned
  `VoiceError` (unrelated), so "verified existing failure/recovery events"
  = the agent row shape + link contracts, not an event subscription. No new
  bus or event class introduced.

## Changes implemented

- `domain/preference.py`: new `RecoveryAttempt` value object
  (action/status/detail/timestamp, lossless round-trip); `FailureRecord`
  gains `observed_symptoms`, `suspected_cause` + `cause_confirmed`,
  `attempts`, `episode_id`, `procedure_id`, and `from_dict` (old rows parse
  via defaults); `to_memory()` quarantines unconfirmed suspicions from the
  summary, stamps `episode_id`/task/session metadata.
- `services/failures.py` (new `FailureRecorder`, `manager.failures`):
  `record_failure` (idempotent by id, honest FAILED/disabled outcomes,
  missing link targets skipped) → `record_attempt` (dedup, cap 50, counted
  truncation) → `resolve` / `confirm_cause` (idempotent); `link_episode` /
  `link_procedure` (late, idempotent); `link_alternative` /
  `failure_alternatives` (`recovered_by` edges with evidence, alternative
  never modified); `get_failure` / `list_failures` / `list_open` (bounded,
  reads never raise).
- `services/manager.py` + `services/__init__.py`: construct + export
  `FailureRecorder` (`failures` accessor). `remember_failure` unchanged.

## Files added

- `src/aetheros/memory/services/failures.py`.
- `tests/memory/test_failure_memory.py` (17 tests).
- `docs/memory/phase-reports/phase-11.md` (this report).

## Files modified

- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `src/aetheros/memory/domain/preference.py`
- `src/aetheros/memory/domain/__init__.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–10) and Trading changes present at
phase start; none within the regions I edited.

## Migrations and compatibility impact

No schema migration (failures ride `memory_items` / `memory_links`). New
`FailureRecord` fields default empty; `from_dict` parses pre-Phase-11 rows —
covered by the single-shot compat test (an agent-integration-style row reads
back with `recovered=True`). No public API removed.

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (202 passed, 4 skipped).
- `python -m pytest tests/memory/test_failure_memory.py -o addopts="" -q`
  (first run) → 13 passed, **4 failed** (1 real recorder bug + 3 test bugs).
- `python -m pytest tests/memory/test_failure_memory.py -o addopts="" -q`
  (after fixes) → exit 0 (**17 passed**).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**219 passed,
  4 skipped**: prior 202 + 17 new, 0 failed).
- `ruff check` on touched files → 3 findings, auto-fixed (`--fix`),
  re-check clean; suite re-run green after the fix.
- `mypy`: unavailable in env (`No module named mypy`), same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **17 passed**, 0 failed, 0 skipped.
- Full memory suite: **219 passed, 4 skipped**, 0 failed. (Before this phase:
  202 passed / 4 skipped; delta = +17 new tests.)
- Not run: suites outside `tests/memory` (out of scope; no shared file
  touched).
- Failure-driven fixes (the suite caught real bugs before merge):
  1. `_mutate` never recomputed tags/confidence/importance → a resolved
     failure kept the stale `open` tag (fixed: rebuild all presentation
     fields from the updated record on every mutation).
  2. `link_episode`/`link_procedure` created duplicate graph link rows on
     repeat (fixed: only link when the row actually changed).
  3. Three test assertion bugs (KeyError on absent metadata key, type string
     asserted in content instead of tags, tautological `or True`).

## Baseline failures and evidence

None. First run's 4 failures were caused by this phase's own new code/tests
(not pre-existing) and fixed in-phase; evidence above. The only warnings are
the pre-existing `datetime.utcnow()` deprecation cosmetics (also present at
HEAD in unrelated tests).

## Required acceptance evidence

Contract-mandated areas, all in `test_failure_memory.py`:
- Failed recovery: `test_failed_recovery_stays_open`.
- Multiple attempts: `test_multiple_attempts_accumulate_in_order`.
- Successful recovery: `test_successful_recovery_closes_with_evidence`.
- Duplicate delivery: `test_duplicate_delivery_is_noop`,
  `test_repeated_resolve_writes_nothing`.
- Missing/late links: `test_missing_link_targets_skipped_not_failed`,
  `test_late_episode_link_attaches`,
  `test_link_alternative_missing_target_raises`.
- Restart: `test_restart_lists_open_and_resumes` (real file DB, fresh
  manager).
- Safe logging: `test_error_payloads_redacted_and_bounded`.
- Historical retrieval: `test_list_filters_and_history`,
  `test_failure_type_retrievable_by_search`.
- Quarantine: `test_suspected_cause_quarantined_until_confirmed`.
- No auto-revision: `test_link_alternative_records_evidence_without_editing`.
- Disabled: `test_disabled_mode_persists_nothing`.
- Compat: `test_single_shot_failure_readable_via_recorder`.
- Degraded reads: `test_get_failure_degrades_to_none`.

## Security and operational concerns

- Redaction before persistence on every input (error, symptoms, attempts,
  context, environment, cause, evidence) — pinned by a dedicated test with
  credentials in exception text, URLs, bodies and tool output.
- Quarantine is structural (summary built without the suspicion), not a
  display filter — retrieval can never surface an unconfirmed cause as fact.
- Alternatives are links, never edits — a later phase cannot inherit a
  silently mutated procedure from this one.
- Bounded retries (3), bounded attempts (50, counted), bounded listings
  (limit + 10×100 page cap). FAILED writes raise; disabled returns unsaved.

## Remaining work

- Carried forward: Finding #1 (authz/redaction/export no-leak layer);
  UP017 style; `datetime.utcnow()` cosmetic.
- Next consumer: procedure evolution mines `failure_type` +
  `successful_recovery` + `recovered_by` evidence (contract in
  `failures.py` docstring + `docs/memory.md` §Failure & recovery memory).

## Exact next-phase handoff

Phase 11 is **DONE** (suite green: 17 new tests, full memory suite 219
passed / 4 skipped). Re-read the contract, `implementation-state.md`
(§Phase 11 handoff), this report, and the live `failures.py` / `manager.py`
source before the next phase. Key identifiers: `FailureRecorder`,
`manager.failures`, `RecoveryAttempt`, `FailureRecord.from_dict`,
`recovered_by` link type.

PHASE 11 — DONE
