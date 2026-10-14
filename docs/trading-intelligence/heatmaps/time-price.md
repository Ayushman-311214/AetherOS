# Heatmaps — Time × Price Liquidity

The primary heatmap: resting liquidity shown across time and price.

## Axes

- **X = time** — binned by `bucket_seconds` (configurable). A cell's
  `timestamp` is its bucket *start*, floored to the boundary, so a cell's own
  time always round-trips to the same bin.
- **Y = price** — binned by `price_step` (configurable). A cell's `price` is
  its bin *lower* bound.
- **Intensity** — `total_intensity = bid_intensity + ask_intensity`, the resting
  liquidity that bin accumulated.

## Aggregation & update

Each engine step writes into the bin its reference price falls in:

- Measured volumes (`bid_intensity`, `ask_intensity`, `executed_buy_volume`,
  `executed_sell_volume`) **accumulate** across observations in the bin — they
  are quantities, so the cell sums them.
- `sample_count` counts how many observations fed the cell.
- Derived scores (persistence, sweep, absorption, pressure) take the **max** —
  a score is a level, not an accumulation, so the strongest signal in the bin
  wins rather than inflating.

Live zones additionally *paint* their `persistence` and resting `liquidity_score`
onto every price bin their band covers, so a standing wall shows as a band of
intensity across its span, not just a point.

`update` is **incremental** — a step writes only its bins; previously-written
cells are untouched (asserted by the no-look-ahead test).

## Resolution & normalisation

- `price_step` and `bucket_seconds` are constructor knobs; finer steps give
  finer detail at more cells, coarser steps aggregate more.
- `render(grid, "liquidity", normalize=True)` scales each cell's intensity to
  `[0,1]` over the **observed** min/max — the range is honestly reported, not
  stretched to fill a fixed band. `normalize=False` returns raw quantities.

## Honest reading

A bright bid cell means *resting bids were displayed there* — not that they
held, and not a support-level prediction. The heatmap shows what liquidity was
shown; whether it was real (spoofed/pulled) is a downstream question.
