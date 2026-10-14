# Liquidity — Zones

A `LiquidityZone` is a band of prices where resting liquidity has clustered
persistently enough to be worth tracking across observations. It is the unit a
heatmap or signal layer reasons about — not "where is the biggest order" but
"where is liquidity that has stood and behaved like a wall".

## Shape

```python
LiquidityZone(
    id,                  # content-addressed: symbol|side|band -> same zone, same id
    symbol, side,        # "bid" (demand wall) | "ask" (supply wall)
    lower_price, upper_price,
    liquidity_score,     # 0..1 resting size relative to its own book side
    persistence_score,   # 0..1 how long it has stood
    first_seen, last_seen,
    touch_count,         # observations where price sat inside the band
    sweep_count,         # times the zone was cleared through
    replenishment_count, # times liquidity reappeared after being eaten
    status,              # active | touched | swept | invalidated
    source, is_mock,
)
```

`id` is content-addressed on the band + side (not time), so the same resting
cluster re-detected across snapshots resolves to the same zone identity — that
is what lets the tracker count persistence, touches and sweeps against one
stable zone.

## Detection (`detect_zones`)

Stateless, single-snapshot cluster detection:

1. A book level is **"large"** when its amount ≥ `CLUSTER_SIZE_RATIO` (1.5×) the
   **median** level size on its side. The bar for "large" is set by the book
   itself, not a fixed quantity — so it is book-relative, never "the single
   biggest order wins".
2. Adjacent large levels merge into one **cluster** (one wall, not many zones);
   a gap of normal levels splits.
3. A cluster must hold ≥ `ZONE_MIN_SHARE` (5%) of its side's total resting
   liquidity to seed a zone — a level must *matter*, not just exist.
4. Clusters whose bands come within `ZONE_MERGE_GAP_RATIO` (0.25) of their span
   merge — a wall split by a thin normal level is still one wall.

The detector is deliberately stateless: persistence, touches and sweeps are the
tracker's job over the stream, not something one snapshot can honestly claim.

## Lifecycle (`ZoneTracker`)

The tracker reconciles each new detection with tracked zones and ages them by
what price and the tape do:

- **created** — a new cluster becomes a tracked zone (`LiquidityZoneCreated`).
- **persist** — re-detected zones accumulate `seen_snapshots`; `persistence_score`
  saturates at 1.0 over `persistence_full` (10) snapshots.
- **touched** — price sat inside the band (`touch_count` up).
- **swept** — price cleared through the far edge (see `sweeps.md`).
- **replenished** — after a sweep, resting liquidity climbed back ≥ half its
  prior size (`replenishment_count` up, `LiquidityReplenished`).
- **weakened** — the wall faded from the latest book (`LiquidityZoneWeakened`).
- **invalidated** — resting liquidity fell below 25% of its formation size
  (`LiquidityZoneInvalidated`).

## "Biggest is not automatically important"

The spec's warning is enforced structurally: `liquidity_score` is relative to
the book's own side (a single fat order in a thin book scores high only if it
clusters/persists), and `persistence_score` rewards *standing over time*. A zone
that flashes once and vanishes is a weak zone — the scores say so, and the
tracker lets it weaken and invalidate rather than keeping it alive.
