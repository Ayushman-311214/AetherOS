# Phase 3 Audit — Market Heatmap & Market-State Visualization

What Phase 3 added, what it reused, and how it stays a read-only observation
layer with no decisions and bounded memory.

## Reused (not rebuilt)

- **`LiquidityEngine`** (`trading/liquidity/engine.py`) — the heatmap replays
  the SAME engine the liquidity layer uses; the grid only *aggregates* the
  `LiquidityStepResult` (observation + zones + lifecycle events) it produces.
  No second liquidity engine, no duplicated detection logic.
- **`LiquidityObservation` / `LiquidityZone` / `LiquidityZoneEvent`** — the
  heatmap consumes them verbatim; it does not redefine liquidity concepts.
- **`OrderBook` / `TradeTick`** — the stream inputs, unchanged.
- **`SourceTier.MOCK` / `is_mock`** — surfaced on every cell, point, view and
  surface.

## New (this phase)

| Module | Contents |
|---|---|
| `heatmap/cell.py` | `HeatmapCell` — one (time,price) bin; measured volumes + derived scores + `net_flow`/`imbalance`/`total_intensity` |
| `heatmap/grid.py` | `HeatmapGrid` — bounded, incremental, look-ahead-free time×price builder (single shared engine) |
| `heatmap/views.py` | `render()` + `HeatmapView`/`HeatmapPoint` + `available_views` — six channel projections |
| `heatmap/surface.py` | `LiquiditySurface` + `project()` — price×time×intensity + terminal 2D map |
| `heatmap/service.py` | `HeatmapService` — replay stream → grid → the 7 getters + `get_surface` |

Wired `HeatmapService` into `bootstrapper._bootstrap_trading` (no provider/bus
deps — it replays caller-supplied streams, so it's a pure builder).

## The six views — one grid, six lenses

`liquidity` (total_intensity), `persistence`, `flow` (net_flow), `sweep`
(sweep_score), `absorption` (absorption_score), `pressure` (pressure_score).
All read the same `HeatmapCell` grid via `render(grid, kind)` — six lenses over
one build, never six engines, so they can never disagree about the data.

## HeatmapCell — meets the field list

`timestamp`, `price`, `bid_intensity`, `ask_intensity`, `total_intensity`
(derived), `executed_buy_volume`, `executed_sell_volume`, `net_flow` (derived),
`persistence`, `consumption`, `replenishment`, `sweep_score`,
`absorption_score`, `pressure_score` — plus `imbalance`, binning and `is_mock`.
Every required field maps to an existing measured/derived quantity; nothing is
invented.

## Boundary decisions

- **No decisions.** No cell/view emits a direction or trade — descriptive only.
- **One build path.** `_build(steps)` → `render(grid, kind)` for every getter;
  no per-heatmap service.
- **Sweep shown as outcome.** Rejection/absorbed vs acceptance/swept are
  distinct scores/events; never labelled a reversal.
- **Absorption as "possible".** `absorption_score` is divergence strength, not
  an "absorbed" verdict.
- **Pressure is a documented heuristic**, not a validated statistic — formula
  and assumptions in `pressure.md`.
- **3D surface is data-first**; `project()` is an optional terminal map that
  doesn't corrupt the underlying cells.

## Tests

`tests/trading/test_heatmap.py` — 21 tests: cell derivation/validation,
time/price bucketing, aggregation, incremental update, derived-max (not sum),
bounded-capacity eviction, six shared views, normalisation range honesty,
service getters, persistence/sweep/absorption/pressure visuals, deterministic
replay, look-ahead safety, surface shape + terminal projection, mock honesty.

## Remaining Phase 4 work

- Surface a `@tool` / CLI surface for the heatmap + a richer terminal renderer.
- Feed real ccxt order-book/trade streams (Yahoo has no book/tape) through a
  live loop rather than one-shot `analyze` calls.
- Persisted heatmap grids / replay artifacts for offline dashboards.
