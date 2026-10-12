"""
Heatmap service (Phase 3).

The reusable, read-only service that builds heatmaps. It replays an ordered
``(order-book, trades)`` stream through the shared :class:`LiquidityEngine`
(the same engine the liquidity layer uses) while folding each step into one
bounded :class:`HeatmapGrid` -- so the heatmap is an *observation layer backed
by real calculated data*, never a second engine and never a decision source.

All the getters return a view (or the surface) projected from the one grid a
build produced. There is deliberately one build path and several lenses, not
one service per heatmap kind.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ..domain.order_book import OrderBook, TradeTick
from ..liquidity.engine import LiquidityEngine
from .grid import HeatmapGrid
from .surface import LiquiditySurface, surface
from .views import HeatmapView, available_views, render

logger = get_logger("trading.heatmap")


class HeatmapService:
    """
    Builds bounded time x price heatmaps from a liquidity stream.

    ``price_step`` and ``bucket_seconds`` set the resolution; ``capacity`` caps
    retained time-buckets (bounded memory). The service holds no analytical
    logic -- the engine computes, the grid aggregates, the views project.
    """

    def __init__(
        self,
        *,
        price_step: float = 0.5,
        bucket_seconds: float = 60.0,
        capacity: int = 256,
    ) -> None:
        self._price_step = price_step
        self._bucket_seconds = bucket_seconds
        self._capacity = capacity

    def _build(
        self,
        steps: list[tuple[OrderBook, tuple[TradeTick, ...]]],
        *,
        symbol: str = "",
        is_mock: bool = False,
    ) -> tuple[HeatmapGrid, LiquidityEngine]:
        """
        Replay a stream into the grid (the single build path for every view).

        Each step drives the shared liquidity engine AND folds that step's
        observation/zones/events into the grid, so the heatmap always reflects
        the same numbers the liquidity engine produced. Each step reads only
        its own data -- look-ahead-free by construction.
        """
        engine = LiquidityEngine()
        grid = HeatmapGrid(
            price_step=self._price_step,
            bucket_seconds=self._bucket_seconds,
            capacity=self._capacity,
            symbol=symbol,
        )
        for book, trades in steps:
            result = engine.step(book, tuple(trades or ()), is_mock=is_mock)
            grid.update(
                result.observation,
                zones=result.zones,
                events=result.events,
            )
        return grid, engine

    # ------------------------------------------------------------------
    # Public getters
    # ------------------------------------------------------------------

    def get_heatmap(
        self,
        steps: list[tuple[OrderBook, tuple[TradeTick, ...]]],
        *,
        symbol: str = "",
        normalize: bool = True,
        is_mock: bool = False,
    ) -> HeatmapView:
        """The primary time x price liquidity heatmap (resting-liquidity lens)."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "liquidity", normalize=normalize)

    def get_liquidity_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """Alias of ``get_heatmap`` -- the resting-liquidity view."""
        return self.get_heatmap(
            steps, symbol=symbol, normalize=normalize, is_mock=is_mock
        )

    def get_persistence_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """How long liquidity stood at each (time, price) bin."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "persistence", normalize=normalize)

    def get_flow_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """Aggressor-signed executed flow (net flow) per bin."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "flow", normalize=normalize)

    def get_sweep_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """Sweep intensity per bin (rejection and acceptance shown, not labelled)."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "sweep", normalize=normalize)

    def get_absorption_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """Absorption divergence strength per bin (aggressive flow vs price move)."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "absorption", normalize=normalize)

    def get_pressure_heatmap(self, steps, *, symbol="", normalize=True, is_mock=False):
        """Derived market-pressure magnitude per bin (documented heuristic)."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return render(grid, "pressure", normalize=normalize)

    def get_surface(
        self,
        steps,
        *,
        symbol: str = "",
        channel: str = "total_intensity",
        is_mock: bool = False,
    ) -> LiquiditySurface:
        """The price x time x intensity surface (renderer-agnostic data)."""
        grid, _ = self._build(steps, symbol=symbol, is_mock=is_mock)
        return surface(grid, channel)

    def views(self) -> tuple[str, ...]:
        """The view kinds this service can render."""
        return available_views()
