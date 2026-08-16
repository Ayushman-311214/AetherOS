from __future__ import annotations

from abc import ABC, abstractmethod


class MouseController(ABC):
    """
    Abstract interface for mouse control.

    Every mouse implementation must implement this interface.
    """

    # ==========================================================
    # Position
    # ==========================================================

    @abstractmethod
    def position(self) -> tuple[int, int]:
        """
        Get the current mouse position.

        Returns:
            (x, y)
        """
        ...

    @abstractmethod
    def move_to(
        self,
        dx: int,
        dy: int,
        duration: float = 0.0,
    ) -> None:
        """
        Move the mouse to an absolute position.
        """
        ...

    @abstractmethod
    def move_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.0,
    ) -> None:
        """
        Move the mouse relative to the current position.
        """
        ...

    # ==========================================================
    # Click
    # ==========================================================

    @abstractmethod
    def click(
        self,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:
        """
        Perform mouse click(s).
        """
        ...

    @abstractmethod
    def double_click(
        self,
        button: str = "left",
    ) -> None:
        """
        Double click.
        """
        ...

    @abstractmethod
    def right_click(self) -> None:
        """
        Right click.
        """
        ...

    @abstractmethod
    def middle_click(self) -> None:
        """
        Middle click.
        """
        ...

    # ==========================================================
    # Drag
    # ==========================================================

    @abstractmethod
    def drag_to(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> None:
        """
        Drag to an absolute position.
        """
        ...

    @abstractmethod
    def drag_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> None:
        """
        Drag relative to the current position.
        """
        ...

    # ==========================================================
    # Button State
    # ==========================================================

    @abstractmethod
    def mouse_down(
        self,
        button: str = "left",
    ) -> None:
        """
        Press and hold a mouse button.
        """
        ...

    @abstractmethod
    def mouse_up(
        self,
        button: str = "left",
    ) -> None:
        """
        Release a mouse button.
        """
        ...

    # ==========================================================
    # Scroll
    # ==========================================================

    @abstractmethod
    def scroll(
        self,
        clicks: int,
    ) -> None:
        """
        Vertical scroll.
        """
        ...

    @abstractmethod
    def hscroll(
        self,
        clicks: int,
    ) -> None:
        """
        Horizontal scroll.
        """
        ...