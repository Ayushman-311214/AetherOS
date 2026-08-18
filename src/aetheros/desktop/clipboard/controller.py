from __future__ import annotations

from pathlib import Path
from typing import Any

from ...core.interfaces.clipboard_controller import ClipboardController
from ...core.logging import get_logger


class ClipboardService:
    """
    High-level clipboard service.

    Delegates clipboard operations to the configured
    ClipboardController backend.
    """

    def __init__(
        self,
        controller: ClipboardController,
    ) -> None:
        self._controller = controller

        self._logger = get_logger("clipboard")

    # ==========================================================
    # Text
    # ==========================================================

    async def copy_text(
        self,
        text: str,
    ) -> None:
        self._logger.debug(
            "Copying text to clipboard."
        )

        self._controller.copy_text(
            text=text,
        )

    async def paste_text(self) -> str:
        self._logger.debug(
            "Reading text from clipboard."
        )

        return self._controller.paste_text()

    # ==========================================================
    # Images
    # ==========================================================

    async def copy_image(
        self,
        image: Any,
    ) -> None:
        self._logger.debug(
            "Copying image to clipboard."
        )

        self._controller.copy_image(
            image=image,
        )

    async def paste_image(self) -> Any | None:
        self._logger.debug(
            "Reading image from clipboard."
        )

        return self._controller.paste_image()

    # ==========================================================
    # Files
    # ==========================================================

    async def copy_files(
        self,
        paths: list[str | Path],
    ) -> None:
        self._logger.debug(
            "Copying %d file(s) to clipboard.",
            len(paths),
        )

        self._controller.copy_files(
            paths=paths,
        )

    async def paste_files(self) -> list[Path]:
        self._logger.debug(
            "Reading files from clipboard."
        )

        return self._controller.paste_files()

    # ==========================================================
    # Clipboard State
    # ==========================================================

    async def clear(self) -> None:
        self._logger.debug(
            "Clearing clipboard."
        )

        self._controller.clear()

    async def has_text(self) -> bool:
        return self._controller.has_text()

    async def has_image(self) -> bool:
        return self._controller.has_image()

    async def has_files(self) -> bool:
        return self._controller.has_files()

    async def is_empty(self) -> bool:
        return self._controller.is_empty()

    # ==========================================================
    # Utilities
    # ==========================================================

    async def get_content_type(self) -> str:
        return self._controller.get_content_type()