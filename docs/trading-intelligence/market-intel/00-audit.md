# Phase 4 Audit — Non-Liquidity Market Intelligence

What Phase 4 added, what it reused, and the boundary decisions that keep it a
feature/evidence layer with no decisions.

## Reused (not rebuilt) — the bulk of the brief already existed

- **`MarketStructureService`** — HH/HL/LH/LL, `TrendState`, support/resistance,
  `StructureSignal` BREAKOUT/BREAKDOWN/RANGE, multi-candle `pivot_window`
  confirmation (no single-candle structure, no look-ahead).
- **`TechnicalAnalysisService` + `indicators/core.py`** — VWAP/EMA/SMA/RSI/
  ATR/MACD/Bollinger/ADX/volatility/volume — modular, causal, deterministic.
  Indicators as evidence, never signals.
- **`RegimeService` + `MarketRegime`/`RegimeAnalysis`** — the deterministic
  ADX/ATR regime read this layer classifies into the 6-state vocabulary.
- **SMC layer** — `StructureBreak` BOS/CHoCH (market-structure-shift) already
  exists; not duplicated.
- **`MarketRegimeChanged` event contract** — existed; now has a producer.
- **`SourceTier.MOCK` honesty** — propagated to every read/feature.

## New (the genuine gaps)

| Module | Contents |
|---|---|
| `market_intel/regime.py` | `MarketRegimeState` (6 states) + `classify_state` + `RegimeTracker` + `RegimeTransition` — LOW_VOLATILITY (calm carved from RANGING) and TRANSITION (temporal) |
| `market_intel/price_action.py` | `PriceActionService`/`PriceActionAnalysis` — momentum, rejection, breakout, failed-breakout, acceptance, range, vol expansion/contraction |
| `market_intel/volume.py` | `VolumeActionService`/`VolumeAnalysis2` — relative volume, expansion/contraction, *estimated* buy/sell split, net flow/delta, volume-price divergence |
| `market_intel/features.py` | `MarketFeatures` + `extract_features` — the canonical 16-feature vector |
| `market_intel/service.py` | `MarketIntelService` — composition + regime tracking + `MarketRegimeChanged` emit |

Wired `MarketIntelService` into `bootstrapper._bootstrap_trading` (resolves the
already-registered MarketStructure/TechnicalAnalysis/Regime services + bus).

## Regime — the 6 states the brief asks for

TRENDING_BULLISH, TRENDING_BEARISH, RANGING, HIGH_VOLATILITY, LOW_VOLATILITY,
TRANSITION — mapped from the deterministic `MarketRegime` read via
`classify_state`. `MarketRegimeChanged` fires **only on a confirmed transition**
(`RegimeTracker.confirm` consecutive reads) — never a flicker; TRANSITION
reports a genuinely-mixed window honestly.

## Boundary decisions

- **No decisions.** Every read produces evidence/features; nothing emits a
  direction as a trade call.
- **Compose, don't duplicate.** The service holds no analytical logic — it
  sequences existing services + the new analyzers.
- **Estimated, not real, buy/sell volume** — bar geometry (CLV), labelled
  "estimated"; a real tape feed takes precedence.
- **Confirmed, not flickering, transitions** — the dwell/confirm rule.
- **`MarketFeatures` distils only** — computes nothing new, so a feature can
  never disagree with the read it came from.

## Tests

`tests/trading/test_market_intel.py` — 18 tests: structure trend/min-bars,
indicator snapshot/None-on-thin, price-action (thin/breakout/failed-
breakout/rejection), volume (relative/split/net-flow/divergence/thin), regime
6-state classification + confirmed transitions + no-change-no-event + event
emit, features shape/bounds/determinism.

## Remaining Phase 5 work

- Fuse `MarketFeatures` + `LiquidityFeatures` into the Signal Engine's input
  contract.
- A real regime-transition live loop (the tracker is the producer; a scheduler
  to drive successive `detect` calls).
- Buy/sell split upgrade when a real aggressor tape feed is available.
