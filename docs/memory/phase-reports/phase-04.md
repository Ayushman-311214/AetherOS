# PHASE 04 — WRITE-PATH HARDENING (RESULTS, IDEMPOTENCY, CONCURRENCY, PROJECTION REPAIR)

Status: DONE

## Starting revision and working-tree summary

- Branch `development`, HEAD `b0a2537` ("Initialize memory system").
- Concurrent audit at phase start (`git status`): the Trading agent holds a large
  uncommitted working set under `src/aetheros/trading/**`, `graphify-out/**`,
  `src/aetheros/logs/**`, and the two **shared** files
  `bootstrap/bootstrapper.py` and `config/settings.py` (modified). The `data/memory.db`
  file is modified by runtime. **No overlap with the Memory-owned source paths
  this phase touched.**
- Pre-existing Memory-area state: `docs/memory/**` control dir (Phases 0–3),
  `docs/modules/memory.txt` (untracked). The Memory source files I edited were
  unmodified by other agents at phase start.

## Scope

Phase 4 only: harden the **write path** with the honesty/safety features the
architecture audit flagged as missing, as the smallest coherent additive change.
Specifically close four gaps: (1) no first-class write-result type; (2) no
idempotent write; (3) no optimistic-concurrency guard on edits; (4) no explicit
vector-projection verify/repair seam. Also make the manager verbs honest under a
disabled config. No Trading Intelligence logic, no new EventBus, no provider
changes, no schema migration.

## Existing implementation reused

- `MemoryManager` / `MemoryWriter` / `MemoryRepository` / `VectorIndex` / `MemoryValidator`
  / `MemoryPolicyEngine` — all composed as-is; new behaviour layered on top.
- Validation + secret redaction (Phase 3) already run on every write — reused
  unchanged via `self._validator.validate(...)`.
- DB error wrapping (`MemoryStorageError`) already present in `SQLiteDatabase`;
  the new `execute_write` follows the identical rollback/wrap pattern.
- Scope/soft-delete filtering already enforced in `repository.candidates()` and
  scoped vector search in the retriever — relied on, not re-implemented.
- `repository.find_by_metadata` / `exists` / `get` reused for idempotency checks.
- `MemoryConfig.enabled` and `MemoryManager._started` reused for disabled-mode gates.

## Changes implemented

1. **`WriteResult` / `WriteStatus`** (`services/results.py`, new): five honest
   outcomes (STORED / SKIPPED / FAILED / UNAVAILABLE / PENDING) with `.ok` and
   `.persisted` helpers and factory constructors. Exported from
   `memory/services/__init__.py`.
2. **`MemoryManager.store(memory, *, idempotency_key=None)`** (new verb): returns
   a `WriteResult`; enforces idempotency by memory id and by optional
   caller key (stamped into metadata, looked up via `find_by_metadata`); honours
   retention policy as `SKIPPED`; reports storage/embedding failure as `FAILED`
   without persisting; returns `UNAVAILABLE` when disabled/uninitialized.
3. **Disabled-mode honesty** on existing verbs: `remember_memory` is a no-op
   returning the unsaved object when `config.enabled` is false; `retrieve`
   degrades to `[]` when disabled/not-started (optional recall degrades safely).
4. **Optimistic-concurrency guard**: `update(id, ..., expected_version=N)` →
   `MemoryManager._update_guarded` → `MemoryRepository.update_guarded` → conditional
   `UPDATE ... WHERE id=? AND version=?` via new `SQLiteDatabase.execute_write`
   (returns rowcount). 0 rows ⇒ `MemoryConflictError` (new, `MEMORY_CONFLICT`);
   losing write never persists and the vector is not re-indexed. Default path
   (no `expected_version`) is unchanged last-writer-wins.
5. **Projection verify/repair seam**: `MemoryWriter.reindex` /
   `verify_projection` / `repair_projection`, surfaced on `MemoryManager`.
   Uses new `VectorIndex.ids()` to inventory the projection; rebuilds missing
   vectors from authoritative rows and removes orphans. Idempotent.

## Files added

- `src/aetheros/memory/services/results.py`
- `tests/memory/test_write_path.py`
- `docs/memory/phase-reports/phase-04.md` (this file)

## Files modified

- `src/aetheros/memory/services/manager.py` — `store`, disabled gates on
  `remember_memory`/`retrieve`, `expected_version` on `update`, `_update_guarded`,
  `verify_projection`/`repair_projection` passthroughs, import of `WriteResult`.
- `src/aetheros/memory/services/writer.py` — `reindex`, `verify_projection`,
  `repair_projection`; `typing.Any` import.
- `src/aetheros/memory/services/__init__.py` — export `WriteResult`/`WriteStatus`.
- `src/aetheros/memory/storage/repository.py` — `update_guarded`,
  `_update_guarded_sync`, `_UPDATE_SQL`.
- `src/aetheros/memory/storage/database.py` — `execute_write` (rowcount-returning).
- `src/aetheros/memory/vector/index.py` — `ids()`.
- `src/aetheros/core/errors/memory_error.py` — `MemoryConflictError`.
- `docs/memory/architecture.md`, `docs/memory.md`, `docs/memory/implementation-state.md`.

## Shared files touched and justification

None. All edits are Memory-owned source or Memory docs. The shared files
(`bootstrapper.py`, `settings.py`) — mid-edit by the Trading agent — were **not**
touched; the new behaviour needed no bootstrap or settings change (it reuses the
existing `MemoryConfig.enabled` and the already-wired disabled-mode bootstrap).

## Concurrent changes observed

The Trading agent's large uncommitted working set (listed above) was present at
start and left untouched. No concurrent modification of any Memory source file
was observed during the phase.

## Migrations and compatibility impact

- **No schema migration.** The guarded update reuses the existing `version`
  column; `execute_write` is additive.
- **Backward compatible.** `remember`/`remember_memory`/`update(id, **changes)`
  keep their signatures and behaviour (the new `expected_version` is keyword-only
  and optional; existing callers in `tools.py`, `provider.py`, `agent_memory.py`
  are unaffected). `store` is a new verb. All 74 pre-existing memory tests pass
  unchanged.

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_write_path.py` → exit 0 (14 passed, after
  one iteration fixing the orphan-vector test to reflect the real FK-CASCADE
  behaviour).
- `python -m pytest tests/memory` → exit 0 (88 passed).
- `python -m pytest tests/memory tests/agents` → exit 0 (427 passed).
- `ruff check` on changed files → only pre-existing/project-wide findings remain
  (I001 import-order and B905 `zip(strict=)` exist in these files at HEAD with my
  changes stashed; UP042 `(str, Enum)` is the project-wide enum convention used by
  every `domain/enums.py` type). No new-code lint regressions.
- `PYTHONPATH=src python -c "import aetheros.memory.services ..."` → import smoke OK.

## Tests passed / failed / skipped / not run

- **Passed:** 427 (`tests/memory` 88 + `tests/agents` 339). New: 14 in
  `test_write_path.py`.
- **Failed:** 0 in the scoped suites.
- **Skipped / deselected / timed-out:** none observed in the scoped run.
- **Not run:** the full repo suite (`tests/trading`, `tests/cli`, etc.) was not
  run this phase; see baseline note below. No claim is made that the whole
  regression suite passes.

## Baseline failures and evidence

The project memory records 22 pre-existing full-suite failures described as
environmental (prior baseline). This phase did **not** re-establish that baseline
with fresh evidence and therefore makes **no** claim about them. Scoped suites
touching changed code (`tests/memory`, `tests/agents`) are green with evidence above.

## Required acceptance evidence

- Five-state result: `test_store_returns_stored`, `test_store_skips_on_policy`,
  `test_store_reports_failure_without_persisting`, `test_disabled_store_is_unavailable`.
- Idempotency: `test_store_is_idempotent_by_id`, `test_store_is_idempotent_by_key`
  (both assert `_repo.count() == 1`).
- Disabled recall degrades: `test_disabled_retrieve_degrades_to_empty`.
- Concurrency guard: `test_guarded_update_succeeds_on_matching_version`,
  `test_guarded_update_rejects_stale_version` (asserts winner survived),
  `test_unguarded_update_is_last_writer_wins`.
- Projection repair (real embedder, real SQLite): `test_projection_consistent_after_normal_writes`,
  `test_repair_reindexes_missing_vector`, `test_repair_removes_orphan_vector`,
  `test_repair_is_idempotent`.
- All exercise the real hashing embedder + real SQLite via the `manager` fixture.
  **Note:** this is hashing-grade semantics; a real-provider integration test is
  still deferred to the embedding-provider phase (§5), unchanged by this phase.

## Security and operational concerns

- No new secret handling; validation/redaction path unchanged and still enforced.
- Soft-delete no-leak invariant unchanged; `repair_projection` additionally
  removes orphan vectors (defensive — FK CASCADE already prevents orphans on the
  normal delete path).
- `FAILED` never persists and surfaces the error reason (no silent success).
- Idempotency key is stored in plaintext metadata; callers must not use secrets
  as keys (documented behaviour, same trust model as other metadata).

## Remaining work

- Graph-side projection rebuild/repair (knowledge graph has no reconciliation yet).
- Automatic repair-on-startup / scheduled consistency check.
- `PENDING` is reserved but has no async-durable write path yet.
- Full authorization / scope-filtering / deletion-visibility layer (Finding #1)
  and real embedding-provider integration (§5) remain for later phases — unchanged.

## Exact next-phase handoff

Phase 4 is DONE. The write path now has honest results, idempotency, an optional
optimistic-concurrency guard, and a real (vector) projection verify/repair seam,
all additive and backward-compatible. Top candidates next (unchanged priority):
Finding #1 (full authorization/scope/deletion-visibility across retrieval, cache,
embedding, graph expansion, export) and the real embedding-provider phase (§5),
plus the graph-side repair counterpart to this phase's vector repair.

PHASE 04 — DONE
