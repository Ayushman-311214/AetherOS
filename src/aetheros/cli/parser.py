from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ParsedCommand:
    """
    Represents a parsed CLI command.
    """

    name: str
    args: list[str]


class CommandParser:
    """
    Parses user input into a command name and arguments.

    Examples:

        "help"
        -> ParsedCommand("help", [])

        "status"
        -> ParsedCommand("status", [])

        "open chrome"
        -> ParsedCommand("open", ["chrome"])

        "move_mouse 500 300"
        -> ParsedCommand(
            "move_mouse",
            ["500", "300"],
        )
    """

    def parse(self, text: str) -> ParsedCommand | None:
        """
        Parse a command string.

        Empty input returns None.
        """

        text = text.strip()

        if not text:
            return None

        parts = text.split()

        return ParsedCommand(
            name=parts[0].lower(),
            args=parts[1:],
        )