"""
Command execution.

Three decisions in here are load-bearing.

**A non-zero exit code is a failure, and it is reported as one.** ``subprocess``
does not raise for a command that ran and failed, so the easy implementation
returns ``success: true`` for ``git push`` rejecting a push, ``pytest`` reporting
failures, or ``pip install`` finding no such package. The agent then builds its
next step on a false premise. :class:`CommandResult` therefore carries
``exit_code`` and derives ``succeeded`` from it, and the tool layer surfaces both.

**Shell and no-shell are separate calls, not a flag.** With ``shell=True`` the
string ``notepad & del important.txt`` is two commands, and any argument
interpolated into it can add more. Plain execution is the default and involves no
shell at all; the shell path is a distinct function gated by the ``ALLOW_SHELL``
capability, so enabling shell semantics is a deliberate configuration choice.

**Execution is genuinely asynchronous.** Everywhere else in this subsystem an
``async def`` service wraps a synchronous backend, because a mouse move takes
microseconds. A command can take a minute, and blocking the event loop for a
minute stalls every other task in the process -- including whatever is supposed to
be monitoring this one. ``asyncio.create_subprocess_*`` is used instead.
"""

from __future__ import annotations

import asyncio
import locale
import os
import time
from dataclasses import dataclass
from pathlib import Path

from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger

# Hard ceiling on any command, regardless of what the caller asks for. A command
# without a bound is a hang with no diagnosis, and the master constraint against
# infinite retries applies to waits for the same reason.
MAX_TIMEOUT_SECONDS = 600.0

DEFAULT_TIMEOUT_SECONDS = 60.0

# Output beyond this is truncated. A command that prints a 40 MB log would
# otherwise arrive in the model's context in full and displace everything else in
# it. Truncation is reported rather than hidden.
MAX_OUTPUT_CHARS = 20_000


def _decode(raw: bytes) -> str:
    """
    Decode command output without ever raising.

    Windows console programs emit the OEM code page, not UTF-8, and a single
    stray byte from a progress spinner would otherwise turn a successful command
    into a UnicodeDecodeError. ``errors="replace"`` keeps the readable part and
    marks the rest, which is strictly more useful than losing the whole stream.
    """

    if not raw:
        return ""

    for encoding in ("utf-8", locale.getpreferredencoding(False), "cp1252"):

        if not encoding:
            continue

        try:
            return raw.decode(encoding)

        except (UnicodeDecodeError, LookupError):
            continue

    return raw.decode("utf-8", errors="replace")


def _clip(text: str) -> tuple[str, bool]:
    """
    Trim output to the cap, reporting whether anything was removed.
    """

    if len(text) <= MAX_OUTPUT_CHARS:
        return text, False

    kept = text[:MAX_OUTPUT_CHARS]

    return (
        f"{kept}\n\n[... {len(text) - MAX_OUTPUT_CHARS} more characters omitted]",
        True,
    )


@dataclass(frozen=True, slots=True)
class CommandResult:
    """
    What a command actually did.

    ``succeeded`` is derived from ``exit_code`` rather than stored, so there is no
    way to construct a result that claims success while carrying a failing code.
    """

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    cwd: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, object]:

        return {
            "command": self.command,
            # First, because it is the field that decides what the caller does
            # next, and burying it under a wall of stdout invites skipping it.
            "exit_code": self.exit_code,
            "succeeded": self.succeeded,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "duration_seconds": round(self.duration, 3),
            "cwd": self.cwd,
        }


class TerminalService:
    """
    Runs commands and reports honestly on how they went.
    """

    def __init__(self) -> None:

        self._logger = get_logger("desktop.terminal")

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _bounded(timeout: float | None) -> float:

        if timeout is None:
            return DEFAULT_TIMEOUT_SECONDS

        if timeout <= 0:
            raise DesktopError(
                code="TERMINAL_TIMEOUT_INVALID",
                message=f"Timeout must be positive, got {timeout}.",
                hint="Pass a timeout in seconds, for example 30.",
            )

        return min(timeout, MAX_TIMEOUT_SECONDS)

    @staticmethod
    def _directory(cwd: str | Path | None) -> Path:

        if cwd is None:
            return Path.cwd()

        resolved = Path(cwd).expanduser()

        if not resolved.is_dir():
            raise DesktopError(
                code="TERMINAL_CWD_INVALID",
                message=f"Working directory does not exist: {resolved}.",
                hint="Create it first, or omit cwd to use the current directory.",
            )

        return resolved

    @staticmethod
    def _environment(env: dict[str, str] | None) -> dict[str, str] | None:
        """
        Extend the current environment rather than replacing it.

        A replaced environment has no PATH, SystemRoot or TEMP, and most Windows
        programs then fail to start in ways that look nothing like a missing
        variable.
        """

        return {**os.environ, **env} if env else None

    async def _collect(
        self,
        process: asyncio.subprocess.Process,
        *,
        command: str,
        limit: float,
        started: float,
        directory: Path,
    ) -> CommandResult:
        """
        Await completion, or kill the command and raise on timeout.
        """

        try:
            raw_out, raw_err = await asyncio.wait_for(
                process.communicate(),
                timeout=limit,
            )

        except (asyncio.TimeoutError, TimeoutError) as exc:

            # Kill rather than terminate: the command has already had its full
            # allowance, and a process ignoring termination would hold the slot
            # indefinitely.
            try:
                process.kill()

            except ProcessLookupError:
                # Exited between the timeout firing and the kill. Nothing to do.
                pass

            try:
                await asyncio.wait_for(process.wait(), timeout=5)

            except (asyncio.TimeoutError, TimeoutError):
                # Reaping failed; the raise below is still the right outcome and
                # the orphan is visible in the log.
                self._logger.bind(command=command).warning(
                    "Timed-out command did not exit after kill."
                )

            raise DesktopError(
                code="TERMINAL_TIMEOUT",
                message=(
                    f"Command exceeded its {limit:g}s timeout and was killed: "
                    f"{command}"
                ),
                hint=(
                    "Output was not captured, because the command was still "
                    "writing when it was killed. Raise the timeout, or run a "
                    "command that finishes."
                ),
                cause=exc,
            ) from exc

        stdout, out_clipped = _clip(_decode(raw_out))
        stderr, err_clipped = _clip(_decode(raw_err))

        # returncode is set once communicate() returns; None would mean the
        # process is somehow still running, which should not be reachable here.
        exit_code = process.returncode if process.returncode is not None else -1

        result = CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=time.perf_counter() - started,
            cwd=str(directory),
            stdout_truncated=out_clipped,
            stderr_truncated=err_clipped,
        )

        # Logged at warning when it failed: a non-zero exit is the thing an
        # operator reading the log is looking for.
        self._logger.bind(
            command=command,
            exit_code=exit_code,
            duration=round(result.duration, 3),
            cwd=str(directory),
        ).log(
            "DEBUG" if result.succeeded else "WARNING",
            "Command finished.",
        )

        return result

    # ==========================================================
    # Execution
    # ==========================================================

    async def run(
        self,
        command: str | list[str],
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Run a program directly, with no shell.

        ``command`` as a list is the safe form: each element is one argument, and
        nothing in it is interpreted. A bare string is accepted for convenience
        and is split on whitespace -- which is wrong for paths containing spaces,
        so a path with spaces must be passed as a list element.

        No shell means no pipes, no redirection, no ``&&``, and no way for an
        interpolated value to become a second command.
        """

        if not command:
            raise DesktopError(
                code="TERMINAL_COMMAND_EMPTY",
                message="No command was given.",
                hint="Pass an executable and its arguments.",
            )

        argv = command.split() if isinstance(command, str) else list(command)

        if not argv:
            raise DesktopError(
                code="TERMINAL_COMMAND_EMPTY",
                message="No command was given.",
                hint="Pass an executable and its arguments.",
            )

        directory = self._directory(cwd)
        limit = self._bounded(timeout)
        rendered = " ".join(argv)

        started = time.perf_counter()

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(directory),
                env=self._environment(env),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        except FileNotFoundError as exc:
            raise DesktopError(
                code="TERMINAL_COMMAND_NOT_FOUND",
                message=f"Executable not found: {argv[0]!r}.",
                hint=(
                    "Use a full path, or a name on PATH. Nothing was run. Note "
                    "that shell builtins such as 'dir' and 'echo' are not "
                    "executables -- use execute_shell for those."
                ),
                cause=exc,
            ) from exc

        except PermissionError as exc:
            raise DesktopError(
                code="TERMINAL_NOT_PERMITTED",
                message=f"Not permitted to run {argv[0]!r}.",
                hint="Check the file's permissions. Nothing was run.",
                cause=exc,
            ) from exc

        except OSError as exc:
            raise DesktopError(
                code="TERMINAL_LAUNCH_FAILED",
                message=f"Could not run {argv[0]!r}: {exc}.",
                hint="Nothing was run.",
                cause=exc,
            ) from exc

        return await self._collect(
            process,
            command=rendered,
            limit=limit,
            started=started,
            directory=directory,
        )

    async def run_shell(
        self,
        command: str,
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Run a command string through the system shell.

        The shell interprets the whole string, so ``;``, ``&&``, ``|``, ``>`` and
        backticks all take effect. That is the point of this method and also its
        danger: one string can be several commands, and anything interpolated into
        it can add more. Callers reach this only through ``execute_shell``, which
        requires the ``ALLOW_SHELL`` capability to be enabled in configuration.

        Prefer :meth:`run` for anything that does not genuinely need shell
        syntax.
        """

        text = command.strip()

        if not text:
            raise DesktopError(
                code="TERMINAL_COMMAND_EMPTY",
                message="No command was given.",
                hint="Pass a shell command.",
            )

        directory = self._directory(cwd)
        limit = self._bounded(timeout)

        started = time.perf_counter()

        self._logger.bind(command=text, cwd=str(directory)).info(
            "Running shell command."
        )

        try:
            process = await asyncio.create_subprocess_shell(
                text,
                cwd=str(directory),
                env=self._environment(env),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        except OSError as exc:
            raise DesktopError(
                code="TERMINAL_LAUNCH_FAILED",
                message=f"Could not start the shell: {exc}.",
                hint="Nothing was run.",
                cause=exc,
            ) from exc

        return await self._collect(
            process,
            command=text,
            limit=limit,
            started=started,
            directory=directory,
        )


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_OUTPUT_CHARS",
    "MAX_TIMEOUT_SECONDS",
    "CommandResult",
    "TerminalService",
]
