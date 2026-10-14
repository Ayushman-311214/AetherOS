# Market Intelligence — Concepts

The non-liquidity market-intelligence layer (Phase 4): market structure, price
action, volume/price action, technical indicators and market regime — the
complement to the order-book/tape liquidity engine (Phase 2).

## The honest four-way split

Every read obeys the RAW DATA / OBSERVATION / DERIVED METRIC / INTERPRETATION
distinction:

- **RAW DATA** — the OHLCV candles themselves, unchanged.
- **OBSERVATION** — measured values straight off the bars: highs/lows, swing
  pivots, last close, bar volume, returns.
- **DERIVED METRIC** — computed quantities: trend strength, RSI/ATR/MACD,
  relative volume, estimated buy/sell split, momentum, ADX, regime
  classification. Derived, never asserted as raw fact.
- **INTERPRETATION** — what a read *suggests*. This layer produces evidence and
  features only — **never a trading decision**, never a "this will happen".

## The reads, and what each honestly answers

| Read | Answers | NOT a prediction |
|---|---|---|
| **Structure** | HH/HL/LH/LL, trend/range, support/resistance, breakout/breakdown | a level "will hold" |
| **Price action** | momentum, rejection, breakout/failed-breakout, acceptance, range, vol expansion/contraction | next bar's direction |
| **Volume** | relative volume, expansion/contraction, est. buy/sell split, net flow, divergence | a real aggressor split |
| **Indicators** | VWAP/EMA/SMA/RSI/ATR/MACD/Bollinger/ADX | signals — indicators are *evidence* |
| **Regime** | TRENDING_BULLISH/BEARISH, RANGING, HIGH/LOW_VOLATILITY, TRANSITION | which way it transitions |

## Key honesty rules

- **Complex structure needs more than one candle.** Rejection, failed breakout
  and acceptance require the configured confirmation (`min_confirm_bars`) — a
  single wick or poke is evidence, not a verdict.
- **Indicators are evidence, not signals.** An RSI of 72 is a number; the
  signal layer decides what it means.
- **Buy/sell volume is *estimated*.** Bars carry no aggressor feed, so the
  split is derived from close-location-in-range and labelled "estimated" — a
  real tape read takes precedence where one exists.
- **Regime transitions are confirmed, not flickers.** `MarketRegimeChanged`
  fires only when the regime settles into a new state (the `confirm` dwell
  rule), with TRANSITION reporting a genuinely-mixed window.
- **UNKNOWN is first-class.** Thin/mock/unusable data yields UNKNOWN reads and
  `is_mock` flags, never a confident read it didn't earn.
