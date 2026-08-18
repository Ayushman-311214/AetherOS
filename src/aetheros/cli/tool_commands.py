from __future__ import annotations

from typing import Any

from ..tools.registry import ToolRegistry, tool_registry
from ..tools.executor import ToolExecutor, tool_executor


class ToolCommandService:
    """
    Bridge between the AetherOS CLI and Tool Framework.
    """

    def __init__(
        self,
        registry: ToolRegistry = tool_registry,
        executor: ToolExecutor = tool_executor,
    ) -> None:

        self._registry = registry
        self._executor = executor

        print("[DEBUG TOOL SERVICE] Registry:", self._registry)
        print(
            "[DEBUG TOOL SERVICE] Count:",
            self._registry.count,
        )
        print(
            "[DEBUG TOOL SERVICE] Tools:",
            self._registry.names(),
        )

    # ==========================================================
    # Discovery
    # ==========================================================

    def list_tools(self) -> list[str]:
        """
        Return registered tool names.
        """

        print(
            "[DEBUG TOOL SERVICE] list_tools() called"
        )

        names = self._registry.names()

        print(
            "[DEBUG TOOL SERVICE] Registry names:",
            names,
        )

        return names

    def list_categories(self) -> list[str]:
        return self._registry.categories()

    def tools_by_category(
        self,
        category: str,
    ):
        return self._registry.by_category(category)

    # ==========================================================
    # Information
    # ==========================================================

    def get_tool(self, name: str):
        return self._registry.get(name)
    
    def get_names(self)->list[str]:
        return self._registry.names()
    
    def exists(self, name: str) -> bool:
        return self._registry.exists(name)

    def count(self) -> int:
        return self._registry.count

    # ==========================================================
    # Execution
    # ==========================================================

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> str:
        """
        Execute a registered AetherOS tool.
        """
        arguments = arguments or {}

        return await self._executor.execute(
            name,
            arguments or {},
        )
        return str(result)