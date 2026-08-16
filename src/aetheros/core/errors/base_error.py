from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ErrorContext:
    """
    Additional information about an error.
    """

    module: str | None = None
    operation: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseError(Exception):
    """
    Base exception for the entire AetherOS project.

    Every custom exception should inherit from this class.

    Example:
        raise BaseError(
            code="CORE_001",
            message="Configuration file not found.",
            hint="Create a .env file in the project root."
        )
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:

        self.code = code
        self.message = message
        self.hint = hint
        self.context = context or ErrorContext()
        self.cause = cause

        super().__init__(message)

    @property
    def error_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the exception into a structured dictionary.
        Useful for logging, APIs, and debugging.
        """

        return {
            "type": self.error_type,
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
            "module": self.context.module,
            "operation": self.context.operation,
            "details": self.context.details,
            "timestamp": self.context.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        output = f"[{self.code}] {self.message}"

        if self.hint:
            output += f"\nHint: {self.hint}"

        return output

    def __repr__(self) -> str:
        return (
            f"{self.error_type}("
            f"code={self.code!r}, "
            f"message={self.message!r})"
        )