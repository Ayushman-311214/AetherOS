"""
The live terminal dashboard (PHASE 7).

The dashboard is pure presentation and must be optional: construction is
side-effect free, it downgrades silently when there is no TTY to draw on (that is
where JSONL persistence carries the trace instead), and no render path may ever
raise into the run. These tests hold it to exactly that -- they do not try to
assert on rendered pixels, only that the contract around drawing is safe.
"""

from __future__ import annotations

from rich.panel import Panel

from aetheros.core.observability import (
    LiveTraceUI,
    TraceEvent,
    TraceEventType,
    TraceStatus,
)


class _NonTerminalConsole:
    """A stand-in console that reports it is not a terminal (e.g. a pipe)."""

    is_terminal = False


class TestLifecycle:
    def test_construction_is_side_effect_free(self) -> None:
        ui = LiveTraceUI()
        assert ui.is_active is False

    def test_start_declines_when_not_a_terminal(self) -> None:
        # Into a pipe or a file the dashboard must not animate; it stays inactive.
        ui = LiveTraceUI(console=_NonTerminalConsole())
        assert ui.start() is False
        assert ui.is_active is False

    def test_update_and_stop_are_no_ops_while_inactive(self) -> None:
        # A recorder always owns a UI and calls these even when nothing is drawn;
        # they must never raise.
        ui = LiveTraceUI(console=_NonTerminalConsole())
        ui.start()
        ui.update([])
        ui.stop()
        assert ui.is_active is False

    def test_stop_is_safe_to_double_call(self) -> None:
        ui = LiveTraceUI(console=_NonTerminalConsole())
        ui.stop()
        ui.stop()


class TestRender:
    def test_render_returns_a_panel(self) -> None:
        ui = LiveTraceUI(console=_NonTerminalConsole())
        assert isinstance(ui._render([], header={}), Panel)

    def test_render_tolerates_a_full_event_row(self) -> None:
        # A completed row exercises the duration suffix; a failed row exercises
        # the error suffix and the red styling -- neither may raise.
        completed = TraceEvent.create(
            TraceEventType.TOOL_EXECUTION_COMPLETED,
            message="mouse_position",
            status=TraceStatus.SUCCESS,
            run_id="run-1",
            iteration=1,
            duration_ms=12.5,
        )
        failed = TraceEvent.create(
            TraceEventType.TOOL_EXECUTION_FAILED,
            message="move_mouse",
            status=TraceStatus.FAILED,
            run_id="run-1",
            iteration=2,
            duration_ms=3.0,
            error="ToolError: boom",
        )
        panel = ui_render_rows([completed, failed])
        assert isinstance(panel, Panel)


def ui_render_rows(events: list[TraceEvent]) -> Panel:
    ui = LiveTraceUI(console=_NonTerminalConsole())
    return ui._render(
        events, header={"run_id": "run-1", "level": "normal", "count": len(events)}
    )
