# Liquidity — Absorption

Absorption is aggressive order flow being soaked up by resting liquidity
without a proportional price response. It is the tape-level signature of a wall
actually working — and it is reported as *evidence, never certainty*.

## The read (`analyze_absorption`)

The spec's two cases, exactly as stated:

- **Aggressive buying + limited upward movement → possible sell-side absorption**
  (`side = "ask"`): buyers are hitting the offers hard but price barely rises —
  resting sellers are absorbing the demand.
- **Aggressive selling + limited downward movement → possible buy-side absorption**
  (`side = "bid"`): sellers are hitting the bids hard but price barely falls —
  resting buyers are absorbing the supply.

## Inputs

- `observation.executed_buy_volume` / `executed_sell_volume` — the aggressor-signed
  print volume.
- `price_change` — the *realised* price move over the observation window,
  supplied by the caller/engine (the previous step's price vs this one's), so
  absorption is judged against what price actually did.
- `typical_price_move` — the volatility baseline (a rolling mean of recent
  absolute moves the engine maintains), so "little movement" is measured against
  real volatility, not a fixed constant.

## Logic

1. There must be executed flow *and* a non-zero baseline, else `side = "none"`
   (honest no-reading).
2. The flow must be one-sided: the dominant aggressor must carry ≥ 60% of total
   volume, else `none`.
3. `move_ratio = |price_change| / typical_price_move`. If `move_ratio ≤
   ABSORPTION_PRICE_BAND` (0.5), price stayed quiet — absorbed. If price moved
   *with* the flow, it is not absorption, so `none`.
4. `score = dominance × quietness`, capped at 1.0 — how dominant the flow was
   weighted by how little price moved.

## What it is and is not

It **is** evidence that resting liquidity at a side resisted the aggressive
flow — a real input to a heatmap or a signal's evidence tuple.

It is **not** a prediction that the wall holds next print, nor that it was
"real" (spoofed or iceberg resting liquidity absorbs identically on the tape).
The score measures *how strongly* the pattern appeared this step; whether it
leads to a hold or a break is a downstream, probabilistic question this layer
deliberately does not answer.

Emitted as a `LiquidityAbsorbed` event when `side != "none"`, carrying the
aggressive volume, the realised move, and the side that absorbed it.
