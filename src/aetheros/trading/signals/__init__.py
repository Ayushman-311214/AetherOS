"""
The signal engine (spec Phase 8).

A :class:`TradeSignal` is the system's proposed *action* -- BUY or SELL, with
its confidence, risk band, reasoning and supporting evidence -- and this
package is where proposals come from and where they are gated.

The composition is strictly one-directional over layers that already exist:

    StrategySetup (the reading)   ──►  RiskAssessment (the geometry)
    CriticReport (the verdict)    ──►  gates ──►  TradeSignal | explained None

The gates (:mod:`aetheros.trading.signals.gates`) are the whole intelligence
of the layer: side agreement, actionability, the critic's approval, and
risk/reward. Everything else here is assembly. A signal is never "more
confident than the adversary that judged it", never carries a quantity, and
nothing in this package can reach a broker -- the §9 path continues through
the decision/policy/execution layers that later phases add.

Exit signals (EXIT / PARTIAL_EXIT / UPDATE_STOP_LOSS) are the same
:class:`TradeAction` vocabulary applied to an open position, which requires a
position manager to exist first; they are part of this package's contract but
are generated only once the position layer (a later phase) supplies open
positions to manage. This increment deliberately implements the entry side
against the layers that exist.
"""

from __future__ import annotations

from .gates import evaluate_candidate

__all__ = ["evaluate_candidate"]
