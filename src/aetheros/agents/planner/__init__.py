"""
Planner.

``GOAL -> the next action``, and nothing else. :mod:`~aetheros.agents.planner.actions`
holds the value types a decision is expressed in;
:mod:`~aetheros.agents.planner.planner` holds the service that produces them from
a provider response. Executing the actions belongs to the loop, which is not part
of this package yet.
"""

from .actions import (
    ERROR_INVALID_ARGUMENTS,
    ERROR_MALFORMED_CALL,
    ERROR_PROVIDER,
    ERROR_TERMINAL_STATE,
    ERROR_TOO_MANY_CALLS,
    ERROR_TOOL_DISABLED,
    ERROR_UNKNOWN_TOOL,
    ActionType,
    PlannedAction,
    PlanResult,
    RejectedToolCall,
)
from .goal import Goal
from .planner import (
    DEFAULT_MAX_TOOL_CALLS,
    TOOL_CALL_CEILING,
    AgentPlanner,
    PlannerConfig,
)

__all__ = [
    "DEFAULT_MAX_TOOL_CALLS",
    "ERROR_INVALID_ARGUMENTS",
    "ERROR_MALFORMED_CALL",
    "ERROR_PROVIDER",
    "ERROR_TERMINAL_STATE",
    "ERROR_TOOL_DISABLED",
    "ERROR_TOO_MANY_CALLS",
    "ERROR_UNKNOWN_TOOL",
    "TOOL_CALL_CEILING",
    "ActionType",
    "AgentPlanner",
    "Goal",
    "PlanResult",
    "PlannedAction",
    "PlannerConfig",
    "RejectedToolCall",
]
