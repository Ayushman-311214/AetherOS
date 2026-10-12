# Backtesting — Metrics & Prediction/Outcome Contracts

The prediction the pipeline records, the outcome it measures, and the metrics
it aggregates — all `None` when not measurable (honest "not measured").

## Prediction record (`PredictionLike`)

```python
prediction_id        # content-addressed: instrument|timeframe|index|direction
instrument_key
timeframe
direction            # UP | DOWN | SIDEWAYS | UNKNOWN
created_at           # the window's last bar (never wall clock)
horizon_bars
entry, target, invalidation_price, probability_up, is_mock
```

## Outcome record (`EnrichedOutcome`)

```python
status               # resolved | pending | unresolvable
realized_return, realized_direction, is_correct
entry_price, exit_price, entry_timestamp, outcome_timestamp
horizon_bars, bars_elapsed

# The PATH (new in Phase 6):
max_favorable_excursion   # furthest the move ran FOR the call
max_adverse_excursion     # furthest it ran AGAINST it
target_hit                # None when no target was stated
invalidation_hit          # None when no invalidation was stated
target, invalidation_price
time_to_outcome           # bars to first hit (or horizon if none)
```

## Metrics (`BacktestMetrics`)

| Metric | Formula | `None` when |
|---|---|---|
| `accuracy` | hits / scored directional outcomes | no scored |
| `precision` | hits / directional calls made | no calls |
| `recall` | hits / actual directional outcomes | none directional |
| `win_rate` / `loss_rate` | hits/misses / resolved | none resolved |
| `false_signal_rate` | misses / scored | no scored |
| `expected_return` | mean realised return | none resolved |
| `mean_mfe` / `mean_mae` | mean excursion | none measured |
| `profit_factor` | gross wins / gross losses | no losses → `inf` |
| `risk_reward_mean` | mean \|MFE\| / \|MAE\| | pairs unavailable |
| `target_hit_rate` | target hits / stated-target calls | none stated |
| `invalidation_hit_rate` | inv hits / stated-invalidation calls | none stated |
| `zone_reaction_rate` | directional hits / scored | no scored |

## Liquidity-specific rates

Read off outcomes that carry liquidity-event context (recorded in
`limitations` as `sweep:rejection` / `sweep:acceptance` / `absorbed` /
`replenished` / `persistent`):

- `zone_reaction_rate` — share of directional calls that resolved as hits.
- `sweep_reversal_rate` — share of sweep-context outcomes that were rejections.
- `sweep_continuation_rate` — share that were acceptances.
- `absorption_success_rate` — share of absorbed zones that held (resolved hit).
- `replenishment_significance` / `persistence_significance` — the
  directional-accuracy *lift* of outcomes carrying that context vs those
  without, in [-1,1] (`None` when the context is absent).

## Reliability gate

`is_reliable` requires `scored >= min_sample` (default 10) AND no mock outcome
in the sample. A thin or MOCK-resolved batch is reported with limitations —
never dressed up as a real track record.
