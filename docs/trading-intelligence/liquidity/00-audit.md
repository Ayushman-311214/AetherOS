# Phase 2 Audit — Liquidity Intelligence

What Phase 2 added, what it reused, and the boundary decisions that kept it
honest and non-duplicative.

## Reused (not rebuilt)

- **`MarketDataProvider` ABC** (`providers/base.py`) — already declared
  `get_candles`/`get_order_book`/`get_recent_trades` + `supports_order_book`/
  `supports_trades`. The liquidity layer plugs into it via `ProviderSource`,
  not a new provider hierarchy — so Yahoo/ccxt/mock all work unchanged.
- **`OrderBook` / `OrderBookLevel` / `TradeTick`** (`domain/order_book.py`) —
  the canonical microstructure value objects, already validated (crossed-book
  rejected, best-first ordering enforced). The liquidity layer consumes them
  verbatim.
- **Shared `EventBus`** + `Event` base — all 10 liquidity events publish on the
  existing bus; no second bus.
- **Store pattern** — `ObservationStore`/`ZoneStore` reuse the append-and-read,
  content-addressed, never-fabricate contract from `PredictionStore`/
  `OutcomeStore` (in-memory + JSON-Lines impls). No new database architecture.
- **`SourceTier.MOCK` / `is_mock`** honesty flag — surfaced on every
  observation, zone and event.

## New (this phase)

| Module | Contents |
|---|---|
| `liquidity/observation.py` | `LiquidityObservation` — resting + executed liquidity, derived imbalance/net_flow |
| `liquidity/zone.py` | `LiquidityZone` — tracked liquidity band + lifecycle (touched/swept/invalidated) |
| `liquidity/sources.py` | `CandleSource`/`OrderBookSource`/`TradeSource`/`ProviderSource` interfaces |
| `liquidity/analyzers.py` | 6 independent pure analyzers (imbalance, zones, sweep, absorption, replenishment, consumption) |
| `liquidity/tracker.py` | `ZoneTracker` — zone lifecycle over the stream + `LiquidityZoneEvent` |
| `liquidity/engine.py` | `LiquidityEngine` — folds (book,trades) → obs+zones+events, deterministic |
| `liquidity/features.py` | `LiquidityFeatures` + `extract_features` — the 12-feature vector |
| `liquidity/persistence.py` | `ObservationStore`/`ZoneStore` + in-memory & JSON-Lines impls |
| `liquidity/service.py` | `LiquidityIntelligenceService` — source fetch → bus + stores + features |
| `events.py` | 10 canonical liquidity `Event` subclasses + `LIQUIDITY_EVENT_TYPES` |
| `errors.py` | `LiquidityError` (TRADING_LQ_001) |

Wired `LiquidityIntelligenceService` into `bootstrapper._bootstrap_trading`
(resolves `MarketDataProvider` → `ProviderSource` → bus).

## Boundary decisions

- **Kept distinct from existing liquidity concepts.** `LiquidityService`/
  `LiquidityAnalysis` reads a volume-*at-price* profile off OHLCV candles; the
  SMC `LiquidityEvent` is a swing sweep on bars. The new microstructure layer
  (order book + tape) is a separate package so none is silently overloaded.
- **"Biggest is not important"** enforced: `liquidity_score` is book-relative,
  `persistence_score` rewards standing over time; a single fat order alone does
  not seed a zone.
- **Sweep ≠ reversal**: rejection (held inside) vs acceptance (cleared through
  and stayed) are observed separately; never auto-classified.
- **`LiquidityObservation` is new** (not a duplicate of `MarketData`/`Quote`):
  it is the *derived* resting+executed read the analyzers consume, distinct from
  the raw candle/book containers.
- **Mock honesty**: `is_mock` on every record/event — synthetic liquidity can
  never read as a real wall.

## Tests

`tests/trading/test_liquidity.py` — 29 tests covering order-book normalisation,
imbalance, zone detection/clustering/persistence/weakening, replenishment,
consumption, sweep acceptance-vs-rejection, absorption, deterministic replay,
look-ahead safety, canonical event emission, persistence round-trip and
provider-source honesty. All deterministic synthetic fixtures.

## Remaining Phase 3 work

- Fuse `LiquidityFeatures` into `TradingReport`/critic as an advisory evidence
  layer (currently standalone).
- Real order-book/trade streaming beyond snapshot pulls (a live book-diff feed
  would refine zone/touch granularity).
- Heatmap / terminal-dashboard rendering of zones over time.
- Options/catalyst evidence layers (still reserved in `EvidenceType`).
