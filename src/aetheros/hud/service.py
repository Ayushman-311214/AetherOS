from __future__ import annotations

import asyncio
import time
from dataclasses import replace
from typing import Any

from ..core.logging.logging import get_logger
from ..runtime.events.event_bus import EventBus
from ..runtime.events.events import Event
from .config import HUDConfig
from .demo import DemoScript
from .process import HUDProcess
from .protocol import (
    MSG_CLOSED,
    MSG_ERROR,
    MSG_READY,
    MSG_STATS,
    Message,
    config_message,
    message_type,
    snapshot_message,
)
from .state import HUDSnapshot, HUDState

#: How often the service talks to the overlay while a turn is in
# flight. Matches the ~20 Hz at which voice publishes audio levels, so
# amplitude updates coalesce one-to-one instead of queueing up.
_ACTIVE_INTERVAL = 0.05

#: The same, while resting. Nothing is moving in IDLE except the
# overlay's own animation, which the child drives on its own, so waking
# 20 times a second here would be pure waste.
_RESTING_INTERVAL = 0.25

#: How long ERROR stays on screen before a return to IDLE is honoured.
#
# The voice pipeline enters ERROR and settles straight back to IDLE so
# the next turn can start immediately, which is correct for it but
# would make the error invisible. Holding the *display* is a presentation
# concern, so it belongs here rather than in the state machine.
_ERROR_DWELL = 2.5

#: Longest text the service will forward. The renderer elides to the
# configured width anyway; this only stops a long LLM reply from being
# pushed through the pipe in full, several times a second.
_MAX_TEXT = 240


class HUDService:
    """
    Keeps the overlay showing what AetherOS is doing.

    Subscribes to the voice events on the existing EventBus, folds them
    into a snapshot, and pushes that to the render process. The
    dependency runs one way only — the HUD never calls into voice, and
    voice has no idea the HUD exists — which is what lets either one be
    absent without the other noticing.

    Every failure here is contained. A HUD that will not start, dies, or
    stops accepting messages is logged and then ignored: the overlay is
    an indicator, and losing an indicator must never take AetherOS with
    it.
    """

    def __init__(
        self,
        *,
        config: HUDConfig | None = None,
        event_bus: EventBus | None = None,
        process: HUDProcess | None = None,
    ) -> None:

        self._config = config or HUDConfig.from_env()
        self._bus = event_bus

        self._logger = get_logger("hud.service")

        # Injectable so tests can drive the whole service against a
        # fake process, with no Qt and no window. An injected one is
        # never replaced; an owned one is rebuilt on every start.
        self._process = process
        self._injected = process is not None

        self._running = False
        self._pump: asyncio.Task[None] | None = None

        self._snapshot = HUDSnapshot(state=HUDState.OFFLINE)

        #: Set when the snapshot has changed but has not been sent. Only
        #: amplitude defers this way; state and text go immediately.
        self._dirty = False

        #: A state that is waiting for the ERROR dwell to expire.
        self._pending_state: HUDState | None = None
        self._error_until = 0.0

        #: Last statistics the child reported, for `hud status`.
        self._fps = 0.0
        self._quality = ""

        #: Set while a demo is driving the overlay, so live voice events
        #: do not fight it for the display.
        self._demo = False

        #: Why the overlay is unavailable, when it is.
        self._failure: str | None = None

        self._subscribed = False

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def config(self) -> HUDConfig:
        return self._config

    @property
    def state(self) -> HUDState:
        return self._snapshot.state

    @property
    def snapshot(self) -> HUDSnapshot:
        return self._snapshot

    @property
    def failure(self) -> str | None:
        return self._failure

    @property
    def is_visible(self) -> bool:
        """
        Whether there is a live overlay on screen.
        """

        process = self._process

        return (
            self._running
            and process is not None
            and process.is_alive
            and process.ready
        )

    def status(self) -> dict[str, Any]:
        """
        A flat snapshot for the CLI.
        """

        process = self._process

        return {
            "running": self._running,
            "visible": self.is_visible,
            "state": str(self._snapshot.state),
            "pid": process.pid if process is not None else None,
            "ready": process.ready if process is not None else False,
            "exit_code": (
                process.exit_code if process is not None else None
            ),
            "failure": self._failure,
            "fps": self._fps or None,
            "quality": self._quality or None,
            "enabled": self._config.enabled,
            "position": self._config.position,
            "size": self._config.pixel_size,
            "opacity": self._config.opacity,
            "target_fps": self._config.fps,
            "requested_quality": self._config.animation_quality,
            "theme": self._config.theme,
            "click_through": self._config.click_through,
            "always_on_top": self._config.always_on_top,
        }

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self) -> bool:
        """
        Show the overlay. Returns whether it came up.

        Reports failure rather than raising it: a machine with no Qt
        runtime, no display, or a broken graphics driver must still get
        a fully working AetherOS.
        """

        if self._running:
            self._logger.debug("HUD service already running.")

            return True

        self._failure = None

        if not self._injected:
            # Rebuilt on every start rather than reused: the
            # configuration may have changed since the last overlay ran,
            # and a fresh object begins from a known state.
            self._process = HUDProcess(self._config)

        self._logger.info("Starting HUD service...")

        if self._process is None or not self._process.start():

            self._failure = (
                self._process.failure
                if self._process is not None
                else None
            ) or "The HUD process did not start."

            self._logger.warning(f"HUD unavailable: {self._failure}")

            return False

        self._running = True

        # OFFLINE until voice reports itself up: the overlay should not
        # claim to be listening for something that is not running.
        self._snapshot = HUDSnapshot(state=HUDState.OFFLINE)
        self._dirty = False

        await self._subscribe()

        self._pump = asyncio.create_task(
            self._pump_loop(),
            name="aetheros-hud-pump",
        )

        self._logger.info(
            f"HUD service started (pid={self._process.pid}, "
            f"quality={self._config.animation_quality}, "
            f"fps={self._config.fps})."
        )

        return True

    async def stop(self) -> None:
        """
        Close the overlay and release everything behind it.

        Ordering matters: stop listening to events first so nothing
        tries to push to a process that is going away, then end the
        pump, then the process itself.
        """

        # Nothing running and no pump means there is nothing to take
        # down, including after a previous stop.
        if not self._running and self._pump is None:
            return

        self._logger.info("Stopping HUD service...")

        self._running = False
        self._demo = False

        await self._unsubscribe()

        pump = self._pump
        self._pump = None

        if pump is not None and not pump.done():

            pump.cancel()

            try:
                await pump

            except (asyncio.CancelledError, Exception):
                pass

        process = self._process

        # Deliberately keeps the reference: `hud status` after a stop
        # should still be able to say how the overlay ended. A fresh
        # start replaces it.
        if process is not None:
            try:
                # Blocking: it waits for the child to actually go, which
                # is the point. Off-thread so a slow Qt teardown cannot
                # stall the shutdown of everything else.
                await asyncio.to_thread(process.stop)

            except Exception:
                self._logger.opt(exception=True).warning(
                    "Ignoring error while stopping the HUD process."
                )

        self._snapshot = HUDSnapshot(state=HUDState.OFFLINE)
        self._pending_state = None
        self._error_until = 0.0

        self._logger.info("HUD service stopped.")

    async def restart(self) -> bool:
        """
        Close the overlay and open a new one.
        """

        await self.stop()

        return await self.start()

    # ==========================================================
    # Display
    # ==========================================================

    def show(
        self,
        state: HUDState | str,
        **fields: object,
    ) -> None:
        """
        Put the overlay into a state directly.

        The manual path, used by `hud state <NAME>` and by anything that
        wants to drive the overlay without voice being involved.
        """

        self._apply_state(HUDState.parse(state), **fields)

    def apply(self, snapshot: HUDSnapshot) -> None:
        """
        Push a complete snapshot as-is.
        """

        self._push(
            replace(snapshot, sequence=self._snapshot.sequence + 1)
        )

    async def reconfigure(self, config: HUDConfig) -> None:
        """
        Apply a new configuration to a running overlay.

        The child rebuilds its window from this, so it is also how
        position, size and quality change without a restart.
        """

        self._config = config

        process = self._process

        if process is None or not self._running:
            return

        process.send(config_message(config.to_dict()))

        self._logger.info("HUD reconfigured.")

    async def demo(
        self,
        *,
        speed: float = 1.0,
        cycles: float = 1.0,
    ) -> None:
        """
        Walk the overlay through every state, with no voice or LLM.

        Runs one pass by default and can be cancelled at any point. This
        is how the animation work is verified visually: no microphone, no
        model, no network, and the same push path a real turn uses.
        """

        script = DemoScript(speed=speed)

        total = script.duration * max(0.1, cycles)

        self._logger.info(
            f"HUD demo running for {total:.1f}s (speed={speed})."
        )

        self._demo = True
        started = time.monotonic()

        try:
            while True:

                elapsed = time.monotonic() - started

                if elapsed >= total:
                    break

                self._push(script.snapshot_at(elapsed))

                await asyncio.sleep(_ACTIVE_INTERVAL)

        finally:
            self._demo = False

            # Leave the overlay somewhere sensible rather than on
            # whichever state the script happened to be showing.
            self._apply_state(
                HUDState.IDLE if self.is_visible else HUDState.OFFLINE
            )

            self._logger.info("HUD demo finished.")

    # ==========================================================
    # Events
    # ==========================================================

    def _handlers(self) -> dict[type[Event], Any]:
        """
        The events the overlay actually reacts to.

        VoiceStateChanged drives the animation; the rest only fill in
        text. Deliberately not every voice event: subscribing to
        something the HUD does not display would just add work on the
        publishing path.

        The voice event types are imported here rather than at module
        level so the HUD package has no structural dependency on the
        voice package. The overlay is then startable, and testable, with
        voice absent entirely — which is the same isolation that lets
        voice run with the overlay absent.
        """

        from ..voice.events import (
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

        return {
            VoiceStateChanged: self._on_state_changed,
            VoiceAudioLevel: self._on_audio_level,
            SpeechTranscribed: self._on_transcribed,
            LLMThinkingFinished: self._on_response,
            ToolExecutionStarted: self._on_tool_started,
            ToolExecutionFinished: self._on_tool_finished,
            SpeechStarted: self._on_speech_started,
            VoiceError: self._on_error,
            VoiceServiceStarted: self._on_voice_started,
            VoiceServiceStopped: self._on_voice_stopped,
        }

    async def _subscribe(self) -> None:

        bus = self._bus

        if bus is None or self._subscribed:
            return

        try:
            handlers = self._handlers()

        except Exception:
            # Voice is not installed or failed to import. The overlay
            # still works; it just has nothing driving it, which is
            # exactly the standalone case.
            self._logger.opt(exception=True).warning(
                "The HUD could not subscribe to voice events."
            )

            return

        for event_type, handler in handlers.items():
            await bus.subscribe(event_type, handler)

        self._subscribed = True

    async def _unsubscribe(self) -> None:

        bus = self._bus

        if bus is None or not self._subscribed:
            return

        self._subscribed = False

        try:
            handlers = self._handlers()

        except Exception:
            return

        for event_type, handler in handlers.items():

            try:
                await bus.unsubscribe(event_type, handler)

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while unsubscribing the HUD."
                )

    # ----------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------

    # Synchronous on purpose. These run on the publishing path, and at
    # 20 Hz for audio levels; a coroutine per event would add a task
    # scheduling round-trip for work that is a dict write and a pipe
    # write.

    def _on_state_changed(self, event: Event) -> None:

        current = getattr(event, "current", None)

        self._apply_state(HUDState.parse(current))

    def _on_audio_level(self, event: Event) -> None:

        level = float(getattr(event, "level", 0.0) or 0.0)

        # Only meaningful while audio is actually flowing. Outside those
        # states a late sample would make a resting overlay twitch.
        if not self._snapshot.is_audio_reactive:
            return

        self._mutate(
            immediate=False,
            amplitude=max(0.0, min(1.0, level)),
        )

    def _on_transcribed(self, event: Event) -> None:

        # A new utterance retires the previous answer, so the overlay
        # never shows this turn's question beside the last one's reply.
        self._mutate(
            transcript=_clip(getattr(event, "text", "")),
            response="",
        )

    def _on_response(self, event: Event) -> None:

        self._mutate(response=_clip(getattr(event, "response", "")))

    def _on_tool_started(self, event: Event) -> None:

        self._mutate(action=_clip(getattr(event, "tool", "")))

    def _on_tool_finished(self, event: Event) -> None:

        tool = _clip(getattr(event, "tool", ""))

        # Only clear the tool that is actually showing: with several
        # calls in one turn, a late finish must not blank a later start.
        if tool and tool == self._snapshot.action:
            self._mutate(action="")

    def _on_speech_started(self, event: Event) -> None:

        # Covers speak() being used directly, where nothing reasoned and
        # so no response event was published.
        text = _clip(getattr(event, "text", ""))

        if text and not self._snapshot.response:
            self._mutate(response=text)

    def _on_error(self, event: Event) -> None:

        self._mutate(message=_clip(getattr(event, "message", "")))

    def _on_voice_started(self, _: Event) -> None:

        self._apply_state(HUDState.IDLE)

    def _on_voice_stopped(self, _: Event) -> None:

        self._apply_state(HUDState.OFFLINE)

    # ==========================================================
    # Snapshot
    # ==========================================================

    def _apply_state(
        self,
        state: HUDState,
        **fields: object,
    ) -> None:
        """
        Move the display to `state`, honouring the ERROR dwell.
        """

        now = time.monotonic()

        # A return to rest is deferred while an error is still being
        # read. Anything else means a new turn has begun, and the user
        # acting on the system always wins over a cosmetic hold.
        if state is HUDState.IDLE and now < self._error_until:
            self._pending_state = state

            return

        self._pending_state = None

        self._error_until = (
            now + _ERROR_DWELL if state is HUDState.ERROR else 0.0
        )

        self._push(self._snapshot.with_state(state, **fields))

    def _mutate(
        self,
        *,
        immediate: bool = True,
        **fields: object,
    ) -> None:
        """
        Change snapshot fields without changing state.
        """

        self._push(
            replace(  # type: ignore[arg-type]
                self._snapshot,
                sequence=self._snapshot.sequence + 1,
                **fields,
            ),
            immediate=immediate,
        )

    def _push(
        self,
        snapshot: HUDSnapshot,
        *,
        immediate: bool = True,
    ) -> None:
        """
        Record a snapshot and, unless deferred, send it.
        """

        self._snapshot = snapshot

        if immediate:
            self._send()

        else:
            self._dirty = True

    def _send(self) -> None:
        """
        Push the current snapshot to the overlay.
        """

        self._dirty = False

        process = self._process

        if process is None or not self._running:
            return

        if not process.send(snapshot_message(self._snapshot)):
            # The child has gone. The pump notices and tidies up; there
            # is nothing useful to do from here.
            self._dirty = False

    # ==========================================================
    # Pump
    # ==========================================================

    async def _pump_loop(self) -> None:
        """
        The service's only background task.

        Three jobs, all of which have to happen off the publishing path:
        send coalesced amplitude updates, release a state held behind the
        ERROR dwell, and read what the child reports back.
        """

        try:
            while self._running:

                self._tick()

                await asyncio.sleep(self._interval())

        except asyncio.CancelledError:
            raise

        except Exception:
            # A pump that dies silently would leave the overlay frozen
            # on whatever it last showed, which looks like a hang.
            self._logger.opt(exception=True).warning(
                "The HUD pump stopped unexpectedly."
            )

    def _tick(self) -> None:

        self._release_pending()

        if self._dirty:
            self._send()

        self._read_child()

    def _interval(self) -> float:
        """
        How long to wait before the next tick.

        Fast while something is happening, slow while resting. The
        overlay animates itself, so there is nothing to send in IDLE.
        """

        if self._demo or self._pending_state is not None:
            return _ACTIVE_INTERVAL

        if self._snapshot.state in (HUDState.IDLE, HUDState.OFFLINE):
            return _RESTING_INTERVAL

        return _ACTIVE_INTERVAL

    def _release_pending(self) -> None:
        """
        Apply a state that was waiting for the ERROR dwell.
        """

        pending = self._pending_state

        if pending is None or time.monotonic() < self._error_until:
            return

        self._pending_state = None
        self._error_until = 0.0

        self._push(self._snapshot.with_state(pending))

    # ----------------------------------------------------------
    # Reverse channel
    # ----------------------------------------------------------

    def _read_child(self) -> None:
        """
        Handle whatever the overlay has reported.
        """

        process = self._process

        if process is None:
            return

        for message in process.poll():

            try:
                self._handle(message)

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring a malformed HUD message."
                )

        if not process.is_alive:
            self._on_child_gone(process.exit_code)

    def _handle(self, message: Message) -> None:

        kind = message_type(message)

        if kind == MSG_READY:

            process = self._process

            if process is not None:
                pid = message.get("pid")

                process.mark_ready(
                    int(pid) if isinstance(pid, (int, float)) else None
                )

                self._logger.info(
                    f"HUD overlay ready (pid={process.pid})."
                )

            # The child starts from its configuration, not from our
            # snapshot, so tell it where we actually are.
            self._send()

        elif kind == MSG_STATS:

            self._fps = float(message.get("fps", 0.0) or 0.0)
            self._quality = str(message.get("quality", "") or "")

        elif kind == MSG_ERROR:

            text = str(message.get("message", "") or "")

            self._logger.warning(f"HUD reported: {text}")

        elif kind == MSG_CLOSED:

            reason = str(message.get("reason", "") or "unknown")

            self._logger.info(f"HUD overlay closed ({reason}).")

            self._failure = (
                None if reason == "quit" else f"The overlay closed ({reason})."
            )

    def _on_child_gone(self, exit_code: int | None) -> None:
        """
        Stop driving an overlay that is no longer there.

        Deliberately does not restart it: a HUD that crashes on startup
        would otherwise be relaunched forever. AetherOS keeps running
        either way, and `hud start` brings it back.
        """

        if not self._running:
            return

        self._running = False

        if self._failure is None and exit_code not in (0, None):
            self._failure = f"The overlay exited with code {exit_code}."

        self._logger.warning(
            f"HUD overlay is gone (exit={exit_code}); stopping updates."
        )


def _clip(value: object, limit: int = _MAX_TEXT) -> str:
    """
    Normalize text for the overlay.

    Collapses whitespace so a multi-line LLM reply cannot break the
    single-line layout, and bounds the length so the pipe carries an
    indicator rather than a transcript.
    """

    if value is None:
        return ""

    text = " ".join(str(value).split())

    if len(text) <= limit:
        return text

    return text[: max(1, limit - 1)].rstrip() + "…"


__all__ = ["HUDService"]
