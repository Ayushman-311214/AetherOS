# Liquidity — Backtesting

How the liquidity layer stays deterministic and look-ahead-free, and how to
replay a recorded stream to get the identical intelligence a live feed would
have produced.

## The guarantee

Every liquidity calculation is a deterministic function of the historical input
it is handed. The same `(order-book snapshot, trade prints)` stream always
produces the same observations, zones, events and features.

This is enforced structurally:

- **No wall clock inside the analyzers.** `analyze_imbalance`,
  `analyze_absorption`, `classify_sweep`, `detect_zones`,
  `analyze_consumption`, `analyze_replenishment` are pure functions — no I/O, no
  `datetime.now()`, no randomness.
- **All timestamps come from the stream.** A zone's `first_seen`/`last_seen`, an
  observation's `timestamp`, an event's `timestamp` are the snapshot/print
  times, never the construction time.
- **State is a pure function of the ordered input.** `ZoneTracker` and
  `LiquidityEngine` hold lifecycle state, but that state is fully determined by
  the sequence of steps fed to them — two engines replayed on the same steps
  reach identical results.

## Timestamp boundaries (no look-ahead)

Each `engine.step(book, trades)` reads **only** that step's inputs:

- The observation uses this step's top-of-book depth and this step's prints.
- Zone lifecycle uses this step's detected clusters and the price range of this
  step (plus the *prior* step's price, which is genuinely *between-step* state —
  carried on the engine for the absorption realised-move window, not future
  information).
- Nothing about step *t* reads step *t+1*. Replaying the same recorded stream
  therefore reproduces exactly what a live feed would have shown at each point.

## Replaying a stream

```python
svc = LiquidityIntelligenceService(order_book_source=src, event_bus=bus)
report = await svc.replay([
    (book_t0, trades_t0),
    (book_t1, trades_t1),
    ...
])
```

`replay` runs a fresh `LiquidityEngine` over the ordered steps, publishes the
canonical events to the bus, and returns the final observation, live zones and
feature vector. Feeding the identical stream twice yields an identical event
sequence and identical zone/feature state — asserted by
`test_engine_deterministic_replay`.

## What this enables downstream

- **Heatmaps** can be built from the persisted `ObservationStore`/`ZoneStore`
  over a historical window.
- **Signals** can consume the `LiquidityFeatures` vector as one evidence input
  among many, computed the same way live and in backtest.
- **Backtesting** can replay recorded books/prints and measure how the detected
  zones/sweeps/absorptions related to realised outcomes — without the detection
  logic ever peaking ahead.

## Persistence for replay

```
liquidity/
    observations   -- FileObservationStore (append-only audit)
    zones          -- FileZoneStore        (last-line-wins lifecycle)
    events         -- the canonical Event subclasses on the bus
```

The stores reuse the established append-and-read, content-addressed,
never-fabricate pattern (`PredictionStore`/`OutcomeStore`) — same contract, no
new database architecture. Re-recording a zone id upserts to its latest state,
so a zone's maturing lifecycle is reflected without rewriting history.
