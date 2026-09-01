from __future__ import annotations

import pyautogui

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.keyboard_controller import KeyboardController

# The bit GetAsyncKeyState sets while a key is physically held. The low bit of
# that return value means "was pressed since the last call", which is not the
# question is_pressed() asks.
_KEY_DOWN_BIT = 0x8000


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
        # Sequential, one key at a time -- which is what the interface promises.
        # This previously called `pyautogui.hotKey(keys)`, wrong three ways: the
        # function is `hotkey` (lowercase k), so the call raised AttributeError
        # immediately; it takes *keys rather than a list; and a hotkey holds
        # every key down simultaneously, which is the opposite of "sequentially".
        for key in keys:
            pyautogui.press(key)

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
        """
        Report whether a key is physically held right now.

        PyAutoGUI itself cannot answer this -- it only sends input -- so this
        goes to the Win32 API directly. The key-name table is borrowed from
        PyAutoGUI rather than written out here, so any name ``key_down`` can send
        is a name this can query. Two hand-maintained tables would drift, and the
        failure mode of that drift is a confident wrong answer.
        """

        # Imported lazily so this module stays importable off Windows; this is
        # the only platform-bound method on the backend.
        try:
            import win32api

        except ImportError as exc:
            raise DesktopError(
                code="KEYBOARD_STATE_UNAVAILABLE",
                message="Reading keyboard state requires pywin32.",
                hint="Install pywin32, or drop the is_pressed check.",
                cause=exc,
            ) from exc

        mapping = getattr(pyautogui.platformModule, "keyboardMapping", None)

        if not mapping:
            raise DesktopError(
                code="KEYBOARD_STATE_UNAVAILABLE",
                message=(
                    "PyAutoGUI exposes no key-name to virtual-key table on this "
                    "platform, so keyboard state cannot be read."
                ),
                hint="This check is only supported on Windows.",
            )

        code = mapping.get(key.strip().lower())

        if code is None:
            raise DesktopError(
                code="KEYBOARD_KEY_UNKNOWN",
                message=f"Unknown key name: {key!r}.",
                hint="Use a PyAutoGUI key name, for example 'ctrlleft' or 'f5'.",
            )

        return bool(win32api.GetAsyncKeyState(code) & _KEY_DOWN_BIT)

    def clear_modifiers(self) -> None:
        # Releasing a key that is not currently held is a no-op for PyAutoGUI,
        # so every modifier can be released unconditionally. Both sides of each
        # modifier are released: a hotkey interrupted mid-flight may have left
        # either one down, and a stuck modifier silently corrupts every
        # keystroke that follows.
        for key in (
            "ctrlleft",
            "ctrlright",
            "altleft",
            "altright",
            "shiftleft",
            "shiftright",
            "winleft",
            "winright",
        ):
            pyautogui.keyUp(key)
