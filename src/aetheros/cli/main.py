from __future__ import annotations

import asyncio
import threading
from typing import Any

from ..core.logging import get_logger

from .commands import CommandRegistry
from .parser import CommandParser
from .ui import CLIUI
from ..runtime.events.event_bus import EventBus
from ..runtime.events.events import Event
from ..hud.service import HUDService

class CLIRuntime:
    """
    Interactive AetherOS CLI runtime.
    """

    def __init__(
        self,
        tool_registry=None,
        llm_service=None,
        tool_loop=None,
        agent=None,
        trace=None,
        event : Event | None = None,
        event_bus : EventBus | None = None,
        ) -> None:

        self._logger = get_logger("cli")

        self._event_bus = event_bus
        self._event=event
        self._parser = CommandParser()
        self._ui = CLIUI()

        self._tool_service = None






        if tool_registry is not None:
            from .tool_commands import ToolCommandService

            self._tool_service = ToolCommandService(
                tool_registry
            )

        self._commands = CommandRegistry(
            self._tool_service,
            llm_service,
            tool_loop=tool_loop,
            agent=agent,
            trace=trace,
        )

        self._running = False

        self._logger.bind(
            tool_count=(
                tool_registry.count
                if tool_registry is not None
                else 0
            ),
            has_llm=llm_service is not None,
            has_tool_loop=tool_loop is not None,
            has_agent=agent is not None,
        ).info("CLI runtime initialized.")

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self) -> None:
        """
        Start the CLI.
        """

        if self._running:
            return

        self._running = True

        self._ui.show_startup()

        await self._loop()

    async def stop(self) -> None:
        """
        Stop the CLI.
        """

        self._running = False

    # ==========================================================
    # Input Loop
    # ==========================================================

    async def _loop(self) -> None:

        while self._running:

            try:
                text = await self._read_line()

            except EOFError:
                self._running = False
                break

            except KeyboardInterrupt:
                self._ui.console.print()
                self._running = False
                break

            command = self._parser.parse(text)

            if command is None:
                continue

            result = await self._commands.execute(command)

            if result == "__EXIT__":
                self._running = False
                self._ui.goodbye()
                break

            if result:
                self._ui.answer(str(result))
                

    async def _read_line(self) -> str:
        """
        Read one prompt line without blocking the event loop.

        `console.input()` blocks until Enter is pressed, and on the event loop
        thread that stalls every other task for as long as the prompt sits
        idle: the HUD's pump task stops draining the overlay's pipe and the
        voice hotkey's `call_soon_threadsafe` is never serviced. Both
        subsystems would appear frozen precisely while the user is waiting at
        the prompt to use them.

        A dedicated daemon thread rather than `asyncio.to_thread`, because the
        default executor is joined during `asyncio.run` teardown. A worker
        still parked inside `input()` at that point — which is exactly the
        state Ctrl+C leaves it in — would hold the interpreter open waiting for
        a keypress that will never come.
        """

        loop = asyncio.get_running_loop()

        future: asyncio.Future[str] = loop.create_future()

        def deliver(result: str | None, error: BaseException | None) -> None:

            # The loop may have moved on — a cancelled read has no one waiting.
            if future.done():
                return

            if error is not None:
                future.set_exception(error)
            else:
                future.set_result(result or "")

        def worker() -> None:

            try:
                text = self._ui.prompt()

            except BaseException as exc:  # noqa: BLE001 - relayed to the awaiter
                loop.call_soon_threadsafe(deliver, None, exc)

            else:
                loop.call_soon_threadsafe(deliver, text, None)

        threading.Thread(
            target=worker,
            name="aetheros-cli-prompt",
            daemon=True,
        ).start()

        return await future
    
    
    # def hud_text(self):
    #     text = HUDService._on_transcribed()
    #     self._ui.success(text)
        
    # def _handlers(self) -> dict[type[Event], Any]:
    #         """
    #         The events the overlay actually reacts to.
    
    #         VoiceStateChanged drives the animation; the rest only fill in
    #         text. Deliberately not every voice event: subscribing to
    #         something the HUD does not display would just add work on the
    #         publishing path.
    
    #         The voice event types are imported here rather than at module
    #         level so the HUD package has no structural dependency on the
    #         voice package. The overlay is then startable, and testable, with
    #         voice absent entirely — which is the same isolation that lets
    #         voice run with the overlay absent.
    #         """
    
    #         from ..voice.events import (
    #             LLMThinkingFinished,
    #             SpeechStarted,
    #             SpeechTranscribed,
    #             ToolExecutionFinished,
    #             ToolExecutionStarted,
    #             VoiceAudioLevel,
    #             VoiceError,
    #             VoiceServiceStarted,
    #             VoiceServiceStopped,
    #             VoiceStateChanged,
    #         )
    
    #         return {
    #             # VoiceStateChanged: self._on_state_changed,
    #             # VoiceAudioLevel: self._on_audio_level,
    #             SpeechTranscribed: self._on_transcribed,
    #             # LLMThinkingFinished: self._on_response,
    #             # ToolExecutionStarted: self._on_tool_started,
    #             # ToolExecutionFinished: self._on_tool_finished,
    #             # SpeechStarted: self._on_speech_started,
    #             # VoiceError: self._on_error,
    #             # VoiceServiceStarted: self._on_voice_started,
    #             # VoiceServiceStopped: self._on_voice_stopped,
    #         }
    
    # async def _subscribe(self) -> None:
    
    #         bus = self._bus
    
    #         if bus is None or self._subscribed:
    #             return
    
    #         try:
    #             handlers = self._handlers()
    
    #         except Exception:
    #             # Voice is not installed or failed to import. The overlay
    #             # still works; it just has nothing driving it, which is
    #             # exactly the standalone case.
    #             self._logger.opt(exception=True).warning(
    #                 "The CLI could not subscribe to voice events."
    #             )
    
    #             return
    
    #         for event_type, handler in handlers.items():
    #             await bus.subscribe(event_type, handler)
    
    #         self._subscribed = True
    
    # def _on_transcribed(self, event: Event) -> None:
    #     """
    #     Update the overlay with the latest transcript.

    #     The HUD is not a transcript display; it only shows the current
    #     utterance while it is being spoken. A new utterance retires the
    #     previous answer, so the overlay never shows this turn's question
    #     beside the last one's reply.
    #     """

    #     # A new utterance retires the previous answer, so the overlay
    #     transcript=getattr(event, "text", "")
    #     self._ui.success(transcript)
    
    
    