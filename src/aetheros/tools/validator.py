from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from ..core.errors.tool_error import ToolError
from .annotations import (
    is_unconstrained,
    public_parameters,
    resolve_hints,
    unwrap_optional,
)
from .registry import ToolDefinition


class ToolValidator:
    """
    Validates tool arguments before execution.

    Arguments arriving from an LLM are untrusted: the model may invent a
    parameter, omit a required one, or send a string where a number is
    required. Validating here means a bad tool call becomes a message the
    model can read and correct, instead of a ``TypeError`` from deep inside a
    desktop backend.
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

        Raises
        ------
        ToolError
            If an argument is unknown, required-but-missing, or of the
            wrong type.
        """

        signature = inspect.signature(tool.function)

        hints = resolve_hints(tool.function)

        self._check_unknown_arguments(
            signature,
            arguments,
        )

        self._check_required_arguments(
            signature,
            arguments,
        )

        self._check_argument_types(
            hints,
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

        for parameter in public_parameters(signature):

            if (
                parameter.default is inspect.Parameter.empty
                and parameter.name not in arguments
            ):
                raise ToolError(
                    f"Missing required argument "
                    f"'{parameter.name}'."
                )

    # ==========================================================
    # Unknown Arguments
    # ==========================================================

    def _check_unknown_arguments(
        self,
        signature: inspect.Signature,
        arguments: dict[str, Any],
    ) -> None:

        # A **kwargs parameter means the function accepts anything.
        accepts_extra = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )

        if accepts_extra:
            return

        allowed = {
            parameter.name
            for parameter in public_parameters(signature)
        }

        for key in arguments:

            if key not in allowed:

                raise ToolError(
                    f"Unknown argument '{key}'. "
                    f"Expected one of: "
                    f"{', '.join(sorted(allowed)) or 'none'}."
                )

    # ==========================================================
    # Type Validation
    # ==========================================================

    def _check_argument_types(
        self,
        hints: dict[str, Any],
        arguments: dict[str, Any],
    ) -> None:

        for name, value in arguments.items():

            annotation = hints.get(
                name,
                inspect.Parameter.empty,
            )

            if is_unconstrained(annotation):
                continue

            if not self._matches(
                value,
                annotation,
            ):
                raise ToolError(
                    f"Invalid type for '{name}'. "
                    f"Expected {self._describe(annotation)}, "
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

        annotation = unwrap_optional(annotation)

        # `X | None` narrowed to X above; an unresolvable or Any annotation
        # constrains nothing.
        if is_unconstrained(annotation):
            return True

        if value is None:
            # Only reachable when the annotation was not Optional.
            return False

        origin = get_origin(annotation)

        if origin is None:

            return self._matches_plain(
                value,
                annotation,
            )

        if origin in (list, set, frozenset, tuple, dict):
            return isinstance(value, origin)

        args = get_args(annotation)

        if args:
            # A union of concrete types: any member may match.
            return any(
                self._matches(value, argument)
                for argument in args
            )

        return True

    def _matches_plain(
        self,
        value: Any,
        annotation: Any,
    ) -> bool:
        """
        isinstance check with the numeric-tower adjustments JSON requires.
        """

        if not isinstance(annotation, type):
            # Something exotic (a TypeVar, a special form). Not checkable.
            return True

        # `bool` is a subclass of `int`, so a plain isinstance check would let
        # True through for an `int` parameter — and `click(button=True)` is not
        # what the model meant.
        if annotation is int:
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        # JSON has one number type: a `float` parameter legitimately receives
        # `5` rather than `5.0`.
        if annotation is float:
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        if annotation is bool:
            return isinstance(value, bool)

        try:
            return isinstance(value, annotation)

        except TypeError:
            # Not a checkable runtime type; do not block execution on it.
            return True

    # ==========================================================
    # Reporting
    # ==========================================================

    def _describe(
        self,
        annotation: Any,
    ) -> str:
        """
        Human-readable type name for an error message the model will read.
        """

        return getattr(
            annotation,
            "__name__",
            str(annotation),
        )


tool_validator = ToolValidator()
