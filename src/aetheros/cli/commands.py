from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING
import ast

import inspect

from ..core.logging import get_logger

if TYPE_CHECKING:
    from .parser import ParsedCommand


CommandHandler = Callable[[list[str]], str]


class CommandRegistry:
    """
    Registry for AetherOS CLI commands.
    """

    def __init__(
        self,
        tool_service=None,
        llm_service=None,
        *,
        tool_loop=None,
    ) -> None:

        self._commands = {}

        self._tool_service = tool_service

        # The raw provider, kept for `llm` status reporting.
        self._llm_service = llm_service

        # The LLMToolLoop. `ask` runs through this so the model can call tools;
        # without it, `ask` degrades to plain generation rather than failing.
        self._tool_loop = tool_loop

        self._logger = get_logger("cli_commands")

        self.register("help", self._help)
        self.register("status", self._status)
        self.register("tools", self._tools)
        self.register("tool", self._tool)

        self.register("desktop", self._desktop)
        self.register("browser", self._browser)
        self.register("vision", self._vision)
        self.register("llm", self._llm)

        self.register("ask", self._ask)


        self.register("clear", self._clear)

        self.register("exit", self._exit)
        self.register("quit", self._exit)

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        name: str,
        handler: CommandHandler,
    ) -> None:
        """
        Register a CLI command.
        """

        self._commands[name.lower()] = handler

    # ==========================================================
    # Execution
    # ==========================================================

    async def execute(
        self,
        command: ParsedCommand,
    ) -> str:
        """
        Execute a parsed command.
        """

        handler = self._commands.get(command.name)

        if handler is None:
            return (
                f"Unknown command: {command.name}\n"
                "Type 'help' to see available commands."
            )

        result = handler(command.args)

        if inspect.isawaitable(result):
            result = await result

        return str(result) if result is not None else ""

    # ==========================================================
    # Built-in Commands
    # ==========================================================

    def _help(self, args: list[str]) -> str:
        return """
                AetherOS Commands

                help       Show available commands
                status     Show system status
                ask        Send a message to the LLM
                tools      List registered tools
                desktop    Desktop operations
                browser    Browser operations
                vision     Vision operations
                llm        LLM operations
                clear      Clear the terminal
                exit       Stop AetherOS
                quit       Stop AetherOS
            """

    def _status(self, args: list[str]) -> str:
        return (
            "\n"
            "AetherOS Status\n"
            "---------------\n"
            "Runtime : ONLINE\n"
            "CLI     : ONLINE\n"
            "Status  : RUNNING\n"
        )

    def _clear(self, args: list[str]) -> str:
        os.system("cls" if os.name == "nt" else "clear")
        return ""

    def _exit(self, args: list[str]) -> str:
        return "__EXIT__"

    def _tools(self, args: list[str]) -> str:

        if self._tool_service is None:
            return (
                "\n"
                "Tool Registry\n"
                "-------------\n"
                "Status : NOT CONNECTED\n"
            )

        tools = self._tool_service.list_tools()

        if not tools:
            return (
                "\n"
                "Tool Registry\n"
                "-------------\n"
                "No tools registered.\n"
            )

        lines = [
            "",
            "Available Tools",
            "---------------",
        ]

        for name in tools:

            try:
                tool = self._tool_service.get_tool(name)
                # args = self._tool_service.get_args(name)
                

                status = (
                    "ON"
                    if tool.enabled
                    else "OFF"
        
                )

                lines.append(
                    f"  {name:<30}      [{status}] "
                )

            except KeyError:
                lines.append(
                    f"  {name:<30}"
                )

        lines.append("")
        lines.append(
            f"Total: {len(tools)}"
        )

        return "\n".join(lines)

    def _desktop(self, args: list[str]) -> str:
        return "Desktop subsystem."

    def _browser(self, args: list[str]) -> str:
        return "Browser subsystem."

    def _vision(self, args: list[str]) -> str:
        return "Vision subsystem."

    def _llm(self, args: list[str]) -> str:
        """
        Show LLM provider status and model information.
        """

        if self._llm_service is None:
            return (
                "\n"
                "LLM\n"
                "---\n"
                "Status : NOT CONNECTED\n"
            )

        provider = self._llm_service

        tools = (
            "ENABLED"
            if self._tool_loop is not None
            else "DISABLED"
        )

        return (
            "\n"
            "LLM Status\n"
            "----------\n"
            f"Provider : {provider.name}\n"
            f"Model    : {provider.model}\n"
            f"Tools    : {tools}\n"
            "Status   : ONLINE\n"
        )

    async def _tool(
            self,
            args: list[str],
            ) -> str:

        if self._tool_service is None:
            return "Tool Registry is not connected."

        if not args:
            return "Usage: tool <tool_name> [arguments...]"

        raw = " ".join(args).strip()

        # ------------------------------------------------------
        # tool move_mouse(785,963)
        # ------------------------------------------------------

        if "(" in raw and raw.endswith(")"):

            name, raw_arguments = raw.split("(", 1)

            name = name.strip()
            raw_arguments = raw_arguments[:-1].strip()

            try:
                if raw_arguments:
                    parsed = ast.parse(
                        f"_tool({raw_arguments})",
                        mode="eval",
                    )
                    values = [
                        ast.literal_eval(argument)
                        for argument in parsed.body.args
                    ]
                else:
                    values = []

            except Exception as exc:
                return f"Invalid tool arguments: {exc}"

        else:
            name = args[0].strip()

            raw_values = args[1:]
            values = []

            for value in raw_values:

                try:
                    values.append(
                        ast.literal_eval(value)
                    )

                except (ValueError, SyntaxError):
                    values.append(value)

        if not self._tool_service.exists(name):
            return f"Tool not found : {name}"

        tool_definition = self._tool_service.get_tool(name)

        if tool_definition is None:

            return (
                f"Tool definition not found: {name}"
            )

    # ==========================================================
    # Get underlying function
    # ==========================================================

        function = tool_definition.function

        signature = inspect.signature(function)

        parameters = list(
            signature.parameters.values()
        )

            # ==========================================================
    # Build arguments dynamically
    # ==========================================================

        arguments = {}

        positional_index = 0

        for parameter in parameters:

            # ------------------------------------------------------
            # Skip *args / **kwargs
            # ------------------------------------------------------

            if parameter.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            # ------------------------------------------------------
            # No more user arguments
            # ------------------------------------------------------

            if positional_index >= len(values):

                if parameter.default is not inspect.Parameter.empty:

                    continue

                return (
                    f"Missing argument: "
                    f"{parameter.name}"
                )

            value = values[positional_index]

            # ------------------------------------------------------
            # Convert according to annotation
            # ------------------------------------------------------

            annotation = parameter.annotation

            try:

                if annotation is int:

                    value = int(value)

                elif annotation is float:

                    value = float(value)

                elif annotation is bool:

                    if isinstance(value, str):

                        value_lower = value.lower()

                        if value_lower in (
                            "true",
                            "1",
                            "yes",
                            "on",
                        ):
                            value = True

                        elif value_lower in (
                            "false",
                            "0",
                            "no",
                            "off",
                        ):
                            value = False

                        else:
                            raise ValueError(
                                f"Invalid boolean: {value}"
                            )

                    else:

                        value = bool(value)

                elif annotation is str:

                    value = str(value)

            except Exception as exc:

                return (
                    f"Invalid argument "
                    f"'{parameter.name}': {exc}"
                )

            arguments[parameter.name] = value

            positional_index += 1

        # ==========================================================
        # Too many arguments
        # ==========================================================

        if positional_index < len(values):

            return (
                f"Too many arguments for tool "
                f"'{name}'. Expected "
                f"{len(parameters)}, got {len(values)}."
            )

        # ==========================================================
        # Execute
        # ==========================================================

        try:

            result = await self._tool_service.execute(
                name,
                arguments,
            )

            return str(result)

        except Exception as exc:

            # Deliberately broad: this is a user-facing REPL command, and any
            # tool failure should print a message rather than kill the session.
            self._logger.bind(
                tool=name,
                error_type=type(exc).__name__,
            ).warning("Manual tool invocation failed.")

            return (
                f"Tool execution failed: {exc}"
            )

    async def _ask(
        self,
        args: list[str],
    ) -> str:
        """
        Send a message to the LLM, letting it call AetherOS tools.
        """

        if self._tool_loop is None and self._llm_service is None:
            return (
                "\n"
                "LLM\n"
                "---\n"
                "Status : NOT CONNECTED\n"
            )

        if not args:
            return "Usage: ask <message>"

        prompt = " ".join(args).strip()

        if not prompt:
            return "Usage: ask <message>"

        # ------------------------------------------------------
        # Tool-enabled path
        # ------------------------------------------------------

        if self._tool_loop is not None:

            try:
                result = await self._tool_loop.run_detailed(prompt)

            except Exception as exc:
                # Only a provider/transport failure reaches here; tool failures
                # are handled inside the loop and reported back to the model.
                self._logger.bind(
                    error_type=type(exc).__name__,
                ).exception("LLM request failed.")

                return (
                    f"LLM request failed: "
                    f"{type(exc).__name__}: {exc}"
                )

            return self._format_answer(result)

        # ------------------------------------------------------
        # No loop wired: plain generation
        # ------------------------------------------------------

        try:
            return await self._llm_service.generate(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )

        except Exception as exc:
            self._logger.bind(
                error_type=type(exc).__name__,
            ).exception("LLM request failed.")

            return (
                f"LLM request failed: "
                f"{type(exc).__name__}: {exc}"
            )

    # ==========================================================
    # Formatting
    # ==========================================================

    def _format_answer(
        self,
        result,
    ) -> str:
        """
        Render an agent-loop result for the terminal.
        """

        answer = result.content or "(no answer)"

        if not result.tool_results:
            return answer

        # Which tools ran is part of the answer's evidence, so it is shown
        # rather than buried in the log file.
        used = ", ".join(
            f"{invocation.name}"
            f"{'' if invocation.ok else ' (failed)'}"
            for invocation in result.tool_results
        )

        lines = [answer, "", f"Tools used: {used}"]

        if result.stopped_reason != "final_answer":
            lines.append(
                f"Stopped early: {result.stopped_reason} "
                f"after {result.iterations} iterations."
            )

        return "\n".join(lines)