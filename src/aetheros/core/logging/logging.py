"""
Backwards-compatible logging facade.

This module used to install its own set of loguru sinks. Because loguru's
``logger`` is a process-wide singleton and every configuration begins with
``logger.remove()``, having two configurations meant whichever module was
imported second silently destroyed the other's handlers — so log output
depended on import order.

The single configuration now lives in :mod:`aetheros.core.logging.logger`
(backed by :mod:`aetheros.core.logging.handlers`). This module re-exports it
so existing imports such as::

    from ..core.logging.logging import get_logger, setup_logging

keep working unchanged.
"""

from __future__ import annotations

from .logger import (
    disable_console_logging,
    enable_console_logging,
    get_logger,
    setup_logging,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "enable_console_logging",
    "disable_console_logging",
]
