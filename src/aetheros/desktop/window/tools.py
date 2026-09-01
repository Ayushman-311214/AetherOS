"""
Window tools.

Every tool here takes the same selector set -- ``hwnd``, ``title``, ``pid``,
``process``, ``active`` -- rather than a bare title, so the model can address a
window by whatever it actually knows. ``hwnd`` is exact and comes straight back
from ``list_windows``; ``active`` needs no name at all.

Each mutating tool returns the window's state *after* the change, read back from
the desktop rather than assumed. That gives the verification layer something real
to check, and it is the difference between "the tool ran" and "the window moved".
"""

from __future__ import annotations

from typing import Any

from ...core.container import container
from ...tools import tool

from .controller import WindowService

# The selector wording is identical in every description below, so it is written
# once here and interpolated. Duplicated prose drifts, and a stale description is
# a tool the model calls wrongly.
_SELECTOR = (
    "Identify the window with exactly one of: hwnd (exact, as returned by "
    "list_windows -- prefer this), title (case-insensitive substring unless "
    "exact=true), pid, process (executable name), or active=true for the "
    "currently focused window. pid and title can be combined to pick one of "
    "several windows with the same title."
)


async def _service() -> WindowService:

    return container.resolve(WindowService)


async def _target(
    *,
    hwnd: int | None,
    title: str | None,
    pid: int | None,
    process: str | None,
    active: bool,
    exact: bool,
) -> tuple[WindowService, Any]:
    """
    Resolve the selector to one window, or raise a DesktopError naming why not.
    """

    windows = await _service()

    window = await windows.resolve(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    return windows, window


# ==============================================================
# Enumeration
# ==============================================================


@tool(
    category="desktop.window",
    description=(
        "List every visible window that has a title, frontmost first. Returns "
        "hwnd, title, class_name, pid, process_name, bounds, state, is_visible "
        "and is_active for each. Use the hwnd from this list to act on a "
        "specific window -- titles are not unique and change as the user works."
    ),
)
async def list_windows(
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    exact: bool = False,
) -> dict[str, Any]:

    windows = await _service()

    found = (
        await windows.search(
            title=title,
            pid=pid,
            process=process,
            exact=exact,
        )
        if (title or pid is not None or process)
        else await windows.list_windows()
    )

    return {
        "count": len(found),
        "windows": [window.to_dict() for window in found],
    }


@tool(
    category="desktop.window",
    description=(
        "Get the window that currently has keyboard focus. Returns null when "
        "nothing is focused, which happens briefly during window switches and "
        "while the lock screen is up. Call this before typing to confirm the "
        "keystrokes will land where intended."
    ),
)
async def get_active_window() -> dict[str, Any] | None:

    windows = await _service()

    window = await windows.active()

    return window.to_dict() if window else None


@tool(
    category="desktop.window",
    description=(
        "Check whether a window exists right now. Returns exists=false rather "
        "than failing, so this is the safe way to confirm a window closed. "
        f"{_SELECTOR}"
    ),
)
async def window_exists(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    exact: bool = False,
) -> dict[str, Any]:

    windows = await _service()

    if hwnd is not None:
        return {"exists": await windows.exists(hwnd), "hwnd": hwnd}

    matches = await windows.search(
        title=title,
        pid=pid,
        process=process,
        exact=exact,
    )

    return {
        "exists": bool(matches),
        "count": len(matches),
        "windows": [window.to_dict() for window in matches],
    }


# ==============================================================
# Focus
# ==============================================================


@tool(
    category="desktop.window",
    description=(
        "Bring a window to the front and give it keyboard focus. Fails with a "
        "clear error if focus does not actually land on it -- Windows blocks "
        "focus changes from a background process, so this can legitimately be "
        "refused. Always focus a window before typing into it. "
        f"{_SELECTOR}"
    ),
)
async def focus_window(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.activate(window)

    # Read back rather than reporting the pre-change snapshot: is_active is the
    # whole point of this call, and the snapshot was taken before the change.
    return (await windows.bounds(window)).to_dict()


# ==============================================================
# State
# ==============================================================


@tool(
    category="desktop.window",
    description=(
        "Minimize a window to the taskbar without activating it. "
        f"{_SELECTOR}"
    ),
)
async def minimize_window(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.minimize(window)

    return (await windows.bounds(window)).to_dict()


@tool(
    category="desktop.window",
    description=(
        "Maximize a window to fill its monitor. "
        f"{_SELECTOR}"
    ),
)
async def maximize_window(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.maximize(window)

    return (await windows.bounds(window)).to_dict()


@tool(
    category="desktop.window",
    description=(
        "Restore a minimized or maximized window to its normal size and "
        "position. "
        f"{_SELECTOR}"
    ),
)
async def restore_window(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.restore(window)

    return (await windows.bounds(window)).to_dict()


@tool(
    category="desktop.window",
    description=(
        "Ask a window to close. This is a request, not a guarantee: an "
        "application with unsaved work will show a save prompt and stay open, "
        "which is correct behaviour. The result reports still_open -- check it, "
        "and handle any dialog before assuming the window is gone. To force a "
        "process to exit, use the process tools instead. "
        f"{_SELECTOR}"
    ),
)
async def close_window(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    handle = window.hwnd
    title_before = window.title

    await windows.close(window)

    # Not a verification, and not presented as one: WM_CLOSE is asynchronous, so
    # a window that will close may still be open for a few more milliseconds.
    # The honest report is what is true now, leaving the caller to wait or check.
    return {
        "hwnd": handle,
        "title": title_before,
        "close_requested": True,
        "still_open": await windows.exists(handle),
    }


@tool(
    category="desktop.window",
    description=(
        "Get whether a window is normal, minimized or maximized. "
        f"{_SELECTOR}"
    ),
)
async def get_window_state(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    current = await windows.bounds(window)

    return {
        "hwnd": current.hwnd,
        "title": current.title,
        "state": current.state,
        "is_visible": current.is_visible,
        "is_active": current.is_active,
    }


# ==============================================================
# Geometry
# ==============================================================


@tool(
    category="desktop.window",
    description=(
        "Get a window's screen rectangle: left, top, width, height, right, "
        "bottom, plus its title and state. Use the bounds to aim a click inside "
        "a specific window rather than at absolute coordinates that assume a "
        "particular layout. "
        f"{_SELECTOR}"
    ),
)
async def get_window_bounds(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    return (await windows.bounds(window)).to_dict()


@tool(
    category="desktop.window",
    description=(
        "Move a window so its top-left corner sits at the given screen "
        "coordinates. The size is unchanged. "
        f"{_SELECTOR}"
    ),
)
async def move_window(
    x: int,
    y: int,
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.move(window, x=x, y=y)

    return (await windows.bounds(window)).to_dict()


@tool(
    category="desktop.window",
    description=(
        "Resize a window to the given width and height in pixels. The position "
        "is unchanged. A maximized window is restored first, since a maximized "
        "window ignores resize requests. "
        f"{_SELECTOR}"
    ),
)
async def resize_window(
    width: int,
    height: int,
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    active: bool = False,
    exact: bool = False,
) -> dict[str, Any]:

    windows, window = await _target(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        active=active,
        exact=exact,
    )

    await windows.resize(window, width=width, height=height)

    return (await windows.bounds(window)).to_dict()


# ==============================================================
# Waiting
# ==============================================================


@tool(
    category="desktop.window",
    description=(
        "Wait until a matching window appears, then return it. Use this after "
        "launching an application instead of a fixed sleep -- it returns as soon "
        "as the window exists and fails with a timeout error if it never does. "
        "The timeout is capped at 120 seconds."
    ),
)
async def wait_for_window(
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    timeout: float = 10.0,
    exact: bool = False,
) -> dict[str, Any]:

    windows = await _service()

    window = await windows.wait_for_window(
        title=title,
        pid=pid,
        process=process,
        timeout=timeout,
        exact=exact,
    )

    return window.to_dict()


@tool(
    category="desktop.window",
    description=(
        "Wait until a matching window has keyboard focus, then return it. "
        "Existing and being focused are different states: typing into a window "
        "that exists but is not focused sends the keystrokes elsewhere. Use this "
        "between focus_window and type_text when an application is slow to take "
        "focus. The timeout is capped at 120 seconds."
    ),
)
async def wait_until_window_active(
    hwnd: int | None = None,
    title: str | None = None,
    pid: int | None = None,
    process: str | None = None,
    timeout: float = 10.0,
    exact: bool = False,
) -> dict[str, Any]:

    windows = await _service()

    window = await windows.wait_until_active(
        hwnd=hwnd,
        title=title,
        pid=pid,
        process=process,
        timeout=timeout,
        exact=exact,
    )

    return window.to_dict()
