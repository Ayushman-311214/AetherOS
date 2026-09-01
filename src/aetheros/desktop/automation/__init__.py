"""
Automation — multi-step desktop work with verification, retries and rollback.

The layering here is deliberate and worth keeping:

* :mod:`workflow` holds only immutable data — :class:`Step`, :class:`Workflow`
  and the result types. Every bound (``MAX_STEPS``, ``ATTEMPT_CEILING``, the wait
  clamps) is enforced in a constructor, so no engine call site can forget one and
  no unbounded workflow can exist as a value in the first place.
* :mod:`recovery` holds context-free repairs, expressed as ordinary tool calls.
* :mod:`engine` executes, and is the only part that has side effects.

``tools`` is **not** imported here. Importing it registers three tools in the
global registry, and a package import should not have that side effect — the
bootstrapper imports it explicitly alongside the other desktop tool modules, so
registration happens once, at a place where the ordering is visible.
"""

from .engine import (
    AutomationEngine,
    automation_engine,
)

from .recovery import (
    STRATEGIES,
    RecoveryAction,
    RecoveryOutcome,
    RecoveryRunner,
    RecoveryStrategy,
    describe_strategies,
    recovery_runner,
)

from .workflow import (
    ATTEMPT_CEILING,
    MAX_STEPS,
    ExecutionResult,
    ExecutionStatus,
    Step,
    StepResult,
    StepStatus,
    Workflow,
    new_execution_id,
)

__all__ = [
    # Engine
    "AutomationEngine",
    "automation_engine",

    # Workflow data
    "ATTEMPT_CEILING",
    "MAX_STEPS",
    "ExecutionResult",
    "ExecutionStatus",
    "Step",
    "StepResult",
    "StepStatus",
    "Workflow",
    "new_execution_id",

    # Recovery
    "STRATEGIES",
    "RecoveryAction",
    "RecoveryOutcome",
    "RecoveryRunner",
    "RecoveryStrategy",
    "describe_strategies",
    "recovery_runner",
]
