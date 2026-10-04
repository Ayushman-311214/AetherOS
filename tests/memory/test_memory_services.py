"""
Service-layer behavioural tests (spec Phase 24).

Exercises the MemoryManager end-to-end against an in-memory database: the
remember/retrieve/update/forget verbs, episodic + failure + trading helpers,
consolidation, decay, the knowledge graph, explainable retrieval, working
memory and the MemoryProvider adapter.
"""

from __future__ import annotations

import pytest

from aetheros.memory.domain import (
    Episode,
    FailureRecord,
    MemoryImportance,
    MemoryType,
    OutcomeStatus,
    Preference,
    PredictionMemory,
    PredictionOutcomeMemory,
    PreferenceKind,
    SourceType,
    Veracity,
)
from aetheros.memory.domain.episode import ActionRecord, Outcome


@pytest.mark.asyncio
async def test_remember_and_retrieve_preference(manager) -> None:
    await manager.remember_preference(
        Preference(
            subject="browser",
            value="Brave",
            kind=PreferenceKind.EXPLICIT,
            confidence=0.9,
        )
    )
    results = await manager.retrieve("which browser does the user like?")
    assert results
    top = results[0]
    assert "Brave" in top.memory.content
    # Explainability (Rule 6): every result justifies itself.
    assert top.explanation.reasons
    assert top.score > 0


@pytest.mark.asyncio
async def test_retrieve_filters_by_type(manager) -> None:
    await manager.remember("A candlestick is a price bar.", memory_type=MemoryType.SEMANTIC)
    await manager.remember_preference(
        Preference(subject="theme", value="dark", kind=PreferenceKind.EXPLICIT)
    )
    prefs = await manager.retrieve("", memory_types=[MemoryType.PREFERENCE], limit=10)
    assert prefs
    assert all(r.memory.memory_type is MemoryType.PREFERENCE for r in prefs)


@pytest.mark.asyncio
async def test_update_changes_content_and_bumps_version(manager) -> None:
    m = await manager.remember("old content", importance=MemoryImportance.HIGH)
    updated = await manager.update(m.id, content="new content", confidence=0.9)
    assert updated.content == "new content"
    assert updated.confidence == 0.9
    assert updated.version == m.version + 1


@pytest.mark.asyncio
async def test_forget_soft_then_hard(manager) -> None:
    m = await manager.remember("ephemeral note about brave browser")
    assert await manager.forget(m.id)  # soft
    # Soft-deleted memories drop out of retrieval.
    results = await manager.retrieve("brave browser")
    assert all(r.memory.id != m.id for r in results)
    # But the row still exists until a hard delete.
    assert await manager.get(m.id) is not None
    assert await manager.forget(m.id, hard=True)
    assert await manager.get(m.id) is None


@pytest.mark.asyncio
async def test_episode_success_is_remembered(manager) -> None:
    episode = Episode(
        goal="Open TradingView and add RSI",
        environment={"application": "Chrome", "entities": ["TradingView", "RSI"]},
        actions=[
            ActionRecord(name="open_browser", status=OutcomeStatus.SUCCESS),
            ActionRecord(name="add_indicator", status=OutcomeStatus.SUCCESS),
        ],
        outcome=Outcome(status=OutcomeStatus.SUCCESS),
    )
    await manager.remember_episode(episode)
    results = await manager.retrieve("how did we add RSI to TradingView?")
    assert results
    assert results[0].memory.memory_type is MemoryType.EPISODIC


@pytest.mark.asyncio
async def test_failure_recovery_is_linked_and_retrievable(manager) -> None:
    failure = await manager.remember_failure(
        FailureRecord(
            failure_type="stale_coordinates",
            error="window moved; fixed coordinates clicked empty space",
            action="click_indicators_button",
            successful_recovery="vision-based grounding",
            recovery_status=OutcomeStatus.SUCCESS,
        )
    )
    results = await manager.retrieve("clicking indicators button failed coordinates")
    assert any(r.memory.id == failure.id for r in results)
    assert "vision-based grounding" in failure.content


@pytest.mark.asyncio
async def test_trading_prediction_and_outcome(manager) -> None:
    pred = PredictionMemory(
        instrument="RELIANCE",
        direction="UP",
        timeframe="1d",
        horizon="1 trading day",
        prob_up=0.78,
        model="momentum_v3",
        model_version="3.2.1",
    )
    pred_mem = await manager.remember_prediction(pred)
    # A prediction is stored as a PREDICTION, never a FACT (CLAUDE.md §15).
    assert pred_mem.veracity is Veracity.PREDICTION

    outcome = PredictionOutcomeMemory(
        prediction_id=pred.id,
        instrument="RELIANCE",
        realized_direction="UP",
        correct=True,
        predicted_prob_up=0.78,
        brier=0.0484,
    )
    outcome_mem = await manager.remember_prediction_outcome(outcome)
    assert outcome_mem.veracity is Veracity.OBSERVATION

    # The outcome is linked to the (untouched) prediction.
    neighbours = await manager._repo.linked_ids(pred.id)
    assert any(nid == outcome_mem.id for nid, _, _ in neighbours)

    # The historical prediction record is unchanged after the outcome is known.
    reloaded = await manager.get(pred.id)
    assert reloaded is not None
    assert reloaded.data["prediction"]["prob_up"] == 0.78


@pytest.mark.asyncio
async def test_consolidation_merges_duplicates(manager) -> None:
    a = await manager.remember("User prefers the Brave browser.", importance=MemoryImportance.NORMAL)
    b = await manager.remember("User prefers the Brave browser.", importance=MemoryImportance.NORMAL)
    assert a.id != b.id

    stats = await manager.consolidate()
    assert stats["merged"] >= 1

    # One survivor stays active with accumulated evidence; the other archives.
    from aetheros.memory.domain import MemoryStatus

    survivors = [
        m
        for m in await manager._repo.iter_all()
        if m.status is MemoryStatus.ACTIVE and "Brave" in m.content
    ]
    assert len(survivors) == 1
    assert survivors[0].evidence_count >= 2


@pytest.mark.asyncio
async def test_decay_expires_past_ttl(manager) -> None:
    from datetime import timedelta

    from aetheros.memory.domain import MemoryStatus
    from aetheros.memory._clock import utcnow

    m = await manager.remember("short-lived note")
    # Force it past its TTL and re-persist.
    m.expires_at = utcnow() - timedelta(days=1)
    await manager._repo.update(m)

    transitions = await manager.decay()
    reloaded = await manager.get(m.id)
    assert reloaded is not None
    assert reloaded.status in (MemoryStatus.EXPIRED, MemoryStatus.STALE, MemoryStatus.ARCHIVED)
    assert transitions


@pytest.mark.asyncio
async def test_graph_reflects_entities_and_finds_path(manager) -> None:
    # Two memories sharing entities build a connected graph automatically.
    await manager.remember(
        "The user uses TradingView for charting.",
        entities=["user", "TradingView"],
    )
    await manager.remember(
        "TradingView contains the RSI indicator.",
        entities=["TradingView", "RSI"],
    )
    path = await manager.find_path("user", "RSI")
    names = [e.name for e in path]
    assert "TradingView" in names


@pytest.mark.asyncio
async def test_validator_rejects_prediction_as_fact(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError

    with pytest.raises(MemoryValidationError):
        await manager.remember(
            "RELIANCE will go up.",
            veracity=Veracity.FACT,
            source_type=SourceType.PREDICTION,
        )


@pytest.mark.asyncio
async def test_working_memory_promotion(manager) -> None:
    manager.working.add("decision", "Chose vision grounding over coordinates",
                        importance=MemoryImportance.HIGH)
    manager.working.add("chatter", "ok", importance=MemoryImportance.TRIVIAL)
    promoted = await manager.promote_working()
    assert len(promoted) == 1
    assert "vision grounding" in promoted[0].content


@pytest.mark.asyncio
async def test_stats_report(manager) -> None:
    await manager.remember("a fact about markets")
    stats = await manager.stats()
    assert stats["total"] >= 1
    assert stats["vectors"] >= 1
    assert "by_type" in stats
    assert stats["embedding_dim"] == 64


@pytest.mark.asyncio
async def test_provider_adapter_kv_roundtrip(memory_config) -> None:
    from aetheros.memory.services.provider import SQLiteMemoryProvider

    provider = SQLiteMemoryProvider(memory_config)
    await provider.initialize()
    try:
        await provider.add("fav_browser", "Brave", {"topic": "preferences"})
        assert await provider.exists("fav_browser")
        assert await provider.get("fav_browser") == "Brave"
        assert "fav_browser" in await provider.list_keys()

        await provider.update("fav_browser", "Firefox")
        assert await provider.get("fav_browser") == "Firefox"

        hits = await provider.search("browser")
        assert hits

        await provider.delete("fav_browser")
        assert not await provider.exists("fav_browser")
    finally:
        await provider.shutdown()
