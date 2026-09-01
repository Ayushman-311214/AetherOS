from __future__ import annotations

from .base_error import BaseError, ErrorContext


class HUDError(BaseError):
    """
    Base exception for all HUD errors.

    Examples:
        - GUI toolkit unavailable
        - HUD process failed to start
        - Renderer initialization failed
    """

    ERROR_PREFIX = "HUD"

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
            context = ErrorContext(module="hud")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class HUDUnavailableError(HUDError):
    """
    The HUD cannot run in this environment.

    A missing GUI toolkit or headless session must never stop
    AetherOS itself, so callers should log and continue.
    """


class HUDProcessError(HUDError):
    """
    The HUD renderer process crashed or refused to start.
    """


__all__ = [
    "HUDError",
    "HUDProcessError",
    "HUDUnavailableError",
]
