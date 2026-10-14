# Heatmaps — Persistence

How long liquidity stood around a price level — and why that is *not* the same
as "the level will hold".

## What it shows

The `persistence` view emphasises a cell's `persistence` channel: how long the
resting liquidity at that (time, price) bin had already stood when observed.
Bright persistence = liquidity that kept showing up at the level, snapshot after
snapshot — the visual signature of a wall with real staying power versus a
flash order that vanished.

## Where the number comes from

Persistence is inherited from the `LiquidityZone`'s `persistence_score` — a
0..1 value the zone tracker increments each snapshot the cluster is re-detected
at the same band (saturating over `persistence_full` = 10 snapshots). The grid
paints a live zone's persistence onto every price bin its band covers, so a
long-lived wall shows as a persistent *band*, not a single dot.

`render(grid, "persistence")` normalises that channel to [0,1] over the
observed range, so the brightest cells are the longest-standing liquidity in
the window.

## Persistence ≠ certainty

The spec is explicit: do not equate persistence with certainty. A persistent
wall is *evidence of sustained displayed interest* — and nothing more:

- Resting orders pull constantly; a long-standing wall can vanish the moment
  price approaches.
- Persistence measures *displayed* liquidity duration, not the intent behind it
  (a spoofed wall can be persistent too).
- A bright persistence cell is a fact about the stream — "this liquidity kept
  reappearing here" — and is weighed alongside sweeps, flow and regime, never
  read as "support will hold".

The view therefore shows *duration*, honestly labelled, and leaves the
"does it hold?" question to the signal layer.
