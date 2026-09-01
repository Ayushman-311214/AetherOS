"""
Regression tests for the tool surface as it actually ships.

Every other test in tests/tools builds an isolated registry from local fixture
functions, which is right for testing registry mechanics but means a tool module
that fails to import is invisible to the suite. That is exactly how the audit
found two whole modules dead: `aetheros.desktop.screenshot.tools` raised
ModuleNotFoundError on a path that never existed, and `aetheros.browser.tools`
used absolute `from core.container import ...` imports, so 17 of 53 tools never
reached the registry — with a green suite throughout.

These tests import the real modules and assert on the real process-wide registry.
"""

from __future__ import annotations

import importlib
import inspect
from collections import Counter
from pathlib import Path

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.tools.annotations import resolve_hints
from aetheros.tools.registry import tool_registry
from aetheros.tools.schema import schema_generator

SRC = Path(__file__).resolve().parents[2] / "src"

SKIP_DIRS = {"__pycache__", ".cache", "logs", "tests", "scripts", "data"}


def _tool_modules() -> list[str]:
    """
    Every ``tools.py`` under the package, discovered from the filesystem.

    Discovered rather than listed: a hard-coded list is what let the two broken
    modules sit unnoticed, because a module nobody imports cannot fail loudly.
    """

    modules: list[str] = []

    for path in sorted((SRC / "aetheros").rglob("tools.py")):

        rel = path.relative_to(SRC)

        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        modules.append(".".join(rel.with_suffix("").parts))

    return modules


TOOL_MODULES = _tool_modules()


# ==============================================================
# Level 1 — import
# ==============================================================


class TestEveryToolModuleImports:

    def test_modules_were_discovered(self) -> None:
        """
        Guard the guard: a discovery bug that found nothing would make every
        other test in this file pass vacuously.
        """

        assert len(TOOL_MODULES) >= 6, TOOL_MODULES

    @pytest.mark.parametrize("module", TOOL_MODULES)
    def test_module_imports(self, module: str) -> None:
        """
        A tool module that cannot be imported registers nothing, and bootstrap
        swallows the failure into a log line nobody reads.
        """

        importlib.import_module(module)


# ==============================================================
# Level 2 — registration
# ==============================================================


class TestRegisteredToolSurface:
    """
    Asserts against the process-wide registry, which the @tool decorator
    populates at import time. Importing the modules is the arrangement.
    """

    @pytest.fixture(autouse=True)
    def _import_all(self) -> None:
        for module in TOOL_MODULES:
            importlib.import_module(module)

    def test_no_duplicate_names_across_modules(self) -> None:
        """
        ToolRegistry.register raises on a collision, so a duplicate name across
        two modules turns the *next* bootstrap into a hard startup failure —
        whichever module happens to be imported second.

        `screen_size` was defined in both desktop/screen/tools.py and
        desktop/screenshot/tools.py; it stayed latent only because the screenshot
        module was already dead on import.
        """

        counts = Counter(tool.name for tool in tool_registry.all())

        duplicates = {
            name: count
            for name, count in counts.items()
            if count > 1
        }

        assert not duplicates, f"duplicate tool names: {duplicates}"

    def test_every_expected_category_is_populated(self) -> None:
        """
        A category vanishing is the visible symptom of a module that stopped
        importing.
        """

        categories = set(tool_registry.categories())

        assert {
            "browser",
            "desktop.automation",
            "desktop.clipboard",
            "desktop.keyboard",
            "desktop.mouse",
            "desktop.screen",
            "desktop.verification",
            "vision",
        } <= categories, sorted(categories)

    def test_registry_is_not_empty(self) -> None:
        """
        The CLI prints "No tools registered." from an empty registry, and that
        message was reachable with the tool modules perfectly healthy.
        """

        assert tool_registry.count > 0

    def test_vision_tools_declare_a_budget_larger_than_the_default(self) -> None:
        """
        Every vision tool was unreachable in practice: a full-screen PaddleOCR
        pass measured 136s cold and 92s warm on CPU, against a 30s executor
        default, so all five ran correctly and reported a timeout.

        Asserted here rather than in the executor tests because the defect was in
        the *registration*, not the mechanism — the per-tool budget worked; no
        vision tool used it. A tool that quietly loses its override regresses
        straight back to a timeout, which reads like a broken subsystem.
        """

        default = get_settings().TOOL_TIMEOUT_SECONDS

        missing = [
            definition.name
            for definition in tool_registry.by_category("vision")
            if definition.timeout_seconds is None
            or definition.timeout_seconds <= default
        ]

        assert not missing, (
            f"vision tools without a budget above the {default}s default: {missing}"
        )

    def test_only_deliberately_slow_tools_raise_their_budget(self) -> None:
        """
        The other half of the same rule. A declared budget is an admission that
        the work is genuinely slow; spreading it to a mouse click or a clipboard
        read would let a wedged pyautogui call stall an agent for minutes with no
        way to tell "slow" from "hung".

        The allowlist is by name rather than by category so that adding a tool to
        an already-allowed category does not silently inherit the exemption. Each
        entry needs a reason:

        * ``run_workflow`` runs many steps in sequence. Its budget is a backstop
          above ``DESKTOP_WORKFLOW_TIMEOUT_SECONDS``, which the engine enforces
          itself — being killed by the executor instead would discard every step
          result already collected, which is exactly what a caller needs after a
          workflow overruns.
        """

        default = get_settings().TOOL_TIMEOUT_SECONDS

        allowed_categories = {"vision"}
        allowed_names = {"run_workflow"}

        raised = {
            definition.name: definition.category
            for definition in tool_registry.all()
            if definition.timeout_seconds is not None
            and definition.timeout_seconds > default
        }

        unexpected = {
            name: category
            for name, category in raised.items()
            if category not in allowed_categories and name not in allowed_names
        }

        assert not unexpected, f"unexpected raised budgets: {unexpected}"


# ==============================================================
# Level 3 — schema
# ==============================================================


class TestEveryRegisteredToolHasAUsableSchema:
    """
    The schema is the only thing the model sees. A tool whose schema is wrong is
    worse than a missing one: the model will call it and misread the failure.
    """

    @pytest.fixture(autouse=True)
    def _import_all(self) -> None:
        for module in TOOL_MODULES:
            importlib.import_module(module)

    def test_schemas_generate_for_every_tool(self) -> None:
        for definition in tool_registry.all():

            schema = schema_generator.generate(definition)

            function = schema["function"]

            assert function["name"] == definition.name
            assert function["description"], definition.name
            assert function["parameters"]["type"] == "object"

    def test_no_parameter_is_left_untyped(self) -> None:
        """
        Every tool module uses ``from __future__ import annotations``, so
        annotations arrive as PEP 563 strings and an unresolvable one degrades
        to a bare ``{}`` schema entry — which the model reads as "any JSON
        accepted", and which the validator cannot check either.

        A *resolved* ``Any`` is left alone: several tools mean it, notably
        ``copy_image(image: Any)``. What is asserted is that resolution
        succeeded, not that every type is narrow.
        """

        unresolved: list[str] = []

        for definition in tool_registry.all():

            for name, hint in resolve_hints(definition.function).items():

                if hint is inspect.Parameter.empty:
                    unresolved.append(f"{definition.name}.{name} (no annotation)")

                elif isinstance(hint, str):
                    unresolved.append(f"{definition.name}.{name} -> {hint!r}")

        assert not unresolved, f"unresolvable annotations: {unresolved}"

    def test_required_matches_parameters_without_defaults(self) -> None:
        """
        A parameter with no default that is missing from ``required`` lets the
        model omit it, and the tool then fails with a TypeError the model cannot
        interpret.
        """

        for definition in tool_registry.all():

            schema = schema_generator.generate(definition)
            parameters = schema["function"]["parameters"]

            required = set(parameters.get("required", []))
            declared = set(parameters["properties"])

            assert required <= declared, definition.name

    def test_additional_properties_is_closed(self) -> None:
        """
        An open schema lets a model invent an argument, which arrives as an
        unexpected keyword and fails at call time rather than at validation.
        """

        for definition in tool_registry.all():

            schema = schema_generator.generate(definition)

            assert (
                schema["function"]["parameters"]["additionalProperties"] is False
            ), definition.name
