"""
The automation tools — multi-step desktop work, exposed to the model.

Three tools, and the split between them is the point:

* ``run_workflow`` executes.
* ``validate_workflow`` checks the same specification without touching the
  machine. A model composing a ten-step workflow gets to find its typos before
  any of them become real mouse clicks. Validation shares the engine's code path
  rather than duplicating it, so a workflow that validates cannot fail live on a
  disagreement between two separate checkers.
* ``list_recovery_strategies`` reports what self-healing is available *right now*,
  which is not a constant: a strategy whose tools are not yet registered reports
  itself unavailable rather than pretending.

**Why these return an ExecutionResult rather than a ToolResult.** Every
single-action desktop tool returns
:class:`~aetheros.desktop.verification.result.ToolResult`, whose ``verified`` is
one boolean about one action. A workflow has one verification *per step*, and
collapsing twelve of them into a single boolean would either hide a failed
read-back or report the whole run unverified because one step could not be
checked. So the payload keeps ``success`` at the top level — the key a model
reliably reads — and each step carries its own verification underneath.
"""

from __future__ import annotations

from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger
from ...tools import tool
from ..verification.verifier import verifier
from .engine import automation_engine
from .recovery import describe_strategies, recovery_runner
from .workflow import MAX_STEPS, ATTEMPT_CEILING, Step, Workflow

WORKFLOW_TOOL_TIMEOUT_SECONDS = 300.0
"""
Executor budget for ``run_workflow``.

A backstop, not the operative limit. ``DESKTOP_WORKFLOW_TIMEOUT_SECONDS`` is what
actually bounds a run, and the engine enforces it itself so that hitting it
returns a complete result instead of being killed mid-step. This sits above that
value purely so the executor never fires first — being killed by the executor
would discard every step result the engine had already collected, which is the
one thing a caller needs after a workflow overruns.

Deliberately a module constant rather than ``get_settings()``: the decorator
below is evaluated at import, before ``.env`` is read, so a settings lookup here
would pin the wrong number.
"""

_logger = get_logger("desktop.automation.tools")


# ==============================================================
# Description helpers
# ==============================================================


def _step_reference() -> str:
    """
    The step schema, rendered for the tool description.

    Built from the live verification and recovery tables so the list the model is
    given cannot drift from what the engine will actually accept.
    """

    methods = ", ".join(f"'{name}'" for name in verifier.methods)
    strategies = ", ".join(f"'{name}'" for name in recovery_runner.names)

    return (
        "Each step is an object:\n"
        "  tool (required): name of a registered tool.\n"
        "  arguments: object of arguments for that tool.\n"
        "  name: label for logs and results; defaults to the tool name.\n"
        "  when: verification object treated as a PRECONDITION. If it does not "
        "hold the step is SKIPPED, not failed — use it for 'only close the "
        "dialog if a dialog is open'.\n"
        "  verify: verification object checked AFTER the tool runs. "
        f"{{'method': one of {methods}, 'expected': ..., 'target': ..., "
        "'mode': 'equals'|'contains'|'not_contains'|'starts_with'|'regex'|"
        "'greater_than'|'less_than', 'tolerance': int, 'region': [l,t,w,h]}}.\n"
        "  timeout_seconds: if > 0, poll 'verify' until it holds or the timeout "
        "expires. Use for anything that is not instant — a window appearing, an "
        "app finishing launch.\n"
        "  wait_before / wait_after: pause in seconds around the step.\n"
        f"  max_attempts: retries for this step (hard ceiling {ATTEMPT_CEILING}).\n"
        f"  recovery: list of repair strategies applied between attempts. "
        f"Available: {strategies}.\n"
        "  fallback: a single alternative step tried once if every attempt "
        "failed. Succeeding through it reports status 'recovered'.\n"
        "  rollback: a single step that undoes this one, run only if the "
        "workflow fails and rollback_on_failure is true.\n"
        "  continue_on_failure: keep going past this step's failure.\n"
    )


def _build(
    name: str,
    steps: list[dict[str, Any]],
    description: str,
    *,
    stop_on_failure: bool = True,
    rollback_on_failure: bool = False,
    dry_run: bool = False,
) -> Workflow:
    """
    Turn the model's JSON into a validated :class:`Workflow`.

    Parse errors are re-raised with the offending step's index attached. A bare
    "unknown key 'path'" is nearly useless against a twelve-step workflow; "step
    7 ('save file')" points straight at it.
    """

    if not isinstance(steps, list):
        raise DesktopError(
            code="WORKFLOW_INVALID",
            message=f"'steps' must be a list of step objects, got {type(steps).__name__}.",
            hint="Pass steps as [{'tool': 'move_mouse', 'arguments': {...}}, ...].",
        )

    parsed: list[Step] = []

    for index, spec in enumerate(steps, start=1):

        try:
            parsed.append(Step.from_dict(spec))

        except DesktopError as exc:
            label = ""

            if isinstance(spec, dict):
                label = str(spec.get("name") or spec.get("tool") or "")

            where = f"step {index}" + (f" ('{label}')" if label else "")

            raise DesktopError(
                code=exc.code,
                message=f"{where}: {exc.message}",
                hint=exc.hint,
                context=exc.context,
                cause=exc,
            ) from exc

    return Workflow(
        name=name,
        steps=tuple(parsed),
        description=description,
        stop_on_failure=stop_on_failure,
        rollback_on_failure=rollback_on_failure,
        dry_run=dry_run,
    )


# ==============================================================
# Tools
# ==============================================================


@tool(
    category="desktop.automation",
    timeout_seconds=WORKFLOW_TOOL_TIMEOUT_SECONDS,
    tags=["desktop", "automation", "workflow"],
    description=(
        "Run a multi-step desktop workflow, verifying each step before moving to "
        "the next. Prefer this over a chain of individual tool calls whenever "
        "steps depend on each other: it retries a failed step with bounded "
        "backoff, applies recovery strategies between attempts, can fall back to "
        "an alternative step, and can roll the whole thing back. Every step "
        "reports what it did and whether read-back confirmed it.\n\n"
        "A step whose 'verify' could not be evaluated reports success with "
        "verified=false rather than being retried — re-running an action that may "
        "already have happened is more dangerous than not confirming it.\n\n"
        "Set dry_run=true first for anything non-trivial: it validates every "
        "tool name, argument, verification method and recovery strategy against "
        "the live registry and executes nothing.\n\n" + _step_reference()
    ),
)
async def run_workflow(
    name: str,
    steps: list[dict[str, Any]],
    description: str = "",
    stop_on_failure: bool = True,
    rollback_on_failure: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute a workflow and return its full execution record.

    :param name: Label for this workflow, used in logs and the result.
    :param steps: The steps, in order. At most ``MAX_STEPS``.
    :param description: What the workflow is for. Recorded, not interpreted.
    :param stop_on_failure: Halt at the first failed step. Leave true unless the
        steps are genuinely independent — continuing past a failed step in a
        dependent sequence means every later step acts on a state nobody checked.
    :param rollback_on_failure: If the workflow fails, run the ``rollback`` step
        of each completed step, most recent first.
    :param dry_run: Validate everything and execute nothing.
    """

    workflow = _build(
        name,
        steps,
        description,
        stop_on_failure=stop_on_failure,
        rollback_on_failure=rollback_on_failure,
        dry_run=dry_run,
    )

    _logger.bind(
        workflow=workflow.name,
        steps=len(workflow.steps),
        dry_run=workflow.dry_run,
    ).info("run_workflow invoked.")

    result = await automation_engine.execute(workflow)

    return result.to_dict()


# ----------------------------------------------------------


@tool(
    category="desktop.automation",
    tags=["desktop", "automation", "workflow", "validation"],
    description=(
        "Check a desktop workflow without executing any of it. Verifies that "
        "every step's tool exists and is enabled, that its arguments would pass "
        "validation, that its verification methods are real, and that its "
        "recovery strategy names are spelled correctly. Returns a per-step "
        "verdict. Nothing on the machine is touched — no clicks, no keystrokes, "
        "no files. Use it before run_workflow for anything longer than two or "
        "three steps.\n\n" + _step_reference()
    ),
)
async def validate_workflow(
    name: str,
    steps: list[dict[str, Any]],
    description: str = "",
) -> dict[str, Any]:
    """
    Validate a workflow specification. Executes nothing.
    """

    workflow = _build(name, steps, description, dry_run=True)

    result = await automation_engine.validate(workflow)

    return result.to_dict()


# ----------------------------------------------------------


@tool(
    category="desktop.automation",
    tags=["desktop", "automation", "recovery"],
    description=(
        "List the self-healing strategies a workflow step can name in its "
        "'recovery' field, with what each one does and whether it is currently "
        "usable. A strategy reports available=false when the tools it needs are "
        "not registered in this build — naming it then is harmless but will not "
        "repair anything, so pick an available one."
    ),
)
def list_recovery_strategies() -> dict[str, Any]:
    """
    Report the recovery strategies and their current availability.
    """

    availability = recovery_runner.availability()
    descriptions = describe_strategies()

    return {
        "count": len(descriptions),
        "max_steps_per_workflow": MAX_STEPS,
        "max_attempts_per_step": ATTEMPT_CEILING,
        "strategies": [
            {
                "name": strategy,
                "available": availability.get(strategy, False),
                "description": descriptions[strategy],
            }
            for strategy in sorted(descriptions)
        ],
    }


__all__ = [
    "WORKFLOW_TOOL_TIMEOUT_SECONDS",
    "list_recovery_strategies",
    "run_workflow",
    "validate_workflow",
]
