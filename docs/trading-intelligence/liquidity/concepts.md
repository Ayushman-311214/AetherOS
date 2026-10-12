# Liquidity — Concepts

What "liquidity" means in AetherOS, what the system observes, what it infers,
and what it can never guarantee.

## What liquidity is

Liquidity is the market's willingness to trade. It shows up in two forms the
liquidity layer keeps strictly separate:

- **Resting liquidity** — the quantity displayed on the order book at each
  price level: bids waiting to buy, asks waiting to sell. This is *intent*,
  observed state. It can be pulled, spoofed or consumed; it is not a promise.
- **Aggressive (executed) liquidity** — the volume that actually *prints*:
  buyer-initiated and seller-initiated trades that cross the spread. This is
  *action*, the flow that consumes, absorbs or is absorbed by resting liquidity.

Reading one as the other is the central error this layer exists to prevent: a
book can be bid-heavy while the tape sells, and a fat displayed wall can be a
bluff.

## What the system observes (not infers)

For each instrument the engine reads order-book snapshots and executed-trade
prints and produces `LiquidityObservation` records:

- `bid_liquidity` / `ask_liquidity` — the top-of-book resting depth on each side.
- `executed_buy_volume` / `executed_sell_volume` — the aggressor-signed print
  volume in the observation window.
- `imbalance` — `(bid − ask) / (bid + ask)`: the resting balance (derived).
- `net_flow` — `(buy − sell) / (buy + sell)`: the aggressive balance (derived).

These are facts about the snapshot and the prints — nothing more.

## What it infers (as evidence, never certainty)

On top of the observations the analyzers infer **liquidity behaviour**:

- **Zones** — price bands where resting liquidity clusters *persistently*. Not
  "the biggest order" — a zone has to be large *relative to its own book* and
  stand over time to matter.
- **Sweeps** — price interacting with a zone and consuming it. Distinguished as
  *rejection* (entered and settled back inside — the wall held) vs *acceptance*
  (cleared through and stayed — the wall gave way). A sweep is never
  auto-classified as a reversal.
- **Absorption** — heavy one-sided printing with little price response,
  suggesting resting liquidity soaked up the aggressive flow. Evidence of a
  wall working, not a guarantee it holds.
- **Replenishment** — resting liquidity repeatedly reappearing at a level after
  being eaten. Evidence of stickier, more persistent interest.
- **Consumption / velocity** — how much of a wall the tape ate, and how fast
  resting liquidity is turning over.

## What is NOT guaranteed

- A displayed wall is not a promise it will be there when price arrives — orders
  pull constantly.
- A sweep is not a reversal — it is observed consumption, nothing more.
- Absorption is not "the level will hold" — it is evidence, weighed alongside
  everything else.
- A MOCK or synthetic book produces labelled-mock reads that can never read as
  real liquidity (`is_mock` travels on every record).

The honest output is always *what the liquidity did*, with provenance and an
honesty flag — never a prediction of what it will do.
