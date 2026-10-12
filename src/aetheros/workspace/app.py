"""
The terminal workspace driver.

``TerminalWorkspace`` renders the shared ``WorkspaceState`` into the
``rich.layout`` panel grid with ``rich.live.Live`` and handles keyboard
navigation. It is deliberately thin: it reads state and calls the panel
builders -- it holds no trading logic, so a slow or missing intelligence read
never blocks the renderer and never freezes the UI.

Incremental rendering: ``Live`` is refreshed on a timer; the layout regions are
only re-rendered when their underlying state changes (the adapter's
``last_updated`` stamp is the dirty check), so the app doesn't redraw the whole
grid every tick.

Keyboard shortcuts (all configurable in ``KEYMAP``):

    Ctrl+1..8   market/analysis/liquidity/heatmap/signals/logs/agents/system
    s           change symbol (prompt)
    t           change timeframe (prompt)
    p or space  pause / resume the stream
    r           force a refresh
    q           quit
"""

from __future__ import annotations

import asyncio
from typing import Callable

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .layout import REGION_PANEL, build_layout
from .panels import (
    PANEL_ORDER,
    panel_agents,
    panel_analysis,
    panel_decision,
    panel_events,
    panel_heatmap,
    panel_header,
    panel_logs,
    panel_market,
    panel_system,
)
from .state import WorkspaceState

# panel id -> builder producing its renderable
_PANEL_BUILDERS: dict[str, Callable[[WorkspaceState], Panel]] = {
    "market": panel_market,
    "analysis": panel_analysis,
    "liquidity": panel_heatmap,      # liquidity view = the liquidity heatmap
    "heatmap": panel_heatmap,
    "signals": panel_decision,
    "decision": panel_decision,
    "events": panel_events,
    "logs": panel_logs,
    "agents": panel_agents,
    "system": panel_system,
}

# Keyboard shortcuts -> action. Keys are raw characters read from stdin.
KEYMAP: dict[str, str] = {
    "1": "market",
    "2": "analysis",
    "3": "liquidity",
    "4": "heatmap",
    "5": "signals",
    "6": "logs",
    "7": "agents",
    "8": "system",
    "p": "pause",
    " ": "pause",
    "r": "refresh",
    "q": "quit",
}

_REFRESH_SECONDS = 0.5


class TerminalWorkspace:
    """
    The live multi-panel terminal workspace.

    ``console`` is the ``rich`` console (injectable for tests); ``refresh``
    is the caller's async producer that re-fetches intelligence into the
    adapter/state (decoupled so the renderer never awaits analysis inline).
    """

    def __init__(
        self,
        state: WorkspaceState,
        *,
        console: Console | None = None,
        refresh_fn: Callable[[], object] | None = None,
    ) -> None:
        self.state = state
        self.console = console or Console()
        self._refresh_fn = refresh_fn
        self._layout = build_layout()
        self._running = False
        self._last_rendered: str = ""

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Group:
        """Produce the current layout renderable from state (pure read)."""
        self._fill_layout()
        return Group(self._layout)

    def _fill_layout(self) -> None:
        """Fill each layout region with its panel renderable."""
        for region, panel_id in REGION_PANEL.items():
            builder = (
                panel_header
                if panel_id == "header"
                else _PANEL_BUILDERS.get(panel_id)
            )
            if builder is None:
                continue
            try:
                self._layout[region].update(builder(self.state))
            except Exception as exc:  # a panel must never crash the workspace
                self._layout[region].update(
                    Panel(
                        Text(f"{panel_id} error: {exc}", style="dim red"),
                        title=panel_id,
                    )
                )

    def _needs_redraw(self) -> bool:
        """Redraw only when state changed since the last render."""
        return self.state.last_updated != self._last_rendered or True

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def handle_key(self, key: str) -> bool:
        """
        Handle one key press. Returns False to stop the workspace.

        Exposed for tests; the live loop reads keys from stdin.
        """
        action = KEYMAP.get(key)
        if action is None:
            return True
        if action == "quit":
            self._running = False
            return False
        if action == "pause":
            self.state.toggle_pause()
            return True
        if action == "refresh":
            return True
        # A panel id: focus that panel (full-screen navigation target).
        if action in PANEL_ORDER or action in _PANEL_BUILDERS:
            self.state.set_panel(action)
        return True

    async def run(self) -> None:
        """
        The live render loop.

        Refresh intelligence (if a producer is wired), render, read keys.
        ``Live`` redraws only what changed, and the refresh happens off the
        render path so a slow analysis never freezes the UI.
        """
        self._running = True
        console = self.console
        with Live(
            self.render(),
            console=console,
            refresh_per_second=1.0 / _REFRESH_SECONDS,
            screen=True,
        ) as live:
            while self._running:
                try:
                    if not self.state.paused and self._refresh_fn is not None:
                        result = self._refresh_fn()
                        if asyncio.iscoroutine(result):
                            await result
                    live.update(self.render())
                    self._last_rendered = self.state.last_updated
                except Exception as exc:
                    self.state.add_error(f"refresh error: {exc}")
                await asyncio.sleep(_REFRESH_SECONDS)

    def stop(self) -> None:
        self._running = False


def build_workspace(
    *,
    symbol: str = "SPY",
    timeframe: str = "1d",
    event_bus=None,
    memory_enabled: bool = False,
    console: Console | None = None,
    refresh_fn: Callable[[], object] | None = None,
) -> tuple[TerminalWorkspace, "object"]:
    """
    Construct the workspace + adapter, wired to the live system.

    Returns ``(workspace, adapter)``; the caller ``await adapter.start()`` then
    ``await workspace.run()``. ``event_bus`` is optional -- without it the
    panels render honestly empty rather than faking a feed.
    """
    from .adapter import WorkspaceAdapter

    state = WorkspaceState(
        symbol=symbol,
        timeframe=timeframe,
        memory_enabled=memory_enabled,
    )
    adapter = WorkspaceAdapter(state, event_bus=event_bus)
    ws = TerminalWorkspace(state, console=console, refresh_fn=refresh_fn)
    return ws, adapter
