# Heatmaps — Architecture

A read-only projection layer, `src/aetheros/trading/heatmap/`, that sits on top
of the Phase-2 liquidity engine. One shared stream → one shared grid → six
projected views. The design deliberately has a single build path so binning,
aggregation, look-ahead-safety and the no-decisions rule each exist once.

## Module map

```
heatmap/
  cell.py      HeatmapCell           -- one (time,price) bin of measured+derived data
  grid.py      HeatmapGrid           -- bounded, incremental time x price builder
  views.py     render() + HeatmapView -- six channel projections over the grid
  surface.py   LiquiditySurface + project() -- price x time x intensity + terminal view
  service.py   HeatmapService        -- replay stream -> grid -> getters
```

## Data flow

```
(order-book, trades) stream
        │
        ▼
LiquidityEngine.step            -- the SAME engine the liquidity layer uses;
        │                          produces observation + zones + lifecycle events
        ▼
HeatmapGrid.update(obs, zones, events)
        │  measured volumes aggregate into (time,price) bins;
        │  zones paint persistence/resting-share onto covered bins;
        │  lifecycle events land their score on the bin they hit
        ▼
HeatmapCell grid  (bounded, look-ahead-free)
        │
        ├──> render(grid, "liquidity"|"persistence"|"flow"|"sweep"|"absorption"|"pressure")
        │           -> HeatmapView  (points + honest min/max range)
        └──> surface(grid, channel) -> LiquiditySurface -> project() (terminal 2D)
```

## Why one grid, not six engines

The six heatmap kinds are *the same cells read through six intensity channels*.
Building six engines would duplicate the binning, aggregation, capacity and
look-ahead logic — six places for a bug or a leak. Instead the grid is built
once per stream, and `render(grid, kind)` projects whichever channel that view
emphasises. The views share the grid, so they can never disagree about the data.

## The HeatmapService contract

`HeatmapService` exposes the brief's getters: `get_heatmap`,
`get_liquidity_heatmap`, `get_persistence_heatmap`, `get_flow_heatmap`,
`get_sweep_heatmap`, `get_absorption_heatmap`, `get_pressure_heatmap`, plus
`get_surface` (the 3D data) and `views()`. Every getter runs the same
`_build(steps)` → `render(grid, kind)` path — there is one service and one
build, not one service per heatmap kind.

## Boundaries

- **No decisions.** Nothing in the layer emits a direction, signal or trade.
- **No second engine.** The heatmap reuses `LiquidityEngine` rather than
  re-implementing liquidity logic; the grid only *aggregates* what it produced.
- **Deterministic.** The grid is a pure function of the ordered stream; feeding
  a recorded stream reproduces the identical cells a live feed would have shown.
- **Bounded.** `capacity` caps retained time-buckets; resolution
  (`price_step`, `bucket_seconds`) caps cell count; the grid never grows
  without limit.
