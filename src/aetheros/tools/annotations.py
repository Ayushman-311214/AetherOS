"""
Annotation resolution shared by the schema generator and the validator.

Every AetherOS tool module starts with ``from __future__ import annotations``
(PEP 563), so ``inspect.signature(fn).parameters[x].annotation`` is the
*string* ``'int'`` rather than the class :class:`int`. Anything that compares
that value against real types — a ``TYPE_MAP`` lookup, an ``isinstance``
check — silently fails.

:func:`resolve_hints` performs the one resolution step both consumers need, so
the schema advertised to the model and the validation applied to the model's
arguments are derived from exactly the same view of the signature. Keeping this
in one place is what stops the two from drifting apart.
"""

from __future__ import annotations

import inspect
import types
import typing
from typing import Any, Union, get_args, get_origin

# Parameters that are never part of a tool's callable surface.
_SKIPPED_KINDS = (
    inspect.Parameter.VAR_POSITIONAL,   # *args
    inspect.Parameter.VAR_KEYWORD,      # **kwargs
)

_SKIPPED_NAMES = frozenset({"self", "cls"})


def public_parameters(
    signature: inspect.Signature,
) -> list[inspect.Parameter]:
    """
    Return the parameters a caller may actually supply.

    Drops ``self``/``cls`` and ``*args``/``**kwargs``: none of them can be
    expressed in a JSON-schema property list, and advertising them would
    invite the model to send arguments the function cannot accept.
    """

    return [
        parameter
        for name, parameter in signature.parameters.items()
        if name not in _SKIPPED_NAMES
        and parameter.kind not in _SKIPPED_KINDS
    ]


def resolve_hints(
    function: Any,
) -> dict[str, Any]:
    """
    Return ``{parameter_name: resolved_annotation}`` for ``function``.

    Uses :func:`typing.get_type_hints` to turn PEP 563 strings back into real
    objects. Resolution is best-effort: a tool annotated with a name that is
    not importable at runtime (a ``TYPE_CHECKING``-only import, a typo) must
    not take down schema generation for every other tool, so on failure the
    raw signature annotations are returned instead and unresolvable entries
    simply stay strings — treated downstream as "unknown type".

    ``return`` is excluded; it is not a parameter.
    """

    try:
        hints = typing.get_type_hints(function)

    except Exception:
        # NameError, and anything a pathological annotation may raise.
        hints = {}

    resolved: dict[str, Any] = {}

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return {
            name: hint
            for name, hint in hints.items()
            if name != "return"
        }

    for parameter in public_parameters(signature):

        if parameter.name in hints:
            resolved[parameter.name] = hints[parameter.name]

        elif parameter.annotation is not inspect.Parameter.empty:
            # get_type_hints() failed wholesale; fall back to whatever the
            # signature carries (possibly still a string).
            resolved[parameter.name] = parameter.annotation

        else:
            resolved[parameter.name] = inspect.Parameter.empty

    return resolved


def unwrap_optional(
    annotation: Any,
) -> Any:
    """
    Reduce ``X | None`` / ``Optional[X]`` to ``X``.

    A tool parameter typed ``str | None`` accepts a string, so both the schema
    and the validator should reason about ``str``. Unions with more than one
    non-``None`` member are returned unchanged — there is no single type to
    narrow them to.
    """

    origin = get_origin(annotation)

    # `X | None` reports types.UnionType; `Optional[X]` reports typing.Union.
    if origin is not Union and origin is not types.UnionType:
        return annotation

    non_none = [
        argument
        for argument in get_args(annotation)
        if argument is not type(None)
    ]

    if len(non_none) == 1:
        return non_none[0]

    return annotation


def is_unconstrained(
    annotation: Any,
) -> bool:
    """
    Whether ``annotation`` places no checkable constraint on a value.

    Covers the missing-annotation case and bare :data:`typing.Any`, plus any
    annotation that could not be resolved to a runtime type (still a string).
    ``isinstance(value, Any)`` raises :class:`TypeError`, and several real
    tools are annotated ``Any`` on purpose — ``clipboard.copy_image(image: Any)``
    takes an arbitrary image object — so these must be recognised explicitly
    rather than discovered through an exception.
    """

    return (
        annotation is inspect.Parameter.empty
        or annotation is Any
        or annotation is None
        or isinstance(annotation, str)
    )
