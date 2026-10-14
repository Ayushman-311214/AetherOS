from __future__ import annotations

from .base_error import BaseError, ErrorContext


class BrowserError(BaseError):
    """
    Base exception for all browser-related errors.

    Examples:
        - Browser launch failed
        - Navigation timeout
        - Page not found
        - Element not found
        - Download failed
        - JavaScript execution failed
    """

    ERROR_PREFIX = "BROWSER"

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
            context = ErrorContext(module="browser")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )