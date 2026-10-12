"""
Market heatmap & market-state visualisation (Phase 3).

A read-only projection layer on top of the liquidity intelligence engine
(``trading/liquidity``). It folds an ordered ``(order-book, trade)`` stream --
the same stream the liquidity engine replays -- into a bounded time x price
grid of ``HeatmapCell`` values, then projects that one grid into the six
canonical heatmap views.

Honesty is the same as every layer below it: the grid holds *measured* and
*derived* quantities only (resting/executed liquidity, persistence, sweeps,
absorption, pressure). It makes no BUY/SELL call -- interpretation lives in the
signal/decision layers downstream, and this layer never produces one. Every
cell carries ``is_mock`` so a synthetic read can never be drawn as real.

The six views share one grid-builder, not six engines -- they differ only in
*which* cell quantity becomes the intensity channel, so a bug or a look-ahead
can exist in exactly one place.
"""

from __future__ import annotations

from .cell import HeatmapCell
from .grid import HeatmapGrid
from .service import HeatmapService
from .surface import LiquiditySurface, project, surface
from .views import HeatmapPoint, HeatmapView, available_views, render

__all__ = [
    "HeatmapCell",
    "HeatmapGrid",
    "HeatmapPoint",
    "HeatmapService",
    "HeatmapView",
    "LiquiditySurface",
    "available_views",
    "project",
    "render",
    "surface",
]
