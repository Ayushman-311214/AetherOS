# Liquidity — Sweeps

A sweep is price interacting with a liquidity zone and consuming (or being
stopped by) the resting liquidity there. The critical honesty rule from the
spec: **a sweep is not automatically a reversal.** What price does *after* it
hits the zone is observed separately and reported as its own verdict.

## The two honest outcomes (`classify_sweep`)

The analyzer takes the zone plus the price extremes reached while interacting
with it (`intrazone_low`/`intrazone_high`), where price *settled* (`close_price`)
and how much was consumed:

- **Rejection** (`SWEEP_REJECTION`) — price entered the zone but settled back
  *inside* it. The resting liquidity held; the sweep was absorbed. Emitted as
  `LiquidityAbsorbed`.
- **Acceptance** (`SWEEP_ACCEPTANCE`) — price cleared through the zone's far
  edge by ≥ `SWEEP_THROUGH_RATIO` (0.5× the zone height) and *stayed* past it.
  The wall gave way. Emitted as `LiquiditySwept`.
- **None** (`SWEEP_NONE`) — the interaction never meaningfully consumed the
  zone. A graze is not a sweep.

Direction is honest too: sweeping the asks is `up` (buying through a supply
wall), sweeping the bids is `down` (selling through a demand wall).

## Detection in the tracker (`_apply_price_interaction`)

Each step, the price *range* — the executed prints plus the reference mid and,
crucially, the *previous* step's price — is compared to each active zone:

- A step only marks a touch if the range overlaps the band.
- `consumed` is the volume that traded **into** the band, plus — when price
  crossed the far edge — the aggressive flow that drove the through-move. A
  sweep *through* a thin wall is caught by the price crossing, not by requiring
  a print to land exactly inside the band.
- Rejection → zone stays `touched`, `LiquidityConsumed`.
- Acceptance → zone becomes `swept`, `sweep_count` up, `LiquiditySwept`, and the
  tracker arms `was_swept` so a later refill counts as replenishment.

## Why "not a reversal" matters

A sweep + rejection can look like a wall that held and a bounce (evidence of
demand/supply working). A sweep + acceptance can look like a breakout through
consumed liquidity. The analyzer reports *which one happened* and its consumed
volume and price travelled — the interpretation ("is this a reversal, a
continuation, a stop-run?") belongs to the signal/strategy layer downstream,
which weighs it alongside regime, momentum and evidence. This layer only ever
says what the liquidity did.

## Absorption vs sweep

The two concepts are related but distinct and kept separate:

- **Absorption** (`analyze_absorption`) reads the *tape*: heavy one-sided
  aggressive printing with little price response — resting liquidity soaked up
  the flow. Evidence of a wall working.
- **Sweep** reads *price vs the zone*: did price clear through the band.
  A rejection often *is* an absorption event viewed from the zone's side — the
  wall held — but the events are emitted separately so a consumer can weight
  the tape-based and zone-based evidence independently.
