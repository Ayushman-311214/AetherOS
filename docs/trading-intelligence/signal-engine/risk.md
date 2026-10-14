# Signal Engine — Risk Model

How the assessment carries risk geometry, and the "no false precision" rule.

## What the risk fields carry

`SignalAssessment` exposes the deterministic risk engine's output
(`RiskAssessment`), when wired:

- **`entry`** — the proposed entry price (the analysis's last price).
- **`invalidation`** — the explicit condition that would void the thesis
  (a stop below/above a structural level or an ATR stop), as a string — never
  a fabricated number when no stop exists.
- **`targets`** — laddered structural/projected targets.
- **`risk_reward_ratio`** — reward ÷ risk per unit.
- **`risk_band`** — LOW / MEDIUM / HIGH / UNKNOWN volatility-aware risk.
- **`risk_factors`** — named risk considerations (high volatility, wide stop,
  contradicting evidence, missing sources).

## Volatility-aware risk

The risk engine bases the stop on ATR when available (a volatility-aware stop
distance) or a structural level as fallback; `volatility_risk`/`overall_risk`
are `RiskBand`s mapped from ATR-as-fraction-of-price (UNKNOWN when ATR is
absent — never a fabricated MEDIUM). `stop_distance_pct` names how wide the
stop is, feeding the "wide stop increases tail risk" risk factor.

## Downside / upside scenarios

The risk geometry is the scenario contract:

- **Upside** — `targets` (where the read pays off).
- **Downside** — `stop_loss` + `stop_distance_pct` + `invalidation` (where the
  thesis is wrong and how much it costs).
- `risk_reward_ratio` weighs the two; `is_actionable` requires it to meet the
  configured minimum.

## No false precision

When the risk engine isn't wired or can't compute (no directional side, no
usable geometry), the assessment does **not** invent levels:

- `entry`, `risk_reward_ratio`, `targets` are `None`/`()`.
- `invalidation` carries an honest string — "no invalidation computed; risk
  engine not wired" — not a made-up number.
- `risk_band` is `UNKNOWN` rather than a guessed band.

This is the structural enforcement of "do not provide false precision": a
missing piece of risk geometry is reported as missing, not estimated.
