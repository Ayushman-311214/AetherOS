from __future__ import annotations

import inspect
from typing import Any
import inspect
from ..core.errors.tool_error import ToolError
from ..core.logging import get_logger

from .registry import ToolDefinition, ToolRegistry, tool_registry


class ToolExecutor:
    """
    Executes registered AetherOS tools.
    """

    def __init__(
        self,
        registry: ToolRegistry = tool_registry,
    ) -> None:

        self._registry = registry

        self._logger = get_logger("tool_executor")

    # ==========================================================
    # Public
    # ==========================================================

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a registered tool.
        """

        arguments = arguments or {}
        print(f"[DEBUG TOOLEXECUTOR] arguments : {arguments}")
        tool = self._registry.get(name)

        print(f"[DEBUG TOOLEXECUTOR] Tool : {tool}")


        if not tool.enabled:
            raise ToolError(
                f"Tool '{name}' is disabled."
            )

        self._logger.info(
            "Executing tool '%s'",
            name,
        )

        try:

            return await self._invoke(
                tool,
                arguments,
            )

        except Exception as exc:

            self._logger.exception(
                "Tool '%s' failed.",
                name,
            )

            raise RuntimeError(
                f"Tool '{name}' failed."
            ) from exc

    # ==========================================================
    # Internal
    # ==========================================================

    async def _invoke(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> Any:
        result =await tool.function(**arguments)
        print(f"[DEBUG EXECUTOR] reult : {result}")
        if inspect.isawaitable(result):
            return await result

        return result
        # if tool.is_async:

        #     return await tool.function(
        #         **arguments
        #     )

        # return tool.function(
        #     **arguments
        # )


tool_executor = ToolExecutor()