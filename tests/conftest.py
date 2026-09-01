"""
Shared pytest configuration and fixtures for the AetherOS test suite.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from loguru import logger

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
