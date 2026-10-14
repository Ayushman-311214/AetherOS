"""
Counterfactual analysis (spec Phase 2 -- was the decision the right call?).

The classifier reads a closed journal entry's own numbers -- entry, exit,
stop/target, recorded P&L, evidence -- and assigns one honest post-trade
category. These tests pin the verdicts: a target hit with a profit supports
the thesis; a stop-out is the geometry firing (INVALIDATION), not a judgement
error; a thin-evidence trade is MISSING_EVIDENCE; a loss is the
NO_TRADE_ALTERNATIVE the desk should have taken.
"""

from __future__ import annotations

import pytest

from aetheros.trading.analytics.counterfactual import (
    CounterfactualKind,
    CounterfactualService,
)
from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.journal import JournalEntry
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.domain.simulation import SimulationExitReason


def _entry(
    *,
    exit_reason=SimulationExitReason.TARGET,
    net: float = 50.0,
    evidence=("ev_a", "ev_b"),
    direction=Direction.UP,
    entry_price=100.0,
    exit_price=110.0,
    exit_bar=5,
) -> JournalEntry:
    return JournalEntry(
        entry_id="jrnl_test",
        instrument_key="TEST",
        strategy_id="strat",
        direction=direction,
        quantity=10.0,
        entry_price=entry_price,
        entry_bar=0,
        exit_price=exit_price,
        exit_bar=exit_bar,
        exit_reason=exit_reason,
        realized_pnl=net,
        commission_paid=0.0,
        net_pnl=net,
        return_pct=net / 1000.0,
        evidence_ids=evidence,
        provenance=Provenance(source="test", tier=SourceTier.PRIMARY),
    )


def test_an_open_entry_is_unscored():
    entry = _entry().from_dict(_entry().to_dict())  # still has exit fields
    # Build a genuinely open entry: no exit.
    open_entry = JournalEntry(
        entry_id="jrnl_open",
        instrument_key="TEST",
        strategy_id="strat",
        direction=Direction.UP,
        quantity=1.0,
        entry_price=100.0,
        entry_bar=0,
        exit_price=None,
        exit_bar=None,
        exit_reason=None,
        realized_pnl=None,
        commission_paid=0.0,
        net_pnl=None,
        return_pct=None,
    )
    result = CounterfactualService().classify(open_entry)
    assert result.kind is CounterfactualKind.UNSCORED


def test_a_target_win_supports_the_thesis():
    result = CounterfactualService().classify(_entry(net=50.0))
    assert result.kind is CounterfactualKind.SUPPORT
    assert result.won is True


def test_a_stop_exit_is_invalidation_not_contradiction():
    result = CounterfactualService().classify(
        _entry(exit_reason=SimulationExitReason.STOP, exit_price=98.0, net=-20.0)
    )
    assert result.kind is CounterfactualKind.INVALIDATION
    assert result.won is False


def test_a_thin_evidence_trade_is_missing_evidence():
    result = CounterfactualService().classify(_entry(evidence=()))
    assert result.kind is CounterfactualKind.MISSING_EVIDENCE


def test_a_loss_is_the_no_trade_alternative():
    result = CounterfactualService().classify(
        _entry(
            exit_reason=SimulationExitReason.FORCED_END,
            exit_price=95.0,
            net=-50.0,
        )
    )
    assert result.kind is CounterfactualKind.NO_TRADE_ALTERNATIVE
    assert result.won is False
