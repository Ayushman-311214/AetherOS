"""
Backtesting, prediction tracking, outcomes and calibration (Phase 6).

The layer that answers "does the intelligence actually work?" -- it replays a
historical ``MarketData`` series through the *same* production components the
live path uses (market-intel, signal-engine, probability), turns each step into
an auditable prediction, and measures the forward outcome against the candles
that unfolded.

Three rules define the whole layer:

* **No look-ahead, structurally.** The only slicing primitive is
  ``MarketData.window(0, t+1)`` -- a step sees *exactly* the bars up to itself
  and never one after. That is the same past-only guarantee the live replay
  and walk-forward folds already use, so a backtest cannot peek ahead.
* **Production components only.** The pipeline composes the real
  ``MarketIntelService`` / ``SignalEngineService`` / ``ProbabilityService`` --
  there is no fake analysis implementation to drift from production.
* **Honest evaluation.** Outcomes are PENDING / RESOLVED / UNRESOLVABLE;
  a thin or mock sample is reported, never a fabricated track record.
"""

from __future__ import annotations

from .evaluator import OutcomeEvaluator, PredictionLike
from .metrics import BacktestMetrics, evaluate
from .outcome import EnrichedOutcome
from .pipeline import BacktestPipeline, BacktestResult

__all__ = [
    "BacktestMetrics",
    "BacktestPipeline",
    "BacktestResult",
    "EnrichedOutcome",
    "OutcomeEvaluator",
    "PredictionLike",
    "evaluate",
]
