# PHASE 06 — REAL VECTOR INDEX: HARDENING, DELETION-SAFETY, BATCH SEARCH

Status: DONE

## Starting revision and working-tree summary

- Baseline commit: `b0a2537` ("Initialize memory system").
- The working tree carries uncommitted Phase 1–5 Memory work plus substantial
  **concurrent Trading-agent** changes (`src/aetheros/trading/**`, trading
  `settings.py` knobs, `graphify-out/`, run logs). Nothing committed; Phase 6
  began on top of this live tree.
- Pre-existing (not mine): all `src/aetheros/trading/**`, graphify artifacts,
  run logs, the Phase 1–5 memory modules. Classified and left untouched except
  the two Memory-owned files below.

## Scope

Phase 6 of the shared contract calls for a "real vector index / vector store".
After auditing the existing implementation I determined the audited backend is
**already a real persistent vector store** (SQLite float32 BLOBs + exact numpy
cosine over L2-normalised vectors, keyed by memory id, identity-scoped by the
`model` column). Per the contract (replace only when the audited architecture
makes it necessary **and** the user approves a migration plan), Phase 6 is a
**hardening** of that real index — not a replacement. Scope:

1. Close the deletion/scope-leakage hole on the direct whole-index search path.
2. Guard stores against wrong-dimension / non-finite vectors (poisoned cosine).
3. Add batch search (contract lists "single/batch search").
4. Bound the whole-index scan and disclose truncation.
5. Comprehensive backend tests + an opt-in real-model relative-retrieval test.

### Backend decision (no new dependency)

Keeping the SQLite+numpy backend over FAISS/Chroma/pgvector is deliberate: the
production recall path (`MemoryRetriever`) always hands the index a SQL-bounded
`candidate_ids` pool, so an ANN engine's large-corpus advantage never applies,
while a native-wheel / server dependency would add real deployment burden. The
`memory_id`-scoped interface is preserved so a real ANN backend can slot in
later behind the same methods if a corpus ever outgrows the exact scan.

## Existing implementation reused

- `VectorIndex` store/update/delete/search/`index_many`/`ids`/`identities`
  (Phases 1 & 5) — extended, not rewritten.
- `EmbeddingProvider.validate_vector` static guard (Phase 5) — reused as the
  store-time dimension/finite check rather than duplicating the logic.
- `memory_embeddings` table + `memory_items.status` column (Phase 2) — the
  deletion-exclusion JOIN uses the existing schema. **No schema/migration change.**
- `HashingEmbeddingProvider` (Phase 1) as the deterministic backend-unit embedder.
- `MemoryWriter.verify_projection` / `repair_projection` (Phase 4) — exercised by
  the repair test; unchanged (they must still see orphan/soft-deleted vectors).
- The opt-in real-Ollama skip/marker pattern from `test_embedding_provider.py`.

## Changes implemented

- `VectorIndex.search` gains `exclude_deleted: bool = True`. On the whole-index
  path (`candidate_ids=None`) it now JOINs `memory_items` and filters
  `status != 'deleted'`, so a soft-deleted memory's vector cannot leak through
  recall. The `candidate_ids` path is unchanged (the retriever already
  status-filters that pool). `exclude_deleted=False` is available for admin/repair.
- `VectorIndex.search_many` — real batch search: loads the eligible matrix once
  and computes `M @ Qᵀ`, top-k per column, one result list per query in input order.
- `VectorIndex._store` now calls `EmbeddingProvider.validate_vector` before
  persisting (rejects wrong-dimension / empty / NaN/inf vectors). Falls back to the
  vector's own length when a lazy provider's `dimension` is not yet probed.
- Whole-index scan bounded by `max_scan` (default `DEFAULT_MAX_SCAN = 50_000`,
  constructor-injectable), ordered `created_at DESC`, with a logged warning when
  the cap truncates recall. The bounded `candidate_ids` path is unaffected.

## Files added

- `tests/memory/test_vector_index.py`
- `docs/memory/phase-reports/phase-06.md` (this file)

## Files modified

- `src/aetheros/memory/vector/index.py` (Memory-owned)
- `docs/memory/implementation-state.md`, `docs/memory.md` (docs)

## Shared files touched and justification

None. No change to `settings.py`, `pyproject.toml`, schema, or any Trading-owned
file. The `real_embeddings` marker reused from Phase 5 already exists in
`pyproject.toml`; no registration change was needed.

## Concurrent changes observed

The Trading agent's uncommitted edits across `src/aetheros/trading/**`,
`graphify-out/`, and run logs were present throughout and left untouched. No
overlap with `src/aetheros/memory/vector/index.py`.

## Migrations and compatibility impact

- No schema or migration change. No persisted-data format change — stored vectors
  are read back exactly as before.
- API compatibility: `search` gained a keyword-only argument with a safe default;
  all existing callers (retriever, manager) are unaffected. `search_many` is new.
- Behaviour change (intended, safety): the direct `search(candidate_ids=None)`
  path now excludes soft-deleted rows by default. The production recall path was
  already safe via its status-filtered pool, so end-to-end recall is unchanged;
  this closes the direct/admin-caller leak.

### Audit note — soft-delete already cascades the vector

`MemoryRepository.update` persists via `INSERT OR REPLACE` on `memory_items`;
because `memory_embeddings.memory_id` is `FK ... ON DELETE CASCADE`, a normal
soft-delete through `MemoryManager.forget(hard=False)` → `repo.update` already
removes the vector row. The new JOIN guard is defense-in-depth for any path that
sets `status='deleted'` without replacing the row (verified by driving that exact
state in the tests). This is behaviour of existing code, documented here, not
changed.

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_vector_index.py -o addopts=""` → exit 0 —
  17 passed, 1 skipped.
- `python -m pytest tests/memory -o addopts=""` → exit 0 — 125 passed, 3 skipped.
- `python -m ruff check tests/memory/test_vector_index.py` → exit 0 — All checks passed.
- `python -m ruff check src/aetheros/memory/vector/index.py` → 2 findings, both
  pre-existing (see baseline note).

## Tests passed / failed / skipped / not run

- Passed: 125 (memory suite), including 17 new Phase 6 backend tests.
- Failed: 0.
- Skipped: 3 — the opt-in real-provider tests (`real_embeddings`): 2 from Phase 5
  + 1 new (`test_real_vector_index_relative_retrieval`). Skipped, not passed:
  no live Ollama daemon was available in this environment.
- Not run: the rest of the repository suite (trading, core, etc.) — out of scope
  and concurrently mid-edit by the Trading agent.

## Baseline failures and evidence

The two `ruff` findings in `index.py` (`I001` import sort, `B905` zip-without-strict
at the pre-existing `index_many`) are **pre-existing**: `git show HEAD:...index.py`
reproduces the same `I001`, and the `B905` line is unchanged by this phase
(`git diff` shows no edit to it). Left untouched to keep the diff minimal.

## Required acceptance evidence

- Real persistence across reopen: `test_persistence_across_reopen` writes with one
  on-disk `SQLiteDatabase` connection, closes it, reopens a fresh connection on the
  same file, and retrieves the vector — real SQLite, real cosine.
- Real cosine semantics with a deterministic backend: insert/update/delete,
  candidate filtering, bounded top-k (descending scores), batch == single.
- Deletion no-leak: soft-deleted vector excluded from whole-index recall while
  physically present (`count() == 2`); `exclude_deleted=False` still sees it.
- Embedding-space isolation: two identities over one DB never cross-contaminate.
- Bad-vector rejection: wrong-dimension and NaN vectors raise before persistence.
- Projection repair: `verify_projection`/`repair_projection` reconcile a dropped
  vector.
- Opt-in real-model: `test_real_vector_index_relative_retrieval` (skipped here,
  no daemon) asserts *relative* ranking (on-topic > off-topic) against a real
  Ollama model — not brittle exact scores. **Real-provider acceptance for this
  assertion remains PENDING until run against a live daemon; the fixture-based
  tests do not substitute for it.**

## Security and operational concerns

- Deletion leakage closed on the direct path; cache/graph-expansion/export no-leak
  remains owed to the dedicated authorization/scope phase (unchanged from the
  Phase 5 handoff).
- Unbounded-scan risk bounded with disclosure; the production bounded path is the
  normal one.
- No secrets touched; no network calls on the default path.

## Remaining work

- Full authorization / scope-filtering / deletion-visibility / sensitive-exclusion
  across retrieval, **cache, graph expansion, and export** (still the top owed item).
- Graph-side projection rebuild/repair (counterpart to the vector repair).
- Auto-reembed-on-identity-change (manual `reembed_all()` exists).
- Run the opt-in real-vector integration test against a live Ollama daemon to
  satisfy the pending real-provider acceptance for Phase 6.

## Exact next-phase handoff

When the next phase is authorized: re-read `agent-contract.md`,
`implementation-state.md`, this report, and the live source for the targeted
modules; re-run the concurrent-agent audit (`git status` / `git diff`); then
follow the Phase Execution Protocol. The highest-priority owed item is the
authorization / scope-filtering / no-leak-across-cache-graph-export layer.

PHASE 06 — DONE
