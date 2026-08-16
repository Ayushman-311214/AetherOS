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
        print(
            f"[DEBUG TOOL] Creating ToolDefinition: "
            f"{tool_name}"
        )
        definition = ToolDefinition(
            name=tool_name,
            description=tool_description,
            function=function,
            category=category,
            enabled=enabled,
            tags=tags or [],
            metadata=metadata or {},
            # is_async=inspect.iscoroutinefunction(function),
            # module=function.__module__,
            # qualname=function.__qualname__,
        )
        print(
            f"[DEBUG TOOL] Registering: {tool_name}"
        )
        tool_registry.register(definition)
        print(
            f"[DEBUG TOOL] Registered successfully: "
            f"{tool_name}"
        )
        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            return await function(*args, **kwargs)

        @wraps(function)
        def sync_wrapper(*args, **kwargs):

            return function(*args, **kwargs)

        inspect.getdoc(function)
        # inspect.iscoroutinefunction(function)
        # if inspect.iscoroutinefunction(function):
        #     return async_wrapper

        return sync_wrapper

    return decorator