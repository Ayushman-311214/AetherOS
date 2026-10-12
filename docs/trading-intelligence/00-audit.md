# Phase 1 Audit — Trading Intelligence Foundation

**Status:** reconciliation audit. The canonical Trading Intelligence foundation
the Phase-1 brief describes is **already built** across ~32 prior increments.
This audit records what exists, what was reused vs. added, and the one small
genuine gap (granular streaming event contracts) that Phase 1 closed.

This document exists because the brief requires a read-only audit *before*
implementation — and the honest finding is that the foundation is done, so the
correct scope is verify + document + fill real gaps, **not** rebuild.

## 1. What already exists

The whole deterministic, LLM-free trading core under `src/aetheros/trading/`:

```
trading/
  domain/        ~40 frozen/slots value objects, all to_dict()-serialisable
  providers/     MarketDataProvider ABC + Yahoo (real), ccxt (real, crypto),
                 mock (SourceTier.MOCK), plus news/calendar/fundamentals ABCs
  services/      ~40 deterministic services (the pipeline stages)
  quant/         numpy-only logistic model + Platt calibration + causal features
  indicators/    vectorised SMA/EMA/RSI/MACD/ATR/ADX/Bollinger/...
  strategies/    strategy panels -> StrategySetup -> SignalCandidate
  backtesting/   walk-forward + metrics + comparison (look-ahead-safe)
  brokers/       paper venue + price source (the only write path to "orders")
  execution/     execution engine (signal -> policy -> risk -> broker)
  events.py      trading-domain events on the shared runtime EventBus
```

The pipeline the brief specifies is implemented end to end:

```
market data -> technical -> structure -> liquidity -> news/sentiment ->
calendar -> fundamentals -> regime -> relative-strength -> anomaly ->
quant features -> probability+Platt calibration -> risk -> walk-forward
backtest -> critic -> TradingReport -> PredictionRecord -> PredictionOutcome
-> PredictionPerformance
```

## 2. Canonical concept → existing model

| Brief concept | Existing model | Location |
|---|---|---|
| Instrument | `Instrument` (`key`, `exchange`, `asset_class`, `parse`) | `domain/instrument.py` |
| Candle | `Candle` (tz-aware UTC, OHLC+finite validated) | `domain/market_data.py` |
| Trade | `TradeTick` (price/amount/aggressor `side`) + `Order`/`Position`/`TradeSignal` | `domain/order_book.py`, `domain/trade.py` |
| OrderBookLevel | `OrderBookLevel` (price/amount/count, positive-validated) | `domain/order_book.py` |
| OrderBookSnapshot | `OrderBook` (bids/asks best-first, crossed-book rejected, `mid_price`/`spread`) | `domain/order_book.py` |
| MarketObservation | `MarketData` (series + `Provenance` + `DataQuality`) | `domain/market_data.py` |
| MarketRegime | `MarketRegime` enum + `RegimeAnalysis` | `domain/enums.py`, `domain/regime.py` |
| MarketFeature | `FeatureMatrix` (8 causal features + label + `latest` live row) | `quant/features.py` |
| TradingSignal | `SignalCandidate` / `SignalEvaluation` / `TradeSignal` | `domain/signal.py`, `domain/trade.py` |
| Prediction | `PredictionRecord` (full §8 contract, content-addressed id) | `domain/prediction.py` |
| PredictionOutcome | `PredictionOutcome` (PENDING/RESOLVED/UNRESOLVABLE) | `domain/outcome.py` |
| Evidence | `Evidence` (type/assertion/direction/weight/provenance/content id) | `domain/evidence.py` |
| RiskAssessment | `RiskAssessment` (entry/stop/target/R:R/band/invalidation) | `domain/risk.py` |
| SignalDirection | `Direction` enum (UP/DOWN/SIDEWAYS/UNKNOWN) | `domain/enums.py` |
| Confidence | `Confidence` band (LOW/MEDIUM/HIGH — never a probability) | `domain/enums.py` |
| Probability | `ProbabilityEstimate` (calibrated `p_up`/`p_down` + `is_reliable`) | `domain/probability.py` |

## 3. Signal model — meets the "not just BUY/SELL" rule

`SignalCandidate` carries direction, an optional `TradeSignal` (None = an
explicit, recorded no-signal), a full `RiskAssessment`, the `CriticReport`
verdict trail, the `StrategySetup` reading it came from, `rejections`,
provenance/quality/limitations, and a content-addressed `candidate_id`. A
signal is a *proposal with a verdict trail*, never an order — there is no order
construction or quantity in this layer (enforced by construction).

Probability is `ProbabilityEstimate` — a calibrated `p_up`/`p_down` gated by an
out-of-sample edge check, never a bare confidence number. `Confidence` is a
separate qualitative band. The two are never conflated.

## 4. Evidence model

`Evidence` is the atomic sourced claim: `EvidenceType` (market_structure,
liquidity, volume, momentum, technical, fundamental, news, sentiment, regime,
volatility, anomaly, macro, ict, market_context, …) + `Assertion`
(OBSERVED/CALCULATED/DETECTED/INFERRED/UNCERTAIN) + direction + `weight` +
`Confidence` + `Provenance` + `DataQuality` + a content-addressed `id` +
`is_reliable` (usable ∧ non-mock ∧ at-least-calculated). Traceable to source and
observation, exactly as the brief requires.

## 5. Event architecture — one bus, no duplication

- **Single `EventBus`**: `runtime/events/event_bus.py`. All trading services
  resolve it from the DI container; ~19 trading-domain `Event` subclasses live
  in `trading/events.py`. There is **no second EventBus**.
- One wrinkle reconciled: `runtime/events/publisher.py` holds a module-level
  `set_event_bus`/`get_event_bus` global. The bootstrapper wires it to the
  *same* instance registered in the container (`bootstrapper.py` ~line 284), so
  both access paths resolve to one bus — not two.
- `agents/tasks/manager.py` calls an `emit()`-style bus — that is a pre-existing
  test failure in the tasks suite (recorded separately), unrelated to trading.

## 6. The genuine gap Phase 1 closed

The canonical *granular streaming* event vocabulary did not exist: there was no
`MarketDataReceived`, `CandleClosed`, `OrderBookUpdated`, `TradeReceived`,
`MarketRegimeChanged`, or `FeatureUpdated`. Because the system is pull-based
(not a live tick feed), these were added honestly — emitted only from the points
where the system genuinely gains the information:

- `MarketDataReceived` + `CandleClosed` — `MarketDataService.get_candles`,
  on a *fresh* (non-cached) snapshot. One `CandleClosed` for the newest bar.
- `OrderBookUpdated` / `TradeReceived` — new `MicrostructureService`, fetching
  via the provider's existing `get_order_book` / `get_recent_trades`.
- `FeatureUpdated` — `ProbabilityService.estimate`, when its matrix recomputes.
- `MarketRegimeChanged` — the transition contract (previous + new regime). Its
  honest producer needs prior-regime state, which the stateless detector does
  not hold — so it is a contract awaiting the deferred memory/state layer, not
  a fabricated emission.

`CandleUpdated` was deliberately **not** added: a still-forming bar does not
exist in a pull-based snapshot model, and inventing it would pretend a
granularity the data does not have.

## 7. Architectural boundary

The layering the brief mandates holds: `domain` (pure) → `providers` (interface
+ impls) → `services` → `tools`/`ToolRegistry` → agents/CLI. Domain logic has no
I/O, no LLM, no rendering dependency. `MicrostructureService` follows the same
interface→provider→service shape as `MarketDataService`.

## 8. Pre-existing test failures (recorded, not caused by this work)

A working-tree circular import between `brokers/paper_provider.py` and
`services/simulation_service.py` breaks `test_execution.py`,
`test_simulation.py`, `test_simulation_service.py`, and a few dependent suites
(≈13 failures in tests/trading + tests/cli). These pre-date this change — they
exist in the uncommitted tree and are unrelated to the streaming events added
here. The `tasks`/`desktop`/`interface_contracts` failures are a separate,
documented environmental baseline.

See `07-future-memory-integration.md` for what remains deferred.
