"""
Agent context assembly.

One :class:`AgentContext` is everything the model needs for *one* iteration of a
run, read out of an :class:`~aetheros.agents.state.AgentState` and shaped into
the payload the existing provider layer already accepts.

The split matters. ``AgentState`` is the record of what happened; the context is
a *projection* of that record, bounded and reproducible. A run that has made
forty tool calls still gets a prompt of predictable size, and the same state
always produces the same prompt.

Three properties are deliberate.

*Deterministic.* :meth:`ContextBuilder.build` is synchronous, performs no I/O and
reads no clock. Tool schemas are sorted by name -- ``ToolRegistry.enabled_tools``
hands back insertion order, which is stable within a process but differs between
two processes that registered the same tools in a different order, and a prompt
that shuffles between runs is a prompt that cannot be cached or diffed.

*Bounded by construction.* Every list that could grow with the length of a run
has a configured limit and a hard ceiling above it, so a misconfiguration cannot
turn into a 200k-token request. Tool result bodies are re-truncated on the way
out even though ``LLMToolLoop`` already truncates on the way in, because the
context cannot assume it was the loop that recorded them.

*Compatible.* History is emitted through ``Message.to_wire()``, the same shapes
``LLMToolLoop`` builds by hand, and it is trimmed adjacency-aware: a ``tool``
message whose assistant turn fell outside the window is dropped rather than sent,
because a provider rejects a tool message whose ``tool_call_id`` is absent from
the preceding assistant turn.

Nothing here calls a provider, plans, or executes a tool. The context is data.

Secret hygiene
--------------
The assembled *prompt* may hold tool argument values -- it is the conversation,
and the model needs them. The digest blocks this module writes into the system
message deliberately carry argument *names* only: the values are already in the
history for the model to read, so repeating them buys nothing and would make
:attr:`AgentContext.system_instructions` unsafe to log. :meth:`AgentContext.describe`
is the redacted view for the sinks, matching ``AgentState.describe``.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from ..core.errors.agent_error import AgentError
from ..core.logging import get_logger
from ..llm.agent_loop import DEFAULT_SYSTEM_PROMPT
from ..llm.tool_schema import get_llm_tools
from ..tools.registry import ToolRegistry, tool_registry
from ..tools.schema import ToolSchemaGenerator, schema_generator
from .state import (
    AgentState,
    Message,
    Observation,
    ToolCallRecord,
    ToolResultRecord,
)


# Hard ceilings. The configured limits below are the tuning dials; these are the
# guard rails, so a caller that passes max_history_messages=100_000 gets a large
# prompt rather than an unbounded one. ITERATION_CEILING in state.py exists for
# the same reason and is set the same way: high enough never to bite a real run.
HISTORY_CEILING = 200
RECORD_CEILING = 50
CHARS_CEILING = 32_000

# Same marker LLMToolLoop._truncate writes, so the model meets one convention
# for "you did not see all of this" no matter which layer shortened the text.
TRUNCATION_TEMPLATE = "{kept}…[truncated {dropped} chars]"


def truncate(text: str, limit: int) -> str:
    """Shorten ``text`` to ``limit`` characters, saying so explicitly."""

    if limit <= 0 or len(text) <= limit:
        return text

    return TRUNCATION_TEMPLATE.format(
        kept=text[:limit],
        dropped=len(text) - limit,
    )


def _clamp(value: Any, *, name: str, low: int, high: int) -> int:
    """Coerce a configured limit into range, or refuse it.

    Clamping rather than raising on an out-of-range number follows the existing
    convention (``limit = max(1, limit)`` in the tool layer): a limit that is too
    large is a tuning mistake and the run should continue. A limit that is not a
    number at all is a programming error and silently coercing it would produce
    a prompt nobody asked for.
    """

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AgentError(
            code="CONTEXT_INVALID_LIMIT",
            message=f"{name} must be an integer, got {value!r}.",
            hint="Limits are message/record counts and character budgets.",
            cause=exc,
        ) from exc

    return max(low, min(number, high))


@dataclass(frozen=True, slots=True)
class ContextConfig:
    """The limits that keep one iteration's prompt a predictable size.

    Defaults are chosen to match what the rest of the stack already assumes:
    ``system_prompt`` and ``tool_result_max_chars`` are taken from
    ``AgentLoopConfig`` rather than restated, so the two layers cannot drift into
    describing AetherOS differently or disagreeing on how much of a tool result
    the model is allowed to see.
    """

    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    # Conversation turns replayed, counted from the most recent. The goal is
    # restated in the system block, so trimming past it loses context but never
    # loses the task.
    max_history_messages: int = 40

    # Structured digests folded into the system block. These survive history
    # trimming, which is their whole purpose: on a long run the oldest tool
    # results are gone from the transcript but still summarized here.
    max_tool_calls: int = 8
    max_tool_results: int = 8
    max_observations: int = 10

    # Applied to `tool` message bodies on the way out. LLMToolLoop truncates
    # before recording; the context cannot assume the loop was the recorder.
    tool_result_max_chars: int = 4000

    # Per-line budgets for the digest blocks, which are summaries -- the full
    # bodies live in the history.
    tool_result_preview_chars: int = 200
    observation_max_chars: int = 500
    goal_max_chars: int = 1000

    include_tool_schemas: bool = True
    include_observations: bool = True
    include_tool_digest: bool = True

    def __post_init__(self) -> None:
        for name, low, high in (
            ("max_history_messages", 0, HISTORY_CEILING),
            ("max_tool_calls", 0, RECORD_CEILING),
            ("max_tool_results", 0, RECORD_CEILING),
            ("max_observations", 0, RECORD_CEILING),
            ("tool_result_max_chars", 0, CHARS_CEILING),
            ("tool_result_preview_chars", 0, CHARS_CEILING),
            ("observation_max_chars", 0, CHARS_CEILING),
            ("goal_max_chars", 0, CHARS_CEILING),
        ):
            object.__setattr__(
                self,
                name,
                _clamp(getattr(self, name), name=name, low=low, high=high),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_history_messages": self.max_history_messages,
            "max_tool_calls": self.max_tool_calls,
            "max_tool_results": self.max_tool_results,
            "max_observations": self.max_observations,
            "tool_result_max_chars": self.tool_result_max_chars,
            "tool_result_preview_chars": self.tool_result_preview_chars,
            "observation_max_chars": self.observation_max_chars,
            "goal_max_chars": self.goal_max_chars,
            "include_tool_schemas": self.include_tool_schemas,
            "include_observations": self.include_observations,
            "include_tool_digest": self.include_tool_digest,
        }


@dataclass(frozen=True, slots=True)
class IterationInfo:
    """Where the run is in its budget.

    Carried explicitly because the model behaves differently on its last turn
    than on its first: with no iterations left there is no point asking for
    another tool call, and the system block says so.
    """

    iteration: int
    max_iterations: int

    @property
    def remaining(self) -> int:
        return max(0, self.max_iterations - self.iteration)

    @property
    def is_first(self) -> bool:
        return self.iteration <= 1

    @property
    def is_final(self) -> bool:
        return self.remaining == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "remaining": self.remaining,
            "is_first": self.is_first,
            "is_final": self.is_final,
        }

    def describe(self) -> str:
        text = (
            f"Iteration {self.iteration} of {self.max_iterations} "
            f"({self.remaining} remaining)."
        )
        if self.is_final:
            text += (
                " This is the last iteration: answer with what you already have "
                "rather than calling another tool."
            )
        return text


@dataclass(frozen=True, slots=True)
class AgentContext:
    """One iteration's worth of assembled context.

    Frozen: a snapshot that can be edited after assembly is not a snapshot, and
    the whole point of building it as a value is that the request actually sent
    can be logged, diffed and replayed. The accessors hand back copies for the
    same reason.

    The eight things a caller can ask for map onto the fields directly:
    :attr:`system_instructions`, :attr:`history`, :attr:`goal`,
    :attr:`recent_tool_calls`, :attr:`recent_tool_results`,
    :attr:`observations`, :attr:`tools` and :attr:`iteration_info`.
    """

    state_id: str
    agent: str
    goal: str
    system_instructions: str
    iteration_info: IterationInfo

    history: tuple[dict[str, Any], ...] = ()
    recent_tool_calls: tuple[ToolCallRecord, ...] = ()
    recent_tool_results: tuple[ToolResultRecord, ...] = ()
    observations: tuple[Observation, ...] = ()
    tools: tuple[dict[str, Any], ...] = ()

    # Why the emitted history is shorter than the transcript. Kept as counts so
    # a caller can tell "the model saw everything" from "the model saw a window",
    # which changes how much its answer can be trusted.
    dropped_messages: int = 0
    dropped_orphans: int = 0
    superseded_system_messages: int = 0

    config: ContextConfig = field(default_factory=ContextConfig)

    # -- iteration --------------------------------------------------------

    @property
    def iteration(self) -> int:
        return self.iteration_info.iteration

    @property
    def max_iterations(self) -> int:
        return self.iteration_info.max_iterations

    @property
    def iterations_remaining(self) -> int:
        return self.iteration_info.remaining

    @property
    def is_final_iteration(self) -> bool:
        return self.iteration_info.is_final

    # -- shape ------------------------------------------------------------

    @property
    def has_tools(self) -> bool:
        return bool(self.tools)

    @property
    def is_trimmed(self) -> bool:
        return bool(self.dropped_messages or self.dropped_orphans)

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(_schema_name(schema) for schema in self.tools)

    # -- provider payload -------------------------------------------------

    def messages(self) -> list[dict[str, Any]]:
        """The request payload, in the order the provider expects.

        Exactly one system message, at index 0: that is what the existing
        OpenAI-compatible provider is sent today, and it is also the only shape
        that survives translation to providers which take the system prompt as a
        separate parameter. System turns found in the transcript are not replayed
        for the same reason -- see :attr:`superseded_system_messages`.
        """

        return [
            {"role": "system", "content": self.system_instructions},
            *(deepcopy(message) for message in self.history),
        ]

    def tool_schemas(self) -> list[dict[str, Any]]:
        """Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts."""

        return [deepcopy(schema) for schema in self.tools]

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Faithful, and therefore not safe for the log sinks.

        Holds the goal, the transcript and tool arguments. Treat it like the
        conversation; :meth:`describe` is the projection for logging.
        """

        return {
            "state_id": self.state_id,
            "agent": self.agent,
            "goal": self.goal,
            "system_instructions": self.system_instructions,
            "iteration": self.iteration_info.to_dict(),
            "history": [deepcopy(m) for m in self.history],
            "recent_tool_calls": [c.to_dict() for c in self.recent_tool_calls],
            "recent_tool_results": [r.to_dict() for r in self.recent_tool_results],
            "observations": [o.to_dict() for o in self.observations],
            "tools": [deepcopy(s) for s in self.tools],
            "dropped_messages": self.dropped_messages,
            "dropped_orphans": self.dropped_orphans,
            "superseded_system_messages": self.superseded_system_messages,
            "config": self.config.to_dict(),
        }

    def describe(self) -> dict[str, Any]:
        """Counts and tool names only -- the view the sinks may keep."""

        return {
            "state_id": self.state_id,
            "agent": self.agent,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "is_final_iteration": self.is_final_iteration,
            "history_messages": len(self.history),
            "system_chars": len(self.system_instructions),
            "tool_calls": len(self.recent_tool_calls),
            "tool_results": len(self.recent_tool_results),
            "observations": len(self.observations),
            "tools": len(self.tools),
            "tool_names": list(self.tool_names),
            "dropped_messages": self.dropped_messages,
            "dropped_orphans": self.dropped_orphans,
            "superseded_system_messages": self.superseded_system_messages,
        }

    def __repr__(self) -> str:
        # No goal text and no instructions: reprs land in tracebacks, and
        # tracebacks land in the log files.
        return (
            f"AgentContext(state_id={self.state_id!r}, agent={self.agent!r}, "
            f"iteration={self.iteration}/{self.max_iterations}, "
            f"history={len(self.history)}, tools={len(self.tools)})"
        )


def _schema_name(schema: dict[str, Any]) -> str:
    """The tool name inside a generated schema, or ``""`` if it is malformed.

    Tolerant on purpose: this is a sort key, and one hand-built schema missing
    its ``function`` block should not take down context assembly for every other
    tool in the registry.
    """

    function = schema.get("function")
    if isinstance(function, dict):
        return str(function.get("name") or "")
    return ""


class ContextBuilder:
    """Turns an :class:`AgentState` into an :class:`AgentContext`.

    Collaborators are injected, and both default to the process-wide singletons
    the rest of the stack already uses. That is the whole reason this class holds
    them at all: a second registry would mean tools the executor can run but the
    model was never offered, and a second schema generator would mean two
    definitions of the same tool's parameters.
    """

    __slots__ = ("_config", "_registry", "_generator", "_logger")

    def __init__(
        self,
        config: ContextConfig | None = None,
        *,
        registry: ToolRegistry = tool_registry,
        generator: ToolSchemaGenerator = schema_generator,
    ) -> None:

        self._config = config or ContextConfig()
        self._registry = registry
        self._generator = generator

        # In __init__, never at import time: get_logger() touches the loguru
        # singleton, and a module-level call would configure it before the
        # application had a say.
        self._logger = get_logger("agent_context")

    @property
    def config(self) -> ContextConfig:
        return self._config

    def with_config(self, config: ContextConfig) -> ContextBuilder:
        """A builder over the same collaborators with different limits."""

        return ContextBuilder(
            config,
            registry=self._registry,
            generator=self._generator,
        )

    # ==========================================================
    # Assembly
    # ==========================================================

    def build(self, state: AgentState) -> AgentContext:
        """Assemble the context for ``state``'s current iteration.

        Synchronous and side-effect free. It reads only the state's synchronous
        accessors, which already hand back immutable snapshots, so it neither
        needs the state's lock nor blocks a concurrent mutation -- and two calls
        against an unchanged state return equal contexts.
        """

        config = self._config

        goal = truncate(state.goal, config.goal_max_chars)

        iteration_info = IterationInfo(
            iteration=state.iteration,
            max_iterations=state.max_iterations,
        )

        calls = _tail(state.tool_calls, config.max_tool_calls)
        results = _tail(state.tool_results, config.max_tool_results)
        observations = (
            _tail(state.observations, config.max_observations)
            if config.include_observations
            else ()
        )

        history, dropped, orphans, superseded = self._history(state)
        tools = self._tools()

        context = AgentContext(
            state_id=state.state_id,
            agent=state.agent,
            goal=goal,
            system_instructions=self._system_instructions(
                goal=goal,
                iteration_info=iteration_info,
                calls=calls,
                results=results,
                observations=observations,
            ),
            iteration_info=iteration_info,
            history=history,
            recent_tool_calls=calls,
            recent_tool_results=results,
            observations=observations,
            tools=tools,
            dropped_messages=dropped,
            dropped_orphans=orphans,
            superseded_system_messages=superseded,
            config=config,
        )

        self._logger.bind(**context.describe()).debug("Agent context assembled")

        return context

    def messages_for(self, state: AgentState) -> list[dict[str, Any]]:
        """Shorthand for ``build(state).messages()``."""

        return self.build(state).messages()

    # ==========================================================
    # History
    # ==========================================================

    def _history(
        self,
        state: AgentState,
    ) -> tuple[tuple[dict[str, Any], ...], int, int, int]:
        """The replayable transcript window, plus what it cost to bound it.

        Two rules beyond "keep the newest N".

        System turns are not replayed. The context owns exactly one system
        message, built from the configured prompt; replaying the one
        ``AgentState.seed_conversation`` may have recorded would send two, and a
        second system turn in the middle of a conversation is either ignored or
        rejected depending on the provider.

        Trimming is adjacency-aware. Taking a plain suffix can cut an assistant
        turn while keeping the ``tool`` messages that answer it, and a provider
        rejects a tool message whose ``tool_call_id`` never appeared -- the whole
        request fails, not just that turn. Orphans are dropped and counted.
        """

        limit = self._config.max_history_messages

        replayable = [m for m in state.messages if m.role != "system"]
        superseded = len(state.messages) - len(replayable)

        dropped = 0
        if len(replayable) > limit:
            dropped = len(replayable) - limit
            # Not `[-limit:]`: with limit == 0 that slice is the whole list.
            replayable = replayable[dropped:]

        live_call_ids: set[str] = set()
        kept: list[Message] = []
        orphans = 0

        for message in replayable:
            if message.role == "assistant" and message.tool_calls:
                live_call_ids.update(
                    str(call.get("id"))
                    for call in message.tool_calls
                    if isinstance(call, dict) and call.get("id")
                )

            if message.role == "tool" and message.tool_call_id not in live_call_ids:
                orphans += 1
                continue

            kept.append(message)

        return tuple(self._bound(m) for m in kept), dropped, orphans, superseded

    def _bound(self, message: Message) -> dict[str, Any]:
        """One wire message, with an oversized tool body shortened.

        ``to_wire`` is reused rather than reimplemented: it is the shape the
        provider layer is already fed, and duplicating it here would be a second
        place to get tool-call replay wrong.
        """

        wire = message.to_wire()

        if message.role == "tool":
            wire["content"] = truncate(
                str(wire.get("content") or ""),
                self._config.tool_result_max_chars,
            )

        return wire

    # ==========================================================
    # Tools
    # ==========================================================

    def _tools(self) -> tuple[dict[str, Any], ...]:
        """Schemas for the enabled tools, in a stable order.

        ``get_llm_tools`` is the existing bridge from the registry to the
        provider format; it already filters to ``enabled_tools()`` and already
        runs every definition through ``ToolSchemaGenerator``. Sorting is the one
        thing added here: ``enabled_tools()`` returns registration order, so two
        processes that imported their tool modules in a different order would
        offer the model the same tools in a different sequence.
        """

        if not self._config.include_tool_schemas:
            return ()

        schemas = get_llm_tools(self._registry, self._generator)

        return tuple(sorted(schemas, key=_schema_name))

    # ==========================================================
    # System block
    # ==========================================================

    def _system_instructions(
        self,
        *,
        goal: str,
        iteration_info: IterationInfo,
        calls: tuple[ToolCallRecord, ...],
        results: tuple[ToolResultRecord, ...],
        observations: tuple[Observation, ...],
    ) -> str:
        """The single system message: instructions, goal, budget, digests.

        Everything that must survive history trimming lives here. The goal in
        particular is restated rather than relied upon: it enters the transcript
        as the first user turn, and on a long run that turn is the first thing a
        suffix window drops.
        """

        blocks: list[str] = [self._config.system_prompt.strip()]

        blocks.append(f"## Current goal\n{goal}")
        blocks.append(f"## Iteration\n{iteration_info.describe()}")

        if observations:
            blocks.append(
                "## Observations\n" + "\n".join(
                    f"- [iteration {o.iteration}] "
                    f"{truncate(o.text, self._config.observation_max_chars)}"
                    for o in observations
                )
            )

        if self._config.include_tool_digest:
            if calls:
                blocks.append(
                    "## Recent tool calls\n" + "\n".join(
                        _describe_call(call) for call in calls
                    )
                )
            if results:
                blocks.append(
                    "## Recent tool results\n" + "\n".join(
                        _describe_result(
                            result,
                            self._config.tool_result_preview_chars,
                        )
                        for result in results
                    )
                )

        return "\n\n".join(block for block in blocks if block)


def _tail(records: tuple[Any, ...], limit: int) -> tuple[Any, ...]:
    """The newest ``limit`` records. ``limit == 0`` means none."""

    if limit <= 0:
        return ()

    return records[-limit:]


def _describe_call(call: ToolCallRecord) -> str:
    """One digest line for a call: names, never values.

    The model already has the arguments verbatim in the assistant turn this
    summarizes, so repeating them here would only make the system block unsafe
    to log -- ``type_text`` and ``set_clipboard`` receive literal keystrokes, and
    the file sinks retain for weeks. Same rule as
    ``ToolExecutor._log_outcome`` and ``AgentState.describe``.
    """

    arguments = ", ".join(call.argument_names)

    return f"- [iteration {call.iteration}] {call.name}({arguments})"


def _describe_result(result: ToolResultRecord, preview_chars: int) -> str:
    """One digest line for a result: outcome, and why if it failed."""

    if result.ok:
        outcome = f"ok, {len(result.content)} chars"
    else:
        reason = truncate(result.error or "no error message", preview_chars)
        outcome = f"failed ({result.error_type or 'ToolError'}): {reason}"

    return f"- [iteration {result.iteration}] {result.name} -> {outcome}"


# A stateless service over the shared registry, matching how `schema_generator`
# and `tool_executor` are exposed. It holds no run data -- that is AgentState's
# job, and AgentState deliberately has no singleton.
context_builder = ContextBuilder()


__all__ = [
    "CHARS_CEILING",
    "HISTORY_CEILING",
    "RECORD_CEILING",
    "AgentContext",
    "ContextBuilder",
    "ContextConfig",
    "IterationInfo",
    "context_builder",
    "truncate",
]
