# Heatmaps — Performance

Heatmaps can grow large; this layer is built to stay bounded and cheap.

## Bounded memory

`HeatmapGrid` is a fixed-resolution matrix over a **rolling time window**, not
an unbounded log:

- **`capacity`** caps the number of *distinct time-buckets* retained (default
  256). Once the window is full, the oldest bucket's cells are evicted — so a
  long replay or a live feed can never exhaust RAM. Total live cells ≤
  `capacity × (price range / price_step)`.
- **`price_step` / `bucket_seconds`** set resolution — finer gives more cells,
  coarser aggregates more. They are the direct knobs for trading detail vs
  footprint.
- **`clear()`** drops all cells.

`test_grid_bounded_capacity_evicts_oldest_bucket` asserts the window stays
within `capacity` buckets and the oldest cells are dropped.

## Incremental updates

`update` writes only the bins the step touches — it never rebuilds the grid.
Per-step cost is O(zones × span + events + 1), independent of grid size, so the
steady-state cost of a live feed is flat.

## Aggregation

Measured volumes accumulate in-place into existing bins (`dict` keyed on
(time,price)); derived scores take the max. A heavy bin costs no more to update
than an empty one.

## Efficient serialization

- `HeatmapCell.to_dict()` / `HeatmapView.to_dict()` /
  `LiquiditySurface.to_dict()` emit flat JSON-friendly structures — no nested
  domain objects, cheap to serialise or ship to a dashboard.
- `HeatmapView.points` are (time, price, intensity) triples — a render-ready
  projection that avoids re-serialising full cell detail when only the
  intensity channel is needed.
- `surface()` materialises only the distinct price/time axes actually present
  (sparse cells read as `0.0`), so a sparse grid stays small.

## Replay cost

`service.replay` / a getter runs the shared `LiquidityEngine` once and folds
each step into the grid — O(steps) total, and the same work the liquidity layer
already does. There is no duplicated liquidity computation, so the heatmap adds
only binning + aggregation on top of the existing engine.
