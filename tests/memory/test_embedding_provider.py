"""
Phase 5 -- real embedding provider: boundary + integration tests.

Two layers, clearly separated:

* **Boundary unit tests** drive :class:`OllamaEmbeddingProvider` against an
  ``httpx.MockTransport`` (a labelled external-boundary mock -- it stands in for
  the Ollama HTTP daemon, NOT for the embedding maths). They prove the provider's
  contract: validated dimension, non-empty/finite vectors, batch cardinality and
  order, bounded retries on transient failures, permanent-error handling, model
  availability checks, embedding-space identity, and that errors never leak the
  prompt payload. These do not and cannot prove real semantic retrieval.

* **Opt-in integration tests** (`-m real_embeddings`) talk to an *actual* running
  Ollama daemon with the configured model, exercising real embeddings, real
  SQLite persistence and the real cosine-search path. They auto-skip unless
  ``AETHEROS_MEMORY_TEST_OLLAMA=1`` and the daemon is reachable, so the default
  suite stays offline-safe.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import numpy as np
import pytest

from aetheros.core.errors.memory_error import EmbeddingError
from aetheros.memory.config import MemoryConfig
from aetheros.memory.embeddings import build_embedding_provider
from aetheros.memory.embeddings.base import EmbeddingProvider
from aetheros.memory.embeddings.ollama import OllamaEmbeddingProvider

# ----------------------------------------------------------------------
# Boundary mock: a stand-in Ollama daemon
# ----------------------------------------------------------------------


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok_embedding(dim: int, seed: float = 1.0) -> list[float]:
    return [seed + i * 0.01 for i in range(dim)]


def _daemon(
    *,
    dim: int = 8,
    models: list[str] | None = None,
    fail_times: int = 0,
    fail_status: int = 503,
):
    """Build a MockTransport handler emulating the two endpoints we use."""
    state = {"embed_calls": 0}
    model_names = models if models is not None else ["test-embed:latest"]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": n} for n in model_names]}
            )
        if request.url.path == "/api/embeddings":
            state["embed_calls"] += 1
            if state["embed_calls"] <= fail_times:
                return httpx.Response(fail_status, json={"error": "loading"})
            import json as _json

            prompt = _json.loads(request.content.decode())["prompt"]
            # Vary the vector by prompt length so different texts differ.
            return httpx.Response(
                200, json={"embedding": _ok_embedding(dim, 1.0 + len(prompt) * 0.001)}
            )
        return httpx.Response(404, json={"error": "not found"})

    return handler, state


# ----------------------------------------------------------------------
# Identity & dimension
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_name_encodes_provider_model_and_dimension():
    handler, _ = _daemon(dim=8)
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    assert p.name == "ollama:test-embed:unprobed"
    await p.ensure_ready()
    assert p.name == "ollama:test-embed:8"
    assert p.dimension == 8


@pytest.mark.asyncio
async def test_dimension_before_probe_raises():
    handler, _ = _daemon()
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    with pytest.raises(EmbeddingError):
        _ = p.dimension


@pytest.mark.asyncio
async def test_empty_model_name_rejected():
    with pytest.raises(EmbeddingError):
        OllamaEmbeddingProvider("   ")


# ----------------------------------------------------------------------
# ensure_ready: availability + capability (not model-list presence alone)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_ready_rejects_absent_model():
    handler, _ = _daemon(models=["some-other-model:latest"])
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    with pytest.raises(EmbeddingError) as exc:
        await p.ensure_ready()
    assert "not available" in str(exc.value)


@pytest.mark.asyncio
async def test_ensure_ready_accepts_bare_name_against_latest_tag():
    handler, _ = _daemon(models=["test-embed:latest"], dim=8)
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    assert await p.ensure_ready() == 8


@pytest.mark.asyncio
async def test_ensure_ready_detects_dimension_mismatch_against_pin():
    handler, _ = _daemon(dim=8)
    # Caller pins 16 but the model really emits 8 -> incompatible space.
    p = OllamaEmbeddingProvider("test-embed", dimension=16, client=_client(handler))
    with pytest.raises(EmbeddingError) as exc:
        await p.ensure_ready()
    assert "Incompatible embedding space" in str(exc.value)


# ----------------------------------------------------------------------
# Vector validation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_returns_normalized_finite_vector():
    handler, _ = _daemon(dim=8)
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    v = await p.embed("hello world")
    assert v.shape == (8,)
    assert v.dtype == np.float32
    assert np.isfinite(v).all()
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-5


@pytest.mark.asyncio
async def test_empty_embedding_response_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embeddings":
            return httpx.Response(200, json={"embedding": []})
        return httpx.Response(200, json={"models": [{"name": "test-embed:latest"}]})

    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    with pytest.raises(EmbeddingError):
        await p.embed("x")


@pytest.mark.asyncio
async def test_non_finite_embedding_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embeddings":
            return httpx.Response(200, json={"embedding": [1.0, float("nan"), 2.0, 3.0]})
        return httpx.Response(200, json={"models": [{"name": "test-embed:latest"}]})

    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    with pytest.raises(ValueError):
        await p.embed("x")


@pytest.mark.asyncio
async def test_validate_vector_static_guard():
    good = np.ones(4, dtype=np.float32)
    assert EmbeddingProvider.validate_vector(good, expected_dim=4) is good
    with pytest.raises(ValueError):
        EmbeddingProvider.validate_vector(np.ones(3, dtype=np.float32), expected_dim=4)
    with pytest.raises(ValueError):
        EmbeddingProvider.validate_vector(
            np.array([1.0, np.inf, 0.0, 0.0], dtype=np.float32), expected_dim=4
        )


# ----------------------------------------------------------------------
# Batch cardinality & order
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_batch_preserves_cardinality_and_order():
    handler, _ = _daemon(dim=8)
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler), max_batch=2)
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    vecs = await p.embed_batch(texts)
    assert len(vecs) == len(texts)
    # Each vector matches what embed() returns for the same text, in order.
    for text, vec in zip(texts, vecs, strict=True):
        single = await p.embed(text)
        assert np.allclose(vec, single)


@pytest.mark.asyncio
async def test_embed_batch_empty_is_empty():
    handler, _ = _daemon()
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    assert await p.embed_batch([]) == []


@pytest.mark.asyncio
async def test_embed_many_is_alias_of_batch():
    handler, _ = _daemon(dim=8)
    p = OllamaEmbeddingProvider("test-embed", client=_client(handler))
    a = await p.embed_many(["one", "two"])
    b = await p.embed_batch(["one", "two"])
    assert len(a) == len(b) == 2
    assert all(np.allclose(x, y) for x, y in zip(a, b, strict=True))


# ----------------------------------------------------------------------
# Retries & error hygiene
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transient_failures_are_retried_then_succeed():
    handler, state = _daemon(dim=8, fail_times=2, fail_status=503)
    sleeps: list[float] = []

    async def _sleep(s: float) -> None:
        sleeps.append(s)

    p = OllamaEmbeddingProvider(
        "test-embed", client=_client(handler), max_retries=3, sleeper=_sleep
    )
    v = await p.embed("retry me")
    assert v.shape == (8,)
    assert state["embed_calls"] == 3  # 2 failures + 1 success
    assert sleeps  # backoff was applied


@pytest.mark.asyncio
async def test_exhausted_retries_raise_without_leaking_prompt():
    handler, _ = _daemon(dim=8, fail_times=99, fail_status=503)

    async def _sleep(_s: float) -> None:
        return None

    p = OllamaEmbeddingProvider(
        "test-embed", client=_client(handler), max_retries=1, sleeper=_sleep
    )
    with pytest.raises(EmbeddingError) as exc:
        await p.embed("SECRET-PROMPT-TEXT")
    assert "SECRET-PROMPT-TEXT" not in str(exc.value)


@pytest.mark.asyncio
async def test_permanent_http_error_raises_immediately():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/embeddings":
            return httpx.Response(400, json={"error": "bad request"})
        return httpx.Response(200, json={"models": [{"name": "test-embed:latest"}]})

    p = OllamaEmbeddingProvider("test-embed", client=_client(handler), max_retries=5)
    with pytest.raises(EmbeddingError) as exc:
        await p.embed("x")
    assert "400" in str(exc.value)


# ----------------------------------------------------------------------
# Factory policy (strict vs loud degrade)
# ----------------------------------------------------------------------


def _cfg(**over) -> MemoryConfig:
    base = dict(
        enabled=True,
        database_path=Path(":memory:"),
        vector_provider="hashing",
        embedding_model="",
        embedding_dim=64,
        embedding_base_url="",
        embedding_fallback_to_hashing=False,
        retrieval_limit=5,
        similarity_threshold=0.0,
        decay_enabled=False,
        decay_halflife_days=30.0,
        consolidation_enabled=False,
        dedup_threshold=0.95,
        max_working_context=50,
        working_ttl_seconds=0.0,
        episode_max_actions=200,
        auto_remember=False,
        agent_recall_limit=5,
        agent_recall_min_score=0.0,
        agent_recall_max_chars=1500,
    )
    base.update(over)
    return MemoryConfig(**base)


def test_factory_builds_hashing_by_default():
    from aetheros.memory.embeddings import HashingEmbeddingProvider

    p = build_embedding_provider(_cfg(vector_provider="hashing"))
    assert isinstance(p, HashingEmbeddingProvider)


def test_factory_builds_ollama_without_network():
    p = build_embedding_provider(
        _cfg(vector_provider="ollama", embedding_model="nomic-embed-text")
    )
    assert isinstance(p, OllamaEmbeddingProvider)
    assert p.model == "nomic-embed-text"


def test_factory_unknown_provider_strict_raises():
    with pytest.raises(EmbeddingError):
        build_embedding_provider(_cfg(vector_provider="pinecone"))


def test_factory_unknown_provider_loud_degrade():
    from aetheros.memory.embeddings import HashingEmbeddingProvider

    p = build_embedding_provider(
        _cfg(vector_provider="pinecone", embedding_fallback_to_hashing=True)
    )
    assert isinstance(p, HashingEmbeddingProvider)


# ----------------------------------------------------------------------
# OPT-IN real-provider integration (real embeddings, real persistence)
# ----------------------------------------------------------------------

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
async def test_real_ollama_embed_identity_and_dimension():
    p = OllamaEmbeddingProvider(_OLLAMA_MODEL, base_url=_OLLAMA_URL)
    dim = await p.ensure_ready()
    assert dim > 0
    assert p.name == f"ollama:{_OLLAMA_MODEL}:{dim}"
    v = await p.embed("RELIANCE is trading above its 200-day moving average")
    assert v.shape == (dim,)
    assert np.isfinite(v).all()
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-4
    print(f"[real] model={_OLLAMA_MODEL} dim={dim} identity={p.name}")


@real
@pytest.mark.real_embeddings
@pytest.mark.asyncio
async def test_real_ollama_semantic_retrieval_end_to_end():
    """Real embeddings + real SQLite + real cosine search."""
    from aetheros.memory.services.manager import MemoryManager

    cfg = MemoryConfig.for_memory_db(Path(":memory:"))
    cfg = _cfg(
        vector_provider="ollama",
        embedding_model=_OLLAMA_MODEL,
        embedding_base_url=_OLLAMA_URL,
        database_path=Path(":memory:"),
    )
    mgr = MemoryManager(cfg)
    await mgr.initialize()
    try:
        await mgr.remember("The RBI raised the repo rate by 25 basis points today")
        await mgr.remember("My favourite programming language is Rust")
        results = await mgr.retrieve("central bank interest rate hike", limit=1)
        assert results
        top = results[0].memory.content.lower()
        assert "repo rate" in top or "rbi" in top
        ids = await mgr.embedding_identities()
        assert list(ids) == [mgr._embedder.name]  # single, uniform identity
        print(f"[real] identities={ids}")
    finally:
        await mgr.shutdown()
