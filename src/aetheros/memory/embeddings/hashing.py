"""
Deterministic, dependency-free hashing embedder (spec Phase 5 default).

Why a hashing embedder rather than a model: the memory layer must be
offline-safe and reproducible (tests cannot depend on a model download or a
network call, and the same text must always embed to the same vector). This
provider uses the *feature-hashing* trick -- it hashes word unigrams and bigrams
into a fixed number of buckets with a signed hash, giving a bag-of-n-grams
vector that captures lexical overlap and short-phrase structure. It is not a
semantic model; it approximates "these two texts share words/phrases", which is
exactly the floor the retriever's lexical+semantic blend needs. A real semantic
model plugs in behind the same :class:`EmbeddingProvider` interface.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

from .base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbeddingProvider(EmbeddingProvider):
    """Signed feature-hashing embedder over unigrams + bigrams."""

    def __init__(self, dimension: int = 256) -> None:
        if dimension < 16:
            raise ValueError("Embedding dimension must be >= 16.")
        self._dim = int(dimension)

    @property
    def name(self) -> str:
        return f"hashing-{self._dim}"

    @property
    def dimension(self) -> int:
        return self._dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        words = _TOKEN_RE.findall(text.lower())
        if not words:
            return []
        bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
        return words + bigrams

    def _bucket(self, token: str) -> tuple[int, float]:
        """Map a token to (index, signed weight) via a stable hash."""
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % self._dim
        sign = 1.0 if (value >> 63) & 1 else -1.0
        return index, sign

    async def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = self._tokens(text)
        for token in tokens:
            index, sign = self._bucket(token)
            vec[index] += sign
        return self.normalize(vec)
