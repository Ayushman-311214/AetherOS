"""
Best-effort emission and the timed span context (PHASES 2, 5, 12).

The contract these tests hold the emitter to: emitting never changes how a run
behaves (a missing bus is swallowed), a wired bus receives the event with
redaction already applied, and ``trace_context`` brackets a block with a
started/completed pair on success -- or a failed event and a *re-raise* on error,
so tracing observes a failure without ever suppressing it.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.core.observability import (
    TraceEventType,
    TraceStatus,
    emit_trace,
    trace_context,
)
from aetheros.runtime.events import publisher
from aetheros.runtime.events.event_bus import EventBus

# ``TraceCollector`` (the recording subscriber) is defined in this package's
# conftest and injected via the ``collector`` fixture; it is annotated as ``Any``
# here because tests/ has no __init__.py, so the sibling conftest is not
# importable by name -- only its fixtures are shared.


class TestEmitTraceIsBestEffort:
    @pytest.mark.asyncio
    async def test_no_bus_configured_is_swallowed(self) -> None:
        # The publisher raises RuntimeError when unset; emit_trace must absorb it
        # so a component that traces before bootstrap is untouched.
        previous = publisher._event_bus
        publisher._event_bus = None
        try:
            await emit_trace(
                TraceEventType.INPUT_RECEIVED, message="no one is listening"
            )
        finally:
            publisher._event_bus = previous

    @pytest.mark.asyncio
    async def test_a_raising_subscriber_does_not_surface(
        self, event_bus: EventBus
    ) -> None:
        # A handler that blows up past the bus's own isolation must still not
        # reach the emitting component.
        def boom(event: object) -> None:
            raise RuntimeError("subscriber failed")

        from aetheros.core.observability import TraceEvent

        await event_bus.subscribe(TraceEvent, boom)
        # No exception escapes.
        await emit_trace(TraceEventType.AGENT_STARTED, message="still fine")


class TestEmitTracePublishes:
    @pytest.mark.asyncio
    async def test_the_event_reaches_a_subscriber(
        self, collector: Any
    ) -> None:
        await emit_trace(
            TraceEventType.TOOL_SELECTED,
            message="mouse_position",
            status=TraceStatus.INFO,
            run_id="run-1",
            iteration=1,
            metadata={"tool_name": "mouse_position"},
        )

        assert collector.types == [TraceEventType.TOOL_SELECTED]
        event = collector.events[0]
        assert event.message == "mouse_position"
        assert event.run_id == "run-1"
        assert event.metadata["tool_name"] == "mouse_position"

    @pytest.mark.asyncio
    async def test_redaction_is_applied_on_the_way_out(
        self, collector: Any
    ) -> None:
        # Defence in depth: even if a caller hands a forbidden key, it never
        # reaches a subscriber.
        await emit_trace(
            TraceEventType.LLM_RESPONSE_RECEIVED,
            metadata={"api_key": "sk-secret", "model": "fake-model"},
            payload={"password": "hunter2", "content_preview": "hi"},
        )

        event = collector.events[0]
        assert event.metadata["api_key"] == "[redacted]"
        assert event.metadata["model"] == "fake-model"
        assert event.payload["password"] == "[redacted]"
        assert event.payload["content_preview"] == "hi"


class TestTraceContext:
    @pytest.mark.asyncio
    async def test_success_emits_started_then_completed_with_duration(
        self, collector: Any
    ) -> None:
        async with trace_context(
            TraceEventType.PLANNER_STARTED,
            TraceEventType.PLANNER_COMPLETED,
            run_id="run-1",
        ) as span:
            span.update(message="decided", metadata={"decision": "final"})

        assert collector.types == [
            TraceEventType.PLANNER_STARTED,
            TraceEventType.PLANNER_COMPLETED,
        ]

        started, completed = collector.events
        assert started.status is TraceStatus.STARTED
        assert completed.status is TraceStatus.SUCCESS
        assert completed.message == "decided"
        assert completed.metadata["decision"] == "final"
        # The completed event carries the measured span.
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0.0

    @pytest.mark.asyncio
    async def test_failure_emits_a_failed_event_and_reraises(
        self, collector: Any
    ) -> None:
        with pytest.raises(ValueError, match="boom"):
            async with trace_context(
                TraceEventType.PLANNER_STARTED,
                TraceEventType.PLANNER_COMPLETED,
                failed_type=TraceEventType.ERROR,
                run_id="run-1",
            ):
                raise ValueError("boom")

        assert collector.types == [
            TraceEventType.PLANNER_STARTED,
            TraceEventType.ERROR,
        ]
        failed = collector.events[1]
        assert failed.status is TraceStatus.FAILED
        # A safe "type: message" string, never a raw traceback.
        assert failed.error == "ValueError: boom"
        assert failed.duration_ms is not None
