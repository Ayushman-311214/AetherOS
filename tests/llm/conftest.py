"""
Fixtures for the LLM layer tests.

Nothing here touches the network. ``FakeLLMProvider`` implements the full
:class:`LLMProvider` interface and replays a scripted list of responses, so the
whole LLM -> tool -> LLM path runs without an API key.

Helpers are exposed as fixtures rather than module-level functions: ``tests/``
has no ``__init__.py``, so a test module cannot import from a sibling conftest
without relying on pytest's sys.path insertion.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from aetheros.core.interfaces.llm_provider import LLMProvider
from aetheros.llm.agent_loop import AgentLoopConfig, LLMToolLoop
from aetheros.llm.engine import LLMEngine
from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


class FakeLLMProvider(LLMProvider):
    """
    Scripted LLMProvider for tests.

    ``responses`` is consumed one entry per ``tool_call``. Once a single entry
    remains it repeats indefinitely, which is what lets a test drive the loop
    into its iteration ceiling or its repeat guard.
    """

    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        *,
        name: str = "fake",
        model: str = "fake-model",
        generate_result: str = "generated",
    ) -> None:

        self._responses = list(responses or [])
        self._name = name
        self._model = model
        self._generate_result = generate_result

        # Recorded so tests can assert on what actually reached the provider.
        self.tool_call_count = 0
        self.generate_count = 0
        self.received_tools: list[list[dict[str, Any]]] = []
        self.received_messages: list[list[dict[str, Any]]] = []

    # ------------------------------------------------------
    # Provider information
    # ------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    # ------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------
    # Generation
    # ------------------------------------------------------

    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:

        self.generate_count += 1
        self.received_messages.append(list(messages))

        return self._generate_result

    async def stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:

        for token in self._generate_result.split():
            yield token

    # ------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------

    async def tool_call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:

        self.tool_call_count += 1
        self.received_tools.append(tools)

        # Copied: the loop keeps appending to its own list, so a test asserting
        # on an earlier turn must see that turn as it was sent.
        self.received_messages.append(list(messages))

        if not self._responses:
            return {"content": "", "tool_calls": []}

        if len(self._responses) == 1:
            return self._responses[0]

        return self._responses.pop(0)

    # ------------------------------------------------------
    # Model management
    # ------------------------------------------------------

    async def list_models(self) -> list[str]:
        return [self._model]

    async def set_model(self, model: str) -> None:
        self._model = model


# ==============================================================
# Response builders
# ==============================================================


def _tool_calls_response(
    *calls: tuple[str, Any],
    content: str = "",
) -> dict[str, Any]:
    """
    Build a provider response requesting the given ``(name, arguments)`` calls.

    ``arguments`` is passed through untouched so a test can supply a dict, a
    JSON string, or deliberate garbage.
    """

    return {
        "content": content,
        "tool_calls": [
            {
                "id": f"call_{index}",
                "name": name,
                "arguments": arguments,
            }
            for index, (name, arguments) in enumerate(calls)
        ],
    }


def _final_response(content: str) -> dict[str, Any]:
    """
    Build a provider response with no tool calls.
    """

    return {"content": content, "tool_calls": []}


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def make_provider() -> type[FakeLLMProvider]:
    """
    The scripted provider class, for tests that need it directly.
    """

    return FakeLLMProvider


@pytest.fixture
def tool_calls() -> Callable[..., dict[str, Any]]:
    return _tool_calls_response


@pytest.fixture
def answer() -> Callable[[str], dict[str, Any]]:
    return _final_response


@pytest.fixture
def make_loop(
    registry: ToolRegistry,
) -> Callable[..., tuple[FakeLLMProvider, LLMToolLoop]]:
    """
    Build a ``(provider, loop)`` pair driven by a scripted response list.

    Schemas come from the isolated ``registry`` fixture, so whatever the test
    registered is exactly what the model is offered — the real
    ``get_llm_tools`` -> ``ToolSchemaGenerator`` -> ``ToolRegistry`` path, with
    only the provider faked.
    """

    def build(
        responses: list[dict[str, Any]] | None = None,
        *,
        config: AgentLoopConfig | None = None,
        offer_tools: bool = True,
        generate_result: str = "generated",
    ) -> tuple[FakeLLMProvider, LLMToolLoop]:

        provider = FakeLLMProvider(
            responses,
            generate_result=generate_result,
        )

        engine = LLMEngine(
            provider,
            tool_provider=(
                (lambda: get_llm_tools(registry))
                if offer_tools
                else None
            ),
        )

        loop = LLMToolLoop(
            engine,
            ToolExecutor(registry),
            config=config,
        )

        return provider, loop

    return build
