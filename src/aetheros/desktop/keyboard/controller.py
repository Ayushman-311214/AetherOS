from __future__ import annotations

from ...core.interfaces.keyboard_controller import KeyboardController
from ...core.logging import get_logger


class KeyboardService:
    """
    High-level keyboard service.

    This service delegates all keyboard operations to the
    configured KeyboardController implementation.

    Cross-cutting concerns such as logging, retries,
    permissions, metrics, and events belong here.
    """

    def __init__(
        self,
        controller: KeyboardController,
    ) -> None:
        self._controller = controller
        self._logger = get_logger("keyboard")

    # ==========================================================
    # Typing
    # ==========================================================

    async def write(
        self,
        text: str,
        interval: float = 0.0,
    ) -> None:
        self._logger.debug(
            "Typing %d characters.",
            len(text),
        )

        self._controller.write(
            text=text,
            interval=interval,
        )

    # ==========================================================
    # Keys
    # ==========================================================

    async def press(
        self,
        key: str,
    ) -> None:
        self._controller.press(key)

    async def release(
        self,
        key: str,
    ) -> None:
        self._controller.release(key)

    async def tap(
        self,
        key: str,
    ) -> None:
        self._controller.tap(key)

    # ==========================================================
    # Hotkeys
    # ==========================================================

    async def hotkey(
        self,
        *keys: str,
    ) -> None:
        self._controller.hotkey(*keys)

    # ==========================================================
    # State
    # ==========================================================

    async def is_pressed(
        self,
        key: str,
    ) -> bool:
        return self._controller.is_pressed(key)