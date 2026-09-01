"""
Window service.

Adds the one thing the raw :class:`WindowController` interface leaves to callers:
a single way to say *which* window. Every tool in this subsystem takes ``hwnd``,
``title``, ``pid``, ``process`` or ``active`` and routes through
:meth:`WindowService.resolve`, so the model can name a window however it happens
to know it and cannot end up with a tool that only accepts titles.

That matters because title-only addressing is the standard way desktop automation
goes wrong. Three Explorer windows share a title; a browser's changes as pages
load; a document window's changes the moment it is edited. ``hwnd`` is exact,
``pid`` narrows to one application, and ``active`` needs no name at all.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.window_controller import WindowController
from ...core.logging import get_logger

from .models import WindowInfo

# Ceiling on any wait, so a bad timeout cannot park a workflow forever. Chosen to
# comfortably cover a cold application launch while still being a bound.
MAX_WAIT_SECONDS = 120.0

# Gap between polls while waiting for a window. Short enough that a wait resolves
# promptly, long enough that enumerating every top-level window ten times a
# second is not the reason the machine feels slow.
_POLL_INTERVAL = 0.15


class WindowService:
    """
    High-level window service.

    Backed by a :class:`WindowController`; holds no window state of its own,
    because window state belongs to the desktop and any cached copy of it is
    wrong the moment the user touches the mouse.
    """

    def __init__(
        self,
        controller: WindowController,
    ) -> None:

        self._controller = controller
        self._logger = get_logger("desktop.window")

    # ==========================================================
    # Target resolution
    # ==========================================================

    async def resolve(
        self,
        *,
        hwnd: int | None = None,
        title: str | None = None,
        pid: int | None = None,
        process: str | None = None,
        active: bool = False,
        exact: bool = False,
    ) -> WindowInfo:
        """
        Identify exactly one window.

        Selectors are tried most-specific first -- ``hwnd``, then ``active``, then
        ``pid``/``process``, then ``title`` -- so supplying several narrows rather
        than conflicts. ``pid`` and ``title`` combine, which is how a caller picks
        one of several same-titled windows belonging to one application.

        Raises rather than returning ``None``: every caller of this is about to
        act on the window, and "no window" is a failure at that point, not a
        result. Tools that want to *ask* whether a window exists call
        :meth:`find` or :meth:`exists`.
        """

        if hwnd is not None:

            if not self._controller.exists(hwnd):
                raise DesktopError(
                    code="WINDOW_NOT_FOUND",
                    message=f"No window with handle {hwnd}.",
                    hint="Call list_windows for current handles.",
                )

            return self._describe(hwnd)

        if active:

            window = self._controller.active()

            if window is None:
                raise DesktopError(
                    code="WINDOW_NOT_FOUND",
                    message="No window currently has focus.",
                    hint=(
                        "This happens during window switches and while the lock "
                        "screen is up. Retry, or name a window explicitly."
                    ),
                )

            return window

        if pid is None and process is None and not title:
            raise DesktopError(
                code="WINDOW_SELECTOR_MISSING",
                message="No window was specified.",
                hint=(
                    "Pass hwnd, title, pid or process, or set active=true for "
                    "the focused window."
                ),
            )

        matches = await self.search(
            title=title,
            pid=pid,
            process=process,
            exact=exact,
        )

        if not matches:
            raise DesktopError(
                code="WINDOW_NOT_FOUND",
                message=(
                    "No window matched "
                    f"{self._describe_selector(title, pid, process)}."
                ),
                hint="Call list_windows to see what is open.",
            )

        if len(matches) > 1:
            # Not an error: the frontmost match is nearly always the intended
            # one, since EnumWindows walks Z-order. Logged so an ambiguous
            # selector is visible in the audit trail rather than silent.
            self._logger.bind(
                selector=self._describe_selector(title, pid, process),
                matches=len(matches),
                chosen=matches[0].hwnd,
            ).info("Ambiguous window selector; using the frontmost match.")

        return matches[0]

    async def search(
        self,
        *,
        title: str | None = None,
        pid: int | None = None,
        process: str | None = None,
        exact: bool = False,
    ) -> list[WindowInfo]:
        """
        Every window matching the given selectors, frontmost first.

        Selectors combine with AND. Text comparison is case-insensitive, and
        substring unless ``exact`` -- real titles carry decoration the caller
        cannot predict ("report.xlsx - Excel"), so demanding an exact match by
        default would make the common case unusable.
        """

        needle = (title or "").strip().lower()
        process_needle = (process or "").strip().lower()

        results: list[WindowInfo] = []

        for window in self._controller.list_windows():

            if needle:

                haystack = window.title.lower()

                if (haystack != needle) if exact else (needle not in haystack):
                    continue

            if pid is not None and window.pid != pid:
                continue

            if process_needle:

                # Matched against the executable name, with or without the
                # extension, because "notepad" and "notepad.exe" are the same
                # request.
                name = window.process_name.lower()

                if process_needle not in name:
                    continue

            results.append(window)

        return results

    # ==========================================================
    # Enumeration
    # ==========================================================

    async def list_windows(self) -> list[WindowInfo]:
        """
        Every visible titled top-level window, frontmost first.
        """

        return list(self._controller.list_windows())

    async def find(
        self,
        title: str,
        exact: bool = False,
    ) -> WindowInfo | None:
        """
        The frontmost window matching ``title``, or ``None``.
        """

        return self._controller.find(title=title, exact=exact)

    async def active(self) -> WindowInfo | None:
        """
        The focused window, or ``None`` when nothing has focus.
        """

        return self._controller.active()

    async def exists(
        self,
        window: Any,
    ) -> bool:

        return self._controller.exists(window)

    # ==========================================================
    # Focus
    # ==========================================================

    async def activate(
        self,
        window: Any,
    ) -> None:
        """
        Focus a window. Raises if focus did not actually land on it.
        """

        hwnd = self._handle(window)

        self._logger.bind(hwnd=hwnd).debug("Activating window.")

        self._controller.activate(hwnd)

    async def is_active(
        self,
        window: Any,
    ) -> bool:

        return self._controller.is_active(self._handle(window))

    # ==========================================================
    # State
    # ==========================================================

    async def minimize(self, window: Any) -> None:

        self._controller.minimize(self._handle(window))

    async def maximize(self, window: Any) -> None:

        self._controller.maximize(self._handle(window))

    async def restore(self, window: Any) -> None:

        self._controller.restore(self._handle(window))

    async def close(self, window: Any) -> None:
        """
        Ask a window to close.

        A request, not a guarantee -- the application may prompt about unsaved
        work and stay open. Verify with :meth:`exists`.
        """

        hwnd = self._handle(window)

        self._logger.bind(hwnd=hwnd).info("Requesting window close.")

        self._controller.close(hwnd)

    async def state(self, window: Any) -> str:
        """
        ``"normal"``, ``"minimized"`` or ``"maximized"``.
        """

        return self._describe(self._handle(window)).state

    # ==========================================================
    # Geometry
    # ==========================================================

    async def bounds(self, window: Any) -> WindowInfo:
        """
        A full snapshot, which carries the bounds along with everything else.
        """

        return self._describe(self._handle(window))

    async def move(
        self,
        window: Any,
        x: int,
        y: int,
    ) -> None:

        self._controller.move(self._handle(window), x, y)

    async def resize(
        self,
        window: Any,
        width: int,
        height: int,
    ) -> None:

        self._controller.resize(self._handle(window), width, height)

    # ==========================================================
    # Waiting
    # ==========================================================

    async def wait_for_window(
        self,
        *,
        title: str | None = None,
        pid: int | None = None,
        process: str | None = None,
        timeout: float = 10.0,
        exact: bool = False,
    ) -> WindowInfo:
        """
        Poll until a matching window appears, or the timeout expires.

        Polling rather than a Win32 event hook: a hook needs a message loop on a
        dedicated thread, and this runs inside an asyncio task. The cost is
        latency bounded by one poll interval, which is invisible next to the time
        an application takes to draw its first window.
        """

        return await self._wait(
            description=self._describe_selector(title, pid, process),
            timeout=timeout,
            probe=lambda: self._first(
                title=title,
                pid=pid,
                process=process,
                exact=exact,
            ),
        )

    async def wait_until_active(
        self,
        *,
        hwnd: int | None = None,
        title: str | None = None,
        pid: int | None = None,
        process: str | None = None,
        timeout: float = 10.0,
        exact: bool = False,
    ) -> WindowInfo:
        """
        Poll until a matching window holds focus, or the timeout expires.

        Distinct from :meth:`wait_for_window` because existing and being focused
        are different states, and typing into a window that exists but is not
        focused sends the keystrokes somewhere else.
        """

        def probe() -> WindowInfo | None:

            current = self._controller.active()

            if current is None:
                return None

            if hwnd is not None:
                return current if current.hwnd == hwnd else None

            candidates = {
                window.hwnd
                for window in self._match(
                    title=title,
                    pid=pid,
                    process=process,
                    exact=exact,
                )
            }

            if not candidates and title is None and pid is None and process is None:
                # No selector at all: any focused window satisfies the wait.
                return current

            return current if current.hwnd in candidates else None

        return await self._wait(
            description=(
                f"window {hwnd} focused"
                if hwnd is not None
                else f"{self._describe_selector(title, pid, process)} focused"
            ),
            timeout=timeout,
            probe=probe,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    async def _wait(
        self,
        *,
        description: str,
        timeout: float,
        probe: Any,
    ) -> WindowInfo:
        """
        Poll ``probe`` until it returns a window, bounded by ``timeout``.

        The bound is enforced here rather than trusted from the caller: an
        unbounded wait inside an automation step is a hang with no diagnosis, and
        the master constraint against infinite retries applies to waits for the
        same reason.
        """

        if timeout <= 0:
            raise DesktopError(
                code="WINDOW_TIMEOUT_INVALID",
                message=f"Timeout must be positive, got {timeout}.",
                hint="Pass a timeout in seconds, for example 10.",
            )

        limit = min(timeout, MAX_WAIT_SECONDS)

        deadline = time.perf_counter() + limit
        attempts = 0

        while True:

            attempts += 1

            found = probe()

            if found is not None:

                self._logger.bind(
                    waited_for=description,
                    attempts=attempts,
                    hwnd=found.hwnd,
                ).debug("Window wait satisfied.")

                return found

            if time.perf_counter() >= deadline:
                raise DesktopError(
                    code="WINDOW_WAIT_TIMEOUT",
                    message=(
                        f"Timed out after {limit:g}s waiting for "
                        f"{description} ({attempts} check(s))."
                    ),
                    hint=(
                        "Check the title spelling with list_windows, or raise "
                        "the timeout if the application is slow to start."
                    ),
                )

            await asyncio.sleep(_POLL_INTERVAL)

    def _match(
        self,
        *,
        title: str | None,
        pid: int | None,
        process: str | None,
        exact: bool,
    ) -> list[WindowInfo]:
        """
        Synchronous selector matching, for use inside poll probes.
        """

        needle = (title or "").strip().lower()
        process_needle = (process or "").strip().lower()

        matched: list[WindowInfo] = []

        for window in self._controller.list_windows():

            if needle:

                haystack = window.title.lower()

                if (haystack != needle) if exact else (needle not in haystack):
                    continue

            if pid is not None and window.pid != pid:
                continue

            if process_needle and process_needle not in window.process_name.lower():
                continue

            matched.append(window)

        return matched

    def _first(
        self,
        *,
        title: str | None,
        pid: int | None,
        process: str | None,
        exact: bool,
    ) -> WindowInfo | None:

        matched = self._match(
            title=title,
            pid=pid,
            process=process,
            exact=exact,
        )

        return matched[0] if matched else None

    def _describe(self, hwnd: int) -> WindowInfo:
        """
        Full snapshot in one call.

        Uses the backend's ``describe`` when it has one -- the Win32 backend does
        -- and otherwise composes the interface's separate title/position/size
        calls. The composed path is three round trips, so the window can change
        between them; the single call cannot tear that way.
        """

        describe = getattr(self._controller, "describe", None)

        if callable(describe):
            return describe(hwnd)

        from .models import WindowBounds, STATE_NORMAL

        left, top = self._controller.position(hwnd)
        width, height = self._controller.size(hwnd)

        return WindowInfo(
            hwnd=hwnd,
            title=self._controller.title(hwnd),
            class_name="",
            pid=0,
            process_name="",
            bounds=WindowBounds(left=left, top=top, width=width, height=height),
            state=STATE_NORMAL,
            is_visible=True,
            is_active=self._controller.is_active(hwnd),
        )

    @staticmethod
    def _handle(window: Any) -> int:
        """
        Accept a snapshot or a raw handle wherever a window is expected.
        """

        return window.hwnd if isinstance(window, WindowInfo) else window

    @staticmethod
    def _describe_selector(
        title: str | None,
        pid: int | None,
        process: str | None,
    ) -> str:
        """
        Render the selector for an error message.

        Worth the few lines: "no window matched title='Notepd'" points straight
        at a typo, where "window not found" sends the reader looking at the
        desktop instead of at their own argument.
        """

        parts: list[str] = []

        if title:
            parts.append(f"title={title!r}")

        if pid is not None:
            parts.append(f"pid={pid}")

        if process:
            parts.append(f"process={process!r}")

        return ", ".join(parts) or "any window"


__all__ = ["MAX_WAIT_SECONDS", "WindowService"]
