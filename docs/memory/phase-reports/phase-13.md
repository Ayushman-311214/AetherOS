# PHASE 13 — CONFIDENCE AND EVIDENCE UPDATES

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–12 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/confidence.py` (new),
    `.../services/manager.py`, `.../services/__init__.py`,
    `tests/memory/test_confidence.py` (new), `docs/memory.md`,
    `docs/memory/*`.
  - **Shared (Core)**: none. No Trading/Agent/Planner/Desktop/Vision file
    modified.

## Scope

Documented confidence updates from source reliability, independent
confirmation, user correction/confirmation, verified reuse, contradictions
and observed outcomes — with bounded scores, deterministic rules, evidence
history, duplicate-aware independence, forecast/history refusals, freshness
without double-penalty, and explicit scoring limitations (heuristic, never
"calibrated" without measurement).

## Existing implementation reused

- Version-guarded `manager.update()` verb, `MemoryStored` announcements via
  the writer, `MemoryValidationError` / `MemoryNotFoundError` domain errors,
  `manager.get` reads — all reused. No new bus, events, tables, or knobs.
- Pre-existing conventions adopted as law: trading predictions pin
  `confidence=0.5`; lifecycle reads (never writes) confidence; the scorer
  blends confidence as one retrieval signal among eight.
- Two ad-hoc nudges (consolidator +0.02, graph +0.05) left in place, capped,
  and documented as pre-existing limitations rather than silently replaced.

## Changes implemented

- `services/confidence.py` (new `ConfidenceUpdater`, `manager.confidence`):
  `confirm` / `correct` / `record_reuse` / `record_outcome` /
  `apply_contradiction` + `history()` reader + `ConfidenceUpdateResult`
  value. Rules bounded (0.1–0.95 float, absolute [0, 1] clamp),
  deterministic, history-appended (cap 20), source/contradictor-deduped,
  version-guarded with 3 bounded retries.
- `services/manager.py` + `services/__init__.py`: construct + export
  (`confidence` accessor).

## Files added

- `src/aetheros/memory/services/confidence.py`.
- `tests/memory/test_confidence.py` (20 tests).
- `docs/memory/phase-reports/phase-13.md` (this report).

## Files modified

- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–12) and Trading changes present at
phase start; none within the regions I edited.

## Migrations and compatibility impact

No schema migration (history lives in the existing `metadata` JSON column).
No public API changed. `manager.update()` raw confidence edits still work
(documented escape hatch, still clamped 0–1).

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (235 passed, 4 skipped).
- `python -m pytest tests/memory/test_confidence.py -o addopts="" -q`
  (first run) → 19 passed, **1 failed** (test bug: flood hit rule bounds
  before the history cap — rewritten with net-zero alternating rules).
- After fix → exit 0 (**20 passed**).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**255 passed,
  4 skipped**: prior 235 + 20 new, 0 failed).
- `ruff check` on touched files → 3 findings, auto-fixed, re-check clean,
  suite re-run green.
- `mypy`: unavailable in env, same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **20 passed**, 0 failed, 0 skipped.
- Full memory suite: **255 passed, 4 skipped**, 0 failed. (Before this phase:
  235 passed / 4 skipped; delta = +20 new tests.)
- Not run: suites outside `tests/memory` (out of scope; no shared file
  touched).

## Baseline failures and evidence

None pre-existing. The single first-run failure was this phase's own test
bug (bounds stopped writes before the cap was reached), fixed in-phase by
making the flood net-zero so all 60 writes apply and the 20-cap engages.

## Required acceptance evidence

Contract-mandated areas, all in `test_confidence.py`:
- Score boundaries: `test_confirm_caps_at_bound`, `test_reuse_floors_and_caps`,
  `test_contradiction_dents_and_floors`.
- Deterministic updates: `test_deterministic_updates`.
- Duplicate evidence: `test_confirm_raises_and_dedups_by_source` (same
  source no-op), `test_contradiction_dents_and_floors` (same contradictor
  no-op).
- Contradictions: `test_contradiction_dents_and_floors`,
  `test_contradiction_refuses_history`.
- Explicit corrections: `test_correct_governs_user_preference`,
  `test_correct_governs_user_input_fact`, `test_correct_noop_when_nothing_changes`,
  `test_correct_refuses_prediction`,
  `test_correct_refuses_episode_and_inferred_fact`.
- Successful/failed verification: `test_reuse_success_and_failure`,
  `test_outcome_confirmed_and_refuted`.
- Immutable historical evidence: `test_correct_refuses_prediction`,
  `test_reuse_refuses_forecasts`, `test_outcome_refuses_prediction_rows`,
  `test_forecast_probability_untouched_by_fact_updates`.
- No retrieval bump: `test_retrieval_never_bumps_confidence`.
- No freshness decay: `test_age_alone_never_moves_confidence`.
- Evidence history: `test_evidence_history_is_capped_and_auditable`.
- Missing rows: `test_missing_row_raises_not_found`.

## Security and operational concerns

- Corrections are gated by row kind: a compromised or careless caller
  cannot rewrite predictions, trading history, episodes, failures or
  procedures through the correction path — it raises with a hint.
- History entries are bounded strings + numbers (no free-text payloads
  beyond source keys), capped at 20 per row — no unbounded growth.
- Version-guarded writes with bounded retries: concurrent updaters converge
  instead of clobbering.
- Heuristic scores are labelled as such in code, docs and report — never
  presented as calibrated probabilities.

## Remaining work

- Carried forward: Finding #1 (authz/redaction/export no-leak layer);
  UP017 style; `datetime.utcnow()` cosmetic.
- Optional: route the two legacy ad-hoc nudges (consolidator +0.02, graph
  +0.05) through history-appended updater calls (needs manager access in
  those services — deferred, documented as a limitation).

## Exact next-phase handoff

Phase 13 is **DONE** (suite green: 20 new tests, full memory suite 255
passed / 4 skipped). Re-read the contract, `implementation-state.md`
(§Phase 13 handoff), this report, and the live `confidence.py` /
`manager.py` source before the next phase. Key identifiers:
`ConfidenceUpdater`, `manager.confidence`, `ConfidenceUpdateResult`.

PHASE 13 — DONE
