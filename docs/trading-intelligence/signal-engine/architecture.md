# Signal Engine — Architecture

`src/aetheros/trading/signal_engine/` — the layer that turns observations and
features into an explainable probabilistic assessment. It is the *aggregation
and assessment* front-end; it feeds (never replaces) the existing
`SignalService`/`CriticService`/risk pipeline.

## Module map

```
signal_engine/
  evidence.py    EvidenceLedger + MissingSource
  scoring.py     ScoreBreakdown + compute_scores
  features.py    features_to_evidence (feature vectors -> Evidence)
  assessment.py  SignalAssessment
  service.py     SignalEngineService
```

## Flow

```
TradingAnalysis (fused read + core Evidence)
        +
MarketFeatures / LiquidityFeatures / HeatmapCells   (optional feature reads)
        │
        ▼
features_to_evidence  -- each feature becomes a traceable Evidence item;
        │                absent sources -> MissingSource records
        ▼
EvidenceLedger  -- items + missing + supporting/opposing split + coverage
        │
        ├──> compute_scores -> ScoreBreakdown
        │       raw_evidence_score / model_score / probability / confidence
        │
        ├──> RiskAssessment  (deterministic risk engine, when wired)
        ├──> ProbabilityEstimate (calibrated quant layer, when wired+reliable)
        ▼
SignalAssessment -- direction, probability, confidence, expected_move,
                    time_horizon, R:R, entry, invalidation, targets, risk_band,
                    supporting, contradicting, risk_factors, missing_sources,
                    coverage, is_actionable, limitations
```

## The four quantities, kept separate

`ScoreBreakdown` is the honest separation the spec requires:

- **`raw_evidence_score`** (`[-1,1]`) — the weighted net of the ledger
  (`net_weight / _NET_WEIGHT_SCALE`). Aggregation only — NOT a probability.
- **`model_score`** — what a downstream model produces (currently a
  pass-through of the raw score, a distinct field so a calibrated model can
  slot in behind the same contract).
- **`probability_up`** — the calibrated estimate, surfaced **verbatim** from
  the quant layer's `ProbabilityEstimate` and only when `is_reliable`; `None`
  otherwise. Never a raw score back-filled into a fake probability.
- **`confidence`** — a qualitative LOW/MEDIUM/HIGH band from `0.4·coverage +
  0.4·agreement + 0.2·reliability`, NOT the probability. A thin or
  contradictory read is low-confidence even when the lean looks strong.

## Missing data

`MissingSource(source, reason)` records each absent input (an `EvidenceType`
or a feature-layer name). It counts toward `coverage` and is listed in the
assessment — the ledger never folds a missing source in as a neutral vote and
never drops it silently.

## Contradictions

`EvidenceLedger.supporting` / `.opposing` split reliable directional evidence
relative to the fused direction. Both are carried on the assessment —
`supporting` and `contradicting` are surfaced side by side, and `agreement`
(the share of directional weight agreeing) feeds confidence.

## Boundaries

- **No decisions.** A `SignalAssessment` is a probabilistic *assessment*, not
  a verdict — `is_actionable` needs reliable, agreeing, actionable evidence.
- **No LLM numbers.** Everything is deterministic/programmatic.
- **Composable.** `risk`/`probability`/feature reads are injectable; a missing
  one is a `MissingSource`, not an error.
- **Deterministic.** The ledger, scores and assessment are pure functions of
  the inputs; identical input → identical output (minus wall-clock stamps).
