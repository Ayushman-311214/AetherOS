"""
psutil process backend.

Two safety rules are enforced here, in the backend, rather than only at the tool
boundary:

* **Critical system processes cannot be terminated.** Killing ``csrss.exe``,
  ``wininit.exe``, ``services.exe`` or ``lsass.exe`` does not close a program --
  it takes the machine down, immediately and without saving anything. The list is
  matched by name and by pid, and it is checked before the call rather than
  trusted to a caller who might reach this through a path that skipped the policy
  layer.
* **This process cannot terminate itself or its own parent.** An agent that kills
  its own interpreter mid-workflow leaves no log of why, and the request is
  almost always a resolution mistake -- a pid read from the wrong field -- rather
  than an intention.

Neither rule is a substitute for the policy gate in ``tools.py``; they are the
layer underneath it. A backend that will kill anything it is handed is one bad pid
away from an unbootable machine, and the policy layer only protects the callers
that go through it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.process_controller import ProcessController

try:
    import psutil

    _IMPORT_ERROR: Exception | None = None

except ImportError as exc:  # pragma: no cover - psutil is a declared dependency
    psutil = None  # type: ignore[assignment]

    _IMPORT_ERROR = exc


# Processes whose death takes Windows with it. Lower-cased for comparison.
#
# svchost is deliberately included even though many instances are non-fatal:
# distinguishing the survivable ones requires inspecting which services each host
# is running, and guessing wrong bluescreens the machine. A caller who genuinely
# needs to stop a service should stop the *service*, not its host process.
PROTECTED_PROCESS_NAMES = frozenset(
    {
        "system",
        "system idle process",
        "registry",
        "memory compression",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "lsm.exe",
        "svchost.exe",
        "dwm.exe",
        "fontdrvhost.exe",
        "sihost.exe",
        "ntoskrnl.exe",
    }
)

# The kernel and the System process. Neither is a normal target and neither is
# reliably reported by name on every Windows build, so they are blocked by number
# too.
PROTECTED_PIDS = frozenset({0, 4})


def _require() -> None:

    if _IMPORT_ERROR is not None:
        raise DesktopError(
            code="PROCESS_BACKEND_UNAVAILABLE",
            message="Process control requires psutil.",
            hint="Install psutil.",
            cause=_IMPORT_ERROR,
        )


class PsutilProcess(ProcessController):
    """
    Process control through psutil, with launching through ``subprocess``.

    No shell is involved in any launch. ``subprocess`` is called without
    ``shell=True`` throughout, so a command containing ``&&``, ``|`` or ``;``
    starts a program with those characters in its arguments rather than running
    several commands. Shell semantics, where they are genuinely wanted, live in
    ``terminal.py`` behind the ``ALLOW_SHELL`` capability gate.
    """

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _process(pid: int) -> Any:
        """
        Fetch a psutil handle, translating its errors into DesktopError.

        psutil's exceptions are informative but escape as an unrelated exception
        type through the tool layer, where they lose the hint that says what to do
        about them.
        """

        _require()

        try:
            return psutil.Process(pid)

        except psutil.NoSuchProcess as exc:
            raise DesktopError(
                code="PROCESS_NOT_FOUND",
                message=f"No process with pid {pid}.",
                hint="Call list_processes for current pids.",
                cause=exc,
            ) from exc

        except (ValueError, OverflowError) as exc:
            raise DesktopError(
                code="PROCESS_PID_INVALID",
                message=f"Not a usable pid: {pid!r}.",
                hint="Pass a positive integer pid.",
                cause=exc,
            ) from exc

    @classmethod
    def _guard(cls, pid: int, action: str) -> Any:
        """
        Refuse to act on a process that must not be stopped.

        Returns the psutil handle so the caller does not fetch it twice.
        """

        if pid in PROTECTED_PIDS:
            raise DesktopError(
                code="PROCESS_PROTECTED",
                message=f"Refusing to {action} pid {pid}: kernel-owned process.",
                hint="This process cannot be stopped. Nothing was changed.",
            )

        if pid == os.getpid():
            raise DesktopError(
                code="PROCESS_PROTECTED",
                message=(
                    f"Refusing to {action} pid {pid}: that is this process."
                ),
                hint=(
                    "Stopping the agent's own process would end the session "
                    "with no record of why. Check where the pid came from."
                ),
            )

        if pid == os.getppid():
            raise DesktopError(
                code="PROCESS_PROTECTED",
                message=(
                    f"Refusing to {action} pid {pid}: that is this process's "
                    "parent (the terminal or launcher running the agent)."
                ),
                hint="Check where the pid came from.",
            )

        handle = cls._process(pid)

        try:
            name = (handle.name() or "").strip().lower()

        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # A process whose name cannot be read is one the current user has no
            # rights over, which in practice means a system process. Refusing is
            # the safe reading of an unreadable target.
            raise DesktopError(
                code="PROCESS_PROTECTED",
                message=(
                    f"Refusing to {action} pid {pid}: its name cannot be read, "
                    "which means it is owned by another account or by the system."
                ),
                hint=(
                    "Run as the owning user if this is genuinely intended. "
                    "Nothing was changed."
                ),
            ) from None

        if name in PROTECTED_PROCESS_NAMES:
            raise DesktopError(
                code="PROCESS_PROTECTED",
                message=(
                    f"Refusing to {action} '{name}' (pid {pid}): stopping it "
                    "would crash Windows."
                ),
                hint=(
                    "Close the application through its own window, or pick a "
                    "different process. Nothing was changed."
                ),
            )

        return handle

    @staticmethod
    def _snapshot(handle: Any) -> dict[str, Any]:
        """
        Read one process into a plain dict.

        Fields that require privileges are filled with ``None`` on AccessDenied
        rather than dropped, so a caller can tell "not permitted to read" from
        "genuinely zero".
        """

        data: dict[str, Any] = {
            "pid": handle.pid,
            "name": None,
            "executable": None,
            "status": None,
            "cpu_percent": None,
            "memory_usage": None,
            "created_at": None,
            "username": None,
        }

        # Each field is attempted separately: on Windows, reading exe() for a
        # process owned by another user is denied while name() succeeds, and
        # losing the whole snapshot over one inaccessible field would make
        # list_processes useless for anything but this user's own programs.
        for key, reader in (
            ("name", handle.name),
            ("executable", handle.exe),
            ("status", handle.status),
            ("cpu_percent", handle.cpu_percent),
            ("created_at", handle.create_time),
            ("username", handle.username),
        ):
            try:
                data[key] = reader()

            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                pass

        try:
            data["memory_usage"] = handle.memory_info().rss

        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            pass

        return data

    # ==========================================================
    # Launching
    # ==========================================================

    def start(
        self,
        command: str | list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> int:
        """
        Start a program and return its pid.

        ``env``, when given, *extends* the current environment rather than
        replacing it. Replacing it strips PATH, SystemRoot and TEMP, which makes
        most Windows programs fail to start in ways that look nothing like a
        missing environment variable.
        """

        if not command:
            raise DesktopError(
                code="PROCESS_COMMAND_EMPTY",
                message="No command was given to start.",
                hint="Pass an executable path or name.",
            )

        working_directory = Path(cwd).expanduser() if cwd else None

        if working_directory is not None and not working_directory.is_dir():
            raise DesktopError(
                code="PROCESS_CWD_INVALID",
                message=f"Working directory does not exist: {working_directory}.",
                hint="Create the directory first, or omit cwd.",
            )

        environment = {**os.environ, **env} if env else None

        try:
            # No shell=True: shell metacharacters stay literal arguments instead
            # of becoming a second command.
            process = subprocess.Popen(
                command,
                cwd=str(working_directory) if working_directory else None,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )

        except FileNotFoundError as exc:
            raise DesktopError(
                code="PROCESS_NOT_LAUNCHABLE",
                message=f"Executable not found: {command!r}.",
                hint=(
                    "Use the full path, or a name that is on PATH. "
                    "Nothing was started."
                ),
                cause=exc,
            ) from exc

        except PermissionError as exc:
            raise DesktopError(
                code="PROCESS_NOT_LAUNCHABLE",
                message=f"Not permitted to run: {command!r}.",
                hint="Check the file's permissions. Nothing was started.",
                cause=exc,
            ) from exc

        except OSError as exc:
            raise DesktopError(
                code="PROCESS_NOT_LAUNCHABLE",
                message=f"Could not start {command!r}: {exc}.",
                hint="Nothing was started.",
                cause=exc,
            ) from exc

        return process.pid

    def open_file(
        self,
        path: str | Path,
    ) -> int:
        """
        Open a file with its registered application.

        Returns ``0``, which means "no pid is knowable" rather than "pid zero".
        The shell decides what handles the file, and it frequently hands it to an
        *already running* instance -- opening a second ``.txt`` while Notepad is
        open starts no new process at all. Any pid returned here would therefore
        be a guess, and a guessed pid used for a later ``terminate`` closes
        something the caller did not choose.

        To wait for the result, wait for the window instead of the process.
        """

        target = Path(path).expanduser()

        if not target.exists():
            raise DesktopError(
                code="PROCESS_TARGET_MISSING",
                message=f"Cannot open: {target} does not exist.",
                hint="Check the path. Nothing was opened.",
            )

        if not hasattr(os, "startfile"):
            raise DesktopError(
                code="PROCESS_OPEN_UNSUPPORTED",
                message="Opening files with the shell is Windows-only.",
                hint="Launch the application explicitly instead.",
            )

        try:
            os.startfile(str(target))  # type: ignore[attr-defined]

        except OSError as exc:
            raise DesktopError(
                code="PROCESS_OPEN_FAILED",
                message=f"The shell could not open {target}: {exc}.",
                hint=(
                    "There may be no application registered for this file type."
                ),
                cause=exc,
            ) from exc

        return 0

    def open_url(
        self,
        url: str,
    ) -> int:
        """
        Open a URL in the default browser.

        Returns ``0`` for the same reason as :meth:`open_file`: the browser is
        usually already running, and the new tab belongs to a process this call
        did not create.

        Only ``http``, ``https`` and ``mailto`` are accepted. The shell will
        happily act on a ``file:`` URL, which turns a URL-opening tool into an
        arbitrary-file-opening one, and on registered custom schemes, which can
        hand arbitrary arguments to a locally installed application.
        """

        candidate = url.strip()

        allowed = ("http://", "https://", "mailto:")

        if not candidate.lower().startswith(allowed):
            raise DesktopError(
                code="PROCESS_URL_INVALID",
                message=f"Refusing to open {candidate!r}.",
                hint=(
                    "Only http, https and mailto URLs are allowed. To open a "
                    "local file, use open_file. Nothing was opened."
                ),
            )

        if not hasattr(os, "startfile"):
            raise DesktopError(
                code="PROCESS_OPEN_UNSUPPORTED",
                message="Opening URLs with the shell is Windows-only.",
                hint="Use the browser tools instead.",
            )

        try:
            os.startfile(candidate)  # type: ignore[attr-defined]

        except OSError as exc:
            raise DesktopError(
                code="PROCESS_OPEN_FAILED",
                message=f"The shell could not open {candidate}: {exc}.",
                hint="Check that a default browser is configured.",
                cause=exc,
            ) from exc

        return 0

    # ==========================================================
    # Enumeration
    # ==========================================================

    def list_processes(self) -> list[Any]:
        """
        Every process the current user can see.

        ``process_iter`` with an explicit attribute list, because that batches the
        privileged reads and skips processes that vanish mid-iteration -- which
        happens constantly on a live desktop.
        """

        _require()

        found: list[dict[str, Any]] = []

        for handle in psutil.process_iter():

            try:
                found.append(self._snapshot(handle))

            except psutil.NoSuchProcess:
                # Exited between the listing and the read. Not part of the answer,
                # and not an error.
                continue

        return found

    def find_by_pid(
        self,
        pid: int,
    ) -> Any | None:

        _require()

        if not psutil.pid_exists(pid):
            return None

        try:
            return self._snapshot(psutil.Process(pid))

        except psutil.NoSuchProcess:
            return None

    def find_by_name(
        self,
        name: str,
    ) -> list[Any]:
        """
        Every process whose name matches, case-insensitively.

        Matched with and without the ``.exe`` suffix, since "notepad" and
        "notepad.exe" are the same request, and as a substring so "chrome" finds
        every renderer.
        """

        _require()

        needle = name.strip().lower()

        if not needle:
            raise DesktopError(
                code="PROCESS_NAME_EMPTY",
                message="A process name is required.",
                hint="Pass a name such as 'notepad'.",
            )

        stem = needle.removesuffix(".exe")

        matched: list[dict[str, Any]] = []

        for handle in psutil.process_iter():

            try:
                process_name = (handle.name() or "").lower()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if stem in process_name.removesuffix(".exe") or needle in process_name:

                try:
                    matched.append(self._snapshot(handle))

                except psutil.NoSuchProcess:
                    continue

        return matched

    # ==========================================================
    # Stopping
    # ==========================================================

    def terminate(
        self,
        pid: int,
    ) -> None:
        """
        Ask a process to exit.

        On Windows psutil's ``terminate`` maps to ``TerminateProcess``, which is
        not graceful in the Unix ``SIGTERM`` sense -- the process gets no chance
        to save. It is still the milder of the two options here, and closing a
        window with unsaved work should go through ``close_window`` instead.
        """

        handle = self._guard(pid, "terminate")

        try:
            handle.terminate()

        except psutil.NoSuchProcess:
            # Already gone. The requested end state holds, so this is a success
            # rather than an error -- but nothing here claims the *call* did it.
            return

        except psutil.AccessDenied as exc:
            raise DesktopError(
                code="PROCESS_ACCESS_DENIED",
                message=f"Not permitted to terminate pid {pid}.",
                hint=(
                    "The process belongs to another user or to the system. "
                    "Nothing was changed."
                ),
                cause=exc,
            ) from exc

    def kill(
        self,
        pid: int,
    ) -> None:
        """
        Stop a process immediately, with no opportunity to save.

        Use only after :meth:`terminate` has been given time and failed.
        """

        handle = self._guard(pid, "kill")

        try:
            handle.kill()

        except psutil.NoSuchProcess:
            return

        except psutil.AccessDenied as exc:
            raise DesktopError(
                code="PROCESS_ACCESS_DENIED",
                message=f"Not permitted to kill pid {pid}.",
                hint=(
                    "The process belongs to another user or to the system. "
                    "Nothing was changed."
                ),
                cause=exc,
            ) from exc

    def restart(
        self,
        pid: int,
    ) -> int:
        """
        Stop a process and start its executable again, returning the new pid.

        The command line is captured *before* stopping, because it is unreadable
        afterwards. If it cannot be read, this fails without stopping anything --
        a restart that terminates and then cannot relaunch is strictly worse than
        a refusal, since the caller ends up with neither the old process nor a new
        one.
        """

        handle = self._guard(pid, "restart")

        try:
            command = handle.cmdline() or []
            executable = handle.exe()
            working_directory = handle.cwd()

        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            raise DesktopError(
                code="PROCESS_RESTART_UNAVAILABLE",
                message=(
                    f"Cannot restart pid {pid}: its command line could not be "
                    "read, so it could not be started again."
                ),
                hint=(
                    "Nothing was stopped. Launch the application explicitly "
                    "with launch_application instead."
                ),
                cause=exc,
            ) from exc

        except OSError as exc:
            raise DesktopError(
                code="PROCESS_RESTART_UNAVAILABLE",
                message=f"Cannot restart pid {pid}: {exc}.",
                hint="Nothing was stopped.",
                cause=exc,
            ) from exc

        launch: str | list[str] = command or executable

        self.terminate(pid)

        try:
            handle.wait(timeout=10)

        except psutil.TimeoutExpired:
            self.kill(pid)

            try:
                handle.wait(timeout=5)

            except psutil.TimeoutExpired as exc:
                raise DesktopError(
                    code="PROCESS_RESTART_FAILED",
                    message=(
                        f"pid {pid} did not exit after terminate and kill, so it "
                        "was not restarted."
                    ),
                    hint=(
                        "The original process may still be running. Check with "
                        "get_process_info before retrying."
                    ),
                    cause=exc,
                ) from exc

        return self.start(
            launch,
            cwd=working_directory if Path(working_directory).is_dir() else None,
        )

    # ==========================================================
    # State
    # ==========================================================

    def exists(
        self,
        pid: int,
    ) -> bool:

        _require()

        try:
            return bool(psutil.pid_exists(pid))

        except (ValueError, OverflowError):
            return False

    def is_running(
        self,
        pid: int,
    ) -> bool:
        """
        Whether a process exists *and* has not become a zombie.

        Distinct from :meth:`exists` because a terminated child whose exit status
        nobody collected still occupies its pid. Treating that as running makes a
        wait-for-exit loop never finish.
        """

        _require()

        try:
            handle = psutil.Process(pid)

            return handle.is_running() and handle.status() != psutil.STATUS_ZOMBIE

        except (psutil.NoSuchProcess, ValueError, OverflowError):
            return False

        except psutil.AccessDenied:
            # Visible but not inspectable: it exists, which is what was asked.
            return True

    def wait(
        self,
        pid: int,
        timeout: float | None = None,
    ) -> None:
        """
        Block until a process exits.

        ``timeout=None`` waits indefinitely, which is why the service above never
        passes it: an unbounded wait inside an automation step is a hang with no
        diagnosis. Kept on the signature because it is the interface's.
        """

        handle = self._process(pid)

        try:
            handle.wait(timeout=timeout)

        except psutil.TimeoutExpired as exc:
            raise DesktopError(
                code="PROCESS_WAIT_TIMEOUT",
                message=(
                    f"pid {pid} was still running after {timeout}s."
                ),
                hint="Raise the timeout, or stop the process explicitly.",
                cause=exc,
            ) from exc

        except psutil.NoSuchProcess:
            # Already exited. The wait's purpose is satisfied.
            return

    def info(
        self,
        pid: int,
    ) -> dict[str, Any]:
        """
        Everything readable about one process.

        ``cpu_percent`` from a single reading is ``0.0`` on the first call for a
        process -- psutil measures it as a delta between two samples. Reported as
        given rather than smoothed, because inventing a plausible number for a
        measurement that has not been taken is the kind of fabrication this
        codebase is meant not to do.
        """

        return self._snapshot(self._process(pid))


__all__ = [
    "PROTECTED_PIDS",
    "PROTECTED_PROCESS_NAMES",
    "PsutilProcess",
]
