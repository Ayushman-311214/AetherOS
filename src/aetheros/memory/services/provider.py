"""
MemoryProvider adapter (spec Phase 4 -- reuse the existing interface).

AetherOS already defines a :class:`~aetheros.core.interfaces.memory_provider.MemoryProvider`
key/value + semantic-search port. Rather than invent a parallel abstraction
(Rule 2), this adapter implements that port on top of the rich
:class:`MemoryManager`, so interface-typed consumers get a working provider while
everything else uses the full manager API. The caller's ``key`` is stored in
metadata (``kv_key``) and looked up by an indexed JSON query.
"""

from __future__ import annotations

from typing import Any

from ...core.interfaces.memory_provider import MemoryProvider
from ..config import MemoryConfig
from ..domain.enums import MemoryType, SourceType, Veracity
from .manager import MemoryManager


class SQLiteMemoryProvider(MemoryProvider):
    """Key/value + semantic-search port backed by the MemoryManager."""

    def __init__(
        self,
        config: MemoryConfig,
        *,
        event_bus=None,
        manager: MemoryManager | None = None,
    ) -> None:
        # Accept an existing manager so the bootstrapper can register the ABC
        # port over the *same* manager instance rather than building a second
        # one on its own database connection.
        self._manager = manager or MemoryManager(config, event_bus=event_bus)

    @property
    def manager(self) -> MemoryManager:
        """The underlying rich API (what the trading/agent layers use)."""
        return self._manager

    # --- lifecycle --------------------------------------------------------

    async def initialize(self) -> None:
        await self._manager.initialize()

    async def shutdown(self) -> None:
        await self._manager.shutdown()

    async def health_check(self) -> bool:
        return await self._manager.health_check()

    # --- store ------------------------------------------------------------

    async def add(
        self, key: str, value: Any, metadata: dict[str, Any] | None = None
    ) -> None:
        meta = dict(metadata or {})
        meta["kv_key"] = key
        await self._manager.remember(
            content=str(value),
            memory_type=MemoryType.SEMANTIC,
            veracity=Veracity.OBSERVATION,
            source_type=SourceType.SYSTEM,
            origin="kv",
            data={"kv_key": key, "value": value},
            metadata=meta,
        )

    async def add_many(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            await self.add(
                item["key"], item.get("value"), item.get("metadata")
            )

    # --- retrieve ---------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        rows = await self._manager._repo.find_by_metadata("kv_key", key)
        if not rows:
            return None
        return rows[0].data.get("value", rows[0].content)

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        results = await self._manager.search(query, limit=limit)
        return [r.to_dict() for r in results]

    async def list_keys(self) -> list[str]:
        return await self._manager._repo.list_metadata_values("kv_key")

    # --- update / delete --------------------------------------------------

    async def update(
        self, key: str, value: Any, metadata: dict[str, Any] | None = None
    ) -> None:
        rows = await self._manager._repo.find_by_metadata("kv_key", key)
        if not rows:
            await self.add(key, value, metadata)
            return
        changes: dict[str, Any] = {
            "content": str(value),
            "data": {"value": value, "kv_key": key},
        }
        if metadata:
            changes["metadata"] = metadata
        await self._manager.update(rows[0].id, **changes)

    async def delete(self, key: str) -> None:
        for row in await self._manager._repo.find_by_metadata("kv_key", key):
            await self._manager.forget(row.id, hard=True)

    async def clear(self) -> None:
        await self._manager.clear()

    # --- metadata ---------------------------------------------------------

    async def exists(self, key: str) -> bool:
        rows = await self._manager._repo.find_by_metadata("kv_key", key)
        return bool(rows)

    async def count(self) -> int:
        return await self._manager._repo.count()

    async def info(self) -> dict[str, Any]:
        return await self._manager.stats()
