"""
Win32 window backend.

Uses pywin32 directly rather than pygetwindow (which pyautogui bundles) for two
reasons that matter to this subsystem specifically:

* pygetwindow identifies windows by title and offers no process information, so
  it cannot answer "which of these three windows called 'Document1 - Word' is the
  one I launched" -- the question automation actually needs.
* Its ``activate()`` swallows the ``SetForegroundWindow`` restriction described
  below and returns as if focus succeeded, which is precisely the failure mode
  the verification layer exists to catch.

``SetForegroundWindow`` is the one genuinely awkward call here. Windows refuses it
unless the calling process already owns the foreground window, or is otherwise
entitled to steal focus -- a deliberate anti-hijacking rule, not a bug to route
around. This backend restores a minimized window first (a minimized window cannot
take focus at all), attempts the call, falls back to ``BringWindowToTop``, and
then *checks ``GetForegroundWindow``*. If focus did not land, it raises. Reporting
success for an unfocused window would send every subsequent keystroke somewhere
nobody chose.

Every mutating method re-validates the handle before acting. An ``hwnd`` outlives
nothing: the window may have closed between the caller reading a
:class:`WindowInfo` and acting on it, and acting on a dead handle otherwise fails
in whatever way the specific API chooses.
"""

from __future__ import annotations

from typing import Any

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.window_controller import WindowController

from .models import (
    STATE_MAXIMIZED,
    STATE_MINIMIZED,
    STATE_NORMAL,
    WindowBounds,
    WindowInfo,
)

# Guarded at import so the module stays importable off Windows -- the test suite
# and any Linux CI need to import the package without pywin32 present. The
# failure is deferred to the first call, where _require() names the dependency.
try:
    import win32con
    import win32gui
    import win32process

    _IMPORT_ERROR: Exception | None = None

except ImportError as exc:  # pragma: no cover - platform dependent
    win32con = None  # type: ignore[assignment]
    win32gui = None  # type: ignore[assignment]
    win32process = None  # type: ignore[assignment]

    _IMPORT_ERROR = exc

# psutil is only needed for the owning process *name*, which is descriptive
# metadata rather than identity -- pid and hwnd carry identity. A missing psutil
# degrades the name to empty rather than failing the enumeration.
try:
    import psutil

except ImportError:  # pragma: no cover - psutil is a declared dependency
    psutil = None  # type: ignore[assignment]


def _require() -> None:
    """
    Fail with a dependency error rather than an AttributeError on ``None``.
    """

    if _IMPORT_ERROR is not None:
        raise DesktopError(
            code="WINDOW_BACKEND_UNAVAILABLE",
            message="Window control requires pywin32 on Windows.",
            hint="Install pywin32. Window management is Windows-only.",
            cause=_IMPORT_ERROR,
        )


class Win32Window(WindowController):
    """
    Window control through the Win32 API.

    Windows are addressed by ``hwnd`` throughout. Methods accept either an
    integer handle or a :class:`WindowInfo` (whose handle is read out), so a
    caller can pass back whatever ``list_windows`` gave it.
    """

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _hwnd(window: Any) -> int:
        """
        Coerce whatever the caller passed into a window handle.

        Accepts a :class:`WindowInfo`, a raw int, or a numeric string -- the last
        because an hwnd that has been through JSON on its way from the model
        arrives as either an int or a string depending on the provider.
        """

        if isinstance(window, WindowInfo):
            return window.hwnd

        if isinstance(window, bool):
            # bool is an int subclass, and True would silently become hwnd 1.
            raise DesktopError(
                code="WINDOW_HANDLE_INVALID",
                message=f"Not a window handle: {window!r}.",
                hint="Pass an hwnd from list_windows, or a window title.",
            )

        if isinstance(window, int):
            return window

        if isinstance(window, str):

            text = window.strip()

            if text.isdigit():
                return int(text)

        raise DesktopError(
            code="WINDOW_HANDLE_INVALID",
            message=f"Not a window handle: {window!r}.",
            hint="Pass an hwnd from list_windows, or a window title.",
        )

    def _validated(self, window: Any) -> int:
        """
        Resolve to a handle and confirm the window still exists.

        Checked on every mutating call because a handle is only a name: the
        window it named may have closed a moment ago, and ``ShowWindow`` on a
        dead handle fails in a way that says nothing about why.
        """

        _require()

        hwnd = self._hwnd(window)

        if not win32gui.IsWindow(hwnd):
            raise DesktopError(
                code="WINDOW_NOT_FOUND",
                message=f"No window with handle {hwnd}.",
                hint=(
                    "The window may have closed. Call list_windows again for "
                    "current handles."
                ),
            )

        return hwnd

    @staticmethod
    def _process_name(pid: int) -> str:
        """
        Owning process name, or empty when it cannot be read.

        Empty rather than an exception: a protected process denies inspection,
        and losing a descriptive field is not a reason to fail an enumeration
        that is otherwise complete and correct.
        """

        if psutil is None or pid <= 0:
            return ""

        try:
            return psutil.Process(pid).name()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return ""

    def _state(self, hwnd: int) -> str:

        if win32gui.IsIconic(hwnd):
            return STATE_MINIMIZED

        if win32gui.IsZoomed(hwnd):
            return STATE_MAXIMIZED

        return STATE_NORMAL

    def _describe(self, hwnd: int) -> WindowInfo:
        """
        Build a snapshot of one window.
        """

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        try:
            _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)

        except Exception:
            # Some system windows refuse this. pid 0 is not a real process, and
            # the caller can tell it apart from a genuine one.
            pid = 0

        return WindowInfo(
            hwnd=hwnd,
            title=win32gui.GetWindowText(hwnd),
            class_name=win32gui.GetClassName(hwnd),
            pid=pid,
            process_name=self._process_name(pid),
            bounds=WindowBounds(
                left=left,
                top=top,
                width=right - left,
                height=bottom - top,
            ),
            state=self._state(hwnd),
            is_visible=bool(win32gui.IsWindowVisible(hwnd)),
            is_active=hwnd == win32gui.GetForegroundWindow(),
        )

    # ==========================================================
    # Enumeration
    # ==========================================================

    def list_windows(self) -> list[Any]:
        """
        Every visible top-level window that has a title, in Z-order.

        Filtered rather than raw: ``EnumWindows`` returns several hundred handles
        on an idle desktop, nearly all of them invisible message-only windows and
        untitled shell surfaces that no automation step can act on. Z-order is
        preserved because ``EnumWindows`` walks front to back, which makes the
        first match in :meth:`find` the topmost one -- the one the user is
        looking at.
        """

        _require()

        found: list[WindowInfo] = []

        def collect(hwnd: int, _extra: Any) -> bool:

            if not win32gui.IsWindowVisible(hwnd):
                return True

            if not win32gui.GetWindowText(hwnd):
                return True

            try:
                found.append(self._describe(hwnd))

            except Exception:
                # The window closed mid-enumeration. Skipping it is correct: it
                # is not part of the answer, and it is not an error for a window
                # to disappear while a list is being built.
                pass

            # Truthy keeps EnumWindows going.
            return True

        win32gui.EnumWindows(collect, None)

        return list(found)

    def find(
        self,
        title: str,
        exact: bool = False,
    ) -> Any | None:
        """
        The topmost window whose title matches.

        Case-insensitive, and a substring match unless ``exact``. Substring by
        default because real titles carry decoration the caller does not know --
        "Untitled - Notepad", "report.xlsx - Excel" -- and requiring an exact
        match would make the common case unusable.

        Returns the first match in Z-order, so with several matching windows the
        frontmost wins. When that ambiguity matters, use :meth:`list_windows` and
        pick by ``pid`` or ``class_name``.
        """

        needle = title.strip().lower()

        if not needle:
            raise DesktopError(
                code="WINDOW_TITLE_EMPTY",
                message="A window title is required to search for a window.",
                hint="Pass a non-empty title, or use list_windows to enumerate.",
            )

        for window in self.list_windows():

            haystack = window.title.lower()

            if (haystack == needle) if exact else (needle in haystack):
                return window

        return None

    def active(self) -> Any | None:
        """
        The foreground window, or ``None`` when nothing is focused.

        ``None`` is a real state, not just an error case: it happens briefly
        during window switches and while the lock screen is up.
        """

        _require()

        hwnd = win32gui.GetForegroundWindow()

        if not hwnd or not win32gui.IsWindow(hwnd):
            return None

        return self._describe(hwnd)

    # ==========================================================
    # Focus
    # ==========================================================

    def activate(
        self,
        window: Any,
    ) -> None:
        """
        Bring a window to the foreground and give it keyboard focus.

        Verified rather than assumed. ``SetForegroundWindow`` is allowed to
        refuse -- Windows blocks focus theft from a process that does not already
        own the foreground -- and it signals that by raising or by returning
        without doing anything. Both are indistinguishable from success unless
        the result is checked, so this checks it.
        """

        hwnd = self._validated(window)

        # A minimized window cannot receive focus at all; restore it first.
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        attempt_error: Exception | None = None

        try:
            win32gui.SetForegroundWindow(hwnd)

        except Exception as exc:
            # Held, not swallowed: it becomes the cause of the error raised below
            # if focus genuinely did not land. If focus *did* land despite the
            # refusal -- which happens, because the shell sometimes grants it
            # anyway -- the caller wanted the outcome, not the complaint.
            attempt_error = exc

        if win32gui.GetForegroundWindow() != hwnd:

            # Weaker fallback: raises the window without necessarily focusing it.
            # Worth trying because it succeeds in some of the cases where
            # SetForegroundWindow is refused.
            try:
                win32gui.BringWindowToTop(hwnd)

            except Exception as exc:
                attempt_error = attempt_error or exc

        if win32gui.GetForegroundWindow() != hwnd:
            raise DesktopError(
                code="WINDOW_FOCUS_FAILED",
                message=(
                    f"Could not give focus to window {hwnd} "
                    f"({win32gui.GetWindowText(hwnd)!r})."
                ),
                hint=(
                    "Windows blocks focus changes from a background process. "
                    "Click the target window once, or focus a window owned by "
                    "this process first."
                ),
                cause=attempt_error,
            )

    def is_active(
        self,
        window: Any,
    ) -> bool:

        _require()

        return self._hwnd(window) == win32gui.GetForegroundWindow()

    # ==========================================================
    # State
    # ==========================================================

    def minimize(
        self,
        window: Any,
    ) -> None:

        hwnd = self._validated(window)

        # SW_MINIMIZE rather than SW_SHOWMINIMIZED: the former does not activate
        # the window on its way down, which is what "minimize" means.
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    def maximize(
        self,
        window: Any,
    ) -> None:

        hwnd = self._validated(window)

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    def restore(
        self,
        window: Any,
    ) -> None:

        hwnd = self._validated(window)

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    def close(
        self,
        window: Any,
    ) -> None:
        """
        Ask a window to close.

        ``WM_CLOSE`` is a request, and deliberately so: the application may show
        an unsaved-changes prompt and stay open. That is the correct behaviour --
        destroying the window outright would discard the user's work without
        asking. A caller that needs the process gone should verify with
        :meth:`exists` and escalate through the process subsystem, where killing
        is an explicit, policy-gated action.

        ``PostMessage`` rather than ``SendMessage``: the latter blocks until the
        application finishes handling the message, which for a window showing a
        modal save prompt means blocking until the user answers it.
        """

        hwnd = self._validated(window)

        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    # ==========================================================
    # Geometry
    # ==========================================================

    def position(
        self,
        window: Any,
    ) -> tuple[int, int]:

        hwnd = self._validated(window)

        left, top, _right, _bottom = win32gui.GetWindowRect(hwnd)

        return left, top

    def size(
        self,
        window: Any,
    ) -> tuple[int, int]:

        hwnd = self._validated(window)

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        return right - left, bottom - top

    def move(
        self,
        window: Any,
        x: int,
        y: int,
    ) -> None:
        """
        Move without resizing.

        ``MoveWindow`` sets position and size together, so the current size is
        read first and passed through unchanged. Reading it here rather than
        letting the caller supply it keeps "move" from silently resizing.
        """

        hwnd = self._validated(window)

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        win32gui.MoveWindow(
            hwnd,
            x,
            y,
            right - left,
            bottom - top,
            True,
        )

    def resize(
        self,
        window: Any,
        width: int,
        height: int,
    ) -> None:
        """
        Resize without moving.

        A maximized window ignores this, so it is restored first -- otherwise the
        call reports success while the window stays exactly as it was.
        """

        hwnd = self._validated(window)

        if width <= 0 or height <= 0:
            raise DesktopError(
                code="WINDOW_SIZE_INVALID",
                message=f"Window size must be positive, got {width}x{height}.",
                hint="Pass a width and height greater than zero.",
            )

        if win32gui.IsZoomed(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        left, top, _right, _bottom = win32gui.GetWindowRect(hwnd)

        win32gui.MoveWindow(
            hwnd,
            left,
            top,
            width,
            height,
            True,
        )

    # ==========================================================
    # Identity
    # ==========================================================

    def exists(
        self,
        window: Any,
    ) -> bool:

        _require()

        try:
            hwnd = self._hwnd(window)

        except DesktopError:
            # An unusable handle is not a window that exists.
            return False

        return bool(win32gui.IsWindow(hwnd))

    def title(
        self,
        window: Any,
    ) -> str:

        hwnd = self._validated(window)

        return win32gui.GetWindowText(hwnd)

    # ==========================================================
    # Beyond the interface
    # ==========================================================

    def describe(
        self,
        window: Any,
    ) -> WindowInfo:
        """
        Full snapshot of one window.

        Not on the interface, which exposes title, position and size as separate
        calls. Three round trips to describe one window is three chances for it
        to change in between, and the tools want one coherent picture.
        """

        return self._describe(self._validated(window))


__all__ = ["Win32Window"]
