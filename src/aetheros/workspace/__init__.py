"""
Terminal-native AetherOS trading-intelligence workspace (Phase 7).

A single application inside the terminal -- multiple synchronised panels over
the same live trading-intelligence state. NOT a GUI app, NOT a collection of
independent processes: one process, one shared state, one renderer.

The TUI is deliberately a *view* layer with **no trading logic**:

    Trading Intelligence
        -> EventBus / services
        -> WorkspaceState + ViewModels   (this package)
        -> Panels (rich renderables)
        -> Terminal renderer (rich.live.Live)

The same state the workspace renders is the state a future graphical UI can
reuse -- the view-model builders return plain data, not render calls, so the
intelligence-to-presentation seam is identical regardless of the renderer.

Honesty: every panel shows *real* data -- a panel with no data shows an honest
"no data yet", never a fabricated read. ``is_mock``/``is_reliable`` are surfaced
so a synthetic or thin read can never be drawn as a real one.
"""

from __future__ import annotations

from .adapter import WorkspaceAdapter, WorkspaceLogHandler
from .app import KEYMAP, TerminalWorkspace, build_workspace
from .layout import build_layout
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
from .state import (
    AgentRow,
    EventRow,
    LogLine,
    SystemMetric,
    WorkspaceState,
)

__all__ = [
    "AgentRow",
    "EventRow",
    "KEYMAP",
    "LogLine",
    "PANEL_ORDER",
    "SystemMetric",
    "TerminalWorkspace",
    "WorkspaceAdapter",
    "WorkspaceLogHandler",
    "WorkspaceState",
    "build_layout",
    "build_workspace",
    "panel_agents",
    "panel_analysis",
    "panel_decision",
    "panel_events",
    "panel_heatmap",
    "panel_header",
    "panel_logs",
    "panel_market",
    "panel_system",
]
