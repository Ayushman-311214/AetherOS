from __future__ import annotations

import pyautogui

from ...core.interfaces.keyboard_controller import KeyboardController


class PyAutoGuiKeyboard(KeyboardController):
    """
    PyAutoGUI implementation of the KeyboardController interface.
    """

    def __init__(self) -> None:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01

    # ==========================================================
    # Typing
    # ==========================================================

    def write(
        self,
        text: str,
        interval: float = 0.0,
    ) -> None:
        pyautogui.write(
            text,
            interval=interval,
        )

    # ==========================================================
    # Keys
    # ==========================================================

    def press(
        self,
        key: str,
    ) -> None:
        pyautogui.press(key)

    def press_many(
        self,
        keys: list[str],
    ) -> None:
        pyautogui.hotKey(keys)

    def key_down(
        self,
        key: str,
    ) -> None:
        pyautogui.keyDown(key)

    def key_up(
        self,
        key: str,
    ) -> None:
        pyautogui.keyUp(key)

    def tap(
        self,
        key: str,
    ) -> None:
        pyautogui.press(key)

    # ==========================================================
    # Hotkeys
    # ==========================================================

    def hotkey(
        self,
        *keys: str,
    ) -> None:
        pyautogui.hotkey(*keys)

    # ==========================================================
    # State
    # ==========================================================

    def is_pressed(
        self,
        key: str,
    ) -> bool:
        raise NotImplementedError(
            "PyAutoGUI does not support querying keyboard state."
        )

    def clear_modifiers(self) -> None:
        print("RELASE ALLL KEYS")