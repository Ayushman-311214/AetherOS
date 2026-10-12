"""
Ollama embedding provider -- the first *real* semantic embedder (spec Phase 5).

Talks to a running Ollama daemon's ``POST /api/embeddings`` endpoint over HTTP
and returns an L2-normalised float32 vector, behind the same
:class:`~aetheros.memory.embeddings.base.EmbeddingProvider` interface the hashing
fallback implements -- so the vector index and retriever are untouched
(CLAUDE.md section 10: depend on the interface, never the concrete provider).

Design mirrors the trading Yahoo provider's HTTP conventions so the codebase has
one shape for network I/O: an optional injected ``httpx.AsyncClient`` (owned by
the caller, testable with ``httpx.MockTransport``), bounded per-request timeouts,
and opt-in bounded retries with exponential backoff on *transient* failures only.

Honesty guarantees this provider upholds (contract / CLAUDE.md sections 9, 20):

* The embedding-space **identity** encoded in :attr:`name` includes the provider,
  the exact model tag, and the dimension -- not just the dimension. Two different
  models that happen to share a dimension are *not* interchangeable, so their
  vectors must never be mixed in one index (the vector index enforces this).
* Every returned vector is validated (correct dimension, non-empty, finite)
  before it is trusted. A partial/garbage response raises rather than silently
  poisoning cosine search.
* The reported :attr:`dimension` is probed once from the real model (there is no
  reliable static table of Ollama embedding dimensions) and then held stable; a
  later response of a different length is a hard error.
* Errors never include the configured text payload or any credential -- only the
  model tag, endpoint, and HTTP status.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx
import numpy as np

from ...core.errors.memory_error import EmbeddingError
from .base import EmbeddingProvider

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_TIMEOUT = 30.0
#: HTTP statuses worth retrying -- transient server/rate conditions only.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embeds text via a local/remote Ollama daemon's embeddings endpoint."""

    def __init__(
        self,
        model: str,
        *,
        dimension: int | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        max_batch: int = 32,
        sleeper: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        model = (model or "").strip()
        if not model:
            raise EmbeddingError(
                "Ollama embedding provider requires a model name "
                "(set MEMORY_EMBEDDING_MODEL).",
                hint="e.g. nomic-embed-text, mxbai-embed-large, or any pulled model.",
            )
        self._model = model
        # None => probe lazily from the model on first use / ensure_ready; a
        # supplied value is treated as the authoritative, pinned dimension.
        self._dim: int | None = int(dimension) if dimension is not None else None
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_batch = max(1, max_batch)
        self._sleeper = sleeper

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Embedding-space identity: provider + exact model + dimension."""
        dim = self._dim if self._dim is not None else "unprobed"
        return f"ollama:{self._model}:{dim}"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        if self._dim is None:
            raise EmbeddingError(
                "Ollama embedding dimension is not known yet; call "
                "`await provider.ensure_ready()` (or embed once) first.",
                hint="Dimension is probed from the live model, not assumed.",
                context={"model": self._model},
            )
        return self._dim

    # ------------------------------------------------------------------
    # Readiness / validation
    # ------------------------------------------------------------------

    async def ensure_ready(self) -> int:
        """
        Verify the daemon, model, and embedding capability for real.

        Confirms the model is present in ``/api/tags`` *and* that it actually
        produces a usable embedding (model-list presence alone is not proof the
        model can embed). Pins and returns the observed dimension. Raises
        :class:`EmbeddingError` with an actionable hint on any failure.
        """
        tags = await self._get_json("/api/tags")
        available = {
            str(m.get("name", "")) for m in tags.get("models", []) if isinstance(m, dict)
        }
        # Ollama tags are often "<name>:latest"; accept a bare name match too.
        if self._model not in available and f"{self._model}:latest" not in available:
            raise EmbeddingError(
                f"Model '{self._model}' is not available on the Ollama daemon.",
                hint=(
                    "Pull it first (`ollama pull <model>`), or set "
                    "MEMORY_EMBEDDING_MODEL to a model that is installed. "
                    f"Installed: {sorted(available) or 'none'}."
                ),
                context={"model": self._model, "endpoint": self._base_url},
            )
        # Prove it can embed and learn the true dimension from the model itself.
        probe = await self._embed_raw("probe")
        observed = int(probe.shape[0])
        if self._dim is not None and observed != self._dim:
            raise EmbeddingError(
                f"Model '{self._model}' produced dimension {observed}, but the "
                f"index/config pins {self._dim}. Incompatible embedding space.",
                hint=(
                    "A different model/dimension needs a separate index: rebuild "
                    "with an explicit migration rather than mixing spaces."
                ),
                context={"model": self._model, "observed": observed, "pinned": self._dim},
            )
        self._dim = observed
        return observed

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> np.ndarray:
        vec = await self._embed_raw(text)
        if self._dim is None:
            self._dim = int(vec.shape[0])
        self.validate_vector(vec, expected_dim=self._dim)
        return self.normalize(vec)

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """
        Embed many texts, preserving order and cardinality.

        Ollama's embeddings endpoint is single-text, so we issue bounded
        concurrent requests in chunks of ``max_batch`` and reassemble in input
        order. Returns exactly ``len(texts)`` vectors.
        """
        if not texts:
            return []
        out: list[np.ndarray] = []
        for start in range(0, len(texts), self._max_batch):
            chunk = texts[start : start + self._max_batch]
            vecs = await asyncio.gather(*(self.embed(t) for t in chunk))
            out.extend(vecs)
        if len(out) != len(texts):  # pragma: no cover - defensive invariant
            raise EmbeddingError(
                f"Batch cardinality mismatch: asked {len(texts)}, got {len(out)}.",
                context={"model": self._model},
            )
        return out

    # ------------------------------------------------------------------
    # HTTP (mirrors the trading provider's transient/permanent split)
    # ------------------------------------------------------------------

    async def _embed_raw(self, text: str) -> np.ndarray:
        payload = await self._post_json(
            "/api/embeddings", {"model": self._model, "prompt": text}
        )
        raw = payload.get("embedding")
        if not isinstance(raw, list) or not raw:
            raise EmbeddingError(
                f"Ollama returned no embedding for model '{self._model}'.",
                hint="Is this a model that supports embeddings?",
                context={"model": self._model},
            )
        return np.asarray(raw, dtype=np.float32)

    async def _get_json(self, path: str) -> dict:
        return await self._request("GET", path, None)

    async def _post_json(self, path: str, body: dict) -> dict:
        return await self._request("POST", path, body)

    async def _request(self, method: str, path: str, body: dict | None) -> dict:
        url = f"{self._base_url}{path}"
        attempts = self._max_retries + 1
        last: EmbeddingError | None = None
        for attempt in range(attempts):
            if attempt > 0:
                await self._sleeper(self._retry_backoff_seconds * (2 ** (attempt - 1)))
            try:
                return await self._request_once(method, url, body)
            except _Transient as exc:
                last = exc.as_embedding_error(self._model, url)
                continue
        assert last is not None  # only reachable after >= 1 transient failure
        raise last

    async def _request_once(self, method: str, url: str, body: dict | None) -> dict:
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.request(method, url, json=body)
        except httpx.HTTPError as exc:
            # Never leak the prompt payload -- only the endpoint and cause.
            raise _Transient(f"transport error: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code in _RETRYABLE_STATUS:
            raise _Transient(f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise EmbeddingError(
                f"Ollama returned HTTP {resp.status_code} for model "
                f"'{self._model}'.",
                hint="Check the model name and that the daemon is reachable.",
                context={"model": self._model, "endpoint": url, "status": resp.status_code},
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise EmbeddingError(
                f"Ollama returned a non-JSON response for '{self._model}'.",
                context={"model": self._model, "endpoint": url},
                cause=exc,
            ) from exc


class _Transient(Exception):
    """Internal marker for a retryable failure; carries no sensitive payload."""

    def as_embedding_error(self, model: str, url: str) -> EmbeddingError:
        return EmbeddingError(
            f"Ollama request to '{model}' failed after retries ({self}).",
            hint="The daemon may be down, overloaded, or the model is loading.",
            context={"model": model, "endpoint": url},
        )
