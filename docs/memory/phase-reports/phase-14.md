# PHASE 14 — DECAY, RETENTION, AND LIFECYCLE

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–13 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/lifecycle.py`,
    `.../services/manager.py`, `.../services/retriever.py`,
    `.../services/writer.py`, `.../domain/enums.py`,
    `.../domain/__init__.py`, `.../storage/repository.py`,
    `tests/memory/test_lifecycle.py` (new), `docs/memory.md`,
    `docs/memory/*`.
  - **Shared (Core)**: none. No Trading/Agent/Planner/Desktop/Vision file
    modified.

## Scope

Explicit ACTIVE/STALE/DECAYED/ARCHIVED transitions, TTL, soft deletion,
configured retention; confidence/freshness/importance/lifecycle/deletion
separation; documented transitions + reactivation; trading-history
protection; bounded/idempotent/restartable/concurrent-safe processing with
controllable clock; propagation to vector/graph projections, caches and
context; immediate authoritative visibility; backup-retention and
archival/soft-delete/erasure documentation.

## Existing implementation reused

- `MemoryLifecycle.evaluate()` shape (PERMANENT veto, TTL-first,
  confidence flag, recency chain) and `decay_pass()` verb — hardened in
  place, not replaced. No new scheduler (caller-invoked verb, like
  `consolidate()`), no new tables/events/buses/knobs.
- Retriever `_passes` + repository SQL status filters, `update_guarded`,
  writer `update`/`reindex`, vector `delete`, `manager.forget` — all reused.

## Changes implemented

- `domain/enums.py`: new `MemoryStatus.DECAYED` (+ transition doc) and
  shared `RECALLABLE_STATUSES` (ACTIVE/LOW_CONFIDENCE/STALE/DECAYED);
  exported from `domain/__init__.py`.
- `services/lifecycle.py`: 3/6/9 half-life neglect chain; history
  protection (TRADING/PREDICTION skip neglect; CRITICAL never archives);
  bounded batched `decay_pass(now, batch_size, max_batches)` with
  version-guarded transitions (`skipped_conflict`), same-pass vector
  propagation (re-index recallable, delete otherwise), injectable clock;
  pure-function `evaluate` (fixed-point re-runs, automatic reactivation
  on fresh access).
- `services/manager.py`: `decay()` forwards clock/batch kwargs;
  new `reactivate()` verb (explicit, re-indexes, refuses DELETED/missing).
- `services/retriever.py` + `storage/repository.py`: one shared recallable
  set (DECAYED served by default, weak score ranks last).
- `services/writer.py`: `verify/repair_projection` narrowed to recallable
  rows (archived/expired vectors are orphans-to-clean, never "missing").

## Files added

- `tests/memory/test_lifecycle.py` (21 tests).
- `docs/memory/phase-reports/phase-14.md` (this report).

## Files modified

- `src/aetheros/memory/services/lifecycle.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/retriever.py`
- `src/aetheros/memory/services/writer.py`
- `src/aetheros/memory/domain/enums.py`
- `src/aetheros/memory/domain/__init__.py`
- `src/aetheros/memory/storage/repository.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–13) and Trading changes present at
phase start; none within the regions I edited.

## Migrations and compatibility impact

No schema migration (statuses are column values; DECAYED is a new value on
the existing column). Old rows evaluate under the new chain on next pass
(STALE→DECAYED→ARCHIVED progression, no surprise archival: thresholds only
deepen neglect states). `decay()`/`consolidate()` defaults preserve old
call shapes. `verify_projection` "memories" count now covers recallable
rows only (documented semantic narrowing). No public API removed.

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (255 passed, 4 skipped).
- `python -m pytest tests/memory/test_lifecycle.py -o addopts="" -q`
  (first run) → 18 passed, **3 failed** (2 test bugs + 1 real silent bug).
- After fixes → exit 0 (**21 passed**).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**276 passed,
  4 skipped**: prior 255 + 21 new, 0 failed).
- `ruff check` on touched files → only pre-existing UP042 (enum style) +
  B905 (writer zip), both evidenced at HEAD via stash, untouched. (One
  import-sort fix applied.)
- `mypy`: unavailable in env, same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **21 passed**, 0 failed, 0 skipped.
- Full memory suite: **276 passed, 4 skipped**, 0 failed. (Before this phase:
  255 passed / 4 skipped; delta = +21 new tests.)
- Not run: suites outside `tests/memory` (out of scope; one shared SQL
  string touched in the memory repository, exercised via the suite).
- Failure-driven fixes (the suite caught real bugs before merge):
  1. Dangling `RECALLABLE_STATUSES` reference hidden by a bare `except`
     (propagation silently no-op'd; vectors never followed status) —
     fixed + the except now logs.
  2. Missing `logger` import (F821; would NameError on propagation
     failure) — fixed.
  3. Boundary test evaluated a fixed clock instead of row-relative time —
     fixed.
  4. CRITICAL test missed the policy's PERMANENT stamp — test now pins
     both protection layers.

## Baseline failures and evidence

None pre-existing. All Phase 14 failures were this phase's own new
code/tests, fixed in-phase (evidence above).

## Required acceptance evidence

Contract-mandated areas, all in `test_lifecycle.py`:
- Time boundaries: `test_neglect_chain_boundaries`,
  `test_boundary_exactness`, `test_ttl_expiry_beats_neglect_chain`.
- High-importance exemptions: `test_critical_never_auto_archives`
  (both layers).
- Expired working memory: `test_working_memory_expiry_untouched_by_decay`.
- Archived retrieval policy: `test_archived_excluded_by_default`,
  `test_decayed_stays_recallable_but_ranks_last`.
- Deleted-record exclusion: `test_decay_never_touches_deleted`,
  `test_deleted_never_served_even_with_flag`.
- Interrupted jobs: `test_bounded_batches_and_resume`.
- Repeated execution: `test_bounded_batches_and_resume` (third-run fixed
  point).
- Concurrency: `test_concurrent_update_wins_over_decay`,
  `test_skipped_conflict_counted`.
- Projections: `test_archive_drops_vector_and_verify_agrees`,
  `test_recallable_transition_keeps_vector`.
- Reactivation: `test_explicit_reactivate_restores_and_reindexes`,
  `test_reactivate_refuses_deleted_and_missing`,
  `test_access_reactivates_stale_automatically`.
- Separation: `test_decay_never_writes_confidence`.
- Protection: `test_trading_history_protected_from_decay`,
  `test_low_confidence_flag_independent_of_age`.
- Disabled: `test_disabled_decay_is_noop`.

## Security and operational concerns

- Decay never deletes: the worst automatic outcome is ARCHIVED (row +
  links intact, reversible via reactivate). Erasure stays an explicit
  user action (`forget(hard=True)`).
- Authoritative visibility is immediate (status column); projections
  follow best-effort with logged warnings + repair reconciliation — no
  phantom consistency claims.
- Version-guarded transitions: a concurrent human edit always wins over
  a background demotion; the pass counts the skip and moves on.
- Trading history (predictions, outcomes, procedures) cannot be aged out
  by ordinary decay — only an explicit TTL or explicit user action
  removes it from recall.
- Backup retention is deployment policy (out of code contract) and is now
  documented as such rather than left implicit.

## Remaining work

- Carried forward: Finding #1 (authz/redaction/export no-leak layer);
  UP017/UP042 style; `datetime.utcnow()` cosmetic; B905 writer zip.
- Phase 15 (user memory controls) was requested earlier and superseded by
  this phase — still open. It can now build on `reactivate()`,
  the archival/soft-delete/erasure distinction, and `RECALLABLE_STATUSES`.

## Exact next-phase handoff

Phase 14 is **DONE** (suite green: 21 new tests, full memory suite 276
passed / 4 skipped). Re-read the contract, `implementation-state.md`
(§Phase 14 handoff), this report, and the live `lifecycle.py` /
`manager.py` source before the next phase. Key identifiers:
`MemoryStatus.DECAYED`, `RECALLABLE_STATUSES`,
`manager.decay(now, batch_size, max_batches)`, `manager.reactivate`.

PHASE 14 — DONE
