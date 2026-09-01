from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any

from ..core.errors.tool_error import ToolError
from ..core.logging import get_logger
from ..config.config_loader import get_settings

from .registry import ToolDefinition, ToolRegistry, tool_registry
from .validator import ToolValidator, tool_validator

# A tool that never returns is indistinguishable from an infinite loop as far
# as the agent is concerned, so every execution is bounded. pyautogui and OCR
# calls are the realistic offenders.
#
# The budget itself lives in configuration (``TOOL_TIMEOUT_SECONDS``, and
# ``VISION_TOOL_TIMEOUT_SECONDS`` for the tools that declare their own), because
# it is a property of the machine rather than of this module.


class _Unset:
    """
    Sentinel type for "the caller did not specify a timeout".

    ``None`` cannot serve as the default because it already means something
    else here — *unbounded* — and a diagnostic run that deliberately asks for no
    timeout must not silently receive the configured one instead.
    """

    __slots__ = ()


_UNSET = _Unset()


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """
    Outcome of a single tool execution.

    Carries failures as data rather than as exceptions so the agent loop can
    report them back to the model and let it recover, instead of aborting the
    whole conversation on one bad call.
    """

    name: str
    ok: bool
    value: Any = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: float = 0.0


class ToolExecutor:
    """
    Executes registered AetherOS tools.
    """

    def __init__(
        self,
        registry: ToolRegistry = tool_registry,
        validator: ToolValidator = tool_validator,
        *,
        timeout_seconds: float | None | _Unset = _UNSET,
    ) -> None:

        self._registry = registry
        self._validator = validator

        if isinstance(timeout_seconds, _Unset):
            # Read here rather than as a default argument value: a default is
            # evaluated once at import, which would pin the budget before .env
            # is loaded and make it untestable.
            self._timeout_seconds: float | None = (
                get_settings().TOOL_TIMEOUT_SECONDS
            )

        else:
            self._timeout_seconds = timeout_seconds

        self._logger = get_logger("tool_executor")

    # ==========================================================
    # Public
    # ==========================================================

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a registered tool, raising on failure.

        Raises
        ------
        ToolError
            Unknown tool, disabled tool, invalid arguments, timeout, or a
            failure inside the tool itself. The underlying message is
            preserved so the caller can act on it.
        """

        result = await self._run(
            name,
            arguments or {},
        )

        if not result.ok:
            raise ToolError(result.error or f"Tool '{name}' failed.")

        return result.value

    async def execute_safe(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """
        Execute a registered tool, reporting failure as a value.

        Never raises for a tool-level problem. This is the entry point the
        agent loop uses: a failed tool becomes an observation the model can
        read, not an exception that ends the run.
        """

        return await self._run(
            name,
            arguments or {},
        )

    # ==========================================================
    # Internal
    # ==========================================================

    async def _run(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        """
        Single execution path shared by execute() and execute_safe().
        """

        started = time.perf_counter()

        def elapsed_ms() -> float:
            return (time.perf_counter() - started) * 1000.0

        def failure(
            error: str,
            error_type: str,
        ) -> ToolExecutionResult:
            return ToolExecutionResult(
                name=name,
                ok=False,
                error=error,
                error_type=error_type,
                duration_ms=elapsed_ms(),
            )

        # ------------------------------------------------------
        # Resolve
        # ------------------------------------------------------

        if not self._registry.exists(name):

            available = ", ".join(self._registry.names())

            return failure(
                f"Unknown tool '{name}'. "
                f"Available tools: {available or 'none'}.",
                "UnknownTool",
            )

        tool = self._registry.get(name)

        if not tool.enabled:
            return failure(
                f"Tool '{name}' is disabled.",
                "ToolDisabled",
            )

        # ------------------------------------------------------
        # Validate before doing anything with side effects
        # ------------------------------------------------------

        try:
            self._validator.validate(tool, arguments)

        except ToolError as exc:
            # Argument names only — values may contain typed text or clipboard
            # contents. See _log_outcome.
            self._logger.bind(
                tool=name,
                argument_names=sorted(arguments),
            ).warning("Tool arguments rejected by validator.")

            return failure(str(exc), "InvalidArguments")

        # ------------------------------------------------------
        # Invoke
        # ------------------------------------------------------

        # Resolved before the call so the timeout message can name the budget
        # that was actually applied. Reporting self._timeout_seconds here told
        # the user "timed out after 30.0 seconds" even when the tool had been
        # granted 180 — a misleading number is worse than none.
        budget = self._budget_for(tool)

        try:
            value = await self._invoke(tool, arguments)

        except asyncio.CancelledError:
            # Shutdown or Ctrl-C. Must propagate, or cancellation hangs.
            raise

        except asyncio.TimeoutError:
            self._log_outcome(name, False, elapsed_ms(), arguments)

            return failure(
                f"Tool '{name}' timed out after {budget} seconds.",
                "Timeout",
            )

        except ToolError as exc:
            self._log_outcome(name, False, elapsed_ms(), arguments)

            return failure(str(exc), "ToolError")

        except Exception as exc:
            self._logger.bind(
                tool=name,
                error_type=type(exc).__name__,
            ).exception("Tool raised an exception.")

            return failure(
                f"Tool '{name}' failed: "
                f"{type(exc).__name__}: {exc}",
                type(exc).__name__,
            )

        self._log_outcome(name, True, elapsed_ms(), arguments)

        return ToolExecutionResult(
            name=name,
            ok=True,
            value=value,
            duration_ms=elapsed_ms(),
        )

    def _budget_for(
        self,
        tool: ToolDefinition,
    ) -> float | None:
        """
        The execution budget for one tool, in seconds.

        A tool's own declared timeout wins over the executor default. That is
        the only way one registry can hold both a mouse click, which is broken
        if it has not returned in 30s, and a full-screen OCR pass, which
        legitimately needs 90s+ on CPU.

        An explicit ``timeout_seconds=None`` on the executor still means
        unbounded and overrides the per-tool value, because that is a deliberate
        choice by the caller — the test suite and one-off diagnostics use it.
        """

        if self._timeout_seconds is None:
            return None

        declared = getattr(tool, "timeout_seconds", None)

        if declared is None:
            return self._timeout_seconds

        return declared

    async def _invoke(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Call the tool function, handling both sync and async tools.
        """

        function = tool.function

        # iscoroutinefunction() is authoritative; ToolDefinition.is_async is a
        # hint that may be absent on a hand-built definition.
        if inspect.iscoroutinefunction(function) or tool.is_async:
            call = function(**arguments)

        else:
            # A blocking sync tool (pyperclip, pyautogui) would otherwise stall
            # the event loop for its whole duration — and a stalled loop cannot
            # honour the timeout below.
            call = asyncio.to_thread(
                lambda: function(**arguments)
            )

        budget = self._budget_for(tool)

        if budget is None:
            result = await call
        else:
            result = await asyncio.wait_for(
                call,
                timeout=budget,
            )

        # A sync tool may still return an awaitable.
        if inspect.isawaitable(result):
            return await result

        return result

    # ==========================================================
    # Logging
    # ==========================================================

    def _log_outcome(
        self,
        name: str,
        ok: bool,
        duration_ms: float,
        arguments: dict[str, Any],
    ) -> None:
        """
        Record that a tool ran, without recording what it was given.

        Tool arguments are deliberately excluded. ``type_text``, ``press_key``
        and ``copy_text`` receive literal keystrokes, which may include a
        password the user was pasting; the file sinks retain for 30-60 days, so
        logging those values would amount to writing a keylogger to disk. The
        argument names are enough to audit which tool ran with which shape of
        input.
        """

        self._logger.bind(
            tool=name,
            ok=ok,
            duration_ms=round(duration_ms, 2),
            argument_names=sorted(arguments),
        ).info("Tool execution finished.")


tool_executor = ToolExecutor()
