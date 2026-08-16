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

    # def discover_package(
    #     self,
    #     package_name: str,
    # ) -> list[str]:
    #     """
    #     Discover every module inside a package.
    #     """

    #     package = importlib.import_module(package_name)

    #     imported: list[str] = []

    #     for module in pkgutil.walk_packages(
    #         package.__path__,
    #         package.__name__ + ".",
    #     ):

    #         name = module.name

    #         if name in self._imported:
    #             continue

    #         try:

    #             importlib.import_module(name)

    #             self._imported.add(name)

    #             imported.append(name)

    #             logger.info(
    #                 "Loaded tool module %s",
    #                 name,
    #             )

    #         except Exception:

    #             logger.exception(
    #                 "Failed to import %s",
    #                 name,
    #             )

    #     return imported


    # def discover_package(self, package_name: str) -> list[str]:
    #     """
    #     Discover and import all modules inside a package.
    #     """

    #     imported: list[str] = []

    #     package = importlib.import_module(package_name)

    #     package_path = getattr(package, "__path__", None)

    #     if package_path is None:
    #         self._logger.warning(
    #             "Skipping %s: not a package.",
    #             package_name,
    #         )
    #         return imported

    #     for module_info in pkgutil.walk_packages(
    #         package_path,
    #         package.__name__ + ".",
    #     ):
    #         module_name = module_info.name

    #         try:
    #             importlib.import_module(module_name)

    #             imported.append(module_name)

    #             self._logger.debug(
    #                 "Discovered tool module: %s",
    #                 module_name,
    #             )

    #         except Exception as exc:
    #             self._logger.exception(
    #                 "Failed to import tool module %s: %s",
    #                 module_name,
    #                 exc,
    #             )

    #     return imported



    def discover_package(self, package_name: str) -> list[str]:
        imported: list[str] = []

        package = importlib.import_module(package_name)

        imported.append(package_name)

        package_path = getattr(package, "__path__", None)

        if package_path is None:
            return imported

        for module_info in pkgutil.walk_packages(
            package_path,
            package.__name__ + ".",
        ):
            module_name = module_info.name

            try:
                importlib.import_module(module_name)
                imported.append(module_name)

            except Exception as exc:
                self._logger.exception(
                    "Failed to import %s: %s",
                    module_name,
                    exc,
                )

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