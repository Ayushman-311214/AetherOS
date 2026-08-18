from __future__ import annotations

from typing import Any

from ..core.interfaces.llm_provider import (
    LLMProvider,
)


class LLMEngine:
    """
    High-level LLM service.

    Responsible for generation and tool-calling orchestration.
    """

    def __init__(
        self,
        provider: LLMProvider,
    ) -> None:

        self._provider = provider

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
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:

        return await self._provider.tool_call(
            messages=messages,
            tools=tools,
            **kwargs,
        )