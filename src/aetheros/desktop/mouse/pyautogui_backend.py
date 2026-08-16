from __future__ import annotations

import pyautogui

from ...core.interfaces.mouse_controller import MouseController


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
        dx: int,
        dy: int,
        duration: float = 0.0,
    ) -> None:
        pyautogui.moveTo(
            dx,
            dy,
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
        raise NotImplementedError(
            "PyAutoGUI does not support querying mouse button state."
        )