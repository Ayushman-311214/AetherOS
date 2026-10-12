# Heatmaps — Sweeps

Where sweeps happened, and — critically — how they resolved, *without* the
visualisation labelling a sweep a reversal.

## What it shows

The `sweep` view emphasises a cell's `sweep_score` channel: the intensity of
sweep activity in that (time, price) bin. Bright = a sweep occurred there.

## Rejection vs acceptance, shown not declared

A sweep is price consuming/resting-liquidity. The visualization distinguishes
the two honest outcomes the liquidity analyzer produces:

- **sweep → rejection** — price entered the zone but settled back inside it
  (the wall held; the sweep was absorbed). Lands `LiquidityAbsorbed` → a
  moderate `sweep_score` + an `absorption_score` on the bin.
- **sweep → acceptance** — price cleared through the zone's far edge and
  *stayed* (the wall gave way). Lands `LiquiditySwept` → the strongest
  `sweep_score` on the bin.

Both are *shown* — the events carry the outcome — but the heatmap **does not
label a sweep a reversal**. A bright sweep cell is observed consumption; whether
it preceded a bounce (rejection) or a break (acceptance) is in the data, but
the verdict "reversal" is a downstream, probabilistic question this layer never
asserts.

## Where the score lands

Each sweep event lands its score on the bin at the event's `price` (the price
where the sweep resolved). `render(grid, "sweep")` normalises that channel, so
the brightest cells are the most decisively-consumed bands in the window.

## Honest reading

- A swept-acceptance cell = "resting liquidity here was consumed and price held
  past it" — evidence of a wall giving way, not a confirmed breakout.
- A rejected/absorbed cell = "price hit the wall and settled back inside" —
  evidence the wall held this time, not that it always will.
- Sweeps are facts about the stream; the heatmap draws them faithfully and
  leaves "is this a reversal" to interpretation downstream.
