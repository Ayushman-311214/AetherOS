from __future__ import annotations

from .commands import CommandRegistry
from .parser import CommandParser
from .ui import CLIUI


class CLIRuntime:
    """
    Interactive AetherOS CLI runtime.
    """

    def __init__(self, tool_registry=None,llm_service=None,) -> None:
        print("\n[DEBUG CLI] ===== CLI INIT =====")
        print("[DEBUG CLI] received registry:", tool_registry)

        if tool_registry is not None:
            print(
                "[DEBUG CLI] registry id:",
                id(tool_registry)
        )
            print(
            "[DEBUG CLI] registry count:",
            tool_registry.count
        )

            print(
            "[DEBUG CLI] registry tools:",
            tool_registry.names()
        )
        else:
            print("[DEBUG CLI] NO TOOL REGISTRY RECEIVED!")

        self._parser = CommandParser()

        self._tool_service = None
        
        if tool_registry is not None:
            from .tool_commands import ToolCommandService
            print(
            "[DEBUG CLI] Creating ToolCommandService..."
        )
            self._tool_service = ToolCommandService(
                tool_registry
            )

            print(
            "[DEBUG CLI] ToolCommandService created:",
            self._tool_service
        )   


        self._commands = CommandRegistry(
            self._tool_service,
            llm_service,
        )

        self._ui = CLIUI()

        self._running = False
        print("[DEBUG CLI] ===== CLI INIT COMPLETE =====\n")
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
                print()
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
                print("result ===============>",result)