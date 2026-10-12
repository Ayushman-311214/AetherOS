# Market Intelligence — Price Action & Structure

Deterministic reads of *how price is behaving* — structure (HH/HL/LH/LL, trend,
range, breakout) and the price-action behaviours the structure read doesn't
already cover.

## Market structure (reused `MarketStructureService`)

Already implemented; reused, not rebuilt:

- **Swing pivots** — a high at index `i` is a swing high only if it's the max
  of `pivot_window` bars either side. This is the multi-candle rule: a swing is
  only *knowable* `pivot_window` bars later, so the detector can't see a pivot
  before it's confirmed (no look-ahead).
- **HH / HL / LH / LL** — `higher_highs`, `higher_lows`, `lower_highs`,
  `lower_lows` from the last two swing highs/lows.
- **Trend / range** — `TrendState` from swing-pattern votes + a short-vs-long
  close-mean slope.
- **Breakout / breakdown / range** — `StructureSignal`s at support/resistance
  levels clustered from the pivots.
- **Structure break / CHoCH** — the SMC layer (`StructureBreak` BOS/CHoCH)
  already provides the deeper market-structure-shift read; this layer doesn't
  duplicate it.

## Price action (new `PriceActionService`)

Behaviours for the latest bar(s), each requiring its confirmation:

- **Breakout** — close beyond the prior-`lookback`-bar high/low.
- **Failed breakout** — a close beyond the extreme that closed *back inside*
  within `_FAIL_WINDOW` (3) bars. Evidence of a trap, not a reversal verdict.
- **Acceptance** — held beyond a level across `min_confirm_bars` closes (the
  multi-candle rule: a single poke is not acceptance).
- **Rejection** — a bar whose dominant wick ≥ `_REJECTION_WICK_BODY`× its body
  (long upper wick = upside rejection, lower = downside).
- **Momentum** — successive higher/lower closes.
- **Range** — price oscillating inside the prior range.
- **Volatility state** — realised vol vs its own baseline: `expanding` /
  `contracting` / `steady` (ratio threshold `_VOL_RATIO` = 1.25).

## The multi-candle rule

The spec is explicit: a single candle is not sufficient evidence for complex
structure unless configured. `min_confirm_bars` (default 2) is that bar —
breakout/acceptance/failed-breakout all need it; dropping it to 1 is an
explicit single-bar opt-in.

## Honesty

`PriceActionAnalysis` carries `kind`, `direction`, `confidence`,
`volatility_state`, `momentum`, `reference_price`, `last_close`, `observation`
and `limitations` — descriptive labels with the supporting numbers, never a
"what happens next" call. Thin data → `UNKNOWN`.
