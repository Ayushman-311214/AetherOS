"""
Workspace panels -- the Rich renderables for each view.

Each ``panel_*`` builder reads ``WorkspaceState`` and returns a ``rich``
renderable (``Panel`` / ``Table`` / ``Text``). They are pure presentation:
no trading logic, no I/O, and every panel honestly shows "no data yet" when
its source hasn't produced anything -- a blank panel is never filled with a
fabricated read.

The panels are grouped into the spec's default layout:

    ┌────────────────────── header (AETHEROS / MARKET / status) ────────┐
    ├────────────── LIVE MARKET ──────────────┬── AETHEROS DECISION ────┤
    ├──────────────── LIQUIDITY HEATMAP ──────┴─────────────────────────┤
    ├── EVIDENCE/ANALYSIS ───────────────┬──── LIVE EVENTS ─────────────┤
    ├── LOGS ────────────────────────────┼──── AGENTS ──────────────────┤
    └────────────────────────────────────┴──────────────────────────────┘
"""

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .state import WorkspaceState

# Panel ids the keyboard shortcuts select.
PANEL_ORDER = (
    "market", "analysis", "liquidity", "heatmap", "signals",
    "logs", "agents", "system",
)


def _no_data(text: str = "no data yet") -> Text:
    return Text(text, style="dim italic")


def _mock_tag(is_mock: bool) -> str:
    return " [mock]" if is_mock else ""


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------


def panel_header(state: WorkspaceState) -> Panel:
    status = "PAUSED" if state.paused else "LIVE"
    right = state.last_updated[11:19] if state.last_updated else "--:--:--"
    title = (
        f"AETHEROS  |  {state.symbol}  |  {state.timeframe}  |  {status}  |  "
        f"{right}  |  panel: {state.active_panel}"
    )
    return Panel(
        Text(title, style="bold cyan"),
        border_style="cyan",
        padding=(0, 1),
    )


# ----------------------------------------------------------------------
# Market panel
# ----------------------------------------------------------------------


def panel_market(state: WorkspaceState) -> Panel:
    """Candles + price + VWAP + structure + liquidity markers (where present)."""
    rows = []
    candles = state.candles[-14:]
    if not candles:
        body = _no_data("no market data yet")
    else:
        # A simple sparkline of closes with the latest price + last candle OHLC.
        closes = [c.get("close", 0.0) for c in candles]
        spark = _sparkline(closes)
        last = candles[-1]
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_row(
            Text.assemble(
                ("price ", "dim"), (f"{last.get('close', 0):.2f}", "bold white"),
                ("  ", ""), spark,
            )
        )
        grid.add_row(
            Text(
                f"O {last.get('open',0):.2f}  H {last.get('high',0):.2f}  "
                f"L {last.get('low',0):.2f}  C {last.get('close',0):.2f}",
                style="white",
            )
        )
        # Structure / VWAP overlays when the intel read has them.
        intel = state.intel or {}
        tech = intel.get("technical") or {}
        struct = intel.get("structure") or {}
        if tech.get("vwap") is not None:
            grid.add_row(Text(f"VWAP {tech['vwap']:.2f}", style="magenta"))
        if struct.get("trend"):
            grid.add_row(
                Text(
                    f"trend {struct['trend']}  "
                    f"strength {struct.get('trend_strength', 0):.2f}",
                    style="green" if struct["trend"] == "uptrend" else "yellow",
                )
            )
        # Liquidity overlay markers (sweeps/absorption the heatmap showed).
        hm = state.heatmap or {}
        if hm.get("sweep") or hm.get("absorption"):
            marks = []
            if hm.get("sweep"):
                marks.append(f"sweep {hm['sweep']}")
            if hm.get("absorption"):
                marks.append(f"absorb {hm['absorption']}")
            grid.add_row(Text(" ".join(marks), style="bold yellow"))
        body = grid
    return Panel(body, title="LIVE MARKET", border_style="green")


def _sparkline(values, *, use_blocks: bool = True) -> Text:
    """A tiny close-price sparkline.

    Uses block glyphs on Unicode-capable terminals and a plain-ASCII ramp
    otherwise (cp1252 consoles can't encode the block characters).
    """
    if not values:
        return Text("")
    import sys
    blocks = use_blocks and sys.stdout.encoding not in ("cp1252", "mbcs")
    chars = "▁▂▃▄▅▆▇█" if blocks else " .:-=+*#"
    lo, hi = min(values), max(values)
    span = hi - lo or 1e-9
    glyphs = "".join(
        chars[min(len(chars) - 1, int((v - lo) / span * (len(chars) - 1)))]
        for v in values
    )
    return Text(glyphs, style="cyan")
    if not values:
        return Text("")
    lo, hi = min(values), max(values)
    span = hi - lo or 1e-9
    glyphs = "".join(
        chars[min(len(chars) - 1, int((v - lo) / span * (len(chars) - 1)))]
        for v in values
    )
    return Text(glyphs, style="cyan")


# ----------------------------------------------------------------------
# Decision / signal panel
# ----------------------------------------------------------------------


def panel_decision(state: WorkspaceState) -> Panel:
    """The signal read -- direction, probability, confidence, R:R, invalidation."""
    a = state.assessment
    if not a:
        a = (state.report or {}).get("signal", {})
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    direction = (a.get("direction") or "unknown") if a else "unknown"
    style = {
        "up": "bold green", "bullish": "bold green",
        "down": "bold red", "bearish": "bold red",
    }.get(direction, "bold yellow")
    grid.add_row(Text(direction.upper(), style=style))
    if a:
        prob = a.get("probability")
        if prob and prob.get("up") is not None:
            grid.add_row(
                Text(f"Probability  {prob['up'] * 100:.0f}%", style="white")
            )
        else:
            grid.add_row(Text("Probability  -- (not reliable)", style="dim"))
        grid.add_row(Text(f"Confidence   {a.get('confidence', '--')}", style="white"))
        rr = a.get("risk_reward_ratio") or (a.get("risk") or {}).get("risk_reward_ratio")
        if rr is not None:
            grid.add_row(Text(f"R:R          1:{rr:.1f}", style="white"))
        inv = a.get("invalidation") or (a.get("risk") or {}).get("invalidation")
        if inv:
            grid.add_row(Text(f"Invalidation {inv}", style="yellow", overflow="fold"))
        if a.get("is_mock"):
            grid.add_row(Text("[mock data]", style="dim red"))
    else:
        grid.add_row(_no_data())
    return Panel(grid, title="AETHEROS DECISION", border_style="magenta")


# ----------------------------------------------------------------------
# Heatmap panel
# ----------------------------------------------------------------------


def panel_heatmap(state: WorkspaceState) -> Panel:
    """The time x price liquidity heatmap (rendered from the real surface)."""
    hm = state.heatmap
    if not hm or not hm.get("projection"):
        body = _no_data("no heatmap yet")
    else:
        body = Text(hm["projection"], style="white")
    return Panel(body, title="LIQUIDITY HEATMAP", border_style="blue")


# ----------------------------------------------------------------------
# Analysis / evidence panel
# ----------------------------------------------------------------------


def panel_analysis(state: WorkspaceState) -> Panel:
    """Evidence + regime + structure + the supporting/contradicting split."""
    intel = state.intel or {}
    assessment = state.assessment or {}
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")

    regime = (intel.get("features") or {}).get("regime") or (
        (state.report or {}).get("market_regime") or {}
    ).get("regime")
    if regime:
        grid.add_row(Text(f"regime      {regime}", style="cyan"))
    feats = intel.get("features") or {}
    if feats:
        grid.add_row(
            Text(
                f"trend {feats.get('trend_strength',0):.2f}  "
                f"mom {feats.get('momentum',0):+.2f}  "
                f"vol {feats.get('volatility_state','--')}  "
                f"adxv {feats.get('adx',0):.2f}",
                style="white",
            )
        )
        grid.add_row(
            Text(
                f"volume {feats.get('volume_state','--')}  "
                f"netflow {feats.get('volume_delta',0):+.2f}  "
                f"relvol {feats.get('relative_volume',0):.2f}",
                style="white",
            )
        )

    # Evidence split -- supporting vs contradicting (the spec's must-show).
    sup = assessment.get("supporting") or []
    con = assessment.get("contradicting") or []
    if sup:
        grid.add_row(Text(f"+ supporting ({len(sup)})", style="green"))
        for e in sup[:4]:
            grid.add_row(Text(f"   + {e.get('detail','')[:46]}", style="green"))
    if con:
        grid.add_row(Text(f"- contradicting ({len(con)})", style="red"))
        for e in con[:4]:
            grid.add_row(Text(f"   - {e.get('detail','')[:46]}", style="red"))
    if not sup and not con and not feats:
        grid.add_row(_no_data())
    return Panel(grid, title="EVIDENCE / ANALYSIS", border_style="yellow")


# ----------------------------------------------------------------------
# Events panel
# ----------------------------------------------------------------------


def panel_events(state: WorkspaceState) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left", overflow="fold")
    events = state.events[-12:]
    if not events:
        table.add_row(_no_data("no events yet"))
    for e in reversed(events):
        ts = e.timestamp[11:19] if e.timestamp else "--:--:--"
        name = e.name + ("[m]" if e.is_mock else "")
        table.add_row(
            Text(f"{ts} {name}", style="cyan"),
            Text(e.detail[:50], style="dim"),
        )
    return Panel(table, title="LIVE EVENTS", border_style="cyan")


# ----------------------------------------------------------------------
# Logs panel
# ----------------------------------------------------------------------


def panel_logs(state: WorkspaceState, *, level: str = "INFO") -> Panel:
    colors = {
        "INFO": "white", "WARNING": "yellow", "ERROR": "bold red",
        "DEBUG": "dim", "CRITICAL": "bold red",
    }
    table = Table.grid(expand=True)
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left", overflow="fold")
    levels = {"INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"}
    rows = [
        l for l in state.logs if l.level in levels
    ][-12:]
    if not rows:
        table.add_row(_no_data("no logs yet"))
    for l in rows:
        ts = l.timestamp[11:19] if l.timestamp else "--:--:--"
        table.add_row(
            Text(f"{ts} {l.level[:4]}", style=colors.get(l.level, "white")),
            Text(f"{l.logger}: {l.message[:46]}", style="dim"),
        )
    return Panel(table, title=f"LOGS [{level}+]", border_style="white")


# ----------------------------------------------------------------------
# Agents panel
# ----------------------------------------------------------------------


def panel_agents(state: WorkspaceState) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="left", overflow="fold")
    agents = state.agents
    if not agents:
        table.add_row(_no_data("no components tracked"))
    for a in agents:
        style = {
            "running": "green", "ready": "green", "idle": "dim",
            "offline": "red", "disabled": "dim red",
        }.get(a.status, "white")
        table.add_row(
            Text(a.name, style="white"),
            Text(f"{a.status}{'[m]' if a.is_mock else ''} {a.detail[:30]}",
                 style=style),
        )
    return Panel(table, title="AGENTS", border_style="magenta")


# ----------------------------------------------------------------------
# System / data-source / memory-status panel
# ----------------------------------------------------------------------


def panel_system(state: WorkspaceState) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="left", overflow="fold")
    rows = state.system
    if not rows:
        table.add_row(_no_data("no system metrics"))
    for m in rows:
        style = {
            "ok": "green", "up": "green", "ready": "green",
            "down": "red", "offline": "red", "disabled": "dim",
            "mock": "yellow",
        }.get(m.status.lower(), "white")
        table.add_row(
            Text(m.name, style="white"),
            Text(f"{m.status} {m.detail[:30]}", style=style),
        )
    # Memory is a status/placeholder boundary only -- honest, not implemented.
    mem = "enabled" if state.memory_enabled else "placeholder (not implemented)"
    table.add_row(
        Text("memory", style="white"),
        Text(mem, style="dim"),
    )
    return Panel(table, title="SYSTEM / DATA / MEMORY", border_style="blue")
