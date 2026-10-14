# PHASE 12 — CONSOLIDATION AND CONTRADICTIONS

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–11 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/consolidator.py`,
    `.../services/manager.py`, `tests/memory/test_consolidation.py` (new),
    `docs/memory.md`, `docs/memory/*`.
  - **Shared (Core)**: none. No Trading/Agent/Planner/Desktop/Vision file
    modified.

## Scope

Exact deduplication, bounded near-duplicate detection, related-memory
linking, contradiction representation, supersession and justified archival —
with configurable criteria (type, entity, source, scope, content, time),
trading-history protection, reversible/auditable decisions, structured-only
contradiction (never similarity), and bounded restartable idempotent batches
on the existing scheduling infrastructure (the caller-invoked verb pattern,
like `decay()` — no memory-owned background scheduler exists, and inventing
one would violate the no-speculative-frameworks rule).

## Existing implementation reused

- `MemoryConsolidator` shape (group → survivor scan → fold + archive +
  `derived_from` link + `MemoryConsolidated` event) — hardened in place,
  not replaced.
- `manager.consolidate()` verb, `list_by(limit, offset)` paging,
  `linked_ids`/`add_link`, `MemoryStatus` transitions, `dedup_threshold`
  config — all reused. No new tables, events, buses, or config knobs.

## Changes implemented

- `services/consolidator.py` rewritten around a five-outcome `_decide`
  (merged / contradiction[+supersede] / related / separate):
  - Exact (byte-identical) copies merge for unprotected non-prediction rows
    with compatible entities; protected types, prediction veracity and
    disjoint entities → `related_to` link, stay separate.
  - Near-merge requires normalised equality + all guards (same type/scope
    group, unprotected, non-prediction, entity overlap when both name
    entities). Genuinely different claims link, never merge.
  - Contradiction: shared entity + negation morphology or divergent
    FACT/USER_INPUT → two-way `contradicts` link, both live. When the pair
    also qualifies for supersession (strictly newer, divergent), the older
    archives with a `supersedes` link too (both counted).
  - Supersession gate: FACT/USER_INPUT only, same entity, strictly newer,
    divergent, unprotected, non-PERMANENT. OBSERVATION series never
    supersede; equal timestamps stay separate.
  - Survivor fold accumulates evidence_count, confidence, `merged_from`
    provenance and the entity union; archived rows carry reason + back-
    pointer metadata. `_link_pair` skips existing same-type links
    (idempotent re-runs). Archived rows leave the survivor pool (live-only
    rejoin guard).
  - `consolidate(batch_size=500, max_batches=0)` pages `list_by`, skips
    archived/expired/deleted rows, honours `enabled` + `consolidation_-
    enabled`, and reports merged/archived/promoted/contradictions/
    superseded/related/skipped_protected/batches.
- `services/manager.py`: `consolidate()` forwards batch kwargs (additive;
  defaults preserve the old call shape).

## Files added

- `tests/memory/test_consolidation.py` (16 tests).
- `docs/memory/phase-reports/phase-12.md` (this report).

## Files modified

- `src/aetheros/memory/services/consolidator.py`
- `src/aetheros/memory/services/manager.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–11) and Trading changes present at
phase start; none within the regions I edited.

## Migrations and compatibility impact

No schema migration. `consolidate()` return shape is a superset (new count
keys added; old keys unchanged). Default call `consolidate()` behaves as
before for exact duplicates (the one pre-existing test still passes
unmodified). No public API removed.

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (219 passed, 4 skipped).
- `python -m pytest tests/memory/test_consolidation.py -o addopts="" -q`
  (first run) → 8 passed, **8 failed** (design flaws, see below).
- After restructure → 13 passed, 3 failed; after veracity-gated redesign →
  syntax error (sync/async) caught immediately; after fix → exit 0
  (**16 passed**).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**235 passed,
  4 skipped**: prior 219 + 16 new, 0 failed).
- `ruff check` on touched files → 2 findings, auto-fixed, re-check clean,
  suite re-run green.
- `mypy`: unavailable in env, same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **16 passed**, 0 failed, 0 skipped.
- Full memory suite: **235 passed, 4 skipped**, 0 failed. (Before this phase:
  219 passed / 4 skipped; delta = +16 new tests.)
- Not run: suites outside `tests/memory` (out of scope; one additive
  manager kwarg touched, exercised via the suite).
- Failure-driven redesign (the suite caught real design flaws before merge):
  1. Supersession fired on OBSERVATION pairs, archiving legitimate series
     points (redesigned: FACT/USER_INPUT only, inside contradiction only).
  2. `_decide` (sync) awaited links (SyntaxError; split decision vs actions).
  3. Superseded candidates rejoined the survivor pool (live-only rejoin).
  4. `manager.consolidate()` dropped batch kwargs (passthrough added).
  5. Consolidation ignored the `enabled` master switch (gate added).
  6. `manager._config` post-construction replace doesn't propagate (test
     rebuilt with a fresh manager instead).

## Baseline failures and evidence

None pre-existing. All Phase 12 failures were caused by this phase's own new
code/tests and fixed in-phase (evidence above). One transient
`FileExistsError` from two concurrent pytest invocations racing the log-dir
creation (environment flake, unrelated to code; single runs unaffected).

## Required acceptance evidence

Contract-mandated areas, all in `test_consolidation.py`:
- Duplicate handling: `test_exact_duplicates_merge_with_evidence`,
  `test_consolidation_is_idempotent`.
- Legitimate repeated observations: `test_repeated_observations_never_merge`.
- Temporal facts: `test_newer_assertion_supersedes_older_with_contradiction_link`,
  `test_equal_timestamps_stay_separate`.
- Contradictory sources: `test_contradictory_sources_link_and_supersede`,
  `test_low_similarity_is_never_contradiction`.
- Preservation of original evidence:
  `test_exact_duplicates_merge_with_evidence` (archived row intact + link).
- Interrupted jobs: `test_interrupted_job_resumes_idempotently`,
  `test_bounded_batches_cover_all_rows`.
- Scope isolation: `test_scope_isolation_no_cross_scope_merge`.
- Trading-history protection: `test_predictions_never_merge`,
  `test_episodes_and_failures_never_near_merge`,
  `test_distinct_entities_never_merge_on_prose`.
- Ambiguity: `test_ambiguous_candidates_stay_separate`.
- Disabled: `test_disabled_consolidation_is_noop`,
  `test_consolidation_flag_off_is_noop`.

## Security and operational concerns

- No secret handling in consolidation (it moves rows/links, never ingests
  free text) — write-path redaction upstream is untouched.
- Archived ≠ deleted: every decision preserves the original row + a typed
  link, so reversal is always "follow the link back".
- Bounded batches + page cap + idempotent links: a consolidation pass can be
  safely re-run after interruption without double-merging or double-linking.
- Contradiction links surface disagreement to retrieval expansion (existing
  `_expand_via_links` picks them up with provenance) without asserting a
  winner.

## Remaining work

- Carried forward: Finding #1 (authz/redaction/export no-leak layer);
  UP017 style; `datetime.utcnow()` cosmetic.
- The `skipped_protected` counter is reported but currently always 0
  (protected rows flow to `related`/`separate`, which have their own
  counters) — kept for future fine-grained reporting, not removed to avoid
  breaking the report shape.

## Exact next-phase handoff

Phase 12 is **DONE** (suite green: 16 new tests, full memory suite 235
passed / 4 skipped). Re-read the contract, `implementation-state.md`
(§Phase 12 handoff), this report, and the live `consolidator.py` /
`manager.py` source before the next phase. Key identifiers:
`MemoryConsolidator.consolidate(batch_size, max_batches)`,
`contradicts` / `supersedes` / `related_to` link types, `_PROTECTED_TYPES`.

PHASE 12 — DONE
