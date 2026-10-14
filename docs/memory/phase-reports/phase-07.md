# PHASE 07 — KNOWLEDGE GRAPH: BOUNDED TRAVERSAL, REFERENTIAL INTEGRITY, JUSTIFIED INDEX

Status: DONE

## Starting revision and working-tree summary

- HEAD `b0a2537` ("Initialize memory system"), branch `development`.
- The working tree carries substantial **uncommitted prior-phase Memory work**
  (Phases 1–6): modified `config.py`, `embeddings/*`, `services/*`,
  `storage/*`, `vector/index.py`, and untracked `domain/content_policy.py`,
  `embeddings/ollama.py`, `services/results.py`, and several `tests/memory/*`.
  These predate this phase and were left untouched except where listed below.
- Pre-existing (not mine): all `src/aetheros/trading/**`, graphify artifacts
  under `graphify-out/`, run logs under `src/aetheros/logs/`.

## Scope

Phase 6 of the shared contract calls for a knowledge graph with entities,
relationships and traversal; that already exists and is real (persisted,
deduplicating entity/relationship store with directed, temporal, evidenced
edges and supersession). Following the contract's "extend, don't replace" rule,
this phase is a **hardening** of that real graph, targeting the operational
invariants the contract demands:

1. **Bounded traversal.** The previous traversal materialised the *entire*
   active edge set into an in-memory networkx graph on every call — unbounded in
   memory and latency as the graph grows. Replaced with a per-hop SQL
   breadth-first walk governed by explicit `TraversalBounds` (max hops, fan-out,
   result count, wall-clock time), cycle-safe, that never loads the whole graph.
2. **Referential integrity.** `add_relationship` now rejects an edge whose
   source or target entity does not exist, so traversal can never dangle.
3. **Justified index (schema v2).** Partial indexes on the active edge set so a
   hop is an index SEARCH on live edges, not a scan that also reads superseded
   history. Index selection verified by EXPLAIN QUERY PLAN.

Out of scope (unchanged, still owed): the cross-cutting authorization /
scope-filtering / soft-delete-no-leak layer (contract Finding #1); graph-side
projection rebuild/repair.

## Existing implementation reused

- `Entity` / `Relationship` domain value objects (`domain/semantic.py`) — unchanged.
- `KnowledgeGraph` entity upsert/dedup, `add_relationship` reinforce-not-duplicate,
  `supersede_relationship`, `find_relationships`, `neighbors`, `stats` — unchanged
  except the invalid-reference guard added inside `add_relationship`.
- The migration framework (`storage/schema.py` `MIGRATIONS`, `database.py`
  incremental runner) — a new version 2 entry was appended; the runner was not
  modified.
- `MemoryValidationError` (`core/errors/memory_error.py`) for the integrity guard.
- `_clock` helpers; `services/writer.py::_reflect_entities` already upserts both
  endpoints before relating them, so the new guard is satisfied on the write path.

## Changes implemented

- `graph/store.py`:
  - New `TraversalBounds` frozen dataclass (max_hops=2, max_fanout=64,
    max_results=256, time_limit_s=1.0 defaults; validated in `__post_init__`;
    `with_hops` back-compat shim).
  - `add_relationship` invalid-reference guard: both endpoints must exist in
    `entities` or `MemoryValidationError` is raised (checked in the write thread).
  - Removed `_active_graph` (whole-graph networkx materialisation) and the
    `networkx` import. Added `_active_neighbor_ids_sync` (one hop, both
    directions, active edges only, optional relation filter) and
    `_bounded_bfs_sync` (cycle-safe BFS honouring every bound, early-exit on goal).
  - `find_related_entities` and `find_path` rewritten on the bounded BFS. Both
    keep their existing signatures and gain optional `relation` and `bounds`
    parameters; `find_path` returns `[]` when the target is unreachable within
    the bounds (previously it scanned the whole graph).
- `graph/__init__.py`: export `TraversalBounds`.
- `storage/schema.py`: migration version 2 — partial indexes
  `ix_rel_active_source` / `ix_rel_active_target` on `relationships(source_id|target_id) WHERE valid_to IS NULL`.
- `docs/memory.md`: updated the Graph layer description and the architecture
  diagram (networkx → bounded SQL BFS).

## Files added

- `tests/memory/test_knowledge_graph.py` — 18 tests.

## Files modified

- `src/aetheros/memory/graph/store.py` (Memory-owned)
- `src/aetheros/memory/graph/__init__.py` (Memory-owned)
- `src/aetheros/memory/storage/schema.py` (Memory-owned)
- `docs/memory.md` (Memory-owned)
- `tests/memory/test_storage_migrations.py` (Memory-owned; test-fidelity fix)

## Shared files touched and justification

None outside the Memory subsystem. `storage/schema.py` is Memory-owned; the
change is purely additive (a new, higher migration version — the existing
version-1 DDL is untouched, so already-migrated databases are unaffected).

## Concurrent changes observed

Prior-phase uncommitted Memory work (Phases 1–6) was present throughout and
left untouched. No overlap with my files beyond the schema migration list,
which I only appended to. Trading, graphify and log artifacts untouched.

## Migrations and compatibility impact

- New schema version 2: two partial indexes. Idempotent (`CREATE INDEX IF NOT
  EXISTS`), additive, no data rewrite, no column change. A v1 database upgrades
  to v2 on next connect; a fresh database arrives at v2 directly.
- `test_storage_migrations.py::test_upgrade_is_incremental` simulated a "v1" DB
  by creating only `memory_items`. A faithful v1 DB also has the `relationships`
  table (created by migration 1), which migration 2 indexes. The test now
  creates `relationships` too, so the simulated baseline matches a real v1 DB.
  This is a test-fidelity correction, not a loosening of the assertion.
- Public API: `find_related_entities` / `find_path` signatures are unchanged for
  existing callers (new params are optional, keyword-only). `add_relationship`
  now raises `MemoryValidationError` on a dangling endpoint; the only internal
  caller (`writer._reflect_entities`) upserts endpoints first, so no behaviour
  change there.

## Commands executed and exit statuses

- `python -m pytest tests/memory/test_knowledge_graph.py -o addopts=""` → exit 0
  — 18 passed.
- `python -m pytest tests/memory -o addopts=""` → exit 0 — 143 passed, 3 skipped.
- `ruff check tests/memory/test_knowledge_graph.py` → exit 0 — All checks passed.
- `ruff check src/aetheros/memory/graph/store.py` → 2 findings, both pre-existing
  (see Baseline failures).
- EXPLAIN QUERY PLAN harness (seeded + ANALYZE) on the exact per-hop queries →
  `SEARCH relationships USING INDEX ix_rel_active_source (source_id=?)` and
  `... ix_rel_active_target (target_id=?)`.
- `mypy` is not installed in this environment (`No module named mypy`); type
  check not run.

## Tests passed / failed / skipped / not run

- Passed: 143 (18 new graph tests + 125 prior memory tests).
- Failed: 0.
- Skipped: 3 (pre-existing opt-in real-provider tests; unchanged, not run here).
- Not run: `mypy` (tool unavailable); non-memory suites (out of scope).

## Baseline failures and evidence

- The 2 `ruff` findings in `graph/store.py` (`I001` import sort; `F401`
  `_clock.utcnow` imported-but-unused) are **pre-existing**: `git show
  HEAD:src/aetheros/memory/graph/store.py` through `ruff` reports both before any
  of my edits. Not introduced here; left untouched to avoid unrelated churn.
- Full non-memory regression suite not claimed; only the memory suite was run.

## Required acceptance evidence

- Real persisted graph (no mocks): all 18 tests run against on-disk/`:memory:`
  `SQLiteDatabase` rows. `test_entity_persists_across_reopen` and
  `test_separate_databases_are_isolated` prove real persistence and store isolation.
- Bounded traversal: `test_max_hops_bounds_reachability`,
  `test_find_path_respects_hop_bound`, `test_max_results_bound`,
  `test_max_fanout_bound`, `test_time_limit_stops_traversal`,
  `test_cycle_is_handled` (termination on a 3-node cycle).
- Temporal correctness: `test_supersede_closes_temporal_validity`,
  `test_superseded_edge_excluded_from_traversal` (closed edges never surface in
  recall/paths; history retained).
- Referential integrity: `test_relationship_invalid_reference_rejected`.
- Dedup/direction: `test_duplicate_edge_reinforces_not_duplicates`,
  `test_edge_direction_is_respected`.
- Index justification: EXPLAIN QUERY PLAN output above shows the partial
  active-edge indexes are selected for the exact per-hop queries.

## Security and operational concerns

- Superseded (soft-closed) edges are filtered at **every** hop (`valid_to IS
  NULL` in each neighbour query), so historical/contradicted edges do not leak
  through graph expansion — consistent with the contract's no-leak invariant.
- Still owed (unchanged): memory-level authorization/scope filtering and
  soft-deleted-memory no-leak across the broader retrieval/cache/export surface
  (contract Finding #1). This phase did not alter that boundary.
- Traversal is now bounded in time and size, removing a latency/memory DoS
  surface present in the whole-graph materialisation.

## Remaining work

- Contract Finding #1: cross-cutting authorization / scope filtering /
  soft-delete no-leak across retrieval, cache, embedding, graph expansion, export.
- Graph-side projection rebuild/repair (counterpart to Phase 6's vector repair).
- `mypy` type check once the tool is available in the environment.

## Exact next-phase handoff

Phase 7 (knowledge-graph hardening) is DONE. Entity/relationship store is real
and persisted; traversal is bounded (`TraversalBounds`) and cycle-safe; edges
are referentially guarded; schema is at version 2 with EXPLAIN-verified partial
active-edge indexes. networkx is no longer used by the memory subsystem (the
dependency declaration was intentionally left in place — removing it is out of
scope and could affect other code).

When the next phase is authorized: re-read `agent-contract.md`,
`implementation-state.md`, this report and the live source for the targeted
modules; re-run the concurrent-agent audit (git status/diff); then follow the
Phase Execution Protocol.

PHASE 07 — DONE
