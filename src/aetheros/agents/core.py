"""
The agent core loop: the driver that turns a goal into a finished run.

This is the first place the previously built pieces meet. One
:class:`~aetheros.agents.state.AgentState` records the run; a
:class:`~aetheros.agents.context.ContextBuilder` projects it into the payload one
iteration sends the model; an :class:`~aetheros.agents.planner.AgentPlanner`
turns the model's answer into a typed
:class:`~aetheros.agents.planner.PlannedAction`; a
:class:`~aetheros.agents.policy.PolicyEngine` (attached to the coordinator, and
consulted here for its emergency stop) decides whether a call may run; and a
:class:`~aetheros.agents.execution.ToolExecutionCoordinator` carries an allowed
call to the existing :class:`~aetheros.tools.executor.ToolExecutor`. Each tool
result is folded back in as an
:class:`~aetheros.agents.observation.Observation`.

The cycle, per iteration, is

    OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD -> OBSERVE

and it repeats until one of five things ends it: a final response, a failure, the
iteration ceiling, cancellation, or the emergency stop.

The core never touches a tool itself. It never calls ``ToolExecutor`` directly,
never resolves a tool outside the registry, and never runs a call the policy did
not allow -- every side effect goes through the coordinator, the single seam
where policy is enforced and the executor is invoked. What the core owns is the
*sequence*: which step runs next, and when the run is over.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..core.interfaces.llm_provider import LLMProvider
from ..core.logging import get_logger
from ..core.observability import (
    TraceEventType,
    TraceStatus,
    emit_trace,
    safe_preview,
)
from ..llm.tool_calls import ToolCall
from ..tools.executor import ToolExecutor
from ..tools.registry import ToolRegistry
from .context import ContextBuilder, ContextConfig
from .execution import ExecutionBatch, ToolExecutionCoordinator
from .observation import ObservationLog, tool_observation
from .planner import AgentPlanner, PlannedAction, PlannerConfig
from .policy import POLICY_EMERGENCY_STOP, PolicyEngine
from .state import (
    STOP_CANCELLED,
    STOP_MAX_ITERATIONS,
    AgentState,
    AgentStatus,
    Message,
)

#: Stop reason for a run halted by the policy emergency stop. Distinct from the
#: per-call refusal the coordinator raises: this is the loop ending the whole
#: run, not one call being turned away at the gate.
STOP_EMERGENCY_STOP = "emergency_stop"


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """The outcome of one :meth:`AgentCore.run`.

    Pairs the terminal :class:`AgentState` -- the authoritative, serializable
    record of everything that happened -- with the :class:`ObservationLog` the
    loop accumulated. The convenience properties read straight off the state, so
    a caller that only wants the answer need not learn the state's shape.
    """

    state: AgentState
    observations: ObservationLog

    @property
    def ok(self) -> bool:
        return self.state.status is AgentStatus.COMPLETED

    @property
    def status(self) -> AgentStatus:
        return self.state.status

    @property
    def final_response(self) -> str | None:
        return self.state.final_response

    @property
    def stopped_reason(self) -> str | None:
        return self.state.stopped_reason

    @property
    def iterations(self) -> int:
        return self.state.iteration


def _planned_to_call(action: PlannedAction) -> ToolCall:
    """Turn a planned tool call into the :class:`ToolCall` an assistant message
    needs to replay it.

    The coordinator accepts a :class:`PlannedAction` directly, so this exists
    only for the assistant turn recorded before execution: the wire format the
    provider expects is built from ``ToolCall`` objects. Inlined rather than
    imported from ``llm.agent_loop`` to avoid depending on that module's private
    helper -- the two must stay in step, and a copy that is read here is easier
    to keep honest than an import that looks incidental.
    """

    return ToolCall(
        id=action.call_id or "",
        name=action.tool_name or "",
        arguments=dict(action.arguments),
        raw_arguments=action.raw_arguments,
    )


class AgentCore:
    """Drives one goal to a terminal state, one iteration at a time.

    Holds no mutable run state of its own: everything a run accumulates lives on
    the :class:`AgentState` passed through :meth:`run`, so one core can drive
    many runs, sequentially or concurrently. It is a *coordinator of
    collaborators* -- planner, context builder, execution coordinator -- and its
    single responsibility is ordering their turns and recognising when the run
    is done.
    """

    __slots__ = (
        "_planner",
        "_coordinator",
        "_context_builder",
        "_policy",
        "_system_prompt",
        "_logger",
    )

    def __init__(
        self,
        planner: AgentPlanner,
        coordinator: ToolExecutionCoordinator,
        *,
        context_builder: ContextBuilder | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._planner = planner
        self._coordinator = coordinator
        self._context_builder = context_builder or ContextBuilder()
        # The one policy for the run is the coordinator's -- the same gate that
        # refuses a call per-call is the one whose emergency stop ends the loop.
        # Reading it here rather than taking a second engine keeps a single
        # source of truth: there is no way for the loop and the coordinator to
        # disagree about whether the stop is engaged.
        self._policy: PolicyEngine | None = coordinator.policy
        self._system_prompt = system_prompt
        self._logger = get_logger("agents.core")

    @classmethod
    def from_provider(
        cls,
        provider: LLMProvider,
        *,
        registry: ToolRegistry | None = None,
        executor: ToolExecutor | None = None,
        policy: PolicyEngine | None = None,
        planner_config: PlannerConfig | None = None,
        context_config: ContextConfig | None = None,
        system_prompt: str | None = None,
    ) -> AgentCore:
        """Assemble a core from a provider and, optionally, its collaborators.

        The convenience path for the common case: give it a provider and it
        wires a planner, an execution coordinator and a context builder over one
        registry, so the planner validates against, the executor runs from, and
        the context advertises, the *same* set of tools. Passing ``registry``
        (and, for tests, ``executor``) keeps an isolated run off the process-wide
        singletons.
        """

        planner = AgentPlanner(provider, registry=registry, config=planner_config)
        coordinator = ToolExecutionCoordinator(
            executor, registry=registry, policy=policy
        )
        # Pass registry through only when the caller set one: ContextBuilder,
        # the coordinator and the planner each default to the process-wide
        # registry, and handing them an explicit ``None`` would override that
        # default rather than fall back to it.
        if registry is not None:
            builder = ContextBuilder(context_config, registry=registry)
        else:
            builder = ContextBuilder(context_config)
        return cls(
            planner,
            coordinator,
            context_builder=builder,
            system_prompt=system_prompt,
        )

    @property
    def policy(self) -> PolicyEngine | None:
        return self._policy

    # -- run --------------------------------------------------------------

    async def run(
        self,
        goal: str,
        *,
        max_iterations: int | None = None,
        system_prompt: str | None = None,
        confirmed: bool = False,
        state: AgentState | None = None,
    ) -> AgentRunResult:
        """Run one goal to a terminal state and report the outcome.

        Creates and seeds a state when none is supplied; an already-started
        state is picked up as-is, so a caller can pre-seed or resume one. The
        loop is wrapped so cancellation -- an ``asyncio.CancelledError`` raised
        into any awaited step -- marks the state cancelled and then re-raises:
        the task that cancelled still sees the ``CancelledError``, but the run's
        own record shows *why* it stopped.
        """

        if state is None:
            state = (
                AgentState(goal, max_iterations=max_iterations)
                if max_iterations is not None
                else AgentState(goal)
            )

        observations = ObservationLog()

        if state.status is AgentStatus.PENDING:
            await state.start()
            await state.seed_conversation(system_prompt or self._system_prompt)

        log = self._logger.bind(
            state_id=state.state_id, goal_chars=len(state.goal)
        )
        log.info("Agent core run started.")

        # INPUT_RECEIVED + AGENT_STARTED mark the agent boundary of the pipeline:
        # the goal is the user's request as the agent received it (safe to
        # preview -- it is the user's own words, not a secret), and state_id is
        # the run_id every downstream event correlates on (PHASE 13).
        await emit_trace(
            TraceEventType.INPUT_RECEIVED,
            message=safe_preview(state.goal, 120),
            run_id=state.state_id,
            payload={"goal_preview": safe_preview(state.goal)},
        )
        await emit_trace(
            TraceEventType.AGENT_STARTED,
            message="Agent run started",
            status=TraceStatus.STARTED,
            run_id=state.state_id,
        )

        try:
            await self._loop(state, observations, confirmed=confirmed)
        except asyncio.CancelledError:
            # Cancellation is not failure: record it, then let it propagate so
            # the awaiting task still unwinds. ``cancel()`` takes an uncontended
            # lock and completes without suspending, so it is not itself cut
            # short by the same cancellation.
            if not state.is_terminal:
                await state.cancel(STOP_CANCELLED)
            log.info("Agent core run cancelled.")
            raise

        log.bind(
            status=state.status.value,
            stopped_reason=state.stopped_reason,
            iterations=state.iteration,
        ).info("Agent core run finished.")

        return AgentRunResult(state, observations)

    # -- the loop ---------------------------------------------------------

    async def _loop(
        self,
        state: AgentState,
        observations: ObservationLog,
        *,
        confirmed: bool,
    ) -> None:
        """The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle.

        Mirrors the shape of :class:`~aetheros.llm.agent_loop.LLMToolLoop`, with
        the two additions the safety layer requires: the emergency stop is
        checked at the top of every iteration -- a latched stop ends the run
        rather than being discovered one refused call at a time -- and each tool
        result is folded back in as an observation before the next context is
        built.
        """

        while state.has_iterations_left and not state.is_terminal:
            # Emergency stop -- a run-ending condition, checked before any work.
            if self._policy is not None and self._policy.is_emergency_stopped:
                await state.fail(
                    "Emergency stop engaged; the run was halted.",
                    error_type=POLICY_EMERGENCY_STOP,
                    stopped_reason=STOP_EMERGENCY_STOP,
                )
                return

            iteration = await state.next_iteration()
            log = self._logger.bind(state_id=state.state_id, iteration=iteration)
            log.debug("Agent iteration started.")

            await emit_trace(
                TraceEventType.AGENT_ITERATION_STARTED,
                message=f"Iteration {iteration} started",
                status=TraceStatus.STARTED,
                run_id=state.state_id,
                iteration=iteration,
            )

            # CONTEXT -- a bounded, deterministic projection of the state.
            context = self._context_builder.build(state)

            # PLAN -- the model's answer, described as a typed action. The
            # planner emits the LLM and PLANNER_DECISION events itself.
            plan = await self._planner.plan(state, context)

            # A provider failure is recorded even when the plan still carries a
            # usable action; a fail action is paired with it.
            if plan.error is not None:
                await state.record_error(
                    plan.error.message,
                    error_type=plan.error.error_type,
                    iteration=iteration,
                    recoverable=plan.error.recoverable,
                )

            if plan.is_failure:
                log.bind(
                    action="fail", error_type=plan.action.error_type
                ).warning("Agent selected a failing action.")
                await emit_trace(
                    TraceEventType.ERROR,
                    message=safe_preview(plan.action.reason, 120),
                    stage="Agent decision",
                    status=TraceStatus.FAILED,
                    run_id=state.state_id,
                    iteration=iteration,
                    error=plan.action.error_type,
                )
                await state.fail(
                    plan.action.reason,
                    error_type=plan.action.error_type,
                )
                return

            if plan.is_final:
                log.bind(action="final").info("Agent selected a final response.")
                await state.add_message(Message.assistant(plan.action.content))
                await state.complete(plan.action.content)
                await emit_trace(
                    TraceEventType.FINAL_RESPONSE_CREATED,
                    message=safe_preview(plan.action.content, 120),
                    status=TraceStatus.SUCCESS,
                    run_id=state.state_id,
                    iteration=iteration,
                    payload={"response_preview": safe_preview(plan.action.content)},
                )
                return

            if plan.tool_calls:
                # Names only -- an argument value may be a secret (a password
                # typed, clipboard text set), so it must never reach a log sink.
                names = [a.tool_name for a in plan.tool_calls]
                log.bind(action="tool_call", tools=names).info(
                    "Agent selected tool calls."
                )
                # TOOL_SELECTED -- one per planned call, argument NAMES only.
                # The coordinator emits the validation/execution/result events;
                # this marks the agent's choice of which tool to run.
                for action in plan.tool_calls:
                    await emit_trace(
                        TraceEventType.TOOL_SELECTED,
                        message=action.tool_name or "",
                        status=TraceStatus.INFO,
                        run_id=state.state_id,
                        iteration=iteration,
                        metadata={
                            "tool_name": action.tool_name,
                            "argument_names": list(action.argument_names),
                        },
                    )
                calls = tuple(_planned_to_call(a) for a in plan.tool_calls)
                await state.add_message(
                    Message.assistant(plan.content, tool_calls=calls)
                )
                # POLICY + EXECUTE -- the coordinator gates each call and, when
                # allowed, delegates to the existing ToolExecutor. RECORD is the
                # coordinator's own doing: it writes each call and each result
                # into the state before returning them.
                results = await self._coordinator.execute_many(
                    state,
                    plan.tool_calls,
                    iteration=iteration,
                    confirmed=confirmed,
                )
                log.bind(
                    tools=[r.tool_name for r in results],
                    delegated=[r.tool_name for r in results if r.delegated],
                ).info("Tool execution finished.")
                await state.extend_messages(
                    [
                        Message.tool(tool_call_id=r.call_id, content=r.content)
                        for r in results
                    ]
                )
                # OBSERVE -- fold each recorded result in for the next turn.
                await self._observe(state, observations, results, iteration)
            elif plan.action.is_continue:
                log.bind(action="continue").debug("Agent chose to continue.")
                await state.record_observation(
                    plan.action.reason, source="planner", iteration=iteration
                )

            await emit_trace(
                TraceEventType.AGENT_ITERATION_COMPLETED,
                message=f"Iteration {iteration} completed",
                status=TraceStatus.SUCCESS,
                run_id=state.state_id,
                iteration=iteration,
            )

        # Fell through without a terminal outcome: the iteration budget is
        # spent. That is a completion, not a failure -- the same way the LLM
        # tool loop ends an over-long run.
        if not state.is_terminal:
            await state.complete(
                self._limit_message(state.max_iterations),
                stopped_reason=STOP_MAX_ITERATIONS,
            )
            await emit_trace(
                TraceEventType.FINAL_RESPONSE_CREATED,
                message=self._limit_message(state.max_iterations),
                status=TraceStatus.SUCCESS,
                run_id=state.state_id,
                iteration=state.iteration,
                metadata={"stopped_reason": STOP_MAX_ITERATIONS},
            )

    # -- OBSERVE ----------------------------------------------------------

    async def _observe(
        self,
        state: AgentState,
        observations: ObservationLog,
        results: ExecutionBatch,
        iteration: int,
    ) -> None:
        """Record one :class:`Observation` per delegated tool result.

        A refused call (``delegated=False``) is skipped: nothing reached a tool,
        so nothing was observed. Its refusal is still in the transcript as a tool
        message -- the coordinator recorded it -- but there is no tool output to
        fold in, and inventing an observation for a call that never ran would put
        a phantom result in front of the next turn.

        For a delegated call the observation is built from the *recorded*
        ``ToolResultRecord`` -- pulled from the state via
        :meth:`AgentState.results_for` -- rather than the execution result,
        because ``tool_observation`` accepts the transcript record and because
        reading back what was persisted keeps the observation faithful to the
        run's own history.
        """

        for result in results:
            if result.refused:
                continue
            records = state.results_for(result.call_id)
            if not records:
                continue
            observation = tool_observation(records[-1])
            observations.record(observation)
            projected = observation.to_state_observation(iteration=iteration)
            await state.record_observation(
                projected.text,
                source=projected.source,
                iteration=projected.iteration,
                metadata=projected.metadata,
            )
            await emit_trace(
                TraceEventType.OBSERVATION_CREATED,
                message=safe_preview(projected.text, 120),
                status=TraceStatus.SUCCESS,
                run_id=state.state_id,
                iteration=iteration,
                metadata={"tool_name": result.tool_name, "source": projected.source},
                payload={"observation_preview": safe_preview(projected.text)},
            )

    @staticmethod
    def _limit_message(max_iterations: int) -> str:
        return (
            "The run reached its iteration budget of "
            f"{max_iterations} before producing a final answer."
        )


__all__ = ["AgentCore", "AgentRunResult", "STOP_EMERGENCY_STOP"]





