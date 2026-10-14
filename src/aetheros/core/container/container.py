from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ServiceContainer:
    """
    Simple Dependency Injection (DI) container.

    Supports:
    - Singleton services
    - Factory services
    - Lazy loading
    """

    def __init__(self) -> None:
        # Keys are usually the service class object itself, so a caller resolves
        # by type rather than by a stringly-typed name.
        self._singletons: dict[Any, Any] = {}
        self._singleton_factories: dict[Any, Callable[[], Any]] = {}
        self._factories: dict[Any, Callable[[], Any]] = {}

    # -----------------------------------------------------
    # Singleton
    # -----------------------------------------------------

    def register_singleton(
        self,
        name: Any,
        factory: Callable[[], Any],
    ) -> None:
        """
        Register a singleton service.
        Instance is created lazily.
        """
        self._singleton_factories[name] = factory

    # -----------------------------------------------------
    # Factory
    # -----------------------------------------------------

    def register_factory(
        self,
        name: Any,
        factory: Callable[[], Any],
    ) -> None:
        """
        Register a factory.
        Every resolve() creates a new instance.
        """
        self._factories[name] = factory

    # -----------------------------------------------------
    # Resolve
    # -----------------------------------------------------

    def resolve(self, name: Any) -> Any:

        if name in self._singletons:
            return self._singletons[name]

        if name in self._singleton_factories:
            instance = self._singleton_factories[name]()
            self._singletons[name] = instance
            return instance

        if name in self._factories:
            return self._factories[name]()

        raise KeyError(f"Service '{name}' is not registered.")

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def has(self, name: Any) -> bool:
        return (
            name in self._singletons
            or name in self._singleton_factories
            or name in self._factories
        )

    def is_instantiated(self, name: Any) -> bool:
        """
        Whether a singleton has actually been built yet.

        Shutdown code needs this: ``resolve()`` would *construct* a service that
        was registered but never used, so tearing down by resolving would load an
        OCR model on the way out of the process.
        """

        return name in self._singletons

    def remove(self, name: Any) -> None:
        self._singletons.pop(name, None)
        self._singleton_factories.pop(name, None)
        self._factories.pop(name, None)

    def clear(self) -> None:
        self._singletons.clear()
        self._singleton_factories.clear()
        self._factories.clear()

    def registered_services(self) -> list[str]:

        services = (
            set(self._singletons)
            | set(self._singleton_factories)
            | set(self._factories)
        )

        return sorted(
            str(service)
            for service in services
        )