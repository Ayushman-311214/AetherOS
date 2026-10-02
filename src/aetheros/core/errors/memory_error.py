from __future__ import annotations

from .base_error import BaseError, ErrorContext


class MemoryError(BaseError):
    """
    Base class for every AetherOS Memory subsystem error.

    Mirrors the other domain errors (LLMError, ToolError, MarketDataError):
    a thin BaseError subclass so callers can `except MemoryError` to catch
    anything the memory layer raises, while each failure keeps a stable code
    and a useful hint (CLAUDE.md section 20).
    """

    def __init__(
        self,
        *,
        code: str = "MEMORY_000",
        message: str,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class MemoryStorageError(MemoryError):
    """A persistence operation (SQLite read/write/migration) failed."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code="MEMORY_STORAGE",
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class MemoryNotFoundError(MemoryError):
    """A memory addressed by id/key does not exist."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code="MEMORY_NOT_FOUND",
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class MemoryValidationError(MemoryError):
    """A memory failed validation before being written."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code="MEMORY_VALIDATION",
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class EmbeddingError(MemoryError):
    """An embedding provider failed to produce a vector."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code="MEMORY_EMBEDDING",
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class MemoryRetrievalError(MemoryError):
    """The retrieval pipeline failed to assemble a result."""

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code="MEMORY_RETRIEVAL",
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )
