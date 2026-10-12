# 07 — Future Memory Integration

Memory is **not** part of this phase and Trading Intelligence does **not**
depend on it. The trading core runs fully with Memory disabled. What this
document defines is the clean, one-directional extension seam a future Memory
subsystem plugs into — so it can consume intelligence without the trading core
ever importing it.

## The seam

```
Trading Intelligence services
        │  (publish on the shared EventBus)
        ▼
Intelligence Events   --  the ONLY coupling point
        │
        ▼
Future Memory Adapter  (subscribes; trading code never calls it)
        │
        ▼
Memory subsystem (episodes, retrieval, learning) -- deferred
```

The contract is the **event vocabulary in `trading/events.py`** plus the
**content-addressed IDs on the domain objects**. A Memory adapter subscribes to
the bus and keys its records on the stable ids; the trading core never imports
Memory, never calls it, and is unaware it exists. Removing the adapter changes
nothing upstream.

## What Memory may later consume

Events already carry everything needed to reconstruct context, each with
provenance (`source_tier`) and an honesty flag (`is_mock` / `is_reliable`) so a
synthetic or unvalidated record can never be stored as a real track record:

- **`PredictionCreated`** → the §8 `PredictionRecord` (id, instrument, horizon,
  direction, probability-when-reliable, risk, model version) — the prediction
  history Memory would index.
- **`PredictionResolved`** / **`PredictionPerformanceEvaluated`** → outcomes and
  aggregate calibration (accuracy, brier, ece) — the "was it right?" and "is it
  calibrated?" signals Memory would learn from.
- **`MarketDataReceived`** / **`CandleClosed`** / **`OrderBookUpdated`** /
  **`TradeReceived`** → the raw observations for episodic market state.
- **`AnalysisCompleted`** / **`MarketRegimeDetected`** / **`FeatureUpdated`** →
  the analytical context (regime, fused direction, feature shape) behind a call.
- **`SignalGenerated`** / **`SignalCritiqued`** / **`TradingReportGenerated`** →
  the proposal, the adversarial verdict, and the final report.
- **`Evidence`** content ids → cross-referencing which claims supported which
  predictions.
- User corrections / strategy performance → stored under the same stable ids.

## The boundary rules (must hold)

1. **No direct dependency.** `src/aetheros/trading/` must never import
   `src/aetheros/memory/`. Coupling is events + ids only.
2. **Works with Memory off.** Every event is best-effort; an absent subscriber
   changes nothing (the services already swallow publish failures).
3. **Honesty travels with the record.** `is_mock`/`is_reliable`/`source_tier`
   are surfaced on every event so a MOCK or unvalidated record can never be
   persisted as a real edge — this is a structural guarantee, not a convention.
4. **Predictions are not facts.** A `PredictionRecord` keeps `recommendation`,
   `is_actionable`, and `is_mock` verbatim — Memory must store it as a
   *prediction*, never upgrade it to a fact (§15).

## What Memory unblocks (deferred, not built)

- **`MarketRegimeChanged` emission** — the contract exists but needs prior-regime
  state; the stateless `RegimeService` holds none. A Memory-backed "last regime"
  store is the honest producer.
- **A durable `PredictionStore`** — the port exists (`PredictionStore` ABC +
  `InMemoryPredictionStore`); a file/db impl behind the same interface survives
  restart.
- **The autonomous monitoring loop** — fetch outstanding records →
  `PredictionEvaluator.resolve_latest` → `PredictionPerformanceService.summarize`
  over time. The primitives exist; the scheduler + durable outcome store await
  Memory.
- **Learning / threshold adaptation** — calibrated-threshold or regime-conditional
  tuning from accumulated outcomes (§29 "Evaluate → Learn").

## Remaining Phase-2 work (not started)

- A real (non-mock) fundamentals/news/calendar provider beyond Yahoo/ccxt.
- The LLM-driven CEO agent narrating on top of the deterministic orchestrator
  (never replacing its calculations).
- The durable store + monitoring loop + regime-transition producer above.
- `OPTIONS`/`CATALYST`/`VISUAL`/`CHART` evidence layers (reserved in the enum).
