from __future__ import annotations

from ...core.interfaces.mouse_controller import MouseController
from ...core.logging import get_logger


class MouseService:
    """
    High-level mouse service.

    This class delegates all operations to the configured
    MouseController implementation.

    Business logic, retries, logging, metrics, and events
    belong here—not in the backend implementation.
    """

    def __init__(
        self,
        controller: MouseController,
    ) -> None:

        self._controller = controller

        self._logger = get_logger("mouse")

    # ==========================================================
    # Movement
    # ==========================================================

    async def move(
        self,
        x: int,
        y: int,
        duration: float = 0.0,
    ) -> None:

        # bind(), not %-style args: loguru formats with str.format, so
        # positional args would be dropped silently.
        self._logger.bind(
            x=x,
            y=y,
        ).debug("Moving mouse to absolute position.")

        self._controller.move_to(
            x=x,
            y=y,
            duration=duration,
        )

    async def move_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.0,
    ) -> None:

        self._controller.move_relative(
            dx=dx,
            dy=dy,
            duration=duration,
        )

    # ==========================================================
    # Clicks
    # ==========================================================

    async def click(
        self,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:

        self._controller.click(
            button=button,
            clicks=clicks,
            interval=interval,
        )

    async def double_click(
        self,
        button: str = "left",
    ) -> None:

        self._controller.double_click(
            button=button,
        )

    async def right_click(self) -> None:

        self._controller.right_click()

    async def middle_click(self) -> None:

        self._controller.middle_click()

    # ==========================================================
    # Button State
    # ==========================================================

    async def mouse_down(
        self,
        button: str = "left",
    ) -> None:
        """
        Press a button and leave it held.

        Exposed separately from click() because a held button is what makes
        press-drag-release sequences possible: selecting a range of text,
        dragging a scrollbar, drawing on a canvas. drag_to() covers the common
        case in one call; this is for the cases it cannot express.
        """

        self._logger.bind(button=button).debug("Holding mouse button.")

        self._controller.mouse_down(button=button)

    async def mouse_up(
        self,
        button: str = "left",
    ) -> None:
        """
        Release a held button.
        """

        self._logger.bind(button=button).debug("Releasing mouse button.")

        self._controller.mouse_up(button=button)

    # ==========================================================
    # Drag
    # ==========================================================

    async def drag_to(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:

        self._controller.drag_to(
            x=x,
            y=y,
            duration=duration,
            button=button,
        )

    async def drag_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:

        self._controller.drag_relative(
            dx=dx,
            dy=dy,
            duration=duration,
            button=button,
        )

    # ==========================================================
    # Scroll
    # ==========================================================

    async def scroll(
        self,
        amount: int,
    ) -> None:

        self._controller.scroll(amount)

    async def hscroll(
        self,
        amount: int,
    ) -> None:

        self._controller.hscroll(amount)

    # ==========================================================
    # Position
    # ==========================================================

    async def position(
        self,
    ) -> tuple[int, int]:

        return self._controller.position()

    # ==========================================================
    # State
    # ==========================================================

    async def is_pressed(
        self,
        button: str,
    ) -> bool:

        return self._controller.is_pressed(button)