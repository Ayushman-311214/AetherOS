from __future__ import annotations

from pathlib import Path
from typing import Any

import pyperclip

from ...core.interfaces.clipboard_controller import ClipboardController


class PyAutoGuiClipboard(ClipboardController):
    """
    Clipboard backend.

    Text operations are implemented using pyperclip.

    Image and file operations are intentionally unsupported
    in this backend and should be implemented by a Windows/
    Win32 clipboard backend later.
    """

    def __init__(self) -> None:
        pass

    # ==========================================================
    # Text
    # ==========================================================

    def copy_text(
        self,
        text: str,
    ) -> None:
        pyperclip.copy(text)

    def paste_text(self) -> str:
        return pyperclip.paste()

    # ==========================================================
    # Images
    # ==========================================================

    def copy_image(
        self,
        image: Any,
    ) -> None:
        raise NotImplementedError(
            "Image clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    def paste_image(self) -> Any | None:
        raise NotImplementedError(
            "Image clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    # ==========================================================
    # Files
    # ==========================================================

    def copy_files(
        self,
        paths: list[str | Path],
    ) -> None:
        raise NotImplementedError(
            "File clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    def paste_files(self) -> list[Path]:
        raise NotImplementedError(
            "File clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    # ==========================================================
    # Clipboard State
    # ==========================================================

    def clear(self) -> None:
        pyperclip.copy("")

    def has_text(self) -> bool:
        return bool(pyperclip.paste())

    def has_image(self) -> bool:
        return False

    def has_files(self) -> bool:
        return False

    def is_empty(self) -> bool:
        return not bool(pyperclip.paste())

    # ==========================================================
    # Utilities
    # ==========================================================

    def get_content_type(self) -> str:
        if self.has_text():
            return "text"

        return "empty"