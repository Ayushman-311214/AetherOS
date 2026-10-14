# Liquidity — Events

Ten canonical `Event` subclasses on the shared `EventBus`, one per liquidity
change. Each is a distinct named type so a subscriber can register for exactly
what it cares about; all share the `LiquidityEvent` base payload so a consumer
can read any of them uniformly.

## Canonical events

| Event | Meaning | Producer |
|---|---|---|
| `LiquidityAppeared` | new resting liquidity showed at a band | detection |
| `LiquidityRemoved` | resting liquidity pulled (not consumed by tape) | tracker |
| `LiquidityReplenished` | resting liquidity reappeared after consumption | tracker |
| `LiquidityConsumed` | price traded into a zone; wall eaten into | tracker |
| `LiquiditySwept` | price cleared through the zone — *acceptance* | tracker |
| `LiquidityAbsorbed` | aggressive flow absorbed / sweep rejected — wall held | tracker + absorption analyzer |
| `LiquidityImbalanceChanged` | resting book flipped to a one-sided regime | imbalance analyzer |
| `LiquidityZoneCreated` | a new cluster became a tracked zone | tracker |
| `LiquidityZoneWeakened` | a zone's liquidity faded but not dissolved | tracker |
| `LiquidityZoneInvalidated` | a zone dissolved — liquidity below the floor | tracker |

## Shared payload (`LiquidityEvent`)

```
instrument_key     -- the instrument
side               -- "bid" | "ask" | "none"
zone_id            -- content-addressed id of the LiquidityZone ("" for whole-book)
lower_price/upper_price -- the band
price              -- the reference price at the event
volume             -- consumed / reappeared / absorbed volume
liquidity_score    -- resting-size score of the zone
persistence_score  -- persistence score of the zone
detail             -- human-readable context (the supporting numbers)
source_tier        -- provenance tier
is_mock            -- honesty flag: synthetic liquidity never reads as real
```

## Context for each consumer

- **Analysis** — `side`, band, `liquidity_score`, `persistence_score`, `volume`
  let an analyzer weigh the change without deserialising a nested zone.
- **Logging** — `detail` carries the supporting numbers ("consumed 60 of 50
  displayed, cleared through and held").
- **Dashboard / heatmap** — `zone_id` + band + status let a renderer key the
  change to one persistent wall.
- **Future Memory** — `zone_id` is content-addressed, so the same wall's
  lifecycle dedupes across replays; `is_mock`/`source_tier` stop a synthetic
  wall being stored as real.
- **Future backtesting** — every event carries the stream `timestamp` and the
  band, so a replay emits the identical sequence deterministically.

## Emission guarantee

The `ZoneTracker`/`LiquidityEngine` produce `LiquidityZoneEvent` value objects;
`LiquidityIntelligenceService` maps each to its canonical subclass via
`LIQUIDITY_EVENT_TYPES` and publishes best-effort — a publish or subscriber
failure is logged and swallowed, never breaking the read.
