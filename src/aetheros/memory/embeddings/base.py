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

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """
        Embed several strings, preserving input order and cardinality.

        The default implementation calls :meth:`embed` per item; a batching
        provider (a network embeddings API) overrides this to amortise the round
        trip. Implementations MUST return exactly ``len(texts)`` vectors in the
        same order as ``texts`` -- callers key stored vectors on that ordering.
        """
        return [await self.embed(t) for t in texts]

    async def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        """Backward-compatible alias of :meth:`embed_batch`."""
        return await self.embed_batch(texts)

    @staticmethod
    def validate_vector(vector: np.ndarray, *, expected_dim: int) -> np.ndarray:
        """
        Guard a single embedding before it is trusted/stored.

        Rejects wrong-dimension, empty, and non-finite (NaN/inf) vectors -- a
        real provider can return any of these on a partial failure, and a bad
        vector silently poisons cosine search. Returns the vector unchanged on
        success so call sites can wrap inline.
        """
        if vector.ndim != 1 or int(vector.shape[0]) != int(expected_dim):
            raise ValueError(
                f"Embedding has shape {tuple(vector.shape)}, expected "
                f"1-D of length {expected_dim}."
            )
        if vector.shape[0] == 0:
            raise ValueError("Embedding is empty.")
        if not bool(np.all(np.isfinite(vector))):
            raise ValueError("Embedding contains non-finite values (NaN/inf).")
        return vector

    @staticmethod
    def normalize(vector: np.ndarray) -> np.ndarray:
        """L2-normalise so cosine similarity reduces to a dot product."""
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)
