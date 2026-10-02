"""
The DEVELOPMENT-mode ``tools`` CLI command.

These sample tools deliberately live in a module under
``from __future__ import annotations`` (PEP 563) -- the same condition every
real tool module is under. That is what makes them a regression guard: without
annotation resolution ``inspect.signature(fn).parameters['x'].annotation`` is
the *string* ``'int'``, and the rendered signature would carry that raw source
instead of a resolved type.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.cli.commands import CommandRegistry
from aetheros.cli.tool_commands import ToolCommandService


# ==============================================================
# Sample tools
# ==============================================================


def move_mouse(x: int, y: int) -> None:
    """Move the mouse to an absolute position."""


def move_mouse_relative(dx: int, dy: int) -> None:
    """Move the mouse by an offset."""


def click(button: str = "left", clicks: int = 1) -> None:
    """Click a mouse button."""


def capture_screen() -> None:
    """Capture the screen."""


def variadic(first: int, *args: int, **kwargs: Any) -> None:
    """Variadic parameters that are not part of the callable surface."""


def optional_arg(name: str | None = None) -> None:
    """A parameter with an optional annotation."""


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def commands(registry, define):
    """
    A CommandRegistry wired to an isolated tool registry, with a known set of
    tools registered.
    """

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(move_mouse_relative, category="desktop"))
    registry.register(define(click, category="desktop"))
    registry.register(define(capture_screen, category="vision"))
    registry.register(define(variadic, category="test"))
    registry.register(define(optional_arg, category="test"))

    service = ToolCommandService(registry)

    return CommandRegistry(service)


# ==============================================================
# Rendering
# ==============================================================


class TestToolsCommand:

    def test_required_arguments_render_with_types(self, commands) -> None:

        output = commands._tools([])

        assert "move_mouse(x: int, y: int)" in output
        assert "move_mouse_relative(dx: int, dy: int)" in output

    def test_optional_arguments_render_their_defaults(self, commands) -> None:

        output = commands._tools([])

        assert 'click(button: str = "left", clicks: int = 1)' in output

    def test_no_argument_tool_renders_empty_parentheses(self, commands) -> None:

        output = commands._tools([])

        assert "capture_screen()" in output

    def test_var_args_and_kwargs_are_excluded(self, commands) -> None:
        """
        *args / **kwargs are not part of a tool's callable surface and must not
        appear in the rendered signature.
        """

        output = commands._tools([])

        assert "variadic(first: int)" in output
        assert "*args" not in output
        assert "**kwargs" not in output

    def test_optional_annotation_is_rendered(self, commands) -> None:

        output = commands._tools([])

        # The exact union spelling varies by Python version; the parameter name,
        # its type, and its default must all be present.
        assert "optional_arg(" in output
        assert "name" in output
        assert "= None" in output

    def test_descriptions_are_not_shown(self, commands) -> None:
        """
        Only ``name(args)`` -- never the tool's docstring/description.
        """

        output = commands._tools([])

        assert "Move the mouse to an absolute position." not in output
        assert "Click a mouse button." not in output

    def test_header_is_present(self, commands) -> None:

        output = commands._tools([])

        assert "Available Tools" in output

    def test_newly_registered_tool_appears_automatically(
        self,
        registry,
        define,
        commands,
    ) -> None:
        """
        The list is read live from the registry, so a tool registered after the
        command was built still shows up.
        """

        def scroll(amount: int) -> None:
            """Scroll the mouse wheel."""

        registry.register(define(scroll, category="desktop"))

        output = commands._tools([])

        assert "scroll(amount: int)" in output

    def test_not_connected_when_no_service(self) -> None:

        commands = CommandRegistry(tool_service=None)

        output = commands._tools([])

        assert "NOT CONNECTED" in output

    def test_empty_registry_reports_no_tools(self, registry) -> None:

        service = ToolCommandService(registry)
        commands = CommandRegistry(service)

        output = commands._tools([])

        assert "No tools registered." in output
