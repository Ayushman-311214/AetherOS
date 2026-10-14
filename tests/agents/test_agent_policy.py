"""
Tests for the agent policy layer.

The policy engine is the gate that sits before ``ToolExecutor``. It is asked
"may this tool run?" and answers ALLOW / DENY / REQUIRE_CONFIRMATION -- and it
runs nothing. So the properties pinned here are the six the task named -- an
allowed action, a denied action, a confirmation-required action, an iteration
limit, an emergency stop, and a policy failure -- plus the two the layer would
be unsafe without: that the precedence order holds (the emergency stop and the
iteration ceiling win over every by-name rule), and that a DENY or a
REQUIRE_CONFIRMATION reaching the coordinator is turned away *before* the
executor is asked.

The engine's statefulness is confined to the emergency stop, so most cases are
pure: one config, one call, one verdict. The coordinator cases use a counting
executor as the independent witness that a refusal never reached a tool.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.agents.execution import ExecutionStatus, ToolExecutionCoordinator
from aetheros.agents.policy import (
    POLICY_ALLOWED,
    POLICY_CONFIRMATION_REQUIRED,
    POLICY_DENIED_TOOL,
    POLICY_EMERGENCY_STOP,
    POLICY_FAILURE,
    POLICY_INVALID_ARGUMENTS,
    POLICY_ITERATION_LIMIT,
    POLICY_NOT_ALLOWED,
    PolicyConfig,
    PolicyDecision,
    PolicyEngine,
)
from aetheros.agents.state import AgentState
from aetheros.config.config_loader import get_settings
from aetheros.llm.tool_calls import ToolCall
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


# ==============================================================
# Tool doubles and helpers
# ==============================================================


def move_mouse(x: int, y: int) -> str:
    """Move the cursor to a screen coordinate."""

    return f"moved to {x},{y}"


def type_text(text: str) -> str:
    """Type literal keystrokes -- a tool whose argument may be a secret."""

    return f"typed {len(text)} chars"


def _call(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    call_id: str = "call_0",
) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


async def _started(goal: str = "Analyze RELIANCE") -> AgentState:
    """A running, seeded state on its first iteration."""

    state = AgentState(goal)
    await state.start()
    await state.seed_conversation("Test system prompt.")
    await state.next_iteration()
    return state


class _CountingExecutor(ToolExecutor):
    """The real engine, counting how often it was actually asked to run a tool.

    ``asked`` is the independent witness a policy test needs: a DENY must never
    reach here, and a subclass of the real executor is the only honest way to
    prove it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    """An isolated registry holding the two live tools these tests drive."""

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(type_text, category="desktop"))
    return registry


@pytest.fixture
def executor(tools: ToolRegistry) -> _CountingExecutor:
    """The real engine over the isolated registry, with no time budget."""

    return _CountingExecutor(tools)


def _coordinator(
    executor: _CountingExecutor,
    tools: ToolRegistry,
    policy: PolicyEngine | None,
) -> ToolExecutionCoordinator:
    """Engine, coordinator and policy over the *same* registry."""

    return ToolExecutionCoordinator(executor, registry=tools, policy=policy)


# ==============================================================
# Engine: the allowed action
# ==============================================================


class TestAllowed:
    def test_empty_policy_allows_any_tool(self) -> None:
        # No allowlist, no denylist: the out-of-the-box policy restricts nothing
        # by name, so a call falls through to ALLOW.
        engine = PolicyEngine(PolicyConfig())

        verdict = engine.evaluate("move_mouse", {"x": 1, "y": 2})

        assert verdict.decision is PolicyDecision.ALLOW
        assert verdict.allowed
        assert verdict.code == POLICY_ALLOWED
        assert verdict.tool == "move_mouse"

    def test_a_tool_on_the_allowlist_is_allowed(self) -> None:
        engine = PolicyEngine(PolicyConfig(allowed_tools={"move_mouse"}))

        assert engine.evaluate("move_mouse").allowed


# ==============================================================
# Engine: the denied action
# ==============================================================


class TestDenied:
    def test_a_denied_tool_is_denied(self) -> None:
        engine = PolicyEngine(PolicyConfig(denied_tools={"type_text"}))

        verdict = engine.evaluate("type_text", {"text": "secret"})

        assert verdict.decision is PolicyDecision.DENY
        assert verdict.denied
        assert verdict.code == POLICY_DENIED_TOOL

    def test_a_tool_absent_from_a_non_empty_allowlist_is_denied(self) -> None:
        engine = PolicyEngine(PolicyConfig(allowed_tools={"move_mouse"}))

        verdict = engine.evaluate("type_text")

        assert verdict.denied
        assert verdict.code == POLICY_NOT_ALLOWED

    def test_denylist_beats_allowlist(self) -> None:
        # A tool named in both is denied: an explicit deny is never overridden
        # by an allow.
        engine = PolicyEngine(
            PolicyConfig(
                allowed_tools={"type_text"},
                denied_tools={"type_text"},
            )
        )

        verdict = engine.evaluate("type_text")

        assert verdict.denied
        assert verdict.code == POLICY_DENIED_TOOL


# ==============================================================
# Engine: the confirmation-required action
# ==============================================================


class TestConfirmation:
    def test_confirmation_required_without_confirmation(self) -> None:
        engine = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))

        verdict = engine.evaluate("move_mouse", {"x": 1, "y": 2})

        assert verdict.decision is PolicyDecision.REQUIRE_CONFIRMATION
        assert verdict.requires_confirmation
        assert verdict.code == POLICY_CONFIRMATION_REQUIRED

    def test_confirmation_satisfied_allows(self) -> None:
        engine = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))

        verdict = engine.evaluate("move_mouse", confirmed=True)

        assert verdict.allowed
        assert verdict.code == POLICY_ALLOWED


# ==============================================================
# Engine: the iteration limit
# ==============================================================


class TestIterationLimit:
    def test_iteration_at_the_ceiling_is_denied(self) -> None:
        # max_iterations=3 permits iterations 0, 1, 2; iteration 3 is spent,
        # matching AgentState's own `iteration >= max_iterations` rule.
        engine = PolicyEngine(PolicyConfig(max_iterations=3))

        verdict = engine.evaluate("move_mouse", iteration=3)

        assert verdict.denied
        assert verdict.code == POLICY_ITERATION_LIMIT

    def test_iteration_below_the_ceiling_is_allowed(self) -> None:
        engine = PolicyEngine(PolicyConfig(max_iterations=3))

        assert engine.evaluate("move_mouse", iteration=2).allowed

    def test_no_ceiling_never_denies_on_iteration(self) -> None:
        engine = PolicyEngine(PolicyConfig())

        assert engine.evaluate("move_mouse", iteration=10_000).allowed


# ==============================================================
# Engine: the emergency stop
# ==============================================================


class TestEmergencyStop:
    def test_stop_denies_everything(self) -> None:
        engine = PolicyEngine(PolicyConfig(allowed_tools={"move_mouse"}))
        engine.trigger_emergency_stop("manual kill")

        verdict = engine.evaluate("move_mouse")

        # Even an allowlisted, otherwise-permitted tool is denied.
        assert verdict.denied
        assert verdict.code == POLICY_EMERGENCY_STOP
        assert engine.is_emergency_stopped

    def test_clearing_the_stop_restores_normal_evaluation(self) -> None:
        engine = PolicyEngine(PolicyConfig())
        engine.trigger_emergency_stop()
        assert engine.evaluate("move_mouse").denied

        engine.clear_emergency_stop()

        assert not engine.is_emergency_stopped
        assert engine.evaluate("move_mouse").allowed

    def test_stop_wins_over_iteration_ceiling(self) -> None:
        # Precedence: the stop is checked before the ceiling, so a stopped engine
        # answers EMERGENCY_STOP even for a call that is also over budget.
        engine = PolicyEngine(PolicyConfig(max_iterations=1))
        engine.trigger_emergency_stop()

        assert engine.evaluate("move_mouse", iteration=99).code == (
            POLICY_EMERGENCY_STOP
        )


# ==============================================================
# Engine: the policy failure (fail-closed)
# ==============================================================


class TestPolicyFailure:
    def test_a_raising_validator_denies_rather_than_waving_through(self) -> None:
        def broken(tool: str, arguments: Any) -> str | None:
            raise RuntimeError("validator blew up")

        engine = PolicyEngine(
            PolicyConfig(argument_validators={"move_mouse": broken})
        )

        verdict = engine.evaluate("move_mouse", {"x": 1, "y": 2})

        # Fail closed: the gate's own failure is a denial, with its own code.
        assert verdict.denied
        assert verdict.code == POLICY_FAILURE

    def test_a_validator_rejecting_arguments_denies(self) -> None:
        def needs_positive(tool: str, arguments: Any) -> str | None:
            if arguments.get("x", 0) < 0:
                return "x must be non-negative"
            return None

        engine = PolicyEngine(
            PolicyConfig(argument_validators={"move_mouse": needs_positive})
        )

        assert engine.evaluate("move_mouse", {"x": 5, "y": 0}).allowed

        verdict = engine.evaluate("move_mouse", {"x": -1, "y": 0})
        assert verdict.denied
        assert verdict.code == POLICY_INVALID_ARGUMENTS

    def test_a_global_validator_applies_to_every_tool(self) -> None:
        def deny_all(tool: str, arguments: Any) -> str:
            return "no tool may run"

        engine = PolicyEngine(
            PolicyConfig(global_argument_validators=[deny_all])
        )

        assert engine.evaluate("move_mouse").code == POLICY_INVALID_ARGUMENTS
        assert engine.evaluate("type_text").code == POLICY_INVALID_ARGUMENTS


# ==============================================================
# Engine: advisory timeout
# ==============================================================


class TestAdvisoryTimeout:
    def test_config_timeout_is_reported(self) -> None:
        engine = PolicyEngine(PolicyConfig(timeout_seconds=2.5))

        assert engine.evaluate("move_mouse").timeout_seconds == 2.5

    def test_timeout_falls_back_to_settings(self) -> None:
        engine = PolicyEngine(PolicyConfig())

        assert engine.evaluate("move_mouse").timeout_seconds == float(
            get_settings().TOOL_TIMEOUT_SECONDS
        )


# ==============================================================
# Coordinator integration
# ==============================================================


class TestCoordinatorIntegration:
    """The gate must decide before delegation, never after.

    ``executor.asked`` is the witness: an ALLOW reaches it, and a DENY or a
    REQUIRE_CONFIRMATION must not.
    """

    @pytest.mark.asyncio
    async def test_an_allowed_call_is_delegated(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        policy = PolicyEngine(PolicyConfig(allowed_tools={"move_mouse"}))
        coordinator = _coordinator(executor, tools, policy)
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))

        assert result.ok
        assert result.delegated
        assert executor.asked == ["move_mouse"]

    @pytest.mark.asyncio
    async def test_a_denied_call_never_reaches_the_executor(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        policy = PolicyEngine(PolicyConfig(denied_tools={"type_text"}))
        coordinator = _coordinator(executor, tools, policy)
        state = await _started()

        result = await coordinator.execute(state, _call("type_text", {"text": "x"}))

        assert result.refused
        assert not result.delegated
        assert result.status is ExecutionStatus.REFUSED
        assert result.error_type == POLICY_DENIED_TOOL
        # The whole point of a gate before the executor.
        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_a_confirmation_required_call_is_held(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        policy = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))
        coordinator = _coordinator(executor, tools, policy)
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))

        assert result.refused
        assert result.error_type == POLICY_CONFIRMATION_REQUIRED
        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_a_confirmed_call_is_delegated(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        policy = PolicyEngine(PolicyConfig(confirmation_tools={"move_mouse"}))
        coordinator = _coordinator(executor, tools, policy)
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("move_mouse", {"x": 1, "y": 2}),
            confirmed=True,
        )

        assert result.ok
        assert result.delegated
        assert executor.asked == ["move_mouse"]

    @pytest.mark.asyncio
    async def test_the_emergency_stop_refuses_at_the_coordinator(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        policy.trigger_emergency_stop("halt")
        coordinator = _coordinator(executor, tools, policy)
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))

        assert result.refused
        assert result.error_type == POLICY_EMERGENCY_STOP
        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_no_policy_delegates_every_enabled_call(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        # Backward compatibility: a coordinator built without a policy behaves
        # exactly as it did before the layer existed.
        coordinator = _coordinator(executor, tools, policy=None)
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))

        assert result.ok
        assert result.delegated
        assert coordinator.policy is None
        assert executor.asked == ["move_mouse"]


