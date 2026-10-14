"""
Workflow value objects — what to do, and what happened.

The automation engine is deliberately split from its data. Everything in this
module is an immutable description: a :class:`Step` says *what* to attempt and
*how to know it worked*, a :class:`Workflow` orders those steps, and
:class:`StepResult` / :class:`ExecutionResult` record what actually occurred.
The engine in :mod:`aetheros.desktop.automation.engine` holds all the behaviour.

That split is what makes a workflow safe to accept from an LLM. A step is plain
data — a tool name, an argument dict, a verification spec — so it can be
validated in full *before* anything with side effects runs, and the same
structure serves the dry-run path and the live path without a second code path
that might diverge from it.

Bounds are enforced here rather than in the engine, because a limit that lives
in the constructor cannot be forgotten at one of the engine's call sites:

* ``max_attempts`` is clamped to :data:`ATTEMPT_CEILING`. "Never create infinite
  retries" is not satisfied by a large number either — a model that asks for
  10,000 attempts at a click has misunderstood the problem, and honouring it
  would hold the machine for hours.
* ``wait_before`` / ``wait_after`` are clamped to ``DESKTOP_MAX_WAIT_SECONDS``.
  An unclamped sleep is the easiest way to wedge a tool, and it does not even
  need malice — ``wait_before: 3600`` reads perfectly reasonable to a model that
  is thinking in "wait for the installer to finish".
* A workflow is capped at :data:`MAX_STEPS`, and fallback/rollback steps may not
  nest further, so a workflow cannot describe an unbounded tree of work.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError
from ..verification.result import VerificationResult, VerificationStatus
from ..verification.strategy import VerificationRequest

MAX_STEPS = 50
"""
Most steps one workflow may contain.

Not a performance limit — 50 sequential desktop actions with verification is
already several minutes of wall clock. It exists so a malformed or runaway
generation cannot queue up an unbounded amount of real input to the machine.
"""

ATTEMPT_CEILING = 10
"""
Hard cap on retries per step, above whatever ``DESKTOP_STEP_MAX_ATTEMPTS`` says.
"""


class StepStatus(str, Enum):
    """
    What became of one step.

    ``RECOVERED`` is kept distinct from ``SUCCEEDED`` on purpose. A step that
    only worked on the third attempt, or only after its fallback ran, is a
    working step *and* a signal that the automation is fragile — collapsing the
    two would hide exactly the information needed to fix it.
    """

    SUCCEEDED = "succeeded"
    RECOVERED = "recovered"
    FAILED = "failed"
    SKIPPED = "skipped"
    VALIDATED = "validated"


class ExecutionStatus(str, Enum):
    """
    What became of the workflow as a whole.
    """

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    VALIDATED = "validated"


# ==============================================================
# Description
# ==============================================================


@dataclass(frozen=True, slots=True)
class Step:
    """
    One tool call, with the conditions around it.

    Fields
    ------
    name
        Label used in logs and results. Defaults to the tool name.
    tool
        Registered tool name. Resolved through the ToolRegistry at execution
        time; never a direct function reference, so a workflow cannot reach a
        callable the registry has not vetted.
    arguments
        Arguments passed to the tool.
    when
        Precondition. When present and not satisfied, the step is *skipped*
        rather than failed — this is how a workflow expresses "close the dialog
        if a dialog is open".
    verify
        Read-back that decides whether the step worked. Absent means the step is
        trusted on the tool's own report, which is honest but weaker; the tools
        themselves already verify internally, so this is the workflow-level
        check on top of that.
    timeout_seconds
        Budget for ``verify`` polling. ``0`` means check once.
    max_attempts
        Attempts for this step, including the first. Clamped.
    recovery
        Names of recovery strategies to run between attempts. See
        :mod:`aetheros.desktop.automation.recovery`.
    fallback
        A different step to try once, after all attempts are exhausted.
    rollback
        Step that undoes this one, run only if the workflow later fails and
        ``rollback_on_failure`` is set.
    continue_on_failure
        Whether the workflow proceeds when this step fails.
    """

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    name: str = ""
    when: VerificationRequest | None = None
    verify: VerificationRequest | None = None
    timeout_seconds: float = 0.0
    wait_before: float = 0.0
    wait_after: float = 0.0
    max_attempts: int | None = None
    recovery: tuple[str, ...] = ()
    fallback: Step | None = None
    rollback: Step | None = None
    continue_on_failure: bool = False

    def __post_init__(self) -> None:

        if not self.tool or not str(self.tool).strip():
            raise DesktopError(
                code="WORKFLOW_STEP_INVALID",
                message="A workflow step needs a 'tool' name.",
                hint='Example: {"tool": "get_screen_size"}',
            )

        object.__setattr__(self, "tool", str(self.tool).strip())

        if not self.name:
            object.__setattr__(self, "name", self.tool)

        if not isinstance(self.arguments, dict):
            raise DesktopError(
                code="WORKFLOW_STEP_INVALID",
                message=(
                    f"Step '{self.name}': arguments must be an object, got "
                    f"{type(self.arguments).__name__}."
                ),
                hint='Example: {"tool": "type_text", "arguments": {"text": "hi"}}',
            )

        ceiling = get_settings().DESKTOP_MAX_WAIT_SECONDS

        object.__setattr__(
            self,
            "wait_before",
            _clamp_seconds(self.wait_before, ceiling),
        )
        object.__setattr__(
            self,
            "wait_after",
            _clamp_seconds(self.wait_after, ceiling),
        )
        object.__setattr__(
            self,
            "timeout_seconds",
            _clamp_seconds(self.timeout_seconds, ceiling),
        )
        object.__setattr__(
            self,
            "recovery",
            tuple(
                str(item).strip().lower()
                for item in self.recovery
                if str(item).strip()
            ),
        )

    # ----------------------------------------------------------

    @property
    def attempt_budget(self) -> int:
        """
        Attempts to make, resolved against configuration and clamped.
        """

        requested = self.max_attempts

        if requested is None:
            requested = get_settings().DESKTOP_STEP_MAX_ATTEMPTS

        try:
            requested = int(requested)
        except (TypeError, ValueError):
            requested = 1

        return max(1, min(requested, ATTEMPT_CEILING))

    # ----------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        spec: dict[str, Any],
        *,
        allow_nested: bool = True,
    ) -> Step:
        """
        Build a step from a plain dict, as the ``run_workflow`` tool receives it.

        Unknown keys are rejected rather than ignored. A step that says
        ``{"tool": "click", "verify_that": {...}}`` clearly meant to verify
        something, and dropping the misspelled key would run an *unverified*
        click while reporting success — the precise failure mode this whole
        subsystem exists to prevent.

        :param allow_nested: ``False`` for a fallback or rollback step, which may
            not carry fallbacks or rollbacks of its own. Without that, a
            workflow could describe an arbitrarily deep tree of recovery work
            whose worst-case duration nobody can compute.
        """

        if not isinstance(spec, dict):
            raise DesktopError(
                code="WORKFLOW_STEP_INVALID",
                message=(
                    "A workflow step must be an object, got "
                    f"{type(spec).__name__}."
                ),
                hint='Example: {"tool": "get_screen_size"}',
            )

        allowed = {
            "tool",
            "arguments",
            "name",
            "when",
            "verify",
            "timeout_seconds",
            "wait_before",
            "wait_after",
            "max_attempts",
            "recovery",
            "fallback",
            "rollback",
            "continue_on_failure",
        }

        unknown = sorted(set(spec) - allowed)

        if unknown:
            raise DesktopError(
                code="WORKFLOW_STEP_INVALID",
                message=f"Unknown step field(s): {', '.join(unknown)}.",
                hint=f"Supported fields: {', '.join(sorted(allowed))}.",
            )

        nested: dict[str, Step | None] = {"fallback": None, "rollback": None}

        for key in nested:

            raw = spec.get(key)

            if raw is None:
                continue

            if not allow_nested:
                raise DesktopError(
                    code="WORKFLOW_STEP_INVALID",
                    message=(
                        f"A {key} step may not declare its own fallback or rollback."
                    ),
                    hint=(
                        "Keep recovery one level deep; use 'recovery' strategies "
                        "instead."
                    ),
                )

            nested[key] = cls.from_dict(raw, allow_nested=False)

        recovery = spec.get("recovery") or ()

        if isinstance(recovery, str):
            recovery = (recovery,)

        elif not isinstance(recovery, (list, tuple)):
            raise DesktopError(
                code="WORKFLOW_STEP_INVALID",
                message=(
                    "Step 'recovery' must be a list of strategy names, got "
                    f"{type(recovery).__name__}."
                ),
                hint='Example: {"recovery": ["settle", "release_modifiers"]}',
            )

        return cls(
            tool=spec.get("tool", ""),
            arguments=dict(spec.get("arguments") or {}),
            name=str(spec.get("name") or ""),
            when=_parse_condition(spec.get("when"), "when"),
            verify=_parse_condition(spec.get("verify"), "verify"),
            timeout_seconds=_as_float(
                spec.get("timeout_seconds"), "timeout_seconds"
            ),
            wait_before=_as_float(spec.get("wait_before"), "wait_before"),
            wait_after=_as_float(spec.get("wait_after"), "wait_after"),
            max_attempts=(
                None
                if spec.get("max_attempts") is None
                else int(_as_float(spec.get("max_attempts"), "max_attempts"))
            ),
            recovery=tuple(recovery),
            fallback=nested["fallback"],
            rollback=nested["rollback"],
            continue_on_failure=bool(spec.get("continue_on_failure", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Round-trippable description, used in logs and dry-run output.
        """

        payload: dict[str, Any] = {
            "name": self.name,
            "tool": self.tool,
        }

        # Argument *names* only. Values reach here from type_text and
        # set_clipboard, so they may hold a password the user was pasting; the
        # log sinks retain for weeks. Same rule the tool executor applies.
        if self.arguments:
            payload["argument_names"] = sorted(self.arguments)

        if self.when is not None:
            payload["when"] = self.when.describe()

        if self.verify is not None:
            payload["verify"] = self.verify.describe()

        if self.recovery:
            payload["recovery"] = list(self.recovery)

        if self.fallback is not None:
            payload["fallback"] = self.fallback.name

        if self.rollback is not None:
            payload["rollback"] = self.rollback.name

        payload["max_attempts"] = self.attempt_budget

        if self.continue_on_failure:
            payload["continue_on_failure"] = True

        return payload


@dataclass(frozen=True, slots=True)
class Workflow:
    """
    An ordered list of steps and the policy for running them.
    """

    name: str
    steps: tuple[Step, ...]
    description: str = ""
    stop_on_failure: bool = True
    rollback_on_failure: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:

        name = str(self.name or "").strip()

        if not name:
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message="A workflow needs a name.",
                hint="Name it after the outcome, e.g. 'save_chart_screenshot'.",
            )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "steps", tuple(self.steps))

        if not self.steps:
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message=f"Workflow '{name}' has no steps.",
                hint="Add at least one step.",
            )

        if len(self.steps) > MAX_STEPS:
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message=(
                    f"Workflow '{name}' has {len(self.steps)} steps; "
                    f"the limit is {MAX_STEPS}."
                ),
                hint="Split it into smaller workflows and run them in sequence.",
            )

    @classmethod
    def from_dict(cls, spec: dict[str, Any]) -> Workflow:
        """
        Build a workflow from a plain dict, as ``run_workflow`` receives it.
        """

        if not isinstance(spec, dict):
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message=f"A workflow must be an object, got {type(spec).__name__}.",
                hint='Example: {"name": "demo", "steps": [{"tool": "get_screen_size"}]}',
            )

        allowed = {
            "name",
            "steps",
            "description",
            "stop_on_failure",
            "rollback_on_failure",
            "dry_run",
        }

        unknown = sorted(set(spec) - allowed)

        if unknown:
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message=f"Unknown workflow field(s): {', '.join(unknown)}.",
                hint=f"Supported fields: {', '.join(sorted(allowed))}.",
            )

        raw_steps = spec.get("steps")

        if not isinstance(raw_steps, (list, tuple)):
            raise DesktopError(
                code="WORKFLOW_INVALID",
                message=(
                    "Workflow 'steps' must be a list, got "
                    f"{type(raw_steps).__name__}."
                ),
                hint='Example: {"steps": [{"tool": "get_screen_size"}]}',
            )

        return cls(
            name=str(spec.get("name") or ""),
            steps=tuple(Step.from_dict(item) for item in raw_steps),
            description=str(spec.get("description") or ""),
            stop_on_failure=bool(spec.get("stop_on_failure", True)),
            rollback_on_failure=bool(spec.get("rollback_on_failure", False)),
            dry_run=bool(spec.get("dry_run", False)),
        )

    def as_dry_run(self) -> Workflow:
        """
        The same workflow, validated instead of executed.
        """

        return replace(self, dry_run=True)

    def to_dict(self) -> dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "stop_on_failure": self.stop_on_failure,
            "rollback_on_failure": self.rollback_on_failure,
            "dry_run": self.dry_run,
        }


# ==============================================================
# Outcome
# ==============================================================


@dataclass(frozen=True, slots=True)
class StepResult:
    """
    What happened when one step ran.

    Carries the full field set PHASE 22 requires for an audit trail — tool,
    timestamps, duration, success, verification status, error, retry count and
    recovery count — so a workflow log can be reconstructed after the fact
    without re-running anything.
    """

    name: str
    tool: str
    status: StepStatus
    attempts: int = 0
    recoveries: int = 0
    value: Any = None
    error: str | None = None
    verification: VerificationResult | None = None
    duration_ms: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    used_fallback: bool = False

    @property
    def ok(self) -> bool:
        """
        Whether this step is a reason to keep going.

        ``SKIPPED`` counts: an unmet precondition means the step was not needed,
        not that it went wrong.
        """

        return self.status in (
            StepStatus.SUCCEEDED,
            StepStatus.RECOVERED,
            StepStatus.SKIPPED,
            StepStatus.VALIDATED,
        )

    def to_dict(self) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "name": self.name,
            "tool": self.tool,
            "status": self.status.value,
            "attempts": self.attempts,
            "duration_ms": round(self.duration_ms, 2),
        }

        if self.recoveries:
            payload["recoveries"] = self.recoveries

        if self.used_fallback:
            payload["used_fallback"] = True

        if self.verification is not None:
            payload["verification"] = self.verification.to_dict()

        if self.value is not None:
            payload["value"] = self.value

        if self.error:
            payload["error"] = self.error

        if self.started_at:
            payload["started_at"] = self.started_at

        if self.finished_at:
            payload["finished_at"] = self.finished_at

        return payload


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """
    What happened when a workflow ran.
    """

    execution_id: str
    workflow: str
    status: ExecutionStatus
    steps: tuple[StepResult, ...] = ()
    duration_ms: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    dry_run: bool = False
    error: str | None = None
    rollback: tuple[StepResult, ...] = ()

    @property
    def success(self) -> bool:
        return self.status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.VALIDATED,
        )

    @property
    def failed_step(self) -> StepResult | None:
        """
        The first step that failed, if any — what a caller actually wants to see.
        """

        for step in self.steps:
            if step.status is StepStatus.FAILED:
                return step

        return None

    def to_dict(self) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "execution_id": self.execution_id,
            "workflow": self.workflow,
            "status": self.status.value,
            "success": self.success,
            "dry_run": self.dry_run,
            "steps": [step.to_dict() for step in self.steps],
            "step_count": len(self.steps),
            "duration_ms": round(self.duration_ms, 2),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

        failed = self.failed_step

        if failed is not None:
            payload["failed_step"] = failed.name

        if self.error:
            payload["error"] = self.error

        if self.rollback:
            payload["rollback"] = [step.to_dict() for step in self.rollback]

        return payload


# ==============================================================
# Helpers
# ==============================================================


def new_execution_id() -> str:
    """
    Correlation id for one workflow run.

    Short enough to read in a terminal, random enough not to collide across
    concurrent runs. Every log line and every step result carries it, which is
    what makes an interleaved log readable after the fact.
    """

    return f"exec-{uuid.uuid4().hex[:12]}"


def utc_now() -> str:
    """
    ISO-8601 UTC timestamp.

    UTC rather than local time: these records are compared against market data
    and log lines from other subsystems, and a DST transition in a local-time
    audit trail silently reorders events.
    """

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def summarise_verification(
    verification: VerificationResult | None,
) -> str:
    """
    Verification status as one word, for structured log fields.
    """

    if verification is None:
        return "none"

    return verification.status.value


def _clamp_seconds(value: Any, ceiling: float) -> float:
    """
    Coerce a duration to a non-negative float no larger than ``ceiling``.
    """

    try:
        seconds = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0

    if seconds != seconds or seconds < 0.0:  # NaN or negative
        return 0.0

    return min(seconds, ceiling)


def _as_float(value: Any, field_name: str) -> float:

    if value is None:
        return 0.0

    try:
        return float(value)

    except (TypeError, ValueError) as exc:
        raise DesktopError(
            code="WORKFLOW_STEP_INVALID",
            message=f"Step '{field_name}' must be a number, got {value!r}.",
            cause=exc,
        ) from exc


def _parse_condition(
    spec: Any,
    field_name: str,
) -> VerificationRequest | None:

    if spec is None:
        return None

    if isinstance(spec, VerificationRequest):
        return spec

    if not isinstance(spec, dict):
        raise DesktopError(
            code="WORKFLOW_STEP_INVALID",
            message=(
                f"Step '{field_name}' must be a verification object, got "
                f"{type(spec).__name__}."
            ),
            hint=(
                'Example: {"'
                + field_name
                + '": {"method": "file", "mode": "exists", "target": "C:/tmp/a.txt"}}'
            ),
        )

    return VerificationRequest.from_spec(spec)


__all__ = [
    "ATTEMPT_CEILING",
    "MAX_STEPS",
    "ExecutionResult",
    "ExecutionStatus",
    "Step",
    "StepResult",
    "StepStatus",
    "VerificationStatus",
    "Workflow",
    "new_execution_id",
    "summarise_verification",
    "utc_now",
]
