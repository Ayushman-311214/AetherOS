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

## 9. Reconciliation update — gaps closed, gaps deferred

This audit's finding stands: the *canonical* Phase-1 foundation is built. A
follow-up pass mapped the spec's remaining sections (3, 7, 13, 15, 16, 17)
against the code and closed the handful of genuine, honest gaps rather than
rebuilding anything. The increments are additive — no existing service,
provider, or pipeline was changed in behaviour except where the spec required a
new check or event.

**Closed in this pass:**

- **Section 3 (data-quality engine).** `MarketDataService._assess_quality`
  already flagged missing / structural / ordering / partial / stale. Added the
  remaining spec checks in the same one place: future-dated / timestamp-drift
  (last bar ahead of wall-clock → `INVALID`), internal mid-series gaps (an
  adjacent-bar spacing ≥ ~2× the series' own median → `PARTIAL`), and abnormal
  magnitude (a close/volume orders-of-magnitude off the series median →
  `PARTIAL`). `BAD_DATA` still propagates to `NO_TRADE` via `DataQuality.usable`.
- **Section 13 (BUY/SELL/WAIT/NO_TRADE).** Added `DecisionAction`, the
  four-valued user-facing outcome, projected deterministically from the
  decision's `direction` + `recommendation` (exposed on
  `TradingDecision.action` and `to_dict`). WAIT is distinct from NO_TRADE: a
  judged-but-wanting directional case is different from insufficient evidence.
- **Section 15 (decision snapshot).** Added `DecisionSnapshot`
  (`domain/snapshot.py`) — content-addressed `ds_` id, the action verbatim, the
  evidence-ledger ids, the critic trail, a `data_fingerprint` (SHA-1 over the
  candle series' identity + close/volume, never the raw series), and the
  `component_versions` manifest. `DecisionService.decide_snapshot` builds it in
  one pass; `snapshot_for` assembles one from a finished decision.
- **Section 16 (versioning).** Added `ComponentVersions` +
  `default_versions(provider)` (`domain/versions.py`) — the single manifest of
  every component that can change a decision (pipeline, indicators, smc_ict
  rules, strategy rules, probability model, calibration, risk model, critic
  rules, risk policy, decision engine, data schema, config, provider). The full
  map feeds the snapshot id, so a rule/model/config change yields a different
  `ds_` id — the reproducibility contract.
- **Section 17 (events).** Added `VolatilityChanged`, `LiquidityChanged`,
  `SignalInvalidated`, `DataQualityDegraded`, `NewsImpactDetected`,
  `RiskStateChanged` to `events.py`. Producers that can honestly emit them were
  wired: `DataQualityDegraded` from `MarketDataService` (a worsening quality
  band between fetches), `NewsImpactDetected` from `EventCalendarService` (a
  HIGH-impact scheduled event first appearing), `RiskStateChanged` from
  `RiskLimitsService.check` (daily-loss/exposure band moving
  within→approaching→breached). The other three are defined as contracts with
  no producer yet (see §10).
- **Supporting.** `EvidenceReason` gained `reason_id` (the underlying `ev_`
  content id) so the snapshot's `evidence_ids` are real references, not
  fabricated keys.

**Deferred, honestly (spec section 17 contracts, no honest producer yet):**

- `SignalInvalidated` — needs a stateful "was a pending signal's recorded
  invalidation condition met mid-flight?" evaluator; the existing
  `PredictionEvaluator` resolves a *prediction at its horizon*, not a pending
  signal. Contract defined; producer awaits that evaluator.
- `VolatilityChanged` — needs prior realised-vol band state to diff against;
  the 6-state `RegimeTracker` tracks *regime*, not a realised-vol band.
- `LiquidityChanged` — needs a net-liquidity picture diff; the tracker emits
  granular zone events but not a single roll-up state.

**Result:** 1525 tests pass in `tests/trading` (was 1505; +20 new). No mock
trading logic, no duplicated infrastructure, no fake probability — the new code
follows the existing domain/service/event pattern verbatim.

See `07-future-memory-integration.md` for what remains deferred.

---

## Phase 2 — production lifecycle (this pass)

Phase 1 ended at *"an honest decision"*. Phase 2 completes the production
lifecycle: **signal → risk → policy → execution → broker → reconciliation →
portfolio → journal → performance → evaluation → memory**, under real safety
controls. Everything below is additive on the same seams — `ServiceContainer`,
the shared `EventBus`, the existing stores — never a rebuilt or duplicated
infrastructure.

**Added:**

- **Signal lifecycle state machine** (`domain/lifecycle.py`,
  `production/lifecycle_service.py`). The spec's
  `CREATED → VALIDATING → APPROVED/INVALIDATED → ACTIVE → EXECUTED /
  PARTIALLY_FILLED → CLOSED → EVALUATED` chain is now a first-class, validated
  record: `SignalLifecycle.transition` enforces a fixed transition table and
  raises `LifecycleError` on an illegal move (a signal cannot be EVALUATED
  before EXECUTED, APPROVED after EXECUTED, or leave a terminal state).
  `SignalLifecycleService` tracks each signal and is wired into the signal
  engine (CREATED/VALIDATING/APPROVED/INVALIDATED), the execution engine
  (ACTIVE/EXECUTED/PARTIALLY_FILLED/INVALIDATED) and the prediction evaluator
  (EVALUATED). Every accepted step publishes `SignalStateChanged`; the
  previously-dangling `SignalInvalidated` contract now has its producer.
- **Position book** (`production/position_service.py`). The single source of
  truth for open positions, realised PnL and gross exposure. The paper venue
  reports every fill into it; an opposite fill reduces/closes the open leg and
  banks the P&L (a partial close keeps the remainder, an oversized close opens
  the reverse). `snapshot()` builds the live `AccountSnapshot` the risk gate
  consumes — no fabricated balance.
- **Idempotent execution** (`domain/execution.py`,
  `brokers/paper_provider.py`). `ExecutionRequest` derives a content-addressed
  `idempotency_key` / `client_order_id` from the signal + side + quantity; the
  venue keeps a `key → order_id` ledger so a retried or re-issued request
  resolves to the order it placed rather than double-filling. Resting orders
  are indexed the same way.
- **Kill switches** (`domain/kill_switch.py`,
  `production/kill_switch_service.py`). Scoped halts — `global` / `strategy` /
  `broker` / `symbol` — consulted by the engine *before* the broker on both
  the validate and validate-opted-out paths. A trip blocks new admissions,
  preserves the book, emits `KillSwitchTripped`, optionally cancels the resting
  orders it covers (`TRADING_KILL_CANCEL_RESTING`), and requires an explicit
  `clear` to recover (a `clear` on nothing returns `False`, never a fabricated
  recovery).
- **Reconciliation** (`domain/reconciliation.py`,
  `production/reconciliation_service.py`). Diffs the venue's reported
  orders/positions against the local book: missing order, quantity/status/
  position/balance divergence are each flagged as a `ReconciliationMismatch`
  and announced with `ReconciliationMismatchDetected`. A leg it cannot see is
  noted as un-reconciled, never assumed clean.
- **Trading health** (`domain/health.py`, `production/health_service.py`).
  `SAFE`/`DEGRADED`/`BLOCKED`, folded from data quality, kill switches,
  positions, broker reachability and reconciliation. The band is the worst
  signal present by construction; `TradingHealthChanged` fires only on a real
  transition.
- **Counterfactual analysis** (`analytics/counterfactual.py`). Classifies a
  closed journal entry's outcome — `SUPPORT` / `CONTRADICTION` /
  `INVALIDATION` / `MISSING_EVIDENCE` / `NO_TRADE_ALTERNATIVE` /
  `EXECUTION_VS_ANALYSIS` — from the entry's own geometry and result, so
  "the stop fired" and "the thesis was wrong" are distinguishable, not
  narrated.
- **Events** (`events.py`): `SignalStateChanged`, `PositionOpened`,
  `KillSwitchTripped`, `KillSwitchCleared`, `ReconciliationMismatchDetected`,
  `TradingHealthChanged`; `OrderFilled` and `PositionClosed` now have real
  producers.
- **Surface.** `TradingAPI` gained `positions`, `account_snapshot`,
  `reconcile`, `health`, `trip_kill_switch`, `clear_kill_switch`,
  `signal_lifecycle`; matching tools were added to `trading/tools.py`
  (`open_positions`, `account_snapshot`, `reconcile_broker`, `trading_health`,
  `trip_kill_switch`, `clear_kill_switch`, `signal_lifecycle`).
- **Config.** `TRADING_KILL_CANCEL_RESTING` (default off).

**Deferred, honestly:**

- **Live broker connectors** — the `BrokerProvider` interface is the seam; a
  real venue (IBKR/Binance/…) is a later phase, not this build.
- **Correlation/factor portfolio exposure** — the book tracks per-instrument
  positions and gross exposure; cross-instrument correlation needs a
  return-series model that is deferred rather than fabricated.
- **Per-bar fill granularity** — the venue fills at the source price it reads;
  intra-bar fill simulation (partial fills inside a single bar's range) is not
  modelled at this resolution.

**Production boundary held:** new services live in `trading/production/`
(registered on the same container and bus) rather than `trading/services/`,
because the execution engine sits *upstream* of `services/__init__` — importing
the book/switch/lifecycle from `services` would close an import cycle. No mock
trading logic, no duplicated infrastructure, no fake probability or health —
every new verdict is derived from real state and fails closed when it cannot
be read.
