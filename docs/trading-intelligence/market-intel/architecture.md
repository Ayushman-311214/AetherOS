# Market Intelligence — Architecture

`src/aetheros/trading/market_intel/` — the composition layer that combines the
non-liquidity reads into one coherent surface and the canonical feature vector.
It *composes* existing deterministic services rather than re-implementing them,
and adds the pieces those services lacked.

## Module map

```
market_intel/
  regime.py         MarketRegimeState (6 states) + classify_state + RegimeTracker
  price_action.py   PriceActionAnalysis + PriceActionService (rejection/breakout/...)
  volume.py         VolumeAnalysis2 + VolumeActionService (split/net-flow/divergence)
  features.py       MarketFeatures + extract_features
  service.py        MarketIntelService -- the composition point
```

## Composition, not reimplementation

```
MarketData (candle series)
   │
   ├──> MarketStructureService   (EXISTING) -> MarketStructure
   │        HH/HL/LH/LL, trend, levels, breakout/range signals
   ├──> TechnicalAnalysisService (EXISTING) -> TechnicalSnapshot
   │        SMA/EMA/RSI/MACD/ATR/Bollinger/VWAP/ADX/vol
   ├──> PriceActionService       (NEW) -> PriceActionAnalysis
   │        momentum/rejection/breakout/failed-breakout/acceptance/vol-state
   ├──> VolumeActionService      (NEW) -> VolumeAnalysis2
   │        relative volume, est. buy/sell split, net flow, divergence
   └──> RegimeService            (EXISTING) -> RegimeAnalysis
            -> classify_state -> RegimeTracker -> MarketRegimeChanged (confirmed only)
        │
        ▼
   extract_features -> MarketFeatures   (the canonical feature vector)
        │
        ▼
   MarketIntelReport { structure, technical, price_action, volume, regime, features }
```

The service computes **nothing itself** — it sequences the reads, feeds the
regime read to the tracker, publishes `MarketRegimeChanged` on a real
transition, and distils the reads into `MarketFeatures`.

## What was reused vs added

**Reused (not rebuilt):**
- `MarketStructureService` — HH/HL/LH/LL, trend, levels, breakout/breakdown,
  multi-candle pivot confirmation (`pivot_window` lag honoured).
- `TechnicalAnalysisService` + `indicators/core.py` — every indicator the brief
  names (VWAP/EMA/SMA/RSI/ATR/MACD/Bollinger/ADX) already exists, modular,
  deterministic.
- `RegimeService` + `MarketRegime`/`RegimeAnalysis` — the deterministic 5-state
  regime read this layer *classifies into* the 6-state vocabulary.
- `MarketRegimeChanged` event contract — existed; now has a producer.

**New (the gaps):**
- `MarketRegimeState` (6 states) + `classify_state` + `RegimeTracker` —
  LOW_VOLATILITY (calm carved out of RANGING) and TRANSITION (a genuinely
  temporal state a single snapshot can't express).
- `PriceActionService` — rejection / failed-breakout / acceptance /
  vol-expansion-contraction (price-action concepts no existing service read).
- `VolumeActionService` — the fuller volume surface (relative volume, estimated
  buy/sell split, net flow/delta, volume-price divergence).
- `MarketFeatures` — the canonical feature vector.

## Boundaries

- **No decisions.** Nothing emits a direction as a decision; outputs are
  evidence/features for the Signal Engine.
- **Deterministic.** Reads are pure functions of the series (plus the tracker's
  prior-regime window); identical input → identical reads/transitions.
- **No look-ahead.** Structure pivot confirmation honours the `pivot_window`
  lag; regime transitions only *confirm* after the fact.
- **Mock honest.** `is_mock` and UNKNOWN states propagate; synthetic data never
  earns a confident read.
