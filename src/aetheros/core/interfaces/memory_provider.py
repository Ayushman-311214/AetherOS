from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """
    Abstract interface for memory providers.

    Supports:
    - Short-term memory
    - Long-term memory
    - Semantic search
    - Metadata
    """

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize memory provider.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown memory provider.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Returns True if provider is healthy.
        """
        ...

    # ==========================================================
    # Store
    # ==========================================================

    @abstractmethod
    async def add(
        self,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store an item.
        """
        ...

    @abstractmethod
    async def add_many(
        self,
        items: list[dict[str, Any]],
    ) -> None:
        """
        Store multiple items.
        """
        ...

    # ==========================================================
    # Retrieve
    # ==========================================================

    @abstractmethod
    async def get(
        self,
        key: str,
    ) -> Any | None:
        """
        Retrieve an item by key.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Semantic search.
        """
        ...

    @abstractmethod
    async def list_keys(self) -> list[str]:
        """
        List stored keys.
        """
        ...

    # ==========================================================
    # Update
    # ==========================================================

    @abstractmethod
    async def update(
        self,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Update an existing item.
        """
        ...

    # ==========================================================
    # Delete
    # ==========================================================

    @abstractmethod
    async def delete(
        self,
        key: str,
    ) -> None:
        """
        Delete an item.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """
        Remove all stored items.
        """
        ...

    # ==========================================================
    # Metadata
    # ==========================================================

    @abstractmethod
    async def exists(
        self,
        key: str,
    ) -> bool:
        """
        Check if a key exists.
        """
        ...

    @abstractmethod
    async def count(self) -> int:
        """
        Number of stored items.
        """
        ...

    @abstractmethod
    async def info(self) -> dict[str, Any]:
        """
        Provider statistics.
        """
        ...