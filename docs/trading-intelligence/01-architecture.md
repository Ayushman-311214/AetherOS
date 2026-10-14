# 01 — Architecture

Trading Intelligence is the core product. Everything else (desktop, vision,
browser, memory) is a supporting layer. The numerical core is deterministic and
LLM-free: an LLM may narrate a report, but it never computes a number.

## Layered design

```
Interface / ABC          MarketDataProvider, NewsProvider, CalendarProvider,
      │                  FundamentalsProvider, PredictionStore, EventBus
      ▼
Backend / Data source    Yahoo (equities), ccxt (crypto books+trades), mock
      ▼
Service                  MarketDataService, TechnicalAnalysisService,
      │                  MarketStructureService, LiquidityService, NewsService,
      │                  CalendarService, FundamentalService, RegimeService,
      │                  RelativeStrengthService, AnomalyService,
      │                  MicrostructureService, ProbabilityService, RiskService,
      │                  BacktestService, CriticService, OrchestrationService, ...
      ▼
Feature                  quant/features.py -> FeatureMatrix (causal, no look-ahead)
      ▼
Signal                   strategies/* -> SignalCandidate -> TradeSignal (proposal)
      ▼
Tool / Agent             trading/tools.py @tool surface -> ToolRegistry -> agents
      ▼
TUI / External           cli/commands.py `analyze`, `track-record`
```

Domain logic never touches I/O, an LLM, or a renderer. Dependency arrows point
inward: services depend on provider *interfaces*, providers on domain models.

## Orchestration

`OrchestrationService` is the deterministic Trading-CEO backbone. It holds **no
analytical logic** — it composes services and assembles a `TradingReport` in
which every number traces to a sub-object. `probability` is surfaced only when
the calibrated estimate passes its own reliability gate; otherwise `None`
(never a fabricated %). `recommendation` is a deterministic projection of the
critic's verdict, so a report is never more confident than the adversary that
judged it.

## Honesty rules (structural, not conventional)

- `SourceTier.MOCK` is first-class. `is_reliable`/`is_actionable` require
  `not is_mock`, so synthetic data can never read as a real edge.
- `Direction.UNKNOWN` / `MarketRegime.UNKNOWN` / `RiskBand.UNKNOWN` are real
  answers — "insufficient evidence" is preferred over a fabricated signal.
- Every `to_dict()` is JSON-serialisable; every record is content-addressed so
  re-derivation dedupes without a database round-trip.
- `NO_TRADE` (a judged, insufficient case) is a valid, auditable outcome —
  distinct from `REJECTED` (a judged, wanting case).

## The Critic's veto map

Hard-FAIL → REJECT: `data_source` (mock), `signal_conflict` (evidence
disagreement), `risk_reward`, `historical_reliability` (no out-of-sample edge),
`probability_calibration` (a *reliable* model disagreeing with the fused side),
`event_risk` (a *reliable* high-impact scheduled event in-horizon).
Advisory (WARN, never veto): `news_sentiment`, `fundamentals`, `market_regime`,
`relative_strength`.
