"""
Phase 16 -- trading memory integration tests.

Exercises ``MemoryManager.trading_history`` (``TradingHistoryAdapter``):

* actual available consumer contracts (memory-domain records + the
  existing remember_prediction[_outcome] verbs; trading-shape dicts via
  the from_* constructors -- representative mappings, not live trading
  instances, per the explicit unverified-integration ledger)
* immutable history (re-ingested predictions return the stored row;
  outcomes never edit predictions)
* idempotent ingestion (same id twice -> one row)
* out-of-order outcomes (outcome-first links on prediction arrival and
  vice versa)
* linkage (has_outcome edges, reasoning source refs)
* restart (file DB reopened by a fresh manager)
* scope isolation (instrument history never crosses)
* as-of retrieval (future rows excluded; undated rows excluded)
* no invented results (caller numbers stored verbatim)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from aetheros.memory.domain import MemoryType, Veracity


def _t0() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def file_manager(tmp_path):
    from pathlib import Path

    from aetheros.memory.config import MemoryConfig
    from aetheros.memory.services.manager import MemoryManager

    cfg = MemoryConfig.for_memory_db(Path(tmp_path) / "trading.db", embedding_dim=64)
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        yield mgr
    finally:
        await mgr.shutdown()


def _prediction(
    pid="pred-1",
    *,
    instrument="RELIANCE",
    prob_up=0.78,
    predicted_at=None,
    **over,
):
    data = {
        "id": pid,
        "instrument": instrument,
        "direction": "UP",
        "timeframe": "1d",
        "horizon": "1 trading day",
        "prob_up": prob_up,
        "model": "momentum_v3",
        "model_version": "3.2.1",
        "data_version": "2026-08-18",
        "source_tier": "real",
        "predicted_at": (predicted_at or _t0()).isoformat(),
    }
    data.update(over)
    return data


def _outcome(oid="out-1", pid="pred-1", *, resolved_at=None, **over):
    data = {
        "id": oid,
        "prediction_id": pid,
        "instrument": "RELIANCE",
        "realized_direction": "UP",
        "correct": True,
        "realized_return": 0.012,
        "brier": 0.0484,
        "predicted_prob_up": 0.78,
        "resolved_at": (resolved_at or _t0()).isoformat(),
    }
    data.update(over)
    return data


# ----------------------------------------------------------------------
# Consumer contracts + immutability + idempotency
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prediction_ingest_and_reingest_idempotent(manager) -> None:
    th = manager.trading_history
    first = await th.ingest_prediction(_prediction())
    assert first.memory_type is MemoryType.TRADING
    assert first.veracity is Veracity.PREDICTION  # never a FACT
    second = await th.ingest_prediction(_prediction())
    assert second.id == first.id
    rows = await manager._repo.list_by(memory_type="trading", limit=100)
    assert [r.id for r in rows].count("pred-1") == 1
    # Numbers verbatim (no invention, no recompute).
    assert first.data["prediction"]["prob_up"] == 0.78
    assert first.data["prediction"]["model_version"] == "3.2.1"


@pytest.mark.asyncio
async def test_prediction_record_shape_accepted(manager) -> None:
    # Trading PredictionRecord-style keys translate losslessly.
    th = manager.trading_history
    stored = await th.ingest_prediction(
        {
            "id": "pred-record-shape",
            "instrument_key": "RELIANCE:NSE",
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "timeframe": "1d",
            "created_at": _t0().isoformat(),
            "recommendation": "UP",
            "direction": "UP",
            "probability_up": 0.66,
            "risk_reward_ratio": 2.0,
            "model_pipeline": "momentum_v3",
            "source_tier": "real",
        }
    )
    payload = stored.data["prediction"]
    assert payload["instrument"] in ("RELIANCE", "RELIANCE:NSE")
    assert payload["prob_up"] == 0.66
    assert payload["risk_reward"] == 2.0


@pytest.mark.asyncio
async def test_outcome_links_and_never_edits_prediction(manager) -> None:
    th = manager.trading_history
    pred = await th.ingest_prediction(_prediction())
    before = dict(pred.data["prediction"])
    out = await th.ingest_outcome(_outcome())
    assert out.data["outcome"]["prediction_id"] == "pred-1"
    assert out.data["outcome"]["brier"] == 0.0484  # verbatim
    neighbours = await manager._repo.linked_ids("pred-1")
    assert any(nid == out.id for nid, _, _ in neighbours)
    # Original forecast untouched.
    reloaded = await manager.get("pred-1")
    assert reloaded is not None
    assert reloaded.data["prediction"] == before
    assert (await th.outcomes_for("pred-1"))[0].id == out.id


@pytest.mark.asyncio
async def test_outcome_first_links_on_prediction_arrival(manager) -> None:
    th = manager.trading_history
    # Out-of-order: outcome lands with no prediction yet.
    await th.ingest_outcome(_outcome(oid="out-early", pid="pred-late"))
    assert (await manager.get("out-early")) is not None
    assert await manager._repo.linked_ids("pred-late") == []
    # Prediction lands later: the pending link backfills (no duplicate).
    await th.ingest_prediction(_prediction(pid="pred-late"))
    neighbours = await manager._repo.linked_ids("pred-late")
    assert [nid for nid, _, _ in neighbours].count("out-early") == 1
    # Re-ingesting the outcome is a no-op, not a second row/link.
    await th.ingest_outcome(_outcome(oid="out-early", pid="pred-late"))
    neighbours = await manager._repo.linked_ids("pred-late")
    assert [nid for nid, _, _ in neighbours].count("out-early") == 1


@pytest.mark.asyncio
async def test_single_shot_paths_read_back(manager) -> None:
    from aetheros.memory.domain import PredictionMemory, PredictionOutcomeMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    out = await manager.remember_prediction_outcome(
        PredictionOutcomeMemory(
            prediction_id=pred.id, instrument="RELIANCE",
            realized_direction="UP", correct=True, predicted_prob_up=0.78,
            brier=0.0484,
        )
    )
    th = manager.trading_history
    assert (await th.get_record(pred.id)) is not None
    assert [o.id for o in await th.outcomes_for(pred.id)] == [out.id]
    assert (await th.get_record("missing")) is None


# ----------------------------------------------------------------------
# Regime / analysis / strategy / calibration / reasoning ingestion
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regime_analysis_strategy_calibration_ingest(manager) -> None:
    th = manager.trading_history
    regime = await th.ingest_regime(
        {
            "id": "reg-1", "instrument": "RELIANCE", "regime": "TRENDING",
            "timeframe": "1d", "venue": "NSE", "direction": "UP",
            "adx": 28.5, "atr_pct": 0.02, "reliable": True,
            "event_time": _t0().isoformat(),
        }
    )
    assert regime.data["regime"]["adx"] == 28.5
    assert regime.metadata["event_time"] == _t0().isoformat()

    analysis = await th.ingest_analysis(
        {
            "id": "ana-1", "instrument": "RELIANCE", "direction": "UP",
            "timeframe": "1d", "last_price": 2500.0, "directional_score": 0.6,
            "evidence_refs": ["reg-1"], "actionable": True,
            "event_time": _t0().isoformat(),
        }
    )
    assert analysis.data["analysis"]["evidence_refs"] == ["reg-1"]

    strat = await th.ingest_strategy(
        {
            "id": "strat-1", "strategy_id": "breakout_v1",
            "instrument": "RELIANCE", "timeframe": "1d", "fired": True,
            "rules_matched": ["donchian_break", "volume_confirm"],
            "event_time": _t0().isoformat(),
        }
    )
    assert strat.data["strategy_observation"]["fired"] is True

    calib = await th.ingest_calibration(
        {
            "id": "cal-1", "scope": "RELIANCE", "instrument": "RELIANCE",
            "sample_size": 120, "brier": 0.21, "baseline_brier": 0.25,
            "mean_predicted": 0.62, "realised_rate": 0.58, "bias": "over",
            "trustworthy": True,
            "proposed_correction": {"shrink": 0.9},
            "event_time": _t0().isoformat(),
        }
    )
    # Caller-computed numbers stored verbatim (never recomputed here).
    assert calib.data["calibration"]["brier"] == 0.21
    assert calib.data["calibration"]["proposed_correction"] == {"shrink": 0.9}

    for mid in ("reg-1", "ana-1", "strat-1", "cal-1"):
        row = await manager.get(mid)
        assert row is not None
        assert row.memory_type is MemoryType.TRADING
        assert row.veracity is Veracity.OBSERVATION  # history, never FACT


@pytest.mark.asyncio
async def test_reasoning_summary_links_sources(manager) -> None:
    th = manager.trading_history
    pred = await th.ingest_prediction(_prediction(pid="pred-rs"))
    out = await th.ingest_outcome(_outcome(oid="out-rs", pid="pred-rs"))
    summary = await th.ingest_reasoning(
        {
            "id": "rs-1", "conclusion": "Momentum setup worked on RELIANCE.",
            "instrument": "RELIANCE", "timeframe": "1d",
            "source_refs": [pred.id, out.id, "missing-ref"],
            "event_time": _t0().isoformat(),
        }
    )
    neighbours = await manager._repo.linked_ids("rs-1")
    assert any(nid == pred.id for nid, _, _ in neighbours)
    assert any(nid == out.id for nid, _, _ in neighbours)
    # Missing ref skipped, citation preserved in the payload.
    assert "missing-ref" in summary.data["reasoning_summary"]["source_refs"]


# ----------------------------------------------------------------------
# As-of retrieval (no future leakage)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_as_of_excludes_future_and_undated(manager) -> None:
    th = manager.trading_history
    t0, t1, t2 = _t0(), _t0() + timedelta(days=1), _t0() + timedelta(days=2)
    await th.ingest_regime(
        {"id": "reg-t0", "instrument": "RELIANCE", "regime": "RANGING",
         "timeframe": "1d", "event_time": t0.isoformat()}
    )
    await th.ingest_regime(
        {"id": "reg-t2", "instrument": "RELIANCE", "regime": "TRENDING",
         "timeframe": "1d", "event_time": t2.isoformat()}
    )
    await th.ingest_prediction(_prediction(pid="pred-undated"))
    # Undated prediction row: strip event metadata to simulate legacy rows.
    undated = await manager.get("pred-undated")
    assert undated is not None
    undated.metadata.pop("event_time", None)
    undated.data["prediction"].pop("predicted_at", None)
    await manager._repo.update(undated)

    as_of_t1 = await th.history_as_of("RELIANCE", t1)
    ids = {r.id for r in as_of_t1}
    assert "reg-t0" in ids
    assert "reg-t2" not in ids  # future outcome cannot leak
    assert "pred-undated" not in ids  # undated rows excluded, not leaked
    # Chronological order.
    stamps = [r.metadata.get("event_time", "") for r in as_of_t1]
    assert stamps == sorted(stamps)


@pytest.mark.asyncio
async def test_as_of_scope_and_kind_filters(manager) -> None:
    th = manager.trading_history
    await th.ingest_regime(
        {"id": "reg-rel", "instrument": "RELIANCE", "regime": "RANGING",
         "timeframe": "1d", "event_time": _t0().isoformat()}
    )
    await th.ingest_regime(
        {"id": "reg-infy", "instrument": "INFY", "regime": "RANGING",
         "timeframe": "1d", "event_time": _t0().isoformat()}
    )
    rel = await th.history_as_of("RELIANCE", _t0() + timedelta(days=1))
    assert {r.id for r in rel} == {"reg-rel"}  # scope isolation
    kinds = await th.history_as_of(
        "RELIANCE", _t0() + timedelta(days=1), kinds=["regime"]
    )
    assert all("regime" in r.data for r in kinds)
    limited = await th.history_as_of(
        "RELIANCE", _t0() + timedelta(days=1), limit=1
    )
    assert len(limited) == 1


# ----------------------------------------------------------------------
# Restart + disabled + consumer ledger
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restart_preserves_history_and_links(file_manager) -> None:
    th = file_manager.trading_history
    await th.ingest_prediction(_prediction(pid="pred-restart"))
    await th.ingest_outcome(_outcome(oid="out-restart", pid="pred-restart"))

    from aetheros.memory.services.manager import MemoryManager as MM

    mgr2 = MM(file_manager.config)
    await mgr2.initialize()
    try:
        rows = await mgr2.trading_history.history_as_of(
            "RELIANCE", _t0() + timedelta(days=1)
        )
        assert "pred-restart" in {r.id for r in rows}
        assert [o.id for o in await mgr2.trading_history.outcomes_for(
            "pred-restart")] == ["out-restart"]
        neighbours = await mgr2._repo.linked_ids("pred-restart")
        assert any(nid == "out-restart" for nid, _, _ in neighbours)
    finally:
        await mgr2.shutdown()


@pytest.mark.asyncio
async def test_disabled_ingest_returns_unsaved(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    await mgr.initialize()
    try:
        await mgr.trading_history.ingest_prediction(_prediction(pid="p-off"))
        # Honest no-op like remember_memory: returned unsaved, no row exists.
        assert await mgr.trading_history.get_record("p-off") is None
        assert [o.id for o in await mgr.trading_history.outcomes_for("p-off")] == []
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_consumer_ledger_is_explicit(manager) -> None:
    report = await manager.trading_history.verify_consumer_contract()
    assert report["adapter"] == "TradingHistoryAdapter"
    assert report["verified_live"]
    assert report["unverified_live_trading_objects"]
    # The ledger names real trading shapes (not invented ones).
    blob = str(report)
    assert "PredictionRecord" in blob
    assert "RegimeAnalysis" in blob
