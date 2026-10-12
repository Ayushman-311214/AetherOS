"""Embedding abstraction + the deterministic default (spec Phase 5)."""

from __future__ import annotations

from ...core.errors.memory_error import EmbeddingError
from ...core.logging import get_logger
from ..config import MemoryConfig
from .base import EmbeddingProvider
from .hashing import HashingEmbeddingProvider
from .ollama import OllamaEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "build_embedding_provider",
]

logger = get_logger("memory.embeddings")

_HASHING_NAMES = frozenset({"hashing", "hash", "local", ""})
_OLLAMA_NAMES = frozenset({"ollama"})


def build_embedding_provider(config: MemoryConfig) -> EmbeddingProvider:
    """
    Select an embedding provider from configuration (spec Phase 5/23).

    - ``hashing`` (default): the dependency-free deterministic embedder. Always
      available, offline-safe, lexical-grade semantics.
    - ``ollama``: a real semantic embedder backed by a running Ollama daemon.
      Its readiness (daemon reachable, model present, embedding capability,
      stable dimension) is validated at startup by the caller via
      ``await provider.ensure_ready()`` -- construction here is cheap and does
      no network I/O.

    Honesty rule (contract / CLAUDE.md section 10): an *explicitly requested*
    real provider is never silently swapped for the hashing embedder. The only
    accepted fallback is ``embedding_fallback_to_hashing=True`` (opt-in degrade),
    which is logged loudly as a warning; otherwise an unknown provider name is a
    configuration error.
    """
    provider = (config.vector_provider or "hashing").lower()

    if provider in _HASHING_NAMES:
        return HashingEmbeddingProvider(dimension=config.embedding_dim)

    if provider in _OLLAMA_NAMES:
        # dimension=None => probe from the live model at ensure_ready(); we never
        # assume an Ollama embedding dimension from a static table.
        return OllamaEmbeddingProvider(
            model=config.embedding_model,
            base_url=config.embedding_base_url or "http://127.0.0.1:11434",
        )

    # Unknown provider name. Degrade only if explicitly opted in, and loudly.
    if config.embedding_fallback_to_hashing:
        logger.bind(requested=provider).warning(
            "Unknown embedding provider '%s'; MEMORY_EMBEDDING_FALLBACK is on, "
            "degrading to the hashing embedder. Retrieval is lexical-grade, NOT "
            "semantic -- fix MEMORY_VECTOR_PROVIDER to use a real model.",
            provider,
        )
        return HashingEmbeddingProvider(dimension=config.embedding_dim)

    raise EmbeddingError(
        f"Unknown embedding provider '{provider}'.",
        hint=(
            "Set MEMORY_VECTOR_PROVIDER to 'hashing' or 'ollama', or set "
            "MEMORY_EMBEDDING_FALLBACK=true to accept the hashing embedder."
        ),
        context={"requested": provider},
    )
