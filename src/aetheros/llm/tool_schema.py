from __future__ import annotations

from ..tools.registry import (
    ToolRegistry,
    tool_registry,
)
from ..tools.schema import (
    ToolSchemaGenerator,
    schema_generator,
)


def get_llm_tools(
    registry: ToolRegistry = tool_registry,
    generator: ToolSchemaGenerator = schema_generator,
) -> list[dict]:
    """
    Return schemas for all enabled AetherOS tools.

    Both collaborators are injectable so the schema list can be built from an
    isolated registry in tests, without touching the process-wide singleton.
    The zero-argument call keeps working for existing callers.
    """

    return [
        generator.generate(tool)
        for tool in registry.enabled_tools()
    ]
