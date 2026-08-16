from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import time
import os

class CLIUI:
    """
    Terminal user interface for AetherOS CLI.
    """

    VERSION = "v0.1.0 — Preview"

    def __init__(self) -> None:
        self.console = Console()

    # ==========================================================
    # Startup Screen
    # ==========================================================

    def show_startup(self) -> None:
        self.console.clear()

        self._show_logo()

        self.console.print()

        version = Text(
            self.VERSION,
            style="dim",
        )

        self.console.print(version)
        self.console.print()

        self.console.print(
            Text.assemble(
                ("Usage: ", "bold"),
                ("aether", "cyan"),
                (" <command> [options]", "white"),
            )
        )

        self.console.print()

        self.console.print(
            "Use 'aether <command> --help' "
            "to get detailed help for any command.",
            style="dim",
        )

        self.console.print()

        self._show_commands()

        self.console.print()

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
            ("help", "Show available commands"),
            ("status", "Show system status"),
            ("tools", "List registered tools"),
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

    def show_startup(self) -> None:
        """
        Clear the terminal and display the AetherOS CLI startup screen.
        """

        # Clear terminal completely before showing CLI UI.
        if os.name == "nt":
            print("JI")
            # os.system("cls")
        else:
            print("hello")
            # os.system("clear")

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