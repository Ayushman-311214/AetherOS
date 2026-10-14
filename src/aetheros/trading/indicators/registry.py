"""
Custom-indicator extension boundary.

A registry mapping names to indicator callables so new indicators can be added
without editing ``core.py``. The contract for a registered indicator is the
same one the core functions honour: pure function of numpy arrays, returns an
array (or tuple of arrays / a result object) aligned to its input, NaN for the
warm-up, deterministic, no I/O.

The registry is an *extension point*, not a replacement: the core indicators
stay directly importable from :mod:`aetheros.trading.indicators.core` and are
NOT seeded into the registry. ``calculate_indicator`` consults the registry
only after the built-in names, so nothing existing changes behaviour.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class IndicatorRegistry:
    """Name -> indicator callable, with duplicate-name protection."""

    def __init__(self) -> None:
        self._indicators: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("Indicator name must not be empty.")
        if not callable(fn):
            raise ValueError(f"Indicator '{name}' must be callable.")
        if key in self._indicators:
            raise ValueError(
                f"Indicator '{key}' is already registered. Unregister it first."
            )
        self._indicators[key] = fn

    def unregister(self, name: str) -> None:
        self._indicators.pop(name.strip().lower(), None)

    def get(self, name: str) -> Callable[..., Any] | None:
        return self._indicators.get(name.strip().lower())

    def names(self) -> list[str]:
        return sorted(self._indicators)

    def clear(self) -> None:
        self._indicators.clear()

    def __contains__(self, name: str) -> bool:
        return name.strip().lower() in self._indicators

    def __len__(self) -> int:
        return len(self._indicators)


# Module-level singleton: the process-wide custom-indicator extension point.
indicator_registry = IndicatorRegistry()


def register_indicator(name: str, fn: Callable[..., Any]) -> None:
    """Register a custom indicator callable under ``name``."""
    indicator_registry.register(name, fn)


def get_indicator(name: str) -> Callable[..., Any] | None:
    """Fetch a registered custom indicator, or None if not registered."""
    return indicator_registry.get(name)
