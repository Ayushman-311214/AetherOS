"""
The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop.

Every step goes through the ToolRegistry via
:meth:`~aetheros.tools.executor.ToolExecutor.execute_safe`. The engine never
holds a function reference and never calls a controller directly, so a workflow
inherits the registry's argument validation, per-tool timeouts and safety policy
for free. It also means the engine cannot become a back door: a tool the policy
layer would gate for a direct caller is gated identically inside a workflow.

Three decisions here are worth reading before changing anything.

**A verification that could not run is not a failed action.** ``FAILED``
verification means something read the state back and it contradicted the
expectation — that is grounds to retry. ``ERROR`` means the *check itself* broke
(service missing, OCR unavailable). Retrying the action then would re-apply a
side effect that may well have succeeded the first time: a step that types a
password twice, or clicks Buy twice, because the engine could not see the
result. So ``ERROR`` records itself honestly in the step result, reports
``verified: false``, and does not trigger a retry. This matches the
:class:`~aetheros.desktop.verification.result.ToolResult` contract exactly —
``success = executed and not contradicted``.

**Retries are bounded three ways.** Per step by ``DESKTOP_STEP_MAX_ATTEMPTS``
and :data:`~aetheros.desktop.automation.workflow.ATTEMPT_CEILING`; recovery runs
per step by ``DESKTOP_RECOVERY_MAX_ATTEMPTS``; and the whole workflow by a
wall-clock deadline. The deadline is enforced *inside* the engine rather than
left to the executor's timeout so that hitting it produces a complete
:class:`~aetheros.desktop.automation.workflow.ExecutionResult` — every step run
so far, with its verification — instead of a bare "timed out" that says nothing
about how far the automation got or what state the machine is now in.

**Dry run shares this code path.** ``workflow.dry_run`` validates every step
against the live registry and validator and executes none of them. Validation is
not a separate implementation, so a workflow that validates cannot fail live on
a mismatch between two divergent checkers.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError
from ...core.errors.tool_error import ToolError
from ...core.logging import get_logger
from ...tools.executor import ToolExecutionResult, ToolExecutor, tool_executor
from ...tools.registry import ToolRegistry, tool_registry
from ...tools.validator import ToolValidator, tool_validator
from ..verification.result import VerificationResult, VerificationStatus
from ..verification.strategy import VerificationRequest
from ..verification.verifier import Verifier, verifier
from .recovery import RecoveryOutcome, RecoveryRunner, recovery_runner
from .workflow import (
    ExecutionResult,
    ExecutionStatus,
    Step,
    StepResult,
    StepStatus,
    Workflow,
    new_execution_id,
    summarise_verification,
    utc_now,
)

_MAX_VALUE_CHARS = 500
"""
How much of a tool's return value a step result keeps.

Screenshot and OCR tools can return several kilobytes of text; a workflow of 20
such steps would produce a result too large to hand back to the model and too
large to read in a log. The full value is available from the tool itself.
"""


class AutomationEngine:
    """
    Executes workflows step by step, verifying as it goes.

    Stateless between runs: everything about one execution lives in local
    variables and the returned :class:`ExecutionResult`. Two concurrent
    workflows therefore cannot interfere through the engine — though they will
    of course fight over the one real mouse, which is the caller's problem to
    avoid.
    """

    def __init__(
        self,
        executor: ToolExecutor = tool_executor,
        registry: ToolRegistry = tool_registry,
        validator: ToolValidator = tool_validator,
        checker: Verifier = verifier,
        recovery: RecoveryRunner = recovery_runner,
    ) -> None:

        self._executor = executor
        self._registry = registry
        self._validator = validator
        self._verifier = checker
        self._recovery = recovery
        self._logger = get_logger("desktop.automation")

    # ==========================================================
    # Public
    # ==========================================================

    async def execute(self, workflow: Workflow) -> ExecutionResult:
        """
        Run a workflow, or validate it when ``workflow.dry_run`` is set.
        """

        if workflow.dry_run:
            return await self.validate(workflow)

        execution_id = new_execution_id()
        started_at = utc_now()
        started = time.perf_counter()

        deadline = started + get_settings().DESKTOP_WORKFLOW_TIMEOUT_SECONDS

        self._logger.bind(
            execution_id=execution_id,
            workflow=workflow.name,
            steps=len(workflow.steps),
            stop_on_failure=workflow.stop_on_failure,
            rollback_on_failure=workflow.rollback_on_failure,
        ).info("Workflow started.")

        results: list[StepResult] = []
        rollback_results: tuple[StepResult, ...] = ()
        error: str | None = None

        try:

            for index, step in enumerate(workflow.steps, start=1):

                if time.perf_counter() >= deadline:
                    error = (
                        f"Workflow deadline of "
                        f"{get_settings().DESKTOP_WORKFLOW_TIMEOUT_SECONDS:g}s "
                        f"reached before step {index} ('{step.name}')."
                    )
                    break

                result = await self._run_step(
                    step,
                    execution_id=execution_id,
                    index=index,
                    deadline=deadline,
                )

                results.append(result)

                if result.ok:
                    continue

                if step.continue_on_failure:
                    self._logger.bind(
                        execution_id=execution_id,
                        step=step.name,
                    ).warning("Step failed; continuing as configured.")
                    continue

                if workflow.stop_on_failure:
                    error = error or (
                        f"Step '{step.name}' failed: {result.error or 'unverified'}"
                    )
                    break

        except asyncio.CancelledError:
            # Shutdown or Ctrl-C. Log what was already done — a cancelled
            # workflow has left the machine in a partially changed state, and
            # that record is the only way to reason about it afterwards — then
            # propagate, because swallowing cancellation hangs shutdown.
            self._logger.bind(
                execution_id=execution_id,
                workflow=workflow.name,
                completed_steps=len(results),
            ).warning("Workflow cancelled.")

            raise

        succeeded = error is None and all(result.ok for result in results)

        if not succeeded and workflow.rollback_on_failure:
            rollback_results = await self._rollback(
                workflow,
                results,
                execution_id=execution_id,
            )

        duration_ms = (time.perf_counter() - started) * 1000.0

        outcome = ExecutionResult(
            execution_id=execution_id,
            workflow=workflow.name,
            status=(
                ExecutionStatus.SUCCEEDED if succeeded else ExecutionStatus.FAILED
            ),
            steps=tuple(results),
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=utc_now(),
            dry_run=False,
            error=error,
            rollback=rollback_results,
        )

        self._logger.bind(
            execution_id=execution_id,
            workflow=workflow.name,
            status=outcome.status.value,
            success=outcome.success,
            steps_run=len(results),
            duration_ms=round(duration_ms, 2),
            error=error,
        ).info("Workflow finished.")

        return outcome

    # ----------------------------------------------------------

    async def validate(self, workflow: Workflow) -> ExecutionResult:
        """
        Check a workflow without executing any of it.

        Catches everything that can be known statically: unknown or disabled
        tools, arguments the validator would reject, verification methods that do
        not exist, and recovery strategy names that are typos. That last one
        matters more than it looks — a bad recovery name only surfaces at the
        moment the workflow was already in trouble, which is the worst possible
        time to discover a typo.
        """

        execution_id = new_execution_id()
        started_at = utc_now()
        started = time.perf_counter()

        results: list[StepResult] = []

        for index, step in enumerate(workflow.steps, start=1):
            results.append(self._validate_step(step, index=index))

        ok = all(result.ok for result in results)

        duration_ms = (time.perf_counter() - started) * 1000.0

        outcome = ExecutionResult(
            execution_id=execution_id,
            workflow=workflow.name,
            status=(
                ExecutionStatus.VALIDATED if ok else ExecutionStatus.FAILED
            ),
            steps=tuple(results),
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=utc_now(),
            dry_run=True,
            error=(
                None
                if ok
                else "Validation failed; see the failing step(s). Nothing was executed."
            ),
        )

        self._logger.bind(
            execution_id=execution_id,
            workflow=workflow.name,
            valid=ok,
            steps=len(results),
        ).info("Workflow validated (dry run).")

        return outcome

    # ==========================================================
    # One step
    # ==========================================================

    async def _run_step(
        self,
        step: Step,
        *,
        execution_id: str,
        index: int,
        deadline: float,
        is_recovery_step: bool = False,
    ) -> StepResult:
        """
        Precondition → wait → (execute → verify → retry) → wait.
        """

        started_at = utc_now()
        started = time.perf_counter()

        log = self._logger.bind(
            execution_id=execution_id,
            step=step.name,
            step_index=index,
            tool=step.tool,
            argument_names=sorted(step.arguments),
        )

        def finish(
            status: StepStatus,
            *,
            attempts: int = 0,
            recoveries: int = 0,
            value: Any = None,
            error: str | None = None,
            verification: VerificationResult | None = None,
            used_fallback: bool = False,
        ) -> StepResult:

            duration_ms = (time.perf_counter() - started) * 1000.0

            log.bind(
                status=status.value,
                attempts=attempts,
                recoveries=recoveries,
                verification_status=summarise_verification(verification),
                duration_ms=round(duration_ms, 2),
                error=error,
            ).info("Step finished.")

            return StepResult(
                name=step.name,
                tool=step.tool,
                status=status,
                attempts=attempts,
                recoveries=recoveries,
                value=_summarise_value(value),
                error=error,
                verification=verification,
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=utc_now(),
                used_fallback=used_fallback,
            )

        # ------------------------------------------------------
        # Precondition
        # ------------------------------------------------------

        if step.when is not None:

            try:
                precondition = await self._verifier.verify(step.when, force=True)

            except DesktopError as exc:
                return finish(
                    StepStatus.FAILED,
                    error=f"Precondition could not be evaluated: {exc}",
                )

            if not precondition.verified:
                log.bind(
                    condition=precondition.condition,
                    verification_status=precondition.status.value,
                ).info("Step skipped; precondition not met.")

                return finish(
                    StepStatus.SKIPPED,
                    verification=precondition,
                )

        # ------------------------------------------------------
        # Attempts
        # ------------------------------------------------------

        if step.wait_before > 0:
            await asyncio.sleep(step.wait_before)

        budget = step.attempt_budget
        recovery_ceiling = max(
            0, get_settings().DESKTOP_RECOVERY_MAX_ATTEMPTS
        )

        attempts = 0
        recoveries = 0
        last_error: str | None = None
        last_verification: VerificationResult | None = None
        last_value: Any = None

        while attempts < budget:

            attempts += 1

            execution = await self._executor.execute_safe(
                step.tool,
                dict(step.arguments),
            )

            last_value = execution.value

            if execution.ok:

                verification = await self._verify_step(step)
                last_verification = verification

                if verification is None or not verification.contradicted:

                    if step.wait_after > 0:
                        await asyncio.sleep(step.wait_after)

                    return finish(
                        (
                            StepStatus.SUCCEEDED
                            if attempts == 1
                            else StepStatus.RECOVERED
                        ),
                        attempts=attempts,
                        recoveries=recoveries,
                        value=execution.value,
                        verification=verification,
                    )

                last_error = (
                    f"Verification contradicted the action: "
                    f"{verification.condition} "
                    f"(expected {verification.expected!r}, "
                    f"actual {verification.actual!r})"
                )

            else:
                last_error = execution.error
                last_verification = None

                if execution.error_type in _UNRETRYABLE:
                    # A misspelled tool name or a rejected argument will be
                    # rejected identically on attempt two. Retrying is pure
                    # latency, and it buries the real problem under a pile of
                    # identical log lines.
                    log.bind(error_type=execution.error_type).warning(
                        "Step failed unretryably."
                    )
                    break

            # Out of attempts, or out of time.
            if attempts >= budget or time.perf_counter() >= deadline:
                break

            if step.recovery and recoveries < recovery_ceiling:
                outcomes = await self._recovery.run(
                    step.recovery,
                    execution_id=execution_id,
                    step_name=step.name,
                )
                recoveries += 1
                last_error = _append_recovery_detail(last_error, outcomes)

            await asyncio.sleep(_backoff_seconds(attempts))

        # ------------------------------------------------------
        # Fallback
        # ------------------------------------------------------

        if step.fallback is not None and not is_recovery_step:

            log.bind(fallback=step.fallback.name).warning(
                "Step exhausted its attempts; trying fallback."
            )

            fallback = await self._run_step(
                step.fallback,
                execution_id=execution_id,
                index=index,
                deadline=deadline,
                is_recovery_step=True,
            )

            if fallback.ok:
                return finish(
                    StepStatus.RECOVERED,
                    attempts=attempts,
                    recoveries=recoveries,
                    value=fallback.value,
                    verification=fallback.verification,
                    used_fallback=True,
                )

            last_error = (
                f"{last_error or 'step failed'}; "
                f"fallback '{step.fallback.name}' also failed: "
                f"{fallback.error or 'unverified'}"
            )

        return finish(
            StepStatus.FAILED,
            attempts=attempts,
            recoveries=recoveries,
            value=last_value,
            error=last_error or "Step failed without reporting an error.",
            verification=last_verification,
        )

    # ----------------------------------------------------------

    async def _verify_step(
        self,
        step: Step,
    ) -> VerificationResult | None:
        """
        Run a step's read-back, polling when it declared a timeout.

        Returns ``None`` when the step declared no verification — distinct from a
        ``SKIPPED`` result, which means verification was requested and switched
        off. The caller must not conflate them: "nothing to check" and "we chose
        not to look" deserve different words in an audit trail.
        """

        if step.verify is None:
            return None

        try:

            if step.timeout_seconds > 0:
                return await self._verifier.wait_until(
                    step.verify,
                    timeout_seconds=step.timeout_seconds,
                )

            return await self._verifier.verify(step.verify, force=True)

        except DesktopError as exc:
            # A malformed request — unknown method, unsupported mode. Report it
            # as a verification error rather than letting it abort the workflow:
            # the action already ran, and the caller needs to know that.
            return VerificationResult.errored(
                step.verify.describe(),
                method=step.verify.method,
                detail=str(exc),
            )

    # ==========================================================
    # Rollback
    # ==========================================================

    async def _rollback(
        self,
        workflow: Workflow,
        results: list[StepResult],
        *,
        execution_id: str,
    ) -> tuple[StepResult, ...]:
        """
        Undo the steps that succeeded, most recent first.

        Only steps that actually ran and declared a ``rollback`` are undone.
        Reverse order because rollback steps are rarely independent — a workflow
        that created a folder and then a file inside it must remove the file
        before the folder.

        Rollback runs with its own attempt budget and no fallback, and a failure
        inside it is recorded rather than raised: the workflow has already
        failed, and losing that outcome to a secondary error would leave the
        caller with no idea what the original problem was.
        """

        undoable = [
            (result, step)
            for result, step in zip(results, workflow.steps)
            if step.rollback is not None
            and result.status
            in (StepStatus.SUCCEEDED, StepStatus.RECOVERED)
        ]

        if not undoable:
            return ()

        self._logger.bind(
            execution_id=execution_id,
            workflow=workflow.name,
            steps=len(undoable),
        ).warning("Rolling back completed steps.")

        deadline = (
            time.perf_counter() + get_settings().DESKTOP_WORKFLOW_TIMEOUT_SECONDS
        )

        rolled: list[StepResult] = []

        for index, (_, step) in enumerate(reversed(undoable), start=1):

            assert step.rollback is not None  # filtered above

            rolled.append(
                await self._run_step(
                    step.rollback,
                    execution_id=execution_id,
                    index=index,
                    deadline=deadline,
                    is_recovery_step=True,
                )
            )

        return tuple(rolled)

    # ==========================================================
    # Validation
    # ==========================================================

    def _validate_step(
        self,
        step: Step,
        *,
        index: int,
        label: str = "",
    ) -> StepResult:

        name = label or step.name
        problems: list[str] = []

        if not self._registry.exists(step.tool):
            problems.append(
                f"unknown tool '{step.tool}'"
            )

        else:
            definition = self._registry.get(step.tool)

            if not definition.enabled:
                problems.append(f"tool '{step.tool}' is disabled")

            else:
                try:
                    self._validator.validate(definition, dict(step.arguments))

                except ToolError as exc:
                    problems.append(f"arguments rejected: {exc}")

        for field_name, request in (
            ("when", step.when),
            ("verify", step.verify),
        ):
            problem = self._validate_request(field_name, request)

            if problem:
                problems.append(problem)

        unknown_recovery = self._recovery.unknown(step.recovery)

        if unknown_recovery:
            problems.append(
                f"unknown recovery strategy: {', '.join(unknown_recovery)} "
                f"(available: {', '.join(self._recovery.names)})"
            )

        for field_name, nested in (
            ("fallback", step.fallback),
            ("rollback", step.rollback),
        ):
            if nested is None:
                continue

            nested_result = self._validate_step(
                nested,
                index=index,
                label=f"{name}.{field_name}",
            )

            if not nested_result.ok:
                problems.append(
                    f"{field_name} step invalid: {nested_result.error}"
                )

        return StepResult(
            name=name,
            tool=step.tool,
            status=(
                StepStatus.VALIDATED if not problems else StepStatus.FAILED
            ),
            error="; ".join(problems) or None,
        )

    def _validate_request(
        self,
        field_name: str,
        request: VerificationRequest | None,
    ) -> str | None:

        if request is None:
            return None

        if request.method not in self._verifier.methods:
            return (
                f"{field_name} uses unknown verification method "
                f"'{request.method}' (available: "
                f"{', '.join(self._verifier.methods)})"
            )

        return None


# ==============================================================
# Helpers
# ==============================================================

_UNRETRYABLE = frozenset(
    {
        "UnknownTool",
        "ToolDisabled",
        "InvalidArguments",
    }
)
"""
Executor error types that a second attempt cannot change.

Deliberately excludes ``Timeout``: a tool that timed out may well succeed on a
quieter machine, and it is exactly the kind of transient fault retries exist for.
"""


def _backoff_seconds(attempt: int) -> float:
    """
    Delay before the next attempt: exponential, and capped.

    Exponential because the usual cause of a failed desktop action is that the UI
    was not ready, and readiness does not arrive on a fixed schedule. Capped
    because a workflow's total duration has to stay predictable — without a cap,
    attempt 10 alone would wait over two minutes.
    """

    base = get_settings().DESKTOP_RETRY_BACKOFF_SECONDS
    ceiling = get_settings().DESKTOP_MAX_WAIT_SECONDS

    return min(base * (2 ** max(0, attempt - 1)), ceiling)


def _append_recovery_detail(
    error: str | None,
    outcomes: tuple[RecoveryOutcome, ...],
) -> str | None:
    """
    Fold recovery outcomes into the error the step will report if it still fails.

    Attached to the error rather than logged alone so the final message answers
    "did anything try to fix this?" without a log dive.
    """

    if not outcomes:
        return error

    summary = ", ".join(
        f"{outcome.strategy}={'applied' if outcome.applied else outcome.detail}"
        for outcome in outcomes
    )

    return f"{error or 'step failed'} [recovery: {summary}]"


def _summarise_value(value: Any) -> Any:
    """
    Trim a tool's return value to something a result can carry.
    """

    if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
        return f"{value[:_MAX_VALUE_CHARS]}… ({len(value)} chars)"

    if isinstance(value, dict):
        return {key: _summarise_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        trimmed = [_summarise_value(item) for item in value[:20]]

        if len(value) > 20:
            trimmed.append(f"… ({len(value)} items)")

        return trimmed

    return value


automation_engine = AutomationEngine()
"""
Process-wide engine.

Stateless, so a single instance is safe to share; the tools import it at module
scope, before the container is populated.
"""


__all__ = [
    "AutomationEngine",
    "ToolExecutionResult",
    "VerificationStatus",
    "automation_engine",
]
