# Signal Engine — Limitations

The honest bounds on what the engine can and cannot claim.

## Probability is an estimate, not a guarantee

- `probability_up` is conditional on the quant layer being wired *and* its
  estimate passing an out-of-sample edge gate. When it's `None`, only
  `raw_evidence_score`/`model_score` exist — a raw aggregate is **not** a
  probability and is never presented as one.
- Even a reliable calibrated estimate is "the model's read under the stated
  conditions", never a promise the move will happen.

## Confidence is a band, not a probability

`confidence` (LOW/MEDIUM/HIGH) reflects *how much trustworthy evidence*
supported the read — not how likely the move is. A thin or contradictory read
is low-confidence even when the lean looks strong.

## Missing data degrades, never defaults

Each absent source is a `MissingSource` counting toward `coverage`. An engine
run on few sources is honestly thin — `coverage` is low and `confidence` drops.
This is deliberate: the engine never silently treats "no news feed" as
"neutral news", and never treats "no liquidity read" as "no liquidity signal".

## Estimated inputs carry their own honesty flags

- **Buy/sell volume** (from `MarketFeatures`) is a bar-geometry *estimate*
  (CLV), not a real aggressor split — a real tape feed takes precedence.
- **`is_mock`** propagates to `is_actionable = False` — a synthetic read can
  never produce an actionable signal.

## What is NOT covered

- **Regime transitions mid-assessment** — the engine reads the regime *as
  classified*; a `TRANSITION` regime is reported as the honest
  between-regimes state, not smoothed into a confident label.
- **Order/tape-level fills** — the assessment assumes a market-order fill at
  `entry`; slippage/queue position is a later execution concern.
- **Learning** — no calibration feedback or threshold adaptation (deferred
  Memory layer); `model_score` is currently a pass-through pending a wired
  calibrated model.

## The structural guarantees

- **No decisions** — a `SignalAssessment` is a probabilistic assessment;
  `is_actionable` requires reliable, agreeing, actionable evidence.
- **No hidden contradictions** — both sides are always carried.
- **No LLM numbers** — the LLM narrates the structure, never produces it.
- **Deterministic** — identical inputs produce identical assessments.
