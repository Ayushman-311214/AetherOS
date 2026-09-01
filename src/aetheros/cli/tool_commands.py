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

    # ==========================================================
    # Discovery
    # ==========================================================

    def list_tools(self) -> list[str]:
        """
        Return registered tool names.
        """

        return self._registry.names()

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
    
    # def get_args(self,name:str):
    #     return self._registry.args(name)
    
    def get_names(self) -> list[str]:
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
    ) -> Any:
        """
        Execute a registered AetherOS tool.

        Raises ToolError on failure; the CLI command that calls this reports the
        message to the user.
        """

        return await self._executor.execute(
            name,
            arguments or {},
        )
