# 06 — Signal Model

A signal in AetherOS is a **proposal with a verdict trail**, never a bare
`BUY`/`SELL` and never an order. Two boundaries are enforced by construction:

- **A signal is a proposal, never an order.** There is no order construction,
  quantity, or submission in the signal layer. Turning a proposal into an
  execution is the execution engine's job, behind the §9 chain
  (strategy → decision → policy → risk → execution validation → broker).
- **"No signal" is data, not an exception.** Most contexts have no edge; the
  reason is recorded rather than raised, and §28 requires it be carried.

## The two signal objects

`TradeSignal` (`domain/trade.py`) is the **output contract** — what a strategy
proposes: `action`, `direction`, `confidence`, `risk` band, `reasoning`,
`supporting_evidence`, plus executable `entry`/`stop_loss`/`take_profit`
geometry when the action is an entry. It validates that a BUY/SELL has the
geometry to be judged.

`SignalCandidate` (`domain/signal.py`) is the **record of why a signal was or
wasn't produced**:

```python
SignalCandidate(
    strategy_id, strategy_name, category, timeframe,
    direction,            # UP or DOWN only -- no SIDEWAYS candidate exists
    signal,               # TradeSignal, or None for an explicit no-signal
    risk,                 # the RiskAssessment the candidate was judged on
    critique,             # the CriticReport verdict trail
    setup,                # the StrategySetup reading it was built from
    rejections,           # every gate it failed, named
    provenance, quality, limitations,
    candidate_id,         # content-addressed
)
```

A candidate is directional or it is an explicit no-signal — a market with no
edge produces no proposal and the reason lives in `rejections`. `fired` is True
only when `signal` is present.

## What a signal supports (the brief's list)

| Required field | Where it lives |
|---|---|
| direction | `direction` (UP/DOWN) |
| probability | `ProbabilityEstimate` on the report (calibrated, gated) |
| confidence | `Confidence` band on the `TradeSignal` |
| expected_move | risk geometry (`entry`/`take_profit`/`stop_loss`) |
| risk_reward | `RiskAssessment.risk_reward_ratio` |
| invalidation | `RiskAssessment.invalidation` |
| time_horizon | `PredictionRecord.horizon_bars` / report `horizon` |
| evidence | `TradeSignal.supporting_evidence` + analysis `evidence` |
| risk_factors | `RiskAssessment` + `limitations` |
| generated_at | `created_at` / `PredictionRecord.created_at` |
| model/strategy id | `strategy_id` + `model_pipeline` |

## Probability ≠ certainty

`ProbabilityEstimate.p_up`/`p_down` is a *calibrated* estimate gated by an
out-of-sample edge check — never a promise. `Confidence` is a separate
qualitative band (LOW/MEDIUM/HIGH); the two are never conflated. A report
surfaces `probability` only when `is_reliable`, else `None`.

## SignalEvaluation — the panel view

`SignalEvaluation` aggregates every strategy's candidate. `consensus` is the
side the *fired* signals agree on, or `UNKNOWN` on mixed sides — disagreement is
surfaced, never averaged away. An evaluation with no fired candidates is the
honest "no trade" answer, with the reason in `limitations`.
