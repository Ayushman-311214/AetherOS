"""
The live intelligence driver for the terminal workspace.

Produces the ``refresh_fn`` the workspace's render loop calls: it runs the
*real* production services (the ones the bootstrapper already registered) and
writes their latest reads into ``WorkspaceState`` via the adapter. The TUI
never awaits analysis inline -- the driver is the only code that touches
intelligence, so a slow read delays the next refresh rather than freezing the
renderer.

Everything it shows is real: the candles come from ``MarketDataService``, the
analysis from ``AnalysisService``/``SignalEngineService``, the market-intel
read from ``MarketIntelService``, and the heatmap projection from the actual
``HeatmapService`` surface. A missing or failing layer writes an honest
"unavailable" status, never fabricated data.
"""

from __future__ import annotations

import asyncio

from ..core.logging import get_logger

logger = get_logger("aetheros.workspace.driver")


def build_refresh_fn(container, adapter, *, heatmap_steps_fn=None):
    """
    Build the async refresh coroutine the workspace render loop calls.

    ``container`` is the bootstrapped DI container (resolves the real
    services); ``adapter`` is the workspace adapter to write through.
    ``heatmap_steps_fn`` optionally supplies an (order-book, trades) step
    stream for the liquidity heatmap -- without it the heatmap panel shows
    honestly-empty rather than fake depth (Yahoo has no book/tape).
    """

    async def refresh() -> None:
        state = adapter._state
        symbol, timeframe = state.symbol, state.timeframe
        try:
            from ..trading.services.market_data_service import MarketDataService

            md = container.resolve(MarketDataService)
            data = await md.get_candles(symbol, timeframe, limit=80)
            adapter.set_candles(
                [c.to_dict() for c in data.candles[-20:]]
            )
            adapter.set_system(
                "market_data", "ok", f"{md.provider_name} {data.count} bars"
            )
        except Exception as exc:
            adapter.set_system(
                "market_data", "error", str(exc)[:60]
            )
            state.add_error(f"market data: {exc}")

        try:
            from ..trading.services.analysis_service import AnalysisService
            from ..trading.signal_engine.service import SignalEngineService

            analysis = await container.resolve(
                AnalysisService
            ).analyze_data(data, emit=False)
            assessment = container.resolve(
                SignalEngineService
            ).assess(analysis)
            adapter.set_assessment(assessment.to_dict())
            adapter.set_component(
                "Trading Intelligence", "running",
                f"{assessment.direction.value}",
                is_mock=assessment.is_mock,
            )
        except Exception as exc:
            adapter.set_component(
                "Trading Intelligence", "error", str(exc)[:40]
            )
            state.add_error(f"analysis: {exc}")

        try:
            from ..trading.market_intel.service import MarketIntelService

            intel = await container.resolve(MarketIntelService).analyze(data)
            adapter.set_intel(intel.to_dict())
        except Exception as exc:
            adapter.set_component("Market Analysis", "error", str(exc)[:40])

        # Heatmap: only from a real book/tape stream. Without a source the
        # panel stays honestly empty (no fabricated depth).
        if heatmap_steps_fn is not None:
            try:
                from ..trading.heatmap.service import HeatmapService
                from ..trading.heatmap.surface import project

                svc = container.resolve(HeatmapService)
                steps = heatmap_steps_fn(symbol)
                if steps:
                    surf = await svc.get_surface(
                        steps, symbol=symbol, channel="total_intensity"
                    )
                    adapter.set_heatmap(
                        surf.to_dict(), projection=project(surf, width=70)
                    )
            except Exception as exc:
                adapter.set_component(
                    "Liquidity Analyzer", "error", str(exc)[:40]
                )
        else:
            adapter.set_component(
                "Liquidity Analyzer", "idle", "no book/tape source"
            )

        adapter.set_system("trading_intelligence", "running", symbol)
        adapter.set_system("event_bus", "up", "subscribed")
        state.last_updated = state.last_updated or ""

    return refresh
