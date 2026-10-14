# Phase 6 Audit — Backtesting, Prediction Tracking, Outcomes & Calibration

What Phase 6 added, what it reused, and how the system now measures whether its
intelligence actually works.

## Reused (not rebuilt)

- **`MarketData.window(0, i+1)`** — the single place the codebase's past-only
  slicing guarantee is defined; the pipeline reuses it so a backtest can't peek
  ahead (same primitive the live replay and walk-forward folds use).
- **`PredictionEvaluator`** (existing) — the endpoint scorer (entry/exit/return/
  hit-miss/PENDING/UNRESOLVABLE) already implemented; this layer extends it with
  the *path* fields.
- **`CalibrationReport`** (`quant/calibration.py`) — Brier / log-loss / accuracy /
  ECE / reliability bins, fully built and reused verbatim.
- **`PredictionPerformanceService`** — the existing aggregate calibration read.
- **Production components** — `AnalysisService`, `SignalEngineService`, the
  deterministic risk & probability services, all wired into the pipeline via the
  bootstrapper rather than re-implemented.

## New (`trading/backtest/`)

| Module | Contents |
|---|---|
| `outcome.py` | `EnrichedOutcome` — the prediction outcome plus path fields (MFE/MAE, target/invalidation hits, time_to_outcome) |
| `evaluator.py` | `OutcomeEvaluator` + `PredictionLike` — measures the *path* through the forward window |
| `metrics.py` | `BacktestMetrics` + `evaluate` — the full metric set + liquidity-specific rates |
| `pipeline.py` | `BacktestPipeline` + `BacktestResult` — the production-component replay loop |

Wired `BacktestPipeline` into `bootstrapper._bootstrap_trading` with a
`_backtest_assess` that runs the real `AnalysisService -> SignalEngineService`
chain on each past-only window.

## The pipeline the spec asks for

```
MarketData
   -> MarketIntelService (structure/technical/volume/regime)
   -> SignalEngineService (evidence -> SignalAssessment)
   -> Prediction (timestamped to the window's last bar)
   -> OutcomeEvaluator (forward path measured)
   -> BacktestMetrics (the full metric set + liquidity rates)
```

All steps are the *same* production components the live path uses — there is
deliberately no fake analysis implementation. The `assess_fn` is injectable so
any production composition can be driven, but the default wires the real chain.

## Look-ahead prevention

Every step reads only `data.window(0, i + 1)`. The prediction timestamp is the
window's *last bar*, never the wall clock, so the evaluator resolves it against
genuinely-following bars. The `test_pipeline_no_lookahead_each_step_only_sees_past`
test spies on the assess fn to prove each window ends exactly at its step's bar.

## Outcome fields (new)

`max_favorable_excursion` / `max_adverse_excursion` (signed in the predicted
direction, read off bar highs/lows), `target_hit` / `invalidation_hit` (`None`
when no level was stated), `time_to_outcome` (bars to first hit), all beside the
existing status/return/is_correct fields.

## Metrics

accuracy, precision, recall, expected_return, win_rate, loss_rate, mean MFE,
mean MAE, profit_factor, risk_reward_mean, false_signal_rate, target_hit_rate,
invalidation_hit_rate, zone_reaction_rate, sweep_reversal_rate,
sweep_continuation_rate, absorption_success_rate, replenishment_significance,
persistence_significance — all `None` when not measurable (honest "not measured").

## Tests

`tests/trading/test_backtest_pipeline.py` — 17 tests: evaluator (resolve/
pending/unresolvable/excursions/hits), metrics (accuracy/rates/return/
excursions/level-rates/thin/mock/liquidity), pipeline (replay/no-lookahead/
determinism/prediction-timestamps), calibration report.

## Remaining Phase 7 work

- A `SignalAssessment`-aware `PredictionRecord` so the signal-engine output can
  be persisted + resolved by the existing `PredictionStore`/`PredictionEvaluator`.
- Wire the pipeline to a `@tool`/CLI surface.
- Real aggressor-tape and order-book-diff feeds for richer liquidity metrics.
