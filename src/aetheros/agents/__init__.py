"""
Agent layer.

Four pieces so far. :mod:`~aetheros.agents.state` is the explicit, serializable
record of one agent run; :mod:`~aetheros.agents.context` is the bounded,
deterministic projection of that record into the payload one iteration sends to
the model; :mod:`~aetheros.agents.planner` turns the model's answer into a typed
description of the next action; :mod:`~aetheros.agents.execution` carries one of
those actions to :class:`~aetheros.tools.executor.ToolExecutor` and writes the
outcome back into the state. The loop that drives the two of them in turn, and the
orchestrator above it, are not part of this package yet.
"""

from .context import (
    CHARS_CEILING,
    HISTORY_CEILING,
    RECORD_CEILING,
    AgentContext,
    ContextBuilder,
    ContextConfig,
    IterationInfo,
    context_builder,
    truncate,
)
from .execution import (
    AgentExecutionResult,
    ExecutionBatch,
    ExecutionConfig,
    ExecutionStatus,
    ToolExecutionCoordinator,
)
from .planner import (
    DEFAULT_MAX_TOOL_CALLS,
    ERROR_INVALID_ARGUMENTS,
    ERROR_MALFORMED_CALL,
    ERROR_PROVIDER,
    ERROR_TERMINAL_STATE,
    ERROR_TOO_MANY_CALLS,
    ERROR_TOOL_DISABLED,
    ERROR_UNKNOWN_TOOL,
    TOOL_CALL_CEILING,
    ActionType,
    AgentPlanner,
    Goal,
    PlannedAction,
    PlannerConfig,
    PlanResult,
    RejectedToolCall,
)
from .state import (
    DEFAULT_MAX_ITERATIONS,
    ITERATION_CEILING,
    MESSAGE_ROLES,
    STOP_CANCELLED,
    STOP_ERROR,
    STOP_FINAL_ANSWER,
    STOP_LOOP_GUARD,
    STOP_MAX_ITERATIONS,
    AgentState,
    AgentStatus,
    ErrorRecord,
    Message,
    Observation,
    ToolCallRecord,
    ToolResultRecord,
    new_state_id,
)

__all__ = [
    "CHARS_CEILING",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_MAX_TOOL_CALLS",
    "ERROR_INVALID_ARGUMENTS",
    "ERROR_MALFORMED_CALL",
    "ERROR_PROVIDER",
    "ERROR_TERMINAL_STATE",
    "ERROR_TOOL_DISABLED",
    "ERROR_TOO_MANY_CALLS",
    "ERROR_UNKNOWN_TOOL",
    "HISTORY_CEILING",
    "ITERATION_CEILING",
    "MESSAGE_ROLES",
    "RECORD_CEILING",
    "STOP_CANCELLED",
    "STOP_ERROR",
    "STOP_FINAL_ANSWER",
    "STOP_LOOP_GUARD",
    "STOP_MAX_ITERATIONS",
    "TOOL_CALL_CEILING",
    "ActionType",
    "AgentContext",
    "AgentExecutionResult",
    "AgentPlanner",
    "AgentState",
    "AgentStatus",
    "ContextBuilder",
    "ContextConfig",
    "ErrorRecord",
    "ExecutionBatch",
    "ExecutionConfig",
    "ExecutionStatus",
    "Goal",
    "IterationInfo",
    "Message",
    "Observation",
    "PlanResult",
    "PlannedAction",
    "PlannerConfig",
    "RejectedToolCall",
    "ToolCallRecord",
    "ToolExecutionCoordinator",
    "ToolResultRecord",
    "context_builder",
    "new_state_id",
    "truncate",
]
