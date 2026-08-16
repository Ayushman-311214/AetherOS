from __future__ import annotations

import asyncio
from typing import Protocol

from core.logging import get_logger


class LifecycleComponent(Protocol):
    """
    Every service that participates in the application
    lifecycle should implement these methods.
    """

    async def initialize(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def health_check(self) -> bool:
        ...


class LifecycleManager:
    """
    Coordinates startup and shutdown of all services.
    """

    def __init__(self) -> None:

        self._logger = get_logger("lifecycle")

        self._components: list[LifecycleComponent] = []

    # ======================================================
    # Registration
    # ======================================================

    def register(
        self,
        component: LifecycleComponent,
    ) -> None:
        """
        Register a lifecycle component.
        """

        if component not in self._components:

            self._components.append(component)

            self._logger.debug(
                f"Registered {component.__class__.__name__}"
            )

    def unregister(
        self,
        component: LifecycleComponent,
    ) -> None:

        if component in self._components:

            self._components.remove(component)

    def clear(self) -> None:

        self._components.clear()

    # ======================================================
    # Initialization
    # ======================================================

    async def initialize_all(self) -> None:
        """
        Initialize every registered component.
        """

        self._logger.info(
            "Initializing services..."
        )

        for component in self._components:

            self._logger.debug(
                f"Initializing {component.__class__.__name__}"
            )

            await component.initialize()

        self._logger.info(
            "All services initialized."
        )

    # ======================================================
    # Shutdown
    # ======================================================

    async def shutdown_all(self) -> None:
        """
        Shutdown all services in reverse order.
        """

        self._logger.info(
            "Shutting down services..."
        )

        for component in reversed(self._components):

            self._logger.debug(
                f"Stopping {component.__class__.__name__}"
            )

            await component.shutdown()

        self._logger.info(
            "All services stopped."
        )

    # ======================================================
    # Health
    # ======================================================

    async def health_check(self) -> dict[str, bool]:
        """
        Execute health checks for all components.
        """

        results: dict[str, bool] = {}

        for component in self._components:

            try:

                healthy = await component.health_check()

            except Exception:

                healthy = False

            results[
                component.__class__.__name__
            ] = healthy

        return results

    async def all_healthy(self) -> bool:
        """
        Returns True if every component is healthy.
        """

        results = await self.health_check()

        return all(results.values())

    # ======================================================
    # Information
    # ======================================================

    @property
    def components(self) -> list[LifecycleComponent]:

        return list(self._components)

    @property
    def count(self) -> int:

        return len(self._components)