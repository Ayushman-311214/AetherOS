from __future__ import annotations

from .base_error import BaseError, ErrorContext


class AgentError(BaseError):
    """
    Base exception for all agent-layer errors.

    Raised for violations of the agent's own contract rather than for
    failures inside the work it delegates. A tool that fails is not an
    AgentError -- ToolExecutor already reports that as data so the model can
    recover from it. An agent asked to record a fourth iteration when its
    budget was three is an AgentError, because no downstream component can
    recover from a run whose own accounting is wrong.

    Examples:
        - A message with an unknown role
        - A tool message with no tool_call_id to answer
        - Advancing past the iteration budget
        - Recording a second outcome for a run that already finished
        - Restoring state from a payload that is missing its goal
    """

    ERROR_PREFIX = "AGENT"

    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:

        if not code.startswith(self.ERROR_PREFIX):
            code = f"{self.ERROR_PREFIX}_{code}"

        if context is None:
            context = ErrorContext(module="agents")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )
