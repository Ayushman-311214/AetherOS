"""
Every concrete backend must actually satisfy its interface.

``PlaywrightProvider`` inherited :class:`BrowserProvider` but never implemented
its ``name`` and ``version`` properties. Nothing caught it: the module imported,
the class was registered in the container, all 16 browser tools registered and
generated valid schemas — and every one of them failed at *call* time with
``TypeError: Can't instantiate abstract class``. The container's factory is lazy,
so the failure surfaced only on first use, one tool call at a time.

Levels 1 to 3 are structurally incapable of catching this, which is why it gets
its own test: an unsatisfied ABC is a class of defect, not a one-off.
"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SKIP_DIRS = {"__pycache__", ".cache", "logs", "tests", "scripts", "data"}

# A class defined in one of these modules is an interface by intent, so leftover
# abstract methods are correct there. Anything else inheriting an AetherOS ABC is
# an implementation and has to be complete.
INTERFACE_MODULE_PARTS = {"interfaces", "base", "abstract"}


def _package_modules() -> list[str]:

    modules: list[str] = []

    for path in sorted((SRC / "aetheros").rglob("*.py")):

        rel = path.relative_to(SRC)

        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        parts = rel.with_suffix("").parts

        if parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            continue

        modules.append(".".join(parts))

    return modules


def _is_interface_module(module_name: str) -> bool:

    tail = module_name.rsplit(".", 2)[-2:]

    return any(
        part in INTERFACE_MODULE_PARTS
        for part in tail
    )


def _incomplete_implementations() -> list[str]:
    """
    Classes that inherit an AetherOS ABC but left abstract methods unimplemented.
    """

    seen: set[type] = set()
    broken: list[str] = []

    for module_name in _package_modules():

        try:
            module = importlib.import_module(module_name)

        except Exception:
            # Import health is asserted by tests/tools/test_tool_surface.py and
            # by test_every_package_module_imports below; failing here too would
            # report one defect as two.
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):

            if obj in seen:
                continue

            seen.add(obj)

            # Only classes this project defines, and only ABC descendants.
            if not obj.__module__.startswith("aetheros"):
                continue

            if not issubclass(obj, ABC):
                continue

            pending = getattr(obj, "__abstractmethods__", frozenset())

            if not pending:
                continue

            if _is_interface_module(obj.__module__):
                continue

            broken.append(
                f"{obj.__module__}.{obj.__qualname__} "
                f"is missing {sorted(pending)}"
            )

    return broken


class TestInterfaceContracts:

    def test_no_implementation_leaves_abstract_methods_unimplemented(
        self,
    ) -> None:

        broken = _incomplete_implementations()

        assert not broken, "incomplete implementations:\n  " + "\n  ".join(broken)

    def test_the_scan_actually_inspected_something(self) -> None:
        """
        Guard the guard: an import or filtering bug that examined no classes
        would make the assertion above pass for the wrong reason.
        """

        assert len(_package_modules()) > 50


class TestPackageImports:

    @pytest.mark.parametrize("module", _package_modules())
    def test_every_package_module_imports(self, module: str) -> None:
        """
        Six modules used absolute imports (``from core.logging import ...``)
        that assumed ``src/`` was the import root. Each failed only when
        something happened to import it, which for two whole subsystems was
        never.
        """

        importlib.import_module(module)
