"""
The Trading API -- the single public surface of the trading module (spec
Phase 24, docs/modules/trading.md "Trading API").

Higher-level modules (Planner, Reasoning, Automation, the CLI, agents) depend
on *this* facade, never on the individual trading services. That keeps the
module's internal composition free to change behind one stable, typed boundary.

The facade is deliberately thin: every method delegates to a service that
already exists and returns that service's own domain object verbatim. It holds
**no analytical logic of its own** -- it does not fuse evidence, size a trade,
compute a probability or decide a direction. It only chooses which service to
call and in what order, exactly as the equivalent tools in ``trading/tools.py``
already do. There is one source of truth for every number, and it is never
here.

Two boundaries are structural, not stylistic:

* **Nothing here fabricates market data.** ``paper_trade`` and ``journal`` run
  on real fetched candles with virtual money (spec: paper = REAL DATA +
  VIRTUAL MONEY); synthetic data only ever arrives through the explicitly
  labelled MOCK provider and stays flagged as such.
* **``execute`` never builds a trade from a free-text or model instruction.**
  It accepts an already-formed, fully-specified :class:`ExecutionRequest` -- the
  §9 trade record produced by the deterministic signal/risk/decision path -- and
  routes it through the execution engine, which re-validates risk limits before
  the broker is ever reached. The facade is a conduit, not a decision-maker; the
  required path (strategy/decision -> policy -> risk -> execution validation ->
  broker) stays intact and an LLM can never short-circuit it.
"""

from __future__ import annotations

from ..brokers.base import BrokerProvider
from ..domain.backtest import BacktestResult
from ..domain.enums import Direction
from ..domain.execution import ExecutionRequest, ExecutionResult
from ..domain.health import TradingHealth
from ..domain.instrument import Instrument
from ..domain.journal import JournalEntry
from ..domain.kill_switch import KillScope, KillSwitch
from ..domain.market_data import MarketData
from ..domain.portfolio import PortfolioCandidate, PortfolioRiskPlan
from ..domain.reconciliation import ReconciliationReport
from ..domain.report import TradingReport
from ..domain.risk_limits import AccountSnapshot
from ..domain.scan import ScanResult
from ..domain.signal import SignalEvaluation
from ..domain.simulation import SimulationReport
from ..domain.trade import Position
from ..errors import TradingError
from ..execution.engine import ExecutionEngine
from ..services.analysis_service import AnalysisService
from ..services.backtest_service import BacktestService
from ..production.health_service import TradingHealthService
from ..services.journal_service import JournalService
from ..services.journal_store import JournalStore
from ..production.kill_switch_service import KillSwitchService
from ..production.lifecycle_service import SignalLifecycleService
from ..services.market_data_service import MarketDataService
from ..services.orchestration_service import OrchestrationService
from ..services.portfolio_service import PortfolioRiskService
from ..production.position_service import PositionBookService
from ..production.reconciliation_service import ReconciliationService
from ..services.risk_service import RiskService
from ..services.scan_service import WatchlistScanService
from ..services.signal_service import SignalService
from ..services.simulation_service import SimulationService
from ..services.strategy_service import StrategyService


class TradingAPI:
    """
    The stable public facade over the trading module's services.

    Every collaborator is injected (dependency inversion, spec section 23);
    the facade constructs nothing and owns no state. Each public method maps
    one-to-one onto a service call and returns that service's domain object.
    """

    def __init__(
        self,
        *,
        orchestration: OrchestrationService,
        scan: WatchlistScanService,
        signals: SignalService,
        backtest: BacktestService,
        simulation: SimulationService,
        journal: JournalService,
        execution: ExecutionEngine,
        portfolio: PortfolioRiskService,
        market_data: MarketDataService,
        analysis: AnalysisService,
        risk: RiskService,
        strategy: StrategyService,
        journal_store: JournalStore | None = None,
        positions: PositionBookService | None = None,
        reconciliation: ReconciliationService | None = None,
        kill_switches: KillSwitchService | None = None,
        health: TradingHealthService | None = None,
        lifecycle: SignalLifecycleService | None = None,
    ) -> None:
        self._orchestration = orchestration
        self._scan = scan
        self._signals = signals
        self._backtest = backtest
        self._simulation = simulation
        self._journal = journal
        self._execution = execution
        self._portfolio = portfolio
        self._market_data = market_data
        self._analysis = analysis
        self._risk = risk
        self._strategy = strategy
        # Phase 2 production services -- optional so a minimal wiring keeps the
        # pre-existing surface; when present they power positions/health/etc.
        self._positions = positions
        self._reconciliation = reconciliation
        self._kill_switches = kill_switches
        self._health = health
        self._lifecycle = lifecycle
        # Optional durable sink for journal entries (spec Phase 27). When wired,
        # the journal path persists each entry it builds so the trail survives
        # the process (spec sections 15, 28); when absent the facade behaves
        # exactly as before -- it returns the entries and keeps nothing.
        self._journal_store = journal_store

    # ------------------------------------------------------------------
    # analyze
    # ------------------------------------------------------------------

    async def analyze(
        self,
        symbol: str | Instrument,
        timeframe: str | None = None,
        *,
        limit: int | None = None,
        direction: Direction | None = None,
        account_equity: float | None = None,
        risk_pct: float | None = None,
        run_backtest: bool = False,
    ) -> TradingReport:
        """
        The full deterministic trading report for one instrument.

        Delegates to the Trading CEO orchestrator, which fuses the analysis,
        risk geometry, critic verdict and all advisory context into one
        auditable :class:`TradingReport`. MOCK or thin data yields a
        NO_TRADE/INSUFFICIENT_EVIDENCE report with its limitations stated --
        never a fabricated signal.
        """
        return await self._orchestration.generate_report(
            symbol,
            timeframe,
            limit=limit,
            direction=direction,
            account_equity=account_equity,
            risk_pct=risk_pct,
            run_backtest=run_backtest,
        )

    # ------------------------------------------------------------------
    # scan
    # ------------------------------------------------------------------

    async def scan(
        self,
        symbols: list[str],
        timeframe: str | None = None,
        *,
        limit: int | None = None,
    ) -> ScanResult:
        """
        A ranked directional scan across a watchlist.

        Delegates to the watchlist scanner, which runs the deterministic
        analysis per symbol and ranks the results actionable-first. Symbols
        that cannot be analysed are reported as errored entries, not dropped.
        """
        return await self._scan.scan(symbols, timeframe, limit=limit)

    # ------------------------------------------------------------------
    # signal
    # ------------------------------------------------------------------

    async def signal(
        self,
        symbol: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        account_equity: float | None = None,
        risk_pct: float | None = None,
        strategy_ids: list[str] | None = None,
    ) -> SignalEvaluation:
        """
        Evaluate the strategy panel and emit the signals that fired.

        Delegates to the signal engine: every strategy's candidate is scored,
        the full risk geometry and critic gate are applied, and only candidates
        that pass every gate become signals. A run where nothing fired is the
        honest insufficient-evidence result, not a failure. A signal is a
        proposal -- it is never an order and nothing here reaches a broker.
        """
        return await self._signals.evaluate(
            symbol,
            timeframe=timeframe,
            limit=limit,
            account_equity=account_equity,
            risk_pct=risk_pct,
            strategy_ids=strategy_ids,
        )

    # ------------------------------------------------------------------
    # backtest
    # ------------------------------------------------------------------

    async def backtest(
        self,
        symbol: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        horizon: int | None = None,
        warmup: int | None = None,
    ) -> BacktestResult:
        """
        Backtest the deterministic analysis signal over past bars.

        Mirrors the ``backtest_signal`` tool: the signal under test is the
        fused analysis direction, evaluated on each growing past-only window
        (look-ahead safe) and measured against the forward return. MOCK data
        comes back never-reliable with the reason stated.
        """
        data = await self._market_data.get_candles(symbol, timeframe, limit=limit)

        async def _signal(window: MarketData) -> Direction:
            # emit=False: a per-bar replay must not flood the event bus with
            # one AnalysisCompleted per window.
            result = await self._analysis.analyze_data(window, emit=False)
            return result.direction

        return await self._backtest.run(
            data, _signal, horizon=horizon, warmup=warmup
        )

    # ------------------------------------------------------------------
    # paper_trade
    # ------------------------------------------------------------------

    async def paper_trade(
        self,
        symbol: str,
        strategy: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        warmup: int | None = None,
        initial_balance: float | None = None,
        commission_bps: float | None = None,
        slippage_bps: float | None = None,
    ) -> SimulationReport:
        """
        Paper-trade a strategy over real market data with virtual money.

        Mirrors the ``simulate_strategy`` tool: real fetched candles are
        replayed bar by bar through the real §9 chain against a virtual paper
        venue (REAL DATA + VIRTUAL MONEY). An unknown strategy is a typed
        error, not a silent empty run.
        """
        self._require_strategy(strategy)
        data = await self._market_data.get_candles(symbol, timeframe, limit=limit)
        return await self._simulation.run(
            data,
            strategy,
            warmup=warmup,
            initial_balance=initial_balance,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    async def execute(
        self,
        request: ExecutionRequest,
        *,
        account_snapshot: AccountSnapshot | None = None,
        validate: bool = True,
        confirmed: bool = False,
    ) -> ExecutionResult:
        """
        Route a fully-specified trade request through the execution engine.

        The facade accepts a complete :class:`ExecutionRequest` -- the §9 trade
        record (instrument, side, quantity, entry, stop, target, risk/reward,
        strategy and reason) that the deterministic signal/risk/decision path
        produces. It builds nothing: there is no path here from a free-text or
        model instruction to a broker. The engine applies the execution policy
        gate (spec Phase 26) and re-validates account-level risk limits before
        the broker is reached (``validate=True``); a policy denial or a risk
        breach returns a REJECTED result and the broker is never called.

        ``confirmed`` is the explicit go-ahead a live order requires under the
        policy; it is ignored for paper/analysis-only paths.

        ``validate=False`` is for callers that have already run the risk gate
        upstream (e.g. a simulation that re-capitalises its venue per order);
        it does not bypass the broker's own §9 geometry re-check, nor the
        execution policy gate, which is enforced on every path.
        """
        return await self._execution.submit(
            request,
            account_snapshot=account_snapshot,
            validate=validate,
            confirmed=confirmed,
        )

    # ------------------------------------------------------------------
    # portfolio
    # ------------------------------------------------------------------

    async def portfolio(
        self,
        symbols: list[str],
        *,
        account_equity: float,
        timeframe: str | None = None,
        limit: int | None = None,
    ) -> PortfolioRiskPlan:
        """
        Risk-budget a basket across several instruments.

        Mirrors the ``size_portfolio`` tool: each symbol is analysed and its
        risk geometry derived; only actionable, sizable candidates feed the
        deterministic allocator, which sizes them within the account's risk and
        exposure caps. Symbols that fail to analyse are skipped, not guessed.
        """
        candidates: list[PortfolioCandidate] = []
        for symbol in symbols:
            try:
                analysis = await self._analysis.analyze(
                    symbol, timeframe, limit=limit
                )
                assessment = await self._risk.assess(
                    analysis, account_equity=account_equity
                )
            except (TradingError, ValueError):
                continue
            if (
                not assessment.is_actionable
                or assessment.stop_loss is None
                or not assessment.risk_per_unit
            ):
                continue
            candidates.append(
                PortfolioCandidate(
                    instrument_key=assessment.instrument.key,
                    direction=assessment.direction,
                    entry=assessment.entry,
                    stop=assessment.stop_loss,
                    risk_per_share=assessment.risk_per_unit,
                )
            )
        return self._portfolio.allocate(candidates, account_equity=account_equity)

    # ------------------------------------------------------------------
    # journal
    # ------------------------------------------------------------------

    async def journal(
        self,
        symbol: str,
        strategy: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        warmup: int | None = None,
        initial_balance: float | None = None,
        commission_bps: float | None = None,
        slippage_bps: float | None = None,
        persist: bool = True,
    ) -> tuple[JournalEntry, ...]:
        """
        The settled-trade journal from paper-trading a strategy.

        Paper-trades the strategy over its real history, then turns each
        settled trade into one content-addressed :class:`JournalEntry` with
        verbatim geometry (no invented rationale). An empty tuple is the honest
        answer when nothing traded.

        When a durable journal store is wired (spec Phase 27) and ``persist`` is
        left on, every entry built here is recorded to it, so the trail survives
        the process (spec sections 15, 28). Recording is an upsert on the entry's
        content-addressed id, so re-running the same history never duplicates a
        row. The entries returned to the caller are the same either way --
        persistence is a side effect, not a change to the result.
        """
        report = await self.paper_trade(
            symbol,
            strategy,
            timeframe=timeframe,
            limit=limit,
            warmup=warmup,
            initial_balance=initial_balance,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
        entries = self._journal.entries_for_report(report)
        if persist and self._journal_store is not None:
            for entry in entries:
                await self._journal_store.record(entry)
        return entries

    # ------------------------------------------------------------------
    # journal_history
    # ------------------------------------------------------------------

    async def journal_history(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> tuple[JournalEntry, ...]:
        """
        The persisted journal trail, newest-first (spec Phase 27).

        Reads back the entries a durable journal store has accumulated across
        runs -- the history the learning/analytics layers measure performance
        against (spec sections 15, 28). Optionally filtered to one instrument
        and capped at ``limit``. When no durable store is wired this is an
        honest empty tuple (nothing was persisted), never a fabricated trail.
        """
        if self._journal_store is None:
            return ()
        return await self._journal_store.list_entries(
            instrument_key=instrument_key, limit=limit
        )

    # ------------------------------------------------------------------
    # Phase 2 -- production lifecycle surface
    # ------------------------------------------------------------------

    def positions(self) -> tuple[Position, ...]:
        """Every position currently open in the tracked book (spec Phase 2)."""
        if self._positions is None:
            return ()
        return self._positions.open_positions()

    def account_snapshot(self) -> AccountSnapshot | None:
        """The live account state built from the real book (spec Phase 2)."""
        if self._positions is None:
            return None
        return self._positions.snapshot()

    async def reconcile(self) -> ReconciliationReport:
        """Diff local state against the venue; report every divergence."""
        if self._reconciliation is None:
            raise TradingError(
                "Reconciliation is not wired into this build.",
                hint="Register ReconciliationService in the container.",
            )
        return await self._reconciliation.reconcile()

    async def health(self) -> TradingHealth:
        """The aggregate SAFE / DEGRADED / BLOCKED desk verdict."""
        if self._health is None:
            raise TradingError(
                "Trading health is not wired into this build.",
                hint="Register TradingHealthService in the container.",
            )
        return await self._health.status()

    def trip_kill_switch(
        self, scope: str, target: str = "", *, reason: str = "manual halt"
    ) -> KillSwitch:
        """Trip a scoped halt on order admission (global/strategy/broker/symbol)."""
        if self._kill_switches is None:
            raise TradingError(
                "Kill switches are not wired into this build.",
                hint="Register KillSwitchService in the container.",
            )
        return self._kill_switches.trip(
            KillSwitch(scope=KillScope(scope), target=target, reason=reason)
        )

    def clear_kill_switch(self, scope: str, target: str = "") -> bool:
        """Explicitly clear a tripped switch; False when none was armed."""
        if self._kill_switches is None:
            raise TradingError(
                "Kill switches are not wired into this build.",
                hint="Register KillSwitchService in the container.",
            )
        return self._kill_switches.clear(KillScope(scope), target)

    def signal_lifecycle(self, signal_id: str) -> dict:
        """The audited lifecycle record of one signal (spec Phase 2)."""
        if self._lifecycle is None:
            return {"signal_id": signal_id, "state": None, "transitions": []}
        record = self._lifecycle.get(signal_id)
        return record.to_dict() if record is not None else {
            "signal_id": signal_id,
            "state": None,
            "transitions": [],
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _require_strategy(self, strategy_id: str) -> None:
        """Fail with a typed, actionable error on an unknown strategy id."""
        registry = self._strategy.registry
        if registry.get(strategy_id) is None:
            raise TradingError(
                f"Unknown strategy '{strategy_id}'. Registered: "
                f"{', '.join(registry.ids()) or 'none'}.",
                hint="Call StrategyService.registry.ids() for the panel.",
            )

    @property
    def broker(self) -> BrokerProvider:
        """The broker the execution engine is wired to (paper by default)."""
        return self._execution.broker
