"""
Agent policy layer.

The gate that sits before tool execution. It answers one question -- "may this
tool call run?" -- with :class:`PolicyDecision.ALLOW`,
:class:`PolicyDecision.DENY`, or :class:`PolicyDecision.REQUIRE_CONFIRMATION`,
and it runs nothing itself. :class:`PolicyConfig` carries the rules as data
(allow / deny / confirm sets, an iteration ceiling, an advisory timeout, and
argument-validation hooks); :class:`PolicyEngine` evaluates a call against them
and owns the one piece of mutable safety state, the emergency stop.

Deciding and doing are separate layers here on purpose: the same evaluation can
be logged, shown to a user, or replayed without a side effect riding along. The
:class:`~aetheros.agents.execution.ToolExecutionCoordinator` consults an engine
between resolving a tool and delegating to the executor, so a DENY or a
REQUIRE_CONFIRMATION never reaches ``ToolExecutor.execute_safe``.
"""

from .config import ArgumentValidator, PolicyConfig
from .decision import (
    POLICY_ALLOWED,
    POLICY_CONFIRMATION_REQUIRED,
    POLICY_DENIED_TOOL,
    POLICY_EMERGENCY_STOP,
    POLICY_FAILURE,
    POLICY_INVALID_ARGUMENTS,
    POLICY_ITERATION_LIMIT,
    POLICY_NOT_ALLOWED,
    PolicyDecision,
    PolicyEvaluation,
)
from .engine import PolicyEngine

__all__ = [
    "POLICY_ALLOWED",
    "POLICY_CONFIRMATION_REQUIRED",
    "POLICY_DENIED_TOOL",
    "POLICY_EMERGENCY_STOP",
    "POLICY_FAILURE",
    "POLICY_INVALID_ARGUMENTS",
    "POLICY_ITERATION_LIMIT",
    "POLICY_NOT_ALLOWED",
    "ArgumentValidator",
    "PolicyConfig",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyEvaluation",
]
