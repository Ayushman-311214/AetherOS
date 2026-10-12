# Liquidity — Replenishment

Replenishment is resting liquidity repeatedly reappearing at a level *after*
being consumed. It is the signature of persistent, sticky interest — evidence
that a wall is real rather than a one-off flash.

## Why it matters

A single big order that gets eaten and never refills is weak evidence — anyone
can show a wall once. A level that keeps refilling after the tape eats it is a
different animal: the interest behind it is persistent, and persistent interest
is what makes a zone worth tracking. The spec is explicit that this may indicate
stronger interest — evidence, not a guarantee.

## How it is tracked (`ZoneTracker`)

The tracker's lifecycle is what makes replenishment observable:

1. When a zone is swept (acceptance), the tracker arms `was_swept` on that zone.
2. On a later step where the cluster is re-detected at the same band with
   resting liquidity back ≥ `REPLENISH_FRACTION` (0.5) of its reference size,
   the tracker counts a replenishment (`replenishment_count` up) and emits
   `LiquidityReplenished`.
3. `was_swept` clears so the next refill is counted separately — each genuine
   refill cycle is recorded, not just "big again once".

`reference_liquidity` is the largest size the zone has ever shown, so "refilled"
is judged against its own peak, not an absolute figure.

## Scoring (`analyze_replenishment`)

`score = 0.5 × refill_ratio + 0.5 × count_factor`, capped at 1.0:

- `refill_ratio = reappeared_volume / consumed_volume` — how much of what was
  eaten came back.
- `count_factor = min(1, replenishment_count / 3)` — repeated refill counts more
  than a single bounce.

Both halves are named, bounded and documented — no magic weight is hidden.

## Honesty

A `LiquidityReplenished` event reports *that* liquidity reappeared and how much —
never that it will keep reappearing, or that the interest is genuine (resting
liquidity can be re-placed as easily as placed). It is a fact about the stream,
weighed alongside persistence and sweep history by whatever consumes it.
