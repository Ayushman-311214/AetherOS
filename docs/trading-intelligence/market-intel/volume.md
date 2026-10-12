# Market Intelligence — Volume

A deterministic volume/price-action read over OHLCV bars — what every
timeframe has, complementing the liquidity layer's tape flow (which needs
executed prints).

## The reads

- **Relative volume / participation** — last volume ÷ baseline volume-MA:
  `high` ≥ 1.5, `low` ≤ 0.75, else `average`.
- **Expansion / contraction** — last volume vs the prior-window mean:
  `expanding` ≥ 1.5×, `contracting` ≤ 0.75×, else `steady`.
- **Estimated buy/sell split** — see below.
- **Delta / net flow** — `delta = est_buy − est_sell`;
  `net_flow = delta / total` in [-1,1].
- **Volume-price divergence** — price rising on *falling* volume → bearish
  divergence (weak backing); price falling on *falling* volume → bullish
  divergence (sellers losing conviction). Same-sign = confirmation, not
  divergence.

## The buy/sell split is *estimated*

Bars carry **no aggressor direction**, so there is no true buy/sell split to
read. The service estimates one from **close-location-in-range (CLV)**: each
bar's volume is split by where the close sat in its high-low range — a close
near the high attributes most volume to buyers, near the low to sellers.

```
clv  = ((close - low) - (high - close)) / (high - low)   in [-1,1]
buy  = volume * (1 + clv) / 2
sell = volume * (1 - clv) / 2
```

This is an **estimate** — a bar is not a tape — so the model names it
`estimated_buy_volume`/`estimated_sell_volume` and records a limitation saying
so. Where a real aggressor feed exists (the liquidity layer's tape), it takes
precedence; this is the honest bar-level fallback.

## Honesty

`VolumeAnalysis2` reports the numbers and the estimate label — participation,
state, split, `net_flow`, `delta`, `divergence` — never "volume confirms a
move" as fact. Thin data → `unknown`. Mock data → a limitation.
