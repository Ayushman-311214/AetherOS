from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from .annotations import (
    is_unconstrained,
    public_parameters,
    resolve_hints,
    unwrap_optional,
)
from .registry import ToolDefinition


class ToolSchemaGenerator:
    """
    Generates JSON schemas for LLM function calling.
    """

    TYPE_MAP = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # ==========================================================
    # Public API
    # ==========================================================

    def generate(
        self,
        tool: ToolDefinition,
    ) -> dict[str, Any]:

        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": self.parameters(
                    tool.function,
                ),
            },
        }

    # ==========================================================
    # Parameters
    # ==========================================================

    def parameters(
        self,
        function,
    ) -> dict[str, Any]:

        signature = inspect.signature(function)

        # Annotations are PEP 563 strings inside the tool modules; resolving
        # them is what makes `dx: int` advertise "integer" instead of
        # defaulting to "string".
        hints = resolve_hints(function)

        properties: dict[str, Any] = {}

        required: list[str] = []

        for parameter in public_parameters(signature):

            name = parameter.name

            properties[name] = self._parameter_schema(
                hints.get(name, parameter.annotation)
            )

            if parameter.default is inspect.Parameter.empty:
                required.append(name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    # ==========================================================
    # Internal
    # ==========================================================

    def _parameter_schema(
        self,
        annotation: Any,
    ) -> dict[str, Any]:

        # No usable annotation (missing, bare Any, or unresolvable): accept a
        # string rather than claiming a type the function does not require.
        if is_unconstrained(annotation):
            return {
                "type": "string"
            }

        annotation = unwrap_optional(annotation)

        if is_unconstrained(annotation):
            return {
                "type": "string"
            }

        origin = get_origin(annotation)

        if origin in (list, set, frozenset, tuple):

            return {
                "type": "array"
            }

        if origin is dict:

            return {
                "type": "object"
            }

        if origin is None:

            return {
                "type": self.TYPE_MAP.get(
                    annotation,
                    "string",
                )
            }

        args = get_args(annotation)

        if args:

            return {
                "type": self.TYPE_MAP.get(
                    args[0],
                    "string",
                )
            }

        return {
            "type": self.TYPE_MAP.get(
                annotation,
                "string",
            )
        }


schema_generator = ToolSchemaGenerator()
