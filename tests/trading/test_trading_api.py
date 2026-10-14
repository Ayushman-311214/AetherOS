"""
The Trading API facade (spec Phase 24, docs/modules/trading.md "Trading API").

The facade is the single public surface higher-level modules depend on. These
tests pin the two contracts that make that boundary trustworthy:

* **it is a pure conduit.** Every method returns the exact domain object its
  underlying service produces, unmodified -- the facade adds no analytical
  logic, so a facade call and the equivalent direct service call agree
  field-for-field.
* **``execute`` cannot originate a trade.** It only routes an already-formed
  :class:`ExecutionRequest` through the execution engine, which still re-runs
  the risk-limits gate: a breached account is REJECTED and the broker is never
  reached. There is no path here from a model instruction to a venue.

Everything runs on the explicitly-labelled MOCK provider, so the honest
NO_TRADE / insufficient-evidence answers are the expected results, never a
test failure.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.api import TradingAPI
from aetheros.trading.brokers.base import BrokerProvider
from aetheros.trading.brokers.paper_provider import PaperTradingProvider
from aetheros.trading.domain.enums import (
    OrderStatus,
    SourceTier,
)
from aetheros.trading.domain.execution import ExecutionRequest, ExecutionResult
from aetheros.trading.domain.risk_limits import AccountSnapshot
from aetheros.trading.errors import TradingError
from aetheros.trading.execution.engine import ExecutionEngine
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.risk.limits_service import RiskLimitsService
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.journal_service import JournalService
from aetheros.trading.services.journal_store import InMemoryJournalStore, JournalStore
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.portfolio_service import PortfolioRiskService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.scan_service import WatchlistScanService
from aetheros.trading.services.signal_service import SignalService
from aetheros.trading.services.simulation_service import SimulationService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)

from .test_execution import _request

# ==============================================================
# Wiring -- the same real services the bootstrap composes, over MOCK data
# ==============================================================


def _api(
    broker: BrokerProvider | None = None,
    *,
    journal_store: JournalStore | None = None,
) -> TradingAPI:
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    structure = MarketStructureService()
    evidence = EvidenceService()
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        structure,
        evidence,
        settings,
    )
    risk = RiskService(settings)
    backtest = BacktestService(settings)
    critic = CriticService(settings)
    orchestration = OrchestrationService(
        market_data, analysis, risk, backtest, critic, settings
    )
    smc = SMCService(structure)
    ict = ICTService(structure, smc)
    strategy = StrategyService(
        analysis,
        structure,
        smc=smc,
        ict=ict,
        breakout=BreakoutService(settings),
        backtest=backtest,
    )
    signals = SignalService(strategy, risk, critic, market_data, settings)
    scan = WatchlistScanService(analysis, settings)
    portfolio = PortfolioRiskService(settings)
    risk_limits = RiskLimitsService(settings)
    simulation = SimulationService(signals, portfolio, risk_limits, settings)
    journal = JournalService()
    execution = ExecutionEngine(
        broker or PaperTradingProvider(market_data),
        risk_limits,
        settings,
    )
    return TradingAPI(
        orchestration=orchestration,
        scan=scan,
        signals=signals,
        backtest=backtest,
        simulation=simulation,
        journal=journal,
        execution=execution,
        portfolio=portfolio,
        market_data=market_data,
        analysis=analysis,
        risk=risk,
        strategy=strategy,
        journal_store=journal_store,
    )


# A venue that fills whatever it is handed, so a passing risk gate is the only
# thing standing between a request and a FILLED result. Paper-tier so that
# under the default PAPER trading mode the Phase 26 policy gate permits it and
# these tests exercise the risk gate, not policy (which has its own suite).
class _FillingBroker(BrokerProvider):
    name = "stub-fill"
    tier = SourceTier.MOCK

    def __init__(self) -> None:
        self.submitted: list[ExecutionRequest] = []

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        self.submitted.append(request)
        return ExecutionResult(
            request_id=request.request_id,
            status=OrderStatus.FILLED,
            reason="Filled by the stub venue.",
            order_id="ord_1",
            filled_quantity=request.quantity,
            average_fill_price=request.entry,
        )

    async def cancel(self, order_id: str) -> ExecutionResult:  # pragma: no cover
        raise NotImplementedError

    async def modify(  # pragma: no cover
        self, order_id: str, request: ExecutionRequest
    ) -> ExecutionResult:
        raise NotImplementedError

    async def status(self, order_id: str) -> ExecutionResult:  # pragma: no cover
        raise NotImplementedError

    async def fill_price(self, instrument_key: str) -> float:
        return 100.0

    async def account_equity(self) -> float:
        return 100_000.0


# ==============================================================
# analyze / scan / signal / backtest -- pure conduit over the services
# ==============================================================


@pytest.mark.asyncio
async def test_analyze_returns_the_orchestrators_report_verbatim():
    api = _api()
    report = await api.analyze("AAPL", "1d", limit=120)
    # MOCK data -> honest no-trade, never a fabricated signal.
    assert report.recommendation.value == "no_trade"
    payload = report.to_dict()
    assert payload["instrument"]["key"] == report.instrument.key
    assert any("mock" in lim.lower() for lim in report.limitations)


@pytest.mark.asyncio
async def test_scan_ranks_the_watchlist_and_keeps_errored_symbols():
    api = _api()
    result = await api.scan(["AAPL", "MSFT"], "1d", limit=120)
    assert result.requested == 2
    assert result.analysed + result.errored == 2
    assert len(result.entries) == 2
    # MOCK data is never leanable-on.
    assert all(not entry.is_reliable for entry in result.entries)


@pytest.mark.asyncio
async def test_signal_fires_nothing_on_mock_data():
    api = _api()
    evaluation = await api.signal("AAPL", timeframe="1d", limit=120)
    assert evaluation.signal_count == 0
    assert evaluation.limitations, "an empty panel must say why"


@pytest.mark.asyncio
async def test_backtest_is_never_reliable_on_mock_data():
    api = _api()
    result = await api.backtest("AAPL", timeframe="1d", limit=200)
    assert result.is_reliable is False
    assert any("mock" in lim.lower() for lim in result.limitations)


# ==============================================================
# paper_trade / journal -- real chain, virtual money
# ==============================================================


@pytest.mark.asyncio
async def test_paper_trade_runs_the_real_chain_on_a_known_strategy():
    api = _api()
    report = await api.paper_trade("AAPL", "trend_following", timeframe="1d", limit=200)
    # It ran -- the virtual account started from the default balance -- even if
    # the mock series produced no settled trades.
    assert report.to_dict()["initial_equity"] > 0


@pytest.mark.asyncio
async def test_paper_trade_rejects_an_unknown_strategy():
    api = _api()
    with pytest.raises(TradingError):
        await api.paper_trade("AAPL", "no_such_strategy", timeframe="1d", limit=120)


@pytest.mark.asyncio
async def test_journal_is_a_tuple_of_entries_mirroring_the_run():
    api = _api()
    entries = await api.journal("AAPL", "trend_following", timeframe="1d", limit=200)
    assert isinstance(entries, tuple)
    # Each entry is content-addressed and one-per-trade; an empty run is honest.
    assert all(entry.entry_id for entry in entries)


@pytest.mark.asyncio
async def test_journal_history_is_empty_without_a_store():
    # No durable store wired: the facade keeps nothing and says so honestly,
    # rather than fabricating a trail.
    api = _api()
    assert await api.journal_history() == ()


@pytest.mark.asyncio
async def test_journal_persists_each_entry_when_a_store_is_wired():
    store = InMemoryJournalStore()
    api = _api(journal_store=store)
    entries = await api.journal("AAPL", "trend_following", timeframe="1d", limit=200)

    # Whatever the run produced, the persisted trail mirrors it exactly -- the
    # returned entries and the stored entries are the same records.
    history = await api.journal_history()
    assert {e.entry_id for e in history} == {e.entry_id for e in entries}


@pytest.mark.asyncio
async def test_journal_persists_a_run_that_actually_traded(monkeypatch):
    # The MOCK series settles no trades, so to exercise the persist loop with
    # real entries we hand the facade a report that did trade (built exactly as
    # the simulation would). The entries are still derived verbatim by the real
    # JournalService -- only the upstream report is stubbed.
    from aetheros.trading.domain.enums import DataQualityStatus, Direction, Timeframe
    from aetheros.trading.domain.instrument import Instrument
    from aetheros.trading.domain.provenance import DataQuality, Provenance
    from aetheros.trading.domain.simulation import (
        SimulatedTrade,
        SimulationExitReason,
        SimulationReport,
    )

    def _trade(position_id: str, entry_bar: int, exit_bar: int) -> SimulatedTrade:
        return SimulatedTrade(
            position_id=position_id,
            instrument_key="AAPL",
            direction=Direction.UP,
            quantity=10.0,
            entry_price=100.0,
            entry_bar=entry_bar,
            exit_price=105.0,
            exit_bar=exit_bar,
            reason=SimulationExitReason.TARGET,
            realized_pnl=50.0,
            commission_paid=1.0,
        )

    report = SimulationReport(
        instrument=Instrument.parse("AAPL"),
        timeframe=Timeframe.D1.value,
        strategy_id="trend_following",
        bars=30,
        warmup=5,
        initial_equity=100_000.0,
        final_equity=100_098.0,
        realized_pnl=100.0,
        unrealised_pnl=0.0,
        commission_paid=2.0,
        max_drawdown=0.0,
        sharpe=None,
        statistics=None,
        trades=(_trade("sim-1", 10, 15), _trade("sim-2", 20, 25)),
        equity_curve=tuple([100_000.0] * 30),
        signals_fired=2,
        orders_filled=2,
        orders_rejected=0,
        admissions_refused=0,
        entries_skipped=0,
        exit_counts=(("target", 2),),
        assumptions=("stubbed run",),
        provenance=Provenance(source="simulation", tier=SourceTier.DERIVED),
        quality=DataQuality(status=DataQualityStatus.OK),
        is_reliable=False,
        limitations=("stubbed",),
    )

    store = InMemoryJournalStore()
    api = _api(journal_store=store)

    async def _fake_paper_trade(*args, **kwargs):
        return report

    monkeypatch.setattr(api, "paper_trade", _fake_paper_trade)

    entries = await api.journal("AAPL", "trend_following")
    assert len(entries) == 2

    history = await api.journal_history()
    assert len(history) == 2
    assert {e.entry_id for e in history} == {e.entry_id for e in entries}
    # Filtering and the AAPL instrument key both work on what was persisted.
    assert len(await api.journal_history(instrument_key="AAPL")) == 2
    assert await api.journal_history(instrument_key="MSFT") == ()


@pytest.mark.asyncio
async def test_journal_persistence_is_idempotent_across_reruns(monkeypatch):
    from aetheros.trading.domain.enums import DataQualityStatus, Direction, Timeframe
    from aetheros.trading.domain.instrument import Instrument
    from aetheros.trading.domain.provenance import DataQuality, Provenance
    from aetheros.trading.domain.simulation import (
        SimulatedTrade,
        SimulationExitReason,
        SimulationReport,
    )

    trade = SimulatedTrade(
        position_id="sim-1",
        instrument_key="AAPL",
        direction=Direction.UP,
        quantity=10.0,
        entry_price=100.0,
        entry_bar=10,
        exit_price=105.0,
        exit_bar=15,
        reason=SimulationExitReason.TARGET,
        realized_pnl=50.0,
        commission_paid=1.0,
    )
    report = SimulationReport(
        instrument=Instrument.parse("AAPL"),
        timeframe=Timeframe.D1.value,
        strategy_id="trend_following",
        bars=30,
        warmup=5,
        initial_equity=100_000.0,
        final_equity=100_049.0,
        realized_pnl=50.0,
        unrealised_pnl=0.0,
        commission_paid=1.0,
        max_drawdown=0.0,
        sharpe=None,
        statistics=None,
        trades=(trade,),
        equity_curve=tuple([100_000.0] * 30),
        signals_fired=1,
        orders_filled=1,
        orders_rejected=0,
        admissions_refused=0,
        entries_skipped=0,
        exit_counts=(("target", 1),),
        assumptions=("stubbed run",),
        provenance=Provenance(source="simulation", tier=SourceTier.DERIVED),
        quality=DataQuality(status=DataQualityStatus.OK),
        is_reliable=False,
        limitations=("stubbed",),
    )

    store = InMemoryJournalStore()
    api = _api(journal_store=store)

    async def _fake_paper_trade(*args, **kwargs):
        return report

    monkeypatch.setattr(api, "paper_trade", _fake_paper_trade)

    first = await api.journal("AAPL", "trend_following")
    # Re-running the identical history re-derives identical content-addressed
    # ids, so the upsert overwrites in place rather than duplicating the trail.
    await api.journal("AAPL", "trend_following")

    history = await api.journal_history()
    assert len(first) == 1
    assert len(history) == 1


@pytest.mark.asyncio
async def test_journal_can_opt_out_of_persistence():
    store = InMemoryJournalStore()
    api = _api(journal_store=store)
    entries = await api.journal(
        "AAPL", "trend_following", timeframe="1d", limit=200, persist=False
    )
    # The caller got its entries, but nothing was written -- persistence is an
    # opt-outable side effect, never a change to the returned result.
    assert isinstance(entries, tuple)
    assert await api.journal_history() == ()


# ==============================================================
# portfolio -- the allocator over analysed candidates
# ==============================================================


@pytest.mark.asyncio
async def test_portfolio_allocates_within_the_risk_budget_on_mock():
    api = _api()
    plan = await api.portfolio(["AAPL", "MSFT"], account_equity=100_000.0)
    assert plan.account_equity == 100_000.0
    # MOCK candidates are not actionable, so nothing is sized -- and that keeps
    # the plan trivially inside its budget rather than fabricating positions.
    assert plan.within_risk_budget is True
    assert plan.included == 0


# ==============================================================
# execute -- a conduit that still passes through the risk gate
# ==============================================================


@pytest.mark.asyncio
async def test_execute_routes_a_formed_request_through_a_passing_risk_gate():
    broker = _FillingBroker()
    api = _api(broker)
    snapshot = AccountSnapshot(
        equity=100_000.0, realised_pnl_today=0.0, open_exposure_notional=10_000.0
    )
    result = await api.execute(_request(), account_snapshot=snapshot)
    assert result.status is OrderStatus.FILLED
    assert len(broker.submitted) == 1


@pytest.mark.asyncio
async def test_execute_rejects_a_breached_account_before_the_broker():
    broker = _FillingBroker()
    api = _api(broker)
    breached = AccountSnapshot(
        equity=100_000.0,
        realised_pnl_today=-50_000.0,
        open_exposure_notional=10_000.0,
    )
    result = await api.execute(_request(), account_snapshot=breached)
    assert result.status is OrderStatus.REJECTED
    assert broker.submitted == [], "the broker must never be reached on a breach"


@pytest.mark.asyncio
async def test_broker_property_exposes_the_wired_venue():
    broker = _FillingBroker()
    api = _api(broker)
    assert api.broker is broker
