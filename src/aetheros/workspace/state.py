"""
Workspace state -- the single shared data model every panel reads.

``WorkspaceState`` is pure data, deliberately free of any rendering or trading
logic. It accumulates what the intelligence layer produced (the latest report /
signal assessment / market-intel read / heatmap), the events and logs the
system emitted, and the agent/system status -- all in bounded ring buffers so
a long session can't grow without limit.

It is the seam between "intelligence" and "presentation": the event adapter
writes into it, the view-model builders read out of it, and a future GUI could
consume the identical structure instead of terminal renderables.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class LogLine:
    """One captured log record for the LOGS panel."""

    level: str            # INFO | WARNING | ERROR | DEBUG
    logger: str
    message: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class EventRow:
    """One intelligence event as the EVENTS panel shows it."""

    name: str
    instrument_key: str
    detail: str
    timestamp: str
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "instrument_key": self.instrument_key,
            "detail": self.detail,
            "timestamp": self.timestamp,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class AgentRow:
    """One tracked component's status for the AGENTS panel."""

    name: str
    status: str           # "running" | "idle" | "ready" | "offline" | "disabled"
    detail: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class SystemMetric:
    """One system-health line for the SYSTEM panel."""

    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


class WorkspaceState:
    """
    The live workspace data model.

    Bounded by design: ``max_events`` / ``max_logs`` cap the ring buffers, so
    the state stays small and constant regardless of how long the session runs.
    The ``report`` / ``assessment`` / ``intel`` / ``heatmap`` fields are simply
    the latest ``to_dict()`` payloads the intelligence layer produced -- the
    state stores them verbatim and computes nothing.
    """

    def __init__(
        self,
        *,
        symbol: str = "SPY",
        timeframe: str = "1d",
        max_events: int = 60,
        max_logs: int = 200,
        memory_enabled: bool = False,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.paused = False
        self.active_panel = "market"     # the focused / full-screen panel id
        self.memory_enabled = memory_enabled

        # The latest intelligence payloads (to_dict() verbatim).
        self.report: dict[str, Any] | None = None
        self.assessment: dict[str, Any] | None = None
        self.intel: dict[str, Any] | None = None          # market-intel read
        self.heatmap: dict[str, Any] | None = None        # surface/heatmap view
        self.candles: list[dict[str, Any]] = []           # recent bars (tail)

        self._events: deque[EventRow] = deque(maxlen=max_events)
        self._logs: deque[LogLine] = deque(maxlen=max_logs)
        self._agents: dict[str, AgentRow] = {}
        self._system: dict[str, SystemMetric] = {}
        self._errors: list[str] = []
        self.last_updated: str = ""

    # ------------------------------------------------------------------
    # Introspection for panels
    # ------------------------------------------------------------------

    @property
    def events(self) -> tuple[EventRow, ...]:
        return tuple(self._events)

    @property
    def logs(self) -> tuple[LogLine, ...]:
        return tuple(self._logs)

    @property
    def agents(self) -> tuple[AgentRow, ...]:
        return tuple(self._agents.values())

    @property
    def system(self) -> tuple[SystemMetric, ...]:
        return tuple(self._system.values())

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)

    # ------------------------------------------------------------------
    # Mutations (the adapter drives these; the renderer never writes)
    # ------------------------------------------------------------------

    def add_event(self, event: EventRow) -> None:
        self._events.append(event)
        self.last_updated = _utcnow().isoformat()

    def add_log(self, line: LogLine) -> None:
        self._logs.append(line)

    def set_agent(self, row: AgentRow) -> None:
        self._agents[row.name] = row

    def set_system(self, metric: SystemMetric) -> None:
        self._system[metric.name] = metric

    def add_error(self, message: str) -> None:
        self._errors.append(message)
        if len(self._errors) > 20:
            self._errors = self._errors[-20:]

    def set_symbol(self, symbol: str) -> None:
        self.symbol = symbol.strip().upper() or self.symbol

    def set_timeframe(self, timeframe: str) -> None:
        self.timeframe = timeframe.strip() or self.timeframe

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def set_panel(self, panel: str) -> None:
        self.active_panel = panel
