"""
Tests for the automation engine.

Nothing here touches the real machine. The engine's contract is "route every step
through the ToolRegistry", so an isolated registry holding synthetic tools
exercises the entire code path — retries, recovery, fallback, rollback,
validation — without generating a single real keystroke. That is not a compromise
for the sake of testability; it is the same property that makes the engine safe to
put behind an LLM.

The synthetic tools count their own invocations, which is what makes the bounding
claims checkable. "``max_attempts`` is respected" is only worth asserting against
the number of times the underlying function actually ran — a step result reporting
``attempts=3`` while the tool ran nine times would look identical from the
outside.
"""

from __future__ import annotations

import asyncio

import pytest

from aetheros.core.errors.desktop_error import DesktopError
from aetheros.desktop.automation.engine import AutomationEngine
from aetheros.desktop.automation.recovery import RecoveryRunner
from aetheros.desktop.automation.workflow import (
    ATTEMPT_CEILING,
    MAX_STEPS,
    ExecutionStatus,
    Step,
    StepStatus,
    Workflow,
)
from aetheros.desktop.verification.result import VerificationResult
from aetheros.desktop.verification.strategy import VerificationRequest
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolDefinition, ToolRegistry


class Calls:
    """
    Invocation counter shared by the synthetic tools.

    A plain object rather than a fixture value because the tool functions close
    over it, and closing over a mutable counter is what lets a test assert on how
    many times the *function* ran rather than how many times the engine says it
    ran.
    """

    def __init__(self) -> None:
        self.ok = 0
        self.flaky = 0
        self.doomed = 0
        self.undo = 0
        self.recovery = 0


@pytest.fixture
def calls() -> Calls:
    return Calls()


@pytest.fixture
def registry(calls: Calls) -> ToolRegistry:
    """
    An isolated registry of harmless synthetic tools.
    """

    def echo(value: str = "hello") -> str:
        calls.ok += 1
        return value

    def flaky() -> str:
        calls.flaky += 1

        if calls.flaky < 3:
            raise RuntimeError(f"attempt {calls.flaky} failed")

        return "worked eventually"

    def doomed() -> str:
        calls.doomed += 1
        raise RuntimeError("permanent failure")

    def undo() -> str:
        calls.undo += 1
        return "undone"

    async def hangs() -> str:
        await asyncio.sleep(60)
        return "never"

    def settle_marker() -> str:
        calls.recovery += 1
        return "settled"

    isolated = ToolRegistry()

    for function, name in (
        (echo, "echo"),
        (flaky, "flaky"),
        (doomed, "doomed"),
        (undo, "undo"),
        (hangs, "hangs"),
        (settle_marker, "press_key"),
    ):
        isolated.register(
            ToolDefinition(
                name=name,
                description=f"Synthetic test tool: {name}.",
                function=function,
            )
        )

    return isolated


@pytest.fixture
def engine(registry: ToolRegistry) -> AutomationEngine:
    """
    An engine wired to the isolated registry, top to bottom.

    The recovery runner gets the same registry so that ``dismiss_dialog`` — whose
    only required tool is ``press_key`` — is genuinely available here, and the
    recovery path is exercised rather than skipped as unavailable.
    """

    executor = ToolExecutor(registry=registry)

    return AutomationEngine(
        executor=executor,
        registry=registry,
        recovery=RecoveryRunner(executor=executor, registry=registry),
    )


def _matching_state(value: str = "x") -> dict[str, str]:
    """A verification spec that always holds."""

    return {"method": "state", "expected": value, "target": value}


def _failing_state() -> dict[str, str]:
    """A verification spec that never holds."""

    return {"method": "state", "expected": "yes", "target": "no"}


# ==============================================================
# The data layer
# ==============================================================


class TestWorkflowBounds:
    """
    Every bound is enforced in a constructor, so an unbounded workflow cannot
    exist as a value. These tests hold that line: moving a check into the engine
    would make it skippable by any future call site.
    """

    def test_waits_are_clamped_to_the_configured_ceiling(self) -> None:

        step = Step.from_dict(
            {
                "tool": "echo",
                "wait_before": 9999,
                "wait_after": 9999,
                "timeout_seconds": 9999,
            }
        )

        assert step.wait_before == 25.0
        assert step.wait_after == 25.0
        assert step.timeout_seconds == 25.0

    def test_attempts_are_capped_by_the_hard_ceiling(self) -> None:
        """
        "Never create infinite retries" is not satisfied by a large number
        either: 500 attempts against a UI that will never respond is a hang with
        extra logging.
        """

        assert Step.from_dict({"tool": "echo", "max_attempts": 500}).attempt_budget == (
            ATTEMPT_CEILING
        )

    def test_name_defaults_to_the_tool(self) -> None:
        assert Step.from_dict({"tool": "echo"}).name == "echo"

    @pytest.mark.parametrize(
        "spec",
        [
            {"tool": "echo", "path": "unexpected"},
            {"arguments": {}},
            {"tool": ""},
            {"tool": "echo", "arguments": "not a dict"},
            {"tool": "echo", "verify": {"method": "file", "path": "x"}},
        ],
        ids=["unknown-key", "no-tool", "empty-tool", "bad-arguments", "bad-verify-key"],
    )
    def test_malformed_steps_are_rejected(self, spec: dict) -> None:
        """
        Unknown keys are rejected rather than ignored. A step that says
        ``{"method": "file", "path": "x"}`` meant ``target``; dropping the key
        would produce a check that passes for the wrong reason, which is worse
        than no check at all.
        """

        with pytest.raises(DesktopError):
            Step.from_dict(spec)

    def test_oversized_workflows_are_rejected(self) -> None:

        with pytest.raises(DesktopError):
            Workflow(
                name="too-big",
                steps=tuple(Step(tool="echo") for _ in range(MAX_STEPS + 1)),
            )

    def test_nested_steps_may_not_nest_further(self) -> None:
        """
        Fallback and rollback are one level deep so a workflow's worst-case
        duration stays computable.
        """

        with pytest.raises(DesktopError):
            Step.from_dict(
                {
                    "tool": "echo",
                    "fallback": {"tool": "echo", "fallback": {"tool": "echo"}},
                }
            )

    def test_step_serialisation_omits_argument_values(self) -> None:
        """
        Arguments can hold a password the user was pasting. The log sinks retain
        for weeks, so results carry argument *names* only.
        """

        payload = Step(
            tool="type_text",
            arguments={"text": "hunter2", "interval": 0.01},
        ).to_dict()

        assert payload["argument_names"] == ["interval", "text"]
        assert "hunter2" not in repr(payload)


# ==============================================================
# Dry run
# ==============================================================


class TestDryRun:

    @pytest.mark.asyncio
    async def test_validation_executes_nothing(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        The whole point of the dry run. A validation pass that touched the
        machine would be worse than no validation, because a model would reach
        for it precisely when it was unsure.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "check",
                    "dry_run": True,
                    "steps": [
                        {"tool": "echo", "arguments": {"value": "hi"}},
                        {"tool": "doomed"},
                    ],
                }
            )
        )

        assert result.status is ExecutionStatus.VALIDATED
        assert result.dry_run is True
        assert all(step.status is StepStatus.VALIDATED for step in result.steps)
        assert (calls.ok, calls.doomed) == (0, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "step, expected_fragment",
        [
            ({"tool": "no_such_tool"}, "unknown tool"),
            ({"tool": "echo", "arguments": {"nope": 1}}, "arguments rejected"),
            (
                {"tool": "echo", "verify": {"method": "telepathy", "expected": "x"}},
                "unknown verification method",
            ),
            (
                {"tool": "echo", "recovery": ["settle", "wibble"]},
                "unknown recovery strategy",
            ),
            (
                {"tool": "echo", "fallback": {"tool": "no_such_tool"}},
                "fallback step invalid",
            ),
        ],
        ids=["tool", "arguments", "method", "recovery", "fallback"],
    )
    async def test_each_class_of_mistake_is_caught(
        self,
        engine: AutomationEngine,
        step: dict,
        expected_fragment: str,
    ) -> None:
        """
        A bad recovery name matters more than it looks: it only surfaces at the
        moment the workflow was already in trouble, which is the worst possible
        time to discover a typo.
        """

        result = await engine.validate(
            Workflow.from_dict({"name": "check", "steps": [step]})
        )

        assert result.status is ExecutionStatus.FAILED
        assert result.steps[0].status is StepStatus.FAILED
        assert expected_fragment in (result.steps[0].error or "")

    @pytest.mark.asyncio
    async def test_a_disabled_tool_is_reported(
        self,
        engine: AutomationEngine,
        registry: ToolRegistry,
    ) -> None:

        registry.disable("echo")

        result = await engine.validate(
            Workflow.from_dict({"name": "check", "steps": [{"tool": "echo"}]})
        )

        assert "disabled" in (result.steps[0].error or "")


# ==============================================================
# Execution
# ==============================================================


class TestExecution:

    @pytest.mark.asyncio
    async def test_a_verified_step_succeeds(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "simple",
                    "steps": [
                        {
                            "tool": "echo",
                            "arguments": {"value": "abc"},
                            "verify": _matching_state("abc"),
                        }
                    ],
                }
            )
        )

        step = result.steps[0]

        assert result.success and result.status is ExecutionStatus.SUCCEEDED
        assert step.status is StepStatus.SUCCEEDED
        assert step.attempts == 1
        assert step.verification is not None and step.verification.verified
        assert calls.ok == 1

    @pytest.mark.asyncio
    async def test_a_step_that_needs_three_attempts_reports_recovered(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        RECOVERED is kept distinct from SUCCEEDED on purpose: a step that only
        worked on the third attempt is working *and* a signal that the automation
        is fragile. Collapsing the two would hide the second fact.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "retry",
                    "steps": [
                        {
                            "tool": "flaky",
                            "max_attempts": 4,
                            "recovery": ["dismiss_dialog"],
                        }
                    ],
                }
            )
        )

        step = result.steps[0]

        assert result.success
        assert step.status is StepStatus.RECOVERED
        assert step.attempts == 3
        assert calls.flaky == 3
        assert step.recoveries == 2
        assert calls.recovery == 2, "recovery strategy did not actually run"

    @pytest.mark.asyncio
    async def test_an_unmet_precondition_skips_rather_than_fails(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        "Close the dialog if a dialog is open" must not fail a workflow when no
        dialog was open.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "conditional",
                    "steps": [{"tool": "echo", "when": _failing_state()}],
                }
            )
        )

        assert result.success
        assert result.steps[0].status is StepStatus.SKIPPED
        assert calls.ok == 0

    @pytest.mark.asyncio
    async def test_contradicted_verification_fails_the_step(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        The tool returned cleanly and read-back disagreed. That is a failure: the
        alternative is a workflow that proceeds on a state nobody confirmed.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "lying-tool",
                    "steps": [
                        {"tool": "echo", "verify": _failing_state(), "max_attempts": 2}
                    ],
                }
            )
        )

        step = result.steps[0]

        assert not result.success
        assert step.status is StepStatus.FAILED
        assert step.attempts == 2 and calls.ok == 2
        assert "contradicted" in (step.error or "")


# ==============================================================
# Bounding
# ==============================================================


class TestBounding:

    @pytest.mark.asyncio
    async def test_attempts_stop_at_the_declared_budget(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "bounded",
                    "steps": [
                        {"tool": "doomed", "max_attempts": 3, "recovery": ["settle"]}
                    ],
                }
            )
        )

        assert calls.doomed == 3, f"tool ran {calls.doomed} times against a budget of 3"
        assert result.steps[0].attempts == 3
        assert not result.success

    @pytest.mark.asyncio
    async def test_recovery_is_capped_below_the_attempt_count(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        ``DESKTOP_RECOVERY_MAX_ATTEMPTS`` bounds repair independently of retries,
        so a step with a ten-attempt budget cannot run ten rounds of recovery.
        """

        from aetheros.config.config_loader import get_settings

        ceiling = get_settings().DESKTOP_RECOVERY_MAX_ATTEMPTS

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "capped",
                    "steps": [
                        {
                            "tool": "doomed",
                            "max_attempts": ATTEMPT_CEILING,
                            "recovery": ["settle"],
                        }
                    ],
                }
            )
        )

        assert result.steps[0].recoveries == ceiling

    @pytest.mark.asyncio
    async def test_unretryable_failures_are_not_retried(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        A misspelled tool name is rejected identically on attempt two. Retrying
        is pure latency, and it buries the real problem under identical log lines.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "typo",
                    "steps": [{"tool": "no_such_tool", "max_attempts": 5}],
                }
            )
        )

        assert result.steps[0].attempts == 1

    @pytest.mark.asyncio
    async def test_cancellation_propagates(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        Swallowing cancellation hangs shutdown. The engine logs what it had done
        and re-raises.
        """

        workflow = Workflow.from_dict(
            {"name": "slow", "steps": [{"tool": "hangs"}]}
        )

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(engine.execute(workflow), timeout=0.2)


# ==============================================================
# Fallback and rollback
# ==============================================================


class TestFallbackAndRollback:

    @pytest.mark.asyncio
    async def test_fallback_rescues_an_exhausted_step(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "plan-b",
                    "steps": [
                        {
                            "tool": "doomed",
                            "name": "plan-a",
                            "max_attempts": 2,
                            "fallback": {"tool": "echo", "name": "plan-b"},
                        }
                    ],
                }
            )
        )

        step = result.steps[0]

        assert result.success
        assert step.status is StepStatus.RECOVERED
        assert step.used_fallback
        assert calls.ok == 1

    @pytest.mark.asyncio
    async def test_stop_on_failure_halts_the_workflow(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "halt",
                    "steps": [
                        {"tool": "doomed", "max_attempts": 1},
                        {"tool": "echo", "name": "never-reached"},
                    ],
                }
            )
        )

        assert len(result.steps) == 1
        assert calls.ok == 0
        assert result.failed_step is not None
        assert result.failed_step.tool == "doomed"

    @pytest.mark.asyncio
    async def test_continue_on_failure_keeps_going(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "independent",
                    "steps": [
                        {
                            "tool": "doomed",
                            "max_attempts": 1,
                            "continue_on_failure": True,
                        },
                        {"tool": "echo"},
                    ],
                }
            )
        )

        assert len(result.steps) == 2
        assert calls.ok == 1
        assert not result.success, "a failed step must not report overall success"

    @pytest.mark.asyncio
    async def test_rollback_undoes_completed_steps_in_reverse(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        Reverse order because rollback steps are rarely independent: a workflow
        that created a folder and then a file inside it must remove the file
        first.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "transactional",
                    "rollback_on_failure": True,
                    "steps": [
                        {
                            "tool": "echo",
                            "name": "first",
                            "rollback": {"tool": "undo", "name": "undo-first"},
                        },
                        {
                            "tool": "echo",
                            "name": "second",
                            "rollback": {"tool": "undo", "name": "undo-second"},
                        },
                        {"tool": "doomed", "max_attempts": 1},
                    ],
                }
            )
        )

        assert not result.success
        assert [step.name for step in result.rollback] == [
            "undo-second",
            "undo-first",
        ]
        assert calls.undo == 2

    @pytest.mark.asyncio
    async def test_no_rollback_without_the_flag(
        self,
        engine: AutomationEngine,
        calls: Calls,
    ) -> None:
        """
        Rollback is opt-in. Undoing a user's work because a later step failed is
        a destructive default.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "no-rollback",
                    "steps": [
                        {
                            "tool": "echo",
                            "rollback": {"tool": "undo"},
                        },
                        {"tool": "doomed", "max_attempts": 1},
                    ],
                }
            )
        )

        assert result.rollback == ()
        assert calls.undo == 0


# ==============================================================
# The verification-error policy
# ==============================================================


class _BrokenVerifier:
    """
    A verifier whose checks always error, standing in for a missing service or an
    unavailable OCR backend.
    """

    methods = ("state",)

    async def verify(self, request: VerificationRequest, *, force: bool = False):
        return VerificationResult.errored(
            request.describe(),
            method=request.method,
            detail="clipboard service is not registered",
        )

    async def wait_until(self, request: VerificationRequest, **_):
        return await self.verify(request)


class TestUnverifiableActions:

    @pytest.mark.asyncio
    async def test_a_broken_check_does_not_trigger_a_retry(
        self,
        registry: ToolRegistry,
        calls: Calls,
    ) -> None:
        """
        The single most important policy decision in the engine.

        ``FAILED`` verification means something read the state back and it
        disagreed — grounds to retry. ``ERROR`` means the *check* broke. Retrying
        then would re-apply a side effect that may well have succeeded: a step
        that types a password twice, or clicks Buy twice, because the engine could
        not see the result.
        """

        executor = ToolExecutor(registry=registry)

        engine = AutomationEngine(
            executor=executor,
            registry=registry,
            checker=_BrokenVerifier(),  # type: ignore[arg-type]
            recovery=RecoveryRunner(executor=executor, registry=registry),
        )

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "unverifiable",
                    "steps": [
                        {
                            "tool": "echo",
                            "verify": _matching_state(),
                            "max_attempts": 5,
                        }
                    ],
                }
            )
        )

        step = result.steps[0]

        assert calls.ok == 1, f"side-effecting tool ran {calls.ok} times"
        assert step.status is StepStatus.SUCCEEDED
        assert step.verification is not None
        assert step.verification.verified is False
        assert step.verification.contradicted is False

    @pytest.mark.asyncio
    async def test_the_result_never_claims_verification_it_did_not_get(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        A step with no ``verify`` reports ``None``, not a passing verification.
        """

        result = await engine.execute(
            Workflow.from_dict({"name": "bare", "steps": [{"tool": "echo"}]})
        )

        payload = result.steps[0].to_dict()

        assert result.steps[0].verification is None
        assert payload.get("verified") in (None, False)


# ==============================================================
# Serialisation
# ==============================================================


class TestSerialisation:

    @pytest.mark.asyncio
    async def test_execution_results_are_json_ready(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        The payload goes to an LLM, so it has to survive json.dumps — an Enum or
        a dataclass left in place raises at the boundary, long after the workflow
        is over.
        """

        import json

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "serialise",
                    "steps": [
                        {"tool": "echo", "verify": _matching_state()},
                        {"tool": "doomed", "max_attempts": 1, "continue_on_failure": True},
                    ],
                }
            )
        )

        payload = json.loads(json.dumps(result.to_dict()))

        assert payload["workflow"] == "serialise"
        assert payload["success"] is False
        assert len(payload["steps"]) == 2

    @pytest.mark.asyncio
    async def test_long_values_are_truncated(
        self,
        engine: AutomationEngine,
    ) -> None:
        """
        A screenshot or OCR tool can return kilobytes. Twenty such steps would
        produce a result too large to hand back to the model.
        """

        result = await engine.execute(
            Workflow.from_dict(
                {
                    "name": "verbose",
                    "steps": [{"tool": "echo", "arguments": {"value": "x" * 5000}}],
                }
            )
        )

        assert len(str(result.steps[0].value)) < 600
