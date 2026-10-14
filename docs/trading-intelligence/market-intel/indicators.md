# Market Intelligence — Technical Indicators

All indicators the brief names already exist, modular and deterministic, in
`trading/indicators/core.py` — reused, not re-implemented.

## The library

Pure numpy, vectorised, causal (each output index uses only inputs up to it):

| Indicator | Function | What it reads |
|---|---|---|
| SMA | `sma(values, period)` | simple moving average |
| EMA | `ema(values, period)` | exponential moving average |
| RSI | `rsi(values, period)` | relative-strength oscillator (0–100) |
| MACD | `macd(values, f, s, sig)` | macd/signal/histogram |
| ATR | `atr(high, low, close, period)` | average true range |
| Bollinger | `bollinger(values, period)` | middle/upper/lower bands |
| VWAP | `vwap(high, low, close, vol)` | volume-weighted average price |
| ADX | `adx(high, low, close, period)` | trend strength (0–100) |
| Volatility | `volatility(values, period)` | rolling std of returns |
| Volume MA | `volume_ma(volume, period)` | baseline volume |
| Volume profile | `volume_profile(...)` | POC + value area |
| Z-score | `zscore(values, period)` | std devs from mean |
| SuperTrend | `supertrend(...)` | trend line + stop |

`TechnicalAnalysisService.compute(data)` packages these into a
`TechnicalSnapshot` — last finite value of each, `None` where an indicator
didn't warm up (honest "not enough data", never a fabricated number). Default
params are in `DEFAULT_PARAMS` and exposed on `snapshot.params` for
reproducibility.

## Indicators are evidence, not signals

The spec's rule is enforced structurally: an indicator output is a *number*,
surfaced to the feature vector as `rsi`, `adx`, `atr_pct`, `vwap_distance`,
`momentum`, `volatility`. Nothing in the layer turns `rsi = 72` into "overbought
→ sell" — the Signal Engine / critic decides what a reading means. A snapshot
reports the indicators computed; it never asserts a trade.

## Causality (no look-ahead)

Every function is causal — `out[t]` depends only on inputs `≤ t`. The
`TechnicalSnapshot` reads the *last finite* value, so a warm-up region is
`None`, never a partial-window guess.
