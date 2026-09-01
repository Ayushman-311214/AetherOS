from __future__ import annotations

from typing import Any

from ..core.logging.logging import get_logger
from ..llm.agent_loop import IterationLimitExceeded, LLMToolLoop
from ..llm.engine import LLMEngine
from ..tools.executor import ToolExecutor, tool_executor
from .config import VoiceConfig


class LLMLoopReasoner:
    """
    Adapts the existing LLMToolLoop to the voice pipeline.

    This is deliberately thin. Reasoning, model selection and tool
    dispatch all stay where they already live: the loop talks to
    LLMEngine, which talks to the configured LLMProvider, and tools
    come from the existing ToolRegistry via ToolExecutor. Voice adds
    nothing but a spoken-style system prompt and progress hooks.
    """

    def __init__(
        self,
        *,
        config: VoiceConfig,
        engine: LLMEngine,
        executor: ToolExecutor | None = None,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.reasoner")

        self._loop = LLMToolLoop(
            engine,
            executor or tool_executor,
        )

    # ==========================================================
    # Construction
    # ==========================================================

    @classmethod
    def from_container(
        cls,
        config: VoiceConfig,
        container: Any,
    ) -> LLMLoopReasoner:
        """
        Build a reasoner from whatever LLM provider is registered.

        Raises:
            KeyError: no LLM provider has been registered.
        """

        provider = container.resolve("llm_provider")

        return cls(
            config=config,
            engine=LLMEngine(provider),
        )

    # ==========================================================
    # Reasoning
    # ==========================================================

    async def respond(
        self,
        text: str,
        *,
        on_tool_start: Any = None,
        on_tool_finished: Any = None,
    ) -> str:
        """
        Produce a spoken reply to `text`.
        """

        try:
            response = await self._loop.run(
                text,
                system_prompt=self._config.system_prompt,
                max_iterations=self._config.max_iterations,
                on_tool_start=on_tool_start,
                on_tool_finished=on_tool_finished,
            )

        except IterationLimitExceeded as exc:

            self._logger.warning(
                f"Reasoning hit the iteration limit after "
                f"{self._config.max_iterations} steps."
            )

            # Say whatever the model last managed rather than nothing.
            return exc.partial or (
                "I ran out of steps before finishing that."
            )

        return response.strip()


class EchoReasoner:
    """
    Returns a canned reply, optionally reporting a tool call.

    The test double for reasoning: it lets the pipeline, the event
    flow and the HUD state machine be exercised with no model, no
    network and no API key.
    """

    def __init__(
        self,
        *,
        reply: str = "Acknowledged.",
        tools: list[str] | None = None,
        fail: Exception | None = None,
    ) -> None:

        self._reply = reply
        self._tools = tools or []
        self._fail = fail

        self.prompts: list[str] = []

    async def respond(
        self,
        text: str,
        *,
        on_tool_start: Any = None,
        on_tool_finished: Any = None,
    ) -> str:

        self.prompts.append(text)

        if self._fail is not None:
            raise self._fail

        for name in self._tools:

            if on_tool_start is not None:
                await on_tool_start(name, {})

            if on_tool_finished is not None:
                await on_tool_finished(name, True, None)

        return self._reply


__all__ = [
    "EchoReasoner",
    "LLMLoopReasoner",
]
