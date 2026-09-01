from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..core.interfaces.llm_provider import (
    LLMProvider,
)


class LLMEngine:
    """
    High-level LLM service.

    Responsible for generation and tool-calling orchestration. The engine owns
    *which* tools the model is offered; it never owns which provider or model
    serves the request — that stays with the injected provider.
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        tool_provider: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:

        self._provider = provider

        # Called per run rather than once at construction, so tools registered
        # after bootstrap are still offered to the model.
        self._tool_provider = tool_provider

    # ==========================================================
    # Provider information
    # ==========================================================

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    # ==========================================================
    # Tool schemas
    # ==========================================================

    def available_tools(self) -> list[dict[str, Any]]:
        """
        Schemas for the tools this engine will offer the model.
        """

        if self._tool_provider is None:
            return []

        return self._tool_provider()

    # ==========================================================
    # Basic generation
    # ==========================================================

    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:

        return await self._provider.generate(
            messages=messages,
            **kwargs,
        )

    # ==========================================================
    # Streaming
    # ==========================================================

    async def stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ):
        async for token in self._provider.stream(
            messages=messages,
            **kwargs,
        ):
            yield token

    # ==========================================================
    # Tool call
    # ==========================================================

    async def tool_call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Ask the model for a response that may contain tool calls.

        ``tools`` defaults to the injected tool provider's schemas.
        """

        resolved = (
            tools
            if tools is not None
            else self.available_tools()
        )

        if not resolved:
            # OpenAI-compatible endpoints reject an empty `tools` array, and
            # LLMProvider.tool_call takes `tools` as required — so with nothing
            # to offer, fall back to plain generation and return the same shape
            # the caller expects. This keeps the provider interface unchanged.
            content = await self._provider.generate(
                messages=messages,
                **kwargs,
            )

            return {
                "content": content,
                "tool_calls": [],
            }

        return await self._provider.tool_call(
            messages=messages,
            tools=resolved,
            **kwargs,
        )
