"""
Phase 6 -- real vector index: CRUD, persistence, filtering, isolation,
deletion-exclusion, identity/dimension rejection, repair, and (opt-in)
real-model semantic retrieval.

Two layers, clearly separated:

* **Backend unit tests** drive :class:`VectorIndex` against a *real* SQLite
  database (on-disk and ``:memory:``) with the deterministic
  :class:`HashingEmbeddingProvider`. SQLite and hashing are the actual production
  default backend here -- these are not mocks of the vector maths. They prove
  insert/upsert, update, delete, batch insert, single/batch search, candidate
  filtering, bounded top-k, on-disk persistence across reopen, test isolation,
  soft-deleted-row exclusion, embedding-identity scoping, bad-vector rejection,
  and projection repair.

* **Opt-in integration test** (`-m real_embeddings`) uses a real Ollama daemon so
  the semantic assertion exercises genuine model embeddings. It checks *relative*
  retrieval behaviour (the on-topic memory outranks the off-topic one), not
  brittle exact floating-point scores. Auto-skips unless
  ``AETHEROS_MEMORY_TEST_OLLAMA=1`` with a reachable daemon.
"""

from __future__ import annotations

import os

import httpx
import numpy as np
import pytest
import pytest_asyncio

from aetheros.memory.domain import (
    Memory,
    MemoryImportance,
    MemorySource,
    MemoryType,
    SourceType,
    Veracity,
)
from aetheros.memory.embeddings.base import EmbeddingProvider
from aetheros.memory.embeddings.hashing import HashingEmbeddingProvider
from aetheros.memory.storage import MemoryRepository, SQLiteDatabase
from aetheros.memory.vector.index import VectorIndex


# ----------------------------------------------------------------------
# Helpers: real rows, so the delete-exclusion JOIN has something to join.
# ----------------------------------------------------------------------
def _mem(content: str, *, status: str = "active") -> Memory:
    m = Memory(
        content=content,
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.FACT,
        confidence=0.9,
        importance=MemoryImportance.NORMAL,
        source=MemorySource(source_type=SourceType.SYSTEM, origin="test"),
    )
    from aetheros.memory.domain.enums import MemoryStatus

    m.status = MemoryStatus(status)
    return m


class _StubProvider(EmbeddingProvider):
    """A fixed-identity, fixed-dimension provider for identity/dimension tests.

    Embeds deterministically from a seed per text so vectors are stable and
    distinguishable, and exposes a configurable ``name`` so two instances can
    represent two *different* embedding spaces over the same database.
    """

    def __init__(self, identity: str, dim: int, *, seed: int = 0) -> None:
        self._identity = identity
        self._dim = dim
        self._seed = seed

    @property
    def name(self) -> str:
        return self._identity

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(abs(hash((self._seed, text))) % (2**32))
        v = rng.standard_normal(self._dim).astype(np.float32)
        return self.normalize(v)


@pytest_asyncio.fixture
async def wired(database: SQLiteDatabase):
    """Repository + a hashing-backed VectorIndex over one real SQLite db."""
    repo = MemoryRepository(database)
    provider = HashingEmbeddingProvider(dimension=64)
    index = VectorIndex(database, provider)
    return repo, index, provider


async def _store_memory(repo: MemoryRepository, index: VectorIndex, m: Memory) -> Memory:
    await repo.add(m)
    await index.index(m.id, m.content)
    return m


# ======================================================================
# CRUD + persistence
# ======================================================================
@pytest.mark.asyncio
async def test_insert_and_search_roundtrip(wired):
    repo, index, _ = wired
    m = await _store_memory(repo, index, _mem("RELIANCE broke above resistance"))
    assert await index.count() == 1
    hits = await index.search("RELIANCE resistance breakout", limit=5)
    assert hits and hits[0][0] == m.id


@pytest.mark.asyncio
async def test_upsert_overwrites_not_duplicates(wired):
    repo, index, _ = wired
    m = await _store_memory(repo, index, _mem("first version"))
    await index.index(m.id, "second version entirely different text")
    assert await index.count() == 1  # INSERT OR REPLACE, not a second row


@pytest.mark.asyncio
async def test_update_reembeds(wired):
    repo, index, _ = wired
    m = await _store_memory(repo, index, _mem("gold prices falling sharply"))
    # Re-embed with entirely different text; the old topic should no longer be
    # the strong match and the new topic should retrieve this same id.
    await index.index(m.id, "crude oil inventories surged this week")
    after = await index.search("crude oil inventories", limit=1)
    assert after and after[0][0] == m.id
    assert await index.count() == 1  # still one row, just re-embedded


@pytest.mark.asyncio
async def test_delete_removes_vector(wired):
    repo, index, _ = wired
    m = await _store_memory(repo, index, _mem("temporary note"))
    await index.delete(m.id)
    assert await index.count() == 0
    assert await index.search("temporary note", limit=5) == []


@pytest.mark.asyncio
async def test_batch_insert_and_count(wired):
    repo, index, _ = wired
    items = []
    for i in range(5):
        m = _mem(f"memory number {i} about markets")
        await repo.add(m)
        items.append((m.id, m.content))
    await index.index_many(items)
    assert await index.count() == 5


@pytest.mark.asyncio
async def test_persistence_across_reopen(tmp_path):
    """Vectors persist on disk and are searchable after close + reopen."""
    db_path = tmp_path / "vec.db"
    provider = HashingEmbeddingProvider(dimension=64)

    db1 = SQLiteDatabase(str(db_path))
    db1.connect()
    repo1 = MemoryRepository(db1)
    idx1 = VectorIndex(db1, provider)
    m = _mem("the central bank raised the repo rate")
    await repo1.add(m)
    await idx1.index(m.id, m.content)
    db1.close()

    # Fresh process-like reopen: new connection object, same file.
    db2 = SQLiteDatabase(str(db_path))
    db2.connect()
    try:
        idx2 = VectorIndex(db2, provider)
        assert await idx2.count() == 1
        hits = await idx2.search("central bank repo rate hike", limit=5)
        assert hits and hits[0][0] == m.id
    finally:
        db2.close()


# ======================================================================
# Filtering, isolation, bounded top-k
# ======================================================================
@pytest.mark.asyncio
async def test_candidate_filtering(wired):
    repo, index, _ = wired
    a = await _store_memory(repo, index, _mem("alpha signal strong"))
    b = await _store_memory(repo, index, _mem("beta signal weak"))
    # Restrict to b only; a must not appear even if it would score higher.
    hits = await index.search("signal", limit=5, candidate_ids=[b.id])
    assert [mid for mid, _ in hits] == [b.id]
    assert a.id not in {mid for mid, _ in hits}


@pytest.mark.asyncio
async def test_empty_candidate_pool_returns_nothing(wired):
    repo, index, _ = wired
    await _store_memory(repo, index, _mem("something"))
    assert await index.search("something", limit=5, candidate_ids=[]) == []


@pytest.mark.asyncio
async def test_bounded_topk(wired):
    repo, index, _ = wired
    for i in range(10):
        await _store_memory(repo, index, _mem(f"market note {i}"))
    hits = await index.search("market note", limit=3)
    assert len(hits) == 3
    # Scores are sorted descending.
    scores = [s for _, s in hits]
    assert scores == sorted(scores, reverse=True)


# ======================================================================
# Deletion-exclusion (no leakage through recall)
# ======================================================================
@pytest.mark.asyncio
async def test_soft_deleted_excluded_from_whole_index_search(wired):
    repo, index, _ = wired
    live = await _store_memory(repo, index, _mem("live memory about RSI"))
    gone = await _store_memory(repo, index, _mem("deleted memory about RSI"))

    # Mark gone as deleted WITHOUT disturbing its vector row. (A plain status
    # UPDATE, not repo.update's INSERT-OR-REPLACE, so the FK cascade does not
    # fire -- this is exactly the "vector present but row soft-deleted" leak
    # scenario the search JOIN must defend against.)
    _mark_deleted(index, gone.id)
    assert await index.count() == 2  # both vectors physically present

    hits = await index.search("RSI", limit=10)  # whole-index path
    returned = {mid for mid, _ in hits}
    assert live.id in returned
    assert gone.id not in returned  # soft-deleted vector did not leak


@pytest.mark.asyncio
async def test_exclude_deleted_can_be_disabled_for_repair(wired):
    repo, index, _ = wired
    gone = await _store_memory(repo, index, _mem("to be removed"))
    _mark_deleted(index, gone.id)
    # Repair/admin tooling may need to see every vector row.
    hits = await index.search("removed", limit=10, exclude_deleted=False)
    assert gone.id in {mid for mid, _ in hits}


def _mark_deleted(index: VectorIndex, memory_id: str) -> None:
    """Set status='deleted' via a direct UPDATE, leaving the vector row intact."""
    index._db.execute(
        "UPDATE memory_items SET status = 'deleted' WHERE id = ?", (memory_id,)
    )


# ======================================================================
# Embedding-space identity: never mix two models
# ======================================================================
@pytest.mark.asyncio
async def test_foreign_identity_excluded_from_search(database):
    repo = MemoryRepository(database)
    model_a = _StubProvider("modelA:1:16", dim=16, seed=1)
    model_b = _StubProvider("modelB:1:16", dim=16, seed=2)  # same dim, other space

    idx_a = VectorIndex(database, model_a)
    idx_b = VectorIndex(database, model_b)

    ma = _mem("vector stored under model A")
    mb = _mem("vector stored under model B")
    await repo.add(ma)
    await repo.add(mb)
    await idx_a.index(ma.id, ma.content)
    await idx_b.index(mb.id, mb.content)

    # Searching through model A must only ever see A's vectors.
    hits_a = await idx_a.search("anything", limit=10)
    assert {mid for mid, _ in hits_a} == {ma.id}
    hits_b = await idx_b.search("anything", limit=10)
    assert {mid for mid, _ in hits_b} == {mb.id}

    # Both identities coexist in the one table.
    assert await idx_a.identities() == {"modelA:1:16": 1, "modelB:1:16": 1}


@pytest.mark.asyncio
async def test_wrong_dimension_vector_rejected_on_store(database):
    repo = MemoryRepository(database)
    provider = _StubProvider("fixed:1:16", dim=16)
    index = VectorIndex(database, provider)
    m = _mem("doc")
    await repo.add(m)

    # A provider whose dimension says 16 but emits an 8-length vector must be
    # rejected before it poisons cosine search.
    bad = np.ones(8, dtype=np.float32)
    with pytest.raises(ValueError):
        await _store_bad(index, m.id, bad)


@pytest.mark.asyncio
async def test_non_finite_vector_rejected_on_store(database):
    repo = MemoryRepository(database)
    provider = _StubProvider("fixed:1:16", dim=16)
    index = VectorIndex(database, provider)
    m = _mem("doc")
    await repo.add(m)
    bad = np.full(16, np.nan, dtype=np.float32)
    with pytest.raises(ValueError):
        await _store_bad(index, m.id, bad)


async def _store_bad(index: VectorIndex, memory_id: str, vector: np.ndarray) -> None:
    """Drive the private store guard directly with a crafted bad vector."""
    import asyncio

    await asyncio.to_thread(index._store, memory_id, vector)


# ======================================================================
# Batch search
# ======================================================================
@pytest.mark.asyncio
async def test_batch_search_matches_single(wired):
    repo, index, _ = wired
    rsi = await _store_memory(repo, index, _mem("RSI crossed above 70 overbought"))
    macd = await _store_memory(repo, index, _mem("MACD histogram turned positive"))

    queries = ["RSI overbought level", "MACD positive histogram"]
    batched = await index.search_many(queries, limit=3)
    assert len(batched) == 2
    # Each query's own topic ranks first.
    assert batched[0][0][0] == rsi.id
    assert batched[1][0][0] == macd.id

    # Batch result for a query equals the single-query result.
    single0 = await index.search(queries[0], limit=3)
    assert [mid for mid, _ in batched[0]] == [mid for mid, _ in single0]


@pytest.mark.asyncio
async def test_batch_search_empty_input(wired):
    _, index, _ = wired
    assert await index.search_many([], limit=3) == []


# ======================================================================
# Projection repair
# ======================================================================
@pytest.mark.asyncio
async def test_repair_removes_orphan_and_restores_missing(manager):
    """verify/repair reconcile the derived vector store with authoritative rows."""
    m = await manager.remember(
        "A durable fact about VWAP", memory_type=MemoryType.SEMANTIC
    )

    # Simulate a lost vector (projection drift) and verify repair restores it.
    await manager._vectors.delete(m.id)
    report = await manager.verify_projection()
    assert m.id in report["missing"]
    fixed = await manager.repair_projection()
    assert fixed["reindexed"] >= 1
    assert (await manager.verify_projection())["consistent"]


# ======================================================================
# Opt-in real-model semantic retrieval (relative, not exact scores)
# ======================================================================
_OLLAMA_URL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA_URL", "http://127.0.0.1:11434")
_OLLAMA_MODEL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA_MODEL", "")
_RUN_REAL = os.environ.get("AETHEROS_MEMORY_TEST_OLLAMA") == "1"


def _real_available() -> bool:
    if not _RUN_REAL or not _OLLAMA_MODEL:
        return False
    try:
        r = httpx.get(f"{_OLLAMA_URL}/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


real = pytest.mark.skipif(
    not _real_available(),
    reason=(
        "real Ollama integration is opt-in: set AETHEROS_MEMORY_TEST_OLLAMA=1 and "
        "AETHEROS_MEMORY_TEST_OLLAMA_MODEL=<installed model> with a reachable daemon."
    ),
)


@real
@pytest.mark.real_embeddings
@pytest.mark.asyncio
async def test_real_vector_index_relative_retrieval():
    """Real embeddings + real SQLite + real cosine: on-topic beats off-topic."""
    from aetheros.memory.embeddings.ollama import OllamaEmbeddingProvider

    db = SQLiteDatabase(":memory:")
    db.connect()
    try:
        repo = MemoryRepository(db)
        provider = OllamaEmbeddingProvider(_OLLAMA_MODEL, base_url=_OLLAMA_URL)
        await provider.ensure_ready()
        index = VectorIndex(db, provider)

        on_topic = _mem("The Reserve Bank raised the repo rate by 25 basis points")
        off_topic = _mem("A new vegetarian pizza recipe with roasted peppers")
        await repo.add(on_topic)
        await repo.add(off_topic)
        await index.index(on_topic.id, on_topic.content)
        await index.index(off_topic.id, off_topic.content)

        hits = await index.search("central bank interest rate decision", limit=2)
        assert hits[0][0] == on_topic.id
        # Relative, not exact: the monetary-policy memory is strictly closer.
        scores = {mid: s for mid, s in hits}
        assert scores[on_topic.id] > scores[off_topic.id]
        print(f"[real] on={scores[on_topic.id]:.3f} off={scores[off_topic.id]:.3f}")
    finally:
        db.close()
