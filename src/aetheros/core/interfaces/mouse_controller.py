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
        x: int,
        y: int,
        duration: float = 0.0,
    ) -> None:
        """
        Move the mouse to an absolute screen position.

        Named ``x``/``y`` rather than ``dx``/``dy`` deliberately: the names
        reach an LLM verbatim in the ``move_mouse`` tool schema, and ``dx`` next
        to :meth:`move_relative`'s genuine ``dx`` made the two indistinguishable
        from the signature alone.
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

    # ==========================================================
    # State
    # ==========================================================

    @abstractmethod
    def is_pressed(
        self,
        button: str,
    ) -> bool:
        """
        Returns True if the button is currently held down.

        Declared here because MouseService already exposes it. It was previously
        implemented on the PyAutoGUI backend only, so the service was reaching
        past its own interface and any second backend would have broken it.
        """
        ...