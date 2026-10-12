# Market Intelligence — Features & Configuration

The canonical `MarketFeatures` vector the Signal Engine consumes, plus the
configuration knobs and limitations.

## The feature vector

`extract_features` distills the composed reads into a flat, bounded,
descriptive vector — every field maps to a single measurable/derived quantity,
never a probability and never a decision.

| Feature | Range | Source |
|---|---|---|
| `trend_strength` | 0..1 | structure read |
| `structure_strength` | 0..1 | trend_strength × coherence (HH+HL or LH+LL) |
| `breakout_strength` | 0..1 | structural breakout signal confidence |
| `momentum` | % | last-bar return (or price-action momentum) |
| `adx` | 0..1 | ADX / 100 (technical or regime) |
| `rsi` | 0..100 | RSI (kept raw — a bounded oscillator) |
| `atr_pct` | frac | ATR / last price |
| `volatility` | 0..1 | ATR% × `_VOL_SCALE` (33) capped |
| `vwap_distance` | % | (price − VWAP) / VWAP × 100, signed |
| `relative_volume` | ratio | last vol / baseline vol |
| `volume_delta` | −1..1 | estimated net-flow share |
| `volume_state` | label | expanding / contracting / steady |
| `price_action` | label | the PriceActionKind |
| `volatility_state` | label | expanding / contracting / steady / unknown |
| `regime` | label | the 6-state regime |
| `regime_confidence` | 0..1 | regime confidence band (0 if unreliable) |

Plus `symbol`, `timeframe`, `is_mock` (the honesty flag).

## The mappings (documented, not magic)

- `adx` is normalised ÷ `_ADX_MAX` (100) — a 0..100 scale mapped to 0..1.
- `volatility` maps ATR-fraction-of-price to 0..1 via a linear cap
  (`_VOL_SCALE` = 33, so ~3% daily ATR reads as full volatility). A heuristic,
  not a fit.
- `structure_strength` is the structure read's `trend_strength` weighted by
  pattern coherence (a clean HH+HL or LH+LL keeps full strength, a muddled
  pattern halves it).
- `breakout_strength` maps a structural breakout/breakdown signal's confidence
  band (low 0.33 / medium 0.66 / high 1.0); a confirmed price-action breakout
  reinforces it.
- `regime_confidence` is the regime analysis's own band mapped to 0..1, zeroed
  when `is_reliable` is False.

## Configuration

- `PriceActionService(lookback, min_confirm_bars, vol_period)` — the channel
  window, the multi-candle confirmation bar, the vol baseline period.
- `VolumeActionService(period, min_bars)` — baseline window, min bars.
- `RegimeTracker(window, confirm)` — the dwell/confirm bars for transitions.
- `LOW_VOL_ATR_PCT` — the calm-tape ATR threshold (0.5%).
- `MarketIntelService(...)` — composes the services; injectable for tests.

## Limitations

- **Estimated buy/sell volume** — a bar-geometry estimate, not a tape; real
  aggressor feeds take precedence.
- **Price action is the latest bar(s)** — it describes recent behaviour, not a
  durable signal; `min_confirm_bars` is the only multi-candle gate.
- **Regime transitions confirm after the fact** — by design, `confirm` reads
  must pass before the event fires, so a real change is reported late rather
  than a flicker early.
- **All features are descriptive** — the Signal Engine weighs them; none is a
  standalone edge.
