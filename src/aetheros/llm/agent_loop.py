"""
The LLM ↔ tool execution loop.

One run is a bounded conversation: the model is offered the enabled tool
schemas, its tool calls are validated and executed, the results are appended
back into the conversation, and the model is asked again — until it answers in
prose, repeats itself, or hits the iteration ceiling.

Nothing here raises for a model-level or tool-level problem. A bad tool call is
an observation the model can read and recover from; only a provider failure
propagates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..core.logging import get_logger
from ..tools.executor import ToolExecutionResult, ToolExecutor
from .engine import LLMEngine
from .tool_calls import (
    MalformedToolCall,
    ToolCall,
    parse_llm_response,
)

DEFAULT_SYSTEM_PROMPT = (
    "You are AetherOS, an autonomous computer operator. "
    "Use the provided tools when they are needed to answer "
    "accurately, then give the user a short, direct answer. "
    "Do not repeat a tool call whose result you already have."
)


@dataclass(frozen=True, slots=True)
class AgentLoopConfig:
    """
    Bounds and behaviour for a single loop run.
    """

    # Hard ceiling on provider round-trips.
    max_iterations: int = 8

    # How many times one identical (name, arguments) call may actually execute
    # before the loop refuses to run it again.
    max_repeated_calls: int = 2

    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    # Tool results longer than this are truncated with an explicit marker, so
    # the model knows it did not see everything rather than silently reasoning
    # over a cut-off value. Screenshots and OCR dumps are the realistic cause.
    tool_result_max_chars: int = 4000

    # Off by default and intended to stay off outside local debugging. Tool
    # arguments carry typed text and clipboard contents — `type_text` may hold
    # a password the user was pasting — and the file sinks retain for weeks.
    log_tool_arguments: bool = False


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    """
    Record of one tool the loop attempted during a run.
    """

    iteration: int
    name: str
    ok: bool

    # The serialized, already-truncated string handed to the model. Kept as
    # text rather than the raw return value so a run's history cannot pin a
    # captured frame or an OCR buffer in memory for the life of the result.
    content: str

    error: str | None = None
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class AgentLoopResult:
    """
    Outcome of a full loop run.
    """

    content: str
    iterations: int
    stopped_reason: str
    tool_results: tuple[ToolInvocation, ...] = ()
    messages: tuple[dict[str, Any], ...] = ()

    @property
    def used_tools(self) -> bool:
        return bool(self.tool_results)


class LLMToolLoop:
    """
    Main LLM ↔ ToolExecutor loop.
    """

    def __init__(
        self,
        engine: LLMEngine,
        executor: ToolExecutor,
        *,
        config: AgentLoopConfig | None = None,
    ) -> None:

        self._engine = engine
        self._executor = executor
        self._config = config or AgentLoopConfig()

        self._logger = get_logger("llm_tool_loop")

    @property
    def config(self) -> AgentLoopConfig:
        return self._config

    # ==========================================================
    # Public
    # ==========================================================

    async def run(
        self,
        user_message: str,
        *,
        system_prompt: str | None = None,
        max_iterations: int | None = None,
    ) -> str:
        """
        Run the loop and return the model's final answer text.
        """

        result = await self.run_detailed(
            user_message,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
        )

        return result.content

    async def run_detailed(
        self,
        user_message: str,
        *,
        system_prompt: str | None = None,
        max_iterations: int | None = None,
    ) -> AgentLoopResult:
        """
        Run the loop and return the full record of what happened.
        """

        config = self._config

        limit = (
            max_iterations
            if max_iterations is not None
            else config.max_iterations
        )

        # A non-positive limit would otherwise skip the provider entirely and
        # return an empty answer with no explanation.
        limit = max(1, limit)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt or config.system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        # Resolved once per run, not per iteration: regenerating every schema
        # on each round-trip is pure waste, and a tool set that changed
        # mid-conversation would invalidate tool_call ids already in flight.
        tools = self._engine.available_tools()

        invocations: list[ToolInvocation] = []
        executed_counts: dict[str, int] = {}
        last_signatures: set[str] = set()

        content = ""
        iterations = 0

        self._logger.bind(
            provider=self._engine.provider_name,
            model=self._engine.model,
            tool_count=len(tools),
            max_iterations=limit,
        ).info("Agent loop started.")

        while iterations < limit:

            iterations += 1

            response = await self._engine.tool_call(
                messages=messages,
                tools=tools,
            )

            parsed = parse_llm_response(response)

            if parsed.content:
                content = parsed.content

            # --------------------------------------------------
            # No tool calls at all — this is the final answer
            # --------------------------------------------------

            if not parsed.has_calls:

                self._logger.bind(
                    iterations=iterations,
                    tool_calls=len(invocations),
                ).info("Agent loop finished with a final answer.")

                return AgentLoopResult(
                    content=content,
                    iterations=iterations,
                    stopped_reason="final_answer",
                    tool_results=tuple(invocations),
                    messages=tuple(messages),
                )

            # --------------------------------------------------
            # Replay the assistant turn
            # --------------------------------------------------

            # Only calls that can be addressed by a `role: "tool"` message are
            # replayed. A provider rejects a tool message whose tool_call_id is
            # absent from the preceding assistant message, so an unnamed call
            # must not appear here.
            replayable: list[ToolCall | MalformedToolCall] = [
                *parsed.tool_calls,
                *(
                    call
                    for call in parsed.malformed
                    if call.is_addressable
                ),
            ]

            unaddressable = [
                call
                for call in parsed.malformed
                if not call.is_addressable
            ]

            if replayable:
                messages.append(
                    self._assistant_message(
                        parsed.content,
                        replayable,
                    )
                )

            # --------------------------------------------------
            # Malformed but addressable calls: report, don't run
            # --------------------------------------------------

            for call in parsed.malformed:

                if not call.is_addressable:
                    continue

                messages.append(
                    self._tool_message(
                        call.id or "",
                        self._payload(
                            ok=False,
                            error=call.reason,
                        ),
                    )
                )

                invocations.append(
                    ToolInvocation(
                        iteration=iterations,
                        name=call.name or "<unknown>",
                        ok=False,
                        content=call.reason,
                        error=call.reason,
                    )
                )

                self._logger.bind(
                    iteration=iterations,
                    tool=call.name,
                ).warning("Model produced a malformed tool call.")

            # --------------------------------------------------
            # Execute the well-formed calls
            # --------------------------------------------------

            signatures: set[str] = set()
            executed_any = False

            for call in parsed.tool_calls:

                signature = self._signature(call)
                signatures.add(signature)

                if (
                    executed_counts.get(signature, 0)
                    >= config.max_repeated_calls
                ):
                    # Refuse the repeat instead of running it again. Re-running
                    # is not just wasted work: for a side-effecting tool such as
                    # `click` or `type_text` it would repeat a real action.
                    note = (
                        f"This exact call to '{call.name}' has already been "
                        f"made {executed_counts[signature]} times and the "
                        f"results are above. Do not call it again — answer the "
                        f"user with what you already have."
                    )

                    messages.append(
                        self._tool_message(
                            call.id,
                            self._payload(ok=False, error=note),
                        )
                    )

                    invocations.append(
                        ToolInvocation(
                            iteration=iterations,
                            name=call.name,
                            ok=False,
                            content=note,
                            error=note,
                        )
                    )

                    self._logger.bind(
                        iteration=iterations,
                        tool=call.name,
                    ).warning("Blocked a repeated tool call.")

                    continue

                executed_counts[signature] = (
                    executed_counts.get(signature, 0) + 1
                )

                result = await self._executor.execute_safe(
                    call.name,
                    call.arguments,
                )

                executed_any = True

                serialized = self._serialize_result(result)

                messages.append(
                    self._tool_message(call.id, serialized)
                )

                invocations.append(
                    ToolInvocation(
                        iteration=iterations,
                        name=call.name,
                        ok=result.ok,
                        content=serialized,
                        error=result.error,
                        duration_ms=result.duration_ms,
                    )
                )

                self._log_invocation(iterations, call, result)

            # --------------------------------------------------
            # Nameless calls: correct via a plain user note
            # --------------------------------------------------

            for call in unaddressable:

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "One of your tool calls was rejected because it "
                            f"had no function name ({call.reason}). Re-issue "
                            "it with a valid tool name, or answer directly."
                        ),
                    }
                )

                invocations.append(
                    ToolInvocation(
                        iteration=iterations,
                        name="<unnamed>",
                        ok=False,
                        content=call.reason,
                        error=call.reason,
                    )
                )

            # --------------------------------------------------
            # Loop guard
            # --------------------------------------------------

            # Only *consecutive* repetition counts. Re-reading the screen before
            # and after an action is legitimate; the same call twice in a row
            # with nothing in between is not. An iteration that executed nothing
            # is exempt — it is already being corrected above.
            if (
                executed_any
                and signatures
                and signatures == last_signatures
            ):
                self._logger.bind(
                    iterations=iterations,
                ).warning("Agent loop stopped by the repeat guard.")

                return AgentLoopResult(
                    content=content or self._guard_message(),
                    iterations=iterations,
                    stopped_reason="loop_guard",
                    tool_results=tuple(invocations),
                    messages=tuple(messages),
                )

            last_signatures = signatures if executed_any else set()

        # ------------------------------------------------------
        # Iteration ceiling
        # ------------------------------------------------------

        # Returning beats raising: the tool results gathered so far are useful,
        # and the CLI would otherwise show a traceback for a bounded, expected
        # outcome.
        self._logger.bind(
            iterations=iterations,
            tool_calls=len(invocations),
        ).warning("Agent loop hit the maximum iteration limit.")

        return AgentLoopResult(
            content=content or self._limit_message(limit),
            iterations=iterations,
            stopped_reason="max_iterations",
            tool_results=tuple(invocations),
            messages=tuple(messages),
        )

    # ==========================================================
    # Message construction
    # ==========================================================

    def _assistant_message(
        self,
        content: str,
        calls: list[ToolCall | MalformedToolCall],
    ) -> dict[str, Any]:
        """
        Rebuild the assistant turn that requested these tool calls.
        """

        tool_calls: list[dict[str, Any]] = []

        for call in calls:

            arguments = (
                call.raw_arguments
                if isinstance(call, ToolCall)
                else call.raw
            )

            tool_calls.append(
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": arguments,
                    },
                }
            )

        return {
            "role": "assistant",
            "content": content or None,
            "tool_calls": tool_calls,
        }

    def _tool_message(
        self,
        tool_call_id: str,
        content: str,
    ) -> dict[str, Any]:

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }

    # ==========================================================
    # Result serialization
    # ==========================================================

    def _serialize_result(
        self,
        result: ToolExecutionResult,
    ) -> str:
        """
        Turn an execution outcome into text the model can read.
        """

        if result.ok:
            return self._payload(ok=True, value=result.value)

        return self._payload(
            ok=False,
            error=result.error or f"Tool '{result.name}' failed.",
            error_type=result.error_type,
        )

    def _payload(
        self,
        *,
        ok: bool,
        value: Any = None,
        error: str | None = None,
        error_type: str | None = None,
    ) -> str:
        """
        JSON payload for one tool message, truncated if oversized.
        """

        body: dict[str, Any] = {"ok": ok}

        if ok:
            body["result"] = value
        else:
            body["error"] = error

            if error_type:
                body["error_type"] = error_type

        try:
            # default=str keeps non-serializable returns (Path, numpy scalars,
            # dataclasses) usable instead of losing the whole result.
            text = json.dumps(body, default=str)

        except (TypeError, ValueError) as exc:
            # default=str does not cover every failure — a dict with tuple keys
            # or a self-referential structure still raises, and a tool result
            # must never be able to break the conversation.
            text = json.dumps(
                {
                    "ok": ok,
                    "error": (
                        "Tool result could not be serialized: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

        # Truncation happens after serializing, so the limit applies to what the
        # model actually receives.
        return self._truncate(text)

    def _truncate(
        self,
        text: str,
    ) -> str:

        limit = self._config.tool_result_max_chars

        if limit <= 0 or len(text) <= limit:
            return text

        dropped = len(text) - limit

        return f"{text[:limit]}…[truncated {dropped} chars]"

    # ==========================================================
    # Loop bookkeeping
    # ==========================================================

    def _signature(
        self,
        call: ToolCall,
    ) -> str:
        """
        Identity of a call for repeat detection.
        """

        try:
            arguments = json.dumps(
                call.arguments,
                sort_keys=True,
                default=str,
            )

        except (TypeError, ValueError):
            arguments = call.raw_arguments

        return f"{call.name}:{arguments}"

    def _guard_message(self) -> str:

        return (
            "Stopped: the model kept requesting the same tool call without "
            "producing an answer. The tool results collected so far are "
            "available in this run's history."
        )

    def _limit_message(
        self,
        limit: int,
    ) -> str:

        return (
            f"Stopped after {limit} iterations without a final answer. The "
            "tool results collected so far are available in this run's history."
        )

    # ==========================================================
    # Logging
    # ==========================================================

    def _log_invocation(
        self,
        iteration: int,
        call: ToolCall,
        result: ToolExecutionResult,
    ) -> None:
        """
        Record that a tool ran, without recording what it was given.

        Argument *values* are omitted by default for the reason documented on
        AgentLoopConfig.log_tool_arguments: they can contain typed text or
        clipboard contents, and the log sinks are long-lived.
        """

        bound = self._logger.bind(
            iteration=iteration,
            tool=call.name,
            ok=result.ok,
            duration_ms=round(result.duration_ms, 2),
            argument_names=sorted(call.arguments),
        )

        if self._config.log_tool_arguments:
            bound = bound.bind(arguments=call.arguments)

        if result.ok:
            bound.info("Tool call completed.")
        else:
            bound.bind(
                error_type=result.error_type,
            ).warning("Tool call failed; reporting back to the model.")
