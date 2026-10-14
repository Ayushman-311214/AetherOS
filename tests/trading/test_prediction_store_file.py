"""
FilePredictionStore: the durable JSON Lines prediction-audit store.

These pin the durability + honesty contract of the file-backed store (CLAUDE.md
sections 8, 15, 19, 28) without a network or the orchestrator: records written
by one store instance are read back by a fresh instance over the same file
(persistence across "restarts"), recording is idempotent on the content-
addressed id (a re-run never inflates the trail or the file), reads are
newest-first with instrument/limit filters, and a malformed trailing line is
skipped on load rather than fabricated into a record.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.errors import PredictionError
from aetheros.trading.services.prediction_store import FilePredictionStore


def _record(pid: str, *, instrument_key: str = "AAPL", symbol: str = "AAPL") -> PredictionRecord:
    """Build a minimal, valid PredictionRecord with a chosen id."""
    return PredictionRecord(
        id=pid,
        instrument_key=instrument_key,
        symbol=symbol,
        exchange=None,
        asset_class="equity",
        name=None,
        timeframe="1d",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_bars=5,
        recommendation="no_trade",
        is_actionable=False,
        direction="unknown",
        confidence="low",
        directional_score=0.0,
        probability_reliable=False,
        probability_up=None,
        probability_down=None,
        risk_reward_ratio=None,
        overall_risk="unknown",
        invalidation="",
        source_tier="mock",
        is_mock=True,
        model_pipeline="deterministic-core/1.0",
        evidence_count=0,
        limitations=(),
    )


@pytest.mark.asyncio
async def test_records_survive_a_fresh_store_instance(tmp_path):
    path = tmp_path / "predictions.jsonl"
    store_a = FilePredictionStore(path)
    await store_a.record(_record("pred_a"))

    # A brand-new instance over the same file sees the persisted record -- this is
    # the durability the in-memory store lacks.
    store_b = FilePredictionStore(path)
    got = await store_b.get("pred_a")
    assert got is not None
    assert got.id == "pred_a"
    assert got.instrument_key == "AAPL"


@pytest.mark.asyncio
async def test_recording_is_idempotent_on_disk(tmp_path):
    path = tmp_path / "predictions.jsonl"
    store = FilePredictionStore(path)
    await store.record(_record("pred_x"))
    await store.record(_record("pred_x"))  # same id again

    assert len(await store.list_records()) == 1
    # The file holds exactly one line -- a re-run never appends a duplicate.
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


@pytest.mark.asyncio
async def test_lists_newest_first_with_filter_and_limit(tmp_path):
    store = FilePredictionStore(tmp_path / "p.jsonl")
    await store.record(_record("pred_1", instrument_key="AAPL", symbol="AAPL"))
    await store.record(_record("pred_2", instrument_key="MSFT", symbol="MSFT"))
    await store.record(_record("pred_3", instrument_key="AAPL", symbol="AAPL"))

    newest = await store.list_records()
    assert [r.id for r in newest] == ["pred_3", "pred_2", "pred_1"]

    only_aapl = await store.list_records(instrument_key="AAPL")
    assert [r.id for r in only_aapl] == ["pred_3", "pred_1"]

    capped = await store.list_records(limit=1)
    assert [r.id for r in capped] == ["pred_3"]

    with pytest.raises(ValueError):
        await store.list_records(limit=-1)


@pytest.mark.asyncio
async def test_malformed_trailing_line_is_skipped_not_fabricated(tmp_path):
    path = tmp_path / "p.jsonl"
    store = FilePredictionStore(path)
    await store.record(_record("pred_ok"))
    # Simulate a crash mid-append leaving a partial/garbage trailing line.
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"id": "pred_broken", "instrument":')  # truncated JSON, no newline

    fresh = FilePredictionStore(path)
    records = await fresh.list_records()
    assert [r.id for r in records] == ["pred_ok"]
    assert await fresh.get("pred_broken") is None


@pytest.mark.asyncio
async def test_empty_or_absent_file_is_honest_empty(tmp_path):
    store = FilePredictionStore(tmp_path / "does_not_exist.jsonl")
    assert await store.list_records() == ()
    assert await store.get("anything") is None


@pytest.mark.asyncio
async def test_unreadable_path_raises_prediction_error(tmp_path):
    # A path whose parent is a *file* (not a directory) cannot be written -> the
    # store surfaces a typed PredictionError rather than silently losing the write.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    store = FilePredictionStore(blocker / "nested" / "p.jsonl")
    with pytest.raises(PredictionError):
        await store.record(_record("pred_z"))
