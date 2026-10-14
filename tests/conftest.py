"""
Shared pytest configuration and fixtures for the AetherOS test suite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from loguru import logger

from aetheros.core.interfaces.llm_provider import LLMProvider
from aetheros.tools.registry import ToolDefinition, ToolRegistry

# tests/cli/test_cli.py imports `src.aetheros.cli.tool_commands`, which builds a
# second copy of the whole package under a different module path. That copy gets
# its own tool_registry, its own DI container and its own loguru configuration —
# and because every logging config starts with logger.remove(), importing it
# tears down the sinks the rest of the session is using. Excluded until that
# test is switched to the `aetheros.` import path.
collect_ignore = [
    "cli/test_cli.py",
]


@pytest.fixture(scope="session", autouse=True)
def _silence_logging():
    """
    Detach every loguru sink for the duration of the test session.

    loguru is a process-wide singleton and AetherOS configures rotating file
    sinks under src/logs. Left attached, the suite writes real log files and, on
    Windows, can fail teardown on a still-open file handle.
    """

    logger.remove()

    yield

    logger.remove()


# ==============================================================
# Tool fixtures
# ==============================================================


def _make_tool_definition(
    function: Callable[..., Any],
    *,
    name: str | None = None,
    description: str | None = None,
    category: str = "test",
    enabled: bool = True,
    timeout_seconds: float | None = None,
) -> ToolDefinition:
    """
    Build a ToolDefinition directly, bypassing the @tool decorator.

    The decorator registers into the process-wide ``tool_registry``; tests need
    definitions that land in an isolated registry instead.
    """

    return ToolDefinition(
        name=name or function.__name__,
        description=description or (function.__doc__ or "").strip(),
        function=function,
        category=category,
        enabled=enabled,
        timeout_seconds=timeout_seconds,
    )


@pytest.fixture
def registry() -> ToolRegistry:
    """
    A registry isolated from the process-wide singleton.
    """

    return ToolRegistry()


@pytest.fixture
def define() -> Callable[..., ToolDefinition]:
    """
    Factory for ToolDefinition objects (the factory-as-fixture pattern).
    """

    return _make_tool_definition


# ==============================================================
# LLM fixtures
# ==============================================================

# Lives at the root rather than under tests/llm/ because more than one package
# needs it: the agent loop tests drive it directly, and the voice reasoner tests
# need the same scripted provider to exercise a spoken turn without a model.
# tests/ has no __init__.py, so a sibling conftest cannot be imported — sharing
# has to happen through the fixture mechanism.


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


# ==============================================================
# HUD fixtures
# ==============================================================

# The double lives in tests/hud_support.py rather than under tests/hud/ because
# the bootstrap wiring tests need it as well, and tests/ has no __init__.py — a
# module in a sibling directory is only importable once pytest has inserted that
# directory into sys.path, which happens when collection reaches it. The tests
# root is on the path from the moment this conftest loads, so it is the one
# place a plain module can be shared from.


@pytest.fixture
def fake_hud_process() -> type:
    """
    The HUD child-process double, for tests that construct their own.

    Returns the class rather than an instance: a caller may need it configured
    (``can_start=False``) or may need several.
    """

    from hud_support import FakeHUDProcess

    return FakeHUDProcess
