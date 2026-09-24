"""
Live execution-trace observability for AetherOS.

A thin, *observer-only* layer that sits alongside ``core.logging``: components
emit structured :class:`TraceEvent` values at their natural seams, those events
travel the existing :class:`~aetheros.runtime.events.event_bus.EventBus`, and a
single :class:`TraceRecorder` subscribes to render a live Rich dashboard and
persist a JSONL trace. Nothing here controls business logic -- an emit failure is
swallowed, and a run behaves identically whether or not anyone is listening.

See ``events`` for the event vocabulary, ``emitter`` for the best-effort publish
helper, ``levels`` for verbosity filtering, ``redaction`` for the log-safe
projections, ``recorder`` for the subscriber, ``ui`` for the dashboard and
``persistence`` for the JSONL sink.
"""

from __future__ import annotations

from .emitter import TraceSpan, emit_trace, trace_context
from .events import TraceEvent, TraceEventType, TraceStatus
from .levels import TraceLevel, level_for_event, resolve_level
from .persistence import TraceFileWriter
from .pipeline import (
    ExecutionPipeline,
    PipelineStage,
    PipelineStatus,
    StageKind,
)
from .recorder import TraceRecorder
from .redaction import redact_keys, safe_metadata, safe_preview, truncate_value
from .ui import LiveTraceUI

__all__ = [
    "TraceEvent",
    "TraceEventType",
    "TraceStatus",
    "TraceLevel",
    "TraceRecorder",
    "TraceFileWriter",
    "LiveTraceUI",
    "ExecutionPipeline",
    "PipelineStage",
    "PipelineStatus",
    "StageKind",
    "emit_trace",
    "trace_context",
    "TraceSpan",
    "level_for_event",
    "resolve_level",
    "safe_metadata",
    "safe_preview",
    "truncate_value",
    "redact_keys",
]
