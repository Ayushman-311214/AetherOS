# PHASE 09 — WORKING MEMORY

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–8 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/working_memory.py`,
    `.../services/manager.py`, `.../services/__init__.py`, `.../config.py`,
    `tests/memory/test_working_memory.py`, `tests/memory/test_embedding_provider.py`,
    `docs/memory.md`, `docs/memory/*`.
  - **Shared (Core)**: `src/aetheros/config/settings.py` — one additive field.
- No Trading/Agent/Planner/Desktop/Vision file modified.

## Scope

Turn working memory from a single process-wide bounded deque into short-lived
**scoped** context: session/task ownership, size limits, expiration, cleanup,
concurrent-update safety, documented restart behavior, current-observation
freshness/sequence rules, and explicit evidence selection for durable formation —
without making working state durable by default and without breaking the legacy
single-session API the Agent/Desktop layers use.

## Existing implementation reused

- `WorkingItem` dataclass, capacity-eviction heuristic (least-important oldest),
  `summarize`, and `to_memories` promotion shape — extended, not replaced.
- `MemoryManager.promote_working` / `manager.working` accessor — extended.
- `MemoryImportance` enum, `Memory`/`MemorySource` domain types, `_clock.utcnow`,
  `MemoryConfig.from_settings` / `for_memory_db`, settings `Field` + `AliasChoices`
  convention — all reused as-is.
- No new EventBus, storage table, or persistence path introduced (working memory
  stays in-process by design).

## Changes implemented

- `working_memory.py` rewritten: multi-session container (`_sessions`,
  `_observations` keyed by `session_id`), each `WorkingItem` gains `session_id`,
  `task_id`, `observed_at`, `sequence`, `expires_at`, `is_evidence`.
  - Session isolation + per-session capacity.
  - TTL via `ttl_seconds` / session-default `default_ttl_seconds`; injectable
    `clock`; `sweep_expired`; expiry honoured on every read.
  - `observe(...)` + `_is_newer(...)` freshness rule; new `ObservationResult`.
  - Cleanup: `end_session`, `complete_task`, `sweep_expired`, scoped `clear`.
  - `mark_evidence` + `to_memories(only_evidence=...)`.
  - `threading.RLock` around all shared state.
- `manager.py`: wires `default_ttl_seconds` from config; `promote_working` gains
  `session_id` / `only_evidence` and short-circuits to `[]` when disabled.
- `config.py`: additive `working_ttl_seconds` field in both factories.
- `settings.py`: additive `MEMORY_WORKING_TTL_SECONDS` field (default 0.0, ge 0).
- `services/__init__.py`: export `ObservationResult`.

## Files added

- `tests/memory/test_working_memory.py` (22 tests).
- `docs/memory/phase-reports/phase-09.md` (this report).

## Files modified

- `src/aetheros/memory/services/working_memory.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `src/aetheros/memory/config.py`
- `src/aetheros/config/settings.py` (shared, additive)
- `tests/memory/test_embedding_provider.py` (helper updated for new config field)
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

- `src/aetheros/config/settings.py`: one additive `MEMORY_WORKING_TTL_SECONDS`
  field following the existing memory-settings pattern (default preserves prior
  behaviour — no expiry). Smallest compatible change; no existing field altered.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–8) and Trading changes present at phase
start; none within the regions I edited beyond my own prior-phase work.

## Migrations and compatibility impact

No schema migration (working memory is not persisted). All new `WorkingItem`
fields and `MemoryConfig.working_ttl_seconds` are additive with defaults
preserving behaviour. The legacy single-session API (`add/update/remove/items/
clear` without `session_id`) now routes to a `"default"` session and behaves as
before — covered by `test_legacy_single_session_api_unchanged`. One direct
`MemoryConfig(**base)` test helper required the new field (updated).

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_working_memory.py -o addopts="" -q` → exit 0.
- `python -m pytest tests/memory -o addopts="" -q` → exit 0.
- `PYTHONPATH=src python -c "<load Settings + MemoryConfig.from_settings>"` →
  exit 0 (`MEMORY_WORKING_TTL_SECONDS` resolves to `0.0`).
- `ruff check <changed files>` → clean apart from pre-existing repo-wide `UP017`.
- `python -m mypy …` → `No module named mypy` (unavailable in env, as prior phases).

## Tests passed / failed / skipped / not run

- New file: **22 passed**, 0 failed, 0 skipped.
- Full memory suite: **181 passed, 4 skipped**, 0 failed. (Before this phase:
  159 passed / 4 skipped; delta = +22 new tests.)
- Not run: suites outside `tests/memory` (out of scope; only an additive shared
  settings field was touched, exercised via the load check above).

## Baseline failures and evidence

None. During development, 4 `test_embedding_provider.py` factory tests failed
because a direct `MemoryConfig(**base)` helper lacked the new field; this was
**caused by my change** (not pre-existing) and fixed by adding
`working_ttl_seconds=0.0` to that helper. Re-run: full suite green.

## Required acceptance evidence

Contract-mandated test areas, all in `test_working_memory.py`:
- Session isolation: `test_sessions_are_isolated`,
  `test_end_session_only_clears_that_session`, `test_observations_are_session_scoped`.
- TTL boundaries (controllable clock): `test_ttl_item_expires_exactly_at_boundary`,
  `test_sweep_expired_reclaims_items`, `test_default_ttl_applies_when_item_ttl_unset`,
  `test_zero_ttl_means_no_expiry`, `test_len_excludes_expired`.
- Stale updates: `test_stale_sequence_observation_rejected`,
  `test_newer_sequence_observation_accepted`,
  `test_stale_timestamp_observation_rejected`,
  `test_sequenced_observation_beats_unsequenced`.
- Task-completion cleanup: `test_complete_task_purges_only_that_task`.
- Bounded size: `test_capacity_evicts_least_important_oldest`,
  `test_capacity_is_per_session`.
- Disabled mode: `test_disabled_mode_promotion_is_noop`.
- Agent/Desktop compatibility: `test_legacy_single_session_api_unchanged`.
- Evidence selection: `test_only_evidence_promotes_marked_items`,
  `test_manager_promote_only_evidence`, `test_importance_promotion_still_works`.

## Security and operational concerns

- Working memory remains ephemeral; current observations are explicitly separated
  from historical references and cannot be overwritten by stale updates
  (freshness rule), upholding "current verified state overrides historical
  memory".
- Promotion is explicit and disabled-mode-safe; nothing durable is created by
  accident. Promoted memories inherit the standard write path (content policy /
  redaction applies there).
- Concurrency guarded by a lock; TTL cleanup is bounded (single pass per sweep).

## Remaining work

- No background sweeper is scheduled; `sweep_expired()` is caller-driven (reads
  already hide expired items). Wiring a periodic sweep into the maintenance loop
  is a future, optional enhancement.
- Full authorization/redaction/export no-leak layer (Finding #1) still owed in a
  later phase.

## Exact next-phase handoff

Recorded in `docs/memory/implementation-state.md` (Phase 9 handoff section):
new identifiers, config/settings names, test command, and the carried-forward
Finding #1. Re-read the contract, that file, this report, and the live
`working_memory.py` / `manager.py` source before the next phase.

PHASE 09 — DONE
