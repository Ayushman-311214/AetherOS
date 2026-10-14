"""
A tiny time-to-live cache.

Used by the market-data service so repeated quotes/candle pulls within a short
window don't re-hit a provider, while still letting the service reason about
freshness (the entry's age feeds DataQuality). Deliberately minimal and
self-contained -- no external cache dependency for the numerical core.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

V = TypeVar("V")


@dataclass(slots=True)
class _Entry(Generic[V]):
    value: V
    stored_at: float
    ttl: float

    def age(self, now: float) -> float:
        return now - self.stored_at

    def is_fresh(self, now: float) -> bool:
        return self.age(now) < self.ttl


class TTLCache(Generic[V]):
    """A single-process, thread-unsafe TTL cache keyed by string.

    Kept intentionally simple: the trading services are async but run their
    cache access inline, so no locking is required. If concurrent access is
    ever introduced this must be revisited.
    """

    def __init__(self, *, default_ttl: float = 60.0, clock=time.monotonic) -> None:
        if default_ttl <= 0:
            raise ValueError("default_ttl must be positive.")
        self._default_ttl = default_ttl
        self._clock = clock
        self._store: dict[str, _Entry[V]] = {}

    def get(self, key: str) -> V | None:
        """Return a fresh value or None (expired entries are evicted)."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if not entry.is_fresh(self._clock()):
            self._store.pop(key, None)
            return None
        return entry.value

    def get_entry_age(self, key: str) -> float | None:
        """Age in seconds of a live entry, ignoring freshness; None if absent."""
        entry = self._store.get(key)
        if entry is None:
            return None
        return entry.age(self._clock())

    def set(self, key: str, value: V, *, ttl: float | None = None) -> None:
        self._store[key] = _Entry(
            value=value,
            stored_at=self._clock(),
            ttl=ttl if ttl is not None else self._default_ttl,
        )

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
