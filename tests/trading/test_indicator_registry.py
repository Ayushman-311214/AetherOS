"""
The custom-indicator extension boundary.

Pins the contract of ``IndicatorRegistry`` and its module-level helpers: a
custom callable can be registered under a name and later fetched, duplicate and
invalid registrations are rejected rather than silently overwriting, and the
lookup is case/whitespace insensitive. The registry is an extension point only,
so the core indicators must remain importable and must NOT be injected into it.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.trading.indicators import core as ind
from aetheros.trading.indicators.registry import (
    IndicatorRegistry,
    get_indicator,
    indicator_registry,
    register_indicator,
)


@pytest.fixture
def registry() -> IndicatorRegistry:
    """A private registry so the process-wide singleton stays untouched."""
    return IndicatorRegistry()


def _double(closes, highs, lows, volumes):
    """A minimal custom indicator honouring the input-aligned array contract."""
    return np.asarray(closes, dtype=float) * 2.0


def test_register_and_get(registry):
    registry.register("double", _double)
    assert registry.get("double") is _double
    assert "double" in registry
    assert len(registry) == 1
    assert registry.names() == ["double"]


def test_lookup_is_case_and_whitespace_insensitive(registry):
    registry.register("  Double  ", _double)
    assert registry.get("double") is _double
    assert registry.get("DOUBLE") is _double
    assert registry.get("  double  ") is _double


def test_unknown_name_returns_none(registry):
    assert registry.get("missing") is None
    assert "missing" not in registry


def test_duplicate_registration_is_rejected(registry):
    registry.register("double", _double)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("double", _double)


def test_empty_and_non_callable_registrations_are_rejected(registry):
    with pytest.raises(ValueError, match="must not be empty"):
        registry.register("   ", _double)
    with pytest.raises(ValueError, match="must be callable"):
        registry.register("broken", 42)  # type: ignore[arg-type]


def test_unregister_and_clear(registry):
    registry.register("double", _double)
    registry.register("triple", _double)
    registry.unregister("double")
    assert registry.get("double") is None
    assert registry.names() == ["triple"]
    registry.unregister("never-registered")  # idempotent
    registry.clear()
    assert len(registry) == 0


def test_module_level_helpers_use_the_singleton():
    try:
        register_indicator("test-singleton", _double)
        assert get_indicator("test-singleton") is _double
        assert indicator_registry.get("test-singleton") is _double
    finally:
        indicator_registry.unregister("test-singleton")
    assert get_indicator("test-singleton") is None


def test_core_indicators_are_not_seeded_into_the_registry():
    # The registry is an extension point, not a replacement: core functions keep
    # their direct import path and a fresh registry starts empty.
    assert get_indicator("sma") is None
    assert get_indicator("rsi") is None
    assert callable(ind.sma)
    assert callable(ind.rsi)
