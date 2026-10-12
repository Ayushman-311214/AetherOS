# Liquidity — Architecture

The liquidity layer is a self-contained package, `src/aetheros/trading/liquidity/`,
kept distinct from the candle-based `LiquidityService` (a volume-*at-price*
profile over OHLCV) and the SMC price-action `LiquidityEvent` (a swing sweep on
bars). Those answer "where did volume trade" and "did price take a level"; this
answers "where is resting and aggressive liquidity *right now*, and what is it
doing".

## Module map

```
liquidity/
  observation.py   LiquidityObservation  -- the atomic read (resting + flow)
  zone.py          LiquidityZone         -- a tracked liquidity band + lifecycle
  sources.py       CandleSource/OrderBookSource/TradeSource/ProviderSource
  analyzers.py     the 6 independent, pure analyzers
  tracker.py       ZoneTracker           -- zone lifecycle over the stream
  engine.py        LiquidityEngine       -- folds (book,trades) -> obs+zones+events
  features.py      LiquidityFeatures     -- the canonical feature vector
  persistence.py   ObservationStore/ZoneStore (+ in-memory & JSONL impls)
  service.py       LiquidityIntelligenceService -- source fetch -> bus + stores
```

## Flow

```
ProviderSource (adapts MarketDataProvider: Yahoo/ccxt/mock)
        │  order_book()  +  recent_trades()   -- typed refusal, never fabricated
        ▼
LiquidityEngine.step(book, trades)
        │  top-of-book depth + aggressor-signed prints -> LiquidityObservation
        │  analyze_imbalance / analyze_absorption / ZoneTracker.update
        ▼
LiquidityStepResult = observation + imbalance + absorption + zones + events
        │
        ├──> LiquidityZoneCreated/Swept/Consumed/Absorbed/...  (EventBus)
        ├──> ObservationStore, ZoneStore                        (persistence)
        └──> extract_features -> LiquidityFeatures              (feature vector)
```

## Source interfaces

The brief's `CandleSource`/`OrderBookSource`/`TradeSource`/`MarketDataSource`
are thin capability interfaces layered on the existing `MarketDataProvider` ABC
— the provider already declares `get_candles`/`get_order_book`/
`get_recent_trades` plus `supports_order_book`/`supports_trades`. `ProviderSource`
adapts any provider (Yahoo, ccxt, mock, or a future adapter) to all three reads,
so no exchange is hard-coded. An unsupported read is an honest `ProviderError`,
never an empty guess.

## Determinism (backtestable by construction)

- Every analyzer is a pure function of its inputs — no I/O, no wall clock.
- `ZoneTracker` holds lifecycle state, but that state is a pure function of the
  ordered input stream: two trackers fed the same `(book, trades)` steps reach
  identical zones, scores and event sequences.
- `LiquidityEngine` carries only the *between-step* state that is genuinely
  between steps (the previous price for absorption's realised-move window).
- Every timestamp a zone or observation records comes from the stream, never
  `datetime.now()`.

`service.replay(steps)` is the backtestable path: feed a recorded historical
stream and get the identical intelligence a live feed would have produced,
look-ahead-free because each step only sees data up to itself.

## Boundaries

- The engine returns plain values and emits *value objects*
  (`LiquidityZoneEvent`); the service translates each into its canonical
  `LiquidityEvent` subclass on the shared `EventBus` — the engine itself never
  touches the bus, keeping it unit-testable.
- Persistence is optional. The service works identically with no stores wired;
  a publish or store failure is logged and swallowed so it never breaks a read.
