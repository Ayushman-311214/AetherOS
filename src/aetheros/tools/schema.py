from __future__ import annotations

import inspect
from typing import Any, get_origin, get_args

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

        properties: dict[str, Any] = {}

        required: list[str] = []

        for name, parameter in signature.parameters.items():

            annotation = parameter.annotation

            properties[name] = self._parameter_schema(
                annotation
            )

            if parameter.default is inspect._empty:
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

        if annotation is inspect._empty:
            return {
                "type": "string"
            }

        origin = get_origin(annotation)

        if origin is list:

            return {
                "type": "array"
            }

        if origin is dict:

            return {
                "type": "object"
            }

        if origin is tuple:

            return {
                "type": "array"
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