# PHASE 08 — EXPLAINABLE HYBRID RETRIEVAL

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–7 and separate
  Trading-owned changes (per the concurrent-agent audit). No worktrees in use.
- Concurrent-agent classification of files I touched: all **Memory-owned**
  (`src/aetheros/memory/**`, `tests/memory/**`, `docs/memory*`). No
  Trading/Agent/Planner/Desktop/Vision/Core file touched. No shared file touched.

## Scope

Harden the recall/ranking path into the Phase-8 contract: bounded structured
filtering + real vector candidates + graph expansion + dedup + ranking + final
budgeted context selection, with uniform constraint filtering across sources,
provenance + component-score explanations, honest degradation, and enforced
`max_memories / max_tokens / max_chars / max_per_type / max_age / min_confidence`.

## Existing implementation reused

- `MemoryRepository.candidates` (SQL hard-filter candidate pool) — unchanged.
- `VectorIndex.search(candidate_ids=...)` real cosine path — unchanged.
- `KnowledgeGraph.find_related_entities` + `repo.linked_ids` graph expansion —
  reused; the entity probe now inherits the query's hard filters.
- `MemoryScorer` eight-signal blend — reused; the retriever now sets
  `explanation.sources` on the returned explanation (no scoring change).
- Existing event (`MemoryRetrieved`), config object, and in-memory SQLite test
  fixtures reused as-is.

## Changes implemented

- **Filter isolation**: new `MemoryRetriever._passes` applies status/scope,
  type, veracity, context, tag, `min_confidence`, and `max_age_days` uniformly
  to every candidate *after* expansion. Entity-expansion probe now carries the
  query's type/veracity/tag/context/confidence/archived filters instead of
  resetting to entities-only. Link expansion no longer silently includes rows
  past the deletion check — the uniform predicate decides.
- **Budget**: `MemoryQuery` gains `max_tokens`, `max_chars`, `max_per_type`,
  `max_age_days` (default 0 == unbounded; validated in `__post_init__`).
  `_apply_budget` performs whole-memory, top-ranked selection honouring every
  bound. `estimate_tokens` is a conservative (over-estimating) heuristic.
- **Provenance + report**: `RetrievalExplanation.sources` added; new
  `RetrievalReport` value object (results + degradation + drop counters +
  `token_count_exact`). `_dedup` merges provenance across duplicates.
- **Safe degradation**: vector/graph source failures caught, recorded in
  `degraded_sources`, recall continues on remaining sources.
- **Manager**: `retrieve(...)` keeps return type, gains four budget kwargs;
  new `retrieve_report(...)` returns the full `RetrievalReport`.

## Files added

- `tests/memory/test_hybrid_retrieval.py` (16 tests + 1 opt-in real-provider test).
- `docs/memory/phase-reports/phase-08.md` (this report).

## Files modified

- `src/aetheros/memory/domain/query.py` — budget fields on `MemoryQuery`;
  `sources` on `RetrievalExplanation`; new `RetrievalReport`.
- `src/aetheros/memory/domain/__init__.py` — export `RetrievalReport`.
- `src/aetheros/memory/services/retriever.py` — rewritten pipeline (filter
  isolation, budget, provenance, degradation, `estimate_tokens`).
- `src/aetheros/memory/services/manager.py` — budget kwargs + `retrieve_report`.
- `docs/memory.md`, `docs/memory/implementation-state.md` — documentation.

## Shared files touched and justification

None. All changes are Memory-owned.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–7) and Trading changes present in the
tree at phase start; none in the files I edited beyond my own work.

## Migrations and compatibility impact

No schema migration. All new `MemoryQuery` / `RetrievalExplanation` fields are
additive with defaults preserving prior behaviour (`retrieve` return type
unchanged; budgets default to unbounded). `MemoryRetriever.retrieve` preserved
as a thin wrapper over `retrieve_report`.

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_hybrid_retrieval.py -o addopts="" -q` → exit 0.
- `python -m pytest tests/memory -o addopts="" -q` → exit 0.
- `ruff check <5 touched files>` → `All checks passed!` (after `--fix` on import
  ordering / one unused import, applied to my files only).
- `python -m mypy src/aetheros/memory/services/retriever.py` → `No module named
  mypy` (type checker unavailable in this environment, as in prior phases).

## Tests passed / failed / skipped / not run

- New file: **16 passed, 1 skipped** (opt-in `real_embeddings`).
- Full memory suite: **159 passed, 4 skipped**, 0 failed. (Baseline before this
  phase was 143 passed, 3 skipped; delta = +16 new tests, +1 new skip.)
- Not run: suites outside `tests/memory` (out of scope; no shared/Core file
  touched).

## Baseline failures and evidence

None in scope. The memory suite was green before (143 passed / 3 skipped,
recorded in prior-phase handoff) and is green after.

## Required acceptance evidence

Contract-mandated test areas, all covered in `test_hybrid_retrieval.py`:
SQL+vector+graph combination & provenance; ranking order; dedup; budget bounds
(limit / max_per_type / max_chars / max_tokens); filter isolation (type +
confidence); max_age cutoff; empty results; partial-source failure (vector +
graph) degrading safely. The real-semantic-retrieval integration path is
written as an opt-in test; **real-provider evidence is pending** (requires a
reachable Ollama daemon) — see Remaining work.

## Security and operational concerns

- Query-supplied scope/context/validity/age/confidence constraints are now
  enforced uniformly, closing the graph/link bypass. A full *authorization*
  boundary (caller identity/permissions), sensitive-field redaction on the
  retrieval/export path, and soft-deleted/historical no-leak across cache/export
  remain owed (Finding #1, next phase).
- Degradation is explicit and non-raising; a failed optional source lowers
  recall quality visibly rather than silently.
- Token budget is conservative and self-disclosed (`token_count_exact=False`).

## Remaining work

- Run the opt-in real-provider integration test against a live Ollama daemon to
  satisfy the semantic-retrieval integration acceptance with real embeddings.
- Authorization/redaction/export no-leak layer (Finding #1).

## Exact next-phase handoff

Recorded in `docs/memory/implementation-state.md` (Phase 8 handoff section):
new identifiers, test commands, pending real-provider evidence, and the
remaining security layer. Re-read the contract, that file, this report, and the
live retriever/manager source before the next phase.

PHASE 08 — DONE
