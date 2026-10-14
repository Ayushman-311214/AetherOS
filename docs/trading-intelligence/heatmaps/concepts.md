# Heatmaps — Concepts

What a market heatmap is in AetherOS, what each kind shows, and the honesty
rules every cell obeys.

## What a heatmap is

A heatmap is a **time × price grid** where each cell holds aggregated liquidity
behaviour. X = time, Y = price, and the *intensity* (what gets coloured) is a
measured or derived quantity the liquidity engine computed. It is a pure
observation/visualisation layer over real data — it draws what was there, it
does not make calls.

## The six views — one grid, six lenses

All six read the **same** underlying `HeatmapCell` grid. They differ only in
*which* cell quantity becomes the intensity channel — so they can never
disagree about what the data was; only about what's emphasised.

| View | Channel | Shows |
|---|---|---|
| `liquidity` | `total_intensity` | where resting liquidity sat (bid+ask) |
| `persistence` | `persistence` | how long liquidity stood at a level |
| `flow` | `net_flow` | aggressor-signed executed volume (buy vs sell) |
| `sweep` | `sweep_score` | where sweeps happened (rejection & acceptance) |
| `absorption` | `absorption_score` | where aggressive flow met little price response |
| `pressure` | `pressure_score` | derived market-pressure magnitude |

## RAW DATA / OBSERVATION / DERIVED METRIC / INTERPRETATION

Every cell keeps the honest four-way distinction the spec requires:

- **RAW DATA** — the order-book levels and trade prints themselves (provider
  input, never altered).
- **OBSERVATION** — the measured cell quantities: `bid_intensity`,
  `ask_intensity`, `executed_buy_volume`, `executed_sell_volume`. These came
  straight off the book/tape.
- **DERIVED METRIC** — computed quantities: `imbalance`, `net_flow`,
  `persistence`, `consumption`, `replenishment`, `sweep_score`,
  `absorption_score`, `pressure_score`. These are *derived*, never asserted as
  raw fact, and a consumer must not read them as such.
- **INTERPRETATION** — what the heatmap *suggests*. This layer stops at the
  numbers; whether a bright cell means "wall held" or "trap" is a downstream,
  probabilistic question it deliberately does not answer.

## The honesty rules

- **No decisions.** No cell or view produces a BUY/SELL. The layer describes
  liquidity behaviour; the signal/decision layers interpret.
- **Possible, not certain.** Absorption is shown as *divergence strength*, not
  a labelled "absorbed" verdict; a sweep shows *outcome* (rejection/acceptance),
  never "reversal".
- **Mock is marked.** `is_mock` travels on every cell, point and view — a
  synthetic heatmap can never be drawn as real market structure.
- **None/0.0 is honest "nothing"** — an empty bin shows as empty, not as a
  fabricated neutral value.
