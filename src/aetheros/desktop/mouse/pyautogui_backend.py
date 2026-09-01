from __future__ import annotations

import pyautogui

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.mouse_controller import MouseController

# The bit GetAsyncKeyState sets while a button is physically held. The low bit
# means "was pressed since the last call", which is a different question.
_BUTTON_DOWN_BIT = 0x8000

# Win32 virtual-key codes for the mouse buttons. These follow the *logical*
# buttons, so on a system with primary and secondary swapped, "left" is still
# the primary button -- which matches how pyautogui sends clicks.
_BUTTON_CODES = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
}


class PyAutoGuiMouse(MouseController):
    """PyAutoGUI implementation of MouseController."""

    def __init__(self) -> None:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01

    # ==========================================================
    # Movement
    # ==========================================================

    def move_to(
        self,
        x: int,
        y: int,
        duration: float = 0.0,
    ) -> None:
        pyautogui.moveTo(
            x,
            y,
            duration=duration,
        )

    def move_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.0,
    ) -> None:
        pyautogui.moveRel(
            dx,
            dy,
            duration=duration,
        )

    # ==========================================================
    # Clicks
    # ==========================================================

    def click(
        self,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:
        pyautogui.click(
            button=button,
            clicks=clicks,
            interval=interval,
        )

    def double_click(
        self,
        button: str = "left",
    ) -> None:
        pyautogui.doubleClick(button=button)

    def right_click(self) -> None:
        pyautogui.rightClick()

    def middle_click(self) -> None:
        pyautogui.middleClick()

    # ==========================================================
    # Mouse buttons
    # ==========================================================

    def mouse_down(
        self,
        button: str = "left",
    ) -> None:
        pyautogui.mouseDown(button=button)

    def mouse_up(
        self,
        button: str = "left",
    ) -> None:
        pyautogui.mouseUp(button=button)

    # ==========================================================
    # Drag
    # ==========================================================

    def drag_to(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:
        pyautogui.dragTo(
            x,
            y,
            duration=duration,
            button=button,
        )

    def drag_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:
        pyautogui.dragRel(
            dx,
            dy,
            duration=duration,
            button=button,
        )

    # ==========================================================
    # Scroll
    # ==========================================================

    def scroll(self, amount: int) -> None:
        pyautogui.scroll(amount)

    def hscroll(self, amount: int) -> None:
        pyautogui.hscroll(amount)

    # ==========================================================
    # Position
    # ==========================================================

    def position(self) -> tuple[int, int]:
        pos = pyautogui.position()
        return pos.x, pos.y

    # ==========================================================
    # State
    # ==========================================================

    def is_pressed(self, button: str) -> bool:
        """
        Report whether a mouse button is physically held right now.

        PyAutoGUI cannot answer this -- it only sends input -- so this reads the
        button state from Win32 directly. Previously it raised
        NotImplementedError while MouseService advertised the capability.
        """

        # Imported lazily so this module stays importable off Windows; this is
        # the only platform-bound method on the backend.
        try:
            import win32api

        except ImportError as exc:
            raise DesktopError(
                code="MOUSE_STATE_UNAVAILABLE",
                message="Reading mouse button state requires pywin32.",
                hint="Install pywin32, or drop the is_pressed check.",
                cause=exc,
            ) from exc

        code = _BUTTON_CODES.get(button.strip().lower())

        if code is None:
            raise DesktopError(
                code="MOUSE_BUTTON_UNKNOWN",
                message=f"Unknown mouse button: {button!r}.",
                hint=f"Use one of: {', '.join(sorted(_BUTTON_CODES))}.",
            )

        return bool(win32api.GetAsyncKeyState(code) & _BUTTON_DOWN_BIT)