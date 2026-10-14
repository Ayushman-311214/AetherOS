"""
The single trace subscriber (PHASES 2, 6, 8, 9, 12).

``TraceRecorder`` is an *observer*: it subscribes once to the shared bus, gates
every event by the configured level, keeps a bounded in-memory window and hands
kept events to the file sink. These tests pin the behaviour the CLI and the
dashboard depend on -- the level gate, the ERROR floor that lets a failure
surface even at a low level, and the runtime ``set_level``/``clear`` controls --
and confirm the recorder never publishes or otherwise steers the run.
"""

from __future__ import annotations

import pytest

from aetheros.core.observability import (
    TraceEvent,
    TraceEventType,
    TraceLevel,
    TraceRecorder,
    TraceStatus,
)
from aetheros.runtime.events.event_bus import EventBus


def _event(
    event_type: TraceEventType,
    *,
    status: TraceStatus = TraceStatus.INFO,
    run_id: str | None = None,
) -> TraceEvent:
    return TraceEvent.create(event_type, status=status, run_id=run_id)


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_subscribes_and_events_are_captured(
        self, event_bus: EventBus
    ) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.NORMAL)
        assert await recorder.start() is True

        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED, run_id="run-1"))

        assert recorder.status()["events_kept"] == 1
        assert recorder.recent()[0].event_type is TraceEventType.TOOL_SELECTED
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_so_later_events_are_ignored(
        self, event_bus: EventBus
    ) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.NORMAL)
        await recorder.start()
        await recorder.stop()

        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))

        # Nothing reaches a stopped recorder.
        assert recorder.status()["events_seen"] == 0

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self, event_bus: EventBus) -> None:
        recorder = TraceRecorder(event_bus=event_bus)
        await recorder.start()
        await recorder.stop()
        await recorder.stop()


class TestLevelGate:
    @pytest.mark.asyncio
    async def test_a_below_threshold_stage_is_seen_but_not_kept(
        self, event_bus: EventBus
    ) -> None:
        # At MINIMAL, an ordinary NORMAL stage is counted as seen but filtered out.
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.MINIMAL)
        await recorder.start()

        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))

        status = recorder.status()
        assert status["events_seen"] == 1
        assert status["events_kept"] == 0
        assert recorder.recent() == []
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_a_major_stage_survives_a_low_level(
        self, event_bus: EventBus
    ) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.MINIMAL)
        await recorder.start()

        await event_bus.publish(_event(TraceEventType.INPUT_RECEIVED))

        assert recorder.status()["events_kept"] == 1
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_off_keeps_nothing(self, event_bus: EventBus) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.OFF)
        await recorder.start()

        await event_bus.publish(_event(TraceEventType.INPUT_RECEIVED))

        assert recorder.status()["events_kept"] == 0
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_a_failure_rides_the_error_floor(self, event_bus: EventBus) -> None:
        # PHASE 12: at ERROR level an ordinary stage is hidden, but the same stage
        # once it FAILED is pulled down to the ERROR floor and surfaces.
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.ERROR)
        await recorder.start()

        await event_bus.publish(
            _event(TraceEventType.TOOL_ARGUMENTS_VALIDATED, status=TraceStatus.INFO)
        )
        await event_bus.publish(
            _event(TraceEventType.TOOL_ARGUMENTS_VALIDATED, status=TraceStatus.FAILED)
        )

        kept = recorder.recent()
        assert len(kept) == 1
        assert kept[0].status is TraceStatus.FAILED
        await recorder.stop()


class TestRuntimeControls:
    @pytest.mark.asyncio
    async def test_set_level_reopens_the_gate(self, event_bus: EventBus) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.OFF)
        await recorder.start()

        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))
        assert recorder.status()["events_kept"] == 0

        assert recorder.set_level("normal") is TraceLevel.NORMAL
        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))
        assert recorder.status()["events_kept"] == 1
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_clear_empties_the_window(self, event_bus: EventBus) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.NORMAL)
        await recorder.start()
        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))
        assert recorder.recent()

        recorder.clear()
        assert recorder.recent() == []
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_recent_returns_a_bounded_tail(self, event_bus: EventBus) -> None:
        # The in-memory window is a ring buffer: a long run cannot grow it without
        # limit, yet the kept counter still reflects everything that passed.
        recorder = TraceRecorder(
            event_bus=event_bus, level=TraceLevel.NORMAL, buffer_size=3
        )
        await recorder.start()
        for _ in range(5):
            await event_bus.publish(_event(TraceEventType.TOOL_SELECTED))

        assert len(recorder.recent()) == 3
        assert recorder.status()["events_kept"] == 5
        assert len(recorder.recent(limit=2)) == 2
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_status_reports_a_flat_snapshot(self, event_bus: EventBus) -> None:
        recorder = TraceRecorder(event_bus=event_bus, level=TraceLevel.NORMAL)
        await recorder.start()
        await event_bus.publish(_event(TraceEventType.TOOL_SELECTED, run_id="run-9"))

        status = recorder.status()
        assert status["running"] is True
        assert status["subscribed"] is True
        assert status["level"] == "normal"
        assert status["persist"] is False
        assert status["last_run_id"] == "run-9"
        await recorder.stop()
