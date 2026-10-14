# 02 — Domain Models

All domain objects are `@dataclass(frozen=True, slots=True)`, immutable, and
serialisable via `to_dict()`. Validation lives in `__post_init__` — a malformed
object cannot be constructed. IDs are content-addressed (SHA-1 over the
identity-relevant fields), so the same claim re-derived yields the same id.

## Identity & market data

- **`Instrument`** — `symbol`, `exchange?`, `asset_class`, `name?`.
  `key` = `EXCHANGE:SYMBOL` (or `SYMBOL`). `parse("NASDAQ:AAPL")` / `parse("AAPL")`.
- **`Candle`** — `timestamp` (tz-aware, normalised to UTC), `open`/`high`/`low`/
  `close`/`volume`. Rejects naive timestamps, non-finite values, `high < max(o,l,c)`,
  `low > min(...)`, negative volume.
- **`Quote`** — latest price + optional bid/ask/volume/change_pct + provenance.
- **`MarketData`** — the canonical series: `instrument`, `timeframe`, `candles`,
  `provenance`, `quality`. Vectorised views (`closes()`, `highs()`, …) plus
  `window(start, end)` — the single place the past-only slicing guarantee lives.

## Microstructure

- **`OrderBookLevel`** — `price`, `amount`, `count` (all validated).
- **`OrderBook`** — `bids`/`asks` best-first; rejects unsorted sides and crossed
  books. `best_bid`/`best_ask`/`mid_price`/`spread`.
- **`TradeTick`** — `price`, `amount`, `side` (UP=buy, DOWN=sell aggressor),
  `timestamp`, optional `tick_id`, `provenance`.

## Analysis objects

- **`Evidence`** — a sourced weighted claim. `EvidenceType`, `Assertion`,
  `direction`, `detail`, `weight ∈ [0,1]` (clamped), `confidence`, `provenance`,
  `quality`, content `id`. `is_reliable` = usable ∧ non-mock ∧ OBSERVED/
  CALCULATED/DETECTED.
- **`TechnicalSnapshot`** — indicator readings (MACD, Bollinger, SuperTrend, …).
- **`MarketStructure`** — swings, levels, `StructureSignal`.
- **`TradingAnalysis`** — the deterministic situation report: direction +
  `directional_score` + `confidence` + technical + structure + evidence +
  quality + limitations. `is_actionable` requires usable, non-mock, directional,
  with evidence.

## Signal, risk, prediction

- **`SignalCandidate`** — `direction` (UP/DOWN only; no-signal is `signal=None`),
  `signal: TradeSignal?`, `risk`, `critique`, `setup?`, `rejections`, `candidate_id`.
- **`SignalEvaluation`** — all candidates + the fired subset + `consensus`
  (UNKNOWN on mixed sides — disagreement surfaced, never averaged away).
- **`RiskAssessment`** — entry, structural/projected stop + target,
  `risk_reward_ratio`, `overall_risk` band, position sizing, `invalidation`.
- **`ProbabilityEstimate`** — `p_up`/`p_down` (calibrated), `raw_p_up`, model +
  calibration id, `feature_names`, `train_metrics`/`holdout_metrics`,
  `baseline_brier`, `is_reliable`. The §3 "estimate, never guarantee" made real.
- **`PredictionRecord`** — the §8 contract flattened from a `TradingReport`:
  instrument, `created_at`, `horizon_bars`, direction, confidence, probability
  (only when `is_reliable`), risk geometry + invalidation, `source_tier`/`is_mock`,
  `model_pipeline`, `evidence_count`. `from_report`/`to_dict`/`from_dict`.
- **`PredictionOutcome`** — `status` (PENDING/RESOLVED/UNRESOLVABLE),
  `predicted_direction`/`realized_direction`, `is_correct` (None for a
  non-directional call), `realized_return`, `brier_contribution`, `is_reliable`.
- **`PredictionPerformance`** — aggregate accuracy/coverage/mean-return +
  `CalibrationReport`, `is_reliable` gated on sample size ∧ non-mock.

## Enums (all `str, Enum` for JSON)

`Direction`, `TrendState`, `MarketRegime`, `MarketPosture`, `TimeframeAlignment`,
`Confidence`, `RiskBand`, `EvidenceType`, `SourceTier`, `DataQualityStatus`,
`Assertion`, `CheckStatus`, `CriticVerdict`, `ReportRecommendation`,
`PredictionOutcomeStatus`, `TradeAction`, `OrderType`/`OrderStatus`,
`PositionStatus`, `StrategyCategory`, `StructureSignalType`/`StructureBreakType`,
`SMCZoneKind`, `LiquidityEventKind`/`LiquidityPoolKind`, `SessionName`,
`KillZoneName`, `ICTConcept`, `AMDPhase`, `SessionModelKind`,
`OptimizationObjective`, `Timeframe` (with `seconds`, `label`, `parse`).
