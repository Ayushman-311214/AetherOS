"""
Trading journal: one traceable entry per paper trade (Phase 11).

The journal describes; it never decides. Entries are built from the settled
trades a simulation report already carries, so a paper trade creates a
complete record automatically wherever the caller asks for one.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import Direction, SourceTier, Timeframe
from aetheros.trading.domain.journal import JournalEntry
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.simulation import SimulatedTrade, SimulationExitReason
from aetheros.trading.services.journal_service import JournalService

from .conftest import make_market_data


def _trade(**overrides) -> SimulatedTrade:
    fields: dict = {
        "position_id": "sim-TEST-10-1",
        "instrument_key": "TEST",
        "direction": Direction.UP,
        "quantity": 10.0,
        "entry_price": 100.0,
        "entry_bar": 10,
        "exit_price": 105.0,
        "exit_bar": 15,
        "reason": SimulationExitReason.TARGET,
        "realized_pnl": 50.0,
        "commission_paid": 1.0,
    }
    fields.update(overrides)
    return SimulatedTrade(**fields)


def _provenance() -> Provenance:
    return Provenance(source="simulation", tier=SourceTier.DERIVED)


def test_entry_ids_are_content_addressed() -> None:
    a = JournalEntry.from_trade(_trade(), strategy_id="trend_following")
    b = JournalEntry.from_trade(_trade(), strategy_id="trend_following")
    assert a.entry_id == b.entry_id
    assert a.entry_id.startswith("jrnl_")


def test_entry_preserves_trade_numbers_verbatim() -> None:
    entry = JournalEntry.from_trade(_trade(), strategy_id="trend_following")
    assert entry.instrument_key == "TEST"
    assert entry.direction is Direction.UP
    assert entry.quantity == 10.0
    assert entry.entry_price == 100.0
    assert entry.exit_price == 105.0
    assert entry.realized_pnl == 50.0
    assert entry.commission_paid == 1.0
    assert entry.net_pnl == pytest.approx(49.0)
    assert entry.exit_reason is SimulationExitReason.TARGET


def test_service_builds_one_entry_per_trade_in_order() -> None:
    from aetheros.trading.domain.enums import DataQualityStatus
    from aetheros.trading.domain.instrument import Instrument
    from aetheros.trading.domain.simulation import SimulationReport

    trades = (
        _trade(position_id="sim-TEST-10-1", exit_bar=15),
        _trade(position_id="sim-TEST-20-2", entry_bar=20, exit_bar=25,
               exit_price=98.0, realized_pnl=-20.0),
    )
    report = SimulationReport(
        instrument=Instrument.parse("TEST"),
        timeframe=Timeframe.D1.value,
        strategy_id="trend_following",
        bars=30,
        warmup=5,
        initial_equity=100_000.0,
        final_equity=100_029.0,
        realized_pnl=30.0,
        unrealised_pnl=0.0,
        commission_paid=2.0,
        max_drawdown=0.001,
        sharpe=None,
        statistics=None,
        trades=trades,
        equity_curve=tuple([100_000.0] * 30),
        signals_fired=2,
        orders_filled=2,
        orders_rejected=0,
        admissions_refused=0,
        entries_skipped=0,
        exit_counts=(("target", 1), ("stop", 1)),
        assumptions=("test fill model",),
        provenance=_provenance(),
        quality=DataQuality(status=DataQualityStatus.OK),
        is_reliable=False,
        limitations=("test run",),
    )
    entries = JournalService().entries_for_report(report)
    assert len(entries) == 2
    assert entries[0].entry_bar == 10
    assert entries[1].entry_bar == 20
    assert all(e.strategy_id == "trend_following" for e in entries)
    assert all(e.timeframe == "1d" for e in entries)


def test_empty_report_yields_no_entries() -> None:
    from aetheros.trading.domain.enums import DataQualityStatus
    from aetheros.trading.domain.instrument import Instrument
    from aetheros.trading.domain.simulation import SimulationReport

    report = SimulationReport(
        instrument=Instrument.parse("TEST"),
        timeframe=Timeframe.D1.value,
        strategy_id="trend_following",
        bars=30,
        warmup=30,
        initial_equity=100_000.0,
        final_equity=100_000.0,
        realized_pnl=0.0,
        unrealised_pnl=0.0,
        commission_paid=0.0,
        max_drawdown=0.0,
        sharpe=None,
        statistics=None,
        trades=(),
        equity_curve=tuple([100_000.0] * 30),
        signals_fired=0,
        orders_filled=0,
        orders_rejected=0,
        admissions_refused=0,
        entries_skipped=0,
        exit_counts=(),
        assumptions=("test fill model",),
        provenance=_provenance(),
        quality=DataQuality(status=DataQualityStatus.OK),
        is_reliable=False,
        limitations=("too short",),
    )
    assert JournalService().entries_for_report(report) == ()


def test_entry_to_dict_shape() -> None:
    entry = JournalEntry.from_trade(
        _trade(),
        strategy_id="trend_following",
        timeframe="1d",
        provenance=_provenance(),
    )
    payload = entry.to_dict()
    assert payload["entry_id"].startswith("jrnl_")
    assert payload["strategy_id"] == "trend_following"
    assert payload["direction"] == "up"
    assert payload["exit_reason"] == "target"
    assert payload["net_pnl"] == pytest.approx(49.0)
    assert payload["provenance"]["tier"] == "derived"


def test_journal_survives_a_mock_run_honestly() -> None:
    data = make_market_data([100.0 + i for i in range(30)], tier=SourceTier.MOCK)
    assert data.provenance.is_mock
    entry = JournalEntry.from_trade(
        _trade(),
        strategy_id="trend_following",
        is_mock=True,
        provenance=data.provenance,
    )
    assert entry.is_mock is True
    assert entry.provenance is not None
    assert entry.provenance.is_mock is True


# ==============================================================
# Entry side: from_request / close (Phase 21 trace)
# ==============================================================


def _request():
    from .test_execution import _request as _exec_request

    return _exec_request()


def test_from_request_captures_the_decision_context_without_outcome() -> None:
    request = _request()
    entry = JournalEntry.from_request(request, entry_bar=10, timeframe="1d")
    assert entry.entry_id.startswith("jrnl_")
    assert entry.instrument_key == request.instrument.key
    assert entry.strategy_id == request.strategy_id
    assert entry.direction is request.direction
    assert entry.entry_price == request.entry
    assert entry.stop_loss == request.stop_loss
    assert entry.take_profit == request.take_profit
    assert entry.risk_reward_ratio == request.risk_reward_ratio
    assert entry.entry_reason == request.reasoning
    # The evidence chain is linked by content id -- the trace back to the
    # market reads the decision rested on.
    assert entry.evidence_ids == tuple(item.id for item in request.evidence)
    # No outcome is known yet -- and none is estimated.
    assert entry.exit_price is None
    assert entry.exit_reason is None
    assert entry.realized_pnl is None
    assert entry.net_pnl is None


def test_from_request_ids_are_content_addressed() -> None:
    request = _request()
    assert (
        JournalEntry.from_request(request, entry_bar=10).entry_id
        == JournalEntry.from_request(request, entry_bar=10).entry_id
    )


def test_close_settles_pnl_from_the_exit_facts() -> None:
    entry = JournalEntry.from_request(_request(), entry_bar=10)
    closed = entry.close(
        exit_price=105.0,
        exit_bar=15,
        exit_reason=SimulationExitReason.TARGET,
        commission_paid=1.0,
    )
    assert closed.exit_price == 105.0
    assert closed.exit_reason is SimulationExitReason.TARGET
    # (105 - entry) * qty - commission, by the position model's arithmetic.
    assert closed.realized_pnl == pytest.approx(
        (105.0 - closed.entry_price) * closed.quantity
    )
    assert closed.net_pnl == pytest.approx(closed.realized_pnl - 1.0)
    # The open record is untouched.
    assert entry.exit_price is None


def test_close_refuses_a_second_settlement_or_a_backwards_exit() -> None:
    entry = JournalEntry.from_request(_request(), entry_bar=10)
    closed = entry.close(
        exit_price=105.0, exit_bar=15, exit_reason=SimulationExitReason.TARGET
    )
    with pytest.raises(ValueError, match="already closed"):
        closed.close(
            exit_price=106.0, exit_bar=16, exit_reason=SimulationExitReason.TARGET
        )
    with pytest.raises(ValueError, match="after the bar"):
        entry.close(
            exit_price=105.0, exit_bar=10, exit_reason=SimulationExitReason.STOP
        )


def test_annotate_records_human_reflection_without_fabrication() -> None:
    entry = JournalEntry.from_trade(_trade(), strategy_id="trend_following")
    assert entry.emotion is None
    assert entry.lesson is None
    noted = entry.annotate(emotion="calm", lesson="Let winners run to target.")
    assert noted.emotion == "calm"
    assert noted.lesson == "Let winners run to target."
    assert entry.emotion is None  # the record is untouched
    blank = entry.annotate(emotion="  ", lesson="")
    assert blank.emotion is None
    assert blank.lesson is None


def test_enriched_entry_to_dict_round_trips() -> None:
    entry = JournalEntry.from_request(
        _request(),
        entry_bar=10,
        timeframe="1d",
        screenshot={"source": "screen", "width": 80, "height": 60},
    ).annotate(emotion="patient", lesson="Trusted the setup.")
    closed = entry.close(
        exit_price=105.0, exit_bar=15, exit_reason=SimulationExitReason.TARGET
    )
    payload = closed.to_dict()
    assert payload["stop_loss"] is not None
    assert payload["take_profit"] is not None
    assert payload["emotion"] == "patient"
    assert payload["lesson"] == "Trusted the setup."
    assert payload["screenshot"] == {"source": "screen", "width": 80, "height": 60}
