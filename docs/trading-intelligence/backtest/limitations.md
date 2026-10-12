# Backtesting — Limitations & Interpretation

How to read a backtest honestly — and where its numbers can mislead.

## What a backtest does NOT prove

- **Past is not a guarantee.** A high historical accuracy is an observation
  about the replayed window, never a promise about the next trade. Regimes
  change; a model tuned to the past can fail in a different market.
- **The pipeline measures the *given* assess_fn.** Its results are only as
  good as the production composition wired in — a weak signal reads as weak,
  and a backtest can't rescue it.
- **Sample size rules everything.** `is_reliable = False` on a thin or mock
  sample is a real statement: don't read meaning into an aggregate over a
  handful of outcomes or a mock-resolved batch.

## Interpretation guard-rails

- **Excursions are realised-path, not limit-order fills.** `max_favorable` /
  `max_adverse` excursions measure how far the move ran for/against the call —
  they do *not* mean a trade at those prices would have filled.
- **`target_hit`/`invalidation_hit` are trade-through, not fill.** A bar's
  high/low reaching a level is a trade-through; whether a real order would
  have filled there is an execution question, not measured here.
- **Profit factor `inf` means no losses** — a sign of a tiny or lucky sample,
  not a real edge. Check `scored`/`min_sample` before trusting it.
- **Liquidity rates need the context.** The `sweep:`/`absorbed`/`replenished`/
  `persistent` rates only populate where the outcome carried that liquidity
  context; they're `None` on a candle-only backtest — honest "not measured",
  not zero.

## Survivorship / selection caveats

- A single-instrument, single-series backtest measures *that* series. It does
  not control for survivorship bias (testing only on instruments that
  survived) or for regime selection.
- Multiple metric reads over the same window invite multiple-comparison bias;
  the metrics are reported together so the reader can weigh them, not cherry-
  pick one.

## What IS reliable to trust

- **The mechanism is honest**: no look-ahead (structurally), deterministic,
  production components only, explicit PENDING/UNRESOLVABLE/thin/MOCK gates.
- **The metrics are honest**: `None` where not measurable, `is_reliable`
  gated, limitations surfaced — never a fabricated edge.

A backtest is the system's account of how it *would have* performed — read it
as evidence about the components, not as a forecast.
