from __future__ import annotations

from core.errors.base_error import BaseError, ErrorContext


class VisionError(BaseError):
    """
    Base exception for all vision-related errors.

    Examples:
        - Screen capture failed
        - OCR failed
        - Image loading failed
        - Object detection failed
        - Template matching failed
        - Model loading failed
        - UI element not detected
    """

    ERROR_PREFIX = "VISION"

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
            context = ErrorContext(module="vision")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )