from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import time


def _ensure_unicode_output() -> None:
    """
    Make stdout/stderr able to carry the UI's box-drawing characters.

    On Windows a *redirected* stdout defaults to the legacy ANSI code page
    (cp1252), which cannot encode the panel borders or the startup logo. The
    application therefore died with ``UnicodeEncodeError`` on the very first
    line it printed — after bootstrap had fully succeeded, before the prompt
    appeared, and only when output was piped, captured by CI, or wrapped by a
    launcher. An interactive run looked perfectly healthy.

    ``errors="replace"`` as well as the encoding: a stream that still cannot
    represent some glyph should degrade to ``?`` and keep going, because
    cosmetics are never worth ending a session for.
    """

    for stream in (sys.stdout, sys.stderr):

        reconfigure = getattr(stream, "reconfigure", None)

        if reconfigure is None:
            # Not a TextIOWrapper — a test's StringIO, or an already-detached
            # stream. Rich handles those; there is nothing to widen.
            continue

        try:
            reconfigure(encoding="utf-8", errors="replace")

        except (OSError, ValueError):
            # Narrow and deliberate: a stream that refuses reconfiguration is
            # left exactly as it was, and rich's safe_box fallback still
            # renders. Not caught broadly, and not silent about why.
            continue


class CLIUI:
    """
    Terminal user interface for AetherOS CLI.
    """

    VERSION = "v0.1.0 — Preview"

    def __init__(self) -> None:
        # Before the Console: the first print is the logo, and it is the
        # widest character set the UI ever emits.
        _ensure_unicode_output()

        self.console = Console()

    # ==========================================================
    # Startup Screen
    # ==========================================================

    # ==========================================================
    # Logo
    # ==========================================================

    def _show_logo(self) -> None:
        logo = r"""
     █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗  ██████╗ ███████╗
    ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔═══██╗██╔════╝
    ███████║█████╗     ██║   ███████║█████╗  ██████╔╝██║   ██║███████╗
    ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗██║   ██║╚════██║
    ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║╚██████╔╝███████║
    ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        """

        text = Text(
            logo,
            style="bold cyan",
        )

        self.console.print(text)

    # ==========================================================
    # Command Table
    # ==========================================================

    def _show_commands(self) -> None:
        table = Table(
            title="Commands",
            title_style="bold blue",
            header_style="bold",
            border_style="dim",
            show_lines=False,
            padding=(0, 1),
        )

        table.add_column(
            "command",
            style="cyan",
            no_wrap=True,
        )

        table.add_column(
            "description",
        )
        

        commands = [
            ("help", "Show available commands",),
            ("status", "Show system status"),
            ("tools", "List registered tools"),
            ("ask", "Send a message to the LLM"),
            ("desktop", "Desktop operations"),
            ("browser", "Browser operations"),
            ("vision", "Vision operations"),
            ("llm", "LLM operations"),
            ("clear", "Clear terminal"),
            ("exit", "Shutdown AetherOS"),
        ]

        for command, description in commands:
            table.add_row(
                command,
                description,
            )

        self.console.print(table)

    # ==========================================================
    # Prompt
    # ==========================================================

    def prompt(self) -> str:
        return self.console.input(
            "\n[bold cyan]AetherOS[/bold cyan] [dim]>[/dim] "
        )

    # ==========================================================
    # Messages
    # ==========================================================

    def success(self, message: str) -> None:
        self.console.print(
            f"[bold green]✓[/bold green] {message}"
        )

    def error(self, message: str) -> None:
        self.console.print(
            f"[bold red]✗[/bold red] {message}"
        )

    def info(self, message: str) -> None:
        self.console.print(
            f"[bold cyan]●[/bold cyan] {message}"
        )

    def goodbye(self) -> None:
        self.console.print()
        self.console.print(
            Panel(
                "AetherOS shutting down...",
                border_style="cyan",
            )
        )

    def answer(
        self,
        message: str,
    ) -> None:
        """
        Render a model response.
        """

        self.console.print()
        self.console.print(
            Panel(
                Text(message),
                title="AetherOS",
                title_align="left",
                border_style="cyan",
            )
        )

    def note(
        self,
        message: str,
    ) -> None:
        """
        Render a secondary line beneath a response.
        """

        self.console.print(
            f"[dim]{message}[/dim]"
        )

    # ==========================================================
    # Startup Screen
    # ==========================================================

    def show_startup(self) -> None:
        """
        Clear the terminal and display the AetherOS CLI startup screen.
        """

        self.console.clear()

        self._show_logo()

        self.console.print()
        time.sleep(0.35)
        self.console.print(
            self.VERSION,
            style="dim",
        )
        time.sleep(.25)

        self.console.print()

        self.console.print(
            "[bold]Usage:[/bold] "
            "[cyan]aether[/cyan] "
            "[white]<command> [options][/white]"
        )
        time.sleep(0.25)

        self.console.print()

        self.console.print(
            "Use 'aether <command> --help' "
            "to get detailed help for any command.",
            style="dim",
        )
        time.sleep(0.35)
        self.console.print()

        self._show_commands()
        time.sleep(0.25)
        self.console.print()

        
    def _slow_print(
    self,
    text: str,
    delay: float = 0.02,
) -> None:
        for char in text:
            self.console.print(
                char,
                end="",
                flush=True,
            )
            time.sleep(delay)

        self.console.print()