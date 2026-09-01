"""
Tool execution: validation, sync/async dispatch, and failure handling.

The executor is the boundary between untrusted model output and real side
effects, so most of what is asserted here is what must *not* happen — an
unvalidated argument reaching a tool, a tool failure escaping as an exception
and killing the conversation, a blocking tool stalling the event loop.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from aetheros.core.errors.tool_error import ToolError
from aetheros.tools.executor import ToolExecutionResult, ToolExecutor


# ==============================================================
# Sample tools
# ==============================================================


def add(a: int, b: int) -> int:
    """Add two integers."""

    return a + b


async def add_async(a: int, b: int) -> int:
    """Add two integers, asynchronously."""

    await asyncio.sleep(0)

    return a + b


def scale(value: float, factor: float = 2.0) -> float:
    """Multiply a number, with a default factor."""

    return value * factor


def returns_none(label: str) -> None:
    """A tool with no return value, like most desktop actions."""


def explodes() -> None:
    """A tool that raises an ordinary exception."""

    raise ValueError("boom")


def raises_tool_error() -> None:
    """A tool that raises the domain error."""

    raise ToolError("backend unavailable")


async def sleeps_forever() -> None:
    """A tool that never returns."""

    await asyncio.sleep(30)


async def sleeps_briefly() -> str:
    """A tool that is slow but does finish — an OCR pass in miniature."""

    await asyncio.sleep(0.15)

    return "finished"


def returns_awaitable() -> object:
    """A sync tool whose return value still has to be awaited."""

    async def _inner() -> str:
        return "awaited"

    return _inner()


# ==============================================================
# Successful execution
# ==============================================================


class TestSyncExecution:

    @pytest.mark.asyncio
    async def test_sync_tool_runs_and_returns_its_value(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": 2, "b": 3},
        )

        assert isinstance(result, ToolExecutionResult)
        assert result.ok is True
        assert result.value == 5
        assert result.error is None
        assert result.name == "add"
        assert result.duration_ms >= 0.0

    @pytest.mark.asyncio
    async def test_execute_returns_the_raw_value(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add))

        assert await ToolExecutor(registry).execute(
            "add",
            {"a": 40, "b": 2},
        ) == 42

    @pytest.mark.asyncio
    async def test_default_arguments_are_honoured(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(scale))

        result = await ToolExecutor(registry).execute_safe(
            "scale",
            {"value": 3},
        )

        assert result.ok is True
        assert result.value == 6.0

    @pytest.mark.asyncio
    async def test_a_tool_returning_none_still_succeeds(
        self,
        registry,
        define,
    ) -> None:
        """
        Most desktop tools return None; that is a success, not a failure.
        """

        registry.register(define(returns_none))

        result = await ToolExecutor(registry).execute_safe(
            "returns_none",
            {"label": "x"},
        )

        assert result.ok is True
        assert result.value is None

    @pytest.mark.asyncio
    async def test_awaitable_returned_by_a_sync_tool_is_awaited(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(returns_awaitable))

        result = await ToolExecutor(registry).execute_safe(
            "returns_awaitable",
        )

        assert result.ok is True
        assert result.value == "awaited"

    @pytest.mark.asyncio
    async def test_sync_tool_does_not_block_the_event_loop(
        self,
        registry,
        define,
    ) -> None:
        """
        Sync tools are offloaded to a thread. Without that, a blocking
        pyautogui or pyperclip call would stall the loop for its whole
        duration — and a stalled loop cannot enforce the timeout either.
        """

        def blocking() -> str:
            """A deliberately blocking sync tool."""

            time.sleep(0.2)

            return "done"

        registry.register(define(blocking))

        ticks = 0
        observed: dict[str, int] = {}

        async def tick() -> None:
            nonlocal ticks

            for _ in range(20):
                await asyncio.sleep(0.01)
                ticks += 1

        async def run_tool() -> ToolExecutionResult:
            result = await ToolExecutor(registry).execute_safe("blocking")
            observed["ticks"] = ticks
            return result

        result, _ = await asyncio.gather(run_tool(), tick())

        assert result.ok is True
        assert result.value == "done"

        # Had the tool run on the loop thread, no tick could have fired before
        # it returned.
        assert observed["ticks"] >= 2


class TestAsyncExecution:

    @pytest.mark.asyncio
    async def test_async_tool_runs_and_returns_its_value(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add_async))

        result = await ToolExecutor(registry).execute_safe(
            "add_async",
            {"a": 7, "b": 1},
        )

        assert result.ok is True
        assert result.value == 8

    @pytest.mark.asyncio
    async def test_async_tool_via_execute(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add_async))

        assert await ToolExecutor(registry).execute(
            "add_async",
            {"a": 1, "b": 1},
        ) == 2


# ==============================================================
# Argument validation
# ==============================================================


class TestArgumentValidation:

    @pytest.mark.asyncio
    async def test_wrong_argument_type_is_rejected(
        self,
        registry,
        define,
    ) -> None:
        """
        The model sending a string for an int parameter must be told so, not
        allowed to trigger a TypeError deep inside a backend.
        """

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": "not-an-int", "b": 3},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"
        assert "'a'" in (result.error or "")

    @pytest.mark.asyncio
    async def test_validation_happens_before_the_tool_runs(
        self,
        registry,
        define,
    ) -> None:
        """
        The point of validating is to stop side effects, so a rejected call
        must not have touched the tool at all.
        """

        calls: list[tuple[object, object]] = []

        def recorder(a: int, b: int) -> int:
            """Records that it ran."""

            calls.append((a, b))

            return 0

        registry.register(define(recorder))

        result = await ToolExecutor(registry).execute_safe(
            "recorder",
            {"a": "nope", "b": 1},
        )

        assert result.ok is False
        assert calls == []

    @pytest.mark.asyncio
    async def test_missing_required_argument_is_rejected(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": 1},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"
        assert "'b'" in (result.error or "")

    @pytest.mark.asyncio
    async def test_unknown_argument_is_rejected(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": 1, "b": 2, "invented": True},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"
        assert "invented" in (result.error or "")

    @pytest.mark.asyncio
    async def test_bool_is_not_accepted_for_an_int_parameter(
        self,
        registry,
        define,
    ) -> None:
        """
        bool subclasses int, so a plain isinstance check would let True through.
        """

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": True, "b": 1},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"

    @pytest.mark.asyncio
    async def test_int_is_accepted_for_a_float_parameter(
        self,
        registry,
        define,
    ) -> None:
        """
        JSON has one number type: a float parameter legitimately receives 5.
        """

        registry.register(define(scale))

        result = await ToolExecutor(registry).execute_safe(
            "scale",
            {"value": 5, "factor": 3},
        )

        assert result.ok is True
        assert result.value == 15

    @pytest.mark.asyncio
    async def test_execute_raises_on_invalid_arguments(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add))

        with pytest.raises(ToolError):
            await ToolExecutor(registry).execute(
                "add",
                {"a": "x", "b": 1},
            )


# ==============================================================
# Unknown and disabled tools
# ==============================================================


class TestUnknownTool:

    @pytest.mark.asyncio
    async def test_unknown_tool_is_reported_not_raised(
        self,
        registry,
        define,
    ) -> None:
        """
        This used to escape as a bare KeyError from registry.get(), outside the
        executor's try block, aborting the whole agent run.
        """

        registry.register(define(add))

        result = await ToolExecutor(registry).execute_safe(
            "teleport",
            {},
        )

        assert result.ok is False
        assert result.error_type == "UnknownTool"
        assert "teleport" in (result.error or "")

    @pytest.mark.asyncio
    async def test_unknown_tool_error_lists_what_is_available(
        self,
        registry,
        define,
    ) -> None:
        """
        The message is fed back to the model, so it has to be actionable.
        """

        registry.register(define(add))
        registry.register(define(scale))

        result = await ToolExecutor(registry).execute_safe("teleport")

        assert "add" in (result.error or "")
        assert "scale" in (result.error or "")

    @pytest.mark.asyncio
    async def test_unknown_tool_with_an_empty_registry(
        self,
        registry,
    ) -> None:

        result = await ToolExecutor(registry).execute_safe("teleport")

        assert result.ok is False
        assert "none" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_raises_for_an_unknown_tool(
        self,
        registry,
    ) -> None:

        with pytest.raises(ToolError, match="teleport"):
            await ToolExecutor(registry).execute("teleport")

    @pytest.mark.asyncio
    async def test_disabled_tool_is_refused(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(add, enabled=False))

        result = await ToolExecutor(registry).execute_safe(
            "add",
            {"a": 1, "b": 2},
        )

        assert result.ok is False
        assert result.error_type == "ToolDisabled"


# ==============================================================
# Failure inside the tool
# ==============================================================


class TestToolFailure:

    @pytest.mark.asyncio
    async def test_exception_is_captured_not_raised(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(explodes))

        result = await ToolExecutor(registry).execute_safe("explodes")

        assert result.ok is False
        assert result.error_type == "ValueError"

    @pytest.mark.asyncio
    async def test_underlying_message_is_preserved(
        self,
        registry,
        define,
    ) -> None:
        """
        Failures used to be re-raised as RuntimeError("Tool 'x' failed."), which
        discarded the only information the model could have acted on.
        """

        registry.register(define(explodes))

        result = await ToolExecutor(registry).execute_safe("explodes")

        assert "boom" in (result.error or "")

    @pytest.mark.asyncio
    async def test_tool_error_keeps_its_type(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(raises_tool_error))

        result = await ToolExecutor(registry).execute_safe(
            "raises_tool_error",
        )

        assert result.ok is False
        assert result.error_type == "ToolError"
        assert "backend unavailable" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_raises_with_the_original_message(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(explodes))

        with pytest.raises(ToolError, match="boom"):
            await ToolExecutor(registry).execute("explodes")

    @pytest.mark.asyncio
    async def test_a_tool_that_never_returns_times_out(
        self,
        registry,
        define,
    ) -> None:
        """
        A hanging tool is indistinguishable from an infinite loop to the agent,
        so execution is bounded.
        """

        registry.register(define(sleeps_forever))

        executor = ToolExecutor(registry, timeout_seconds=0.05)

        result = await executor.execute_safe("sleeps_forever")

        assert result.ok is False
        assert result.error_type == "Timeout"

    @pytest.mark.asyncio
    async def test_execute_safe_never_raises(
        self,
        registry,
        define,
    ) -> None:
        """
        The contract the agent loop depends on: every failure mode comes back
        as a value, so one bad tool call cannot end the conversation.
        """

        registry.register(define(explodes))
        registry.register(define(raises_tool_error))
        registry.register(define(add))

        executor = ToolExecutor(registry)

        cases = [
            ("explodes", {}),
            ("raises_tool_error", {}),
            ("add", {"a": "x", "b": 1}),
            ("add", {}),
            ("nonexistent", {"anything": 1}),
        ]

        for name, arguments in cases:
            result = await executor.execute_safe(name, arguments)

            assert result.ok is False, name
            assert result.error


# ==============================================================
# Per-tool execution budgets
# ==============================================================


class TestExecutionBudget:
    """
    One registry holds a mouse click and a full-screen OCR pass, and no single
    timeout serves both. A click that has not returned in 30s is broken; an OCR
    pass measured 136s cold on CPU and was cancelled every time by that same 30s
    default — the vision tools worked correctly and reported a timeout anyway.

    So a tool may declare its own budget. These tests pin the resolution order,
    because getting it wrong is silent in both directions: too low cancels
    working tools, too high lets a wedged one stall an agent.
    """

    @pytest.mark.asyncio
    async def test_a_declared_budget_overrides_a_shorter_default(
        self,
        registry,
        define,
    ) -> None:
        """
        The actual vision bug: slow but correct work must be allowed to finish.
        """

        registry.register(
            define(sleeps_briefly, timeout_seconds=5.0)
        )

        result = await ToolExecutor(
            registry,
            timeout_seconds=0.05,
        ).execute_safe("sleeps_briefly")

        assert result.ok is True, result.error
        assert result.value == "finished"

    @pytest.mark.asyncio
    async def test_a_declared_budget_also_tightens_a_longer_default(
        self,
        registry,
        define,
    ) -> None:
        """
        The override is a budget, not a licence: a tool may ask for *less* than
        the default, and a tool that hangs is still cut off.
        """

        registry.register(
            define(sleeps_forever, timeout_seconds=0.05)
        )

        result = await ToolExecutor(
            registry,
            timeout_seconds=30.0,
        ).execute_safe("sleeps_forever")

        assert result.ok is False
        assert result.error_type == "Timeout"

    @pytest.mark.asyncio
    async def test_a_tool_without_a_declared_budget_uses_the_default(
        self,
        registry,
        define,
    ) -> None:

        registry.register(define(sleeps_forever))

        result = await ToolExecutor(
            registry,
            timeout_seconds=0.05,
        ).execute_safe("sleeps_forever")

        assert result.ok is False
        assert result.error_type == "Timeout"

    @pytest.mark.asyncio
    async def test_an_unbounded_executor_ignores_a_declared_budget(
        self,
        registry,
        define,
    ) -> None:
        """
        ``timeout_seconds=None`` is a deliberate choice by the caller — a
        diagnostic run measuring how long a tool really takes — so it has to win
        over what the tool declares. Otherwise the measurement is the thing being
        cut off.
        """

        registry.register(
            define(sleeps_briefly, timeout_seconds=0.01)
        )

        result = await ToolExecutor(
            registry,
            timeout_seconds=None,
        ).execute_safe("sleeps_briefly")

        assert result.ok is True, result.error
        assert result.value == "finished"

    @pytest.mark.asyncio
    async def test_the_timeout_message_names_the_budget_that_applied(
        self,
        registry,
        define,
    ) -> None:
        """
        The message used to report the executor default regardless, so a tool
        granted 300s was told it "timed out after 30.0 seconds". A wrong number
        sends whoever reads it looking in the wrong place.
        """

        registry.register(
            define(sleeps_forever, timeout_seconds=0.05)
        )

        result = await ToolExecutor(
            registry,
            timeout_seconds=30.0,
        ).execute_safe("sleeps_forever")

        assert result.error is not None
        assert "0.05" in result.error
        assert "30.0" not in result.error

    @pytest.mark.asyncio
    async def test_the_default_budget_comes_from_configuration(
        self,
        registry,
        define,
        monkeypatch,
    ) -> None:
        """
        The right timeout is a property of the machine, not of this module: the
        same OCR pass is 136s on CPU and single-digit seconds on CUDA. Hard-coding
        it means one of those two users is always wrong.
        """

        from aetheros.tools import executor as executor_module

        settings = executor_module.get_settings()

        monkeypatch.setattr(
            executor_module,
            "get_settings",
            lambda: settings.model_copy(
                update={"TOOL_TIMEOUT_SECONDS": 0.05},
            ),
        )

        registry.register(define(sleeps_forever))

        result = await ToolExecutor(registry).execute_safe("sleeps_forever")

        assert result.ok is False
        assert result.error_type == "Timeout"
        assert result.error is not None
        assert "0.05" in result.error


# ==============================================================
# Registry guarantees the executor relies on
# ==============================================================


class TestRegistryGuarantees:

    def test_duplicate_tool_name_is_rejected_loudly(
        self,
        registry,
        define,
    ) -> None:
        """
        Two tools sharing a name would make dispatch ambiguous, so registration
        fails rather than silently overwriting.
        """

        registry.register(define(add, name="duplicate"))

        with pytest.raises(ValueError, match="already registered"):
            registry.register(define(scale, name="duplicate"))

    def test_registry_fixture_is_isolated(
        self,
        registry,
    ) -> None:
        """
        Tests must not see, or pollute, the process-wide tool_registry.
        """

        from aetheros.tools.registry import tool_registry

        assert registry is not tool_registry
        assert registry.count == 0
