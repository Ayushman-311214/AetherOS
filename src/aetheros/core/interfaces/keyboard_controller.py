from __future__ import annotations

from abc import ABC, abstractmethod


class KeyboardController(ABC):
    """
    Abstract interface for keyboard automation.

    Every keyboard implementation must implement this interface.
    """

    # ==========================================================
    # Typing
    # ==========================================================

    @abstractmethod
    def write(
        self,
        text: str,
        interval: float = 0.0,
    ) -> None:
        """
        Type text.
        """
        ...

    @abstractmethod
    def press(
        self,
        key: str,
    ) -> None:
        """
        Press and release a key.
        """
        ...

    @abstractmethod
    def press_many(
        self,
        keys: list[str],
    ) -> None:
        """
        Press multiple keys sequentially.
        """
        ...

    # ==========================================================
    # Key State
    # ==========================================================

    @abstractmethod
    def key_down(
        self,
        key: str,
    ) -> None:
        """
        Hold a key.
        """
        ...

    @abstractmethod
    def key_up(
        self,
        key: str,
    ) -> None:
        """
        Release a held key.
        """
        ...

    # ==========================================================
    # Hotkeys
    # ==========================================================

    @abstractmethod
    def hotkey(
        self,
        *keys: str,
    ) -> None:
        """
        Execute a keyboard shortcut.

        Example:
            Ctrl+C
            Ctrl+Shift+Esc
            Alt+Tab
        """
        ...

    # ==========================================================
    # Utility
    # ==========================================================

    @abstractmethod
    def is_pressed(
        self,
        key: str,
    ) -> bool:
        """
        Returns True if the key is currently pressed.
        """
        ...

    @abstractmethod
    def clear_modifiers(self) -> None:
        """
        Release all modifier keys.

        Useful after automation failures.
        """
        ...