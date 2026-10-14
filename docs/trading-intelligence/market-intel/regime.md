# Market Intelligence — Market Regime

The 6-state regime model, the deterministic base read it builds on, and the
transition tracker that emits `MarketRegimeChanged` only on a real change.

## The 6 states

```
TRENDING_BULLISH   -- directional up-trend (ADX strong, rising)
TRENDING_BEARISH   -- directional down-trend (ADX strong, falling)
RANGING            -- non-trending, oscillating (ADX weak)
HIGH_VOLATILITY    -- whipsawing, high realised vol (ATR% high)
LOW_VOLATILITY     -- calm, compressed realised vol (ATR% low)
TRANSITION         -- the regime is mid-shift (temporal state)
UNKNOWN            -- mock / unusable / too-thin data (honest)
```

## How it is derived (`classify_state`)

The deterministic `RegimeService` produces a 5-state `MarketRegime`
(TRENDING_UP/DOWN, RANGING, VOLATILE, UNKNOWN) from ADX (trend strength) and
ATR-as-fraction-of-price (realised vol). `classify_state` maps that read into
the 6-state vocabulary:

- TRENDING_UP → `TRENDING_BULLISH`; TRENDING_DOWN → `TRENDING_BEARISH`.
- VOLATILE → `HIGH_VOLATILITY`.
- RANGING → `LOW_VOLATILITY` when realised vol is genuinely compressed
  (`atr_pct ≤ LOW_VOL_ATR_PCT`, default 0.5%) — a *calm* range — else `RANGING`
  (a choppy-but-not-calm range is not low-volatility).
- UNKNOWN → `UNKNOWN` (mock/thin data never earns a confident regime).

`LOW_VOLATILITY` and `TRANSITION` are the two genuinely *temporal* states a
single snapshot can't express — the former needs a vol baseline, the latter is
by definition a property of successive reads.

## The transition tracker (`RegimeTracker`)

Emits `MarketRegimeChanged` **only on a confirmed change**, per configured
logic — never on a flicker:

- `window` — a short deque of recent classified states.
- `confirm` — the new state must hold for this many consecutive reads to be
  adopted as the regime (a confirmed flip). This is the dwell bar that stops a
  one-off noisy read from announcing a regime that immediately reverts.
- A *mixed* window (the running state no longer dominant, new state not yet
  confirmed) reports `TRANSITION` — the honest "between regimes" read rather
  than a fabricated confident label.
- An unchanged state or an unconfirmed new read emits `None` — no event.

So the event fires exactly when the regime *actually* changed: establishment
(no event on the first read), a confirmed flip, or a genuine transition.

## Honesty

- Regime is a *characterisation*, not a prediction — `direction` is the new
  regime's bias, never a probability.
- `is_reliable` follows the analysis's own gate; `is_mock` is surfaced so a
  synthetic read never becomes a real regime change.
- The tracker is a pure function of the ordered reads fed to it — replaying the
  same window reproduces the same transitions (deterministic, backtestable).
