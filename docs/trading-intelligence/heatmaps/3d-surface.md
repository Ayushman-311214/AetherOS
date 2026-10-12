# Heatmaps — 3D Liquidity Surface

The price × time × intensity surface — a renderer-agnostic *data* representation
plus an optional terminal-compatible projection.

## The axes

```
X = price      (ascending price-bin bounds)
Y = time       (ascending time-bucket starts)
Z = liquidity intensity   (the channel value at that cell)
```

`LiquiditySurface` is the data: `prices`, `timestamps`, and a `values[t][p]`
matrix where each entry is the chosen channel's intensity for that (price, time)
cell — `0.0` where the grid had no cell (an honest "nothing observed", never an
interpolated fill).

## Data, not a renderer

The surface is a **pure projection of the shared grid** — the same
`HeatmapCell`s the 2D views use, re-shaped into a matrix. No renderer is
mandatory for the core intelligence: the surface exists as data, so a terminal,
a future GUI or a web dashboard can all consume the identical numbers. It never
becomes a parallel source of truth.

```python
surf = svc.get_surface(steps, symbol="BTC/USD", channel="total_intensity")
# surf.values[t][p] -> intensity at (price[p], time[t])
```

## Terminal projection

A terminal can't draw a true 3D surface, so `project(surface, width)` renders a
2D text intensity map: rows = time, columns = price, glyph = intensity against
the surface's own observed max. It is a faithful projection — downsampled by
windowed *max* (so a hot cell is never averaged away) and honest about its
range — and it does not mutate or corrupt the underlying `HeatmapCell` data.
An empty surface renders `(empty liquidity surface)`, not a fabricated
gradient.

## Reusable by

- **Terminal** — `project()` text map above.
- **Future GUI / web dashboard** — `LiquiditySurface.to_dict()` (prices,
  timestamps, values matrix) is directly consumable by a real 3D or heatmap
  renderer; the data is identical regardless of where it's drawn.
- **Backtesting** — the surface is a pure function of the replayed stream, so
  it serialises deterministically for offline analysis.

## Honesty

- `channel` names which quantity the surface encodes (default
  `total_intensity`), so a consumer always knows what Z means.
- `is_mock` travels on the surface so synthetic depth is never drawn as real.
- The Z axis is liquidity *behaviour shown*, never a "will it hold" axis —
  persistence and probability stay in their own channels.
