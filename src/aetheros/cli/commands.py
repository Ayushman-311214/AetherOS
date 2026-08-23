from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING
from .tool_commands import ToolCommandService
import ast

import inspect

if TYPE_CHECKING:
    from .parser import ParsedCommand


CommandHandler = Callable[[list[str]], str]


class CommandRegistry:
    """
    Registry for AetherOS CLI commands.
    """

    def __init__(self,tool_service=None, llm_service=None,) -> None:
        # self._commands: dict[str, CommandHandler] = {}
        self._commands = {}
        self._tool_service = tool_service
        # print("[TOOL_SERVICE] --------------> ",tool_service)
        self._llm_service = llm_service
        
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

        print(
        "[DEBUG COMMANDS] handler:",
        handler,
    )
        result=handler(command.args)

    #     print(
    #     "[DEBUG COMMANDS] handler result:",
    #     result,
    # )

        if inspect.isawaitable(result):
            result = await result
        if hasattr(result, "__await__"):
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

        print(
            "[DEBUG COMMANDS] Tools received:",
            tools,
        )

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
                tool_args = self._tool_service.get_names()
                
                status = (
                    "ON"
                    if tool.enabled
                    else "OFF"
                )

                lines.append(
                    f"  {name:<30}      [{status}]"
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

        return (
            "\n"
            "LLM Status\n"
            "----------\n"
            f"Provider : {provider.name}\n"
            f"Model    : {provider.model}\n"
            "Status   : ONLINE\n"
        )
    
    async def _tool(
            self,
            args: list[str],
            ) -> str:

        print("[DEBUG _TOOL] args:", args)

        if self._tool_service is None:
            return "Tool Registry is not connected."

        if not args:
            return "Usage: tool <tool_name> [arguments...]"

        raw = " ".join(args).strip()

        print("[DEBUG _TOOL] raw:", raw)

        # ------------------------------------------------------
        # tool move_mouse(785,963)
        # ------------------------------------------------------

        if "(" in raw and raw.endswith(")"):

            name, raw_arguments = raw.split("(", 1)

            name = name.strip()
            raw_arguments = raw_arguments[:-1].strip()

            print(f"[DEBUG _TOOL] raw_arguments : {raw_arguments}, name : {name}")

            arguments = {}

            try:
                if raw_arguments:
                    parsed = ast.parse(
                        f"_tool({raw_arguments})",
                        mode="eval",
                    )
                    values = [
                        ast.literal_eval(argument)
                        for argument in parsed.body.args
                    # value.strip()
                    # for value in raw_arguments.split(",")
                    ]
                else:
                    values=[]
            except Exception as e:
                return (f"Invalid tool arguments: {e}")

            # print(f"[DEBUG _TOOL] Values : {values}")
            
        else:
            name = args[0].strip()

            raw_values = args[1:]
            values=[]
            
            for value in raw_values:

                try:
                    values.append(
                        ast.literal_eval(value)
                    )

                except (ValueError, SyntaxError):
                        values.append(value)
        # print(
        #     "[DEBUG _TOOL] Values:",
        #     values,
        # )
            
        if not self._tool_service.exists(name):
            return f"Tool not found : {name}"
        
        
        tool_definition = self._tool_service.get_tool(name)

        if tool_definition is None:

            return (
                f"Tool definition not found: {name}"
            )

        print(
            "[DEBUG _TOOL] definition:",
            tool_definition,
        )
        print("[DEBUG _TOOL] name:", name)
        # print("[DEBUG _TOOL] arguments:", arguments)
    # ==========================================================
    # Get underlying function
    # ==========================================================

        function = tool_definition.function

        signature = inspect.signature(function)

        parameters = list(
            signature.parameters.values()
        )

        print(
            "[DEBUG _TOOL] signature:",
            signature,
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

        print(
            "[DEBUG _TOOL] name:",
            name,
        )

        print(
            "[DEBUG _TOOL] arguments:",
            arguments,
        )

        # ==========================================================
        # Execute
        # ==========================================================

        print(
            "[DEBUG _TOOL] executing:",
            name,
            arguments,
        )

        try:

            result = await self._tool_service.execute(
                name,
                arguments,
            )

            print(
                "[DEBUG _TOOL] result:",
                result,
            )

            return str(result)

        except Exception as exc:

            print(
                "[DEBUG _TOOL] ERROR:",
                type(exc).__name__,
                exc,
            )

            return (
                f"Tool execution failed: {exc}"
            )
            
            
    async def _ask(
    self,
    args: list[str],
) -> str:

        if self._llm_service is None:
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

        try:
            response = await self._llm_service.generate(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )

            return response

        except Exception as exc:
            return (
                f"LLM request failed: "
                f"{type(exc).__name__}: {exc}"
            )
                
                
                
                
            