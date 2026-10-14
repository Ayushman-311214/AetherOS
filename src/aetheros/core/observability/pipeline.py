"""
The execution-pipeline projection (live presentation model).

A *pure, observational* fold of the recorder's rolling ``TraceEvent`` window into
an ordered list of :class:`PipelineStage` values that describe one run as a single
connected flow::

    USER -> AGENT -> LLM -> PLANNER -> ACTION -> TOOL EXECUTOR
         -> TOOL RESULT -> OBSERVATION -> (AGENT LOOP -> ...) -> FINAL -> TTS

This layer plans nothing, calls no LLM, executes no tool and mutates no agent
state -- it only reshapes events that already happened into something a terminal
can draw. A stage never appears unless an event for it actually arrived: the fold
does not invent missing stages, so an unimplemented subsystem (STT/TTS) simply
leaves its stage absent rather than faking it.

Safety: only the already-log-safe fields of a ``TraceEvent`` are read (message,
status, duration_ms, metadata, payload, error). Those projections were built
upstream by ``redaction`` and the ``.describe()``/``.argument_names`` helpers --
raw argument *values*, secrets, prompts and chain-of-thought never reach here, so
the renderer cannot leak them. Argument *names* are shown; argument *values* are
not, because the events deliberately never carried them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Sequence

from .events import TraceEvent, TraceEventType, TraceStatus


class PipelineStatus(str, Enum):
    """How a single pipeline stage is doing, in presentation terms."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"


class StageKind(str, Enum):
    """The visual groups a run's events collapse into, in flow order."""

    USER = "user"
    STT = "stt"
    AGENT = "agent"
    LOOP = "loop"
    LLM = "llm"
    PLANNER = "planner"
    ACTION = "action"
    TOOL_EXEC = "tool_exec"
    TOOL_RESULT = "tool_result"
    OBSERVATION = "observation"
    FINAL = "final"
    TTS = "tts"
    DIAGNOSTIC = "diagnostic"


# Icon + human title per stage group. Presentation only; tuning it never touches
# the event contract.
_KIND_PRESENTATION: dict[StageKind, tuple[str, str]] = {
    StageKind.USER: ("🎤", "USER / VOICE"),
    StageKind.STT: ("📝", "SPEECH-TO-TEXT"),
    StageKind.AGENT: ("🤖", "AGENT"),
    StageKind.LOOP: ("🔄", "AGENT LOOP"),
    StageKind.LLM: ("🧠", "LLM"),
    StageKind.PLANNER: ("📋", "PLANNER"),
    StageKind.ACTION: ("🔧", "ACTION"),
    StageKind.TOOL_EXEC: ("⚙️", "TOOL EXECUTOR"),
    StageKind.TOOL_RESULT: ("📤", "TOOL RESULT"),
    StageKind.OBSERVATION: ("👁", "OBSERVATION"),
    StageKind.FINAL: ("💬", "FINAL RESPONSE"),
    StageKind.TTS: ("🔊", "TEXT-TO-SPEECH"),
    StageKind.DIAGNOSTIC: ("⚠️", "DIAGNOSTIC"),
}

# Which event type feeds which visual group.
_EVENT_KIND: dict[TraceEventType, StageKind] = {
    TraceEventType.INPUT_RECEIVED: StageKind.USER,
    TraceEventType.STT_STARTED: StageKind.STT,
    TraceEventType.STT_COMPLETED: StageKind.STT,
    TraceEventType.AGENT_STARTED: StageKind.AGENT,
    TraceEventType.AGENT_REQUEST_RECEIVED: StageKind.AGENT,
    TraceEventType.AGENT_ITERATION_STARTED: StageKind.LOOP,
    TraceEventType.AGENT_ITERATION_COMPLETED: StageKind.LOOP,
    TraceEventType.LLM_REQUEST_STARTED: StageKind.LLM,
    TraceEventType.LLM_REQUEST_COMPLETED: StageKind.LLM,
    TraceEventType.LLM_RESPONSE_RECEIVED: StageKind.LLM,
    TraceEventType.PLANNER_STARTED: StageKind.PLANNER,
    TraceEventType.PLANNER_COMPLETED: StageKind.PLANNER,
    TraceEventType.PLANNER_DECISION: StageKind.PLANNER,
    TraceEventType.ACTION_CREATED: StageKind.ACTION,
    TraceEventType.ACTION_NORMALIZED: StageKind.ACTION,
    TraceEventType.TOOL_SCHEMA_GENERATED: StageKind.ACTION,
    TraceEventType.TOOL_SELECTED: StageKind.ACTION,
    TraceEventType.TOOL_ARGUMENTS_VALIDATED: StageKind.TOOL_EXEC,
    TraceEventType.TOOL_EXECUTION_STARTED: StageKind.TOOL_EXEC,
    TraceEventType.TOOL_EXECUTION_COMPLETED: StageKind.TOOL_RESULT,
    TraceEventType.TOOL_EXECUTION_FAILED: StageKind.TOOL_RESULT,
    TraceEventType.OBSERVATION_CREATED: StageKind.OBSERVATION,
    TraceEventType.FINAL_RESPONSE_CREATED: StageKind.FINAL,
    TraceEventType.TTS_STARTED: StageKind.TTS,
    TraceEventType.TTS_COMPLETED: StageKind.TTS,
    TraceEventType.ERROR: StageKind.DIAGNOSTIC,
    TraceEventType.WARNING: StageKind.DIAGNOSTIC,
}

# Groups that occur once per run (not per agent-loop iteration).
_RUN_LEVEL: frozenset[StageKind] = frozenset(
    {StageKind.USER, StageKind.STT, StageKind.AGENT, StageKind.FINAL, StageKind.TTS}
)

@dataclass
class PipelineStage:
    """One visible node of the pipeline, folded from one or more trace events.

    ``compact`` is always safe to show; ``details`` are short, already-redacted
    lines (never argument values or secrets) shown beneath the node.
    """

    kind: StageKind
    icon: str
    title: str
    status: PipelineStatus = PipelineStatus.PENDING
    description: str = ""
    details: list[str] = field(default_factory=list)
    timestamp: datetime | None = None
    duration_ms: float | None = None
    iteration: int | None = None

    # Internal status-fold accumulators (not for display).
    _failed: bool = False
    _warning: bool = False
    _success: bool = False
    _started: bool = False
    _info: bool = False

    def _resolve_status(self) -> None:
        """Collapse the accumulated event outcomes into one display status.

        A stage with a start and no success is still *running*; that is what
        makes the currently-active node obvious. Historic running nodes are
        promoted to completed once the pipeline has moved past them (see
        :meth:`ExecutionPipeline._finalize`).
        """

        if self._failed:
            self.status = PipelineStatus.FAILED
        elif self._warning:
            self.status = PipelineStatus.WARNING
        elif self._started and not self._success:
            self.status = PipelineStatus.RUNNING
        elif self._success or self._info:
            self.status = PipelineStatus.COMPLETED
        else:
            self.status = PipelineStatus.PENDING


def _slot_key(kind: StageKind, event: TraceEvent, diag_seq: int) -> tuple[Any, ...]:
    """Group events into stages: once-per-run, once-per-iteration, or unique.

    Diagnostics (ERROR/WARNING) each get their own node so no failure is hidden
    by folding it into a neighbour.
    """

    if kind is StageKind.DIAGNOSTIC:
        return (kind, "diag", diag_seq)
    if kind in _RUN_LEVEL:
        return (kind,)
    iteration = event.iteration if event.iteration is not None else 0
    return (kind, iteration)


def _short(text: Any, limit: int = 110) -> str:
    """Clip a value to a single terminal-friendly line."""

    rendered = "" if text is None else str(text)
    rendered = rendered.replace("\n", " ").strip()
    if len(rendered) <= limit:
        return rendered
    return f"{rendered[:limit]}…"


def _accumulate_status(stage: PipelineStage, status: TraceStatus) -> None:
    if status in (TraceStatus.FAILED, TraceStatus.ERROR):
        stage._failed = True
    elif status is TraceStatus.WARNING:
        stage._warning = True
    elif status is TraceStatus.SUCCESS:
        stage._success = True
    elif status in (TraceStatus.STARTED, TraceStatus.IN_PROGRESS):
        stage._started = True
    elif status is TraceStatus.INFO:
        stage._info = True


def _detail(stage: PipelineStage, line: str) -> None:
    """Append a detail line if it is non-empty and not already present."""

    line = line.strip()
    if line and line not in stage.details:
        stage.details.append(line)


def _apply_event(stage: PipelineStage, event: TraceEvent) -> None:
    """Fold one event's safe fields into its stage's description and details."""

    _accumulate_status(stage, event.status)

    # Earliest timestamp anchors the node; longest measured span is its duration.
    if stage.timestamp is None or event.timestamp < stage.timestamp:
        stage.timestamp = event.timestamp
    if event.duration_ms is not None:
        stage.duration_ms = max(stage.duration_ms or 0.0, event.duration_ms)

    meta = event.metadata or {}
    payload = event.payload or {}
    etype = event.event_type

    if etype is TraceEventType.INPUT_RECEIVED:
        stage.description = _short(event.message or payload.get("goal_preview"))
    elif etype in (TraceEventType.AGENT_STARTED, TraceEventType.AGENT_REQUEST_RECEIVED):
        stage.description = event.message or "request received"
    elif etype in (
        TraceEventType.AGENT_ITERATION_STARTED,
        TraceEventType.AGENT_ITERATION_COMPLETED,
    ):
        stage.iteration = event.iteration
        stage.description = f"iteration {event.iteration}"
    elif etype is TraceEventType.LLM_REQUEST_STARTED:
        provider, model = meta.get("provider"), meta.get("model")
        if provider or model:
            stage.description = f"requesting {provider or '?'}/{model or '?'}"
        if meta.get("tool_count") is not None:
            _detail(stage, f"tools offered: {meta.get('tool_count')}")
    elif etype in (
        TraceEventType.LLM_RESPONSE_RECEIVED,
        TraceEventType.LLM_REQUEST_COMPLETED,
    ):
        stage.description = _short(event.message) or stage.description
        if meta.get("finish_reason"):
            _detail(stage, f"finish: {meta.get('finish_reason')}")
        if meta.get("tool_calls") is not None:
            _detail(stage, f"tool calls: {meta.get('tool_calls')}")
        if payload.get("content_preview"):
            _detail(stage, f"“{_short(payload.get('content_preview'))}”")
    elif etype in (
        TraceEventType.PLANNER_DECISION,
        TraceEventType.PLANNER_STARTED,
        TraceEventType.PLANNER_COMPLETED,
    ):
        stage.description = _short(event.message) or stage.description
        tool = meta.get("tool_name") or meta.get("tool")
        if tool:
            _detail(stage, f"→ tool: {tool}")
        if meta.get("type") or meta.get("decision"):
            _detail(stage, f"decision: {meta.get('type') or meta.get('decision')}")
    elif etype in (
        TraceEventType.TOOL_SELECTED,
        TraceEventType.ACTION_CREATED,
        TraceEventType.ACTION_NORMALIZED,
        TraceEventType.TOOL_SCHEMA_GENERATED,
    ):
        tool = meta.get("tool_name") or event.message
        if tool:
            stage.description = f"tool: {tool}" if stage.kind is StageKind.ACTION else stage.description
        names = meta.get("argument_names")
        if names:
            _detail(stage, f"args (names only): {', '.join(str(n) for n in names)}")
    elif etype is TraceEventType.TOOL_ARGUMENTS_VALIDATED:
        stage.description = stage.description or f"validating {meta.get('tool_name') or ''}".strip()
        _detail(stage, "validation: passed")
        names = meta.get("argument_names")
        if names:
            _detail(stage, f"args (names only): {', '.join(str(n) for n in names)}")
    elif etype is TraceEventType.TOOL_EXECUTION_STARTED:
        stage.description = f"executing {meta.get('tool_name') or event.message or ''}".strip()
    elif etype is TraceEventType.TOOL_EXECUTION_COMPLETED:
        stage.description = f"{event.message or meta.get('tool_name') or 'tool'} → success"
        if payload.get("result_preview"):
            _detail(stage, f"result: {_short(payload.get('result_preview'))}")
    elif etype is TraceEventType.TOOL_EXECUTION_FAILED:
        stage.description = f"{event.message or meta.get('tool_name') or 'tool'} → failed"
        if event.error:
            _detail(stage, _short(event.error))
    elif etype is TraceEventType.OBSERVATION_CREATED:
        stage.description = _short(event.message or payload.get("observation_preview"))
        if meta.get("tool_name"):
            _detail(stage, f"from: {meta.get('tool_name')}")
    elif etype is TraceEventType.FINAL_RESPONSE_CREATED:
        stage.description = _short(event.message or payload.get("response_preview"), 200)
    elif etype in (TraceEventType.TTS_STARTED, TraceEventType.TTS_COMPLETED):
        stage.description = _short(event.message) or "speaking"
    elif etype in (TraceEventType.ERROR, TraceEventType.WARNING):
        stage.description = _short(event.message) or etype.value
        if event.error:
            _detail(stage, _short(event.error))
        if meta.get("tool_name"):
            _detail(stage, f"tool: {meta.get('tool_name')}")
    else:
        stage.description = stage.description or _short(event.message)


@dataclass
class ExecutionPipeline:
    """One run rendered as an ordered, connected sequence of stages."""

    run_id: str | None
    stages: list[PipelineStage]
    complete: bool
    status: PipelineStatus
    duration_ms: float | None

    @classmethod
    def from_events(
        cls,
        events: Sequence[TraceEvent],
        *,
        run_id: str | None = None,
    ) -> "ExecutionPipeline":
        """Fold the recorder's event window into the pipeline for one run.

        The target run is ``run_id`` when given, else the most recent run seen in
        the window -- so a new request (new run_id) naturally replaces the prior
        pipeline instead of merging two requests into one flow.
        """

        target = run_id
        if target is None:
            for event in reversed(events):
                if event.run_id:
                    target = event.run_id
                    break

        selected = [
            e for e in events if target is None or e.run_id is None or e.run_id == target
        ]

        slots: dict[tuple[Any, ...], PipelineStage] = {}
        order: list[tuple[Any, ...]] = []
        diag_seq = 0
        first_ts: datetime | None = None
        last_ts: datetime | None = None

        for event in selected:
            kind = _EVENT_KIND.get(event.event_type)
            if kind is None:
                continue
            if kind is StageKind.DIAGNOSTIC:
                diag_seq += 1
            key = _slot_key(kind, event, diag_seq)
            stage = slots.get(key)
            if stage is None:
                icon, title = _presentation_for(kind, event)
                stage = PipelineStage(
                    kind=kind,
                    icon=icon,
                    title=title,
                    iteration=event.iteration,
                )
                slots[key] = stage
                order.append(key)
            _apply_event(stage, event)

            if first_ts is None or event.timestamp < first_ts:
                first_ts = event.timestamp
            if last_ts is None or event.timestamp > last_ts:
                last_ts = event.timestamp

        stages = [slots[k] for k in order]
        cls._finalize(stages)

        complete = any(s.kind is StageKind.FINAL for s in stages) or any(
            s.kind is StageKind.TTS for s in stages
        )
        if any(s.status is PipelineStatus.FAILED for s in stages):
            status = PipelineStatus.FAILED
        elif complete:
            status = PipelineStatus.COMPLETED
        else:
            status = PipelineStatus.RUNNING

        duration_ms: float | None = None
        if first_ts is not None and last_ts is not None:
            duration_ms = (last_ts - first_ts).total_seconds() * 1000.0

        return cls(
            run_id=target,
            stages=stages,
            complete=complete,
            status=status,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _finalize(stages: list[PipelineStage]) -> None:
        """Resolve each stage's status, then promote passed-through nodes.

        The last stage is the live one, so it keeps a RUNNING marker; every
        earlier RUNNING node is historic and shown as completed.
        """

        for stage in stages:
            stage._resolve_status()
        for stage in stages[:-1]:
            if stage.status is PipelineStatus.RUNNING:
                stage.status = PipelineStatus.COMPLETED

    # Suppress the first-iteration agent-loop marker: iteration 1 is the initial
    # pass (already implied by the AGENT node); the 🔄 marker is meaningful only
    # when the agent actually loops back (iteration >= 2).
    def visible_stages(self) -> list[PipelineStage]:
        out: list[PipelineStage] = []
        for stage in self.stages:
            if stage.kind is StageKind.LOOP and (stage.iteration or 0) < 2:
                continue
            out.append(stage)
        return out


def _presentation_for(kind: StageKind, event: TraceEvent) -> tuple[str, str]:
    """Icon + title for a new stage node, specialised for diagnostics."""

    if kind is StageKind.DIAGNOSTIC:
        if event.event_type is TraceEventType.ERROR:
            return ("❌", "ERROR")
        return ("⚠️", "WARNING")
    return _KIND_PRESENTATION[kind]


__all__ = [
    "ExecutionPipeline",
    "PipelineStage",
    "PipelineStatus",
    "StageKind",
]
