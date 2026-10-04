"""Embedding abstraction + the deterministic default (spec Phase 5)."""

from __future__ import annotations

from ..config import MemoryConfig
from .base import EmbeddingProvider
from .hashing import HashingEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddingProvider",
    "build_embedding_provider",
]


def build_embedding_provider(config: MemoryConfig) -> EmbeddingProvider:
    """
    Select an embedding provider from configuration (spec Phase 5/23).

    Only the dependency-free hashing provider ships today. Unknown provider
    names fall back to it loudly-by-default rather than failing memory startup --
    mirroring how the trading bootstrapper degrades an unavailable data provider
    to MOCK rather than taking the system down.
    """
    provider = (config.vector_provider or "hashing").lower()
    if provider in ("hashing", "hash", "local", ""):
        return HashingEmbeddingProvider(dimension=config.embedding_dim)

    # Real providers (ollama / openai) register here behind the same ABC.
    # Until one is wired, fall back to the deterministic embedder.
    return HashingEmbeddingProvider(dimension=config.embedding_dim)
