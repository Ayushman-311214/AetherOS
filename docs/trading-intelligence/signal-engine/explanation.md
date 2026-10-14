# Signal Engine — Explanation

Structured explanations, with the LLM as narrator — never as the source of a
number.

## What the assessment already explains

`SignalAssessment.to_dict()` is itself a structured explanation: it exposes
*what* the engine concluded (direction, expected_move, risk geometry) **and**
*why* — every supporting and contradicting `Evidence` item with its full
WHAT/WHEN/SOURCE/STRENGTH/DIRECTION/CONFIDENCE/WHY/LIMITATIONS fields, plus
the missing sources, coverage, and risk factors.

A consumer can render an explanation straight from the payload — no LLM needed
to produce the substance:

```
Direction:     bullish (up)
Probability:   74%  (calibrated; or "null — not reliable")
Confidence:    HIGH  (reliability+coverage+agreement band)
R:R:           1:2.8    Invalidation: 25,120
Supporting:    structure (+0.8), liquidity (+0.6), volume (+0.4)
Contradicting: resistance wall (-0.7), volatility (-0.3)
Missing:       fundamentals, options
Coverage:      0.63
```

## The division of labour

- **Deterministic core (this layer)** — produces every number, score, band,
  level, and evidence item. This is the source of truth.
- **Existing `Explanation`/`ExplanationService`** — already turns a
  `TradingReport` into a de-duplicated supporting/opposing ledger + a plain
  summary, with the same "only reliable evidence moves the weight" rule.
- **The LLM** — may *narrate* the structured assessment into prose ("the
  bullish continuation is backed by structure and liquidity but meets a
  resistance wall"), but can never be where a number comes from. If the LLM
  writes a number the engine didn't produce, that number is wrong — so the
  contract is: the LLM explains the structure, never invents it.

## What it must never do

- Fabricate a probability or a confidence band not in the payload.
- Hide or average away `contradicting` items.
- Present a `MissingSource` as if it had voted.
- Upgrade a `raw_evidence_score` or `model_score` into a probability.

## Example (the spec's shape, honestly populated)

```
Bullish continuation
Probability:  73%   (calibrated estimate, when reliable — else null)
Confidence:   78%   (qualitative band)
R:R:          1:2.8
Invalidation: 25,120
Evidence:     structure +, liquidity +, volume +, resistance −, volatility −
```

These are the fields of `SignalAssessment` — representation, never hard-coded
output.
