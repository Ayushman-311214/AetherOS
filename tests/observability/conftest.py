"""
Fixtures for the live-execution-trace tests.

The trace layer publishes through a *process-wide* module-level bus
(``aetheros.runtime.events.publisher``). Every fixture here restores that global
on teardown so one test's bus can never leak into the next -- the same isolation
``tests/conftest.py`` gives the loguru sinks.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
import pytest_asyncio

from aetheros.runtime.events import publisher
from aetheros.runtime.events.event_bus import EventBus
from aetheros.core.observability import TraceEvent


@pytest.fixture
def event_bus() -> Iterator[EventBus]:
    """A fresh bus wired as the global publisher, torn down afterwards.

    ``emit_trace`` reaches the bus only through ``publisher.publish`` / the
    module-level ``_event_bus``; setting and restoring it here is what lets a
    test observe emitted events without a full bootstrap.
    """

    previous = publisher._event_bus
    bus = EventBus()
    publisher.set_event_bus(bus)
    try:
        yield bus
    finally:
        publisher._event_bus = previous


class TraceCollector:
    """A recording subscriber -- the honest witness for what was emitted.

    Sync handler, exactly as ``TraceRecorder._on_trace_event`` is: it runs on
    the publish path and only appends. ``types`` is the ordered list of
    ``TraceEventType`` values, which is what the pipeline assertions compare.
    """

    # EventBus.subscribe logs ``handler.__name__``; a plain callable instance has
    # none, so give it one rather than have the (silenced) debug log raise.
    __name__ = "TraceCollector"

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def __call__(self, event: Any) -> None:
        if isinstance(event, TraceEvent):
            self.events.append(event)

    @property
    def types(self) -> list[Any]:
        return [e.event_type for e in self.events]

    def of_type(self, event_type: Any) -> list[TraceEvent]:
        return [e for e in self.events if e.event_type == event_type]


@pytest_asyncio.fixture
async def collector(event_bus: EventBus) -> TraceCollector:
    """A :class:`TraceCollector` already subscribed to the bus.

    ``@pytest_asyncio.fixture`` (not a plain ``@pytest.fixture``) because the
    suite runs pytest-asyncio in its default *strict* mode -- no ``asyncio_mode``
    in ``pyproject.toml`` -- where an async fixture wired with the plain
    decorator would hand the test an un-awaited coroutine instead of a
    subscribed collector.
    """

    sink = TraceCollector()
    await event_bus.subscribe(TraceEvent, sink)
    return sink
