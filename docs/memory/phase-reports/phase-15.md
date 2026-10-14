# PHASE 15 — USER MEMORY CONTROLS

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–14 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/controls.py` (new),
    `.../services/manager.py`, `.../services/__init__.py`,
    `.../services/confidence.py`, `.../tools.py`,
    `.../graph/store.py`, `.../storage/repository.py`,
    `tests/memory/test_user_controls.py` (new), `docs/memory.md`,
    `docs/memory/*`.
  - **Shared (CLI/Core)**: `src/aetheros/cli/commands.py` — additive verbs
    only, existing forget-wording preserved.
- No Trading/Agent/Planner/Desktop/Vision file modified.

## Scope

Authorized inspection, correction, forgetting, deletion, export,
statistics and enable/disable through Memory APIs — on the existing
identity model (scopes + master switch; no parallel auth), with global
vs session/user disable semantics, attributable correction history,
immediate forget-exclusion, coordinated erasure (soft ≠ erasure),
trading-history protection with an open override policy, and no raw
storage internals in user-facing surfaces.

## Existing implementation reused

- `manager.forget` / `get` / `update` / `link` verbs, `confidence.correct`
  path, `MemoryStored`/`MemoryForgotten` announcements, `ENABLE_MEMORY`
  gating convention, `_repo`/`_vectors`/`_graph` handles — all reused.
- No new bus, events (existing ones announce), tables, migrations, knobs,
  scheduler, or auth system. No background jobs exist (verified by search):
  "pending-job behavior" is honestly defined as zeroed maintenance
  reports + run-to-completion in-flight ops, not a queue that was built.

## Changes implemented

- `services/controls.py` (new `UserControls`, `manager.controls`):
  scope-enforced inspect/list/correct/forget/erase/export/stats + disable
  gates + `is_disabled` + `_require_enabled` on writes.
- `services/manager.py`: construct + expose (`controls` accessor);
  `forget` hardened (soft drops vector immediately with logged best-
  effort; hard deletes vector + both-direction links + graph evidence).
- `services/confidence.py`: correction gate widened to USER authorship
  (veracity labels truth-status, source labels authorship).
- `storage/repository.py`: `delete_links(memory_id)` (memory_links lacks
  FK cascade — without this, erasure orphaned edges).
- `graph/store.py`: `scrub_memory(memory_id)` (strips erased id from edge
  evidence lists; topology stays — shared knowledge, not the row's).
- `memory/tools.py`: `correct_memory` + `export_memories` tools; additive
  scope params on get/update/list/forget; content-edits route through
  correction; `list_memories` off raw `mgr._repo`.
- `cli/commands.py`: `correct` / `erase` / `export` verbs; list/forget via
  controls; existing hard-delete wording preserved.

## Files added

- `src/aetheros/memory/services/controls.py`.
- `tests/memory/test_user_controls.py` (17 tests).
- `docs/memory/phase-reports/phase-15.md` (this report).

## Files modified

- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `src/aetheros/memory/services/confidence.py`
- `src/aetheros/memory/tools.py`
- `src/aetheros/memory/graph/store.py`
- `src/aetheros/memory/storage/repository.py`
- `src/aetheros/cli/commands.py` (shared, additive)
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

- `src/aetheros/cli/commands.py`: three additive subcommands + list/forget
  routed through controls (same outputs, stricter path). Existing
  `test_memory_forget` wording ("hard-deleted") preserved deliberately —
  breaking it for prose would be a gratuitous contract change.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–14) and Trading changes present at
phase start; none within the regions I edited.

## Migrations and compatibility impact

No schema migration. `forget_memory(hard=True)` now returns coordinated
counts (superset keys) instead of bare `hard: true` — same `ok` shape.
`update_memory(content=)` now routes through correction (same version-bump
semantics; the pinned existing test passes unmodified). `get_memory` on a
missing id returns NOT_FOUND as before. No public API removed.

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (276 passed, 4 skipped).
- `python -m pytest tests/memory/test_user_controls.py -o addopts="" -q`
  (first run) → 14 passed, **3 failed** (2 test bugs + 1 design gap).
- After fixes → exit 0 (**17 passed**).
- `python -m pytest tests/memory tests/cli/test_memory_command.py -o
  addopts="" -q` → 1 failed (CLI wording regression, mine) → fixed →
  exit 0 (**297 passed, 4 skipped**: 276 memory + 17 new + 4 CLI... note:
  276 included pre-existing memory tests; +17 new memory + CLI file = 297).
- `ruff check` on touched files → my E741 fixed; remaining F841 (CLI) and
  earlier UP042/B905 evidenced pre-existing at HEAD, untouched.
- `mypy`: unavailable in env, same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **17 passed**, 0 failed, 0 skipped.
- Memory + CLI suite: **297 passed, 4 skipped**, 0 failed.
- Not run: suites outside `tests/memory` + `tests/cli/test_memory_command.py`
  (out of scope; one additive CLI file touched, exercised via its tests).
- Failure-driven fixes:
  1. USER-authored (tool-created) rows uncorrectable — gate widened to
     source authorship (design gap, not test bug).
  2. CLI `forget hard` wording regression — restored "hard-deleted".
  3. Tool tests need container wiring (existing `register_singleton`
     pattern adopted).
  4. Single-entity rows create graph nodes but no edges (sanity assert
     replaced with a two-entity evidence-holder check).

## Baseline failures and evidence

None pre-existing. All Phase 15 failures were this phase's own new
code/tests, fixed in-phase (evidence above).

## Required acceptance evidence

Contract-mandated areas, all in `test_user_controls.py` unless noted:
- Authorization: `test_own_scope_inspect_and_list`,
  `test_session_scoping`.
- Cross-scope denial: `test_cross_scope_denial_reveals_nothing`
  (read/correct/forget/erase/export).
- Correction precedence: `test_correction_precedence_and_history`,
  `test_correct_refuses_immutable_history`.
- Export fidelity: `test_export_fidelity_round_trip`
  (from_dict round-trip + history + links + no-internals assertions).
- Disabled writes/recall: `test_global_disable_writes_and_recall`,
  `test_session_disable_purges_working_and_gates_writes`,
  `test_user_disable_gate`.
- Deleted data exclusion: `test_soft_forget_excludes_immediately`
  (recall/export/listings/vectors), `test_deleted_never_served_even_with_flag`
  (Phase 14 suite, still green).
- Pending-job behavior: `test_maintenance_verbs_zeroed_when_disabled`.
- Trading-history guard: `test_history_guard_and_explicit_override`.
- Coordinated erase: `test_hard_erase_is_coordinated` (row/vector/links/
  graph-evidence/neighbour-intact/recall-clean).
- No raw internals: `test_tools_round_trip_without_internals` (JSON-
  serialisable payloads), `test_cli_memory_verbs`.

## Security and operational concerns

- Scope boundary is uniform-denial (no existence oracle across scopes);
  enforcement documented at service/tools/CLI (storage has no auth
  boundary — single-operator app, stated not hidden).
- Erasure completeness is counted and verifiable (links_removed +
  graph_edges_scrubbed in the receipt); backups called out as deployment
  policy, never pretended.
- History guard defaults closed, opens explicitly (`allow_history`) with
  full coordination — erasure/retention conflicts resolve openly.
- Disabled gates are restart-cleared (no phantom persistent policy);
  durable rows untouched by disable (disable ≠ forget).

## Remaining work

- Carried forward: Finding #1 (full authz/redaction/export no-leak layer
  — Phase 15 adds scope enforcement at the controls layer; the deeper
  retrieval/cache/embedding/graph/export no-leak pass is still owed);
  UP017/UP042 style; `datetime.utcnow()` cosmetic; B905/F841 pre-existing.
- Optional: persistent per-user disable policy in configuration (deferred
  deliberately — gates are restart-cleared by design).

## Exact next-phase handoff

Phase 15 is **DONE** (suite green: 17 new tests, memory + CLI suite 297
passed / 4 skipped). Re-read the contract, `implementation-state.md`
(§Phase 15 handoff), this report, and the live `controls.py` /
`manager.py` source before the next phase. Key identifiers:
`UserControls`, `manager.controls`, `repo.delete_links`,
`graph.scrub_memory`, `EXPORT_FORMAT_VERSION`.

PHASE 15 — DONE
