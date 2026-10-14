"""
AetherOS Tool Framework

Public API for tool registration, discovery,
schema generation and execution.
"""

from .tool import tool

from .registry import (
    ToolDefinition,
    ToolRegistry,
    tool_registry,
)

from .executor import (
    ToolExecutionResult,
    ToolExecutor,
    tool_executor,
)

from .schema import (
    ToolSchemaGenerator,
    schema_generator,
)

from .validator import (
    ToolValidator,
    tool_validator,
)

from .discovery import (
    ToolDiscovery,
    tool_discovery,
)

__all__ = [
    # Decorator
    "tool",

    # Registry
    "ToolDefinition",
    "ToolRegistry",
    "tool_registry",

    # Executor
    "ToolExecutionResult",
    "ToolExecutor",
    "tool_executor",

    # Validator
    "ToolValidator",
    "tool_validator",

    # Discovery
    "ToolDiscovery",
    "tool_discovery",

    # Schema
    "ToolSchemaGenerator",
    "schema_generator",
]