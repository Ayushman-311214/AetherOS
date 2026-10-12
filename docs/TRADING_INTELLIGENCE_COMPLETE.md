# AetherOS Trading Intelligence — Complete Reference

> **What it is:** an evidence-based, probabilistic, explainable, backtestable
> **Trading Intelligence and Decision-Support System**. It is not a chatbot
> that guesses BUY/SELL, and it is not an autonomous order-execution bot.
> Every number it reports is traceable to a deterministic computation over
> validated data; every probability is calibrated and gated; every prediction
> is recorded and later scored against what the market actually did.
>
> This document is the single top-level reference. Per-package deep-dives live
> under `docs/trading-intelligence/`.

---

## 1. What the system does

Given an instrument and a timeframe, the pipeline converts raw market data
into an explainable, probability-gated trading decision:

```text
Market data (candles, order book, trades)
        │
        ▼
  Observations          ── per-step reads of the book + tape
        │
        ▼
  Liquidity engine      ── zones, sweeps, absorption, replenishment
        │
        ▼
  Heatmap grid          ── one time×price grid, six read-only lenses
        │
        ▼
  Market intelligence   ── structure / price-action / volume / regime
        │
        ▼
  Feature vector        ── the numeric row the quant layer consumes
        │
        ▼
  Evidence aggregation  ── supporting vs opposing, coverage, gaps
        │
        ▼
  Signal scoring        ── raw score → model score → calibrated probability
        │
        ▼
  Risk / reward         ── stops, invalidation, R-multiples (deterministic)
        │
        ▼
  Critic / gates        ── may REJECT a weak or unsafe signal
        │
        ▼
  Prediction record     ── the auditable section-8 contract
        │
        ▼
  Outcome resolution    ── scored later against realised forward moves
        │
        ▼
  Calibration + metrics ── accuracy, Brier, ECE, excursion stats
        │
        ▼
  Terminal workspace    ── the live multi-pane TUI (read-only view)
```

Every stage is a real component; the TUI and the orchestrator **compose** these
components rather than re-implementing them. The same production components run
in live mode and in backtest mode — there is no separate "fake" analysis path.

---

## 2. Governing invariants

These are the rules every component obeys. They are what make the output
trustworthy.

### 2.1 Deterministic numerical core

All numbers — indicators, regime classification, liquidity scores, probabilities,
risk/reward, backtest metrics — are computed by deterministic Python. An LLM may
*narrate* a result, but it is **never the source of numerical truth**. The same
inputs always produce the same outputs, which is what makes the system testable
and reproducible.

### 2.2 No look-ahead bias

At any bar index `T`, a component may only see data at or before `T`. The single
slicing primitive is `MarketData.window(0, i + 1)` — an inclusive prefix window
of the candle series ending at bar `i`. Both the live path and the backtest
pipeline reuse this same primitive, so a backtest can never peek at a future bar
that live analysis would not have had. The backtest docs (`docs/trading-intelligence/backtest/look-ahead.md`) spell out the mechanism.

### 2.3 No fake probabilities

A raw evidence score is **not** a probability. The pipeline keeps four quantities
deliberately separate in `SignalAssessment` (`signal_engine/assessment.py`):

```text
raw_evidence_score   – opaque aggregation of evidence weights (unitless)
model_score          – the learned/statistical read (still not a probability)
probability_up       – present ONLY when a reliable calibrated estimate exists
confidence           – a separate gate about evidence quality, not P(win)
```

`probability_up` is `None` whenever the calibrated estimate is unavailable or
unreliable (thin sample, MOCK data, weak edge). The system prefers *"I don't
have enough evidence"* over a fabricated number — `NO_TRADE` /
`INSUFFICIENT_EVIDENCE` is a first-class, valid result, never a failure.

### 2.4 Honesty flags everywhere

Data and conclusions carry provenance and honesty markers throughout:

- `SourceTier` — `PRIMARY`, `SECONDARY`, `DERIVED`, `MOCK`, … classifies the
  origin of every datum.
- `is_mock` — set on zones, events, predictions and outcomes that rest on
  synthetic data. A MOCK prediction can never later be read as a real track
  record.
- `is_reliable` — set on estimates, regimes, features and aggregates that have
  cleared their own evidence gate. An aggregate (e.g.
  `PredictionPerformanceEvaluated`) is reported but flagged unreliable when the
  scored sample is thinner than the configured minimum.

### 2.5 Content-addressed identity

Evidence, zones and predictions get IDs derived from their content (sha1), so
the same observation deduplicates and a record is stable across the pipeline and
any future store.

### 2.6 The TUI holds no trading logic

The terminal workspace is a pure view: it subscribes to events, renders panels
and never computes an indicator, a probability or a risk number. All
intelligence lives in the trading services; the TUI only displays what they emit.

---

## 3. What data it consumes

| Input | Provider / source | Notes |
|-------|-------------------|-------|
| OHLCV candles | `MarketDataProvider` (e.g. Yahoo) via `MarketDataService` | the canonical price series; `MarketData.window` is the look-ahead-safe slice |
| Order book | `OrderBookSource` / `ProviderSource` | drives liquidity zones, imbalance, walls |
| Executed trades / tape | `TradeSource` / `ProviderSource` | drives flow, consumption, absorption |
| Fundamentals | fundamentals provider | secondary input to fundamental agent |
| News / events | news provider + `calendar/` | sentiment + event calendar |
| Configuration | `Settings` (`TRADING_*`) | every threshold/credential comes from config |

A provider that cannot serve books or trades **degrades honestly** — the service
returns a typed refusal or "no flow", it never fabricates a wall. Stale,
incomplete or invalid data is surfaced through `DataQuality`, never silently used.

---

## 4. The pipeline, stage by stage

### 4.1 Microstructure — `services/microstructure_service.py`

Adapts the raw provider into order-book and trade observations and republishes
`OrderBookUpdated` / `TradeReceived` events. This is the ingest boundary for the
microstructure layer.

### 4.2 Liquidity intelligence — `liquidity/`

Turns order-book + tape into a tracked model of resting and executed liquidity.

- **`observation.py`** — `LiquidityObservation`: a frozen per-step read of the
  book (imbalance `(bid-ask)/(bid+ask)`, net flow, …).
- **`zone.py`** — `LiquidityZone`: a clustered band of resting liquidity with
  `lower_price`/`upper_price`, `liquidity_score`, `persistence_score`, status
  and `is_mock`.
- **`analyzers.py`** — six pure functions: `analyze_imbalance`, `detect_zones`
  (median-based level clustering), `categorize_sweep` (acceptance / rejection /
  none), `analyze_absorption`, `analyze_replenishment`, `analyze_consumption`.
- **`tracker.py`** — `ZoneTracker`: rebuilds and tracks zone lifecycle (overlap,
  sweep detection, price interaction).
- **`engine.py`** — `LiquidityEngine.step(book, trades)` → `LiquidityStepResult`
  (observation + imbalance + absorption + zones + events).
- **`sources.py`** — `CandleSource` / `OrderBookSource` / `TradeSource` /
  `ProviderSource` adapt any `MarketDataProvider`.
- **`service.py`** — `LiquidityIntelligenceService` publishes the ten
  `LiquidityEvent` subclasses.
- **`persistence.py`** — in-memory and JSONL-file `ObservationStore` /
  `ZoneStore` (extension point for durable storage).

Deep-dive: `docs/trading-intelligence/liquidity/`.

### 4.3 Heatmap — `heatmap/`

A **single time×price grid** read through **six lenses** — "one grid, six
lenses", not six engines. The grid accumulates raw volumes per cell; each view
is a read-only projection, never a separate computation.

- **`cell.py`** — `HeatmapCell`: bid/ask intensity, executed buy/sell, net flow,
  persistence, consumption, replenishment, sweep/absorption/pressure scores.
- **`grid.py`** — `HeatmapGrid`: time+price bucketing; `update()` accumulates
  volumes and takes the max of derived scores; bounded capacity.
- **`views.py`** — `render(grid, kind)`; `_VIEW_CHANNELS` maps each view kind to
  a channel: `liquidity → total_intensity`, `persistence`, `flow → net_flow`,
  `sweep`, `absorption`, `pressure`.
- **`surface.py`** — `LiquiditySurface` + `project()` for the 3-D read.
- **`service.py`** — `HeatmapService` (read-only observation layer over the
  liquidity engine).

Deep-dive: `docs/trading-intelligence/heatmaps/`.

### 4.4 Market intelligence — `market_intel/`

Non-liquidity reads, composed — not duplicated — into a feature vector. The
service injects the already-registered `MarketStructureService`,
`TechnicalAnalysisService` and `RegimeService` and computes nothing itself.

- **`regime.py`** — `MarketRegimeState` (6 states + transition + unknown):
  `TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGING`, `HIGH_VOLATILITY`,
  `LOW_VOLATILITY`, `TRANSITION`, `UNKNOWN`; `classify_state` + `RegimeTracker`
  with windowed confirmation (publishes `MarketRegimeChanged` only on a real
  transition).
- **`price_action.py`** — `PriceActionKind` + `PriceActionService` (momentum /
  structure reads).
- **`volume.py`** — `VolumeAnalysis` + `VolumeActionService`.
- **`features.py`** — `MarketFeatures` + `extract_features`: the numeric row the
  quant layer consumes.
- **`service.py`** — `MarketIntelService.analyze` (async; awaits `RegimeService.detect`).

Deep-dive: `docs/trading-intelligence/market-intel/`.

### 4.5 Signal engine — `signal_engine/`

Aggregates evidence + the feature vector into an explainable
`SignalAssessment`. This is where the four separated quantities (2.3) live.

- **`evidence.py`** — `EvidenceLedger`: supporting vs opposing split, coverage,
  `MissingSource` accounting (explicit gaps, never silent).
- **`features.py`** — `features_to_evidence`: turn `MarketFeatures` into evidence.
- **`scoring.py`** — `compute_scores`: keeps `raw_evidence_score` / `model_score`
  / `probability_up` / `confidence` separate.
- **`assessment.py`** — `SignalAssessment`: the deliverable.
- **`service.py`** — `SignalEngineService.assess`.

Deep-dive: `docs/trading-intelligence/signal-engine/`.

### 4.6 Risk & reward

Risk is computed **deterministically** (see `risk/`, `services/risk_service.py`):
ATR-based stops (`TRADING_RISK_ATR_STOP_MULT`), minimum reward gate
(`TRADING_RISK_MIN_REWARD`), position sizing by account % (`TRADING_RISK_ACCOUNT_PCT`),
daily-loss and max-exposure limits. The output is an R-multiple and an
**invalidation condition** — never false precision.

### 4.7 Critic / gates — `services/critic_service.py`

A standing adversary that can **REJECT** a signal that is weak, contradictory,
unsupported or unsafe (e.g. an earnings event inside the horizon where the model
is historically unreliable). A rejected signal never becomes a prediction.

### 4.8 Prediction record — `domain/prediction.py`

`PredictionRecord`: the auditable section-8 contract — instrument, timestamp,
horizon, direction, probability, confidence, risk/reward, invalidation, model
pipeline, source tier, `is_mock`. Round-trips through `to_dict`/`from_dict` for
the durable store (`services/prediction_store.py`, JSONL at
`TRADING_PREDICTION_STORE_PATH`).

### 4.9 Outcome resolution + metrics — `backtest/` + `services/`

- **`backtest/outcome.py`** — `EnrichedOutcome`: realised direction/return,
  `max_favorable_excursion`, `max_adverse_excursion`, `target_hit`,
  `invalidation_hit`, `time_to_outcome`.
- **`backtest/evaluator.py`** — `OutcomeEvaluator` over a `PredictionLike`.
- **`backtest/metrics.py`** — `BacktestMetrics` + `evaluate`: accuracy,
  precision, recall, expected return, mean MFE/MAE, profit factor, plus the
  liquidity-specific reads (zone-reaction, sweep-reversal/-continuation,
  absorption-success rates).
- **`backtest/pipeline.py`** — `BacktestPipeline(assess_fn, horizon, warmup,
  step)`: replays a series through `window(0, i+1)` and measures the forward
  outcome; `assess_fn` is the real production chain (see §5).
- `services/outcome_store.py`, `services/prediction_evaluator.py`,
  `services/calibration_history_service.py`, `services/track_record_service.py`,
  `services/walk_forward_service.py` — persistence + aggregate evaluation +
  walk-forward validation.

Deep-dive: `docs/trading-intelligence/backtest/`.

---

## 5. Wiring — how it is assembled

Everything is registered as singletons in `bootstrap/bootstrapper.py`
(`_bootstrap_trading`, ~line 766). Composition over duplication throughout:

```python
LiquidityIntelligenceService(
    ProviderSource(market_data_provider),   # books
    ProviderSource(market_data_provider),   # trades
    event_bus=event_bus,
)
MarketIntelService(
    settings=…, event_bus=event_bus,
    structure=MarketStructureService,       # injected, not rebuilt
    technical=TechnicalAnalysisService,
    regime=RegimeService,
)
SignalEngineService(settings)
BacktestPipeline(
    assess_fn=_backtest_assess,             # the REAL production chain
    horizon=TRADING_BACKTEST_HORIZON,
    warmup=TRADING_BACKTEST_WARMUP,
)
```

`_backtest_assess` runs `AnalysisService.analyze_data(window, emit=False)` →
`SignalEngineService.assess(analysis)` — i.e. a backtest exercises **exactly**
the components a live prediction does, over a past-only window.

---

## 6. Events — the Memory-compatible surface

The system announces every important state change on the shared `EventBus`
(`runtime/events/event_bus.py`). **Dispatch is by exact event type** — a
subscriber registers for each concrete class it wants.

The structured-intelligence events a future Memory subsystem would subscribe to:

| Spec concept | Canonical event class |
|---|---|
| Prediction created | `PredictionCreated` |
| Prediction outcome recorded | `PredictionResolved` *(this is the outcome record)* |
| Signal generated | `SignalGenerated` |
| Evidence generated | `AnalysisCompleted` / `EvidenceService` evidence |
| Market regime changed | `MarketRegimeChanged` |
| Liquidity zone created | `LiquidityZoneCreated` |
| Liquidity sweep detected | `LiquiditySwept` *(the acceptance kind; rejection is `LiquidityAbsorbed`)* |
| Analysis completed | `AnalysisCompleted` |
| Performance aggregate | `PredictionPerformanceEvaluated` |
| Backtest done | `BacktestCompleted` |
| Probability estimated | `ProbabilityEstimated` |

> The Phase-8 spec used idealised names (`PredictionOutcomeRecorded`,
> `LiquiditySweepDetected`, `EvidenceGenerated`). The production events that
> actually carry those semantics are `PredictionResolved`, `LiquiditySwept` and
> the evidence emitted by `AnalysisCompleted` — verified in
> `tests/trading/test_memory_compatibility.py`.

A Memory subscriber needs only the bus's public `subscribe(type, handler)` API —
it must expose a **named** async handler (e.g. `handle`), because the bus logs
`handler.__name__`. No trading code changes are required to attach it. See
`docs/trading-intelligence/07-future-memory-integration.md`.

---

## 7. Configuration

No key, URL, credential or threshold is hard-coded — all come from `Settings`
(`config/settings.py`) with `AETHEROS_TRADING_*` / `TRADING_*` env aliases.
Grouped by subsystem:

| Group | Representative settings |
|---|---|
| Data | `TRADING_DEFAULT_TIMEFRAME`, `TRADING_MAX_CANDLES`, `TRADING_CACHE_TTL_*`, `TRADING_STALE_MULTIPLIER`, `TRADING_HTTP_TIMEOUT`, `TRADING_PROVIDER_*` |
| Risk | `TRADING_RISK_ATR_STOP_MULT`, `TRADING_RISK_MIN_REWARD`, `TRADING_RISK_ACCOUNT_PCT`, `TRADING_RISK_DAILY_LOSS_PCT`, `TRADING_RISK_MAX_EXPOSURE_PCT` |
| Backtest | `TRADING_BACKTEST_HORIZON`, `TRADING_BACKTEST_WARMUP`, `TRADING_BACKTEST_MIN_SAMPLE`, `TRADING_WF_TRAIN_BARS`, `TRADING_WF_TEST_BARS`, `TRADING_WF_MIN_FOLDS` |
| Critic | `TRADING_CRITIC_MIN_EVIDENCE`, `TRADING_CRITIC_MIN_AGREEMENT` |
| Probability | `TRADING_PROB_HORIZON`, `TRADING_PROB_MIN_TRAIN`, `TRADING_PROB_MIN_CALIB`, `TRADING_PROB_MIN_HOLDOUT`, `TRADING_PROB_L2`, `TRADING_PROB_ECE_BINS`, `TRADING_PROB_DIRECTION_BAND` |
| Regime | `TRADING_REGIME_ADX_TREND`, `TRADING_REGIME_VOL_HIGH_PCT`, `TRADING_REGIME_PERIOD`, `TRADING_REGIME_MIN_BARS` |
| Calibration | `TRADING_CALIB_HOLDOUT_FRACTION`, `TRADING_CALIB_MIN_SAMPLE`, `TRADING_CALIB_BIAS_BAND` |
| Monitoring | `TRADING_MONITOR_ENABLED` (off by default), `TRADING_MONITOR_INTERVAL_SECONDS` |
| Persistence | `TRADING_PREDICTION_STORE_PATH`, `TRADING_OUTCOME_STORE_PATH` |

---

## 8. The terminal workspace (TUI)

`src/aetheros/workspace/` — a Rich-based, in-terminal multi-pane workspace
(Phase 7). It is a view layer only.

- `state.py` — `WorkspaceState`: bounded ring buffers (`deque`) for events and
  logs, plus the latest report/assessment/intel/heatmap/candles payloads.
- `panels.py` — nine `panel_*` builders (market, analysis, liquidity, heatmap,
  signals, events, logs, agents, system).
- `layout.py` — `build_layout` + the region→panel map.
- `adapter.py` — `WorkspaceAdapter` subscribes to each concrete trading event
  type (`_subscribed_types`); `WorkspaceLogHandler` routes log lines.
- `driver.py` — `build_refresh_fn`.
- `app.py` — `TerminalWorkspace` + `KEYMAP` (`1`–`8` switch panes, `p`/space
  pause, `r` refresh, `q` quit); `build_workspace(...)`.

Keymap / panes: `1` market · `2` analysis · `3` liquidity · `4` heatmap ·
`5` signals · `6` logs · `7` agents · `8` system.

Deep-dive: `docs/trading-intelligence/workspace/`.

---

## 9. How a future Memory subsystem integrates

Memory is **deliberately not built** in this phase — but the architecture leaves
it a clean, verified seam:

1. **Subscribe, don't embed.** A `MemoryAdapter` registers named async handlers
   on the `EventBus` for each event class in §6 — no changes to trading code.
2. **Persistable shapes.** `Evidence`, `LiquidityZone`, `PredictionRecord`,
   `EnrichedOutcome` are content-addressed and `to_dict`/`from_dict`
   round-trippable — the same shape a store writes.
3. **Honesty preserved.** `is_mock`, `is_reliable`, `source_tier` travel on the
   events and records, so Memory can never later report a MOCK run as a real
   track record.
4. **Bounded.** The workspace already uses bounded buffers; a Memory store
   follows the same pattern and is itself a `register_singleton` service.

Verified by `tests/trading/test_memory_compatibility.py` (3 tests): the adapter
receives every structured event via the public bus API, the system works
identically with zero subscribers, and the domain records are persistable,
id-stable shapes.

---

## 10. What is implemented vs optional

**Implemented (deterministic core, tested):** market-data ingest, microstructure
observations, liquidity zones/sweeps/absorption, the six-lens heatmap, market
structure/price-action/volume, the 6-state regime, the feature layer, evidence
aggregation, signal scoring with calibrated probability, risk/reward, the
critic gate, prediction + outcome records, the look-ahead-safe backtest
pipeline + metrics + calibration, walk-forward validation, the event surface,
and the terminal workspace.

**Optional / layered on top:** the LLM orchestration / CEO narrative (reasoning
over the deterministic output — never the source of its numbers), monitoring
scheduler (`TRADING_MONITOR_ENABLED`, off by default), fundamentals/news
providers as secondary inputs, and the future Memory subsystem.

---

## 11. Known limitations

- **No Memory yet** — by design; the seam is verified, the store is not built.
- **Provider coverage** — a provider that cannot serve order books or the tape
  degrades to "no flow" honestly; liquidity reads are only as good as the feed.
- **Probabilities are gated** — `probability_up` may legitimately be `None`;
  that is the system declining to fabricate, not a bug.
- **Calibration needs sample** — calibrated reliability only earns out over
  enough resolved predictions (`TRADING_PROB_MIN_*`, `TRADING_CALIB_MIN_SAMPLE`).
- **Backtest realism** — the pipeline measures forward outcome and excursion
  statistics; it does not model fills/slippage at the broker level (that lives
  in the separate simulation/broker layer).
- **Pre-existing suite failures** — six tests in the *legacy* execution /
  simulation / walk-forward area fail from an uncommitted circular import
  (`brokers/paper_provider.py` ↔ `services/simulation_service.py`). They are
  pre-existing, unrelated to this pipeline, and reported separately.

---

## 12. Testing & verification

- 82 test files under `tests/trading/` + `tests/workspace/` cover domain
  foundation, indicators, each pipeline stage, the signal gates, the backtest
  pipeline (incl. look-ahead), prediction stores, calibration, providers and
  the workspace.
- The look-ahead guarantee is asserted directly (a backtest window can never
  contain a bar after `T`).
- `test_memory_compatibility.py` proves the Memory seam without building it.
- Deterministic components have deterministic numerical tests.

Run the suite: `python -m pytest tests/trading tests/workspace -q`.

---

## 13. Reading map

| Want | Doc |
|---|---|
| Top-level architecture / data flow / events | `docs/trading-intelligence/0[1-6]-*.md` |
| Liquidity engine | `docs/trading-intelligence/liquidity/` |
| Heatmap | `docs/trading-intelligence/heatmaps/` |
| Market intel / regime | `docs/trading-intelligence/market-intel/` |
| Signal / probability / risk | `docs/trading-intelligence/signal-engine/` |
| Backtest / calibration / look-ahead | `docs/trading-intelligence/backtest/` |
| TUI | `docs/trading-intelligence/workspace/` |
| Memory integration | `docs/trading-intelligence/07-future-memory-integration.md` |

---

*Trading Intelligence is the core product. Every supporting system — LLM,
automation, memory, vision — exists to serve it, and none of them may ever
manufacture a number the deterministic core did not compute.*
