from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Every provider (OpenAI, Ollama, OpenRouter, Groq, etc.)
    must implement this interface.
    """

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name.

        Example:
            OpenAI
            Ollama
            OpenRouter
        """
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """
        Current model name.
        """
        ...

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize provider resources.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Release provider resources.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Returns True if provider is healthy.
        """
        ...

    # ==========================================================
    # Generation
    # ==========================================================

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """
        Generate a complete response.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream tokens incrementally.
        """
        ...

    # ==========================================================
    # Tool Calling
    # ==========================================================

    @abstractmethod
    async def tool_call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute a tool-calling request.

        Returns:
            Provider-specific tool call response.
        """
        ...

    # ==========================================================
    # Model Management
    # ==========================================================

    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        Return all available models.
        """
        ...

    @abstractmethod
    async def set_model(self, model: str) -> None:
        """
        Change the active model.
        """
        ...