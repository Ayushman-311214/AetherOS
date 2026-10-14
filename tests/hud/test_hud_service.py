"""
The HUD service — voice event in, overlay snapshot out.

This is the only place the HUD and voice packages meet, and they meet through
the EventBus rather than through an import: voice publishes, the service folds
each event into a snapshot, and the snapshot goes down a pipe. So the real
EventBus and the real voice event classes are used here; only the child process
is faked, which is what makes the whole path runnable with no Qt and no display.

The other half of the contract is containment. An overlay that will not start,
or that dies mid-conversation, must cost the indicator and nothing else.
"""

from __future__ import annotations

import asyncio

import pytest

from aetheros.hud.config import HUDConfig
from aetheros.hud.service import HUDService
from aetheros.hud.state import HUDState
from aetheros.voice.events import (
    LLMThinkingFinished,
    SpeechStarted,
    SpeechTranscribed,
    ToolExecutionFinished,
    ToolExecutionStarted,
    VoiceAudioLevel,
    VoiceError,
    VoiceServiceStarted,
    VoiceServiceStopped,
    VoiceStateChanged,
)
from aetheros.voice.state import VoiceState

# ==============================================================
# Lifecycle
# ==============================================================


class TestLifecycle:

    @pytest.mark.asyncio
    async def test_start_brings_the_overlay_up(
        self,
        make_service,
        process,
        bus,
    ) -> None:

        hud = make_service(process)

        assert await hud.start() is True

        try:
            assert hud.is_running is True
            assert process.start_calls == 1

            # OFFLINE until voice reports itself up: the overlay must not claim
            # to be listening for something that is not running.
            assert hud.state is HUDState.OFFLINE

            # Subscribed to the voice events it displays.
            assert bus.listener_count(VoiceStateChanged) == 1

        finally:
            await hud.stop()

    @pytest.mark.asyncio
    async def test_a_process_that_will_not_start_is_reported(
        self,
        make_service,
        fake_process,
    ) -> None:
        """
        No Qt, no display, or a broken driver. AetherOS still has to work.
        """

        hud = make_service(fake_process(can_start=False))

        assert await hud.start() is False

        assert hud.is_running is False
        assert hud.failure
        assert hud.is_visible is False

    @pytest.mark.asyncio
    async def test_stop_releases_the_subscriptions(
        self,
        make_service,
        process,
        bus,
    ) -> None:
        """
        A bus that keeps the old service's bound methods would push snapshots
        into a dead pipe after a restart.
        """

        hud = make_service(process)

        await hud.start()
        await hud.stop()

        assert bus.listener_count(VoiceStateChanged) == 0
        assert process.stop_calls == 1
        assert hud.state is HUDState.OFFLINE

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(
        self,
        make_service,
        process,
    ) -> None:

        hud = make_service(process)

        await hud.start()
        await hud.stop()
        await hud.stop()

        assert process.stop_calls == 1

    @pytest.mark.asyncio
    async def test_start_is_idempotent(
        self,
        make_service,
        process,
    ) -> None:

        hud = make_service(process)

        assert await hud.start() is True
        assert await hud.start() is True

        try:
            assert process.start_calls == 1

        finally:
            await hud.stop()

    @pytest.mark.asyncio
    async def test_the_overlay_is_visible_once_it_reports_ready(
        self,
        service,
        process,
    ) -> None:

        assert service.is_visible is False

        process.report_ready(pid=1234)

        await asyncio.sleep(0.35)

        assert service.is_visible is True
        assert service.status()["pid"] == 1234


# ==============================================================
# Events
# ==============================================================


class TestVoiceEvents:

    @pytest.mark.asyncio
    async def test_voice_starting_wakes_the_overlay(
        self,
        service,
        process,
        bus,
    ) -> None:

        await bus.publish(VoiceServiceStarted(stt_provider="null"))

        assert service.state is HUDState.IDLE
        assert process.states[-1] == "IDLE"

    @pytest.mark.asyncio
    async def test_a_state_change_is_forwarded(
        self,
        service,
        process,
        bus,
    ) -> None:

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.IDLE,
                current=VoiceState.LISTENING,
            )
        )

        assert service.state is HUDState.LISTENING
        assert process.last_snapshot["state"] == "LISTENING"

    @pytest.mark.asyncio
    async def test_a_transcript_retires_the_previous_answer(
        self,
        service,
        bus,
    ) -> None:
        """
        Otherwise the overlay shows this turn's question beside the last one's
        reply.
        """

        await bus.publish(LLMThinkingFinished(response="Previously."))

        assert service.snapshot.response == "Previously."

        await bus.publish(SpeechTranscribed(text="open notepad"))

        assert service.snapshot.transcript == "open notepad"
        assert service.snapshot.response == ""

    @pytest.mark.asyncio
    async def test_a_multiline_reply_is_collapsed_for_the_overlay(
        self,
        service,
        bus,
    ) -> None:
        """
        The HUD is one line; a raw LLM reply would break the layout.
        """

        await bus.publish(
            LLMThinkingFinished(response="line one\n\n   line two\t")
        )

        assert service.snapshot.response == "line one line two"

    @pytest.mark.asyncio
    async def test_the_running_tool_is_shown_then_cleared(
        self,
        service,
        bus,
    ) -> None:

        await bus.publish(ToolExecutionStarted(tool="click"))

        assert service.snapshot.action == "click"

        await bus.publish(ToolExecutionFinished(tool="click", success=True))

        assert service.snapshot.action == ""

    @pytest.mark.asyncio
    async def test_a_late_finish_does_not_blank_a_later_tool(
        self,
        service,
        bus,
    ) -> None:
        """
        Several calls can run in one turn; the display shows the current one.
        """

        await bus.publish(ToolExecutionStarted(tool="click"))
        await bus.publish(ToolExecutionStarted(tool="type_text"))

        await bus.publish(ToolExecutionFinished(tool="click", success=True))

        assert service.snapshot.action == "type_text"

    @pytest.mark.asyncio
    async def test_speak_alone_still_fills_in_the_reply(
        self,
        service,
        bus,
    ) -> None:
        """
        `speak()` used directly means nothing reasoned, so no response event.
        """

        await bus.publish(SpeechStarted(text="Good morning."))

        assert service.snapshot.response == "Good morning."

    @pytest.mark.asyncio
    async def test_voice_stopping_takes_the_overlay_offline(
        self,
        service,
        bus,
    ) -> None:

        await bus.publish(VoiceServiceStarted())
        await bus.publish(VoiceServiceStopped())

        assert service.state is HUDState.OFFLINE


# ==============================================================
# Audio levels
# ==============================================================


class TestAudioLevels:

    @pytest.mark.asyncio
    async def test_a_level_is_coalesced_rather_than_sent_immediately(
        self,
        service,
        process,
        bus,
    ) -> None:
        """
        Levels arrive at ~20 Hz. Sending each one on the publishing path would
        put a pipe write inside the audio callback's critical path, so the pump
        sends the latest value instead.
        """

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.IDLE,
                current=VoiceState.LISTENING,
            )
        )

        before = len(process.snapshots)

        await bus.publish(VoiceAudioLevel(level=0.4))
        await bus.publish(VoiceAudioLevel(level=0.9))

        assert len(process.snapshots) == before
        assert service.snapshot.amplitude == pytest.approx(0.9)

        # The pump ticks at 0.05s while a turn is in flight.
        await asyncio.sleep(0.2)

        assert len(process.snapshots) > before
        assert process.last_snapshot["amplitude"] == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_a_level_is_ignored_while_resting(
        self,
        service,
        bus,
    ) -> None:
        """
        A sample that arrives after capture ended would make a resting overlay
        twitch.
        """

        await bus.publish(VoiceServiceStarted())
        await bus.publish(VoiceAudioLevel(level=0.8))

        assert service.snapshot.amplitude == 0.0

    @pytest.mark.asyncio
    async def test_a_level_is_clamped(
        self,
        service,
        bus,
    ) -> None:
        """
        The visualizer scales by this directly; an out-of-range value would
        draw outside the window.
        """

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.IDLE,
                current=VoiceState.SPEAKING,
            )
        )

        await bus.publish(VoiceAudioLevel(level=7.5))

        assert service.snapshot.amplitude == 1.0


# ==============================================================
# Errors
# ==============================================================


class TestErrors:

    @pytest.mark.asyncio
    async def test_an_error_is_held_on_screen(
        self,
        service,
        bus,
    ) -> None:
        """
        Voice enters ERROR and settles straight back to IDLE so the next turn
        can start at once — correct for the state machine, but it would make the
        error invisible. Holding the *display* is a presentation concern, so it
        happens here.
        """

        await bus.publish(VoiceError(message="Microphone unavailable."))

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.THINKING,
                current=VoiceState.ERROR,
            )
        )

        assert service.state is HUDState.ERROR
        assert service.snapshot.message == "Microphone unavailable."

        # Voice has already gone back to resting; the overlay has not.
        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.ERROR,
                current=VoiceState.IDLE,
            )
        )

        assert service.state is HUDState.ERROR

    @pytest.mark.asyncio
    async def test_a_new_turn_overrides_the_error_hold(
        self,
        service,
        bus,
    ) -> None:
        """
        The user acting on the system always beats a cosmetic hold.
        """

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.IDLE,
                current=VoiceState.ERROR,
            )
        )

        await bus.publish(
            VoiceStateChanged(
                previous=VoiceState.ERROR,
                current=VoiceState.LISTENING,
            )
        )

        assert service.state is HUDState.LISTENING
        assert service.snapshot.message == ""


# ==============================================================
# Containment
# ==============================================================


class TestContainment:

    @pytest.mark.asyncio
    async def test_a_dead_overlay_stops_the_updates(
        self,
        service,
        process,
    ) -> None:
        """
        Deliberately not restarted: a HUD that crashes on startup would
        otherwise be relaunched forever.
        """

        process.crash(exit_code=3)

        # Resting cadence is 0.25s.
        await asyncio.sleep(0.4)

        assert service.is_running is False
        assert "3" in (service.failure or "")

    @pytest.mark.asyncio
    async def test_a_publish_survives_a_dead_overlay(
        self,
        service,
        process,
        bus,
    ) -> None:
        """
        Voice must not learn about the overlay by having an event raise.
        """

        process.crash()

        await bus.publish(SpeechTranscribed(text="still talking"))

        assert service.snapshot.transcript == "still talking"

    @pytest.mark.asyncio
    async def test_a_malformed_child_message_is_ignored(
        self,
        service,
        process,
    ) -> None:

        process.inbox.append({"type": "ready", "pid": "not a number"})
        process.inbox.append({"nonsense": True})

        await asyncio.sleep(0.35)

        assert service.is_running is True

    @pytest.mark.asyncio
    async def test_the_service_runs_without_a_bus(
        self,
        fake_process,
    ) -> None:
        """
        `hud demo` and `hud state` drive the overlay with no voice at all.
        """

        hud = HUDService(
            config=HUDConfig(enabled=True),
            event_bus=None,
            process=fake_process(),
        )

        assert await hud.start() is True

        try:
            hud.show(HUDState.THINKING)

            assert hud.state is HUDState.THINKING

        finally:
            await hud.stop()


# ==============================================================
# Manual display
# ==============================================================


class TestManualDisplay:

    @pytest.mark.asyncio
    async def test_show_accepts_a_name(
        self,
        service,
        process,
    ) -> None:
        """
        `hud state THINKING` passes a string straight through.
        """

        service.show("thinking")

        assert service.state is HUDState.THINKING
        assert process.states[-1] == "THINKING"

    @pytest.mark.asyncio
    async def test_an_unknown_name_does_not_break_the_display(
        self,
        service,
    ) -> None:

        service.show("BANANA")

        assert service.state is HUDState.IDLE

    @pytest.mark.asyncio
    async def test_the_sequence_number_only_advances(
        self,
        service,
        process,
        bus,
    ) -> None:
        """
        The renderer uses it to tell that it fell behind.
        """

        await bus.publish(VoiceServiceStarted())
        await bus.publish(SpeechTranscribed(text="one"))
        await bus.publish(ToolExecutionStarted(tool="click"))

        sequences = [
            int(payload["sequence"]) for payload in process.snapshots
        ]

        assert sequences == sorted(sequences)
        assert len(set(sequences)) == len(sequences)

    @pytest.mark.asyncio
    async def test_status_is_flat_and_complete(
        self,
        service,
        process,
    ) -> None:
        """
        `hud status` renders this directly, so every value has to be printable.
        """

        process.report_stats(fps=58.5, quality="medium")

        await asyncio.sleep(0.35)

        status = service.status()

        assert status["running"] is True
        assert status["state"] == "OFFLINE"
        assert status["fps"] == pytest.approx(58.5)
        assert status["quality"] == "medium"
        assert status["enabled"] is True
