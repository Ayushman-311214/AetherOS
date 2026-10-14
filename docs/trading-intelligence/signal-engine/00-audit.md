# Phase 5 Audit — Signal, Probability, Risk & Explanation Engine

What Phase 5 added, what it reused, and how the engine produces an explainable
probabilistic assessment — never a claim of certainty.

## Reused (not rebuilt)

- **`Evidence`** (`domain/evidence.py`) — the sourced, weighted, content-id'd
  claim. The engine aggregates these verbatim; it does not redefine evidence.
- **`TradingAnalysis`** + its evidence tuple — the core fused read.
- **`ProbabilityEstimate`** (quant layer) — the calibrated P(up), surfaced
  verbatim and only when `is_reliable`.
- **`RiskAssessment`** (risk engine) — entry, ATR/structural stop, targets,
  R:R, invalidation, volatility risk band.
- **`MarketFeatures` / `LiquidityFeatures` / `HeatmapCell`** — the Phase 2-4
  feature vectors, converted to evidence items.
- **Existing `Explanation`/`ExplanationService`, `CriticService`,
  `SignalService`** — the broader signal pipeline stays intact; this layer is
  the *evidence-aggregation + assessment* front-end feeding it.

## New (`trading/signal_engine/`)

| Module | Contents |
|---|---|
| `evidence.py` | `EvidenceLedger` — items + `MissingSource` accounting + supporting/opposing split + coverage |
| `scoring.py` | `ScoreBreakdown` + `compute_scores` — raw/model/probability/confidence honestly separated |
| `features.py` | `features_to_evidence` — feature vectors → `Evidence` items + missing-source records |
| `assessment.py` | `SignalAssessment` — the full explainable output |
| `service.py` | `SignalEngineService` — aggregation → scoring → risk → assessment |

Wired `SignalEngineService` into `bootstrapper._bootstrap_trading`.

## The honesty contract (what makes this Phase 5)

- **Four quantities, honestly separated.** `raw_evidence_score` (weighted net,
  -1..1), `model_score`, `probability_up` (calibrated, None when not reliable),
  `confidence` (qualitative band). A raw score is never dressed up as a
  calibrated probability — when the quant layer isn't reliable, probability is
  `None` and a limitation says so.
- **Missing data is explicit.** Each absent source is a `MissingSource` with a
  reason, counting toward `coverage` — never a silent neutral vote.
- **Contradictions are never hidden.** `supporting` and `contradicting` are
  both carried; agreement is a scored input to confidence.
- **No false precision.** Without the risk engine there's no entry/targets/RR
  — honest `None`/`()` and an "invalidation not computed" string.
- **The LLM is never a number source.** Everything is deterministic.

## Tests

`tests/trading/test_signal_engine.py` — 17 tests: ledger aggregation,
contradiction split, unreliable-item gating, missing-source accounting,
coverage, score separation, probability boundary (only-when-reliable),
confidence on thin/contradictory evidence, feature-to-evidence conversion,
assessment shape/determinism/mock-honesty/no-false-precision.

## Remaining Phase 6 work

- A calibrated model behind `model_score`/`probability_up` (the architecture is
  ready; the current quant layer already supplies `p_up` when wired).
- Wire `SignalAssessment` into the orchestrator/CLI as an alternate, richer
  explanation surface alongside `TradingReport`.
- Tool/CLI surface for the engine.
