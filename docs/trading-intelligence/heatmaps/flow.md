# Heatmaps — Flow

Aggressor-signed executed flow — and the lifecycle distinction between
appearing, disappearing, consumed, replenished and moving liquidity.

## What it shows

The `flow` view emphasises a cell's `net_flow` channel: the executed
buyer-minus-seller-initiated volume in the bin, in [-1,1]. Positive (buyer-led)
is aggressive demand crossing the spread; negative (seller-led) is aggressive
supply. Bright net-flow cells show *which side* was doing the aggressive work
at that (time, price).

`net_flow = (buy − sell) / (buy + sell)` is derived from the measured
`executed_buy_volume`/`executed_sell_volume` — so it is a derived quantity over
the prints, never a raw resting read.

## The five flow states

The visualization distinguishes what liquidity *did* in a bin, sourced from the
zone lifecycle events the tracker emits:

| State | Signal | Event |
|---|---|---|
| **appearing** | new resting liquidity showed at a band | `LiquidityZoneCreated` / `LiquidityAppeared` |
| **disappearing** | resting liquidity pulled/faded (not eaten) | `LiquidityZoneWeakened` |
| **consumed** | the tape ate into the wall | `LiquidityConsumed` |
| **replenished** | liquidity reappeared after being eaten | `LiquidityReplenished` |
| **moving** | the zone's band shifted across price | reflected in where subsequent zones form |

Each lands its score on the bin at the event's price, so a flow view over a
replay shows *where* liquidity appeared, faded, was eaten or refilled — not
just net aggression.

## Reading flow vs resting liquidity

Flow and resting liquidity are deliberately separate channels:

- The `liquidity` view shows what the book *displayed* (intent).
- The `flow` view shows what the tape *executed* (action).

A bin can be resting-ask-heavy while the tape buys through it — the two views
disagreeing is information, not a bug. Reading flow as resting (or vice versa)
is exactly the error the separate channels exist to prevent.
