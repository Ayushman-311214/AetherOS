# PHASE 17 — KNOWLEDGE AND DOCUMENT INGESTION

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree: Memory phases 1–16 uncommitted + an uncommitted Trading
  working tree from the other agent (re-verified present, untouched). No
  worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/domain/document.py` (new),
    `src/aetheros/memory/services/ingestion.py` (new),
    `.../domain/__init__.py`, `.../services/manager.py`,
    `.../services/__init__.py`, `tests/memory/test_ingestion.py` (new),
    `docs/memory.md`, `docs/memory/*`.
  - **Trading-owned**: NONE touched.
  - **Shared**: none.

## Scope

Memory-facing ingestion for supported documents, notes, research,
concepts and structured knowledge using existing parsers — bounded
chunking, content limits, idempotency, redaction before embedding,
resumable indexing — with defined update/remove/correct/partial
semantics, no orphaned chunks or stale projections, untrusted-evidence
treatment, no invented formats, no remote fetching.

## Existing implementation reused

- Audited first: **no document parsers or ingestion code exist** in the
  repo (`grep` for ingest/parser/chunk across `src/` finds only this
  phase's new files); `pyproject.toml` carries no PDF/DOCX/HTML/Markdown
  libraries. Supported formats are therefore stdlib-only by evidence,
  not by choice: txt/md/json/jsonl/csv.
- `store` (idempotency keys + five-state `WriteResult`), `update`
  (version-guarded), `get`, `link`, `find_by_metadata`, `repo.update_guarded`,
  `_vectors.delete`, write-path validator (redact-by-default), `MemoryStored`
  announcements — reused. No new bus, events, tables, migrations, knobs,
  or scheduler.
- Lifecycle's `_transition_one` pattern (guard + bump + logged skip) is
  the template for `_archive_row`; lifecycle's `_propagate` documents why
  vectors drop inline on archive.

## Changes implemented

- `domain/document.py` (new): `checksum_text` (sha256 identity),
  `SUPPORTED_FORMATS`, `DocumentSource` (source registry row:
  source_id/origin/format/version=checksum/chunk_ids/chunks_total/
  cursor/status/scope/ingested_at, `docsrc:{id}:{version}` id) and
  `DocumentChunk` (deterministic `doc:{source}:{version}:{index}` id;
  SEMANTIC/UNVERIFIED/DOCUMENT-source rows with source/version/ref
  citation metadata; docstring states the untrusted-evidence treatment).
- `services/ingestion.py` (new `DocumentIngestion`,
  `manager.documents`): `ingest_text` (format dispatch: prose/Markdown
  section splitter, per-record JSON, per-line JSONL, per-row CSV;
  per-unit + per-source bounds, all rejected-never-truncated);
  `ingest_file` (one explicit local path, byte cap, UTF-8, URL-shaped
  input refused); same-checksum fast path returns the stored source;
  new-checksum `_supersede_previous` (guarded archive + inline vector
  drop + best-effort `derived_from` link, old registry rows kept as
  audit trail); cursor-advanced `_index` that **never claims progress
  for an unpersisted chunk** (STORED advances, idempotent SKIPPED
  replays, FAILED raises `MemoryStorageError`, UNAVAILABLE/policy
  SKIPPED stops with the partial row recording the cursor);
  `_write_source_row` (store-then-guarded-update); `get_source` /
  `source_chunks` / `remove_source` (counts receipt); `_ensure_enabled`
  gate on ingest/remove (the archive paths write through the repo
  directly, so a disabled-mode ingest must not archive the old version
  while persisting nothing — the one honest gap the chunk loop alone
  could not close); `verify_ingestion_contract` ledger.
- `services/manager.py` + `services/__init__.py` + `domain/__init__.py`:
  construct, accessor, exports (additive).
- `docs/memory.md`: new "Document & knowledge ingestion" section;
  Testing + Deferred sections updated (Phase 17 no longer deferred).

## Files added

- `src/aetheros/memory/domain/document.py`.
- `src/aetheros/memory/services/ingestion.py`.
- `tests/memory/test_ingestion.py` (18 tests).
- `docs/memory/phase-reports/phase-17.md` (this report).

## Files modified

- `src/aetheros/memory/domain/__init__.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None (deliberately — no shared seam needed a change).

## Concurrent changes observed

Uncommitted Trading working tree still present at phase start and
re-verified before writing; no Memory-owned region touched by the other
agent. The adapter takes no trading dependency, so their edits cannot
break this phase.

## Migrations and compatibility impact

No schema migration (sources + chunks ride `memory_items`/`memory_links`
+ the existing `source_id` indexed metadata column). No public API
removed. New ids (`doc:*`, `docsrc:*`) are namespaced and cannot collide
with existing rows.

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_ingestion.py -o addopts="" -q`
  (first run) → 8 passed, **1 failed** (my test's off-by-one: the source-row
  store consumes a call, so the injected failure hit at cursor 1, not 2).
- After fix → 16 passed, **2 failed** (both mine: CSV `"a,b\n1"` parses fine
  as one row — kept the genuinely-empty `"a,b\n"` case; and a sync vector
  internal poked through `await` — replaced with persistence-level proof).
- After fix → exit 0 (**18 passed**).
- `python -m pytest tests/memory tests/cli/test_memory_command.py -o
  addopts="" -q` → exit 0 (**327 passed, 4 skipped**: prior 309 + 18 new).
- `ruff check` on touched files → auto-fixed import sort + 2 F841; I fixed
  the remaining 2 F841 + 2 B017 (now assert `MemoryStorageError`) by hand;
  final: only the repo-wide pre-existing UP017 (`timezone.utc`, evidenced
  at HEAD via stash in `domain/episode.py`, untouched everywhere) remains.
- `ruff format` → my files clean; `manager.py` drift is at lines 148/315,
  regions I did not touch (pre-existing).
- `mypy`: unavailable in env, same as prior phases.
- `graphify update .` → run after the code settled (see below).

## Tests passed / failed / skipped / not run

- New file: **18 passed**, 0 failed, 0 skipped.
- Memory + CLI suite: **327 passed, 4 skipped**, 0 failed. (Before this
  phase: 309 passed / 4 skipped; delta = +18 new tests.)
- Not run: `tests/trading/*` (Trading-owned, other agent's tree in flux —
  deliberately untouched and unexecuted).

## Baseline failures and evidence

None pre-existing. All three first-run failures were this phase's own
test bugs (off-by-one store-call count, a valid-CSV negative case, a
sync-internal probe), fixed in-phase — the implementation was never at
fault after the initial smoke test.

## Required acceptance evidence

Contract-mandated areas, all in `test_ingestion.py`:
- Supported formats: `test_txt_ingest_chunks_and_cites`,
  `test_md_ingest_keeps_section_refs`,
  `test_json_ingest_one_chunk_per_key`,
  `test_jsonl_ingest_one_chunk_per_line`,
  `test_csv_ingest_one_chunk_per_row`, `test_file_ingest_round_trip`.
- Source citation fidelity: every format test asserts
  source_id/version/ref metadata; txt test asserts checksum identity.
- Repeated ingestion: `test_reingest_same_bytes_is_noop` (one row, same ids).
- Updates: `test_update_supersedes_old_chunks` (archived + reason +
  `superseded_by` + `derived_from` link + old text leaves recall + latest
  pointer moves).
- Partial failures: `test_partial_ingest_reports_cursor` (FAILED raises,
  partial row reports the exact cursor, retry completes all 6).
- Restart: `test_restart_resumes_from_cursor` (file DB + fresh manager).
- Malicious instruction text: `test_malicious_instruction_text_is_inert_data`
  (verbatim UNVERIFIED SEMANTIC row, no privilege).
- Sensitive-data exclusion: `test_secrets_redacted_before_persistence`
  (credential absent from every row of the source + `redacted_secret_kinds`
  labelled; redaction precedes indexing on the write path).
- Deleted-source visibility: `test_remove_source_leaves_recall_stays_auditable`
  (receipt counts, no `doc:t13:*` in recall, direct reads archived).
- Unsupported: `test_unsupported_format_rejected` (pdf/docx/html/xlsx),
  `test_remote_ingest_rejected`, `test_oversize_file_rejected`,
  `test_malformed_json_rejected`, `test_contract_ledger_is_honest`.

## Security and operational concerns

- Chunk rows are UNVERIFIED veracity, never FACT — imported prose cannot
  be mistaken for ground truth by the epistemic validator.
- Secrets are redacted by the write-path validator before SQLite *and*
  before the embedder sees the text; the label travels in metadata.
- Disabled-mode ingest/remove refuse outright (no half-archive).
- `ingest_file` resolves one explicit local path: no URLs, globs, or
  directory walks; `..` traversal writes nothing outside the read (only
  reads the named file).
- Consolidation interplay: chunks carry no entities and UNVERIFIED (not
  PREDICTION) veracity, so byte-identical re-ingests stay idempotent
  while distinct sources merge only under the ordinary normalised-equality
  guards — cross-version duplicates cannot arise because old versions
  archive on supersede. (No new test pins this; the guards are Phase 12's.)
- Observed: the source registry row (`docsrc:*`) is ACTIVE and therefore
  surfaces in retrieval alongside chunks — acceptable (it's source
  metadata, not a leak), noted for the Phase 22 coverage pass.

## Remaining work

- Carried forward: Finding #1 (deeper retrieval/cache/embedding/graph/
  export no-leak pass); Phase 22 automatic coverage (include a document
  source in the lifecycle sweep: neglected chunks follow the ordinary
  STALE→ARCHIVED chain today, unpinned by any test); procedure evolution
  consuming failure evidence; live trading-consumer verification with the
  Trading agent; UP017/UP042/`datetime.utcnow()`/B905/F841 cosmetics.
- Optional: `ingest_file` directory-batch mode is deliberately absent
  (one explicit path per call keeps the bound auditable).

## Exact next-phase handoff

Phase 17 is **DONE** (suite green: 18 new tests, memory + CLI suite 327
passed / 4 skipped; Trading tree untouched). Re-read the contract,
`implementation-state.md` (§Phase 17 handoff), this report, the live
`ingestion.py` / `document.py` source before the next phase. Key
identifiers: `DocumentIngestion`, `manager.documents`, `DocumentSource` /
`DocumentChunk`, `checksum_text`, `SUPPORTED_FORMATS`,
`verify_ingestion_contract`, `doc:{source}:{version}:{index}` /
`docsrc:{source}:{version}` ids.

PHASE 17 — DONE
