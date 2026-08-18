from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from ...core.interfaces.llm_provider import (
    LLMProvider,
)
from ..config import LLMConfig


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider implementation for OpenAI-compatible APIs.

    The same implementation can be configured with
    different base URLs and models.
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        provider_name: str = "openai-compatible",
    ) -> None:

        self._config = config
        self._provider_name = provider_name

        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

        self._model = config.model
        self._initialized = False

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

        await self._client.close()

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True

        except Exception:
            return False

    # ==========================================================
    # Generation
    # ==========================================================

    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:

        response = (
            await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                **kwargs,
            )
        )

        return (
            response.choices[0].message.content
            or ""
        )

    # ==========================================================
    # Streaming
    # ==========================================================

    async def stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:

        stream = (
            await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                **kwargs,
            )
        )

        async for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta.content:
                yield delta.content

    # ==========================================================
    # Tool Calling
    # ==========================================================

    async def tool_call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:

        response = (
            await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                **kwargs,
            )
        )

        message = response.choices[0].message

        tool_calls: list[dict[str, Any]] = []

        for call in message.tool_calls or []:

            raw_arguments = (
                call.function.arguments
                or "{}"
            )

            try:
                arguments = json.loads(
                    raw_arguments
                )
            except json.JSONDecodeError:
                arguments = {}

            tool_calls.append(
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": arguments,
                }
            )

        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
        }

    # ==========================================================
    # Model Management
    # ==========================================================

    async def list_models(self) -> list[str]:

        response = (
            await self._client.models.list()
        )

        return sorted(
            model.id
            for model in response.data
        )

    async def set_model(
        self,
        model: str,
    ) -> None:

        if not model.strip():
            raise ValueError(
                "Model name cannot be empty."
            )

        self._model = model