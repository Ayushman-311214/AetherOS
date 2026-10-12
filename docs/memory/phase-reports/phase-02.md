# PHASE 02 — PERSISTENT STORAGE AND MIGRATIONS

Status: DONE

## Starting revision and working-tree summary

- Branch `development`, HEAD `b0a2537`.
- At phase start, Memory source was clean (only untracked `docs/memory/`).
- Shared `src/aetheros/bootstrap/bootstrapper.py` and
  `src/aetheros/config/settings.py` carry the concurrent Trading agent's
  uncommitted edits — inspected only, **not touched** this phase.

## Scope

Harden and prove the authoritative SQLite store per the Phase 2 contract:
bounded lock/busy handling, native backup/recovery, and the full persistence +
migration acceptance test matrix. Reuse the existing schema/migrations/repository
— no new storage framework, no schema migration added (the Phase 1 domain design
maps completely to schema v1; a no-op v2 would be noise).

## Existing implementation reused

- Schema v1 (`storage/schema.py`): `memory_items` with durable `id` PK,
  provenance (`source` JSON + promoted indexed context columns
  `session_id/task_id/episode_id/instrument_id/user_id/application`), `version`,
  soft-delete `status`, projection tables (`memory_embeddings`, `entities`,
  `relationships`), `memory_links`, normalised `memory_tags`/`memory_entities`
  with `ON DELETE CASCADE`, `memory_access` audit.
- Ordered append-only migrations with idempotent skip, per-version atomic
  commit/rollback, `schema_migrations` version table (`storage/database.py`).
- WAL + `PRAGMA foreign_keys=ON`; RLock-serialised single connection driven
  async via `asyncio.to_thread` in `MemoryRepository`; transaction primitive
  `execute_script` with rollback.

## Changes implemented

- `SQLiteDatabase.__init__(busy_timeout_ms=5000)` + `PRAGMA busy_timeout` on
  connect — bounded wait on a contended cross-connection lock instead of an
  immediate "database is locked" error.
- `SQLiteDatabase.backup(destination) -> Path` — consistent online backup via
  SQLite's native backup API (safe under WAL); creates the destination dir;
  rejects `:memory:` destinations.
- No change to connection lifecycle semantics, repository API, or schema.

## Files added

- `tests/memory/test_storage_migrations.py` (15 tests).
- `docs/memory/phase-reports/phase-02.md` (this report).

## Files modified

- `src/aetheros/memory/storage/database.py` (Memory-owned) — busy_timeout +
  backup; +52/-1 lines.
- `docs/memory.md` — Backup & recovery section + irreversible-operation note.
- `docs/memory/architecture.md` §4.6 — reflect busy_timeout + backup now exist.
- `docs/memory/implementation-state.md` — Phase 2 ledger entry.

## Shared files touched and justification

None. `bootstrapper.py` / `settings.py` not touched (no new config needed; the
`busy_timeout_ms` default is a constructor argument, not a settings field).

## Concurrent changes observed

Unchanged from Phase 1: Trading agent's uncommitted edits span `trading/**` and
the two shared files. No overlap with Memory-owned storage paths. `git diff
--stat` confirms my only source change is `storage/database.py`.

## Migrations and compatibility impact

No schema migration added; `LATEST_VERSION` unchanged. `busy_timeout` and
`backup` are purely additive. Existing databases open unchanged. The
`SQLiteDatabase(path)` call sites keep working (new arg is keyword-only with a
default). Fully backward compatible.

## Commands executed and exit statuses

1. `python -m pytest tests/memory/test_storage_migrations.py -q` — exit 0 after
   one fix (PK test needed a parent `memory_items` row before the FK side-table
   insert); final 15 passed.
2. `python -m pytest tests/memory tests/cli/test_memory_command.py
   tests/agents/test_agent_memory_integration.py` — exit 0, **61 passed**.
3. `git status --porcelain` / `git diff --stat` — confirmed storage-only change.

## Tests passed / failed / skipped / not run

- Passed: 61 (46 prior baseline + 15 new Phase 2 storage/migration tests).
- Failed: 0. Skipped: 0.
- Not run: full-repo regression (out of scope; tree mid-edit by Trading agent).
  The ~22 documented environmental full-suite failures were not re-exercised and
  are not claimed as passing.

## Baseline failures and evidence

None in scope. One pre-existing non-failing `datetime.utcnow()` DeprecationWarning
(unchanged). The new tests surface the same warning via a `monkeypatch`'d
migration string — cosmetic, not a failure.

## Required acceptance evidence (phase-mandated matrix)

- Fresh installation → `test_fresh_install_creates_latest_schema`,
  `test_fresh_install_sets_pragmas`.
- Upgrade from older schema → `test_upgrade_from_empty_schema_applies_all_migrations`,
  `test_upgrade_is_incremental`.
- Transaction rollback → `test_execute_script_rolls_back_atomically`,
  `test_failed_migration_rolls_back`.
- Constraints / FK cascade → `test_hard_delete_cascades_side_tables`,
  `test_primary_key_constraint_enforced`.
- Repeated migration invocation → `test_repeated_connect_does_not_remigrate`,
  `test_connect_idempotent_in_process`.
- Concurrent access → `test_concurrent_writers_two_connections` (two connections,
  30 writes, no lock error, all persisted).
- Close/reopen + restart persistence → `test_records_persist_across_close_reopen`.
- Records survive migration without loss → `test_representative_records_survive_remigration`.
- Backup/recovery → `test_backup_then_recover`, `test_backup_rejects_memory_destination`.
- Never touched a real user database: every test uses `tmp_path` or `:memory:`.

## Security and operational concerns

- No regression to the scope/provenance/soft-delete invariants.
- `backup()` copies the whole DB including any sensitive rows — the redaction
  layer gap (finding #1) still applies to exports/backups and is unchanged.
- Hard delete remains the only irreversible path; documented in `docs/memory.md`.

## Remaining work

Findings #1–#7 (architecture §6) minus the now-closed busy_timeout/backup items.
Still open: authorization/redaction, projection rebuild/repair, graph
soft-delete-leak, embedding-identity guard, real embedding provider, WriteResult/
health, retention policy.

## Exact next-phase handoff

No forced sequence. Highest-value next phases (user to choose): projection
consistency/rebuild (the earlier plan in `phase-2-migration-plan.md`, now better
named "projections phase") or the authorization/redaction layer (finding #1).
Storage foundation is now complete, bounded, backed-up, and migration-proven.

PHASE 02 — DONE
