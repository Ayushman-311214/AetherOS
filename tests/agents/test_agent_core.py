"""
Tests for the agent core loop.

``AgentCore`` is the driver that turns a goal into a finished run by taking the
previously built pieces in turn -- state, context, planner, policy, execution
coordinator, observation log. These tests pin the behaviours the task named: a
plain answer with no tools, one tool call, several across iterations, a tool
that fails, a denied tool, a confirmation-required tool, the iteration ceiling,
cancellation, a malformed model response, and a final answer that arrives after
a tool result -- and close with an end-to-end run of the real ``mouse_position``
tool through the real executor.

The provider is scripted (``conftest``'s ``FakeLLMProvider``): every model turn
is spelled out, so each case is one deterministic path through the loop. The
executor is the *real* one, wrapped only to count how often a tool was actually
invoked -- the honest witness that a denied or unconfirmed call never ran.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aetheros.agents.core import (
    MAX_CONSECUTIVE_FAILURES,
    MAX_REPEATED_CALLS,
    AgentCore,
)
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.agents.state import (
    STOP_CANCELLED,
    STOP_LOOP_GUARD,
    STOP_MAX_ITERATIONS,
    AgentState,
    AgentStatus,
)
from aetheros.core.interfaces.mouse_controller import MouseController
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


# ==============================================================
# Tool doubles
# ==============================================================


def move_mouse(x: int, y: int) -> str:
    """Move the cursor to a screen coordinate."""

    return f"moved to {x},{y}"


def type_text(text: str) -> str:
    """Type literal keystrokes."""

    return f"typed {len(text)} chars"


def boom() -> str:
    """A tool that always fails, to drive the tool-failure path."""

    raise RuntimeError("tool exploded")


# -- doubles for the Phase-4 execution-architecture tests ----------------
#
# These model the shapes the real subsystems return, without the subsystems:
# a browser open, a completion check whose *content* tells the model the goal
# is already met, a grounding call that resolves below the safe band, and a
# click that reports success while the screen never actually changes. Each
# returns a content string (or a JSON-serialisable dict the executor renders),
# because the whole point of the fix is that the observation now carries what
# the tool returned, not a bare "succeeded".


def open_browser(url: str) -> str:
    """Open a browser at a URL (test double)."""

    return f"browser opened at {url}"


def check_playing() -> str:
    """Report what is currently playing (test double).

    The content names the finished goal, so a model that reads the observation
    can recognise the task is already done and stop -- the direct counter to the
    32-iteration trace, where every observation said only "succeeded".
    """

    return "now playing: Churake by Vilen"


def ground_target(target: str) -> dict[str, Any]:
    """Resolve a target below the safe-to-act band (test double).

    Mirrors the grounding engine's not-safe result: it *succeeds* as a tool
    call, but the payload says the match is low-confidence and was not acted on.
    The model must read that and decide, not blindly retry.
    """

    return {
        "target": target,
        "confidence": 0.3,
        "band": "LOW",
        "safe_to_act": False,
        "action": "none",
        "action_reason": (
            "Not clicked: the target was not resolved with high enough "
            "confidence to act on safely."
        ),
    }


def click_element(selector: str) -> str:
    """Click an element, reporting success but changing nothing (test double).

    The tool call is ``ok``; the returned content is identical every time. A
    model that cannot verify a change may keep issuing the same click -- which
    is exactly the unproductive loop the guard must catch.
    """

    return f"click dispatched to {selector}"



# ==============================================================
# Executor witness and helpers
# ==============================================================


class _CountingExecutor(ToolExecutor):
    """The real engine, counting how often it was actually asked to run a tool.

    ``asked`` is the independent witness: a denied or unconfirmed call must
    never reach here, and a subclass of the real executor is the only honest
    way to show it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


@pytest.fixture
def tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    """An isolated registry holding the live tools these tests drive."""

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(type_text, category="desktop"))
    registry.register(define(boom, category="desktop"))
    return registry


@pytest.fixture
def rich_tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    """The doubles above plus the base three, for the execution-architecture tests."""

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(type_text, category="desktop"))
    registry.register(define(boom, category="desktop"))
    registry.register(define(open_browser, category="browser"))
    registry.register(define(check_playing, category="browser"))
    registry.register(define(ground_target, category="vision.grounding"))
    registry.register(define(click_element, category="browser"))
    return registry


def _build(
    provider: Any,
    registry: ToolRegistry,
    *,
    policy: PolicyEngine | None = None,
) -> tuple[AgentCore, _CountingExecutor]:
    """A core and its counting executor over the same registry."""

    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Test system prompt.",
    )
    return core, executor


# ==============================================================
# 1. A plain answer, no tools
# ==============================================================


class TestSimpleAnswer:
    @pytest.mark.asyncio
    async def test_no_tools_returns_the_models_answer(
        self, make_provider: Any, registry: ToolRegistry
    ) -> None:
        # Empty registry: the context advertises no tools, so the planner asks
        # the provider to generate prose and the first answer ends the run.
        provider = make_provider(generate_result="The answer is 42.")
        core, executor = _build(provider, registry)

        result = await core.run("What is the answer?")

        assert result.ok
        assert result.status is AgentStatus.COMPLETED
        assert result.final_response == "The answer is 42."
        assert result.iterations == 1
        assert executor.asked == []
        assert provider.generate_count == 1
        assert provider.tool_call_count == 0
        assert len(result.observations) == 0


# ==============================================================
# 2. One tool call, then a final answer
# ==============================================================


class TestOneToolCall:
    @pytest.mark.asyncio
    async def test_one_call_is_executed_then_answered(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 1, "y": 2})),
                answer("Done moving."),
            ]
        )
        core, executor = _build(provider, tools)

        result = await core.run("Move the mouse.")

        assert result.ok
        assert result.final_response == "Done moving."
        assert executor.asked == ["move_mouse"]
        records = result.state.results_for("call_0")
        assert len(records) == 1
        assert records[0].ok
        # The result was folded back in as exactly one observation.
        assert len(result.observations) == 1


# ==============================================================
# 3. Several tool calls across iterations
# ==============================================================


class TestMultipleSequentialToolCalls:
    @pytest.mark.asyncio
    async def test_calls_across_iterations_run_in_order(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 1, "y": 2})),
                tool_calls(("type_text", {"text": "hello"})),
                answer("All done."),
            ]
        )
        core, executor = _build(provider, tools)

        result = await core.run("Do two things in turn.")

        assert result.ok
        assert result.final_response == "All done."
        assert executor.asked == ["move_mouse", "type_text"]
        assert result.iterations == 3
        assert len(result.observations) == 2


# ==============================================================
# 4. A tool that fails
# ==============================================================


class TestToolFailure:
    @pytest.mark.asyncio
    async def test_a_failing_tool_is_recorded_and_the_run_continues(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("boom", {})),
                answer("Recovered."),
            ]
        )
        core, executor = _build(provider, tools)

        result = await core.run("Try the broken tool.")

        # A tool failure is data the model can read, not the end of the run.
        assert result.ok
        assert result.final_response == "Recovered."
        assert executor.asked == ["boom"]
        records = result.state.results_for("call_0")
        assert len(records) == 1
        assert not records[0].ok
        # The failure was still folded in as an observation.
        assert len(result.observations) == 1


# ==============================================================
# 5. A denied tool
# ==============================================================


class TestDeniedTool:
    @pytest.mark.asyncio
    async def test_a_denied_call_never_reaches_the_executor(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        policy = PolicyEngine(PolicyConfig(denied_tools={"move_mouse"}))
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 1, "y": 2})),
                answer("Carrying on without it."),
            ]
        )
        core, executor = _build(provider, tools, policy=policy)

        result = await core.run("Try a denied tool.")

        assert result.ok
        assert result.final_response == "Carrying on without it."
        # The gate turned it away before delegation: the executor was never asked.
        assert executor.asked == []
        # The refusal is still recorded as a not-ok result the model can read...
        records = result.state.results_for("call_0")
        assert len(records) == 1
        assert not records[0].ok
        # ...but nothing a tool observed is folded in, because nothing ran.
        assert len(result.observations) == 0


# ==============================================================
# 6. A confirmation-required tool
# ==============================================================


class TestConfirmationRequired:
    @pytest.mark.asyncio
    async def test_unconfirmed_call_is_held_and_not_run(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        policy = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 1, "y": 2})),
                answer("Moved on without confirming."),
            ]
        )
        core, executor = _build(provider, tools, policy=policy)

        result = await core.run("Try a confirm-gated tool.")

        assert result.ok
        # Held at the gate: nothing reached the executor.
        assert executor.asked == []
        # The hold is recorded as a not-ok result, not delegated and not observed.
        records = result.state.results_for("call_0")
        assert len(records) == 1
        assert not records[0].ok

    @pytest.mark.asyncio
    async def test_confirmed_call_is_executed(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        policy = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 1, "y": 2})),
                answer("Confirmed and moved."),
            ]
        )
        core, executor = _build(provider, tools, policy=policy)

        result = await core.run("Confirm the move.", confirmed=True)

        assert result.ok
        assert result.final_response == "Confirmed and moved."
        assert executor.asked == ["move_mouse"]


# ==============================================================
# 7. The iteration ceiling
# ==============================================================


class TestMaxIterations:
    @pytest.mark.asyncio
    async def test_the_ceiling_ends_the_run_as_a_completion(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any
    ) -> None:
        # One response that repeats: the model keeps asking for the same tool,
        # so only the iteration budget can stop it.
        provider = make_provider([tool_calls(("move_mouse", {"x": 1, "y": 2}))])
        core, executor = _build(provider, tools)

        result = await core.run("Loop without answering.", max_iterations=2)

        # Running out of budget is a completion, not a failure.
        assert result.status is AgentStatus.COMPLETED
        assert result.stopped_reason == STOP_MAX_ITERATIONS
        assert result.iterations == 2
        assert executor.asked == ["move_mouse", "move_mouse"]


# ==============================================================
# 7b. The configured (run-wide) iteration budget
# ==============================================================


class TestConfiguredBudget:
    """The budget threaded into ``from_provider`` reaches the real loop.

    This is the seam the ``AETHEROS_MAX_TOOL_CALLS`` setting flows through: the
    bootstrapper builds the core with ``max_iterations=<configured>`` and every
    run that does not pass its own budget must use it. Without this wiring the
    setting would be read at startup and then quietly ignored by the loop.
    """

    @pytest.mark.asyncio
    async def test_from_provider_budget_stops_a_run_with_no_per_call_override(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any
    ) -> None:
        # The core is built with a budget of 3 (as the bootstrapper does from
        # config) and run() is NOT given a max_iterations, so the configured
        # value is the only thing that can stop this never-answering model.
        provider = make_provider([tool_calls(("move_mouse", {"x": 1, "y": 2}))])
        executor = _CountingExecutor(tools)
        core = AgentCore.from_provider(
            provider,
            registry=tools,
            executor=executor,
            system_prompt="Test system prompt.",
            max_iterations=3,
        )

        result = await core.run("Loop without answering.")

        assert result.status is AgentStatus.COMPLETED
        assert result.stopped_reason == STOP_MAX_ITERATIONS
        assert result.iterations == 3
        assert executor.asked == ["move_mouse", "move_mouse", "move_mouse"]

    @pytest.mark.asyncio
    async def test_per_call_max_iterations_overrides_the_configured_budget(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any
    ) -> None:
        # A run that names its own budget wins over the core's configured
        # default, so a caller can still bound a single run more tightly.
        provider = make_provider([tool_calls(("move_mouse", {"x": 1, "y": 2}))])
        executor = _CountingExecutor(tools)
        core = AgentCore.from_provider(
            provider,
            registry=tools,
            executor=executor,
            system_prompt="Test system prompt.",
            max_iterations=5,
        )

        result = await core.run("Loop without answering.", max_iterations=2)

        assert result.stopped_reason == STOP_MAX_ITERATIONS
        assert result.iterations == 2


# ==============================================================
# 8. The emergency stop
# ==============================================================


class TestEmergencyStop:
    @pytest.mark.asyncio
    async def test_a_latched_stop_ends_the_run_before_the_next_plan(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        policy.trigger_emergency_stop("halt")
        provider = make_provider([tool_calls(("move_mouse", {"x": 1, "y": 2}))])
        core, executor = _build(provider, tools, policy=policy)

        result = await core.run("Should never get going.")

        assert result.status is AgentStatus.FAILED
        assert result.stopped_reason == "emergency_stop"
        # Halted before the first plan: the provider was never even asked.
        assert provider.tool_call_count == 0
        assert executor.asked == []


# ==============================================================
# 9. Cancellation (asyncio semantics)
# ==============================================================


class TestCancellation:
    @pytest.mark.asyncio
    async def test_cancellation_marks_the_state_and_reraises(
        self, make_provider: Any, tools: ToolRegistry
    ) -> None:
        # A provider whose turn is cancelled: the CancelledError propagates
        # untouched through the planner, and the core records the cancellation
        # before re-raising so the awaiting task still unwinds.
        provider = make_provider()

        async def _cancel(*args: Any, **kwargs: Any) -> Any:
            raise asyncio.CancelledError()

        provider.tool_call = _cancel  # type: ignore[method-assign]
        provider.generate = _cancel  # type: ignore[method-assign]
        core, executor = _build(provider, tools)

        # Own the state so it can be inspected after run() re-raises.
        state = AgentState("Get cancelled mid-run.")

        with pytest.raises(asyncio.CancelledError):
            await core.run("Get cancelled mid-run.", state=state)

        assert state.status is AgentStatus.CANCELLED
        assert state.stopped_reason == STOP_CANCELLED
        assert executor.asked == []


# ==============================================================
# 10. A malformed model response
# ==============================================================


class TestMalformedResponse:
    @pytest.mark.asyncio
    async def test_a_malformed_call_does_not_run_and_the_run_recovers(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        # Arguments that are not valid JSON: the parser marks the call
        # malformed, the planner rejects it, and the loop takes another turn
        # rather than executing anything.
        provider = make_provider(
            [
                tool_calls(("move_mouse", "{ this is not json")),
                answer("Handled the bad call."),
            ]
        )
        core, executor = _build(provider, tools)

        result = await core.run("Send a malformed call.")

        assert result.ok
        assert result.final_response == "Handled the bad call."
        assert executor.asked == []
        assert result.iterations == 2


# ==============================================================
# 11. A final answer after a tool result
# ==============================================================


class TestFinalAfterToolResult:
    @pytest.mark.asyncio
    async def test_the_transcript_orders_call_result_then_answer(
        self, make_provider: Any, tools: ToolRegistry, tool_calls: Any, answer: Any
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 3, "y": 4})),
                answer("The mouse moved as asked."),
            ]
        )
        core, executor = _build(provider, tools)

        result = await core.run("Move, then tell me.")

        assert result.ok
        assert result.final_response == "The mouse moved as asked."
        # seed = system + user; then the tool-calling assistant turn, the tool
        # result, and finally the answering assistant turn -- in that order.
        roles = [m.role for m in result.state.messages]
        assert roles == ["system", "user", "assistant", "tool", "assistant"]
        # The answer arrived only after the tool result was recorded.
        assert result.state.results_for("call_0")[0].ok


# ==============================================================
# 12. End-to-end: the real mouse_position tool through the real executor
# ==============================================================


class _FakeMouse(MouseController):
    """A ``MouseController`` that reports a fixed position and moves nothing.

    ``mouse_position`` is the one read-only mouse tool, so only ``position``
    needs a real answer; the rest are stubbed to satisfy the abstract interface
    without touching a real cursor. The fixed ``(7, 11)`` is the value the E2E
    test looks for in the recorded tool result.
    """

    def position(self) -> tuple[int, int]:
        return (7, 11)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None: ...
    def move_relative(self, dx: int, dy: int, duration: float = 0.0) -> None: ...
    def click(
        self, button: str = "left", clicks: int = 1, interval: float = 0.0
    ) -> None: ...
    def double_click(self, button: str = "left") -> None: ...
    def right_click(self) -> None: ...
    def middle_click(self) -> None: ...
    def drag_to(
        self, x: int, y: int, duration: float = 0.5, button: str = "left"
    ) -> None: ...
    def drag_relative(
        self, dx: int, dy: int, duration: float = 0.5, button: str = "left"
    ) -> None: ...
    def mouse_down(self, button: str = "left") -> None: ...
    def mouse_up(self, button: str = "left") -> None: ...
    def scroll(self, clicks: int) -> None: ...
    def hscroll(self, clicks: int) -> None: ...
    def is_pressed(self, button: str) -> bool:
        return False


class TestEndToEndMousePosition:
    @pytest.mark.asyncio
    async def test_the_real_mouse_position_tool_runs_and_reports_coordinates(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        # The real tool, wired to the real executor. Importing the tools module
        # registers `mouse_position` (and its siblings) into the process-wide
        # `tool_registry`; we copy just that one definition into the isolated
        # registry these tests own, so the run advertises and executes only it.
        from aetheros.core.container import container
        from aetheros.desktop.mouse import tools as mouse_tools  # noqa: F401
        from aetheros.desktop.mouse.controller import MouseService
        from aetheros.tools import tool_registry

        registry.register(tool_registry.get("mouse_position"))

        # The tool resolves `MouseService` from the global container at call
        # time; register a fake mouse so the read-only lookup returns (7, 11)
        # without a real cursor. Removed afterwards so no global state leaks.
        container.register_singleton(
            MouseService, lambda: MouseService(_FakeMouse())
        )
        try:
            provider = make_provider(
                [
                    tool_calls(("mouse_position", {})),
                    answer("The cursor is at 7, 11."),
                ]
            )
            core, executor = _build(provider, registry)

            result = await core.run("Where is the mouse?")

            assert result.ok
            assert result.final_response == "The cursor is at 7, 11."
            assert executor.asked == ["mouse_position"]
            # The real result came back through the real executor and was
            # recorded: it succeeded and its content carries the coordinates.
            records = result.state.results_for("call_0")
            assert len(records) == 1
            assert records[0].ok
            assert "7" in records[0].content
            assert "11" in records[0].content
            assert len(result.observations) == 1
        finally:
            container.remove(MouseService)


# ==============================================================
# 13. Phase-4: the execution-architecture behaviours
# ==============================================================


class TestSimpleBrowserTask:
    """A bounded multi-step task completes and the effort metrics are split.

    The 32-iteration trace conflated "loop passes" with "work done" and could
    not say how much actually happened. Here a two-step browser task answers on
    the third pass, and the metrics report the pieces separately: three model
    round-trips, two tool calls, two steps, no retries and no recovery.
    """

    @pytest.mark.asyncio
    async def test_two_steps_complete_and_metrics_are_recorded(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("open_browser", {"url": "youtube.com"})),
                tool_calls(("type_text", {"text": "Churake Vilen"})),
                answer("Playing Churake by Vilen."),
            ]
        )
        core, executor = _build(provider, rich_tools)

        result = await core.run("Play Churake by Vilen on YouTube.")

        assert result.ok
        assert result.final_response == "Playing Churake by Vilen."
        assert executor.asked == ["open_browser", "type_text"]
        assert result.iterations == 3
        # The counters are separate numbers, not the iteration count reused.
        assert result.metrics["llm_calls"] == 3
        assert result.metrics["tool_calls"] == 2
        assert result.metrics["step_count"] == 2
        assert result.metrics["retries"] == 0
        assert result.metrics["recovery_attempts"] == 0


class TestGroundingBelowSafeBand:
    """A low-confidence grounding result is surfaced with its content.

    The grounding call succeeds as a tool call, but resolves at confidence 0.3
    and is not safe to act on. The fix means the observation now carries that
    payload -- not a bare "ground_target succeeded" -- so the model can read the
    low confidence, decline to act, and answer, instead of clicking a guess.
    """

    @pytest.mark.asyncio
    async def test_not_safe_result_is_observed_and_the_model_can_decline(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("ground_target", {"target": "the Search button"})),
                answer("Could not locate the target with enough confidence."),
            ]
        )
        core, executor = _build(provider, rich_tools)

        result = await core.run("Click the Search button.")

        assert result.ok
        assert executor.asked == ["ground_target"]
        assert result.iterations == 2
        # The observation carries the grounding payload, not just "succeeded":
        # the confidence and the not-safe verdict are what let the model decide.
        latest = result.observations.latest(1)[0]
        assert "0.3" in latest.description
        assert "safe_to_act" in latest.description


class TestConsecutiveFailureCeiling:
    """A run whose every tool round fails is stopped with a reason, not silently.

    The model keeps calling a tool that always fails. Rather than burning the
    whole iteration budget, the loop guard ends the run once
    ``MAX_CONSECUTIVE_FAILURES`` rounds in a row have all failed -- a bounded
    failure path with an honest stop reason and a recorded recovery attempt for
    each retry after the first failure.
    """

    @pytest.mark.asyncio
    async def test_all_failing_rounds_trip_the_loop_guard(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
    ) -> None:
        # One repeating response: boom always raises, and no answer ever comes.
        provider = make_provider([tool_calls(("boom", {}))])
        core, executor = _build(provider, rich_tools)

        # Budget well above the failure ceiling, so the guard -- not the budget
        # -- is what stops the run.
        result = await core.run("Keep hitting the broken tool.", max_iterations=20)

        assert result.status is AgentStatus.COMPLETED
        assert result.stopped_reason == STOP_LOOP_GUARD
        # Stopped at the ceiling, far short of the 20-iteration budget.
        assert result.iterations == MAX_CONSECUTIVE_FAILURES
        assert executor.asked == ["boom"] * MAX_CONSECUTIVE_FAILURES
        # Each act after the first failure is a bounded recovery attempt.
        assert result.metrics["recovery_attempts"] == MAX_CONSECUTIVE_FAILURES - 1
        assert result.stopped_reason != STOP_MAX_ITERATIONS


class TestAlreadyCompletedRecognition:
    """A content-bearing observation lets the model stop the moment it is done.

    The completion check returns content that names the finished goal. Because
    the observation now carries that content, the model recognises the task is
    already met and answers on the next pass -- it does not re-check. This is the
    behaviour whose absence produced the 32-iteration run.
    """

    @pytest.mark.asyncio
    async def test_the_goal_is_recognised_from_the_observation_content(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("check_playing", {})),
                answer("Churake by Vilen is already playing; nothing to do."),
            ]
        )
        core, executor = _build(provider, rich_tools)

        result = await core.run("Make sure Churake by Vilen is playing.")

        assert result.ok
        # Checked once and stopped -- no re-verification loop.
        assert executor.asked == ["check_playing"]
        assert result.iterations == 2
        # The observation carried the concrete state, not a bare "succeeded".
        latest = result.observations.latest(1)[0]
        assert "Churake" in latest.description


class TestToolFailureRecovery:
    """A single failure is a recoverable event, not the end of the run.

    ``boom`` fails once; the model then switches to a different action that
    succeeds, and answers. The consecutive-failure counter resets on the
    success, so the guard never trips, and the recovery -- acting again right
    after an all-failed round -- is counted exactly once.
    """

    @pytest.mark.asyncio
    async def test_a_failure_then_a_different_action_recovers(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        provider = make_provider(
            [
                tool_calls(("boom", {})),
                tool_calls(("move_mouse", {"x": 5, "y": 6})),
                answer("Recovered and moved."),
            ]
        )
        core, executor = _build(provider, rich_tools)

        result = await core.run("Fail once, then recover.")

        assert result.ok
        assert result.final_response == "Recovered and moved."
        assert executor.asked == ["boom", "move_mouse"]
        assert result.iterations == 3
        assert result.stopped_reason != STOP_LOOP_GUARD
        # Exactly one recovery: the move that followed the failing round.
        assert result.metrics["recovery_attempts"] == 1
        assert result.metrics["tool_calls"] == 2


class TestVerificationFailureLoopGuard:
    """An action that reports success but never changes the state is caught.

    ``click_element`` returns ``ok`` with identical content every time, so the
    goal is never actually verified as met. A model that cannot tell the screen
    did not change may keep issuing the same click. The fingerprint guard sees
    the identical outcome recur and stops the run at ``MAX_REPEATED_CALLS`` --
    turning an unbounded verification loop into a bounded, explained stop.
    """

    @pytest.mark.asyncio
    async def test_an_unverifiable_repeat_trips_the_loop_guard(
        self,
        make_provider: Any,
        rich_tools: ToolRegistry,
        tool_calls: Any,
    ) -> None:
        # The model keeps clicking the same element and never answers.
        provider = make_provider(
            [tool_calls(("click_element", {"selector": "#play"}))]
        )
        core, executor = _build(provider, rich_tools)

        result = await core.run("Click play until it plays.", max_iterations=20)

        assert result.status is AgentStatus.COMPLETED
        assert result.stopped_reason == STOP_LOOP_GUARD
        # The identical outcome recurred until the repeat ceiling; the run
        # stopped there rather than at the far larger budget.
        assert result.iterations == MAX_REPEATED_CALLS
        assert executor.asked == ["click_element"] * MAX_REPEATED_CALLS
        # Every pass after the first was a counted retry of the same outcome.
        assert result.metrics["retries"] == MAX_REPEATED_CALLS - 1






