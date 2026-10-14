"""
Fixtures for the LLM layer tests.

The scripted ``FakeLLMProvider`` and the response builders (``tool_calls``,
``answer``, ``make_provider``) live in the root ``tests/conftest.py``, because
the voice reasoner tests need the same doubles. Only the loop assembly is
specific to this package.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from aetheros.llm.agent_loop import AgentLoopConfig, LLMToolLoop
from aetheros.llm.engine import LLMEngine
from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


@pytest.fixture
def make_loop(
    registry: ToolRegistry,
    make_provider: type,
) -> Callable[..., tuple[Any, LLMToolLoop]]:
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
    ) -> tuple[Any, LLMToolLoop]:

        provider = make_provider(
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
