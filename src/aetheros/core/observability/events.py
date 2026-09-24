"""
The trace event vocabulary.

One concrete :class:`TraceEvent` class (not a class per stage) carries a
:class:`TraceEventType` discriminator. That keeps the
:class:`~aetheros.runtime.events.event_bus.EventBus` wiring trivial -- the
recorder subscribes to the single ``TraceEvent`` type and receives every stage --
while ``event_type`` still lets the UI and the level filter tell one stage from
another.

``TraceEvent`` subclasses the project's frozen/slots
:class:`~aetheros.runtime.events.events.Event`, so it inherits ``event_id`` and
``timestamp`` and stays immutable: a record of what happened that can be edited
afterwards is not an audit trail (CLAUDE.md 8/19).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ...runtime.events.events import Event


class TraceEventType(str, Enum):
    """Every stage of the live execution pipeline.

    ``str``-valued so a serialized event reads as ``{"event_type": "tool_selected"}``
    rather than carrying an enum repr, matching the project's other wire enums.
    """

    # -- input / speech-to-text --
    INPUT_RECEIVED = "input_received"
    STT_STARTED = "stt_started"
    STT_COMPLETED = "stt_completed"

    # -- agent --
    AGENT_STARTED = "agent_started"
    AGENT_REQUEST_RECEIVED = "agent_request_received"
    AGENT_ITERATION_STARTED = "agent_iteration_started"
    AGENT_ITERATION_COMPLETED = "agent_iteration_completed"

    # -- llm --
    LLM_REQUEST_STARTED = "llm_request_started"
    LLM_REQUEST_COMPLETED = "llm_request_completed"
    LLM_RESPONSE_RECEIVED = "llm_response_received"

    # -- planner --
    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"
    PLANNER_DECISION = "planner_decision"

    # -- action normalization --
    ACTION_CREATED = "action_created"
    ACTION_NORMALIZED = "action_normalized"

    # -- tools --
    TOOL_SCHEMA_GENERATED = "tool_schema_generated"
    TOOL_SELECTED = "tool_selected"
    TOOL_ARGUMENTS_VALIDATED = "tool_arguments_validated"
    TOOL_EXECUTION_STARTED = "tool_execution_started"
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"

    # -- observation / loop --
    OBSERVATION_CREATED = "observation_created"

    # -- response / text-to-speech --
    FINAL_RESPONSE_CREATED = "final_response_created"
    TTS_STARTED = "tts_started"
    TTS_COMPLETED = "tts_completed"

    # -- diagnostics --
    ERROR = "error"
    WARNING = "warning"


class TraceStatus(str, Enum):
    """How the stage an event reports is doing.

    Kept small and orthogonal to :class:`TraceEventType`: the type says *which*
    stage, the status says *how it went*, so the UI can colour a row without
    re-deriving success from the type.
    """

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# Arbitrary constructor default: every event is built through :meth:`TraceEvent.create`
# or ``emit_trace``, which always supply an explicit type. A default is required only
# because the frozen ``Event`` base gives ``event_id``/``timestamp`` defaults, so
# every field declared after them must default too.
_UNSET_TYPE = TraceEventType.WARNING


@dataclass(frozen=True, slots=True)
class TraceEvent(Event):
    """One observed moment in a run, safe to log and to persist.

    Only observable, log-safe data belongs here: never API keys, credentials,
    system prompts, chain-of-thought, or raw argument *values* (which may carry a
    password a tool was asked to type). Callers pass projections built by
    ``redaction`` and the existing ``.describe()``/``.argument_names`` helpers.
    """

    event_type: TraceEventType = _UNSET_TYPE

    # Human-facing stage label, e.g. "Tool execution" -- what the dashboard row
    # is titled. Distinct from ``event_type`` so the wire value can stay stable
    # while the display label is tuned.
    stage: str = ""

    # A short, already-safe sentence describing what happened.
    message: str = ""

    status: TraceStatus = TraceStatus.INFO

    # Correlation. ``run_id`` follows one request end to end (it is the
    # AgentState.state_id); ``iteration`` is the agent loop turn; ``task_id`` is
    # reserved for multi-agent orchestration and mirrors ``run_id`` until that
    # exists.
    run_id: str | None = None
    task_id: str | None = None
    iteration: int | None = None

    # How long the stage took, when the emitter measured it.
    duration_ms: float | None = None

    # Small, log-safe structured extras (counts, names, model id, ...).
    metadata: dict[str, Any] = field(default_factory=dict)

    # Compact + expandable display payload (e.g. a truncated response preview).
    payload: dict[str, Any] = field(default_factory=dict)

    # A safe error string (type/message), never a full traceback with secrets.
    error: str | None = None

    @classmethod
    def create(
        cls,
        event_type: TraceEventType,
        *,
        message: str = "",
        stage: str = "",
        status: TraceStatus = TraceStatus.INFO,
        run_id: str | None = None,
        task_id: str | None = None,
        iteration: int | None = None,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TraceEvent:
        """Build an event, defaulting the stage label from the type."""

        return cls(
            event_type=event_type,
            stage=stage or _default_stage(event_type),
            message=message,
            status=status,
            run_id=run_id,
            task_id=task_id if task_id is not None else run_id,
            iteration=iteration,
            duration_ms=duration_ms,
            metadata=dict(metadata or {}),
            payload=dict(payload or {}),
            error=error,
        )

    def to_dict(self) -> dict[str, Any]:
        """A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601."""

        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "stage": self.stage,
            "message": self.message,
            "status": self.status.value,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "iteration": self.iteration,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "payload": self.payload,
            "error": self.error,
        }


# Display labels, kept out of the enum so the wire values stay terse.
_STAGE_LABELS: dict[TraceEventType, str] = {
    TraceEventType.INPUT_RECEIVED: "Input",
    TraceEventType.STT_STARTED: "Speech-to-text",
    TraceEventType.STT_COMPLETED: "Speech-to-text",
    TraceEventType.AGENT_STARTED: "Agent",
    TraceEventType.AGENT_REQUEST_RECEIVED: "Agent",
    TraceEventType.AGENT_ITERATION_STARTED: "Agent loop",
    TraceEventType.AGENT_ITERATION_COMPLETED: "Agent loop",
    TraceEventType.LLM_REQUEST_STARTED: "LLM request",
    TraceEventType.LLM_REQUEST_COMPLETED: "LLM request",
    TraceEventType.LLM_RESPONSE_RECEIVED: "LLM response",
    TraceEventType.PLANNER_STARTED: "Planner",
    TraceEventType.PLANNER_COMPLETED: "Planner",
    TraceEventType.PLANNER_DECISION: "Planner decision",
    TraceEventType.ACTION_CREATED: "Action",
    TraceEventType.ACTION_NORMALIZED: "Action",
    TraceEventType.TOOL_SCHEMA_GENERATED: "Tool schema",
    TraceEventType.TOOL_SELECTED: "Tool selected",
    TraceEventType.TOOL_ARGUMENTS_VALIDATED: "Tool arguments",
    TraceEventType.TOOL_EXECUTION_STARTED: "Tool execution",
    TraceEventType.TOOL_EXECUTION_COMPLETED: "Tool execution",
    TraceEventType.TOOL_EXECUTION_FAILED: "Tool execution",
    TraceEventType.OBSERVATION_CREATED: "Observation",
    TraceEventType.FINAL_RESPONSE_CREATED: "Final response",
    TraceEventType.TTS_STARTED: "Text-to-speech",
    TraceEventType.TTS_COMPLETED: "Text-to-speech",
    TraceEventType.ERROR: "Error",
    TraceEventType.WARNING: "Warning",
}


def _default_stage(event_type: TraceEventType) -> str:
    return _STAGE_LABELS.get(event_type, event_type.value)


__all__ = ["TraceEvent", "TraceEventType", "TraceStatus"]
