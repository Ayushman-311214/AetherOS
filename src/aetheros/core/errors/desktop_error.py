from __future__ import annotations

from .base_error import BaseError, ErrorContext


class DesktopError(BaseError):
    """
    Base exception for all desktop automation errors.

    Examples:
        - Mouse movement failed
        - Keyboard input failed
        - Window not found
        - Clipboard access failed
        - Screen capture failed
        - Process launch failed
        - File operation failed
    """

    ERROR_PREFIX = "DESKTOP"

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
            context = ErrorContext(module="desktop")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )