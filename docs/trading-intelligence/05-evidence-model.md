# 05 — Evidence Model

`Evidence` is the atomic unit every decision layer reasons over: a single,
sourced, confidence-weighted claim about an instrument ("RSI is 72, overbought"
/ "price closed above the 50-day SMA"). It is the seam between *raw data* and
*judgement* — a claim is only as trustworthy as the data and the reasoning that
produced it, and the model carries both.

## Shape

```python
Evidence(
    instrument_key: str,
    type: EvidenceType,        # the category of claim
    assertion: Assertion,      # HOW the claim was arrived at
    direction: Direction,      # the lean it supports
    detail: str,               # human-readable justification
    weight: float,             # 0..1 strength of THIS piece (clamped) -- NOT a probability
    confidence: Confidence,    # LOW/MEDIUM/HIGH qualitative band
    provenance: Provenance,    # where the underlying data came from
    quality: DataQuality,      # staleness/partiality/validity read
    data: dict,                # raw supporting payload (e.g. the indicator value)
    id: str,                   # content-addressed -- same claim -> same id
)
```

## EvidenceType — what kind of claim

`TECHNICAL`, `MARKET_STRUCTURE`, `TREND`, `MOMENTUM`, `VOLUME`, `VOLATILITY`,
`MARKET_CONTEXT`, `REGIME`, `NEWS`, `FUNDAMENTAL`, `SENTIMENT`, `OPTIONS`,
`CATALYST`, `ANOMALY`, `HISTORICAL`, `VISUAL`, `CHART`, `MACRO`, `ICT`.

The populated set today covers every layer the pipeline produces — technicals,
structure, volume, momentum, volatility, regime, news/sentiment, fundamentals,
macro/event calendar, market-context (relative strength), anomaly, ICT. A few
types (`OPTIONS`, `CATALYST`, `VISUAL`, `CHART`, `HISTORICAL`) are reserved for
future layers so the schema stays stable.

## Assertion — the epistemic status

This is what separates measurement from inference (CLAUDE.md §56):

| Assertion | Meaning | Example |
|---|---|---|
| `OBSERVED` | directly read from data | "volume this bar is 2M" |
| `CALCULATED` | derived arithmetic | "RSI is 72", "RR is 2.1" |
| `DETECTED` | a pattern/condition found | "BOS above prior swing high", "sentiment up" |
| `INFERRED` | an interpretation | a regime implication |
| `UNCERTAIN` | a claim under weak basis | a thin-data read |

`is_reliable` requires `quality.usable` ∧ `not provenance.is_mock` ∧ assertion ∈
{OBSERVED, CALCULATED, DETECTED} — an `INFERRED`/`UNCERTAIN` claim, or one on
mock/stale data, can never drive a signal.

## Traceability

Every evidence item is traceable to: its **source** (`provenance.source` +
`tier`), a **timestamp** (`created_at` + the observation's bar time in `data`),
the **observation/feature** it was computed from (`detail` + `data`), its
**direction/contribution** (`direction` + `weight`), and a **strength**
(`weight` + `confidence`). The content-addressed `id` means the same structural
fact re-derived is the *same* evidence — so a prediction and its supporting
claims stay auditable across runs without a database round-trip.

## In the pipeline

- `EvidenceService` fuses technical/structure reads into evidence tuples on the
  `TradingAnalysis`.
- Advisory layers (news, calendar, fundamentals, relative-strength, anomaly)
  each emit their own soft-capped evidence — a `weight` cap keeps a soft source
  below the technical layer.
- The `CriticService` reads evidence *counts and agreement*, never the raw
  technical internals — so a soft/advisory claim can support but never dominate
  a decision.
- `NO_TRADE` is a first-class outcome: when reliable evidence is absent, the
  honest product is "insufficient evidence," not a fabricated signal.
