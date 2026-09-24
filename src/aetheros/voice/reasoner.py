from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..agents.state import STOP_FINAL_ANSWER
from ..core.logging.logging import get_logger
from ..llm.agent_loop import LLMToolLoop
from ..llm.engine import LLMEngine
from ..tools.executor import ToolExecutor, tool_executor
from .config import VoiceConfig

if TYPE_CHECKING:
    from ..agents.core import AgentCore


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
        Build a reasoner from whatever LLM layer is registered.

        The already-built LLMEngine is preferred over constructing one from
        the raw provider, because bootstrap registers it with a
        `tool_provider` bound to the live ToolRegistry. A locally built
        `LLMEngine(provider)` has no tool provider, so `available_tools()`
        returns an empty list and the model is offered nothing to call —
        voice would be able to talk but not to act.

        Raises:
            KeyError: neither an LLM engine nor a provider is registered.
        """

        if container.has(LLMEngine):
            return cls(
                config=config,
                engine=container.resolve(LLMEngine),
            )

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

        result = await self._loop.run_detailed(
            text,
            system_prompt=self._config.system_prompt,
            max_iterations=self._config.max_iterations,
            on_tool_start=on_tool_start,
            on_tool_finished=on_tool_finished,
        )

        # run_detailed never raises for a bounded outcome: it returns the
        # partial answer with a stopped_reason. Saying that partial answer is
        # the point — silence is worse than an incomplete reply out loud.
        if result.stopped_reason != "final_answer":

            self._logger.bind(
                stopped_reason=result.stopped_reason,
                iterations=result.iterations,
                tool_calls=len(result.tool_results),
            ).warning(
                "Reasoning stopped without a final answer."
            )

        content = result.content.strip()

        if content:
            return content

        return "I ran out of steps before finishing that."


class AgentReasoner:
    """
    Adapts the AgentCore to the voice pipeline's ``VoiceReasoner`` seam.

    This is the voice counterpart of the CLI's ``ask`` migration: the Agent
    Core is the single orchestration layer. Voice contributes nothing but a
    spoken-style system prompt — it never talks to an LLM provider and never
    dispatches a tool itself. It hands the transcript to :meth:`AgentCore.run`
    and reads the result back, exactly the boundary the task requires.

    The pipeline's HUD still expects per-tool progress hooks. ``AgentCore.run``
    does not surface live per-call callbacks, so once the run has finished its
    recorded ``state.tool_results`` are replayed in order to fire
    ``on_tool_start`` / ``on_tool_finished``. Only tool *names* are replayed:
    the arguments a tool ran with may carry secrets, so ``{}`` is passed rather
    than any value — and the record does not retain arguments anyway.
    """

    def __init__(
        self,
        *,
        config: VoiceConfig,
        agent: AgentCore,
    ) -> None:

        self._config = config
        self._agent = agent
        self._logger = get_logger("voice.reasoner")

    # ==========================================================
    # Construction
    # ==========================================================

    @classmethod
    def from_container(
        cls,
        config: VoiceConfig,
        container: Any,
    ) -> AgentReasoner:
        """
        Build a reasoner over the registered Agent Core.

        Raises:
            KeyError: no agent core is registered.
        """

        return cls(
            config=config,
            agent=container.resolve("agent_core"),
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
        Produce a spoken reply to `text` by running the Agent Core.

        Cancellation raised into the run propagates out unchanged — the
        pipeline's `_guarded`/`cancel()` path owns turning it into a cancelled
        turn, and the Agent Core has already recorded *why* it stopped.
        """

        result = await self._agent.run(
            text,
            system_prompt=self._config.system_prompt,
            max_iterations=self._config.max_iterations,
        )

        # Replay the run's tool history so the HUD's EXECUTING state has a
        # producer, just as the loop reasoner drove it live. The per-tool
        # latency is logged from `duration_ms`, the authoritative source: the
        # replay clock would read ~0, so the recorded duration is the honest
        # number.
        for record in result.state.tool_results:

            if on_tool_start is not None:
                await on_tool_start(record.name, {})

            self._logger.bind(
                tool=record.name,
                ok=record.ok,
                latency_ms=round(record.duration_ms, 3),
            ).info("Tool execution latency.")

            if on_tool_finished is not None:
                await on_tool_finished(record.name, record.ok, record.error)

        # The run never raises for a bounded outcome: it returns a terminal
        # state with a stopped_reason. Saying whatever partial answer it has is
        # the point — silence out loud is worse than an incomplete reply.
        if result.stopped_reason != STOP_FINAL_ANSWER:

            self._logger.bind(
                stopped_reason=result.stopped_reason,
                iterations=result.iterations,
                tool_calls=len(result.state.tool_results),
            ).warning(
                "Reasoning stopped without a final answer."
            )

        content = (result.final_response or "").strip()

        if content:
            return content

        return "I ran out of steps before finishing that."


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
    "AgentReasoner",
    "EchoReasoner",
    "LLMLoopReasoner",
]
