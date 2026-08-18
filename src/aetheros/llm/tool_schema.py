from __future__ import annotations

from ..tools.registry import (
    tool_registry,
)
from ..tools.schema import (
    schema_generator,
)


def get_llm_tools() -> list[dict]:
    """
    Return schemas for all enabled AetherOS tools.
    """

    return [
        schema_generator.generate(tool)
        for tool in tool_registry.enabled_tools()
    ]