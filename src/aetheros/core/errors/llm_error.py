from __future__ import annotations

from core.errors.base_error import BaseError, ErrorContext


class LLMError(BaseError):
    """
    Base exception for all LLM-related errors.

    Examples:
        - Provider connection failed
        - Invalid API key
        - Model not found
        - Request timeout
        - Tool execution failed
        - Response parsing failed
        - Streaming interrupted
    """

    ERROR_PREFIX = "LLM"

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
            context = ErrorContext(module="llm")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )