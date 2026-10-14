"""
Phase 13 -- confidence and evidence update tests.

Exercises ``MemoryManager.confidence`` (``ConfidenceUpdater``):

* score boundaries (floor / cap / contradiction floor)
* deterministic updates (same sequence -> same value)
* duplicate evidence (same source / same contradictor twice is a no-op)
* contradictions (dent, floored, named evidence)
* explicit corrections (user facts governed; predictions/history refused)
* successful/failed verification (reuse up/down; outcome up/down)
* immutable historical evidence (predictions, trading, episodes, failures,
  procedures refused)
* no retrieval bump (retrieve N times -> confidence unchanged)
* no freshness decay (age alone never moves confidence)
* evidence history (appended, capped, auditable)
"""

from __future__ import annotations

import pytest

from aetheros.memory.domain import Preference, PreferenceKind, Veracity


@pytest.mark.asyncio
async def test_confirm_raises_and_dedups_by_source(manager) -> None:
    m = await manager.remember("User prefers the Brave browser.")
    before = m.confidence
    r1 = await manager.confidence.confirm(m.id, source="agent-run-1")
    assert r1.applied
    after = (await manager.get(m.id)).confidence
    assert after == pytest.approx(min(0.95, before + 0.05))
    # Same source again: duplicate observation, not new evidence.
    r2 = await manager.confidence.confirm(m.id, source="agent-run-1")
    assert not r2.applied
    assert (await manager.get(m.id)).confidence == pytest.approx(after)
    # A different source counts.
    r3 = await manager.confidence.confirm(m.id, source="agent-run-2")
    assert r3.applied


@pytest.mark.asyncio
async def test_confirm_caps_at_bound(manager) -> None:
    m = await manager.remember("Stable fact.", confidence=0.94)
    for i in range(5):
        await manager.confidence.confirm(m.id, source=f"s{i}")
    assert (await manager.get(m.id)).confidence == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_deterministic_updates(manager) -> None:
    a = await manager.remember("Deterministic fact A.", confidence=0.5)
    b = await manager.remember("Deterministic fact A.", confidence=0.5)
    for source in ("s1", "s2"):
        await manager.confidence.confirm(a.id, source=source)
        await manager.confidence.confirm(b.id, source=source)
    assert (await manager.get(a.id)).confidence == pytest.approx(
        (await manager.get(b.id)).confidence
    )


@pytest.mark.asyncio
async def test_correct_governs_user_preference(manager) -> None:
    m = await manager.remember_preference(
        Preference(subject="browser", value="Brave", kind=PreferenceKind.EXPLICIT)
    )
    result = await manager.confidence.correct(m.id, content="User prefers Firefox.")
    assert result.applied
    row = await manager.get(m.id)
    assert row is not None
    assert row.content == "User prefers Firefox."
    assert row.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_correct_governs_user_input_fact(manager) -> None:
    m = await manager.remember(
        "My desk is on floor 3.", veracity=Veracity.USER_INPUT
    )
    result = await manager.confidence.correct(m.id, content="My desk is on floor 5.")
    assert result.applied
    assert (await manager.get(m.id)).content == "My desk is on floor 5."


@pytest.mark.asyncio
async def test_correct_noop_when_nothing_changes(manager) -> None:
    m = await manager.remember("Same.", veracity=Veracity.USER_INPUT)
    result = await manager.confidence.correct(m.id, content="Same.")
    assert not result.applied


@pytest.mark.asyncio
async def test_correct_refuses_prediction(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    with pytest.raises(MemoryValidationError):
        await manager.confidence.correct(pred.id, content="UPDATED")
    # Untouched.
    assert (await manager.get(pred.id)).content == pred.content


@pytest.mark.asyncio
async def test_correct_refuses_episode_and_inferred_fact(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError

    ep = await manager.episodes.start_episode("goal", episode_id="ep-corr")
    with pytest.raises(MemoryValidationError):
        await manager.confidence.correct(ep.id, content="rewritten goal")
    plain = await manager.remember("Some inferred thing.")
    with pytest.raises(MemoryValidationError):
        await manager.confidence.correct(plain.id, content="changed")


@pytest.mark.asyncio
async def test_reuse_success_and_failure(manager) -> None:
    m = await manager.remember("Reusable know-how.", confidence=0.5)
    ok = await manager.confidence.record_reuse(m.id, succeeded=True)
    assert ok.applied
    assert (await manager.get(m.id)).confidence == pytest.approx(0.53)
    bad = await manager.confidence.record_reuse(m.id, succeeded=False)
    assert bad.applied
    assert (await manager.get(m.id)).confidence == pytest.approx(0.48)


@pytest.mark.asyncio
async def test_reuse_floors_and_caps(manager) -> None:
    low = await manager.remember("Shaky.", confidence=0.11)
    await manager.confidence.record_reuse(low.id, succeeded=False)
    assert (await manager.get(low.id)).confidence == pytest.approx(0.1)
    # Floor holds on repeat.
    await manager.confidence.record_reuse(low.id, succeeded=False)
    assert (await manager.get(low.id)).confidence == pytest.approx(0.1)

    high = await manager.remember("Trusted.", confidence=0.89)
    await manager.confidence.record_reuse(high.id, succeeded=True)
    assert (await manager.get(high.id)).confidence == pytest.approx(0.9)
    await manager.confidence.record_reuse(high.id, succeeded=True)
    assert (await manager.get(high.id)).confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_reuse_refuses_forecasts(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    with pytest.raises(MemoryValidationError):
        await manager.confidence.record_reuse(pred.id, succeeded=True)


@pytest.mark.asyncio
async def test_outcome_confirmed_and_refuted(manager) -> None:
    m = await manager.remember("NIFTY regime trending.", confidence=0.5)
    await manager.confidence.record_outcome(m.id, correct=True)
    assert (await manager.get(m.id)).confidence == pytest.approx(0.55)
    await manager.confidence.record_outcome(m.id, correct=False)
    assert (await manager.get(m.id)).confidence == pytest.approx(0.45)


@pytest.mark.asyncio
async def test_outcome_refuses_prediction_rows(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    with pytest.raises(MemoryValidationError):
        await manager.confidence.record_outcome(pred.id, correct=True)
    # Convention holds: the record stays 0.5-confident.
    assert (await manager.get(pred.id)).confidence == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_contradiction_dents_and_floors(manager) -> None:
    m = await manager.remember("Claim A.", confidence=0.5)
    r = await manager.confidence.apply_contradiction(m.id, contradicted_by="other-1")
    assert r.applied
    assert (await manager.get(m.id)).confidence == pytest.approx(0.45)
    # Same contradictor twice: duplicate, not new evidence.
    r2 = await manager.confidence.apply_contradiction(m.id, contradicted_by="other-1")
    assert not r2.applied

    low = await manager.remember("Fragile.", confidence=0.22)
    await manager.confidence.apply_contradiction(low.id, contradicted_by="x1")
    assert (await manager.get(low.id)).confidence == pytest.approx(0.2)
    await manager.confidence.apply_contradiction(low.id, contradicted_by="x2")
    assert (await manager.get(low.id)).confidence == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_contradiction_refuses_history(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryValidationError

    ep = await manager.episodes.start_episode("goal", episode_id="ep-contra")
    with pytest.raises(MemoryValidationError):
        await manager.confidence.apply_contradiction(ep.id, contradicted_by="x")


@pytest.mark.asyncio
async def test_retrieval_never_bumps_confidence(manager) -> None:
    m = await manager.remember("Retrieved fact about the Brave browser.")
    before = m.confidence
    for _ in range(5):
        await manager.retrieve("Brave browser")
        await manager.search("Brave browser")
    row = await manager.get(m.id)
    assert row is not None
    assert row.access_count > 0  # accesses were recorded...
    assert row.confidence == pytest.approx(before)  # ...but confidence didn't move


@pytest.mark.asyncio
async def test_age_alone_never_moves_confidence(manager) -> None:
    m = await manager.remember("Old fact.", confidence=0.7)
    row = await manager.get(m.id)
    assert row is not None
    # Simulate a year of untouched age on the touch timestamps.
    import datetime

    aged = row.updated_at - datetime.timedelta(days=365)
    row.updated_at = aged
    row.created_at = aged
    await manager._repo.update(row)
    # Lifecycle may restatus it, but confidence is untouched by time.
    await manager.decay()
    assert (await manager.get(m.id)).confidence == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_evidence_history_is_capped_and_auditable(manager) -> None:
    m = await manager.remember("Audited fact.", confidence=0.5)
    await manager.confidence.confirm(m.id, source="s1")
    await manager.confidence.record_reuse(m.id, succeeded=True)
    history = await manager.confidence.history(m.id)
    assert [e["rule"] for e in history] == ["confirm", "reuse_succeeded"]
    assert history[0]["source"] == "s1"
    assert history[0]["before"] == pytest.approx(0.5)
    assert history[0]["after"] == pytest.approx(0.55)
    assert history[1]["delta"] == pytest.approx(0.03)
    assert all("at" in e for e in history)

    # Flood with alternating rules (net-zero drift, so no bound stops the
    # writes): history caps at 20, oldest dropped.
    for i in range(30):
        await manager.confidence.confirm(m.id, source=f"flood-{i}")
        await manager.confidence.record_reuse(m.id, succeeded=False)
    history = await manager.confidence.history(m.id)
    assert len(history) == 20
    # Alternating confirm/reuse: the last confirm in the capped window.
    confirm_sources = [e["source"] for e in history if e["rule"] == "confirm"]
    assert confirm_sources[-1] == "flood-29"
    assert history[-1]["rule"] == "reuse_failed"


@pytest.mark.asyncio
async def test_missing_row_raises_not_found(manager) -> None:
    from aetheros.core.errors.memory_error import MemoryNotFoundError

    with pytest.raises(MemoryNotFoundError):
        await manager.confidence.confirm("no-such-id")
    with pytest.raises(MemoryNotFoundError):
        await manager.confidence.history("no-such-id")


@pytest.mark.asyncio
async def test_forecast_probability_untouched_by_fact_updates(manager) -> None:
    # The stored-fact number and the forecast number are different things:
    # updating confidence around a prediction row is refused, and the
    # prediction payload's own probabilities are never rewritten.
    from aetheros.memory.domain import PredictionMemory

    pred = await manager.remember_prediction(
        PredictionMemory(
            instrument="RELIANCE", direction="UP", timeframe="1d",
            horizon="1 trading day", prob_up=0.78,
            model="momentum_v3", model_version="3.2.1",
        )
    )
    row = await manager.get(pred.id)
    assert row is not None
    assert row.data["prediction"]["prob_up"] == pytest.approx(0.78)
    assert row.confidence == pytest.approx(0.5)
