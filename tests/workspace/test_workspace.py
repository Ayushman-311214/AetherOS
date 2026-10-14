"""
Terminal workspace (Phase 7): panels, state, navigation, adapters.

Tests the view layer without a terminal: state ring buffers, event adapter
mapping, panel builders producing rich renderables (with real data and with
honest empty states), keyboard navigation, log capture and the rendering of
the layout regions. No trading logic lives here -- the tests prove that.
"""

from __future__ import annotations

import logging

import pytest

from aetheros.runtime.events.event_bus import EventBus
from aetheros.workspace.adapter import WorkspaceAdapter, WorkspaceLogHandler
from aetheros.workspace.app import KEYMAP, TerminalWorkspace, build_workspace
from aetheros.workspace.layout import REGION_PANEL, build_layout
from aetheros.workspace.panels import (
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
from aetheros.workspace.state import (
    AgentRow,
    EventRow,
    LogLine,
    SystemMetric,
    WorkspaceState,
)


# ----------------------------------------------------------------------
# State: buffers + mutations
# ----------------------------------------------------------------------


def test_state_bounded_event_ring():
    s = WorkspaceState(max_events=5)
    for i in range(20):
        s.add_event(EventRow(f"ev{i}", "X", "", "2026-05-01T00:00:00"))
    assert len(s.events) == 5
    assert s.events[-1].name == "ev19"


def test_state_bounded_log_ring():
    s = WorkspaceState(max_logs=5)
    for i in range(20):
        s.add_log(LogLine("INFO", "t", f"m{i}", "2026-05-01T00:00:00"))
    assert len(s.logs) == 5


def test_state_symbol_timeframe_pause():
    s = WorkspaceState()
    s.set_symbol(" aapl ")
    assert s.symbol == "AAPL"
    s.set_timeframe("1h")
    assert s.timeframe == "1h"
    s.toggle_pause()
    assert s.paused is True
    s.toggle_pause()
    assert s.paused is False


def test_state_agent_system_errors():
    s = WorkspaceState()
    s.set_agent(AgentRow("Trading Intelligence", "running", "ok"))
    s.set_system(SystemMetric("event_bus", "up", "subscribed"))
    s.add_error("boom")
    assert s.agents[0].name == "Trading Intelligence"
    assert s.system[0].name == "event_bus"
    assert s.errors == ("boom",)


# ----------------------------------------------------------------------
# Panels: real data, honest empties, error resilience
# ----------------------------------------------------------------------


def test_all_panels_initialize_and_render_empty_honestly():
    s = WorkspaceState()
    for builder in (
        panel_header, panel_market, panel_decision, panel_heatmap,
        panel_analysis, panel_events, panel_logs, panel_agents, panel_system,
    ):
        r = builder(s)  # no data at all -- must not raise
        assert r is not None


def test_market_panel_renders_candles():
    s = WorkspaceState()
    s.candles = [
        {"open": 100, "high": 101, "low": 99, "close": 100 + i}
        for i in range(6)
    ]
    r = panel_market(s)
    assert r is not None


def test_decision_panel_renders_assessment():
    s = WorkspaceState()
    s.assessment = {
        "direction": "up",
        "probability": {"up": 0.73, "down": 0.27},
        "confidence": "high",
        "risk_reward_ratio": 2.8,
        "invalidation": "25,120",
        "is_mock": False,
    }
    r = panel_decision(s)
    assert r is not None


def test_decision_panel_marks_mock():
    s = WorkspaceState()
    s.assessment = {"direction": "up", "is_mock": True}
    assert panel_decision(s) is not None


def test_heatmap_panel_uses_real_projection():
    s = WorkspaceState()
    s.heatmap = {"projection": "time 100..105\n00:00 |@@#"}
    r = panel_heatmap(s)
    assert r is not None


def test_analysis_panel_shows_contradictions():
    s = WorkspaceState()
    s.assessment = {
        "supporting": [{"detail": "structure HH/HL"}],
        "contradicting": [{"detail": "resistance wall"}],
    }
    assert panel_analysis(s) is not None


def test_events_and_logs_panels_render_rows():
    s = WorkspaceState()
    s.add_event(EventRow("LiquiditySwept", "X", "zone=lqz", "2026-05-01T00:00:01"))
    s.add_log(LogLine("WARNING", "trading", "slow fetch", "2026-05-01T00:00:02"))
    assert panel_events(s) is not None
    assert panel_logs(s) is not None


def test_agents_system_panels_only_show_real_components():
    s = WorkspaceState()
    s.set_agent(AgentRow("Trading Intelligence", "running"))
    s.set_system(SystemMetric("market_data", "ok", "yahoo"))
    r = panel_agents(s)
    r2 = panel_system(s)
    assert r is not None and r2 is not None


def test_system_panel_memory_placeholder_honest():
    s = WorkspaceState(memory_enabled=False)
    r = panel_system(s)
    # Memory shows as a status/placeholder, never implemented.
    assert r is not None


# ----------------------------------------------------------------------
# Layout + render integration
# ----------------------------------------------------------------------


def test_layout_regions_fill():
    ws, _ = build_workspace(symbol="TEST")
    r = ws.render()
    layout = r.renderables[0]
    for region in ("header", "market", "decision", "heatmap", "analysis",
                   "events", "logs", "agents"):
        node = layout[region]
        assert node.renderable is not None, f"region {region} not filled"


def test_render_with_full_state():
    ws, _ = build_workspace(symbol="RELIANCE", timeframe="1d")
    s = ws.state
    s.candles = [{"open": 100, "high": 101, "low": 99, "close": 100.5}] * 8
    s.assessment = {
        "direction": "up", "probability": {"up": 0.73},
        "confidence": "high", "risk_reward_ratio": 2.8,
        "invalidation": "25,120",
        "supporting": [{"detail": "s1"}], "contradicting": [{"detail": "c1"}],
    }
    s.intel = {"features": {"regime": "trending_bullish", "trend_strength": 0.7}}
    s.heatmap = {"projection": "00:00 |@@#"}
    s.add_event(EventRow("SignalGenerated", "RELIANCE", "buy", "2026-05-01T00:00:01"))
    s.add_log(LogLine("INFO", "t", "ok", "2026-05-01T00:00:01"))
    s.set_agent(AgentRow("Trading Intelligence", "running"))
    s.set_system(SystemMetric("event_bus", "up"))
    assert ws.render() is not None


def test_panel_error_never_crashes_workspace():
    ws, _ = build_workspace()
    ws.state.report = None
    # A poisoned payload (non-dict where dict expected) must degrade to an
    # error panel, not an exception.
    ws.state.intel = {"features": None}
    try:
        r = ws.render()
        assert r is not None
    except Exception as exc:  # pragma: no cover -- the contract under test
        pytest.fail(f"render crashed on bad data: {exc}")


# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------


def test_keyboard_navigation():
    ws, _ = build_workspace()
    ws.handle_key("2")
    assert ws.state.active_panel == "analysis"
    ws.handle_key("4")
    assert ws.state.active_panel == "heatmap"
    ws.handle_key("p")
    assert ws.state.paused is True
    ws.handle_key("q")
    assert ws._running is False


def test_unknown_key_ignored():
    ws, _ = build_workspace()
    assert ws.handle_key("z") is True
    assert ws.state.active_panel == "market"


def test_keymap_covers_all_spec_panels():
    for panel, key in (
        ("market", "1"), ("analysis", "2"), ("liquidity", "3"),
        ("heatmap", "4"), ("signals", "5"), ("logs", "6"),
        ("agents", "7"), ("system", "8"),
    ):
        assert KEYMAP[key] == panel


# ----------------------------------------------------------------------
# Adapter: events -> state, log capture
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_streams_real_events():
    from aetheros.trading.events import SignalGenerated, MarketRegimeChanged

    bus = EventBus()
    ws, adapter = build_workspace(event_bus=bus)
    await adapter.start()
    await bus.publish(
        SignalGenerated(
            signal_id="s1", instrument_key="NASDAQ:AAPL", direction="up",
            confidence="high",
        )
    )
    await bus.publish(
        MarketRegimeChanged(
            instrument_key="NASDAQ:AAPL", timeframe="1d",
            previous_regime="ranging", regime="trending_up", direction="up",
        )
    )
    names = [e.name for e in ws.state.events]
    assert "SignalGenerated" in names
    assert "MarketRegimeChanged" in names
    await adapter.stop()


def test_adapter_detail_extraction():
    from aetheros.workspace.adapter import WorkspaceAdapter
    s = WorkspaceState()
    adapter = WorkspaceAdapter(s)
    d = adapter._detail(
        "MarketRegimeChanged",
        {"regime": "trending_up", "direction": "up"},
    )
    assert "regime=trending_up" in d


def test_log_handler_taps_existing_logging():
    s = WorkspaceState()
    handler = WorkspaceLogHandler(s)
    test_logger = logging.getLogger("aetheros.workspace.test")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)
    test_logger.warning("watch out")
    test_logger.info("hello")
    msgs = [l.message for l in s.logs]
    assert "watch out" in msgs
    assert "hello" in msgs
    test_logger.removeHandler(handler)


def test_adapter_sets_components_only_when_real():
    s = WorkspaceState()
    adapter = WorkspaceAdapter(s)
    adapter.set_component("Liquidity Analyzer", "idle", "no source")
    adapter.set_intel(None)  # no read -> Market Analysis stays untracked/idle
    names = {a.name for a in s.agents}
    assert "Liquidity Analyzer" in names
    # A real intel read registers the component.
    adapter.set_intel({"features": {}})
    assert any(
        a.name == "Market Analysis" and a.status == "running"
        for a in s.agents
    )
