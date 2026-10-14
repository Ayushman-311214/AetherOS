# PHASE 16 — TRADING MEMORY INTEGRATION

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree: Memory phases 1–15 uncommitted + a 34-file uncommitted
  Trading working tree from the other agent. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/trading_history.py`
    (new), `.../domain/trading.py`, `.../domain/__init__.py`,
    `.../services/manager.py`, `.../services/__init__.py`,
    `tests/memory/test_trading_history.py` (new), `docs/memory.md`,
    `docs/memory/*`.
  - **Trading-owned**: NONE touched (re-read live interfaces only, per
    the contract's concurrent-agent rule).
  - **Shared**: none.

## Scope

Memory-owned adapter for historical analysis, regimes, concepts,
predictions, outcomes, evaluations, calibration records, strategy
observations and attributable reasoning summaries — with instrument/
venue/timeframe/as-of support, exact preservation + linked appends,
event/ingestion/evaluation time separation, as-of retrieval, idempotent
ingestion, out-of-order outcomes, restart/scope/disabled coverage, and an
explicit unverified-integration ledger. No trading algorithms touched or
duplicated; no results or calibration computed here.

## Existing implementation reused

- `PredictionMemory` / `PredictionOutcomeMemory` + `remember_prediction` /
  `remember_prediction_outcome` (immutable + `has_outcome` links) — kept;
  the adapter builds on the same verbs and link shape.
- `store` (idempotency keys), `link`, `get`, `find_by_metadata`,
  `instrument_id` indexed columns, `MemoryStored` announcements — reused.
- No new bus, events, tables, migrations, knobs, or scheduler.

## Changes implemented

- `domain/trading.py`: 5 new history records (`MarketRegimeMemory`,
  `AnalysisSnapshotMemory`, `StrategyObservationMemory`,
  `CalibrationRecordMemory`, `ReasoningSummaryMemory`) + shared
  `_trading_memory` TRADING/OBSERVATION projection (instrument/timeframe/
  event_time metadata); module docstring gains the three-times contract.
- `services/trading_history.py` (new `TradingHistoryAdapter`,
  `manager.trading_history`): `from_*` constructors (tolerant, verbatim);
  idempotent `ingest_prediction/outcome/regime/analysis/strategy/
  calibration/reasoning`; bidirectional out-of-order outcome linking
  (`_backfill_outcome_links`); `outcomes_for`; `history_as_of`
  (event_time<=as_of, undated excluded, chronological, kind/timeframe/
  limit filters); `get_record`; `verify_consumer_contract` ledger.
- `services/manager.py` + `services/__init__.py`: construct + export
  (`trading_history` accessor).

## Files added

- `src/aetheros/memory/services/trading_history.py`.
- `tests/memory/test_trading_history.py` (12 tests).
- `docs/memory/phase-reports/phase-16.md` (this report).

## Files modified

- `src/aetheros/memory/domain/trading.py`
- `src/aetheros/memory/domain/__init__.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

None (deliberately — the Trading tree is mid-edit by another agent).

## Concurrent changes observed

34-file uncommitted Trading working tree (domains, providers, services,
tools) present at phase start and re-verified before writing: value
objects used for the seam (`PredictionRecord`, `RegimeAnalysis`,
`TradingAnalysis`, `StrategyEvaluation`, `CalibrationHistoryService`)
were read live; the adapter takes no dependency on them (plain-dict
seam), so their ongoing edits cannot break this phase. No Memory-owned
region was touched by the other agent.

## Migrations and compatibility impact

No schema migration (history rides `memory_items`/`memory_links` +
existing indexed metadata columns). `remember_prediction[_outcome]`
unchanged and interoperable (adapter reads their rows). No public API
removed.

## Commands executed and exit statuses

- `python -m pytest tests/memory -o addopts="" -q` (baseline) → exit 0
  (293 passed, 4 skipped).
- `python -c "import ..."` (import check) → exit 0.
- `python -m pytest tests/memory/test_trading_history.py -o addopts="" -q`
  (first run) → 11 passed, **1 failed** (test setup bug: DB read before
  initialize on a disabled manager).
- After fix → exit 0 (**12 passed**).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**305 passed,
  4 skipped**: prior 293 + 12 new, 0 failed).
- `python -m pytest tests/memory tests/cli/test_memory_command.py -o
  addopts="" -q` → exit 0 (**309 passed, 4 skipped**).
- `ruff check` on touched files → auto-fixed import sort; my 2 F841 fixed
  by hand; final: clean.
- `mypy`: unavailable in env, same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **12 passed**, 0 failed, 0 skipped.
- Memory + CLI suite: **309 passed, 4 skipped**, 0 failed. (Before this
  phase: 297 passed / 4 skipped; delta = +12 new tests.)
- Not run: `tests/trading/*` (Trading-owned, other agent's tree in flux —
  deliberately untouched and unexecuted).

## Baseline failures and evidence

None pre-existing. The single first-run failure was this phase's own test
setup bug (queried a never-initialized manager), fixed in-phase.

## Required acceptance evidence

Contract-mandated areas, all in `test_trading_history.py`:
- Actual available consumer contracts:
  `test_prediction_ingest_and_reingest_idempotent` (memory-domain),
  `test_prediction_record_shape_accepted` (trading-shape mapping),
  `test_single_shot_paths_read_back` (existing verbs interoperate).
- Immutable history: `test_outcome_links_and_never_edits_prediction`.
- Idempotent ingestion: `test_prediction_ingest_and_reingest_idempotent`,
  outcome re-ingest in `test_outcome_first_links_on_prediction_arrival`.
- Out-of-order outcomes: `test_outcome_first_links_on_prediction_arrival`.
- Linkage: outcome `has_outcome` links, `test_reasoning_summary_links_sources`.
- Restart: `test_restart_preserves_history_and_links` (file DB + fresh manager).
- Scope isolation: `test_as_of_scope_and_kind_filters`.
- As-of retrieval: `test_as_of_excludes_future_and_undated`,
  `test_as_of_scope_and_kind_filters` (order + bounds).
- No invented results: verbatim assertions on prob_up/model_version/brier/
  correction payloads in every ingest test.
- Disabled honesty: `test_disabled_ingest_returns_unsaved`.
- Explicit ledger: `test_consumer_ledger_is_explicit`.

## Security and operational concerns

- History rows are OBSERVATION veracity, never FACT — stored forecasts
  cannot be mistaken for ground truth by the epistemic validator.
- Trading-history protection (Phases 12/14/15) covers these rows: no
  near-merge, no decay demotion, guarded forget/erase.
- Reasoning summaries link sources; missing refs skip with a warning
  (never fail ingestion, never invent the missing source).
- No credentials path: payloads are trading numbers + labels; the
  write-path validator still screens every row.

## Remaining work

- Live-consumer verification (a TradingReport → adapter ingest round-trip
  against a real trading instance) is owed to a joint session with the
  Trading agent once their tree settles — the ledger names exactly what.
- Carried forward: Finding #1; UP017/UP042 style; `datetime.utcnow()`
  cosmetic; B905/F841 pre-existing.

## Exact next-phase handoff

Phase 16 is **DONE** (suite green: 12 new tests, memory + CLI suite 309
passed / 4 skipped; Trading tree untouched). Re-read the contract,
`implementation-state.md` (§Phase 16 handoff), this report, the live
`trading_history.py` / `trading.py` source, and re-check the Trading
working tree (still in flux) before the next phase. Key identifiers:
`TradingHistoryAdapter`, `manager.trading_history`,
`MarketRegimeMemory` / `AnalysisSnapshotMemory` /
`StrategyObservationMemory` / `CalibrationRecordMemory` /
`ReasoningSummaryMemory`, `history_as_of`, `verify_consumer_contract`.

PHASE 16 — DONE
