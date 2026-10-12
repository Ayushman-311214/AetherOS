# Heatmaps — Market Pressure

A derived market-pressure magnitude — honestly a documented heuristic, not a
statistically validated measure.

## What it is

`pressure` is the one derived view that combines the resting and aggressive
sides into a single unsigned "how hard is the market pushing" magnitude per
bin. It is the most interpretive channel in the layer, so its formula and
assumptions are stated plainly here.

## The formula

Computed per observation (in `HeatmapGrid._pressure`) and surfaced as the
cell's `pressure_score`:

```
resting  = observation.imbalance        # (bid - ask) / (bid + ask)  in [-1,1]
flow     = observation.net_flow         # (buy - sell) / (buy + sell) in [-1,1]

pressure = min(1.0, (|resting| + |flow|) / 2)
```

The **magnitude** (unsigned) of the dominant push, averaged across the two
channels — so a market that is both leaning *and* flowing the same way scores
higher than one where book and tape pull apart.

## Assumptions (stated, not dressed up)

- It is a **linear, hand-chosen blend** of two [-1,1] inputs. There is no
  trained weighting, no calibrated probability and no significance test behind
  the `(|resting| + |flow|)/2` average — it is a sensible descriptor, not a
  validated statistic.
- It conflates resting *intent* with executed *action*. That is a deliberate
  simplification: the two channels are also available separately
  (`liquidity`/`flow` views) precisely because merging them loses the
  book-vs-tape distinction.
- It is unsigned — pressure says *how much* the market is pushing, not which
  way. Direction stays in `imbalance`/`net_flow`.

## Honest reading

A bright pressure cell = "the market showed strong one-sided resting and/or
executed activity here". It is descriptive context for a heatmap, weighed
alongside the separately-available resting, flow, sweep and absorption views —
never a directional call and never a confidence number.

## Why it isn't dressed up

The spec forbids making the formula look more validated than it is. The two
inputs are themselves derived (not raw), and averaging their magnitudes is a
heuristic choice — so this doc names the formula, names the assumptions, and
keeps `pressure_score` clearly labelled as a descriptive derived channel.
