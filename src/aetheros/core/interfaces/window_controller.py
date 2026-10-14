from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WindowController(ABC):
    """
    Abstract interface for window management.

    Every implementation (PyGetWindow, Win32 API, UI Automation, etc.)
    must implement this interface.
    """

    # ==========================================================
    # Discovery
    # ==========================================================

    @abstractmethod
    def list_windows(self) -> list[Any]:
        """
        Returns all open windows.
        """
        ...

    @abstractmethod
    def find(
        self,
        title: str,
        exact: bool = False,
    ) -> Any | None:
        """
        Find a window by title.
        """
        ...

    @abstractmethod
    def active(self) -> Any | None:
        """
        Returns the currently active window.
        """
        ...

    # ==========================================================
    # Focus
    # ==========================================================

    @abstractmethod
    def activate(
        self,
        window: Any,
    ) -> None:
        """
        Bring a window to the foreground.
        """
        ...

    @abstractmethod
    def minimize(
        self,
        window: Any,
    ) -> None:
        """
        Minimize a window.
        """
        ...

    @abstractmethod
    def maximize(
        self,
        window: Any,
    ) -> None:
        """
        Maximize a window.
        """
        ...

    @abstractmethod
    def restore(
        self,
        window: Any,
    ) -> None:
        """
        Restore a minimized or maximized window.
        """
        ...

    @abstractmethod
    def close(
        self,
        window: Any,
    ) -> None:
        """
        Close a window.
        """
        ...

    # ==========================================================
    # Geometry
    # ==========================================================

    @abstractmethod
    def position(
        self,
        window: Any,
    ) -> tuple[int, int]:
        """
        Returns (x, y).
        """
        ...

    @abstractmethod
    def size(
        self,
        window: Any,
    ) -> tuple[int, int]:
        """
        Returns (width, height).
        """
        ...

    @abstractmethod
    def move(
        self,
        window: Any,
        x: int,
        y: int,
    ) -> None:
        """
        Move window.
        """
        ...

    @abstractmethod
    def resize(
        self,
        window: Any,
        width: int,
        height: int,
    ) -> None:
        """
        Resize window.
        """
        ...

    # ==========================================================
    # State
    # ==========================================================

    @abstractmethod
    def exists(
        self,
        window: Any,
    ) -> bool:
        """
        Check whether a window still exists.
        """
        ...

    @abstractmethod
    def is_active(
        self,
        window: Any,
    ) -> bool:
        """
        Returns True if the window is active.
        """
        ...

    @abstractmethod
    def title(
        self,
        window: Any,
    ) -> str:
        """
        Returns the window title.
        """
        ...