# Signal Engine — Contradictory Evidence

How the engine surfaces — never hides — conflicting evidence.

## The split is structural, not cosmetic

`EvidenceLedger` separates reliable directional evidence into
`supporting` (agreeing with the fused direction) and `opposing` (contradicting
it). Both are carried on the `SignalAssessment` verbatim — there is no code
path that drops the losing side.

```
Bullish evidence:      Contradicting evidence:
+ structure            - resistance wall
+ liquidity            - volatility
+ volume               - bearish news
```

## How it shows up

- **`supporting` / `contradicting`** — both tuples on the assessment, each
  item keeping its full explanation (type, detail, direction, weight,
  provenance, is_reliable).
- **`agreement`** — the share of *reliable directional weight* on the fused
  side (`supporting / (supporting + opposing)`). A 50/50 split reads 0.5.
- **`confidence`** — agreement is a 40% input to the confidence band, so a
  contradiction lowers confidence even when the raw lean looks strong.
- **`risk_factors`** — a contradiction is itself named as a risk factor.
- **`limitations`** — `"{n} contradicting evidence item(s) surface the
  disagreement; the read is weaker for it."`

## The honesty rule

A signal under disagreement is a **weaker, more honest signal** — the engine
reports the lean *and* the friction against it, and the confidence and
actionability reflect both. It never "resolves" a contradiction by hiding the
losing side, never averages a strong conflicting item into silence, and never
lets a mock or unreliable item *create* a fake contradiction either
(unreliable items are excluded from both sides).

## When both sides are thin

If there's little reliable directional evidence either way, `agreement` is
low, `coverage` is low, and the assessment reads LOW confidence — the honest
"we don't have a clear case" rather than a forced directional call.
