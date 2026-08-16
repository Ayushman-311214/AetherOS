from __future__ import annotations

import inspect
from typing import Any, get_origin, get_args

from ..core.errors.tool_error import ToolError
from .registry import ToolDefinition


class ToolValidator:
    """
    Validates tool arguments before execution.
    """

    # ==========================================================
    # Public
    # ==========================================================

    def validate(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
    ) -> None:
        """
        Validate arguments against the tool signature.
        """

        signature = inspect.signature(tool.function)

        self._check_unknown_arguments(
            signature,
            arguments,
        )

        self._check_required_arguments(
            signature,
            arguments,
        )

        self._check_argument_types(
            signature,
            arguments,
        )

    # ==========================================================
    # Required Arguments
    # ==========================================================

    def _check_required_arguments(
        self,
        signature: inspect.Signature,
        arguments: dict[str, Any],
    ) -> None:

        for name, parameter in signature.parameters.items():

            if (
                parameter.default is inspect._empty
                and name not in arguments
            ):
                raise ToolError(
                    f"Missing required argument '{name}'."
                )

    # ==========================================================
    # Unknown Arguments
    # ==========================================================

    def _check_unknown_arguments(
        self,
        signature: inspect.Signature,
        arguments: dict[str, Any],
    ) -> None:

        allowed = set(signature.parameters.keys())

        for key in arguments:

            if key not in allowed:

                raise ToolError(
                    f"Unknown argument '{key}'."
                )

    # ==========================================================
    # Type Validation
    # ==========================================================

    def _check_argument_types(
        self,
        signature: inspect.Signature,
        arguments: dict[str, Any],
    ) -> None:

        for name, value in arguments.items():

            annotation = signature.parameters[
                name
            ].annotation

            if annotation is inspect._empty:
                continue

            if not self._matches(
                value,
                annotation,
            ):
                raise ToolError(
                    f"Invalid type for '{name}'. "
                    f"Expected {annotation}, "
                    f"got {type(value).__name__}."
                )

    # ==========================================================
    # Type Matching
    # ==========================================================

    def _matches(
        self,
        value: Any,
        annotation: Any,
    ) -> bool:

        origin = get_origin(annotation)

        if origin is None:

            try:
                return isinstance(
                    value,
                    annotation,
                )

            except TypeError:
                return True

        if origin is list:

            return isinstance(
                value,
                list,
            )

        if origin is dict:

            return isinstance(
                value,
                dict,
            )

        if origin is tuple:

            return isinstance(
                value,
                tuple,
            )

        if origin is set:

            return isinstance(
                value,
                set,
            )

        if origin is Any:

            return True

        args = get_args(annotation)

        if args:

            return isinstance(
                value,
                args[0],
            )

        return True


tool_validator = ToolValidator()