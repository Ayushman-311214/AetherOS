from __future__ import annotations

from ..core.logging import get_logger

from .commands import CommandRegistry
from .parser import CommandParser
from .ui import CLIUI


class CLIRuntime:
    """
    Interactive AetherOS CLI runtime.
    """

    def __init__(
        self,
        tool_registry=None,
        llm_service=None,
        tool_loop=None,
    ) -> None:

        self._logger = get_logger("cli")

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
                text = self._ui.prompt()

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
