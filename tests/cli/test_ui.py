"""
The terminal UI must not be able to abort the application.

Bootstrap succeeding and then the first ``console.print`` killing the process is
the worst failure shape available: every subsystem reported healthy, and the user
saw a traceback instead of a prompt. It happened for real — a redirected stdout
on Windows gets the legacy cp1252 code page, which cannot encode the startup
logo's block characters or a rich Panel's borders — and it was invisible
interactively, where stdout is a UTF-8 console.
"""

from __future__ import annotations

import io
import sys

import pytest

from aetheros.cli.ui import CLIUI


@pytest.fixture
def cp1252_stdout(monkeypatch: pytest.MonkeyPatch):
    """
    Replace stdout with a real cp1252 text stream.

    A ``TextIOWrapper`` over ``BytesIO`` rather than ``StringIO``: only the
    wrapper actually encodes, and encoding is the whole point. StringIO accepts
    any str and would make the test pass without the fix.
    """

    buffer = io.BytesIO()

    stream = io.TextIOWrapper(
        buffer,
        encoding="cp1252",
        errors="strict",
        newline="",
        write_through=True,
    )

    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)

    return stream


class TestNonUnicodeTerminal:

    def test_startup_screen_renders_on_a_cp1252_stdout(
        self,
        cp1252_stdout,
    ) -> None:
        """
        The regression itself: this raised UnicodeEncodeError from _show_logo.
        """

        CLIUI().show_startup()

    def test_stdout_is_widened_to_utf8(
        self,
        cp1252_stdout,
    ) -> None:
        """
        Asserts the mechanism, not just the absence of a crash — so that a
        future refactor which happens to avoid the logo does not quietly leave
        every other panel exposed.
        """

        assert cp1252_stdout.encoding.lower() == "cp1252"

        CLIUI()

        assert sys.stdout.encoding.lower() == "utf-8"
        assert sys.stdout.errors == "replace"

    def test_an_unreconfigurable_stream_does_not_raise(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        StringIO has no ``reconfigure``, which is how pytest's own capture and
        most test doubles behave. Constructing the UI must still work.
        """

        monkeypatch.setattr(sys, "stdout", io.StringIO())
        monkeypatch.setattr(sys, "stderr", io.StringIO())

        CLIUI()

    def test_a_stream_that_refuses_reconfiguration_does_not_raise(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        A stream may expose ``reconfigure`` and still reject it — a detached or
        already-closed wrapper raises ValueError. That must not surface as a
        startup failure.
        """

        class Hostile(io.StringIO):

            def reconfigure(self, **kwargs: object) -> None:
                raise ValueError("stream is detached")

        monkeypatch.setattr(sys, "stdout", Hostile())
        monkeypatch.setattr(sys, "stderr", Hostile())

        CLIUI()

    def test_logo_survives_a_glyph_the_stream_cannot_encode(
        self,
        cp1252_stdout,
    ) -> None:
        """
        ``errors="replace"`` is the second half of the fix. Without it a single
        unrepresentable character still aborts the print, so assert that writing
        one degrades instead of raising.
        """

        ui = CLIUI()

        ui.console.print("█╗ 中文 \U0001f600")
