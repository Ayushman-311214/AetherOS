"""
The trading module's public API surface (spec Phase 24).

Higher-level modules depend only on :class:`TradingAPI`. See
``trading_api.py`` for the rationale and the per-method contracts.
"""

from __future__ import annotations

from .trading_api import TradingAPI

__all__ = ["TradingAPI"]
