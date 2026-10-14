"""
The single trace subscriber (PHASES 2, 6, 8, 9).

``TraceRecorder`` is the one component that listens for :class:`TraceEvent`
values on the shared :class:`~aetheros.runtime.events.event_bus.EventBus`. It is
an *observer* in the strict sense the brief demands: it consumes events, filters
them by the configured :class:`~aetheros.core.observability.levels.TraceLevel`,
keeps a bounded in-memory window for the live dashboard, and appends each kept
event to the JSONL sink. It never publishes, never calls back into an agent,
planner or executor, and swallows its own failures -- a run behaves identically
whether or not a recorder is attached.

The lifecycle mirrors ``hud/service.py`` deliberately: construct with an
``event_bus``, ``start()`` subscribes the single handler, ``stop()`` unsubscribes
and releases the UI and file handles. Because the bus dispatches by exact type
and every stage is the same ``TraceEvent`` class, one subscription receives the
whole pipeline.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from ...runtime.events.event_bus import EventBus
from ...runtime.events.events import Event
from ..logging import get_logger
from .events import TraceEvent
from .levels import TraceLevel, level_for_event, resolve_level
from .persistence import TraceFileWriter
from .ui import LiveTraceUI

logger = get_logger("trace.recorder")


class TraceRecorder:
    """Subscribe to trace events, filter, display and persist them.

    Everything is best-effort. The recorder holds no lock on correctness: if the
    UI cannot draw, the buffer still fills and the file still writes; if the file
    cannot be written, the dashboard still updates; if nothing works, the run is
    untouched.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        level: TraceLevel | str | int | None = TraceLevel.NORMAL,
        ui: LiveTraceUI | None = None,
        writer: TraceFileWriter | None = None,
        buffer_size: int = 200,
    ) -> None:
        self._bus = event_bus
        self._level = resolve_level(level)
        self._ui = ui
        self._writer = writer

        # Bounded so a long run cannot grow the dashboard's backing store without
        # limit; the UI only ever shows the tail anyway.
        self._events: deque[TraceEvent] = deque(maxlen=buffer_size)

        self._running = False
        self._subscribed = False

        # Lightweight counters for `trace status`.
        self._seen = 0
        self._kept = 0
        self._last_run_id: str | None = None

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self) -> bool:
        """Subscribe to :class:`TraceEvent` and bring up the dashboard."""

        if self._running:
            return True

        if self._ui is not None and self._level > TraceLevel.OFF:
            try:
                self._ui.start()
            except Exception:
                logger.opt(exception=True).debug("Trace UI failed to start.")

        await self._subscribe()
        self._running = True
        logger.info(f"Trace recorder started (level={self._level.name.lower()}).")
        return True

    async def stop(self) -> None:
        """Unsubscribe, stop the dashboard and flush the file. Idempotent."""

        if not self._running and not self._subscribed:
            return

        self._running = False
        await self._unsubscribe()

        if self._ui is not None:
            try:
                self._ui.stop()
            except Exception:
                logger.opt(exception=True).debug("Trace UI failed to stop.")

        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                logger.opt(exception=True).debug("Trace writer failed to close.")

        logger.info("Trace recorder stopped.")

    async def _subscribe(self) -> None:
        bus = self._bus
        if bus is None or self._subscribed:
            return
        await bus.subscribe(TraceEvent, self._on_trace_event)
        self._subscribed = True

    async def _unsubscribe(self) -> None:
        bus = self._bus
        if bus is None or not self._subscribed:
            return
        self._subscribed = False
        try:
            await bus.unsubscribe(TraceEvent, self._on_trace_event)
        except Exception:
            logger.opt(exception=True).debug("Ignoring error while unsubscribing trace.")

    # ==========================================================
    # Handler
    # ==========================================================

    def _on_trace_event(self, event: Event) -> None:
        """Consume one trace event. Sync, on the publish path, never raises.

        Kept synchronous for the same reason the HUD's handlers are: this runs
        inside ``EventBus.publish`` and does only cheap work -- a level compare, a
        deque append, a redraw of an in-place table, and one buffered file line.
        """

        if not isinstance(event, TraceEvent):
            return

        self._seen += 1

        # The level gate is the single place verbosity is decided (PHASE 8);
        # failures ride the ERROR floor via level_for_event so they surface even
        # when the configured level would otherwise hide the stage (PHASE 12).
        if self._level <= TraceLevel.OFF:
            return
        if level_for_event(event.event_type, event.status) > self._level:
            return

        self._kept += 1
        self._last_run_id = event.run_id or self._last_run_id
        self._events.append(event)

        if self._writer is not None:
            self._writer.write(event)

        if self._ui is not None and self._ui.is_active:
            self._ui.update(
                self._events,
                header={
                    "run_id": self._last_run_id,
                    "level": self._level.name.lower(),
                    "count": self._kept,
                },
            )

    # ==========================================================
    # Runtime controls (CLI `trace ...`)
    # ==========================================================

    def set_level(self, level: TraceLevel | str | int | None) -> TraceLevel:
        """Change verbosity on the live recorder (PHASE 10 `trace level <x>`).

        Mutates held state rather than the cached settings: ``get_settings()`` is
        ``@lru_cache``d, so re-reading the environment would not reflect a runtime
        command. Bringing the UI up or down to match keeps ``trace off``/``on``
        honest.
        """

        self._level = resolve_level(level)
        if self._ui is not None:
            if self._level <= TraceLevel.OFF:
                self._ui.stop()
            elif self._running and not self._ui.is_active:
                try:
                    self._ui.start()
                except Exception:
                    logger.opt(exception=True).debug("Trace UI failed to (re)start.")
        return self._level

    @property
    def level(self) -> TraceLevel:
        return self._level

    def clear(self) -> None:
        """Drop the in-memory window (PHASE 10 `trace clear`)."""

        self._events.clear()
        if self._ui is not None and self._ui.is_active:
            self._ui.update([], header={"level": self._level.name.lower(), "count": 0})

    def recent(self, limit: int | None = None) -> list[TraceEvent]:
        """A copy of the buffered events, newest last."""

        events = list(self._events)
        return events if limit is None else events[-limit:]

    def status(self) -> dict[str, Any]:
        """A flat snapshot for `trace status`."""

        return {
            "running": self._running,
            "subscribed": self._subscribed,
            "level": self._level.name.lower(),
            "live_ui": bool(self._ui is not None and self._ui.is_active),
            "persist": self._writer is not None,
            "events_seen": self._seen,
            "events_kept": self._kept,
            "buffered": len(self._events),
            "last_run_id": self._last_run_id,
        }


__all__ = ["TraceRecorder"]
