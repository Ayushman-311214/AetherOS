"""
Workspace layout -- how the panels are arranged in the terminal.

A ``rich.layout.Layout`` tree matching the spec's default workspace. The layout
only arranges *named regions*; the renderer fills each region with the panel
renderable for that region's id. Keeping layout separate from the panel content
means a panel can be swapped, resized or re-arranged without touching what it
displays.
"""

from __future__ import annotations

from rich.layout import Layout


def build_layout() -> Layout:
    """
    The default multi-window workspace:

        ┌───────────── header ─────────────┐
        ├──────── market ──────┬─ decision ┤
        ├──────────── heatmap ─────────────┤
        ├─── analysis/evidence ─┬─ events ─┤
        ├───── logs ────────────┼─ agents ─┤
        └───────────────────────┴──────────┘
    """
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="top", ratio=2),
        Layout(name="heatmap", size=8),
        Layout(name="middle", ratio=2),
        Layout(name="bottom", ratio=2),
    )
    layout["top"].split_row(
        Layout(name="market", ratio=3),
        Layout(name="decision", ratio=1),
    )
    layout["middle"].split_row(
        Layout(name="analysis", ratio=1),
        Layout(name="events", ratio=1),
    )
    layout["bottom"].split_row(
        Layout(name="logs", ratio=1),
        Layout(name="agents", ratio=1),
    )
    return layout


# The panel renderable to fill each layout region. ``system`` is reachable via
# the keyboard shortcut; it shares the bottom-right cell with agents in the
# default layout but is a first-class panel for navigation.
REGION_PANEL = {
    "header": "header",
    "market": "market",
    "decision": "decision",
    "heatmap": "heatmap",
    "analysis": "analysis",
    "events": "events",
    "logs": "logs",
    "agents": "agents",
}
