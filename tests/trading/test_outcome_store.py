"""
The outcome store: in-memory + durable JSON Lines accumulation of resolved
prediction outcomes (spec sections 15, 29).

These pin the upsert/durability/honesty contract: an outcome is keyed on its
prediction_id and re-recording upserts in place (a PENDING reading later matures
to RESOLVED -- latest wins, never two rows for one prediction); the file backend
persists across fresh instances; reads are newest-first with instrument/limit
filters; a malformed trailing line is skipped on load; and PredictionOutcome
round-trips losslessly through to_dict/from_dict.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import Direction, PredictionOutcomeStatus
from aetheros.trading.domain.outcome import PredictionOutcome
from aetheros.trading.errors import PredictionError
from aetheros.trading.services.outcome_store import (
    FileOutcomeStore,
    InMemoryOutcomeStore,
)


def _outcome(
    pid: str,
    *,
    instrument_key: str = "AAPL",
    status: PredictionOutcomeStatus = PredictionOutcomeStatus.RESOLVED,
    is_correct: bool | None = True,
) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id=pid,
        instrument_key=instrument_key,
        timeframe="1d",
        status=status,
        predicted_direction=Direction.UP,
        realized_direction=Direction.UP,
        is_correct=is_correct,
        realized_return=0.02,
        horizon_bars=5,
        bars_elapsed=5,
        is_reliable=True,
        is_mock=False,
    )


def test_outcome_round_trips_through_dict():
    original = _outcome("p1")
    rebuilt = PredictionOutcome.from_dict(original.to_dict())
    assert rebuilt.prediction_id == original.prediction_id
    assert rebuilt.status is original.status
    assert rebuilt.predicted_direction is original.predicted_direction
    assert rebuilt.realized_direction is original.realized_direction
    assert rebuilt.is_correct == original.is_correct
    assert rebuilt.realized_return == original.realized_return


@pytest.mark.asyncio
async def test_in_memory_upserts_on_prediction_id():
    store = InMemoryOutcomeStore()
    await store.record(_outcome("p1", status=PredictionOutcomeStatus.PENDING, is_correct=None))
    await store.record(_outcome("p1", status=PredictionOutcomeStatus.RESOLVED, is_correct=True))

    assert len(store) == 1  # one prediction, not two
    got = await store.get("p1")
    assert got.status is PredictionOutcomeStatus.RESOLVED


@pytest.mark.asyncio
async def test_file_store_persists_across_instances(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    a = FileOutcomeStore(path)
    await a.record(_outcome("p1"))

    b = FileOutcomeStore(path)
    got = await b.get("p1")
    assert got is not None
    assert got.prediction_id == "p1"
    assert got.status is PredictionOutcomeStatus.RESOLVED


@pytest.mark.asyncio
async def test_file_store_last_line_wins_on_reload(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    a = FileOutcomeStore(path)
    await a.record(_outcome("p1", status=PredictionOutcomeStatus.PENDING, is_correct=None))
    await a.record(_outcome("p1", status=PredictionOutcomeStatus.RESOLVED, is_correct=True))

    # Two appended lines for p1; a fresh load keeps only the latest (RESOLVED).
    b = FileOutcomeStore(path)
    outcomes = await b.list_outcomes()
    assert len(outcomes) == 1
    assert outcomes[0].status is PredictionOutcomeStatus.RESOLVED


@pytest.mark.asyncio
async def test_file_store_newest_first_filter_and_limit(tmp_path):
    store = FileOutcomeStore(tmp_path / "o.jsonl")
    await store.record(_outcome("p1", instrument_key="AAPL"))
    await store.record(_outcome("p2", instrument_key="MSFT"))
    await store.record(_outcome("p3", instrument_key="AAPL"))

    assert [o.prediction_id for o in await store.list_outcomes()] == ["p3", "p2", "p1"]
    aapl = await store.list_outcomes(instrument_key="AAPL")
    assert [o.prediction_id for o in aapl] == ["p3", "p1"]
    assert [o.prediction_id for o in await store.list_outcomes(limit=1)] == ["p3"]
    with pytest.raises(ValueError):
        await store.list_outcomes(limit=-1)


@pytest.mark.asyncio
async def test_file_store_skips_a_malformed_line(tmp_path):
    path = tmp_path / "o.jsonl"
    store = FileOutcomeStore(path)
    await store.record(_outcome("p_ok"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"prediction_id": "p_bad"')  # truncated

    fresh = FileOutcomeStore(path)
    assert [o.prediction_id for o in await fresh.list_outcomes()] == ["p_ok"]


@pytest.mark.asyncio
async def test_file_store_unwritable_path_raises(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    store = FileOutcomeStore(blocker / "nested" / "o.jsonl")
    with pytest.raises(PredictionError):
        await store.record(_outcome("p1"))
