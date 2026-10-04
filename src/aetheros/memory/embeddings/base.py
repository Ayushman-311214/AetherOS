"""
Embedding provider abstraction (spec Phase 5).

The vector layer must not be hard-wired to one embedding backend, so every
embedder implements :class:`EmbeddingProvider`. The default shipped
implementation is the dependency-free, deterministic
:class:`~aetheros.memory.embeddings.hashing.HashingEmbeddingProvider`; real
providers (Ollama, an OpenAI-compatible embeddings endpoint, a local
sentence-transformer) slot in behind this same interface later without touching
the vector index or the retriever (CLAUDE.md §10 -- depend on the interface).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    """Turns text into a fixed-dimension, L2-normalised vector."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier recorded alongside each stored vector."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of every vector this provider emits."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> np.ndarray:
        """Embed one string. Returns a float32 array of length ``dimension``."""
        ...

    async def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        """
        Embed several strings.

        Default implementation calls :meth:`embed` per item; a batching provider
        (a network embeddings API) overrides this to amortise the round trip.
        """
        return [await self.embed(t) for t in texts]

    @staticmethod
    def normalize(vector: np.ndarray) -> np.ndarray:
        """L2-normalise so cosine similarity reduces to a dot product."""
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)
