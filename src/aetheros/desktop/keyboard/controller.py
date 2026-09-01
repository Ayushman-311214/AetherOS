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

    The method names mirror ``KeyboardController`` deliberately. An earlier
    version exposed ``release()`` and ``tap()``, which no interface method
    matched: ``release()`` called a backend method that does not exist, so the
    registered ``key_up`` tool raised AttributeError on every call, and
    ``tap()`` reached a method PyAutoGUI's backend happened to define outside the
    contract -- meaning it worked only by luck and would break under any other
    backend.
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
        # bind(), not %-style args: loguru formats with str.format, so "%d" was
        # emitted literally and the length was dropped. The text itself is never
        # logged -- it routinely carries passwords and API keys.
        self._logger.bind(
            characters=len(text),
        ).debug("Typing text.")

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
        """
        Press and release a key.
        """

        self._controller.press(key)

    async def press_many(
        self,
        keys: list[str],
    ) -> None:
        """
        Press and release several keys, one after another.

        Not a shortcut -- use ``hotkey`` for keys held together.
        """

        self._controller.press_many(keys)

    async def key_down(
        self,
        key: str,
    ) -> None:
        """
        Hold a key down until ``key_up`` releases it.
        """

        self._logger.bind(key=key).debug("Holding key.")

        self._controller.key_down(key)

    async def key_up(
        self,
        key: str,
    ) -> None:
        """
        Release a held key.
        """

        self._logger.bind(key=key).debug("Releasing key.")

        self._controller.key_up(key)

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

    async def clear_modifiers(self) -> None:
        """
        Release every modifier key.

        Worth exposing on its own: a workflow that fails between ``key_down``
        and ``key_up`` leaves a modifier stuck, and from then on every keystroke
        the machine receives is silently wrong. This is the recovery path for
        that, and it is safe to call when nothing is held.
        """

        self._logger.debug("Releasing all modifier keys.")

        self._controller.clear_modifiers()
