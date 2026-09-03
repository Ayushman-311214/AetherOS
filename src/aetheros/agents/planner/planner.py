"""
Agent planner.

One responsibility: ``GOAL -> the next action``. The planner sends an assembled
context to the model and turns what comes back into a :class:`PlanResult`. It
does not run tools, touch a desktop backend, or change the registry -- it decides
what should happen next and says so as data.

The split exists because deciding and doing fail differently. A planner that
also executed would make "the model asked for the wrong tool" and "the mouse
driver crashed" the same kind of event, and only the first of those is something
the model can fix. Keeping the decision separate means the loop can validate,
retry, log or refuse a step before anything moves.

Two entry points, and the difference between them is the whole design:

:meth:`AgentPlanner.plan`
    Async. Calls the provider, and is therefore the only part that can fail for
    reasons outside this process.
:meth:`AgentPlanner.decide`
    Sync, pure, and side-effect free. Given the same response it returns the same
    plan -- no clock, no randomness, no state mutation. This is what "keep the
    planner deterministic around the provider response" means, and it is why the
    interesting cases (malformed calls, unknown tools, bad arguments) can be
    tested without a provider at all.

Validation reuses what already exists rather than restating it:
:func:`~aetheros.llm.tool_calls.parse_llm_response` for the wire shape,
:class:`~aetheros.tools.registry.ToolRegistry` to resolve names -- read-only --
and :class:`~aetheros.tools.validator.ToolValidator` for arguments. The rejection
messages are the validator's own words, because those sentences were written to
be read by the model and rewording them here would only let the two layers
disagree.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ...core.errors.agent_error import AgentError
from ...core.errors.tool_error import ToolError
from ...core.interfaces.llm_provider import LLMProvider
from ...core.logging import get_logger
from ...llm.tool_calls import ToolCall, parse_llm_response
from ...tools.registry import ToolDefinition, ToolRegistry, tool_registry
from ...tools.validator import ToolValidator, tool_validator
from ..context import AgentContext
from ..state import AgentState, ErrorRecord
from .actions import (
    ERROR_INVALID_ARGUMENTS,
    ERROR_MALFORMED_CALL,
    ERROR_PROVIDER,
    ERROR_TERMINAL_STATE,
    ERROR_TOO_MANY_CALLS,
    ERROR_TOOL_DISABLED,
    ERROR_UNKNOWN_TOOL,
    PlannedAction,
    PlanResult,
    RejectedToolCall,
)

# Calls accepted from one provider response. Eight matches the iteration budget
# in ``AgentLoopConfig``: a model that wants more actions than the run has turns
# is not being helped by having all of them accepted.
DEFAULT_MAX_TOOL_CALLS = 8

# Absolute cap, whatever the configuration says. A provider that returns
# hundreds of calls is malfunctioning, and the planner should not turn that into
# hundreds of queued side effects.
TOOL_CALL_CEILING = 32


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    """What the planner is willing to accept from one response.

    All three defaults are the strict reading. Loosening any of them moves a
    check downstream to :class:`~aetheros.tools.executor.ToolExecutor`, which
    performs the same checks before it runs anything -- so the cost of turning
    one off is a worse error message and a wasted iteration, not an unchecked
    tool call.
    """

    # Providers that return several calls per turn are supported. Turning this
    # off keeps the first and rejects the rest, which is the shape to use against
    # an endpoint that mishandles parallel calls.
    allow_parallel_tool_calls: bool = True

    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS

    # Reject names the registry does not know, and tools it has disabled.
    require_known_tools: bool = True

    # Run ToolValidator over the arguments before the call is planned.
    validate_arguments: bool = True

    def __post_init__(self) -> None:
        try:
            limit = int(self.max_tool_calls)
        except (TypeError, ValueError) as exc:
            raise AgentError(
                code="PLANNER_INVALID_LIMIT",
                message=(
                    "max_tool_calls must be an integer, got "
                    f"{self.max_tool_calls!r}."
                ),
                hint="It counts calls accepted from one provider response.",
                cause=exc,
            ) from exc

        # Clamped rather than refused, following the tool layer's
        # ``limit = max(1, limit)``: an out-of-range number is a tuning mistake
        # and the run should continue. A non-number is a programming error.
        object.__setattr__(
            self,
            "max_tool_calls",
            max(1, min(limit, TOOL_CALL_CEILING)),
        )

    @property
    def effective_max_tool_calls(self) -> int:
        """The limit actually applied, once parallelism is accounted for."""

        return self.max_tool_calls if self.allow_parallel_tool_calls else 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_parallel_tool_calls": self.allow_parallel_tool_calls,
            "max_tool_calls": self.max_tool_calls,
            "require_known_tools": self.require_known_tools,
            "validate_arguments": self.validate_arguments,
        }


class AgentPlanner:
    """Decides the next action for one iteration of an agent run.

    Holds the provider and the two read-only collaborators it validates against.
    Nothing here is mutated by planning: the registry is only read, and the state
    is only read -- a planner that changed the run while deciding what the run
    should do next would make the decision impossible to replay.
    """

    __slots__ = ("_config", "_logger", "_provider", "_registry", "_validator")

    def __init__(
        self,
        provider: LLMProvider,
        *,
        registry: ToolRegistry | None = None,
        validator: ToolValidator | None = None,
        config: PlannerConfig | None = None,
    ) -> None:
        self._provider = provider
        self._registry = registry or tool_registry
        self._validator = validator or tool_validator
        self._config = config or PlannerConfig()

        # Built here, not at import time: loguru is a process-wide singleton and
        # every configuration begins by removing existing sinks.
        self._logger = get_logger("agents.planner")

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def config(self) -> PlannerConfig:
        return self._config

    # -- planning ---------------------------------------------------------

    async def plan(
        self,
        state: AgentState,
        context: AgentContext,
        **kwargs: Any,
    ) -> PlanResult:
        """Ask the model what to do next, and describe the answer as an action.

        The only failure this can produce that :meth:`decide` cannot is a
        provider failure, and that is returned as a ``fail`` action rather than
        raised. The caller is an orchestrator deciding whether to retry, fall back
        to another provider, or stop; an exception through five layers gives it
        less to work with than an action carrying the cause. Note that this
        differs from :class:`~aetheros.llm.agent_loop.LLMToolLoop`, which lets
        provider errors propagate -- the loop has no action vocabulary to put them
        in.

        ``kwargs`` are forwarded to the provider untouched, for per-call
        generation settings.
        """

        blocked = self._blocked(state, context)
        if blocked is not None:
            return blocked

        messages = context.messages()
        tools = context.tool_schemas()

        try:
            if tools:
                response: Any = await self._provider.tool_call(
                    messages,
                    tools,
                    **kwargs,
                )
            else:
                # OpenAI-compatible endpoints reject an empty ``tools`` array,
                # which is why LLMEngine.tool_call falls back the same way.
                response = await self._provider.generate(messages, **kwargs)
        except asyncio.CancelledError:
            # Cancellation is not a provider failure; the run is being torn down
            # and swallowing it would hide that from the task that asked.
            raise
        except Exception as exc:
            return self._provider_failure(exc, context)

        return self.decide(context, response)

    def decide(self, context: AgentContext, response: Any) -> PlanResult:
        """Turn a provider response into a plan. Pure and deterministic.

        ``response`` is untrusted: anything the provider returned, including a
        bare string, a dict with no choices, or a tool call whose arguments are
        not JSON. :func:`parse_llm_response` absorbs all of that and never
        raises, so the decision below is a small table rather than a guard maze.

        The table:

        =============================== ===================
        response                        action
        =============================== ===================
        no calls, some content          ``final_response``
        no calls, no content            ``continue``
        calls, at least one accepted    ``tool_call`` (one per accepted call)
        calls, all rejected             ``continue``
        =============================== ===================

        An all-rejected response is ``continue`` rather than ``fail`` because the
        model asked for work and can be told what was wrong with the request. Only
        something the model cannot fix is a failure.
        """

        parsed = parse_llm_response(response)
        content = parsed.content

        if not parsed.has_calls:
            if content.strip():
                action = PlannedAction.final_response(content)
            else:
                action = PlannedAction.continue_(
                    "The provider returned neither content nor a tool call."
                )
            return self._log(
                self._result((action,), context, content=content)
            )

        accepted, rejections = self._review(parsed.tool_calls, parsed.malformed)
        requested = len(parsed.tool_calls) + len(parsed.malformed)

        if not accepted:
            accepted = [
                PlannedAction.continue_(
                    "Every requested tool call was rejected before execution "
                    f"({requested} in total); the model has to correct them."
                )
            ]

        return self._log(
            self._result(
                tuple(accepted),
                context,
                content=content,
                rejections=tuple(rejections),
                requested_calls=requested,
            )
        )

    # -- validation -------------------------------------------------------

    def _review(
        self,
        calls: tuple[ToolCall, ...],
        malformed: tuple[Any, ...],
    ) -> tuple[list[PlannedAction], list[RejectedToolCall]]:
        """Sort requested calls into ones worth attempting and ones to answer.

        Malformed calls are reported first so the rejections come back in the
        order a reader would expect: what the parser refused, then what the
        registry and validator refused.
        """

        rejections: list[RejectedToolCall] = [
            RejectedToolCall(
                tool_name=call.name,
                reason=call.reason,
                error_type=ERROR_MALFORMED_CALL,
                call_id=call.id,
                raw_arguments=call.raw,
            )
            for call in malformed
        ]

        accepted: list[PlannedAction] = []
        limit = self._config.effective_max_tool_calls

        for call in calls:
            if len(accepted) >= limit:
                rejections.append(
                    self._reject(
                        call,
                        reason=(
                            f"Only {limit} tool call(s) can be planned per "
                            "iteration. Ask for this one on the next turn."
                        ),
                        error_type=ERROR_TOO_MANY_CALLS,
                    )
                )
                continue

            rejected = self._inspect(call)
            if rejected is not None:
                rejections.append(rejected)
                continue

            accepted.append(
                PlannedAction.tool_call(
                    call.name,
                    call.arguments,
                    call_id=call.id,
                    raw_arguments=call.raw_arguments,
                )
            )

        return accepted, rejections

    def _inspect(self, call: ToolCall) -> RejectedToolCall | None:
        """Check one call against the registry and the validator.

        Read-only throughout: :meth:`ToolRegistry.exists` before
        :meth:`ToolRegistry.get`, because ``get`` raises ``KeyError`` on an
        unknown name and an invented tool name is the single most common thing a
        model gets wrong -- it should come back as a sentence, not a traceback.
        """

        tool = self._resolve(call.name)

        if tool is None:
            if not self._config.require_known_tools:
                # Name checking is off and the registry has never heard of this
                # tool. There is nothing left to validate against, so the call
                # goes downstream for the executor to refuse.
                return None
            return self._reject(
                call,
                reason=(
                    f"Unknown tool '{call.name}'. "
                    f"Available tools: {self._available() or 'none'}."
                ),
                error_type=ERROR_UNKNOWN_TOOL,
            )

        if self._config.require_known_tools and not tool.enabled:
            return self._reject(
                call,
                reason=f"Tool '{call.name}' is disabled.",
                error_type=ERROR_TOOL_DISABLED,
            )

        if self._config.validate_arguments:
            try:
                self._validator.validate(tool, call.arguments)
            except ToolError as exc:
                # The validator's own wording: names and type names, never
                # argument values, which is what makes it safe to log.
                return self._reject(
                    call,
                    reason=exc.message,
                    error_type=ERROR_INVALID_ARGUMENTS,
                )

        return None

    def _resolve(self, name: str) -> ToolDefinition | None:
        return self._registry.get(name) if self._registry.exists(name) else None

    def _available(self) -> str:
        """Enabled tool names, sorted, for a message the model has to read."""

        return ", ".join(sorted(tool.name for tool in self._registry.enabled_tools()))

    @staticmethod
    def _reject(
        call: ToolCall,
        *,
        reason: str,
        error_type: str,
    ) -> RejectedToolCall:
        return RejectedToolCall(
            tool_name=call.name,
            reason=reason,
            error_type=error_type,
            call_id=call.id,
            argument_names=tuple(sorted(call.arguments)),
            raw_arguments=call.raw_arguments,
        )

    # -- refusals ---------------------------------------------------------

    def _blocked(
        self,
        state: AgentState,
        context: AgentContext,
    ) -> PlanResult | None:
        """Refuse to plan when there is nothing a next action could mean.

        Only one condition qualifies: the run has already ended. A spent
        iteration budget deliberately does not, because
        :meth:`AgentState.next_iteration` refuses to advance past the budget --
        so on the last allowed turn ``has_iterations_left`` is already ``False``
        while that turn is exactly the one that needs planning. Guarding on it
        would refuse the final iteration of every run.

        Whether a tool call is worth planning on the final turn is the loop's
        judgement, and the model is already told which turn it is on through
        :class:`~aetheros.agents.context.IterationInfo`.
        """

        if not state.is_terminal:
            return None

        return self._log(
            self._result(
                (
                    PlannedAction.fail(
                        f"The run already finished ({state.status.value}); "
                        "there is no next action to plan.",
                        error_type=ERROR_TERMINAL_STATE,
                    ),
                ),
                context,
            )
        )

    def _provider_failure(
        self,
        exc: Exception,
        context: AgentContext,
    ) -> PlanResult:
        """Describe a provider failure as a ``fail`` action.

        The cause is kept as an :class:`~aetheros.agents.state.ErrorRecord`
        rather than a bare string so the caller has every field
        :meth:`AgentState.record_error` asks for -- message, type, iteration and
        recoverability -- without re-deriving them from an exception it never
        saw. It is marked recoverable: a provider that timed out once may answer
        on the next attempt, and whether to make one is the orchestrator's call.
        """

        error = ErrorRecord.from_exception(
            exc,
            iteration=context.iteration,
            recoverable=True,
        )

        return self._log(
            self._result(
                (
                    PlannedAction.fail(
                        f"{self._provider.name} failed to answer: {exc}",
                        error_type=ERROR_PROVIDER,
                    ),
                ),
                context,
                error=error,
            )
        )

    # -- assembly ---------------------------------------------------------

    def _result(
        self,
        actions: tuple[PlannedAction, ...],
        context: AgentContext,
        *,
        content: str = "",
        rejections: tuple[RejectedToolCall, ...] = (),
        requested_calls: int = 0,
        error: ErrorRecord | None = None,
    ) -> PlanResult:
        """Attach provenance. Every plan carries the model that produced it,
        because CLAUDE.md 8 requires a prediction to name its model version."""

        return PlanResult(
            actions=actions,
            content=content,
            rejections=rejections,
            iteration=context.iteration,
            provider=self._provider.name,
            model=self._provider.model,
            requested_calls=requested_calls,
            error=error,
        )

    def _log(self, result: PlanResult) -> PlanResult:
        """One line per decision, log-safe, returning the result unchanged.

        :meth:`PlanResult.describe` is the projection that withholds argument
        values and the model's prose; the file sinks keep what they are given for
        weeks, and a tool like ``type_text`` receives literal keystrokes.
        """

        self._logger.bind(**result.describe()).debug(
            "Planned {action} for iteration {iteration}",
            action=result.type.value,
            iteration=result.iteration,
        )
        return result


__all__ = [
    "DEFAULT_MAX_TOOL_CALLS",
    "TOOL_CALL_CEILING",
    "AgentPlanner",
    "PlannerConfig",
]
