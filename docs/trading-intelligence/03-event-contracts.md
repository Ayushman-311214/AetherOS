# 03 — Event Contracts

One shared `EventBus` (`runtime/events/event_bus.py`). All trading-domain events
are `@dataclass(frozen=True, slots=True)` subclasses of `Event` carrying
`event_id` + `timestamp` (tz-aware). Every `to_dict()` returns a flat, already-
serialised payload — subscribers never see domain internals. Publishing is
best-effort inside each service: a subscriber/bus failure is logged and
swallowed so an event can never break the operation it describes.

## Pull-based reality → honest events

AetherOS fetches *snapshots*, not a live tick stream. So "a bar closed" or "a
trade arrived" can only mean "the snapshot/depth/prints the system just fetched
contain them." The streaming events are therefore emitted only at the points
where the system genuinely gains that information — never fabricated as a
pseudo-feed.

| Event | Emitted by | When | Key payload |
|---|---|---|---|
| `MarketDataReceived` | `MarketDataService.get_candles` | a fresh (non-cached) snapshot arrives | instrument, timeframe, `candle_count`, `last_price`, first/last bar ts, tier, quality, `is_mock` |
| `CandleClosed` | `MarketDataService.get_candles` | once per fresh fetch — for the **newest** delivered bar | instrument, timeframe, `index`, `is_final_bar`, `bar_timestamp`, OHLCV, tier, quality |
| `MarketDataUpdated` | `MarketDataService.get_candles` | fresh fetch (kept for existing subscribers) | instrument, timeframe, count, last_price, tier, quality |
| `OrderBookUpdated` | `MicrostructureService.get_order_book` | a depth snapshot was fetched | bid/ask levels, best bid/ask, mid, spread, book ts, tier, `is_mock` |
| `TradeReceived` | `MicrostructureService.get_recent_trades` | once per delivered print | instrument, price, amount, `side` (aggressor), trade ts, `tick_id`, tier, `is_mock` |
| `MarketRegimeDetected` | `RegimeService.detect` | a regime read was produced | instrument, timeframe, `regime`, adx, atr_pct, trend_strength, `is_reliable` |
| `MarketRegimeChanged` | *(contract — awaits prior-regime state)* | a real before→after transition | `previous_regime` + `regime` + `direction`, `is_reliable` |
| `FeatureUpdated` | `ProbabilityService.estimate` | the causal feature matrix was recomputed | instrument, timeframe, horizon, `feature_names` (+derived `feature_count`), `has_live_row`, `model`, `is_reliable` |
| `ProbabilityEstimated` | `ProbabilityService.estimate` | a calibrated estimate was produced | `p_up`, holdout vs baseline brier, `is_reliable` |
| `SignalGenerated` | signal/execution path | a proposed action fired | signal_id, action, direction, confidence, risk |
| `AnalysisCompleted` | `AnalysisService` | a `TradingAnalysis` was produced | direction, score, `is_actionable`, evidence_count |
| `RiskAssessed` | `RiskService` | a risk plan was produced | entry/stop/RR, overall_risk, `is_actionable` |
| `BacktestCompleted` | `BacktestService` | a walk-forward run finished | evaluated, accuracy vs base rate, `is_reliable` |
| `SignalCritiqued` | `CriticService` | the critic returned a verdict | verdict, `approved`, check counts |
| `NewsSentimentAnalyzed` | `NewsSentimentService` | a sentiment read was produced | direction, score, item/pos/neg counts, `is_reliable` |
| `MarketEventsDetected` | `EventCalendarService` | a calendar lookup was produced | event_count, `has_high_impact`, next-event info |
| `FundamentalsAnalyzed` | `FundamentalAnalysisService` | a fundamentals read was produced | direction, health_score, metric counts, `is_reliable` |
| `TradingReportGenerated` | `OrchestrationService` | a report was composed | recommendation, direction, verdict, `is_actionable` |
| `PredictionCreated` | `OrchestrationService` | a report was captured as a §8 record | `prediction_id`, recommendation, direction, `probability_up`, `is_mock` |
| `PredictionResolved` | `PredictionEvaluator` | a prediction genuinely RESOLVED | predicted/realized direction, `is_correct`, `realized_return`, brier |
| `PredictionPerformanceEvaluated` | `PredictionPerformanceService` | a batch of outcomes was aggregated | accuracy, coverage, brier, ece, `is_reliable`, `is_mock` |
| `MonitoringSweepCompleted` | monitoring sweep | one bounded resolve+evaluate pass | swept/resolved/pending/scored, accuracy, `is_reliable` |
| `OrderSubmitted`/`OrderFilled`/`PositionClosed`/`RiskLimitReached`/`MarketOpened` | execution/risk path | order/lifecycle/limit events | see `events.py` |

## State-change events (spec section 17)

These announce a *transition*, not a state: each producer keeps a small
last-seen memory keyed on instrument/timeframe (or limit-name) and publishes
once when the band actually moves, never on a flicker. The first observation
only seeds the tracker — a service that has never seen a feed/band cannot
honestly assert a *change*, so nothing fires until there is real history to
diff against.

| Event | Emitted by | When | Key payload |
|---|---|---|---|
| `MarketRegimeChanged` | `MarketIntelService` (6-state tracker) | a confirmed before→after regime transition | `previous_regime` + `regime` + `direction`, `is_reliable` |
| `VolatilityChanged` | *(contract — needs prior realised-vol band)* | calm→normal→elevated realised-vol crossing | `previous_band`/`band`, `atr_pct`, `is_reliable` |
| `LiquidityChanged` | *(contract — needs net-liquidity diff)* | resting liquidity at price materially shifted | `previous_state`/`state`, `detail`, `is_reliable` |
| `SignalInvalidated` | *(contract — needs a signal-state machine)* | a signal's recorded invalidation condition met | `signal_id`/`prediction_id`, `reason`, `invalidation` |
| `DataQualityDegraded` | `MarketDataService` | quality band worsened (OK→PARTIAL/STALE/INVALID) | `previous_status`/`status`, `issues`, `is_mock` |
| `NewsImpactDetected` | `EventCalendarService` | a HIGH-impact scheduled event first appears | `kind`, `title`, `scheduled_at`, `is_reliable` |
| `SignalStateChanged` | `SignalLifecycleService` | a signal advanced one *legal* lifecycle step | `signal_id`, `from_state`, `to_state`, `reason` |
| `SignalInvalidated` | `SignalLifecycleService` | a signal moved to `INVALIDATED` (basis broke / gate refused) | `signal_id`, `reason`, `invalidation` |
| `PositionOpened` | `PositionBookService` | a fill opened a tracked position | `position_id`, `direction`, `quantity`, `entry_price` |
| `PositionClosed` | `PositionBookService` | a fill closed (or reduced) a tracked position | `position_id`, `exit_price`, `realized_pnl` |
| `KillSwitchTripped` | `KillSwitchService` | a scoped halt armed | `scope`, `target`, `reason` |
| `KillSwitchCleared` | `KillSwitchService` | a halt explicitly cleared for recovery | `scope`, `target` |
| `ReconciliationMismatchDetected` | `ReconciliationService` | local and venue state diverged on one leg | `kind`, `detail`, `order_id`, `position_id` |
| `TradingHealthChanged` | `TradingHealthService` | the desk's aggregate band moved | `previous_state`, `state`, `reasons` |
| `RiskStateChanged` | `RiskLimitsService.check` | daily-loss/exposure band moves (within→approaching→breached) | `kind`, `previous_state`/`state`, `utilisation` |
| `PredictionCreated` | `OrchestrationService` | a report was captured as a §8 record | `prediction_id`, recommendation, direction, `probability_up`, `is_mock` |

## Deliberate absences

- **`CandleUpdated`** — not defined. There is no still-forming bar in a
  pull-based snapshot; inventing one would pretend a granularity the data lacks.
- **`SignalInvalidated`** — now produced by `SignalLifecycleService` when a
  candidate/signal moves to `INVALIDATED` (a gate refused it, or its basis
  broke). The earlier "contract without a producer" note is retired.
- **`VolatilityChanged`, `LiquidityChanged`** — contracts defined, but no
  honest producer exists yet in this build: realised-vol / net-liquidity
  *diffs* need a prior-value memory the stateless readers don't carry. They
  are defined so a later producer can publish without a schema change — never
  fabricated as pseudo-events.
- **`MarketRegimeChanged` emission** — the *contract* exists and the
  `MarketIntelService` 6-state `RegimeTracker` produces real transitions, but
  it is wired in the `market_intel` package's own service path; the stateless
  `RegimeService` in the deterministic core still only emits
  `MarketRegimeDetected`.

## Ordering guarantee

`MarketDataReceived` → `CandleClosed` (final bar) → `MarketDataUpdated`, per
fresh fetch. Cache hits emit nothing — a stale snapshot is never re-announced
as new data.
