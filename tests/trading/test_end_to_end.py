"""
End-to-end pipeline on real market data (spec Phase 28).

Every other trading test that exercises the full stack runs on the explicitly
labelled MOCK provider, where the honest answer is always NO_TRADE /
insufficient-evidence. That proves the honesty rules but never proves the
pipeline *works on real data* -- that a fetched, parsed, non-mock series flows
all the way through analysis, signal, risk, the §9 execution chain, the journal
and the analytics book without a single layer fabricating a number.

This module closes that gap. It wires the exact services the bootstrap composes,
but behind the **real** :class:`YahooMarketDataProvider` -- the production
adapter -- driven through an ``httpx.MockTransport`` that returns canned Yahoo
chart payloads. The transport makes the test deterministic and offline; the
provider code under it is the real parsing/provenance path, so the data that
reaches the pipeline is genuine ``SourceTier.SECONDARY``, ``is_mock=False``
market data, exactly as it would be against the live endpoint.

What it pins, end to end:

* **Real data stays real.** The provenance that reaches analysis, the paper
  simulation and the journal is SECONDARY and non-mock -- the pipeline never
  silently downgrades or re-labels it.
* **Paper trading is REAL DATA + VIRTUAL MONEY.** A strategy replayed over the
  fetched history settles trades against a virtual paper venue; the trades are
  non-mock, they persist to the durable journal store, and the analytics book
  reads the same trades back and grades them.
* **The §9 execution chain holds on real data.** A fully-specified request
  fills at the real paper venue under a healthy account and is REJECTED (broker
  never reached) under a breached one -- policy gate, risk-limits gate and the
  venue's own geometry re-check all in force. ``execute`` originates nothing.
"""

from __future__ import annotations

import time
from dataclasses import replace

import httpx
import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.analytics.journal_analytics import JournalAnalyticsService
from aetheros.trading.api import TradingAPI
from aetheros.trading.brokers.paper_provider import PaperTradingProvider
from aetheros.trading.domain.enums import Direction, OrderStatus, SourceTier
from aetheros.trading.domain.execution import ExecutionRequest
from aetheros.trading.domain.risk_limits import AccountSnapshot
from aetheros.trading.execution.engine import ExecutionEngine
from aetheros.trading.providers.yahoo_provider import YahooMarketDataProvider
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

from .test_critic import _risk
from .test_signal_domain import _setup, _signal

pytestmark = pytest.mark.asyncio


# ==============================================================
# A canned-but-real market: the Yahoo adapter parses this exactly as it would
# parse the live endpoint, so the series reaching the pipeline is genuine
# SECONDARY, non-mock data -- not the MOCK provider's self-labelled synthetic.
# ==============================================================

_SYMBOL = "TEST"


def _cyclical_closes(bars: int, *, up: int, down: int, rise: float, fall: float):
    """A deterministic up/down cycle: enough structure for a trend strategy to
    actually fire trades over the replay, so the journal and analytics book are
    exercised on real settled trades rather than an empty run."""
    closes: list[float] = []
    price = 100.0
    period = up + down
    for i in range(bars):
        price += rise if i % period < up else -fall
        closes.append(round(max(price, 1.0), 2))
    return closes


def _chart_payload(closes: list[float]) -> dict:
    """A Yahoo /v8/finance/chart payload the real provider parses verbatim."""
    n = len(closes)
    step = 86400
    base = int(time.time()) - step * n
    timestamps = [base + step * i for i in range(n)]
    opens = [round(c - 0.2, 2) for c in closes]
    highs = [round(c + 0.6, 2) for c in closes]
    lows = [round(c - 0.6, 2) for c in closes]
    volumes = [1_000_000.0] * n
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "exchangeName": "NMS",
                        "currency": "USD",
                        "symbol": _SYMBOL,
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": volumes,
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def _real_adapter(closes: list[float]) -> YahooMarketDataProvider:
    """The real production adapter, driven offline through MockTransport."""
    payload = _chart_payload(closes)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def sleeper(seconds: float) -> None:  # retry backoff never slows us
        return None

    return YahooMarketDataProvider(client=client, sleeper=sleeper)


def _api(
    closes: list[float],
    *,
    broker=None,
    journal_store: JournalStore | None = None,
) -> tuple[TradingAPI, MarketDataService]:
    """The same service graph the bootstrap composes, behind the real adapter."""
    settings = get_settings()
    market_data = MarketDataService(_real_adapter(closes), settings)
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
    api = TradingAPI(
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
    return api, market_data


def _healthy() -> AccountSnapshot:
    return AccountSnapshot(
        equity=100_000.0, realised_pnl_today=0.0, open_exposure_notional=10_000.0
    )


def _breached() -> AccountSnapshot:
    # A day already past the daily-loss limit: the risk gate must reject.
    return AccountSnapshot(
        equity=100_000.0, realised_pnl_today=-5_000.0, open_exposure_notional=10_000.0
    )


# ==============================================================
# Real data stays real through the pipeline
# ==============================================================


async def test_fetched_data_is_real_secondary_not_mock() -> None:
    """The series reaching the pipeline is genuine SECONDARY, non-mock data --
    the real adapter's provenance, not the MOCK provider's self-label."""
    api, market_data = _api(_cyclical_closes(60, up=6, down=4, rise=1.0, fall=0.8))
    data = await market_data.get_candles(_SYMBOL, "1d", limit=60)

    assert data.provenance.tier is SourceTier.SECONDARY
    assert data.provenance.is_mock is False
    assert len(data.candles) == 60


async def test_analyze_runs_on_real_data_and_keeps_its_provenance() -> None:
    """A full report is produced over real data and keeps the real source; the
    report is honestly DERIVED (a computed artifact) but never mock, and it
    never re-labels the underlying feed."""
    api, _ = _api(_cyclical_closes(120, up=7, down=4, rise=1.1, fall=0.9))
    report = await api.analyze(_SYMBOL, timeframe="1d", limit=120)

    assert report.instrument.key.endswith(_SYMBOL)
    # The report is a derived artifact, but it carries the real feed's source
    # and is never flagged mock -- the real-data chain is preserved.
    assert report.provenance.source == "yahoo"
    assert report.provenance.is_mock is False
    # A report over real data is a full, serialisable record either way --
    # whether the critic approved a direction or honestly declined.
    assert "recommendation" in report.to_dict()


# ==============================================================
# Paper trading: REAL DATA + VIRTUAL MONEY, persisted, then measured
# ==============================================================


async def test_paper_trade_journal_persist_and_analytics_on_real_data() -> None:
    """A strategy replayed over fetched history settles non-mock trades, the
    journal persists them to the durable store, and the analytics book reads the
    same trades back -- one unbroken real-data trail from candles to metrics."""
    store = InMemoryJournalStore()
    closes = _cyclical_closes(150, up=6, down=4, rise=1.2, fall=1.0)
    api, _ = _api(closes, journal_store=store)

    entries = await api.journal(_SYMBOL, "trend_following", timeframe="1d", limit=150)

    # Real data + virtual money: trades actually settled, and none is mock.
    assert len(entries) > 0
    assert all(entry.is_mock is False for entry in entries)

    # The trail persisted: what the store holds is exactly what the run produced.
    history = await api.journal_history()
    assert len(history) == len(entries)
    assert {e.entry_id for e in history} == {e.entry_id for e in entries}

    # Analytics reads the persisted trail and grades the same trades.
    analytics = JournalAnalyticsService(get_settings()).summarize(history)
    assert analytics.trades == len(entries)
    assert analytics.mock_trades == 0


async def test_journal_persistence_is_idempotent_across_reruns() -> None:
    """Re-running the same history never duplicates a row: the store upserts on
    the content-addressed entry id, so the real-data trail is stable."""
    store = InMemoryJournalStore()
    closes = _cyclical_closes(150, up=6, down=4, rise=1.2, fall=1.0)
    api, _ = _api(closes, journal_store=store)

    first = await api.journal(_SYMBOL, "trend_following", timeframe="1d", limit=150)
    await api.journal(_SYMBOL, "trend_following", timeframe="1d", limit=150)
    history = await api.journal_history()

    assert len(history) == len(first)


# ==============================================================
# The §9 execution chain, end to end on the real paper venue
# ==============================================================


async def test_execute_fills_at_real_paper_venue_under_healthy_account() -> None:
    """A fully-specified request fills at the real paper venue (REAL DATA +
    VIRTUAL MONEY) once the policy gate and risk-limits gate both pass."""
    closes = [round(100.0 + i * 0.1, 2) for i in range(60)]
    settings = get_settings()
    market_data = MarketDataService(_real_adapter(closes), settings)
    venue = PaperTradingProvider(market_data)
    api, _ = _api(closes, broker=venue)

    risk = replace(_risk(2.0, direction=Direction.UP), risk_pct=1.0)
    request = ExecutionRequest.from_signal(
        _signal(Direction.UP), risk, _setup(Direction.UP), quantity=5.0
    )

    result = await api.execute(request, account_snapshot=_healthy())

    assert result.status is OrderStatus.FILLED
    assert venue.order_count == 1


async def test_execute_rejected_on_breached_account_broker_never_reached() -> None:
    """A breached account is REJECTED by the risk-limits gate before the broker
    is reached -- the §9 chain holds even when the request itself is valid."""
    closes = [round(100.0 + i * 0.1, 2) for i in range(60)]
    settings = get_settings()
    market_data = MarketDataService(_real_adapter(closes), settings)
    venue = PaperTradingProvider(market_data)
    api, _ = _api(closes, broker=venue)

    risk = replace(_risk(2.0, direction=Direction.UP), risk_pct=1.0)
    request = ExecutionRequest.from_signal(
        _signal(Direction.UP), risk, _setup(Direction.UP), quantity=5.0
    )

    result = await api.execute(request, account_snapshot=_breached())

    assert result.status is OrderStatus.REJECTED
    # The breach was caught before the venue: no order was ever accepted.
    assert venue.order_count == 0
