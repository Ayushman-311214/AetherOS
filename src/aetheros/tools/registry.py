from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from collections.abc import Callable
from typing import Any


@dataclass(slots=True)
class ToolDefinition:
    """
    Metadata describing a tool.
    """

    name: str
    description: str
    function: Callable[..., Any]
    category: str = "general"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Recorded by the @tool decorator. The executor treats
    # inspect.iscoroutinefunction(function) as authoritative and uses this
    # only as a hint, so a hand-built ToolDefinition still executes correctly.
    is_async: bool = False

    # Per-tool execution budget, in seconds. None means "use the executor's
    # default", which is deliberately short so a wedged pyautogui call cannot
    # hang an agent.
    #
    # A single global timeout cannot serve both ends of this registry: a mouse
    # click that has not returned in 30s is broken, while a full-screen OCR pass
    # legitimately takes 90s+ on CPU. The default was silently failing every
    # vision tool — they worked correctly and were cancelled anyway — so the
    # slow ones declare their own budget rather than everything paying for them.
    timeout_seconds: float | None = None


class ToolRegistry:
    """
    Central registry for every tool in AetherOS.

    Responsibilities
    ----------------
    - Register tools
    - Remove tools
    - Find tools
    - Group by category
    - Enable / Disable tools
    """

    def __init__(self) -> None:

        self._tools: dict[str, ToolDefinition] = {}

        self._categories: dict[str, set[str]] = defaultdict(set)

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        tool: ToolDefinition,
    ) -> None:

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' already registered."
            )

        self._tools[tool.name] = tool

        self._categories[
            tool.category
        ].add(tool.name)

    def unregister(
        self,
        name: str,
    ) -> None:

        tool = self._tools.pop(name)

        self._categories[
            tool.category
        ].discard(name)

    # ==========================================================
    # Lookup
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> ToolDefinition:

        return self._tools[name]

    # def args(
    #     self,
    #     name:str
    # )->ToolDefinition:
    #     return self._tools[name,"description"]
    
    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._tools

    # ==========================================================
    # Listing
    # ==========================================================

    def all(self) -> list[ToolDefinition]:

        return list(self._tools.values())

    def names(self) -> list[str]:

        return sorted(self._tools)

    def categories(self) -> list[str]:

        return sorted(self._categories.keys())

    def by_category(
        self,
        category: str,
    ) -> list[ToolDefinition]:

        return [
            self._tools[name]
            for name in sorted(
                self._categories.get(category, [])
            )
        ]

    # ==========================================================
    # Enable / Disable
    # ==========================================================

    def enable(
        self,
        name: str,
    ) -> None:

        self.get(name).enabled = True

    def disable(
        self,
        name: str,
    ) -> None:

        self.get(name).enabled = False

    def enabled_tools(
        self,
    ) -> list[ToolDefinition]:

        return [
            tool
            for tool in self._tools.values()
            if tool.enabled
        ]

    # ==========================================================
    # Utilities
    # ==========================================================

    def clear(self) -> None:

        self._tools.clear()

        self._categories.clear()

    @property
    def count(self) -> int:

        return len(self._tools)

    def __contains__(
        self,
        name: str,
    ) -> bool:

        return self.exists(name)

    def __len__(self) -> int:

        return self.count

    def __iter__(self):

        return iter(self._tools.values())


# Global registry singleton
tool_registry = ToolRegistry()