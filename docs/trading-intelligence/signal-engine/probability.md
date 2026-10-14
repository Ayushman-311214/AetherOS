# Signal Engine — Probability & Confidence Semantics

What `probability` and `confidence` mean, and why they are kept apart.

## Probability — an estimate, not a guarantee

`probability_up` is the calibrated estimate of P(up) for the fused direction,
produced by the quant layer (`ProbabilityEstimate` — logistic + Platt
calibration, out-of-sample validated) and surfaced **verbatim only when
`is_reliable`**. When the estimate isn't reliable or isn't wired, the field is
`None`.

- It is **bounded** (0..1) and **conditional** — "the model estimates X under
  the stated conditions".
- It is **never a raw score dressed up as a probability.** `raw_evidence_score`
  and `model_score` are *inputs/computations*; they are never back-filled into
  `probability_up` to fake a calibrated number. When there's no reliable
  estimate the assessment honestly shows `probability: null` and a limitation
  names why.
- `has_calibrated_probability` tells a consumer whether a real estimate exists.

## The four quantities, and what each is *not*

| Field | What it is | What it is NOT |
|---|---|---|
| `raw_evidence_score` | weighted net of the evidence ledger, −1..1 | a probability |
| `model_score` | the score a downstream model produced | a probability |
| `probability_up` | calibrated P(up) when reliable, else `None` | a guarantee or a score |
| `confidence` | qualitative band from evidence quality | a probability |

## Confidence — a band, not a probability

`confidence` is LOW / MEDIUM / HIGH, derived from *how much trustworthy
evidence stood behind the read*:

```
score = 0.4·coverage + 0.4·agreement + 0.2·min(1, reliable/4)
HIGH   if score ≥ 0.70 and reliable ≥ 2
MEDIUM if score ≥ 0.40 and reliable ≥ 1
LOW    otherwise (or no direction / no reliable evidence)
```

- It measures **evidence quality** — how many reliable sources agreed, how
  much of the expected evidence arrived, and how much the directional weight
  agreed — *not* how likely the move is.
- A thin or contradictory read is low-confidence **even if its probability
  looks strong** — a calibrated 0.8 on a thin or mock dataset stays honest.

## The calibration assumption, stated

The spec forbids "converting an arbitrary score into a fake probability
without documenting calibration assumptions". The rule here: **probability
comes only from the calibrated quant layer** (`ProbabilityEstimate`), which
itself trains a model, calibrates on a holdout slice and gates on an
out-of-sample edge. Until a calibrated estimate is wired and reliable, the
engine reports `None` and only the raw/model scores exist — the architecture
is *prepared* for calibration, and it is explicit that a raw score is not yet
a probability.
