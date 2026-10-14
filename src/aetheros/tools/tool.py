from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable

from .registry import (
    ToolDefinition,
    tool_registry,
)


def tool(
    *,
    name: str | None = None,
    description: str | None = None,
    category: str = "general",
    enabled: bool = True,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
):
    """
    Decorator used to register a function as an AetherOS tool.

    Example:
        @tool(
            category="desktop",
            description="Move mouse"
        )
        def move_mouse(x, y):
            ...

    ``timeout_seconds`` overrides the executor's default budget for this tool
    alone. Set it only where the work is genuinely slow — full-screen OCR, model
    loading — never to paper over a tool that hangs.
    """

    def decorator(
        function: Callable[..., Any],
    ) -> Callable[..., Any]:

        tool_name = name or function.__name__

        tool_description = (
            description
            or inspect.getdoc(function)
            or ""
        )

        is_async = inspect.iscoroutinefunction(function)

        # `function` is the raw, undecorated callable on purpose. The executor
        # calls it directly, and both the schema generator and the validator
        # resolve its annotations with typing.get_type_hints() — which
        # evaluates them against the *defining* module's globals. Storing a
        # wrapper defined in this module would resolve them here instead and
        # raise NameError for every tool.
        definition = ToolDefinition(
            name=tool_name,
            description=tool_description,
            function=function,
            category=category,
            enabled=enabled,
            tags=tags or [],
            metadata=metadata or {},
            is_async=is_async,
            timeout_seconds=timeout_seconds,
        )

        tool_registry.register(definition)

        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            return await function(*args, **kwargs)

        @wraps(function)
        def sync_wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        # Return a wrapper of the same kind as the wrapped function, so that
        # `inspect.iscoroutinefunction()` on the decorated name stays truthful
        # for any caller that imports the tool directly.
        if is_async:
            return async_wrapper

        return sync_wrapper

    return decorator