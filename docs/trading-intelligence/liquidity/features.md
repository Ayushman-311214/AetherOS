# Liquidity — Features

The canonical liquidity feature vector (`LiquidityFeatures`) is the contract a
heatmap, a signal layer or a backtester consumes. Every feature is deterministic
from the inputs, bounded to a stated range, and *descriptive of liquidity
behaviour* — never a directional signal or a probability. `0.0`/`None` are
honest "no reading" values.

## Feature list

| Feature | Range | Meaning |
|---|---|---|
| `nearest_bid_zone_distance` | bps, ≤500 | signed distance to nearest active bid zone |
| `nearest_ask_zone_distance` | bps, ≤500 | signed distance to nearest active ask zone |
| `bid_liquidity_score` | 0..1 | resting-size score of nearest bid zone |
| `ask_liquidity_score` | 0..1 | resting-size score of nearest ask zone |
| `liquidity_imbalance` | −1..1 | resting bid/ask balance (the observation's) |
| `sweep_up_score` | 0..1 | how often the tape swept asks (up-pressure), normalised |
| `sweep_down_score` | 0..1 | how often the tape swept bids (down-pressure), normalised |
| `absorption_bid_score` | 0..1 | strength of the latest buy-side absorption read |
| `absorption_ask_score` | 0..1 | strength of the latest sell-side absorption read |
| `replenishment_score` | 0..1 | how persistently walls refill after being eaten |
| `liquidity_velocity` | 0..1 | how fast resting liquidity is turning over |
| `persistence_score` | 0..1 | standing time of the most durable active zone |

Plus the honesty/quality context a consumer needs: `symbol`, `timestamp`,
`observations_seen`, `is_mock`.

## Where each comes from

- **Distances** — `_bps_distance(price, zone)`: the gap from the reference price
  to the zone's nearest edge, in basis points, capped at 500 so a zone on the
  other side of the book can't dominate the vector.
- **Liquidity scores** — taken verbatim from the zones (`liquidity_score`) and
  the observation (`imbalance`); the feature layer computes nothing here.
- **Sweep scores** — the running up/down sweep counts over `observations_seen`,
  supplied by the service (counts are genuinely between-step state).
- **Absorption** — the `AbsorptionResult.score` for whichever side fired, else 0.
- **Replenishment / persistence** — the max `persistence_score` across active
  zones (a zone that keeps standing and refilling is the durable one).
- **Velocity** — `(consumed + removed) / displayed` resting liquidity: high is a
  churning, contested book; low is a resting, stacked one.

## No magic weights

The few mappings are linear and named (`_DISTANCE_CAP_BPS`, the analyzer
thresholds in `analyzers.py`). Nothing in the vector is an opaque composite
score — each feature names a single measurable quantity, and the
normalisation constants are documented in place so a reader can see and change
them.

## Determinism

`extract_features` is a pure function of the observation, the live zones and
the running counters the caller supplies. Feed a recorded stream through
`service.replay` and you get the identical feature sequence — look-ahead-free
because each step reads only its own data.
