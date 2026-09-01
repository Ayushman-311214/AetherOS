"""
Process service.

Sits between the tools and the psutil backend, and adds the two things the raw
interface leaves out: **name-based resolution** and **bounded waiting**.

Name resolution matters because a pid is not something a model knows. It knows
"Notepad". Resolving a name to pids happens here, and it deliberately returns
*every* match rather than picking one -- "chrome" is twenty processes, and quietly
terminating the first of them is not what anyone asked for. Tools that stop a
process therefore require an explicit pid, and offer name lookup as a separate
step.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.process_controller import ProcessController
from ...core.logging import get_logger

# Ceiling on any wait for a process, so a bad timeout cannot park a workflow.
MAX_WAIT_SECONDS = 300.0

_POLL_INTERVAL = 0.2

# Grace period between asking a process to exit and forcing it, when the caller
# asks for the escalating stop. Long enough for a normal application to close its
# windows, short enough not to look like a hang.
_TERMINATE_GRACE_SECONDS = 5.0


class ProcessService:
    """
    High-level process operations.
    """

    def __init__(
        self,
        controller: ProcessController,
    ) -> None:

        self._controller = controller
        self._logger = get_logger("desktop.process")

    # ==========================================================
    # Launching
    # ==========================================================

    async def start(
        self,
        command: str | list[str],
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> int:

        pid = self._controller.start(command, cwd=cwd, env=env)

        self._logger.bind(command=str(command), pid=pid).info("Started process.")

        return pid

    async def open_file(self, path: str | Path) -> int:

        return self._controller.open_file(path)

    async def open_url(self, url: str) -> int:

        return self._controller.open_url(url)

    # ==========================================================
    # Discovery
    # ==========================================================

    async def list_processes(self) -> list[dict[str, Any]]:

        return list(self._controller.list_processes())

    async def find_by_pid(self, pid: int) -> dict[str, Any] | None:

        return self._controller.find_by_pid(pid)

    async def find_by_name(self, name: str) -> list[dict[str, Any]]:

        return list(self._controller.find_by_name(name))

    async def resolve_one(self, name: str) -> dict[str, Any]:
        """
        Resolve a name to exactly one process, or explain why it could not.

        Refuses to guess when several match. An application with twenty processes
        has no "main" one that can be picked reliably -- the oldest is often a
        launcher stub, and the largest is whichever tab happens to be busy -- so
        the caller is told the pids and asked to choose. Guessing here would mean
        stopping something nobody selected.
        """

        matches = await self.find_by_name(name)

        if not matches:
            raise DesktopError(
                code="PROCESS_NOT_FOUND",
                message=f"No running process matches {name!r}.",
                hint="Call list_processes to see what is running.",
            )

        if len(matches) > 1:
            raise DesktopError(
                code="PROCESS_AMBIGUOUS",
                message=(
                    f"{len(matches)} processes match {name!r}: "
                    f"{[entry['pid'] for entry in matches[:12]]}"
                    f"{' ...' if len(matches) > 12 else ''}."
                ),
                hint=(
                    "Pass one pid explicitly. Nothing was changed. Applications "
                    "like browsers and editors run many processes, and stopping "
                    "an arbitrary one of them is rarely what is wanted."
                ),
            )

        return matches[0]

    # ==========================================================
    # State
    # ==========================================================

    async def exists(self, pid: int) -> bool:

        return self._controller.exists(pid)

    async def is_running(self, pid: int) -> bool:

        return self._controller.is_running(pid)

    async def info(self, pid: int) -> dict[str, Any]:

        return self._controller.info(pid)

    # ==========================================================
    # Stopping
    # ==========================================================

    async def terminate(self, pid: int) -> dict[str, Any]:
        """
        Ask a process to exit, then report whether it actually did.

        The report is read back from the system rather than assumed: a process can
        ignore termination, and a tool that says "terminated" about a process
        still holding a file lock sends the caller down a wrong path.
        """

        # Captured first: after the process exits, its name is unreadable, and an
        # audit line that says only "pid 8123 terminated" is not much of an audit.
        before = self._controller.find_by_pid(pid)
        name = (before or {}).get("name")

        self._controller.terminate(pid)

        exited = await self._await_exit(pid, timeout=_TERMINATE_GRACE_SECONDS)

        self._logger.bind(pid=pid, process=name, exited=exited).info(
            "Terminate requested."
        )

        return {
            "pid": pid,
            "name": name,
            "terminate_requested": True,
            "exited": exited,
            "still_running": not exited,
        }

    async def kill(self, pid: int) -> dict[str, Any]:
        """
        Stop a process immediately, then confirm it is gone.
        """

        before = self._controller.find_by_pid(pid)
        name = (before or {}).get("name")

        self._controller.kill(pid)

        exited = await self._await_exit(pid, timeout=_TERMINATE_GRACE_SECONDS)

        self._logger.bind(pid=pid, process=name, exited=exited).warning(
            "Process killed."
        )

        return {
            "pid": pid,
            "name": name,
            "killed": True,
            "exited": exited,
            "still_running": not exited,
        }

    async def stop(self, pid: int) -> dict[str, Any]:
        """
        Ask a process to exit, and force it only if asking did not work.

        The escalation is what a person does at a terminal, and doing it in one
        call means the common case does not need two round trips. It is still
        reported honestly: ``forced`` says whether the kill was needed.
        """

        outcome = await self.terminate(pid)

        if outcome["exited"]:
            return {**outcome, "forced": False}

        self._logger.bind(pid=pid).info(
            "Process ignored termination; escalating to kill."
        )

        forced = await self.kill(pid)

        return {**forced, "forced": True}

    async def restart(self, pid: int) -> dict[str, Any]:

        before = self._controller.find_by_pid(pid)

        new_pid = self._controller.restart(pid)

        self._logger.bind(
            old_pid=pid,
            new_pid=new_pid,
            process=(before or {}).get("name"),
        ).info("Restarted process.")

        return {
            "old_pid": pid,
            "new_pid": new_pid,
            "name": (before or {}).get("name"),
            "running": self._controller.is_running(new_pid),
        }

    # ==========================================================
    # Waiting
    # ==========================================================

    async def wait_for_exit(
        self,
        pid: int,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Wait until a process exits, bounded by ``timeout``.

        Polls rather than calling the backend's blocking ``wait``, because that
        would block the event loop for the whole duration -- stalling every other
        task in the process, including anything watching this one.
        """

        limit = self._bound(timeout)

        exited = await self._await_exit(pid, timeout=limit)

        if not exited:
            raise DesktopError(
                code="PROCESS_WAIT_TIMEOUT",
                message=f"pid {pid} was still running after {limit:g}s.",
                hint=(
                    "Raise the timeout, or stop the process explicitly with "
                    "stop_process."
                ),
            )

        return {"pid": pid, "exited": True, "waited_seconds": round(limit, 3)}

    async def wait_for_process(
        self,
        name: str,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Wait until at least one process with this name is running.

        Used after launching something: the launcher returns as soon as the
        process is created, which is before the application is ready for input.
        """

        limit = self._bound(timeout)

        deadline = time.perf_counter() + limit
        attempts = 0

        while True:

            attempts += 1

            matches = await self.find_by_name(name)

            if matches:
                return {
                    "name": name,
                    "running": True,
                    "count": len(matches),
                    "processes": matches,
                }

            if time.perf_counter() >= deadline:
                raise DesktopError(
                    code="PROCESS_WAIT_TIMEOUT",
                    message=(
                        f"No process named {name!r} appeared within {limit:g}s "
                        f"({attempts} check(s))."
                    ),
                    hint=(
                        "Check the executable name, or raise the timeout if the "
                        "application is slow to start."
                    ),
                )

            await asyncio.sleep(_POLL_INTERVAL)

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _bound(timeout: float) -> float:

        if timeout <= 0:
            raise DesktopError(
                code="PROCESS_TIMEOUT_INVALID",
                message=f"Timeout must be positive, got {timeout}.",
                hint="Pass a timeout in seconds, for example 30.",
            )

        return min(timeout, MAX_WAIT_SECONDS)

    async def _await_exit(
        self,
        pid: int,
        *,
        timeout: float,
    ) -> bool:
        """
        Poll until the process is gone, returning whether it went.

        Returns a bool rather than raising, because both callers -- terminate and
        kill -- need to *report* the outcome rather than fail on it.
        """

        deadline = time.perf_counter() + timeout

        while True:

            if not self._controller.is_running(pid):
                return True

            if time.perf_counter() >= deadline:
                return False

            await asyncio.sleep(_POLL_INTERVAL)


__all__ = ["MAX_WAIT_SECONDS", "ProcessService"]
