"""
Tool schema generation.

These tests deliberately live in a module that starts with
``from __future__ import annotations`` — the same condition every real tool
module is under. That is what makes them a regression guard: with PEP 563
active, ``inspect.signature(fn).parameters['dx'].annotation`` is the *string*
``'int'``, and a TYPE_MAP lookup against it silently falls through to
``"string"``. Every numeric parameter in AetherOS was advertised to the model
as text because of it.
"""

from __future__ import annotations

import json
from typing import Any

from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.schema import ToolSchemaGenerator, schema_generator


# ==============================================================
# Sample tools
# ==============================================================


def move_mouse(dx: int, dy: int) -> None:
    """Move the mouse by a relative offset."""


def every_scalar(
    text: str,
    count: int,
    ratio: float,
    flag: bool,
) -> None:
    """One parameter per JSON scalar type."""


def containers(
    items: list[str],
    mapping: dict[str, Any],
    bare_list: list,
    tags: tuple[str, ...],
) -> None:
    """Container-typed parameters."""


def optionals(
    name: str | None = None,
    limit: int | None = None,
) -> None:
    """Optional parameters."""


def mixed_defaults(
    required_one: str,
    required_two: int,
    optional_one: int = 5,
) -> None:
    """Two required parameters and one with a default."""


def variadic(
    first: int,
    *args: int,
    **kwargs: Any,
) -> None:
    """Variadic parameters that are not expressible as schema properties."""


def unannotated(value, count: int) -> None:
    """One parameter with no annotation at all."""


def anything(payload: Any) -> None:
    """A parameter that genuinely accepts any object."""


def unresolvable(value: NotAnImportableType) -> None:  # noqa: F821
    """An annotation that cannot be resolved at runtime."""


class _Widget:

    def resize(self, width: int) -> None:
        """A method, whose `self` is not part of the callable surface."""


# ==============================================================
# Parameter types
# ==============================================================


class TestParameterTypes:

    def test_int_parameter_is_advertised_as_integer(self) -> None:
        """
        The regression. Before annotation resolution this reported "string".
        """

        schema = schema_generator.parameters(move_mouse)

        assert schema["properties"]["dx"] == {"type": "integer"}
        assert schema["properties"]["dy"] == {"type": "integer"}

    def test_every_scalar_type_maps_correctly(self) -> None:

        properties = schema_generator.parameters(
            every_scalar
        )["properties"]

        assert properties["text"] == {"type": "string"}
        assert properties["count"] == {"type": "integer"}
        assert properties["ratio"] == {"type": "number"}

        # bool is a subclass of int but a distinct TYPE_MAP key: a flag must
        # not be advertised as a number.
        assert properties["flag"] == {"type": "boolean"}

    def test_container_types_map_to_array_and_object(self) -> None:

        properties = schema_generator.parameters(
            containers
        )["properties"]

        assert properties["items"] == {"type": "array"}
        assert properties["bare_list"] == {"type": "array"}
        assert properties["tags"] == {"type": "array"}
        assert properties["mapping"] == {"type": "object"}

    def test_optional_annotations_are_unwrapped(self) -> None:

        properties = schema_generator.parameters(
            optionals
        )["properties"]

        assert properties["name"] == {"type": "string"}
        assert properties["limit"] == {"type": "integer"}

    def test_unannotated_parameter_falls_back_to_string(self) -> None:

        properties = schema_generator.parameters(
            unannotated
        )["properties"]

        assert properties["value"] == {"type": "string"}

        # The annotated sibling is unaffected.
        assert properties["count"] == {"type": "integer"}

    def test_any_falls_back_to_string(self) -> None:

        properties = schema_generator.parameters(
            anything
        )["properties"]

        assert properties["payload"] == {"type": "string"}

    def test_unresolvable_annotation_does_not_raise(self) -> None:
        """
        A tool annotated with a name that is not importable at runtime must
        still produce a schema, not take down generation for every other tool.
        """

        schema = schema_generator.parameters(unresolvable)

        assert schema["properties"]["value"] == {"type": "string"}


# ==============================================================
# Required parameters
# ==============================================================


class TestRequiredParameters:

    def test_parameters_without_defaults_are_required(self) -> None:

        schema = schema_generator.parameters(mixed_defaults)

        assert schema["required"] == [
            "required_one",
            "required_two",
        ]

    def test_parameters_with_defaults_are_not_required(self) -> None:

        schema = schema_generator.parameters(mixed_defaults)

        assert "optional_one" in schema["properties"]
        assert "optional_one" not in schema["required"]

    def test_optional_parameters_are_never_required(self) -> None:

        schema = schema_generator.parameters(optionals)

        assert schema["required"] == []

    def test_var_args_and_var_kwargs_are_excluded(self) -> None:
        """
        *args / **kwargs cannot be expressed as properties, and advertising
        them would invite calls the function cannot accept.
        """

        schema = schema_generator.parameters(variadic)

        assert set(schema["properties"]) == {"first"}
        assert schema["required"] == ["first"]

    def test_self_is_excluded(self) -> None:

        schema = schema_generator.parameters(_Widget.resize)

        assert set(schema["properties"]) == {"width"}
        assert schema["properties"]["width"] == {"type": "integer"}


# ==============================================================
# Schema envelope
# ==============================================================


class TestSchemaEnvelope:

    def test_openai_function_shape(self, define) -> None:

        definition = define(
            move_mouse,
            description="Move the mouse.",
        )

        schema = schema_generator.generate(definition)

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "move_mouse"
        assert schema["function"]["description"] == "Move the mouse."

        parameters = schema["function"]["parameters"]

        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False
        assert set(parameters["properties"]) == {"dx", "dy"}

    def test_generator_is_stateless(self, define) -> None:
        """
        Two generators must agree; the module singleton holds no per-tool state.
        """

        definition = define(every_scalar)

        assert (
            ToolSchemaGenerator().generate(definition)
            == schema_generator.generate(definition)
        )


# ==============================================================
# get_llm_tools
# ==============================================================


class TestGetLlmTools:

    def test_one_schema_per_enabled_tool(self, registry, define) -> None:

        registry.register(define(move_mouse))
        registry.register(define(every_scalar))

        schemas = get_llm_tools(registry)

        assert len(schemas) == 2

        assert {schema["function"]["name"] for schema in schemas} == {
            "move_mouse",
            "every_scalar",
        }

    def test_disabled_tools_are_not_offered(self, registry, define) -> None:

        registry.register(define(move_mouse))
        registry.register(define(every_scalar, enabled=False))

        schemas = get_llm_tools(registry)

        assert [schema["function"]["name"] for schema in schemas] == [
            "move_mouse",
        ]

    def test_empty_registry_yields_no_schemas(self, registry) -> None:

        assert get_llm_tools(registry) == []

    def test_schemas_are_json_serializable(self, registry, define) -> None:
        """
        Whatever is generated has to survive the trip to the provider.
        """

        registry.register(define(containers))
        registry.register(define(optionals))

        assert json.loads(json.dumps(get_llm_tools(registry)))
