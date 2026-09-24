"""
The live terminal dashboard (PHASE 7).

A thin Rich renderer over a rolling window of the most recent trace events. It
holds no trace state of its own beyond what it is handed each refresh -- the
:class:`~aetheros.core.observability.recorder.TraceRecorder` owns the ring buffer
and calls :meth:`update` -- and every Rich interaction is wrapped so a headless
or non-TTY environment silently downgrades to "no dashboard" rather than raising
into the run. That is the PHASE 7 contract in one place: a clean live view when a
terminal can show one, and no obligation on anything upstream when it cannot.

Uses a single ``rich.live.Live`` so the frame is redrawn *in place* on every
event instead of scrolling a fresh copy -- the "do NOT flood the terminal /
update without repeatedly printing the whole dashboard" requirement.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .events import TraceEvent
from .pipeline import ExecutionPipeline, PipelineStage, PipelineStatus

# Pipeline status -> Rich style + glyph. Kept here (presentation) rather than on
# the model so colours can be tuned without touching the event contract. The
# RUNNING node is highlighted so the currently-active stage is obvious at a
# glance.
_STATUS_STYLE: dict[PipelineStatus, str] = {
    PipelineStatus.PENDING: "dim",
    PipelineStatus.RUNNING: "bold yellow",
    PipelineStatus.COMPLETED: "green",
    PipelineStatus.FAILED: "bold red",
    PipelineStatus.WARNING: "yellow",
}

_STATUS_GLYPH: dict[PipelineStatus, str] = {
    PipelineStatus.PENDING: "○",
    PipelineStatus.RUNNING: "⏳",
    PipelineStatus.COMPLETED: "✅",
    PipelineStatus.FAILED: "❌",
    PipelineStatus.WARNING: "⚠️",
}

_STATUS_WORD: dict[PipelineStatus, str] = {
    PipelineStatus.PENDING: "PENDING",
    PipelineStatus.RUNNING: "RUNNING",
    PipelineStatus.COMPLETED: "COMPLETED",
    PipelineStatus.FAILED: "FAILED",
    PipelineStatus.WARNING: "WARNING",
}


class LiveTraceUI:
    """Render a run as a live, in-place vertical execution pipeline.

    Construction is cheap and side-effect free; nothing touches the terminal
    until :meth:`start`. If Rich is unavailable or the stream is not a TTY the
    UI marks itself inactive and every method becomes a no-op, so a recorder can
    always own one without caring whether it can actually draw.

    The dashboard draws the connected flow (USER → AGENT → LLM → PLANNER →
    ACTION → TOOL EXECUTOR → TOOL RESULT → OBSERVATION → AGENT LOOP → … → FINAL)
    from the :class:`~aetheros.core.observability.pipeline.ExecutionPipeline`
    projection of the events it is handed -- it holds no trace state of its own
    and never plans, calls an LLM or executes a tool.
    """

    def __init__(self, *, console: Any | None = None, max_rows: int = 40) -> None:
        self._max_rows = max_rows
        self._live: Any | None = None
        self._active = False
        self._title = "AetherOS Live Execution Trace"

        # Import Rich lazily and defensively: the trace layer must not make Rich
        # a hard import of the whole app, and a missing/broken Rich just means no
        # dashboard.
        try:
            from rich.console import Console

            self._console = console or Console(stderr=True)
            self._ok = True
        except Exception:
            self._console = None
            self._ok = False

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> bool:
        """Enter the Rich Live context. Returns whether a dashboard is showing."""

        if not self._ok or self._active or self._console is None:
            return self._active

        # No point animating into a pipe or a file; that is where JSONL
        # persistence carries the trace instead.
        if not getattr(self._console, "is_terminal", False):
            return False

        try:
            from rich.live import Live

            self._live = Live(
                self._render([], header={}),
                console=self._console,
                auto_refresh=False,
                transient=False,
            )
            self._live.start()
            self._active = True
        except Exception:
            self._live = None
            self._active = False

        return self._active

    def update(
        self,
        events: Sequence[TraceEvent],
        *,
        header: dict[str, Any] | None = None,
    ) -> None:
        """Redraw the dashboard from the recorder's current window. Never raises."""

        if not self._active or self._live is None:
            return
        try:
            self._live.update(self._render(events, header or {}))
            self._live.refresh()
        except Exception:
            # A render glitch must not propagate; drop the frame.
            pass

    def stop(self) -> None:
        """Leave the Live context, restoring the terminal. Safe to double-call."""

        if self._live is not None:
            try:
                self._live.stop()
            except Exception:
                pass
        self._live = None
        self._active = False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self, events: Sequence[TraceEvent], header: dict[str, Any]) -> Any:
        from rich.console import Group
        from rich.panel import Panel
        from rich.text import Text

        pipeline = ExecutionPipeline.from_events(
            events, run_id=header.get("run_id") or None
        )
        stages = pipeline.visible_stages()

        run_id = pipeline.run_id or header.get("run_id") or "-"
        level = header.get("level") or "-"

        if not stages:
            body: Any = Text("waiting for events…", style="dim")
            subtitle = f"run={run_id}   level={level}"
            return Panel(
                body, title=self._title, subtitle=subtitle, border_style="blue"
            )

        # Cap on very long runs so the live frame fits a terminal; the JSONL trace
        # keeps the complete record regardless.
        shown = stages[-self._max_rows :]
        renderables: list[Any] = []
        if len(shown) < len(stages):
            hidden = len(stages) - len(shown)
            renderables.append(Text(f"… {hidden} earlier stage(s) hidden", style="dim"))
            renderables.append(self._connector())

        for index, stage in enumerate(shown):
            renderables.append(self._stage_block(stage))
            if index < len(shown) - 1:
                renderables.append(self._connector())

        if pipeline.complete:
            duration = self._fmt_ms(pipeline.duration_ms)
            word = _STATUS_WORD.get(pipeline.status, "DONE")
            style = _STATUS_STYLE.get(pipeline.status, "green")
            renderables.append(Text(f"■ RUN {word}   duration = {duration}", style=style))

        status_word = _STATUS_WORD.get(pipeline.status, "-").lower()
        subtitle = f"run={run_id}   {status_word}   level={level}"
        return Panel(
            Group(*renderables),
            title=self._title,
            subtitle=subtitle,
            border_style="blue",
        )

    def _connector(self) -> Any:
        from rich.text import Text

        return Text("   │\n   ▼", style="dim")

    def _stage_block(self, stage: PipelineStage) -> Any:
        from rich.text import Text

        style = _STATUS_STYLE.get(stage.status, "white")
        glyph = _STATUS_GLYPH.get(stage.status, "·")

        header = Text()
        header.append(f"{stage.icon} ")
        title = stage.title
        if stage.kind.name == "LOOP" and stage.iteration is not None:
            title = f"{title}  (iteration {stage.iteration})"
        header.append(title, style="bold")
        header.append(f"   {glyph} ", style=style)
        header.append(_STATUS_WORD.get(stage.status, ""), style=style)
        if stage.duration_ms is not None:
            header.append(f"   ({stage.duration_ms:.0f}ms)", style="dim")

        block = Text()
        block.append_text(header)
        if stage.description:
            block.append("\n")
            block.append(f"   {stage.description}", style=style if stage.status
                         in (PipelineStatus.FAILED, PipelineStatus.WARNING) else "white")
        for line in stage.details:
            block.append("\n")
            block.append(f"     - {line}", style="dim")
        return block

    @staticmethod
    def _fmt_ms(duration_ms: float | None) -> str:
        if duration_ms is None:
            return "-"
        if duration_ms >= 1000:
            return f"{duration_ms / 1000:.2f}s"
        return f"{duration_ms:.0f}ms"


__all__ = ["LiveTraceUI"]
