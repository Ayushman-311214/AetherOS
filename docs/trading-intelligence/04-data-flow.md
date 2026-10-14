# 04 — Data Flow

Two flows matter: the *data* path (raw market input → the canonical `MarketData`
container every stage reads) and the *report* path (the composed pipeline that
produces a `TradingReport`). They share the same services.

## The data path

```
Provider (Yahoo / ccxt / mock)          -- returns raw candles/quotes/books/trades
        │  raises a typed error, never fabricates
        ▼
MarketDataService.get_candles           -- validates, assesses DataQuality,
        │                                   downgrades rather than passing bad bars
        │  (emits MarketDataReceived -> CandleClosed -> MarketDataUpdated)
        ▼
MarketData                              -- immutable series + Provenance + DataQuality
        │  .closes()/.highs()/...  vectorised views
        │  .window(start,end)      the single past-only slicing primitive
        ▼
Analysis services / quant features / backtester
```

Every downstream stage reads `MarketData` — never re-fetches, never a parallel
container. `Provenance` (source + `SourceTier` + `is_mock`) and `DataQuality`
(status + issues) travel with the data so no stage has to guess where numbers
came from. MOCK is a first-class tier, never re-stamped.

## Microstructure

`MicrostructureService` fetches depth/ticks through the provider's
`supports_order_book`/`supports_trades` contract — an unsupported provider is an
honest typed refusal, not an empty guess — and emits `OrderBookUpdated` /
`TradeReceived`. Books reject crossed/unsorted levels; prints carry aggressor
side and `is_mock`.

## The report path

```
generate_trading_report(symbol, timeframe)
        │
        ▼  OrchestrationService composes, computing nothing itself
  analysis ──> technical, structure, evidence -> TradingAnalysis
  risk ──────> RiskAssessment (ATR stop / structural target / RR / invalidation)
  backtest ──> optional walk-forward (off by default, look-ahead-safe)
  probability> logistic + Platt -> ProbabilityEstimate (gated is_reliable)
  news ──────> NewsAnalysis (advisory)
  calendar ──> EventCalendar (advisory; high-impact can veto via critic)
  fundamentals> FundamentalAnalysis (advisory, longer-horizon)
  regime ────> RegimeAnalysis (advisory, situational context)
  rel-strength> RelativeStrengthAnalysis (advisory MARKET_CONTEXT)
  anomaly ───> AnomalyAnalysis (advisory)
        │
        ▼
  CriticService.critique(analysis, risk, backtest, probability, news,
                         calendar, fundamentals, regime, ...)
        │  verdict: APPROVE / REJECT / INSUFFICIENT_EVIDENCE
        ▼
  TradingReport  ->  ReportRecommendation.from_verdict
        │  probability surfaced only when is_reliable, else None
        ▼
  PredictionRecord (§8 contract) -> PredictionStore + PredictionCreated
```

## Failure semantics

- Provider/network failure → typed `MarketDataError`/`InsufficientDataError`;
  an advisory layer (news/calendar/fundamentals) degrades to `None` + limitation
  rather than sinking the report.
- Validation catches malformed data *before* downstream stages — a broken bar
  downgrades `DataQuality`, never crashes the pipeline.
- An advisory fetch failure is try/except-logged; a core stage is not wrapped so
  a real bug surfaces loudly.
- A publish/subscriber failure never propagates into the operation.

## Caching & freshness

`MarketDataService` holds a short TTL candle/quote cache so repeated identical
requests don't hammer the source — but freshness is real (tracked age), and a
cache hit re-emits nothing (a stale snapshot is never re-announced as new).
