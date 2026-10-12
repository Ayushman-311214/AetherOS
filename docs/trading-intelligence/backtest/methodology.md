# Backtesting — Methodology

How the backtest pipeline replays historical data through the production
components and measures the result.

## The walk-forward loop

```
for i in warmup .. (n-1-horizon) step=step:
    window  = data.window(0, i + 1)          # the bars UP TO step i only
    assess  = assess_fn(window)             # the PRODUCTION read on that window
    predict = timestamp to window.last_bar   # never the wall clock
    outcome = evaluator(predict, data)       # measured over bars AFTER i
```

`BacktestPipeline.run(data)` produces a `BacktestResult` holding every
`PredictionLike`, every `EnrichedOutcome`, and the aggregated `BacktestMetrics`.

## Production components only

The pipeline does **not** ship its own analysis. It takes an `assess_fn` —
injectable so the caller drives whichever production composition is under
test. The bootstrapper's default wires the real chain:

```python
analysis = await AnalysisService.analyze_data(window, emit=False)
return SignalEngineService.assess(analysis)
```

This is deliberately the *same* `AnalysisService`/`SignalEngineService` the live
path uses. A separate "fake analysis" implementation would let the backtest
drift from what production actually does — the spec explicitly forbids that, so
the pipeline only ever *composes* the real components.

## Window, horizon, warmup, step

- **`warmup`** — bars skipped at the front so indicators/structure warm up.
- **`horizon`** — bars ahead the prediction is scored over.
- **`step`** — stride between entry points (1 = every bar).
- **`window(0, i+1)`** — the half-open slice `[0, i+1)`: the prediction made at
  step `i` sees the bar at `i` and every bar before it, never one after.

## Timestamp honesty

A prediction's `created_at` is the *window's last bar timestamp* — the bar it
was made against — so the evaluator locates the entry by "last candle at or
before the prediction" and measures `horizon` bars forward. Nothing uses the
wall clock, so a replayed prediction resolves the way a live one would have at
that moment.

## Replaying the full stack

To backtest the *whole* intelligence stack (liquidity + heatmap + market-intel
+ signal-engine), supply an `assess_fn` that runs those services on the window:

```python
async def assess(window):
    intel  = await market_intel.analyze(window)
    analysis = await analysis_service.analyze_data(window, emit=False)
    return signal_engine.assess(
        analysis,
        market_features=intel.features,
        liquidity_features=liq_features_for(window),
    )
pipe = BacktestPipeline(assess, horizon=5, warmup=40)
result = await pipe.run(data)
```

Each helper runs on the same past-only window, so the replay is the identical
analysis a live step would have produced.
