"""
Application service.

An application is not a process, and conflating the two is where desktop
automation quietly goes wrong:

* ``calc.exe`` is a stub. It starts, hands off to a packaged app running under a
  different pid, and exits. The pid the launcher returns is dead within a second,
  and a tool that reports "running: false" from it is describing the stub, not
  Calculator.
* ``chrome.exe`` with an existing window creates a tab in the *already running*
  process and exits. Again the returned pid is meaningless, and terminating it
  achieves nothing.
* One application is routinely many processes. "Is Chrome running" has a sensible
  answer; "which pid is Chrome" does not.

So this service works in terms of *names* and reports pids as evidence rather than
as identity. Launching optionally waits for a window rather than for the process,
because a window is what the next automation step needs, and closing goes through
windows first -- which lets the application prompt about unsaved work -- before
anything touches the process.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger

from ..process.controller import ProcessService
from ..window.controller import WindowService
from ..window.models import WindowInfo

from .resolver import is_uri, resolve_application

# Ceiling on any wait here, matching the window subsystem's.
MAX_WAIT_SECONDS = 120.0

_POLL_INTERVAL = 0.2

# Shell URIs this service will hand to Explorer. Only Windows' own settings and
# store schemes, because a URI is not a program: a registered custom scheme can
# pass arbitrary arguments to whatever locally installed application claimed it,
# so "launch anything that looks like a URI" is an arbitrary-execution path
# wearing a launcher's clothes. http/https/mailto go through open_url instead,
# which is narrower still.
_SHELL_URI_PREFIXES = ("ms-settings:", "ms-windows-store:", "ms-clock:")

_BROWSER_URI_PREFIXES = ("http://", "https://", "mailto:")


class ApplicationService:
    """
    Launch, inspect and close applications by name.
    """

    def __init__(
        self,
        processes: ProcessService,
        windows: WindowService,
    ) -> None:

        self._processes = processes
        self._windows = windows
        self._logger = get_logger("desktop.application")

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _executable_name(target: str) -> str:
        """
        The executable's filename, which is what psutil and Win32 report.
        """

        return Path(target).name or target

    @staticmethod
    def _bound(timeout: float) -> float:

        if timeout <= 0:
            raise DesktopError(
                code="APPLICATION_TIMEOUT_INVALID",
                message=f"Timeout must be positive, got {timeout}.",
                hint="Pass a timeout in seconds, for example 15.",
            )

        return min(timeout, MAX_WAIT_SECONDS)

    async def _windows_for(self, executable: str) -> list[WindowInfo]:
        """
        Windows owned by a process with this executable name.

        Matched on the process name rather than on a pid, for the reasons in the
        module docstring: the pid a launch returns frequently belongs to a stub
        that has already exited.
        """

        return await self._windows.search(process=executable)

    # ==========================================================
    # Launching
    # ==========================================================

    async def launch(
        self,
        name: str,
        *,
        args: list[str] | None = None,
        cwd: str | Path | None = None,
        wait_for_window: bool = True,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """
        Start an application, optionally waiting until it has a window.

        The window wait is on by default because it is what makes the result
        usable: without it, the next step types into whatever had focus before.
        When the wait times out the launch is still reported as having happened --
        with ``window`` null and ``window_appeared`` false -- because the
        application may simply be slow, and claiming the launch failed would be
        wrong.
        """

        target = resolve_application(name)

        if is_uri(target):
            return await self._launch_uri(name, target)

        executable = self._executable_name(target)

        # Captured before launching, so "did a new window appear" can be answered
        # by difference rather than by assuming there were none.
        before = {window.hwnd for window in await self._windows_for(executable)}

        pid = await self._processes.start(
            [target, *args] if args else target,
            cwd=cwd,
        )

        self._logger.bind(
            application=name,
            target=target,
            pid=pid,
        ).info("Launched application.")

        result: dict[str, Any] = {
            "requested": name,
            "target": target,
            "kind": "process",
            "pid": pid,
            "launched": True,
            # Reported plainly, and explained: a stub launcher exiting instantly
            # is normal and does not mean the launch failed.
            "launcher_still_running": await self._processes.is_running(pid),
        }

        if not wait_for_window:
            return result

        window = await self._wait_for_new_window(
            executable=executable,
            excluding=before,
            timeout=self._bound(timeout),
        )

        result["window_appeared"] = window is not None
        result["window"] = window.to_dict() if window else None

        if window is None:
            result["note"] = (
                f"No new {executable} window appeared within {timeout:g}s. The "
                "application may still be starting, or may run without a window."
            )

        return result

    async def _launch_uri(self, name: str, target: str) -> dict[str, Any]:
        """
        Open a shell URI such as ``ms-settings:``.

        Restricted to the two prefix sets above, and everything else is refused
        rather than passed through. Explorer is used for the ``ms-`` schemes
        because the shell -- not this process -- decides what handles them; that
        is also exactly why the set is closed rather than open.
        """

        lowered = target.lower()

        if lowered.startswith(_BROWSER_URI_PREFIXES):

            await self._processes.open_url(target)

        elif lowered.startswith(_SHELL_URI_PREFIXES):

            # Through Explorer, which resolves the scheme. Explorer exits
            # immediately, so its pid says nothing about what opened.
            await self._processes.start(["explorer.exe", target])

        else:
            raise DesktopError(
                code="APPLICATION_URI_REFUSED",
                message=f"Refusing to open the URI {target!r}.",
                hint=(
                    "Only http, https, mailto and Windows ms-settings style URIs "
                    "are allowed, because a registered custom scheme can pass "
                    "arbitrary arguments to a local application. To open a file, "
                    "use the file tools. Nothing was launched."
                ),
            )

        self._logger.bind(application=name, target=target).info("Opened URI.")

        return {
            "requested": name,
            "target": target,
            "kind": "uri",
            # The shell opened it; no pid is knowable, and none is invented.
            "pid": None,
            "launched": True,
            "note": (
                "Opened through the shell. No pid is available, because the "
                "handler was probably already running."
            ),
        }

    async def launch_url(self, url: str) -> dict[str, Any]:
        """
        Open a URL in the default browser.
        """

        await self._processes.open_url(url)

        return {
            "url": url,
            "opened": True,
            # The browser was probably already running, so the new tab belongs to
            # a process this call did not create.
            "pid": None,
        }

    async def _wait_for_new_window(
        self,
        *,
        executable: str,
        excluding: set[int],
        timeout: float,
    ) -> WindowInfo | None:
        """
        Poll for a window of this executable that was not open before.

        Returns ``None`` on timeout rather than raising: the caller reports the
        outcome, and a slow application is not a failed launch.
        """

        deadline = time.perf_counter() + timeout

        while True:

            for window in await self._windows_for(executable):

                if window.hwnd not in excluding:
                    return window

            if time.perf_counter() >= deadline:
                return None

            await asyncio.sleep(_POLL_INTERVAL)

    # ==========================================================
    # State
    # ==========================================================

    async def is_running(self, name: str) -> dict[str, Any]:
        """
        Whether an application is running, by executable name.
        """

        executable = self._executable_name(resolve_application(name))

        matches = await self._processes.find_by_name(executable)

        return {
            "application": name,
            "executable": executable,
            "running": bool(matches),
            "process_count": len(matches),
            "pids": [entry["pid"] for entry in matches],
        }

    async def info(self, name: str) -> dict[str, Any]:
        """
        Processes and windows belonging to an application.

        Both, because either alone is misleading: a browser with twelve processes
        and one window is one application, and a background service with one
        process and no window is running but not visible.
        """

        executable = self._executable_name(resolve_application(name))

        processes = await self._processes.find_by_name(executable)
        windows = await self._windows_for(executable)

        return {
            "application": name,
            "executable": executable,
            "running": bool(processes),
            "process_count": len(processes),
            "processes": processes,
            "window_count": len(windows),
            "windows": [window.to_dict() for window in windows],
            "total_memory_usage": sum(
                entry.get("memory_usage") or 0 for entry in processes
            ),
        }

    async def wait_for(
        self,
        name: str,
        *,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """
        Wait until an application is running.
        """

        executable = self._executable_name(resolve_application(name))

        limit = self._bound(timeout)

        deadline = time.perf_counter() + limit
        attempts = 0

        while True:

            attempts += 1

            matches = await self._processes.find_by_name(executable)

            if matches:
                return {
                    "application": name,
                    "executable": executable,
                    "running": True,
                    "process_count": len(matches),
                    "pids": [entry["pid"] for entry in matches],
                }

            if time.perf_counter() >= deadline:
                raise DesktopError(
                    code="APPLICATION_WAIT_TIMEOUT",
                    message=(
                        f"{executable} was not running after {limit:g}s "
                        f"({attempts} check(s))."
                    ),
                    hint=(
                        "Check the application name, or raise the timeout if it "
                        "is slow to start."
                    ),
                )

            await asyncio.sleep(_POLL_INTERVAL)

    # ==========================================================
    # Closing
    # ==========================================================

    async def close(
        self,
        name: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """
        Ask an application to close through its windows.

        Windows first, deliberately. Closing a window lets the application run its
        own shutdown -- flush buffers, prompt about unsaved work, save session
        state. Terminating the process does none of that. The result reports how
        many windows are still open, and an application showing a save prompt is
        *correctly* still open, not a failure.

        Nothing here escalates to the process. That is :meth:`terminate`, which is
        a separate, higher-risk tool.
        """

        executable = self._executable_name(resolve_application(name))

        windows = await self._windows_for(executable)

        if not windows:

            still_running = await self._processes.find_by_name(executable)

            return {
                "application": name,
                "executable": executable,
                "windows_closed": 0,
                "windows_remaining": 0,
                "still_running": bool(still_running),
                "note": (
                    "No windows found."
                    + (
                        " The application is running without a visible window; "
                        "use terminate_application to stop it."
                        if still_running
                        else " The application does not appear to be running."
                    )
                ),
            }

        requested = [window.hwnd for window in windows]

        for window in windows:
            await self._windows.close(window)

        remaining = await self._wait_for_windows_to_close(
            executable=executable,
            watching=set(requested),
            timeout=self._bound(timeout),
        )

        self._logger.bind(
            application=name,
            requested=len(requested),
            remaining=len(remaining),
        ).info("Requested application close.")

        return {
            "application": name,
            "executable": executable,
            "windows_closed": len(requested) - len(remaining),
            "windows_remaining": len(remaining),
            "remaining_titles": remaining,
            "still_running": bool(await self._processes.find_by_name(executable)),
            "note": (
                None
                if not remaining
                else (
                    "Some windows are still open. This usually means an unsaved-"
                    "changes prompt is waiting; handle it before continuing."
                )
            ),
        }

    async def _wait_for_windows_to_close(
        self,
        *,
        executable: str,
        watching: set[int],
        timeout: float,
    ) -> list[str]:
        """
        Poll until the watched windows are gone, returning the titles of any left.
        """

        deadline = time.perf_counter() + timeout

        while True:

            open_now = [
                window
                for window in await self._windows_for(executable)
                if window.hwnd in watching
            ]

            if not open_now:
                return []

            if time.perf_counter() >= deadline:
                return [window.title for window in open_now]

            await asyncio.sleep(_POLL_INTERVAL)

    async def terminate(
        self,
        name: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Stop every process belonging to an application.

        Unsaved work is lost -- there is no prompt and no shutdown sequence. The
        per-process outcome is reported individually, because a partial result is
        the common one: some processes are protected, and reporting an overall
        "stopped" would hide that.
        """

        executable = self._executable_name(resolve_application(name))

        matches = await self._processes.find_by_name(executable)

        if not matches:
            raise DesktopError(
                code="APPLICATION_NOT_RUNNING",
                message=f"{executable} is not running.",
                hint="Nothing was changed.",
            )

        outcomes: list[dict[str, Any]] = []

        for entry in matches:

            pid = entry["pid"]

            try:
                outcomes.append(
                    await (
                        self._processes.kill(pid)
                        if force
                        else self._processes.stop(pid)
                    )
                )

            except DesktopError as exc:
                # Recorded rather than raised: one protected process should not
                # hide what happened to the other eleven.
                outcomes.append(
                    {
                        "pid": pid,
                        "name": entry.get("name"),
                        "exited": False,
                        "still_running": True,
                        "error": exc.message,
                        "error_code": exc.code,
                    }
                )

        stopped = [entry for entry in outcomes if entry.get("exited")]

        self._logger.bind(
            application=name,
            targeted=len(matches),
            stopped=len(stopped),
            forced=force,
        ).warning("Terminated application.")

        return {
            "application": name,
            "executable": executable,
            "processes_targeted": len(matches),
            "processes_stopped": len(stopped),
            "fully_stopped": len(stopped) == len(matches),
            "results": outcomes,
            "still_running": bool(
                await self._processes.find_by_name(executable)
            ),
        }

    async def restart(
        self,
        name: str,
        *,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """
        Stop an application and start it again.

        Resolved to a launch target *before* stopping anything, so a name that
        cannot be relaunched fails without leaving the application closed.
        """

        target = resolve_application(name)
        executable = self._executable_name(target)

        stopped = (
            await self.terminate(name)
            if await self._processes.find_by_name(executable)
            else {"processes_targeted": 0, "processes_stopped": 0}
        )

        launched = await self.launch(
            target,
            wait_for_window=True,
            timeout=timeout,
        )

        return {
            "application": name,
            "executable": executable,
            "stopped": stopped,
            "launched": launched,
        }


__all__ = ["MAX_WAIT_SECONDS", "ApplicationService"]
