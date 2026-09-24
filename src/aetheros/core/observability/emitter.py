"""
Best-effort emission of trace events.

The one rule this module exists to enforce: *emitting a trace must never change
how a run behaves*. A component calls :func:`emit_trace` at a natural seam and
carries on regardless of whether a bus is wired, whether a recorder is
listening, or whether the publish raised. Every failure -- no bus configured
(``RuntimeError`` from the publisher), a serialization edge case, a handler
blowing up -- is swallowed here so business logic upstream is untouched. This is
the "observational only, must NOT control business logic" guarantee in code.

Payloads are run through the ``redaction`` helpers on the way out, a defence in
depth on top of the ``.describe()`` projections callers are expected to pass:
``metadata`` is bounded by :func:`safe_metadata`, and ``payload`` keeps its
already-truncated previews but has forbidden keys stripped by
:func:`redact_keys`.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from ...runtime.events.publisher import publish
from .events import TraceEvent, TraceEventType, TraceStatus
from .redaction import redact_keys, safe_metadata


async def emit_trace(
    event_type: TraceEventType,
    *,
    message: str = "",
    stage: str = "",
    status: TraceStatus = TraceStatus.INFO,
    run_id: str | None = None,
    task_id: str | None = None,
    iteration: int | None = None,
    duration_ms: float | None = None,
    metadata: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Publish one trace event, swallowing every failure.

    Never raises: a missing bus, a redaction hiccup, or a misbehaving subscriber
    must not surface into the caller's control flow. The trace layer is an
    observer, so its faults stay its own.
    """

    try:
        event = TraceEvent.create(
            event_type,
            message=message,
            stage=stage,
            status=status,
            run_id=run_id,
            task_id=task_id,
            iteration=iteration,
            duration_ms=duration_ms,
            metadata=safe_metadata(dict(metadata) if metadata else None),
            payload=redact_keys(dict(payload) if payload else None),
            error=error,
        )
    except Exception:
        # Building the event should never fail, but if it does the caller must
        # not pay for it.
        return

    try:
        await publish(event)
    except RuntimeError:
        # No EventBus configured yet (unit tests, early bootstrap). Expected;
        # the run proceeds with nobody listening.
        return
    except Exception:
        # A subscriber raised past the bus's own isolation, or the publish path
        # broke. Still not the caller's problem.
        return


@dataclass(slots=True)
class TraceSpan:
    """Mutable handle a :func:`trace_context` body uses to enrich the closing event.

    The started event fires immediately with what is known up front; the body
    then records the outcome (a message, counts, a preview) and the completed --
    or failed -- event carries it. Nothing here is emitted directly; the context
    manager reads these fields when the block exits.
    """

    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def update(
        self,
        *,
        message: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if metadata:
            self.metadata.update(metadata)
        if payload:
            self.payload.update(payload)


@asynccontextmanager
async def trace_context(
    started_type: TraceEventType,
    completed_type: TraceEventType,
    *,
    failed_type: TraceEventType = TraceEventType.ERROR,
    stage: str = "",
    message: str = "",
    run_id: str | None = None,
    task_id: str | None = None,
    iteration: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AsyncIterator[TraceSpan]:
    """Bracket a stage with a started event and a timed completed/failed event.

    Emits ``started_type`` on entry, yields a :class:`TraceSpan` the body fills
    in, and on exit emits ``completed_type`` (SUCCESS) with the measured
    ``duration_ms`` -- or, if the block raised, ``failed_type`` (FAILED) carrying
    a safe ``type: message`` error string before re-raising. The re-raise matters:
    tracing observes the failure (PHASE 12) but never suppresses it, so the
    agent's own error handling still runs.
    """

    span = TraceSpan(message=message)
    start = time.perf_counter()

    await emit_trace(
        started_type,
        stage=stage,
        message=message,
        status=TraceStatus.STARTED,
        run_id=run_id,
        task_id=task_id,
        iteration=iteration,
        metadata=metadata,
    )

    try:
        yield span
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        await emit_trace(
            failed_type,
            stage=stage,
            message=span.message or message,
            status=TraceStatus.FAILED,
            run_id=run_id,
            task_id=task_id,
            iteration=iteration,
            duration_ms=elapsed_ms,
            metadata=span.metadata,
            payload=span.payload,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        await emit_trace(
            completed_type,
            stage=stage,
            message=span.message or message,
            status=TraceStatus.SUCCESS,
            run_id=run_id,
            task_id=task_id,
            iteration=iteration,
            duration_ms=elapsed_ms,
            metadata=span.metadata,
            payload=span.payload,
        )


__all__ = ["emit_trace", "trace_context", "TraceSpan"]
