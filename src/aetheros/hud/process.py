from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..core.logging.logging import get_logger
from .config import HUDConfig
from .pipe import PipeReader, PipeWriter
from .protocol import Message, drain, quit_message

#: How long to wait for the overlay to close politely before killing
# it. Generous enough for Qt to tear a window down, short enough that
# shutting AetherOS down never feels like it hung.
_GRACE_SECONDS = 4.0

#: Module the child runs. Also usable directly:
#   python -m aetheros.hud.app --demo
_CHILD_MODULE = "aetheros.hud.app"


class HUDProcess:
    """
    The overlay, running as a separate process.

    Separate rather than a thread for three reasons: Qt insists on
    owning the thread it was created on and the CLI already owns the
    main one; a rendering crash must not be able to take AetherOS with
    it; and the overlay has to be startable on its own.

    A plain subprocess rather than multiprocessing.spawn, because spawn
    re-imports the parent's __main__ in the child — which here would
    drag the entire AetherOS bootstrap chain, and its model loading,
    into a process whose only job is to draw a circle.
    """

    def __init__(
        self,
        config: HUDConfig,
        *,
        python: str | None = None,
        module: str = _CHILD_MODULE,
    ) -> None:

        self._config = config
        self._python = python or sys.executable
        self._module = module

        self._logger = get_logger("hud.process")

        self._process: subprocess.Popen[str] | None = None
        self._reader: PipeReader | None = None
        self._writer: PipeWriter | None = None

        #: Set once the child reports itself ready to draw.
        self._ready = False

        #: The child's own pid, as it reported it. Not always the pid we
        #: launched: a Windows venv python.exe is a launcher that runs
        #: the real interpreter as a child, so this is the process that
        #: actually owns the window.
        self._child_pid: int | None = None

        #: Kept so status still reports how the overlay ended after the
        #: Popen handle has been released.
        self._exit_code: int | None = None

        #: Why the last start attempt failed, if it did.
        self._failure: str | None = None

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_alive(self) -> bool:

        process = self._process

        return process is not None and process.poll() is None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def pid(self) -> int | None:
        """
        The process that owns the window, as best we know it.
        """

        if self._child_pid is not None:
            return self._child_pid

        process = self._process

        return process.pid if process is not None else None

    @property
    def exit_code(self) -> int | None:

        process = self._process

        if process is not None:
            return process.poll()

        return self._exit_code

    @property
    def failure(self) -> str | None:
        return self._failure

    def mark_ready(self, pid: int | None = None) -> None:
        """
        Record that the child has reported MSG_READY.
        """

        self._ready = True

        if pid is not None:
            self._child_pid = pid

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def start(self) -> bool:
        """
        Launch the overlay. Returns whether it started.

        Failure is reported rather than raised: a missing Qt runtime
        must leave AetherOS entirely usable.
        """

        if self.is_alive:
            return True

        self._failure = None
        self._ready = False
        self._exit_code = None
        self._child_pid = None

        command = [
            self._python,
            "-m",
            self._module,
            "--ipc",
        ]

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                # Qt writes plugin diagnostics to stderr. Keeping it
                # separate means it can never be mistaken for a message
                # on stdout.
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=self._working_directory(),
                env=self._child_environment(),
                creationflags=self._creation_flags(),
            )

        except Exception as exc:

            self._failure = str(exc)

            self._logger.warning(f"Could not start the HUD process: {exc}")

            return False

        self._process = process

        if process.stdin is None or process.stdout is None:

            self._failure = "The HUD process has no usable pipes."

            self.stop()

            return False

        self._writer = PipeWriter(
            process.stdin,
            on_error=self._logger.warning,
        )

        self._reader = PipeReader(process.stdout)
        self._reader.start()

        self._logger.info(f"HUD process started (pid={process.pid}).")

        # The child reads its configuration from the first message
        # rather than the command line, so a live reconfiguration uses
        # exactly the same path as the initial one.
        self.send(
            {
                "type": "config",
                "config": self._config.to_dict(),
            }
        )

        return True

    def stop(self, timeout: float = _GRACE_SECONDS) -> None:
        """
        Shut the overlay down and release every handle.

        Escalates: ask, then terminate, then kill. Returns only once
        the process is gone, so no overlay outlives AetherOS.
        """

        process = self._process

        if process is None:
            self._teardown_pipes()

            return

        if process.poll() is None:

            # 1. Ask politely.
            self.send(quit_message())

            # Then close our end of its input. If the quit message were
            # ever missed, the resulting EOF trips the child's orphan
            # guard, so shutdown does not depend on a single message
            # arriving.
            writer = self._writer

            if writer is not None:
                writer.close()

            try:
                process.wait(timeout=timeout)

            except subprocess.TimeoutExpired:

                self._logger.warning(
                    "HUD process did not exit; terminating."
                )

                self._force_stop(process)

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while waiting for the HUD."
                )

        # Only now: closing the pipes earlier would take away the
        # channel the quit message travels on.
        self._teardown_pipes()

        code = process.poll()

        self._exit_code = code
        self._process = None
        self._ready = False
        self._child_pid = None

        self._logger.info(f"HUD process stopped (exit={code}).")

    def _force_stop(self, process: subprocess.Popen[str]) -> None:
        """
        Kill the overlay and anything it started.

        Not just process.terminate(): on Windows a venv's python.exe is
        a small launcher that runs the real interpreter as a *child*, so
        terminating what we launched can leave the actual window alive
        and orphaned. taskkill /T covers the tree.
        """

        if sys.platform.startswith("win"):

            try:
                subprocess.run(
                    [
                        "taskkill",
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                    ],
                    capture_output=True,
                    timeout=5.0,
                    check=False,
                )

            except Exception:
                self._logger.opt(exception=True).debug(
                    "taskkill was unavailable; falling back."
                )

        for step in (process.terminate, process.kill):

            if process.poll() is not None:
                return

            try:
                step()
                process.wait(timeout=2.0)

            except Exception:
                self._logger.opt(exception=True).debug(
                    f"Ignoring error during HUD {step.__name__}."
                )

    def _teardown_pipes(self) -> None:
        """
        Close both channels and join the reader thread.
        """

        writer = self._writer
        self._writer = None

        if writer is not None:
            writer.close()

        reader = self._reader
        self._reader = None

        if reader is not None:
            reader.stop()

    # ==========================================================
    # Messaging
    # ==========================================================

    def send(self, message: Message) -> bool:
        """
        Send one message to the overlay.

        Returns whether it was handed to the pipe. A False here means
        the child is gone, which callers treat as "stop sending", not
        as an error.
        """

        writer = self._writer

        if writer is None or writer.broken:
            return False

        writer.put(message)

        return not writer.broken

    def poll(self) -> list[Message]:
        """
        Collect whatever the overlay has reported since last time.
        """

        reader = self._reader

        if reader is None:
            return []

        return drain(reader)

    @property
    def stream_closed(self) -> bool:
        """
        Whether the child's output stream has ended.

        Reaches the parent slightly before the exit code does, so this
        is the earliest reliable sign the overlay has gone.
        """

        reader = self._reader

        return reader is not None and reader.closed

    # ==========================================================
    # Child environment
    # ==========================================================

    def _working_directory(self) -> str | None:
        """
        Run the child from the project root.

        Keeps `.env` discovery and relative paths behaving the same in
        the child as in the parent.
        """

        try:
            # .../src/aetheros/hud/process.py -> project root
            return str(Path(__file__).resolve().parents[3])

        except Exception:
            return None

    def _child_environment(self) -> dict[str, str]:
        """
        The child's environment.

        Inherits everything, then guarantees the package is importable
        even when AetherOS was launched from a script rather than an
        installed entry point.
        """

        environment = dict(os.environ)

        try:
            source_root = str(Path(__file__).resolve().parents[2])

        except Exception:
            return environment

        existing = environment.get("PYTHONPATH", "")

        parts = [
            part
            for part in existing.split(os.pathsep)
            if part
        ]

        if source_root not in parts:
            parts.insert(0, source_root)

        environment["PYTHONPATH"] = os.pathsep.join(parts)

        # Unbuffered, so a message written by the child is readable
        # immediately rather than sitting in a pipe buffer.
        environment["PYTHONUNBUFFERED"] = "1"

        return environment

    def _creation_flags(self) -> int:
        """
        Windows process-creation flags.

        Detaching from the console keeps a Ctrl-C in the CLI from also
        interrupting the overlay: shutdown should run through the
        normal path, not race a signal.
        """

        if not sys.platform.startswith("win"):
            return 0

        return int(
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ) | int(
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )


__all__ = ["HUDProcess"]
