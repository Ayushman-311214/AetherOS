"""
The prediction audit store: interface, in-memory reference impl, and the
orchestrator's opt-in recording of every produced report.

These pin the section-8/19/28 audit contract at the store boundary: an
InMemoryPredictionStore records idempotently (a re-run of the same report never
inflates the history), reads back newest-first, filters by instrument and honours
a limit; the orchestrator records a prediction only when a store is wired (absent
= no behaviour change), and a store failure is swallowed so it can never sink a
report that was produced honestly.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.errors import PredictionError
from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.events import PredictionCreated
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.orchestration_service import OrchestrationService
from aetheros.trading.services.prediction_store import (
    InMemoryPredictionStore,
    PredictionStore,
)
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


class _Bus:
    """A minimal event bus that records what the orchestrator publishes."""

    def __init__(self) -> None:
        self.events: list = []

    async def publish(self, event) -> None:
        self.events.append(event)


def _orchestrator(
    prediction_store: PredictionStore | None = None,
    *,
    event_bus: _Bus | None = None,
) -> OrchestrationService:
    settings = get_settings()
    market_data = MarketDataService(MockMarketDataProvider(), settings)
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        MarketStructureService(),
        EvidenceService(),
        settings,
    )
    return OrchestrationService(
        market_data,
        analysis,
        RiskService(settings),
        BacktestService(settings),
        CriticService(settings),
        settings,
        prediction_store=prediction_store,
        event_bus=event_bus,
    )


async def _report():
    return await _orchestrator().generate_report("AAPL", "1d", limit=120)


# --------------------------------------------------------------------------- #
# InMemoryPredictionStore                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_store_records_and_reads_back():
    store = InMemoryPredictionStore()
    record = PredictionRecord.from_report(await _report())

    returned_id = await store.record(record)

    assert returned_id == record.id
    assert await store.get(record.id) == record
    assert await store.get("pred_missing") is None
    assert await store.list_records() == (record,)


@pytest.mark.asyncio
async def test_store_recording_same_prediction_is_idempotent():
    store = InMemoryPredictionStore()
    record = PredictionRecord.from_report(await _report())

    await store.record(record)
    await store.record(record)  # same content-addressed id

    # A re-run of the identical report must not inflate the history.
    assert len(store) == 1
    assert await store.list_records() == (record,)


@pytest.mark.asyncio
async def test_store_lists_newest_first_and_filters_by_instrument():
    store = InMemoryPredictionStore()
    orch = _orchestrator()

    aapl = PredictionRecord.from_report(
        await orch.generate_report("AAPL", "1d", limit=120)
    )
    msft = PredictionRecord.from_report(
        await orch.generate_report("MSFT", "1d", limit=120)
    )
    await store.record(aapl)
    await store.record(msft)

    # Newest-first ordering.
    assert await store.list_records() == (msft, aapl)
    # Instrument filter isolates one symbol's history.
    assert await store.list_records(instrument_key=aapl.instrument_key) == (aapl,)
    # Limit caps the page.
    assert await store.list_records(limit=1) == (msft,)


@pytest.mark.asyncio
async def test_store_rejects_negative_limit():
    store = InMemoryPredictionStore()
    with pytest.raises(ValueError):
        await store.list_records(limit=-1)


# --------------------------------------------------------------------------- #
# Orchestrator integration                                                     #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_orchestrator_records_prediction_when_store_wired():
    store = InMemoryPredictionStore()
    report = await _orchestrator(store).generate_report("AAPL", "1d", limit=120)

    history = await store.list_records()
    assert len(history) == 1
    recorded = history[0]
    # The recorded prediction is the report's own section-8 contract.
    assert recorded.id == PredictionRecord.from_report(report).id
    assert recorded.instrument_key == report.instrument.key
    assert recorded.recommendation == report.recommendation.value
    assert recorded.is_actionable is report.is_actionable


@pytest.mark.asyncio
async def test_orchestrator_without_store_is_a_no_op():
    # No store wired: the report is produced exactly as before, nothing recorded.
    report = await _orchestrator().generate_report("AAPL", "1d", limit=120)
    assert report.recommendation.value == "no_trade"


class _FailingStore(PredictionStore):
    """A store whose backing fails on every write (durable-store outage sim)."""

    def __init__(self) -> None:
        self.attempts = 0

    async def record(self, record: PredictionRecord) -> str:
        self.attempts += 1
        raise PredictionError("audit backend unavailable")

    async def get(self, prediction_id: str):
        return None

    async def list_records(self, *, instrument_key=None, limit=None):
        return ()


@pytest.mark.asyncio
async def test_store_failure_never_sinks_the_report():
    store = _FailingStore()

    # A recording failure is an audit side-effect: it is logged and swallowed,
    # so the honestly-produced report still comes back intact.
    report = await _orchestrator(store).generate_report("AAPL", "1d", limit=120)

    assert store.attempts == 1
    assert report.recommendation.value == "no_trade"
    assert report.is_actionable is False


# --------------------------------------------------------------------------- #
# PredictionCreated announcement                                               #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_prediction_created_is_announced_with_the_section8_contract():
    bus = _Bus()
    report = await _orchestrator(event_bus=bus).generate_report(
        "AAPL", "1d", limit=120
    )

    created = [e for e in bus.events if isinstance(e, PredictionCreated)]
    assert len(created) == 1
    event = created[0]
    # The announced contract mirrors the report's own section-8 record.
    record = PredictionRecord.from_report(report)
    assert event.prediction_id == record.id
    assert event.instrument_key == report.instrument.key
    assert event.recommendation == report.recommendation.value
    assert event.direction == report.direction.value
    assert event.is_actionable is report.is_actionable
    # Mock market data -> honestly flagged, never a real track record, and no
    # fabricated probability leaks into the announcement.
    assert event.is_mock is True
    assert event.probability_up is None


@pytest.mark.asyncio
async def test_prediction_announced_even_without_a_store():
    # The prediction was created regardless of where (or whether) it is saved.
    bus = _Bus()
    await _orchestrator(event_bus=bus).generate_report("AAPL", "1d", limit=120)
    assert any(isinstance(e, PredictionCreated) for e in bus.events)


@pytest.mark.asyncio
async def test_prediction_announced_even_when_the_store_write_fails():
    # Announcement and persistence are independent audit side-effects: a store
    # outage must not suppress the PredictionCreated signal.
    bus = _Bus()
    store = _FailingStore()
    await _orchestrator(store, event_bus=bus).generate_report(
        "AAPL", "1d", limit=120
    )

    assert store.attempts == 1
    assert any(isinstance(e, PredictionCreated) for e in bus.events)


@pytest.mark.asyncio
async def test_announced_prediction_matches_the_recorded_one():
    bus = _Bus()
    store = InMemoryPredictionStore()
    await _orchestrator(store, event_bus=bus).generate_report(
        "AAPL", "1d", limit=120
    )

    recorded = (await store.list_records())[0]
    created = [e for e in bus.events if isinstance(e, PredictionCreated)][0]
    assert created.prediction_id == recorded.id
