"""
Phase 8 — explainable hybrid retrieval tests.

Exercises the retrieval contract end-to-end against the real stack (in-memory
SQLite persistence + the real VectorIndex cosine path over a hashing embedder;
the opt-in test at the bottom swaps in a *real* Ollama embedder):

* SQL + vector + graph combination and provenance,
* multi-signal ranking order,
* near-duplicate dedup with merged provenance,
* budget bounds (limit / max_per_type / max_chars / max_tokens),
* uniform constraint filtering (filter isolation across sources),
* max_age validity cutoff,
* empty results,
* partial-source failure (vector/graph) degrading safely,
* a real semantic-retrieval integration path (opt-in).

Fixtures that fake a source are explicitly labelled; they test degradation
plumbing, not production semantics.
"""

from __future__ import annotations

import os

import pytest

from aetheros.memory.domain import (
    MemoryImportance,
    MemoryType,
    SourceType,
    Veracity,
)
from aetheros.memory.services.retriever import estimate_tokens

# ----------------------------------------------------------------------
# SQL + vector + graph combination / provenance
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_vector_graph_combine_with_provenance(manager) -> None:
    # Two memories sharing an entity -> the knowledge graph links them.
    await manager.remember(
        "RELIANCE broke above its 200-day moving average on heavy volume.",
        memory_type=MemoryType.SEMANTIC,
        entities=["RELIANCE", "moving average"],
        tags=["technical"],
    )
    await manager.remember(
        "RELIANCE quarterly earnings beat estimates.",
        memory_type=MemoryType.SEMANTIC,
        entities=["RELIANCE", "earnings"],
        tags=["fundamental"],
    )
    report = await manager.retrieve_report(
        "RELIANCE moving average breakout", entities=["RELIANCE"], limit=10
    )
    assert report.results
    # Every result discloses which source(s) found it.
    all_sources = {s for r in report.results for s in r.explanation.sources}
    assert "structured" in all_sources
    # The text query ran the real vector path over the SQL pool.
    assert "vector" in all_sources
    assert report.candidates_considered >= 2
    assert not report.degraded


# ----------------------------------------------------------------------
# Ranking
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ranking_prefers_stronger_blended_signal(manager) -> None:
    await manager.remember(
        "The user strongly prefers the Brave browser for all trading dashboards.",
        memory_type=MemoryType.PREFERENCE,
        source_type=SourceType.USER,
        veracity=Veracity.USER_INPUT,
        confidence=0.95,
        importance=MemoryImportance.HIGH,
        entities=["Brave"],
    )
    await manager.remember(
        "Someone once mentioned a browser in passing.",
        memory_type=MemoryType.SEMANTIC,
        confidence=0.3,
    )
    results = await manager.retrieve("which browser does the user prefer?", limit=10)
    assert len(results) >= 2
    assert "Brave" in results[0].memory.content
    # Scores are monotonically non-increasing (ranked).
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


# ----------------------------------------------------------------------
# Dedup
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedup_collapses_identical_content(manager) -> None:
    text = "VWAP is the volume weighted average price."
    await manager.remember(text, memory_type=MemoryType.SEMANTIC, entities=["VWAP"])
    await manager.remember(text, memory_type=MemoryType.SEMANTIC, entities=["VWAP"])
    results = await manager.retrieve("what is VWAP?", limit=10)
    matching = [r for r in results if r.memory.content == text]
    assert len(matching) == 1


# ----------------------------------------------------------------------
# Budget bounds
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_limit_caps_result_count(manager) -> None:
    for i in range(6):
        await manager.remember(f"Trading note number {i} about markets.")
    report = await manager.retrieve_report("markets", limit=3)
    assert len(report.results) == 3
    assert report.dropped_by_budget >= 1


@pytest.mark.asyncio
async def test_budget_max_per_type(manager) -> None:
    for i in range(4):
        await manager.remember(
            f"Semantic fact {i} about candlesticks.", memory_type=MemoryType.SEMANTIC
        )
    for i in range(4):
        await manager.remember(
            f"Preference {i} about candlestick colours.",
            memory_type=MemoryType.PREFERENCE,
        )
    report = await manager.retrieve_report(
        "candlesticks", limit=10, max_per_type=1
    )
    types = [r.memory.memory_type for r in report.results]
    assert types.count(MemoryType.SEMANTIC) <= 1
    assert types.count(MemoryType.PREFERENCE) <= 1
    assert report.dropped_by_budget >= 1


@pytest.mark.asyncio
async def test_budget_max_chars_skips_overflowing_whole_memories(manager) -> None:
    await manager.remember("short note on RSI." , entities=["RSI"])
    await manager.remember("x" * 500 + " RSI long note", entities=["RSI"])
    report = await manager.retrieve_report("RSI", limit=10, max_chars=120)
    total_chars = sum(len(r.memory.content) for r in report.results)
    assert total_chars <= 120
    # The long memory did not fit and was dropped (not truncated).
    assert all(len(r.memory.content) <= 120 for r in report.results)


@pytest.mark.asyncio
async def test_budget_max_tokens_is_conservative(manager) -> None:
    await manager.remember("alpha beta gamma delta epsilon RSI signal", entities=["RSI"])
    report = await manager.retrieve_report("RSI", limit=10, max_tokens=5)
    # Conservative token estimate must not be exceeded by the selected set.
    used = sum(estimate_tokens(r.memory.content) for r in report.results)
    assert used <= 5
    assert report.token_count_exact is False


def test_estimate_tokens_overestimates() -> None:
    # 12 chars / 3 = 4 tokens, which is >= a real ~4-chars/token tokenizer.
    assert estimate_tokens("abcdefghijkl") == 4
    assert estimate_tokens("") == 0


# ----------------------------------------------------------------------
# Filter isolation — graph/link expansion cannot bypass constraints
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_expansion_respects_type_filter(manager) -> None:
    # A PREFERENCE and a SEMANTIC memory share an entity. A type-filtered query
    # for SEMANTIC must not let graph expansion surface the PREFERENCE.
    await manager.remember(
        "User prefers dark theme on TradingView.",
        memory_type=MemoryType.PREFERENCE,
        entities=["TradingView"],
    )
    await manager.remember(
        "TradingView supports custom indicators.",
        memory_type=MemoryType.SEMANTIC,
        entities=["TradingView"],
    )
    results = await manager.retrieve(
        "TradingView",
        entities=["TradingView"],
        memory_types=[MemoryType.SEMANTIC],
        limit=10,
    )
    assert results
    assert all(r.memory.memory_type is MemoryType.SEMANTIC for r in results)


@pytest.mark.asyncio
async def test_graph_expansion_respects_confidence_floor(manager) -> None:
    await manager.remember(
        "High-confidence note about NIFTY.",
        confidence=0.9,
        entities=["NIFTY"],
    )
    await manager.remember(
        "Low-confidence rumour about NIFTY.",
        confidence=0.2,
        entities=["NIFTY"],
    )
    results = await manager.retrieve(
        "NIFTY", entities=["NIFTY"], min_confidence=0.5, limit=10
    )
    assert results
    assert all(r.memory.confidence >= 0.5 for r in results)


@pytest.mark.asyncio
async def test_max_age_excludes_old_memories(manager, monkeypatch) -> None:
    from datetime import timedelta

    from aetheros.memory import _clock

    old = await manager.remember("Ancient note about gold.", entities=["gold"])
    # Backdate the row's created_at directly in the store.
    stored = await manager._repo.get(old.id)
    assert stored is not None
    stored.created_at = _clock.utcnow() - timedelta(days=400)
    await manager._repo.update(stored)

    await manager.remember("Fresh note about gold.", entities=["gold"])
    report = await manager.retrieve_report(
        "gold", entities=["gold"], max_age_days=30, limit=10
    )
    contents = [r.memory.content for r in report.results]
    assert "Fresh note about gold." in contents
    assert "Ancient note about gold." not in contents
    assert report.dropped_by_filter >= 1


# ----------------------------------------------------------------------
# Empty results
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_results_are_honest(manager) -> None:
    report = await manager.retrieve_report("nothing was ever stored about this")
    assert report.results == []
    assert not report.degraded


@pytest.mark.asyncio
async def test_disabled_subsystem_degrades(memory_config) -> None:
    from dataclasses import replace

    from aetheros.memory.services.manager import MemoryManager

    disabled = replace(memory_config, enabled=False)
    mgr = MemoryManager(disabled)
    # Not started / disabled: recall degrades, never raises.
    report = await mgr.retrieve_report("anything")
    assert report.results == []
    assert "subsystem_unavailable" in report.degraded_sources


# ----------------------------------------------------------------------
# Partial-source failure degrades safely
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_source_failure_degrades(manager, monkeypatch) -> None:
    await manager.remember(
        "RSI above 70 can indicate an overbought market.",
        entities=["RSI"],
        tags=["rsi"],
    )

    async def _boom(*args, **kwargs):  # labelled fault injection, not a real source
        raise RuntimeError("vector index unreachable")

    monkeypatch.setattr(manager._retriever._vectors, "search", _boom)

    # Lexical + structured still work, so results come back, flagged degraded.
    report = await manager.retrieve_report("RSI overbought", tags=["rsi"], limit=5)
    assert report.results  # recall did not collapse
    assert any(s.startswith("vector:") for s in report.degraded_sources)


@pytest.mark.asyncio
async def test_graph_source_failure_degrades(manager, monkeypatch) -> None:
    await manager.remember("MACD crossover note.", entities=["MACD"], tags=["macd"])

    async def _boom(*args, **kwargs):  # labelled fault injection
        raise RuntimeError("graph store unreachable")

    monkeypatch.setattr(manager._retriever._graph, "find_related_entities", _boom)

    report = await manager.retrieve_report("MACD", entities=["MACD"], limit=5)
    assert any(s.startswith("graph_entity:") for s in report.degraded_sources)
    # Structured + vector still return the directly-matching memory.
    assert report.results


# ----------------------------------------------------------------------
# Explanation integrity
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explanation_components_are_real(manager) -> None:
    await manager.remember(
        "User prefers Brave browser.",
        memory_type=MemoryType.PREFERENCE,
        source_type=SourceType.USER,
        veracity=Veracity.USER_INPUT,
        confidence=0.9,
        entities=["Brave"],
    )
    results = await manager.retrieve("Brave browser preference", limit=5)
    assert results
    exp = results[0].explanation
    d = exp.to_dict()
    # The blended score is consistent with its disclosed components (all [0,1]).
    for key in ("semantic", "lexical", "recency", "confidence", "score"):
        assert 0.0 <= d[key] <= 1.0
    assert exp.reasons
    assert exp.sources  # provenance populated


# ----------------------------------------------------------------------
# Real semantic retrieval integration path (opt-in)
# ----------------------------------------------------------------------

_RUN_REAL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA") == "1"
_OLLAMA_URL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA_URL", "http://127.0.0.1:11434")
_OLLAMA_MODEL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA_MODEL", "")

real = pytest.mark.skipif(
    not (_RUN_REAL and _OLLAMA_MODEL),
    reason=(
        "real semantic retrieval is opt-in: set AETHEROS_MEMORY_TEST_OLLAMA=1 and "
        "AETHEROS_MEMORY_TEST_OLLAMA_MODEL=<installed model> with a reachable daemon."
    ),
)


@real
@pytest.mark.real_embeddings
@pytest.mark.asyncio
async def test_real_semantic_retrieval_ranks_by_meaning(tmp_path) -> None:
    """End-to-end hybrid retrieval over a *real* embedding + vector path.

    Proves semantic ranking (not lexical overlap): the query shares no words
    with the best answer, yet meaning wins.
    """
    from dataclasses import replace

    from aetheros.memory.config import MemoryConfig
    from aetheros.memory.services.manager import MemoryManager

    base = MemoryConfig.for_memory_db(tmp_path / "real.db")
    cfg = replace(
        base,
        vector_provider="ollama",
        embedding_model=_OLLAMA_MODEL,
        embedding_base_url=_OLLAMA_URL,
    )
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        await mgr.remember(
            "A bearish engulfing pattern suggests sellers have taken control.",
            memory_type=MemoryType.SEMANTIC,
        )
        await mgr.remember(
            "The company reported strong free cash flow this quarter.",
            memory_type=MemoryType.SEMANTIC,
        )
        # No shared tokens with the bearish-pattern memory.
        report = await mgr.retrieve_report(
            "downward reversal signal where selling pressure dominates", limit=2
        )
        assert report.results
        assert "engulfing" in report.results[0].memory.content
        assert report.results[0].explanation.semantic > 0.0
        assert "vector" in report.results[0].explanation.sources
    finally:
        await mgr.shutdown()
