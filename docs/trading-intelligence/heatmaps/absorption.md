# Heatmaps — Absorption

Where aggressive flow and price response diverge — shown as *possible*
absorption, never declared certainty.

## The pattern

Absorption is the divergence the spec describes:

```
large aggressive buy volume
   +
limited upward price movement
   =
possible sell-side absorption
```

Heavy one-sided printing with little price response suggests resting liquidity
soaked up the aggressive flow. The same holds for selling absorbed by resting
buyers.

## What the cell carries

The `absorption` view emphasises a cell's `absorption_score` — the `0..1`
divergence strength the absorption analyzer computed (`dominance × quietness`):
how one-sided the flow was, weighted by how little price moved for the effort.

The score is **descriptive strength, not a verdict**:

- It measures *how strongly* the aggressive-vs-movement divergence appeared in
  the bin.
- It deliberately preserves "possible" — a bright cell says "the divergence
  looked strong here", not "sellers definitely absorbed the buys".

## Why "possible" is preserved

Declaring certainty would overclaim what the data supports:

- A resting wall can be a bluff (spoofed or iceberg liquidity absorbs
  identically on the tape).
- Whether absorbed flow leads to a hold or a break is a probabilistic,
  downstream question.

So the visualization keeps the *divergence strength* as the signal and never
stamps a cell "absorbed" as fact. `absorption_bid_score`/`absorption_ask_score`
in the feature vector carry which side the read leaned toward; the heatmap
shows where the divergence was strongest.

## Event distinction

An `LiquidityAbsorbed` event on the zone side (a sweep rejected — the wall
held) and the analyzer's absorption read are related but distinct: one is
zone-level evidence, the other tape-level. They land on the bin independently
so a consumer can weigh both rather than have one hidden inside the other.
