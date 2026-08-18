from __future__ import annotations

from ..core.logging import get_logger

from .bootstrapper import Bootstrapper
from ..cli.main import CLIRuntime

import asyncio
from ..tools.registry import tool_registry

class Application:
    """
    Main AetherOS application.

    Responsible for managing the application's lifecycle.

    Startup logic lives inside Bootstrapper.
    """

    def __init__(self) -> None:
        self._logger = get_logger("application")
        self._bootstrapper = Bootstrapper()
        self._cli = None
        self._running = False

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_running(self) -> bool:
        """
        Returns whether the application is running.
        """
        return self._running

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self) -> None:
        """
        Start the application.
        """

        if self._running:
            self._logger.warning("Application already running.")
            return

        self._logger.info("Starting AetherOS...")

        # ----------------------------------------------
        # Bootstrap EVERYTHING first
        # ----------------------------------------------

        await self._bootstrapper.start()

        # ----------------------------------------------
        # Now create CLI
        # ----------------------------------------------
        from ..cli import CLIRuntime

        print(
            "[DEBUG APPLICATION] Bootstrap complete."
        )

        print(
            "[DEBUG APPLICATION] Registry:",
            self._bootstrapper.tool_registry
        )

    
        self._cli = CLIRuntime(
            tool_registry=self._bootstrapper.tool_registry
        )

        self._running = True

        self._logger.info("AetherOS started successfully.")




    async def run(self) -> None:
        if not self._running:
            raise RuntimeError(
                "Application has not been started."
            )

        self._logger.info(
            "Application is running..."
        )

        await self._cli.start()

    async def stop(self) -> None:
        if not self._running:
            return

        self._logger.info(
            "Stopping AetherOS..."
        )

        await self._cli.stop()
        await self._bootstrapper.shutdown()

        self._running = False

        self._logger.info(
            "Application stopped."
        )

    async def restart(self) -> None:
        """
        Restart the application.
        """

        self._logger.info("Restarting AetherOS...")

        await self.stop()

        await self.start()