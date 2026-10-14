# Phase 2 Migration Plan — Projection Consistency, Recovery & Rebuild

> Concrete, bounded plan for the next phase. Produced in Phase 1; **not
> implemented here.** Phase 2 must re-read `agent-contract.md`,
> `implementation-state.md`, the Phase 1 docs, and the live source before coding,
> and revalidate git/concurrent-agent state.

## Why this is Phase 2 (selection rationale)

The Phase 1 audit found the Memory core sound, but the single invariant with the
weakest implementation is **projection consistency / recovery / rebuild**
(architecture §4.6). The contract is explicit: "Vector and graph projections must
have explicit consistency, recovery, and rebuild behavior." Today:
- Writes are ordered (row → vector → graph → event) with **no transaction**
  spanning the stores, so a crash between steps can leave the vector index or
  graph missing an entry that the authoritative `memory_items` table has.
- There is **no path** to rebuild the vector index or graph from the
  authoritative store, nor to detect drift.
- Graph expansion does not re-check `status`, a potential soft-delete leak.

This is foundational for every later phase (a real embedding provider in
particular requires a reindex/rebuild path), so it is sequenced first. The
authorization/redaction gap (architecture §6.1) is higher-severity but larger; it
is proposed as Phase 3 so Phase 2 stays a small, self-contained correctness fix.

## Scope (Phase 2, intentionally small)

Memory-owned files only. Additive — no public signature changes.

1. **Drift detection** — a read-only reconcile report:
   `MemoryManager.projection_report() -> dict` comparing authoritative row count
   (non-deleted) vs `VectorIndex.count()` and vs graph entity/edge counts, listing
   memory ids present in the store but missing from the vector index.
2. **Rebuild from authoritative store** — `MemoryManager.rebuild_projections(*,
   vectors=True, graph=True) -> dict` that re-embeds and re-indexes every
   non-deleted memory and re-reflects entities, reporting counts. Bounded batching
   via the existing `index_many`. Idempotent (`INSERT OR REPLACE`).
3. **Close the graph soft-delete leak** — `retriever` graph-expansion must drop
   neighbours whose `status='deleted'` (and respect `include_archived`), mirroring
   the candidate-pool filter already in `repository.candidates()`.
4. **Embedding-identity stamp on rebuild** — record the active `provider.name`
   and `dim`; `projection_report()` flags vectors whose stored `model`/`dim` differ
   from the active provider (prep for the real-provider phase; detection only, no
   enforcement yet).

Explicitly **out of scope** for Phase 2: real embedding providers, the
authorization/redaction layer, `WriteResult` type, background scheduler, retention
policy. Those remain later phases (architecture §6).

## Design constraints

- No new EventBus; reuse the shared one. Emit an existing-style event (e.g. a new
  `ProjectionRebuilt` on the shared `Event` base) only if cheap and additive.
- No distributed-transaction claim. Rebuild is a recovery operation, not atomicity.
- Deterministic and reproducible: rebuild from the same store yields the same
  index (hashing embedder is deterministic).
- Bounded: batch size from config; no unbounded traversal.

## Files (anticipated — re-confirm ownership at Phase 2 start)

- Modify (Memory-owned): `services/manager.py` (two methods),
  `services/retriever.py` (status filter on expansion), possibly `vector/index.py`
  (a `missing_ids` helper). All additive.
- Tests (Memory-owned): extend `tests/memory/test_memory_services.py` /
  `test_memory_storage.py` with: drift detected after a simulated partial write;
  rebuild restores vector count; soft-deleted memory never returned via graph
  expansion; identity mismatch flagged.
- Docs: update `docs/memory/architecture.md` §4.6 and `implementation-state.md`.

## Shared files

None expected. `bootstrapper.py` / `settings.py` should **not** need changes
(rebuild is a manager method, not new config). If a config knob proves necessary
(batch size), add it following the existing `AliasChoices` pattern with the
smallest compatible edit, after re-reading the live diff (the Trading agent is
mid-edit on both shared files).

## Acceptance criteria (Phase 2 "DONE")

- `projection_report()` returns accurate drift for a store with a deliberately
  missing vector; rebuild makes vector count equal the non-deleted row count.
- Soft-deleted memory provably cannot return via graph expansion (test).
- Identity mismatch is reported (not enforced).
- `tests/memory` + `tests/cli/test_memory_command.py` +
  `tests/agents/test_agent_memory_integration.py` all pass; no regression in the
  evidenced baseline (46 passing).
- Architecture doc and implementation-state updated to match the code.

## Risks

- Concurrent edits to shared files by the Trading agent (mitigation: Phase 2
  avoids them; re-read diffs first if forced).
- Rebuild cost on a large real DB (mitigation: batched, and run on explicit
  invocation, never automatically in Phase 2).
