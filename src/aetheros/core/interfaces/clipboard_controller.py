from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ClipboardController(ABC):
    """
    Abstract interface for clipboard operations.

    Every clipboard implementation (Pyperclip, Win32 API, etc.)
    must implement this interface.
    """

    # ==========================================================
    # Text
    # ==========================================================

    @abstractmethod
    def copy_text(
        self,
        text: str,
    ) -> None:
        """
        Copy text to the clipboard.
        """
        ...

    @abstractmethod
    def paste_text(self) -> str:
        """
        Returns clipboard text.
        """
        ...

    # ==========================================================
    # Images
    # ==========================================================

    @abstractmethod
    def copy_image(
        self,
        image: Any,
    ) -> None:
        """
        Copy an image to the clipboard.
        """
        ...

    @abstractmethod
    def paste_image(self) -> Any | None:
        """
        Returns an image from the clipboard.

        Returns:
            None if clipboard doesn't contain an image.
        """
        ...

    # ==========================================================
    # Files
    # ==========================================================

    @abstractmethod
    def copy_files(
        self,
        paths: list[str | Path],
    ) -> None:
        """
        Copy one or more files/folders to the clipboard.
        """
        ...

    @abstractmethod
    def paste_files(self) -> list[Path]:
        """
        Returns copied file paths.

        Returns:
            Empty list if clipboard contains no files.
        """
        ...

    # ==========================================================
    # Clipboard State
    # ==========================================================

    @abstractmethod
    def clear(self) -> None:
        """
        Clear the clipboard.
        """
        ...

    @abstractmethod
    def has_text(self) -> bool:
        """
        Returns True if clipboard contains text.
        """
        ...

    @abstractmethod
    def has_image(self) -> bool:
        """
        Returns True if clipboard contains an image.
        """
        ...

    @abstractmethod
    def has_files(self) -> bool:
        """
        Returns True if clipboard contains files.
        """
        ...

    @abstractmethod
    def is_empty(self) -> bool:
        """
        Returns True if clipboard is empty.
        """
        ...

    # ==========================================================
    # Utilities
    # ==========================================================

    @abstractmethod
    def get_content_type(self) -> str:
        """
        Returns the clipboard content type.

        Examples:
            "text"
            "image"
            "files"
            "empty"
            "unknown"
        """
        ...