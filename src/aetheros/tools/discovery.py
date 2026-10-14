from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Iterable


logger = logging.getLogger(__name__)


class ToolDiscovery:
    """
    Automatically discovers and imports tool modules.

    Importing a module executes its @tool decorators,
    which register the tools in the global registry.
    """

    def __init__(self) -> None:
        self._imported: set[str] = set()

    # ==========================================================
    # Public API
    # ==========================================================

    def discover(
        self,
        packages: Iterable[str],
    ) -> list[str]:
        """
        Discover tools from multiple packages.

        Returns:
            List of imported module names.
        """

        imported: list[str] = []

        for package in packages:

            imported.extend(
                self.discover_package(package)
            )

        return imported

    def discover_package(
        self,
        package_name: str,
    ) -> list[str]:
        """
        Import a package and every module beneath it.

        Returns the modules imported by *this* call. A module already imported by
        an earlier call is skipped rather than reported twice — its @tool
        decorators ran the first time and the registry rejects duplicate names.
        """

        imported: list[str] = []

        try:
            package = importlib.import_module(package_name)

        except Exception:
            logger.exception(
                "Failed to import tool package %s",
                package_name,
            )
            return imported

        if package_name not in self._imported:
            self._imported.add(package_name)
            imported.append(package_name)

        package_path = getattr(package, "__path__", None)

        if package_path is None:
            return imported

        for module_info in pkgutil.walk_packages(
            package_path,
            package.__name__ + ".",
        ):
            module_name = module_info.name

            if module_name in self._imported:
                continue

            try:
                importlib.import_module(module_name)

            except Exception:
                # The failure is logged, not raised: one unimportable tool module
                # must not take down discovery of every other tool. exception()
                # keeps the traceback, so the real cause stays diagnosable.
                logger.exception(
                    "Failed to import tool module %s",
                    module_name,
                )
                continue

            self._imported.add(module_name)
            imported.append(module_name)

        return imported

    # ==========================================================
    # Utilities
    # ==========================================================

    def clear(self) -> None:
        """
        Clears imported module history.

        Useful for testing.
        """

        self._imported.clear()

    @property
    def imported_modules(self) -> list[str]:

        return sorted(self._imported)


tool_discovery = ToolDiscovery()
