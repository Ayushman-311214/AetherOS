from __future__ import annotations

import asyncio
import threading

from ..core.logging import get_logger
from ..core.observability.events import TraceEvent, TraceEventType, TraceStatus

from .commands import CommandRegistry
from .parser import CommandParser
from .ui import CLIUI
from ..runtime.events.event_bus import EventBus
from ..runtime.events.events import Event

#: Longest answer/response text the terminal renders inline from a trace
#: event. The final answer is shown in full; this only guards a stray
#: oversized preview from other events.
_MAX_STATUS = 240

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
        gateway=None,
        event : Event | None = None,
        event_bus : EventBus | None = None,
        ) -> None:

        self._logger = get_logger("cli")

        self._event_bus = event_bus
        self._event=event
        self._parser = CommandParser()
        self._ui = CLIUI()

        # The unified entry every `ask` submits through, so the run is tagged
        # with source="terminal" and emits the same lifecycle the HUD observes.
        self._gateway = gateway

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
            gateway=gateway,
        )

        self._running = False

        #: True while a subscription to the shared TraceEvent stream is live.
        self._subscribed = False

        self._logger.bind(
            tool_count=(
                tool_registry.count
                if tool_registry is not None
                else 0
            ),
            has_llm=llm_service is not None,
            has_tool_loop=tool_loop is not None,
            has_agent=agent is not None,
            has_gateway=gateway is not None,
            has_bus=event_bus is not None,
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

        # Become a renderer of the one agent's lifecycle: subscribe to the
        # shared TraceEvent stream so a turn from *either* front end (this
        # terminal or voice) surfaces here. This is what makes the terminal and
        # the HUD synchronized views of the same run rather than two systems.
        await self._subscribe()

        self._ui.show_startup()

        await self._loop()

    async def stop(self) -> None:
        """
        Stop the CLI.
        """

        self._running = False

        await self._unsubscribe()

    # ==========================================================
    # Live lifecycle rendering
    # ==========================================================

    async def _subscribe(self) -> None:
        """
        Subscribe the terminal to the shared execution trace.

        Defensive: a runtime wired without a bus (a unit test, a minimal
        embedding) simply renders nothing live and falls back to the direct
        answer path. The bus dispatches on the exact ``TraceEvent`` type, which
        is the single class every stage of the pipeline is emitted as.
        """

        bus = self._event_bus

        if bus is None or self._subscribed:
            return

        try:
            await bus.subscribe(TraceEvent, self._on_trace)
            self._subscribed = True

        except Exception:
            self._logger.opt(exception=True).warning(
                "The CLI could not subscribe to the execution trace."
            )

    async def _unsubscribe(self) -> None:

        bus = self._event_bus

        if bus is None or not self._subscribed:
            return

        self._subscribed = False

        try:
            await bus.unsubscribe(TraceEvent, self._on_trace)

        except Exception:
            self._logger.opt(exception=True).debug(
                "Ignoring error while unsubscribing the CLI."
            )

    def _on_trace(self, event: Event) -> None:
        """
        Render one lifecycle event as safe, user-facing terminal output.

        Synchronous on purpose: it runs on the publishing path and must never
        block (no ``input()`` here -- that was the old HUD bug). Only ever reads
        the event's already-safe projections -- ``stage``/``message``, tool
        *names*, and the final answer text -- and NEVER internal reasoning or a
        token stream. This is the PHASE 8 chain-of-thought guard in the renderer
        itself: there is no field here through which private reasoning could
        reach the screen.
        """

        if not isinstance(event, TraceEvent):
            return

        try:
            self._render_trace(event)

        except Exception:
            # A renderer fault must not break the run it is only observing.
            self._logger.opt(exception=True).debug(
                "Ignoring error while rendering a trace event."
            )

    def _render_trace(self, event: TraceEvent) -> None:

        kind = event.event_type

        if kind is TraceEventType.INPUT_RECEIVED:
            # Echo the request only when it did not originate here: a voice turn
            # should appear in the terminal, but re-printing what the user just
            # typed would be noise. Both UIs still receive the event -- this is
            # a render choice, not routing.
            if event.source and event.source != "terminal":
                who = event.source.upper()
                self._ui.console.print(
                    f"\n[bold green]{who} »[/bold green] {event.message}"
                )
            return

        if kind is TraceEventType.AGENT_STARTED:
            self._ui.info("Understanding request…")
            return

        if kind is TraceEventType.TOOL_SELECTED:
            name = event.metadata.get("tool_name") or event.message
            if name:
                self._ui.note(f"→ running tool: {name}")
            return

        if kind is TraceEventType.TOOL_EXECUTION_FAILED:
            name = event.metadata.get("tool_name") or event.message or "tool"
            self._ui.error(f"tool failed: {name}")
            return

        if kind is TraceEventType.FINAL_RESPONSE_CREATED:
            # The full, untruncated answer travels in payload["response"]; the
            # message is only a preview. Fall back to the preview if absent.
            answer = event.payload.get("response") or event.message or "(no answer)"
            self._ui.answer(str(answer))
            return

        if kind is TraceEventType.ERROR and event.status is TraceStatus.FAILED:
            self._ui.error(event.message or event.error or "The run failed.")
            return

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
