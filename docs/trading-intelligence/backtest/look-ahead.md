# Backtesting — Data Leakage Prevention

The structural guarantee that a backtest can't see the future.

## The single slicing primitive

`MarketData.window(start, end)` is the one place the codebase defines the
past-only contract: a half-open `[start, end)` slice carrying the same
provenance/quality, bounds-checked so a slice off the end is a loud error.
The backtester, the walk-forward folds and the live replay *all* go through it
— there is no second, leakier path.

At step `i` the pipeline hands the assess function `data.window(0, i + 1)`:
the bar at index `i` and every bar before it. Nothing after `i` is ever in the
window, so the prediction cannot encode future information.

## Where leaks would come from (and how each is closed)

| Leak vector | Closed by |
|---|---|
| The prediction sees a future bar | `window(0, i+1)` — the window ends at `i` |
| The prediction is timestamped "now" | `created_at` = the window's last bar, not wall clock |
| An indicator reads ahead | indicators are causal (`out[t]` uses inputs `≤ t`) |
| The evaluator feeds the prediction | the evaluator reads `data` *after* the prediction is made; the prediction is already immutable |
| A separate "backtest engine" drifts | the pipeline composes the production `assess_fn`, no second implementation |

## The spy test

`test_pipeline_no_lookahead_each_step_only_sees_past` hands the pipeline an
`assess_fn` that records every window it's given. It asserts each window's
`count` equals the step's index + 1 and its `last_price` is *that bar's* close
— proving the assess fn saw no bar beyond the step.

## What "no look-ahead" does NOT mean

- The **evaluator** legitimately reads bars after the prediction — that's the
  *measurement*, not the *prediction*. The no-look-ahead rule is about what
  the prediction saw, and the two are strictly separated.
- A `PENDING` outcome (horizon not yet elapsed in the data) is honest "too
  early to judge", not a resolved call.

## Reproducibility

`test_pipeline_deterministic` replays the same series twice and asserts
identical prediction ids and identical metrics — the pipeline is a pure
function of the input stream, so a backtest is fully reproducible.
