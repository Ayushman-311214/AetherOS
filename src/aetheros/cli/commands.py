from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
import ast

import inspect

from ..core.logging import get_logger
from ..tools.annotations import public_parameters, resolve_hints

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
        agent=None,
        trace=None,
        gateway=None,
    
    ) -> None:

        self._commands = {}

        self._tool_service = tool_service

        # The raw provider, kept for `llm` status reporting.
        self._llm_service = llm_service

        # The agent core. `ask` runs through this so the agent owns
        # orchestration -- OBSERVE -> PLAN -> POLICY -> EXECUTE -- and the CLI
        # only submits the goal and displays the result.
        self._agent = agent

        # The unified interaction gateway. When present, `ask` submits through
        # it so the run is tagged source="terminal" and emits the shared
        # lifecycle both UIs observe -- the terminal then renders the answer
        # from that stream, not from this method's return value.
        self._gateway = gateway

        # The legacy LLMToolLoop, kept as a fallback for a runtime wired before
        # the agent existed; without either, `ask` degrades to plain generation
        # rather than failing.
        self._tool_loop = tool_loop

        # The live execution-trace recorder. The `trace` command mutates it
        # (level, clear) and reads its status; None when tracing was not wired,
        # in which case `trace` reports that rather than failing.
        self._trace = trace

        # self._desktop_service = desktop_service

        self._logger = get_logger("cli_commands")

        self.register("help", self._help)
        self.register("status", self._status)
        self.register("tools", self._tools)
        self.register("tool", self._tool)

        self.register("analyze", self._analyze)
        self.register("brief", self._brief_command)
        self.register("investigate", self._investigate_command)
        self.register("explain", self._explain_command)
        self.register("scan", self._scan_command)
        self.register("portfolio", self._portfolio_command)
        self.register("monitor", self._monitor_command)
        self.register("monitor-loop", self._monitor_loop_command)
        self.register("track-record", self._track_record_command)

        self.register("memory", self._memory_command)

        self.register("desktop", self._desktop)
        self.register("browser", self._browser)
        self.register("vision", self._vision)
        self.register("llm", self._llm)

        self.register("ask", self._ask)

        self.register("trace", self._trace_command)

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
                analyze    Deterministic trading report (analyze <symbol> [timeframe] [backtest])
                brief      CEO brief from a free-text request (brief should I look at AAPL this week)
                investigate  Agentic CEO tool-loop (investigate [research|quant|critic] <request>)
                explain    Why a recommendation came out that way (explain <symbol> [timeframe])
                scan       Rank a watchlist by signal (scan <SYM1> <SYM2> ... [timeframe])
                portfolio  Risk-budget a basket (portfolio <SYM1> <SYM2> ... <equity>)
                monitor    Resolve + score recorded predictions (monitor [SYMBOL:EXCHANGE] [limit])
                monitor-loop  Autonomous monitoring loop (monitor-loop start|stop|status)
                track-record  Recorded predictions + how they scored (track-record [SYMBOL:EXCHANGE] [limit])
                memory     Inspect/manage memory (memory [stats|search <q>|show <id>|list|forget <id>])
                tools      List registered tools
                desktop    Desktop operations
                browser    Browser operations
                vision     Vision operations
                llm        LLM operations
                trace      Live execution trace (trace / on / off / level / clear / status)
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

        names = self._tool_service.list_tools()

        if not names:
            return (
                "\n"
                "Tool Registry\n"
                "-------------\n"
                "No tools registered.\n"
            )

        lines = [
            "",
            "Available Tools",
            "─" * 40,
            "",
        ]

        for name in names:

            try:
                tool = self._tool_service.get_tool(name)
                signature = self._format_tool_signature(
                    name,
                    tool.function,
                    # tool.description,   
                    )
                # lines.append(f"{name}")
            except KeyError:
                # Listed by the registry but no longer resolvable: keep the
                # name in the list rather than silently dropping it.
                signature = f"{name}()"
                # self._logger.warning(
                #     "Tool listed but not found in registry: %s",)
            lines.append(signature)
            lines.append("")
                

        return "\n".join(lines)

    # ==========================================================
    # Tool signature rendering
    # ==========================================================

    def _format_tool_signature(
        self,
        name: str,
        function,
    ) -> str:
        """
        Render one tool as ``name(arg: type, arg: type = default)``.

        Names, types, and defaults are read straight from the tool's own
        function signature through the shared annotation resolver -- the same
        view the schema generator and the validator use. Nothing here is a
        second, hand-written copy of a tool's parameters, so the list always
        reflects the live ToolRegistry, including any newly registered tool.
        """

        try:
            signature = inspect.signature(function)

        except (TypeError, ValueError):
            # A builtin or C callable with no introspectable signature.
            return f"{name}(...)"

        # PEP 563 leaves annotations as strings inside the tool modules;
        # resolving them is what makes a parameter read ``x: int`` rather than
        # carrying the bare source text.
        hints = resolve_hints(function)

        parts: list[str] = []

        for parameter in public_parameters(signature):

            piece = parameter.name

            type_name = self._annotation_name(
                hints.get(parameter.name, parameter.annotation)
            )

            if type_name:
                piece += f": {type_name}"

            if parameter.default is not inspect.Parameter.empty:
                piece += f" = {self._format_default(parameter.default)}"

            parts.append(piece)

        return f"{name}({', '.join(parts)})"

    @staticmethod
    def _annotation_name(annotation) -> str:
        """
        A readable type name for a resolved annotation, or "" when there is no
        usable type to show (missing annotation).
        """

        if annotation is inspect.Parameter.empty or annotation is None:
            return ""

        if isinstance(annotation, str):
            # get_type_hints() could not resolve it; the raw source (e.g.
            # "int") is already the readable form.
            return annotation

        name = getattr(annotation, "__name__", None)

        if name:
            return name

        # typing constructs (Optional[...], list[str], unions) carry no
        # __name__; their str() reads fine once the "typing." prefix is dropped.
        return str(annotation).replace("typing.", "")

    @staticmethod
    def _format_default(value) -> str:
        """
        Render a parameter's default value for display.
        """

        if isinstance(value, str):
            return f'"{value}"'

        return repr(value)


    async def _memory_command(self, args: list[str]) -> str:
        """
        Inspect and manage the memory subsystem (spec Phase 15/28).

        Usage:
            memory                      Show memory statistics
            memory stats                Show memory statistics
            memory search <query>       Hybrid, explainable recall
            memory show <id>            Full detail for one memory
            memory list [type]          List recent memories (optionally by type)
            memory forget <id> [hard]   Forget a memory (soft, or hard-delete)

        Read-only by default; `forget` is the only mutation and it is explicit.
        Resolves the live MemoryManager from the DI container, so it honestly
        reports NOT ENABLED when ENABLE_MEMORY is off rather than pretending.
        """
        from ..core.container import container
        from ..memory.services.manager import MemoryManager

        if not container.has(MemoryManager):
            return (
                "\nMemory\n------\n"
                "Status : NOT ENABLED\n"
                "Set ENABLE_MEMORY=true to turn the memory subsystem on.\n"
            )

        manager = container.resolve(MemoryManager)
        sub = (args[0].strip().lower() if args else "stats")
        rest = args[1:]

        if sub in ("stats", ""):
            stats = await manager.stats()
            by_type = ", ".join(f"{k}={v}" for k, v in sorted(stats["by_type"].items()))
            return (
                "\nMemory\n------\n"
                f"Total memories : {stats['total']}\n"
                f"By type        : {by_type or 'none'}\n"
                f"Vectors        : {stats['vectors']}\n"
                f"Graph          : {stats['graph']['entities']} entities, "
                f"{stats['graph']['relationships']} relationships\n"
                f"Working set    : {stats['working']}\n"
                f"Embedder       : {stats['embedder']} (dim {stats['embedding_dim']})\n"
                f"Schema version : {stats['schema_version']}\n"
            )

        if sub == "search":
            if not rest:
                return "Usage: memory search <query>"
            results = await manager.retrieve(" ".join(rest), limit=10)
            if not results:
                return "No matching memories."
            lines = [f"\nMemory search: {' '.join(rest)}\n"]
            for r in results:
                why = "; ".join(r.explanation.reasons)
                lines.append(
                    f"[{r.score:.2f}] ({r.memory.memory_type.value}) "
                    f"{r.memory.content}\n      id={r.memory.id}  why: {why}"
                )
            return "\n".join(lines)

        if sub == "show":
            if not rest:
                return "Usage: memory show <id>"
            memory = await manager.get(rest[0])
            if memory is None:
                return f"No memory with id {rest[0]}"
            d = memory.to_dict()
            return (
                f"\nMemory {d['id']}\n"
                f"  type       : {d['memory_type']}\n"
                f"  veracity   : {d['veracity']}\n"
                f"  content    : {d['content']}\n"
                f"  confidence : {d['confidence']:.3f} ({memory.confidence_band})\n"
                f"  importance : {d['importance']}\n"
                f"  status     : {d['status']}  scope: {d['scope']}\n"
                f"  source     : {d['source']['source_type']} / {d['source']['origin']}\n"
                f"  tags       : {', '.join(d['tags']) or 'none'}\n"
                f"  entities   : {', '.join(d['entities']) or 'none'}\n"
                f"  created    : {d['created_at']}\n"
            )

        if sub == "list":
            mtype = rest[0].strip().lower() if rest else None
            memories = await manager._repo.list_by(memory_type=mtype, limit=20)
            if not memories:
                return "No memories stored."
            lines = ["\nStored memories\n"]
            for m in memories:
                lines.append(
                    f"  {m.id[:8]}  [{m.memory_type.value:<10}] "
                    f"({m.status.value}) {m.content[:70]}"
                )
            return "\n".join(lines)

        if sub == "forget":
            if not rest:
                return "Usage: memory forget <id> [hard]"
            hard = len(rest) > 1 and rest[1].strip().lower() in ("hard", "--hard")
            ok = await manager.forget(rest[0], hard=hard)
            if not ok:
                return f"No memory with id {rest[0]}"
            return f"Forgot {rest[0]} ({'hard-deleted' if hard else 'soft-deleted'})."

        return (
            f"Unknown memory subcommand: {sub}\n"
            "Try: memory [stats|search|show|list|forget]"
        )

    def _desktop(self, args: list[str]) -> str:
        from ..desktop.main import status

        status_dict = status()

        return (
            "\n"
            "Desktop Status\n"
            "----------\n"
            f"Keyboard : {status_dict.get('keyboard', 'N/A')}\n"
            f"Mouse    : {status_dict.get('mouse', 'N/A')}\n"
            f"Clipboard: {status_dict.get('clipboard', 'N/A')}\n"
            f"Screen   : {status_dict.get('screen', 'N/A')}\n"
            f"Process  : {status_dict.get('process', 'N/A')}\n"
            f"Window   : {status_dict.get('window', 'N/A')}\n"
            "Status   : ONLINE\n"
        )

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
            if self._agent is not None or self._tool_loop is not None
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

    def _trace_command(self, args: list[str]) -> str:
        """
        Inspect and control the live execution trace (PHASE 10).

        Subcommands:
            trace              Show trace status (same as `trace status`).
            trace on           Restore tracing to the NORMAL level.
            trace off          Silence the trace (level OFF).
            trace level <x>    Set the level: off|error|minimal|normal|debug|verbose.
            trace clear        Drop the in-memory dashboard window.
            trace status       Trace / Level / Live UI / Persistence snapshot.

        Mutates the live recorder in place -- it does not touch the cached
        settings, so a runtime change here does not require a restart and does
        not persist to the environment.
        """

        if self._trace is None:
            return (
                "\n"
                "Live Execution Trace\n"
                "--------------------\n"
                "Status : NOT CONNECTED\n"
            )

        action = args[0].lower() if args else "status"

        if action in ("status", "show"):
            return self._format_trace_status()

        if action == "on":
            level = self._trace.set_level("normal")
            return f"Trace on (level={level.name.lower()})."

        if action == "off":
            self._trace.set_level("off")
            return "Trace off."

        if action == "clear":
            self._trace.clear()
            return "Trace window cleared."

        if action == "level":
            if len(args) < 2:
                return (
                    f"Current trace level: {self._trace.level.name.lower()}.\n"
                    "Usage: trace level <off|error|minimal|normal|debug|verbose>"
                )
            level = self._trace.set_level(args[1])
            return f"Trace level set to {level.name.lower()}."

        return (
            f"Unknown trace subcommand: {action}\n"
            "Usage: trace [on|off|level <x>|clear|status]"
        )

    def _format_trace_status(self) -> str:
        status = self._trace.status()

        return (
            "\n"
            "Live Execution Trace\n"
            "--------------------\n"
            f"Trace       : {'ON' if status['running'] else 'OFF'}\n"
            f"Level       : {status['level']}\n"
            f"Live UI     : {'ON' if status['live_ui'] else 'OFF'}\n"
            f"Persistence : {'ON' if status['persist'] else 'OFF'}\n"
            f"Events seen : {status['events_seen']}\n"
            f"Events kept : {status['events_kept']}\n"
            f"Buffered    : {status['buffered']}\n"
            f"Last run    : {status['last_run_id'] or '-'}\n"
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

    async def _analyze(
        self,
        args: list[str],
    ) -> str:
        """
        Run the deterministic trading pipeline for one instrument and render
        the section-27 report for a human -- no LLM involved.

        Usage:
            analyze <symbol> [timeframe] [backtest]

        The command routes through the ToolRegistry (the ``generate_trading_report``
        tool), so it computes nothing itself: every number it prints traces to a
        sub-object of the composed report. It surfaces the pipeline's honesty
        contract verbatim -- a MOCK-data run degrades to NO_TRADE, carries no
        fabricated probability, and states its limitations rather than hiding
        them (spec sections 11, 27, 28, 61).
        """

        if self._tool_service is None:
            return (
                "\n"
                "Trading Analysis\n"
                "----------------\n"
                "Status : NOT CONNECTED\n"
            )

        if not args:
            return (
                "Usage: analyze <symbol> [timeframe] [backtest]\n"
                "Example: analyze AAPL 1d"
            )

        symbol = args[0].strip()

        if not symbol:
            return (
                "Usage: analyze <symbol> [timeframe] [backtest]\n"
                "Example: analyze AAPL 1d"
            )

        # Remaining tokens: a `backtest` flag toggles the walk-forward run; any
        # other token is read as the timeframe (last one wins). Defaults mirror
        # the tool's own signature so the CLI adds no hidden behaviour.
        timeframe = "1d"
        run_backtest = False

        for token in args[1:]:
            lowered = token.strip().lower()

            if lowered in ("backtest", "--backtest", "-b"):
                run_backtest = True
            elif lowered:
                timeframe = token.strip()

        try:
            payload = await self._tool_service.execute(
                "generate_trading_report",
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "run_backtest": run_backtest,
                },
            )

        except Exception as exc:
            # A user-facing REPL command: a pipeline failure prints a message
            # rather than killing the session. Names/types only -- an argument
            # value never belongs in the visible transcript.
            self._logger.bind(
                symbol=symbol,
                error_type=type(exc).__name__,
            ).warning("analyze command failed.")

            return f"Analysis failed: {type(exc).__name__}: {exc}"

        # A bad argument (e.g. an unknown direction) comes back as a successful
        # result carrying an ``error`` key, not a raise -- surface it plainly.
        if isinstance(payload, dict) and "error" in payload:
            supported = payload.get("supported")
            message = str(payload["error"])

            if supported:
                message += f" Supported: {', '.join(map(str, supported))}."

            return message

        return self._format_trading_report(payload)

    async def _brief_command(
        self,
        args: list[str],
    ) -> str:
        """
        Answer a free-text request with a CEO brief -- the LLM narration layer
        over the deterministic report (spec sections 4, 5, 10).

        Usage:
            brief <free text, e.g. should I look at AAPL this week>

        Routes through the ToolRegistry (``ask_ceo``). The CEO interprets which
        instrument/timeframe you mean, runs the deterministic report, and narrates
        it; the deterministic core still decides. With no LLM configured the
        narration is a deterministic summary. If no instrument can be identified,
        it says so rather than analysing a guess.
        """

        if self._tool_service is None:
            return (
                "\n"
                "CEO Brief\n"
                "---------\n"
                "Status : NOT CONNECTED\n"
            )

        request = " ".join(a for a in args if a.strip()).strip()
        if not request:
            return (
                "Usage: brief <request>\n"
                "Example: brief should I look at AAPL this week"
            )

        try:
            payload = await self._tool_service.execute("ask_ceo", {"request": request})
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "brief command failed."
            )
            return f"Brief failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_brief(payload)

    def _format_brief(self, payload) -> str:
        """Render a CEO brief dict as plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        lines: list[str] = [
            "",
            f"CEO Brief: {get('instrument_key', '?')} ({get('timeframe', '-')})",
            "=" * 40,
            f"Recommendation   : {str(get('recommendation', 'unknown')).upper()}",
            f"Actionable       : {'YES' if get('is_actionable') else 'NO'}",
            f"Narrated by      : {get('narrated_by', '-')}",
            "",
            str(get("narrative") or ""),
            "",
            "The deterministic core decides; the narration only explains. "
            "Estimates, not guarantees -- analysis, not advice.",
            "",
        ]
        return "\n".join(lines)

    async def _investigate_command(
        self,
        args: list[str],
    ) -> str:
        """
        Run an agentic CEO investigation -- the LLM chooses and sequences the
        deterministic trading tools itself (spec sections 4, 5).

        Usage:
            investigate [research|quant|critic] <free-text request>

        An optional leading persona word narrows the sub-agent's toolset. Routes
        through the ToolRegistry (``investigate_ceo``); only trading tools are
        callable and the loop is bounded. With no LLM configured it returns an
        honest 'needs an LLM' result rather than fabricating a tool sequence.
        """

        if self._tool_service is None:
            return (
                "\n"
                "CEO Investigation\n"
                "-----------------\n"
                "Status : NOT CONNECTED\n"
            )

        tokens = [a for a in args if a.strip()]
        persona: str | None = None
        if tokens and tokens[0].lower() in ("research", "quant", "critic", "full"):
            persona = tokens[0].lower()
            tokens = tokens[1:]
        request = " ".join(tokens).strip()
        if not request:
            return (
                "Usage: investigate [research|quant|critic] <request>\n"
                "Example: investigate quant is AAPL overbought on the daily"
            )

        try:
            payload = await self._tool_service.execute(
                "investigate_ceo",
                {"request": request, "persona": persona}
                if persona
                else {"request": request},
            )
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "investigate command failed."
            )
            return f"Investigation failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_investigation(payload)

    def _format_investigation(self, payload) -> str:
        """Render a CEO investigation dict as plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        steps = get("steps") or []
        lines: list[str] = [
            "",
            "CEO Investigation",
            "=================",
            f"Grounded         : {'YES' if get('grounded') else 'NO'}",
            f"Stopped          : {get('stopped_reason', '-')}",
            f"Narrated by      : {get('narrated_by', '-')}",
            f"Tools used       : {', '.join(get('used_tools') or []) or '(none)'}",
        ]

        if steps:
            lines += ["", "Steps", "-----"]
            for s in steps:
                if not isinstance(s, dict):
                    continue
                flag = "ok" if s.get("ok") else f"FAILED ({s.get('error', '-')})"
                lines.append(f"  {s.get('index', '?')}. {s.get('tool', '?')} -> {flag}")

        lines += [
            "",
            "Answer",
            "------",
            str(get("answer") or ""),
            "",
            "The LLM orchestrates; the deterministic tools compute. Every number "
            "traces to a tool result above. Analysis, not advice.",
            "",
        ]
        return "\n".join(lines)

    async def _explain_command(
        self,
        args: list[str],
    ) -> str:
        """
        Explain WHY an instrument's recommendation came out the way it did -- no
        LLM involved (spec section 1).

        Usage:
            explain <symbol> [timeframe]

        Routes through the ToolRegistry (the ``explain_signal`` tool), so it
        computes nothing itself: it renders the consolidated evidence ledger the
        tool produced -- reasons that support vs oppose the fused direction, their
        net reliable weight, and the critic's reasons. A MOCK/insufficient run
        explains itself honestly as NO_TRADE (spec sections 27, 28).
        """

        if self._tool_service is None:
            return (
                "\n"
                "Signal Explanation\n"
                "------------------\n"
                "Status : NOT CONNECTED\n"
            )

        if not args or not args[0].strip():
            return (
                "Usage: explain <symbol> [timeframe]\n"
                "Example: explain AAPL 1d"
            )

        symbol = args[0].strip()
        timeframe = "1d"
        for token in args[1:]:
            if token.strip():
                timeframe = token.strip()

        try:
            payload = await self._tool_service.execute(
                "explain_signal",
                {"symbol": symbol, "timeframe": timeframe},
            )
        except Exception as exc:
            self._logger.bind(
                symbol=symbol, error_type=type(exc).__name__
            ).warning("explain command failed.")
            return f"Explanation failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_explanation(payload)

    def _format_explanation(self, payload) -> str:
        """Render an explanation dict as honest, plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        instrument = get("instrument") or {}
        symbol = instrument.get("symbol") or "?"
        exchange = instrument.get("exchange")
        header = symbol if not exchange else f"{symbol}:{exchange}"

        lines: list[str] = [
            "",
            f"Why: {header}",
            "=" * max(16, len(header) + 5),
            f"Timeframe        : {get('timeframe') or '-'}",
            f"RECOMMENDATION   : {str(get('recommendation') or 'unknown').upper()}",
            f"Direction        : {str(get('direction', 'unknown')).upper()}",
            f"Confidence       : {str(get('confidence', 'unknown')).upper()}",
            f"Actionable       : {'YES' if get('is_actionable') else 'NO'}",
            "",
            get("summary") or "",
            "",
            (
                f"Reliable evidence: {get('reliable_evidence_count', 0)} "
                f"of {get('total_evidence_count', 0)} total   "
                f"(support {self._fmt_num(get('supporting_weight'))} vs "
                f"oppose {self._fmt_num(get('opposing_weight'))}, "
                f"net {self._fmt_num(get('net_weight'))})"
            ),
        ]

        supporting = get("supporting") or []
        if supporting:
            lines += ["", "Supporting", "----------"]
            for r in supporting[:6]:
                if isinstance(r, dict):
                    lines.append(
                        f"  + [{r.get('type', '-')}] {r.get('detail', '-')} "
                        f"(w {self._fmt_num(r.get('weight'))})"
                    )

        opposing = get("opposing") or []
        if opposing:
            lines += ["", "Opposing", "--------"]
            for r in opposing[:6]:
                if isinstance(r, dict):
                    lines.append(
                        f"  - [{r.get('type', '-')}] {r.get('detail', '-')} "
                        f"(w {self._fmt_num(r.get('weight'))})"
                    )

        critic_reasons = get("critic_reasons") or []
        if critic_reasons:
            lines += ["", "Critic", "------"]
            for reason in critic_reasons[:8]:
                lines.append(f"  * {reason}")

        limitations = get("limitations") or []
        if limitations:
            lines += ["", "Limitations", "-----------"]
            for lim in limitations:
                lines.append(f"  ! {lim}")

        lines += [
            "",
            "This explains the deterministic recommendation; it is analysis, not "
            "advice, and probabilities are estimates, not guarantees.",
            "",
        ]
        return "\n".join(lines)

    async def _scan_command(
        self,
        args: list[str],
    ) -> str:
        """
        Scan a watchlist and rank it by directional signal for a human -- no LLM
        involved (spec sections 1, 26).

        Usage:
            scan <SYM1> <SYM2> ... [timeframe]

        Routes through the ToolRegistry (the ``scan_watchlist`` tool), so it
        computes nothing itself: every ranked row traces to that symbol's
        analysis. A trailing token matching a known timeframe (e.g. ``1d``) is
        read as the timeframe; everything else is a symbol. Mock/unusable rows
        are shown but flagged not actionable, and a symbol that could not be
        fetched is shown as an error row rather than dropped (spec sections 27, 28).
        """

        if self._tool_service is None:
            return (
                "\n"
                "Watchlist Scan\n"
                "--------------\n"
                "Status : NOT CONNECTED\n"
            )

        if not args:
            return (
                "Usage: scan <SYM1> <SYM2> ... [timeframe]\n"
                "Example: scan AAPL MSFT NVDA 1d"
            )

        # A trailing timeframe-shaped token is the timeframe; the rest are
        # symbols. Timeframes are short like 1d/1h/1wk/4h -- detect by a small
        # known set so a real symbol is never mistaken for one.
        _TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"}
        tokens = [t.strip() for t in args if t.strip()]
        timeframe = "1d"
        if len(tokens) > 1 and tokens[-1].lower() in _TIMEFRAMES:
            timeframe = tokens[-1].lower()
            tokens = tokens[:-1]

        if not tokens:
            return (
                "Usage: scan <SYM1> <SYM2> ... [timeframe]\n"
                "Example: scan AAPL MSFT NVDA 1d"
            )

        try:
            payload = await self._tool_service.execute(
                "scan_watchlist",
                {"symbols": tokens, "timeframe": timeframe},
            )
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "scan command failed."
            )
            return f"Scan failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_scan(payload)

    def _format_scan(self, payload) -> str:
        """Render a watchlist-scan dict as an honest, ranked plain-text table."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        entries = get("entries") or []

        lines: list[str] = [
            "",
            "Watchlist Scan",
            "==============",
            f"Timeframe   : {get('timeframe') or '-'}",
            (
                f"Requested   : {get('requested', 0)}   "
                f"Analysed : {get('analysed', 0)}   "
                f"Actionable : {get('actionable', 0)}   "
                f"Errored : {get('errored', 0)}"
            ),
            "",
            f"  {'#':<3} {'Symbol':<14} {'Signal':<9} {'Conf':<7} "
            f"{'Score':>7}  {'Act':<4} {'Reliable':<9} Note",
            "  " + "-" * 74,
        ]

        if not entries:
            lines.append("  (no symbols scanned)")
        else:
            for i, e in enumerate(entries, start=1):
                if not isinstance(e, dict):
                    continue
                direction = str(e.get("direction", "unknown")).upper()
                confidence = str(e.get("confidence", "-")).upper()
                score = e.get("directional_score")
                score_str = f"{score:+.2f}" if isinstance(score, (int, float)) else "-"
                actionable = "YES" if e.get("is_actionable") else "no"
                reliable = "reliable" if e.get("is_reliable") else "NOT rel."
                note = e.get("note") or ""
                if len(note) > 40:
                    note = note[:37] + "..."
                lines.append(
                    f"  {i:<3} {str(e.get('symbol', '?')):<14} {direction:<9} "
                    f"{confidence:<7} {score_str:>7}  {actionable:<4} "
                    f"{reliable:<9} {note}"
                )

        lines += [
            "",
            "Ranking is by directional signal strength, not a buy/sell "
            "recommendation.",
            "Signals are estimates, not guarantees -- decision support, not advice.",
            "",
        ]
        return "\n".join(lines)

    async def _portfolio_command(
        self,
        args: list[str],
    ) -> str:
        """
        Risk-budget a basket of trades for a human -- no LLM involved (spec
        section 5, portfolio-level position sizing / exposure).

        Usage:
            portfolio <SYM1> <SYM2> ... <equity> [timeframe]

        Routes through the ToolRegistry (the ``size_portfolio`` tool), so it
        computes nothing itself: it renders the allocation the tool produced --
        per-position shares/risk/notional, the total risk vs budget, gross
        exposure vs cap, and any excluded names with their reason. On MOCK data no
        symbol is actionable, so the plan is an honest empty allocation rather
        than a fabricated one (spec sections 27, 28).
        """

        if self._tool_service is None:
            return (
                "\n"
                "Portfolio Risk\n"
                "--------------\n"
                "Status : NOT CONNECTED\n"
            )

        # Split tokens: a known-timeframe token is the timeframe, a numeric token
        # is the account equity (last wins), everything else is a symbol.
        _TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"}
        symbols: list[str] = []
        equity: float | None = None
        timeframe = "1d"
        for raw in args:
            token = raw.strip()
            if not token:
                continue
            if token.lower() in _TIMEFRAMES:
                timeframe = token.lower()
                continue
            try:
                equity = float(token.replace(",", ""))
                continue
            except ValueError:
                symbols.append(token)

        if not symbols or equity is None:
            return (
                "Usage: portfolio <SYM1> <SYM2> ... <equity> [timeframe]\n"
                "Example: portfolio AAPL MSFT NVDA 100000"
            )
        if equity <= 0:
            return "Account equity must be a positive number."

        try:
            payload = await self._tool_service.execute(
                "size_portfolio",
                {"symbols": symbols, "account_equity": equity, "timeframe": timeframe},
            )
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "portfolio command failed."
            )
            return f"Portfolio sizing failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_portfolio(payload)

    def _format_portfolio(self, payload) -> str:
        """Render a portfolio-risk plan dict as honest, plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        positions = get("positions") or []

        lines: list[str] = [
            "",
            "Portfolio Risk",
            "==============",
            f"Account equity   : {self._fmt_num(get('account_equity'))}",
            (
                f"Risk budget      : {self._fmt_num(get('total_risk_budget'))}   "
                f"(used {self._fmt_num(get('total_risk'))}, "
                f"within budget: {'YES' if get('within_risk_budget') else 'NO'})"
            ),
            (
                f"Max exposure     : {self._fmt_num(get('max_gross_exposure'))}   "
                f"(gross {self._fmt_num(get('gross_exposure'))}, "
                f"within cap: {'YES' if get('within_exposure_cap') else 'NO'})"
            ),
            (
                f"Candidates       : {get('requested', 0)} requested, "
                f"{get('included', 0)} sized, {get('excluded', 0)} excluded"
            ),
            "",
            f"  {'Symbol':<14} {'Dir':<5} {'Shares':>10} {'Risk':>12} "
            f"{'Notional':>14}  Note",
            "  " + "-" * 72,
        ]

        if not positions:
            lines.append("  (no actionable candidates)")
        else:
            for p in positions:
                if not isinstance(p, dict):
                    continue
                note = p.get("note") or ("included" if p.get("included") else "excluded")
                if len(note) > 32:
                    note = note[:29] + "..."
                lines.append(
                    f"  {str(p.get('instrument_key', '?')):<14} "
                    f"{str(p.get('direction', '-')).upper():<5} "
                    f"{self._fmt_num(p.get('shares')):>10} "
                    f"{self._fmt_num(p.get('risk_amount')):>12} "
                    f"{self._fmt_num(p.get('notional')):>14}  {note}"
                )

        limitations = get("limitations") or []
        if limitations:
            lines += ["", "Notes", "-----"]
            for lim in limitations:
                lines.append(f"  ! {lim}")

        lines += [
            "",
            "Advisory risk geometry, not a recommendation to trade; sizes assume "
            "the stops shown hold.",
            "",
        ]
        return "\n".join(lines)

    async def _monitor_command(
        self,
        args: list[str],
    ) -> str:
        """
        Run one monitoring sweep for a human -- resolve the recorded predictions
        against the freshest market data and show how they scored (no LLM; spec
        sections 16, 29).

        Usage:
            monitor [SYMBOL:EXCHANGE] [limit]

        Routes through the ToolRegistry (``run_monitoring_pass``), so it computes
        nothing itself. It is one bounded pass, not a running background loop. A
        purely-numeric token is the limit; any other token is an instrument key
        (verbatim). PENDING/UNRESOLVABLE outcomes are surfaced and a thin or MOCK
        sample is reported but never called a reliable track record.
        """

        if self._tool_service is None:
            return (
                "\n"
                "Monitoring Sweep\n"
                "----------------\n"
                "Status : NOT CONNECTED\n"
            )

        instrument_key: str | None = None
        limit: int | None = None
        for raw in args:
            token = raw.strip()
            if not token:
                continue
            if token.isdigit():
                limit = int(token)
            else:
                instrument_key = token

        try:
            monitor_args: dict[str, Any] = {}
            if instrument_key is not None:
                monitor_args["instrument_key"] = instrument_key
            if limit is not None:
                monitor_args["limit"] = limit
            payload = await self._tool_service.execute(
                "run_monitoring_pass",
                monitor_args,
            )
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "monitor command failed."
            )
            return f"Monitoring failed: {type(exc).__name__}: {exc}"

        if isinstance(payload, dict) and "error" in payload:
            return str(payload["error"])

        return self._format_monitor(payload)

    def _format_monitor(self, payload) -> str:
        """Render a monitoring-sweep dict as honest, plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        perf = get("performance") or {}
        counts = perf.get("counts") or {}

        reliable = "YES" if perf.get("is_reliable") else "NO"
        mock = " (MOCK-resolved)" if perf.get("is_mock") else ""

        lines: list[str] = [
            "",
            "Monitoring Sweep",
            "================",
            (
                f"Swept            : {get('swept', 0)}   "
                f"(resolved {get('resolved', 0)}, pending {get('pending', 0)}, "
                f"unresolvable {get('unresolvable', 0)})"
            ),
            f"Scored           : {counts.get('scored', perf.get('scored', 0))}",
            f"Directional acc. : {self._fmt_pct(perf.get('directional_accuracy'))}",
            f"Coverage         : {self._fmt_pct(perf.get('coverage'))}",
            f"Mean realized    : {self._fmt_pct(perf.get('mean_realized_return'))}",
            f"Reliable         : {reliable}{mock}",
        ]

        limitations = perf.get("limitations") or []
        if limitations:
            lines += ["", "Notes", "-----"]
            for lim in limitations:
                lines.append(f"  ! {lim}")

        lines += [
            "",
            "One bounded resolve-and-score pass, not a running loop. A past "
            "track record is not a guarantee of future accuracy -- decision "
            "support, not advice.",
            "",
        ]
        return "\n".join(lines)

    async def _monitor_loop_command(
        self,
        args: list[str],
    ) -> str:
        """
        Control the autonomous monitoring loop (spec section 29 -- bounded, opt-in).

        Usage:
            monitor-loop start | stop | status

        Routes through the ToolRegistry. The loop only actually runs when it is
        enabled in configuration (TRADING_MONITOR_ENABLED); otherwise 'start'
        reports it stayed off. 'stop' is safe to call when it is not running.
        """

        if self._tool_service is None:
            return (
                "\n"
                "Monitoring Loop\n"
                "---------------\n"
                "Status : NOT CONNECTED\n"
            )

        action = (args[0].strip().lower() if args and args[0].strip() else "status")
        tool_by_action = {
            "start": "start_monitoring_loop",
            "stop": "stop_monitoring_loop",
            "status": "monitoring_loop_status",
        }
        if action not in tool_by_action:
            return "Usage: monitor-loop start | stop | status"

        try:
            payload = await self._tool_service.execute(tool_by_action[action], {})
        except Exception as exc:
            self._logger.bind(error_type=type(exc).__name__).warning(
                "monitor-loop command failed."
            )
            return f"Monitoring loop {action} failed: {type(exc).__name__}: {exc}"

        return self._format_scheduler_state(action, payload)

    def _format_scheduler_state(self, action: str, payload) -> str:
        """Render the monitoring-loop state as plain terminal text."""

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get
        running = "RUNNING" if get("running") else "stopped"
        enabled = "enabled" if get("enabled") else "disabled (set TRADING_MONITOR_ENABLED)"
        lines = [
            "",
            "Monitoring Loop",
            "===============",
            f"Action           : {action}",
            f"State            : {running}",
            f"Configured       : {enabled}",
            f"Interval         : {self._fmt_num(get('interval_seconds'))}s",
        ]
        if action == "start" and get("started") is False and not get("running"):
            lines.append(
                "Note             : the loop is disabled in configuration, so it "
                "did not start."
            )
        lines.append("")
        return "\n".join(lines)

    async def _track_record_command(
        self,
        args: list[str],
    ) -> str:
        """
        Surface the recorded prediction-audit trail and its track record for a
        human -- no LLM involved (spec sections 8, 28, 29).

        Usage:
            track-record [SYMBOL:EXCHANGE] [limit]

        The command routes through the ToolRegistry (``evaluate_track_record``
        for the aggregate, ``list_predictions`` for the trail), so it computes
        nothing itself: every count and rate it prints traces to a sub-object of
        those tools' results. It surfaces the honesty contract verbatim -- a
        thin or MOCK-resolved sample is reported but flagged NOT reliable, an
        empty history reads as "nothing to measure yet" rather than an error, and
        a past track record is never dressed up as a guarantee of future accuracy.
        """

        if self._tool_service is None:
            return (
                "\n"
                "Prediction Track Record\n"
                "-----------------------\n"
                "Status : NOT CONNECTED\n"
            )

        # Tolerant, order-independent parsing that mirrors ``analyze``: a purely
        # numeric token is the limit; any other token is the instrument key
        # (verbatim, SYMBOL:EXCHANGE -- the CLI never guesses an exchange). Last
        # of each wins, so the command adds no hidden behaviour of its own.
        instrument_key: str | None = None
        limit: int | None = None

        for token in args:
            cleaned = token.strip()
            if not cleaned:
                continue
            if cleaned.isdigit():
                limit = int(cleaned)
            else:
                instrument_key = cleaned

        # The aggregate covers the whole (optionally scoped) history; the trail
        # is capped so a long session does not flood the terminal.
        evaluate_args: dict[str, Any] = {}
        list_args: dict[str, Any] = {"limit": limit if limit is not None else 50}
        if instrument_key is not None:
            evaluate_args["instrument_key"] = instrument_key
            list_args["instrument_key"] = instrument_key
        if limit is not None:
            evaluate_args["limit"] = limit

        try:
            performance = await self._tool_service.execute(
                "evaluate_track_record",
                evaluate_args,
            )
            listing = await self._tool_service.execute(
                "list_predictions",
                list_args,
            )

        except Exception as exc:
            # A user-facing REPL command: a failure prints a message rather than
            # killing the session. Names/types only -- never an argument value.
            self._logger.bind(
                error_type=type(exc).__name__,
            ).warning("track-record command failed.")

            return f"Track record unavailable: {type(exc).__name__}: {exc}"

        return self._format_track_record(performance, listing, instrument_key)

    # ==========================================================
    # Track-record rendering
    # ==========================================================

    def _format_track_record(
        self,
        performance,
        listing,
        instrument_key: str | None,
    ) -> str:
        """
        Render the aggregate track record + the recorded audit trail as honest
        plain text. Composes only: every field is read straight from the two
        tools' ``to_dict`` payloads; nothing is computed or inferred here.
        """

        if not isinstance(performance, dict) or not isinstance(listing, dict):
            return str(performance)

        scope = instrument_key or "all instruments"
        counts = performance.get("counts") or {}
        listed = listing.get("predictions") or []

        reliable = bool(performance.get("is_reliable"))
        is_mock = bool(performance.get("is_mock"))

        lines: list[str] = [
            "",
            "Prediction Track Record",
            "=======================",
            f"Scope            : {scope}",
            f"Recorded (listed): {listing.get('count', 0)}",
            "",
            "Aggregate",
            "---------",
            f"Sample size      : {performance.get('sample_size', 0)}",
            f"Resolved         : {counts.get('resolved', 0)} "
            f"(pending {counts.get('pending', 0)}, "
            f"unresolvable {counts.get('unresolvable', 0)})",
            f"Scored           : {counts.get('scored', 0)} "
            f"(hits {counts.get('hits', 0)}, misses {counts.get('misses', 0)})",
            f"Directional acc  : {self._fmt_pct(performance.get('directional_accuracy'))}",
            f"Coverage         : {self._fmt_pct(performance.get('coverage'))}",
            f"Mean realized    : {self._fmt_num(performance.get('mean_realized_return'))}",
            f"Reliable         : {'YES' if reliable else 'NO'}"
            f"{' (MOCK-resolved)' if is_mock else ''}",
        ]

        limitations = performance.get("limitations") or []
        if limitations:
            lines += ["", "Limitations", "-----------"]
            for limitation in limitations:
                lines.append(f"  - {limitation}")

        lines += ["", "Recorded predictions", "--------------------"]

        if not listed:
            lines.append("  (none recorded this session)")
        else:
            for index, record in enumerate(listed, start=1):
                if not isinstance(record, dict):
                    continue
                instrument = record.get("instrument") or {}
                signal = record.get("signal") or {}
                provenance = record.get("provenance") or {}
                key = instrument.get("key") or instrument.get("symbol") or "?"
                lines.append(
                    f"  {index:>2}. {key:<16} "
                    f"{record.get('timeframe', '-'):<4} "
                    f"{str(record.get('recommendation', '?')).upper():<9} "
                    f"dir={str(signal.get('direction', '?')).upper():<8} "
                    f"conf={str(signal.get('confidence', '?')).upper():<6} "
                    f"tier={provenance.get('tier', '-'):<8} "
                    f"{record.get('created_at', '-')}"
                )

        lines += [
            "",
            "Note: a track record measures past predictions under stated "
            "conditions; it is not a guarantee of future accuracy. This is "
            "decision support, not advice.",
        ]

        return "\n".join(lines)

    async def _ask(
        self,
        args: list[str],
    ) -> str:
        """
        Send a message to the LLM, letting it call AetherOS tools.
        """

        if (
            self._agent is None
            and self._tool_loop is None
            and self._llm_service is None
        ):
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
        # Agent path -- the agent owns orchestration; the CLI only submits
        # the goal and renders the outcome.
        # ------------------------------------------------------

        if self._agent is not None:

            log = self._logger.bind(goal_chars=len(prompt))
            log.info("Agent run starting.")

            try:
                # Through the gateway when wired, so the run is tagged
                # source="terminal" and its lifecycle reaches both UIs. Without
                # a gateway (a minimal embedding), fall back to the agent
                # directly -- untagged, but still functional.
                if self._gateway is not None:
                    result = await self._gateway.submit(prompt, source="terminal")
                else:
                    result = await self._agent.run(prompt)

            except Exception as exc:
                # Only a provider/transport failure reaches here; tool failures
                # and policy refusals are handled inside the run and recorded on
                # the state. No lifecycle event will follow, so this is the one
                # agent-path outcome the terminal renders from a returned string.
                self._logger.bind(
                    error_type=type(exc).__name__,
                ).exception("Agent run failed.")

                return (
                    f"LLM request failed: "
                    f"{type(exc).__name__}: {exc}"
                )

            if result.ok:
                log.bind(
                    iterations=result.iterations,
                ).info("Agent run finished.")
            else:
                # A non-completed run (failure / emergency stop / spent budget)
                # is still returned to the user; the reason is logged for audit.
                self._logger.bind(
                    status=result.status.value,
                    stopped_reason=result.stopped_reason,
                    iterations=result.iterations,
                ).warning("Agent run did not complete.")

            # With a gateway wired, the run enters the unified interaction
            # pipeline and the CLI's TraceEvent subscriber renders the answer
            # (and every tool/error along the way) as the run emits it -- the
            # single source of truth both UIs share. Returning "" then keeps
            # that the one render path and avoids double-printing the answer.
            #
            # Without a gateway (a unit test, a minimal embedding) there is no
            # subscriber listening, so the answer would be lost. Fall back to
            # rendering it directly from the returned result -- the same
            # defensive direct path the CLI runtime documents.
            if self._gateway is not None:
                return ""

            return self._format_run_result(result)

        # ------------------------------------------------------
        # Legacy tool-loop path
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

    def _format_run_result(
        self,
        result,
    ) -> str:
        """
        Render an ``AgentRunResult`` for the terminal.

        Deliberately the same shape as :meth:`_format_answer` so the migration
        to the agent core does not change what the user sees: the answer, then
        the tools that ran, then an "stopped early" note when the run ended for
        any reason other than a final answer.
        """

        answer = result.final_response or "(no answer)"

        records = result.state.tool_results

        if not records:
            return answer

        # Which tools ran is part of the answer's evidence, so it is shown
        # rather than buried in the log file. Names only -- an argument value
        # may be a secret and never belongs in the visible transcript either.
        used = ", ".join(
            f"{record.name}"
            f"{'' if record.ok else ' (failed)'}"
            for record in records
        )

        lines = [answer, "", f"Tools used: {used}"]

        if result.stopped_reason != "final_answer":
            lines.append(
                f"Stopped early: {result.stopped_reason} "
                f"after {result.iterations} iterations."
            )

        return "\n".join(lines)

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

    # ==========================================================
    # Trading report rendering
    # ==========================================================

    @staticmethod
    def _fmt_num(value, digits: int = 4) -> str:
        """A number for display, or ``-`` when it is missing/non-numeric."""

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "-"

        return f"{value:,.{digits}f}"

    @staticmethod
    def _fmt_pct(value, digits: int = 1) -> str:
        """A 0-1 fraction as a percentage, or ``-`` when missing."""

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "-"

        return f"{value * 100:.{digits}f}%"

    def _format_advisory(self, label: str, section) -> str:
        """
        One honest line for an advisory layer (news / calendar / fundamentals).

        Absent layer -> "not analysed"; present -> its directional/summary read
        plus an explicit reliability flag, so an unreliable MOCK read is never
        dressed up as a trustworthy one.
        """

        if section is None:
            return f"{label:<16} : not analysed"

        reliable = section.get("is_reliable")
        flag = "reliable" if reliable else "NOT reliable"

        return f"{label:<16} : {self._advisory_summary(section)} ({flag})"

    @staticmethod
    def _advisory_summary(section: dict) -> str:
        """A compact human summary of an advisory layer's own read."""

        # Calendar has no direction; it is summarised by event pressure.
        if "has_high_impact" in section or "event_count" in section:
            count = section.get("event_count", 0)
            impact = "high-impact event ahead" if section.get(
                "has_high_impact"
            ) else "no high-impact event"
            return f"{impact}, {count} scheduled"

        direction = str(section.get("direction", "unknown")).upper()

        # Macro context: the broad-market posture is the headline read.
        if "posture" in section:
            posture = str(section.get("posture", "unknown")).upper()
            return f"{posture} ({direction})"

        # Multi-timeframe: the alignment against the higher timeframe is headline.
        if "alignment" in section:
            alignment = str(section.get("alignment", "unknown")).upper()
            higher_tf = section.get("higher_timeframe", "higher")
            higher_dir = str(section.get("higher_direction", "unknown")).upper()
            return f"{alignment} ({higher_tf} {higher_dir})"

        # Divergence: whether a momentum divergence is present and which way.
        if "has_divergence" in section:
            if section.get("has_divergence"):
                return f"divergence {direction}"
            return f"no divergence ({direction})"

        # Breakout: whether the latest close broke the channel and which way.
        if "has_breakout" in section:
            if section.get("has_breakout"):
                vol = " vol-confirmed" if section.get("volume_confirmed") else ""
                return f"breakout {direction}{vol}"
            return f"no breakout ({direction})"

        # Relative strength: the excess return vs the benchmark is the headline.
        if "relative_return" in section:
            excess = section.get("relative_return")
            bench = section.get("benchmark") or "benchmark"
            if isinstance(excess, (int, float)):
                return f"{direction} vs {bench} ({excess * 100:+.2f}% excess)"
            return f"{direction} vs {bench}"

        # Anomaly: whether the last bar is a statistical outlier.
        if "is_anomalous" in section:
            state = "anomaly" if section.get("is_anomalous") else "no anomaly"
            return f"{state} ({direction})"

        # Historical analogue: the share of nearest analogues that rose.
        if "up_rate" in section:
            up_rate = section.get("up_rate")
            if isinstance(up_rate, (int, float)):
                return f"{direction} ({up_rate * 100:.0f}% of analogues rose)"
            return direction

        # News / fundamentals: a directional lean is the headline read.
        confidence = section.get("confidence")
        if isinstance(confidence, str) and confidence:
            return f"{direction} (confidence {confidence.upper()})"

        return direction

    def _format_trading_report(self, payload) -> str:
        """
        Render a section-27 trading report dict as honest, plain terminal text.

        Composes only -- it reads fields straight from the tool's ``to_dict``
        and never computes or infers a value the pipeline did not produce. A
        missing probability is shown as "not available" with its reason, a MOCK
        run is shown as NO_TRADE / not actionable, and every report ends with
        the mandatory reminder that probabilities are estimates, not guarantees.
        """

        if not isinstance(payload, dict):
            return str(payload)

        get = payload.get

        instrument = get("instrument") or {}
        symbol = instrument.get("symbol") or "?"
        exchange = instrument.get("exchange")
        name = instrument.get("name")

        header = symbol if not exchange else f"{symbol}:{exchange}"
        title = header if not name else f"{header}  ({name})"

        signal = get("signal") or {}
        recommendation = str(get("recommendation") or "unknown").upper()
        actionable = bool(get("is_actionable"))

        lines: list[str] = [
            "",
            title,
            "=" * max(16, len(title)),
            f"Timeframe        : {get('timeframe') or '-'}",
            f"Last price       : {self._fmt_num(get('last_price'))}",
            "",
            f"RECOMMENDATION   : {recommendation}",
            f"Actionable       : {'YES' if actionable else 'NO'}",
            "",
            "Signal",
            "------",
            f"Direction        : {str(signal.get('direction', 'unknown')).upper()}",
            f"Confidence       : {str(signal.get('confidence', 'unknown')).upper()}",
        ]

        score = signal.get("directional_score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            lines.append(f"Directional score: {score:+.3f}")

        # ------------------------------------------------------
        # Probability -- never fabricated. The report only carries an estimate
        # once it has passed its own out-of-sample reliability gate; otherwise
        # the field is null and the omission is stated, not invented.
        # ------------------------------------------------------

        probability = get("probability")

        lines += ["", "Probability", "-----------"]

        if probability is None:
            lines.append(
                "Not available -- no calibrated probability passed its "
                "out-of-sample reliability gate (never fabricated)."
            )
        else:
            prob = probability.get("probability") or {}
            lines.append(f"P(UP)            : {self._fmt_pct(prob.get('up'))}")
            lines.append(f"P(DOWN)          : {self._fmt_pct(prob.get('down'))}")
            lines.append(
                f"Horizon          : {probability.get('horizon', '-')} bars"
            )

        # ------------------------------------------------------
        # Market regime + key levels
        # ------------------------------------------------------

        regime = get("market_regime") or {}
        # The deterministic trending/ranging/volatile read is surfaced only when
        # the regime layer ran and produced a reliable classification; otherwise
        # only the structure-derived trend is shown (no fabricated regime).
        detected = regime.get("regime") or {}
        lines += [
            "",
            "Market regime",
            "-------------",
            f"Trend            : {str(regime.get('trend', 'unknown')).upper()}",
            f"Trend strength   : {self._fmt_num(regime.get('trend_strength'), 3)}",
        ]
        if detected:
            classification = str(detected.get("regime", "unknown")).upper()
            reliable = "yes" if detected.get("is_reliable") else "no"
            lines += [
                f"Classification   : {classification}",
                f"ADX              : {self._fmt_num(detected.get('adx'), 1)}",
                f"ATR % of price   : {self._fmt_num(detected.get('atr_pct'), 4)}",
                f"Reliable         : {reliable}",
            ]

        key_levels = get("key_levels") or {}
        supports = key_levels.get("supports") or []
        resistances = key_levels.get("resistances") or []

        def _levels(levels: list) -> str:
            prices = [
                self._fmt_num(lvl.get("price"), 2)
                for lvl in levels
                if isinstance(lvl, dict)
            ]
            return ", ".join(prices) if prices else "none identified"

        lines += [
            "",
            "Key levels",
            "----------",
            f"Supports         : {_levels(supports)}",
            f"Resistances      : {_levels(resistances)}",
        ]

        # ------------------------------------------------------
        # Risk / reward
        # ------------------------------------------------------

        risk = get("risk") or {}
        lines += [
            "",
            "Risk / reward",
            "-------------",
            f"Entry            : {self._fmt_num(risk.get('entry'), 2)}",
            f"Stop loss        : {self._fmt_num(risk.get('stop_loss'), 2)}",
            f"Target           : {self._fmt_num(risk.get('target'), 2)}",
            f"Risk/reward      : {self._fmt_num(risk.get('risk_reward_ratio'), 2)}",
            f"Overall risk     : {str(risk.get('overall_risk', 'unknown')).upper()}",
        ]

        invalidation = get("invalidation") or risk.get("invalidation")
        lines.append(f"Invalidation     : {invalidation or '-'}")

        horizon = get("horizon") or {}
        lines.append(
            f"Horizon          : {horizon.get('bars', '-')} bars "
            f"({horizon.get('timeframe', '-')})"
        )

        # ------------------------------------------------------
        # Critic verdict + per-check statuses
        # ------------------------------------------------------

        critique = get("critique") or {}
        lines += [
            "",
            "Critic",
            "------",
            f"Verdict          : {str(critique.get('verdict', 'unknown')).upper()}",
        ]

        for check in critique.get("checks") or []:
            if not isinstance(check, dict):
                continue
            status = str(check.get("status", "?")).upper()
            detail = check.get("detail")
            row = f"  - {check.get('name', '?'):<22} {status}"
            if detail:
                row += f" : {detail}"
            lines.append(row)

        # ------------------------------------------------------
        # Advisory layers -- surfaced with an explicit reliability flag so an
        # unreliable MOCK read is never presented as trustworthy.
        # ------------------------------------------------------

        lines += [
            "",
            "Advisory layers",
            "---------------",
            self._format_advisory("News/sentiment", get("news")),
            self._format_advisory("Event calendar", get("calendar")),
            self._format_advisory("Fundamentals", get("fundamentals")),
            self._format_advisory("Relative strength", get("relative_strength")),
            self._format_advisory("Anomaly", get("anomaly")),
            self._format_advisory("Historical", get("historical_analogue")),
            self._format_advisory("Macro context", get("macro")),
            self._format_advisory("Multi-timeframe", get("multi_timeframe")),
            self._format_advisory("Divergence", get("divergence")),
            self._format_advisory("Breakout", get("breakout")),
        ]

        backtest = get("backtest")
        if isinstance(backtest, dict):
            reliable = "reliable" if backtest.get("is_reliable") else "NOT reliable"
            lines.append(
                f"{'Backtest':<16} : {backtest.get('evaluated', '-')} calls, "
                f"accuracy {self._fmt_pct(backtest.get('directional_accuracy'))} "
                f"({reliable})"
            )

        # ------------------------------------------------------
        # Evidence (top items) + limitations
        # ------------------------------------------------------

        evidence = get("evidence") or []
        if evidence:
            lines += ["", "Evidence", "--------"]
            for item in evidence[:6]:
                if isinstance(item, dict):
                    detail = item.get("detail") or item.get("assertion") or "-"
                    lines.append(f"  - {detail}")

        limitations = get("limitations") or []
        if limitations:
            lines += ["", "Limitations", "-----------"]
            for limitation in limitations:
                lines.append(f"  - {limitation}")

        # ------------------------------------------------------
        # Provenance / model + the mandatory uncertainty reminder
        # ------------------------------------------------------

        model = get("model") or {}
        provenance = get("provenance") or {}
        lines += [
            "",
            f"Data source      : tier={provenance.get('tier', '-')}",
            f"Model            : {model.get('pipeline', '-')}",
            "",
            "Note: probabilities and signals are estimates under the stated "
            "conditions, not guarantees. This is decision support, not advice.",
        ]

        return "\n".join(lines)