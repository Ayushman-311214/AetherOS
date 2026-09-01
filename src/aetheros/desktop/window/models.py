"""
Window identity and geometry.

A title is not an identity. Two Explorer windows routinely share one, a browser's
changes as the user navigates, and tool windows often have none at all. Every
window that leaves this subsystem therefore carries its ``hwnd`` -- the only
handle Windows guarantees to be stable and unique for the window's lifetime --
alongside the process that owns it, and every tool that accepts a window accepts
an hwnd as well as a title.

That is the difference between "focus the window called Untitled - Notepad" and
"focus *this* window", and it is the difference between an automation sequence
that keeps typing into the right place and one that silently switches target
halfway through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# The three states ShowWindow can leave a window in that a caller can observe.
# Kept as strings rather than an enum because they cross the tool boundary into
# JSON, where an enum would serialise as its value anyway.
STATE_NORMAL = "normal"
STATE_MINIMIZED = "minimized"
STATE_MAXIMIZED = "maximized"


@dataclass(frozen=True, slots=True)
class WindowBounds:
    """
    A window's screen rectangle.

    Stored as origin plus extent rather than as two corners because that is what
    both callers want: ``move_window`` needs the origin and ``resize_window``
    needs the extent. ``right`` and ``bottom`` are derived so the two
    representations cannot drift apart.
    """

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def center(self) -> tuple[int, int]:
        """
        Midpoint, for aiming a click at a window without knowing its layout.
        """

        return (
            self.left + self.width // 2,
            self.top + self.height // 2,
        )

    def to_dict(self) -> dict[str, int]:

        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "right": self.right,
            "bottom": self.bottom,
        }


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """
    A snapshot of one top-level window.

    A snapshot, emphatically: the user can move, close or retitle the window the
    instant after this is built. ``hwnd`` stays valid as an identifier -- it
    either still names this window or names nothing -- which is why every
    mutating call re-checks the handle rather than trusting the rest of these
    fields.
    """

    hwnd: int
    title: str
    class_name: str
    pid: int
    process_name: str
    bounds: WindowBounds
    state: str
    is_visible: bool
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        """
        Flatten for a tool result.

        ``hwnd`` is first because it is the field the model should pass back to
        act on this window.
        """

        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "class_name": self.class_name,
            "pid": self.pid,
            "process_name": self.process_name,
            "bounds": self.bounds.to_dict(),
            "state": self.state,
            "is_visible": self.is_visible,
            "is_active": self.is_active,
        }


__all__ = [
    "STATE_MAXIMIZED",
    "STATE_MINIMIZED",
    "STATE_NORMAL",
    "WindowBounds",
    "WindowInfo",
]
