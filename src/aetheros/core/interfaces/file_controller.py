from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class FileController(ABC):
    """
    Abstract interface for filesystem operations.

    Every implementation (pathlib, shutil, cloud storage, etc.)
    must implement this interface.
    """

    # ==========================================================
    # Create
    # ==========================================================

    @abstractmethod
    def create_file(
        self,
        path: str | Path,
        overwrite: bool = False,
    ) -> Path:
        """
        Create an empty file.
        """
        ...

    @abstractmethod
    def create_directory(
        self,
        path: str | Path,
        parents: bool = True,
        exist_ok: bool = True,
    ) -> Path:
        """
        Create a directory.
        """
        ...

    # ==========================================================
    # Read / Write
    # ==========================================================

    @abstractmethod
    def read_text(
        self,
        path: str | Path,
        encoding: str = "utf-8",
    ) -> str:
        """
        Read a text file.
        """
        ...

    @abstractmethod
    def write_text(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        """
        Write text to a file.
        """
        ...

    @abstractmethod
    def append_text(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        """
        Append text to a file.
        """
        ...

    @abstractmethod
    def read_bytes(
        self,
        path: str | Path,
    ) -> bytes:
        """
        Read binary data.
        """
        ...

    @abstractmethod
    def write_bytes(
        self,
        path: str | Path,
        data: bytes,
    ) -> None:
        """
        Write binary data.
        """
        ...

    # ==========================================================
    # Copy / Move
    # ==========================================================

    @abstractmethod
    def copy(
        self,
        source: str | Path,
        destination: str | Path,
    ) -> Path:
        """
        Copy a file or directory.
        """
        ...

    @abstractmethod
    def move(
        self,
        source: str | Path,
        destination: str | Path,
    ) -> Path:
        """
        Move a file or directory.
        """
        ...

    @abstractmethod
    def rename(
        self,
        source: str | Path,
        new_name: str,
    ) -> Path:
        """
        Rename a file or directory.
        """
        ...

    # ==========================================================
    # Delete
    # ==========================================================

    @abstractmethod
    def delete(
        self,
        path: str | Path,
        recursive: bool = False,
    ) -> None:
        """
        Delete a file or directory.
        """
        ...

    # ==========================================================
    # Search
    # ==========================================================

    @abstractmethod
    def exists(
        self,
        path: str | Path,
    ) -> bool:
        """
        Check if a path exists.
        """
        ...

    @abstractmethod
    def is_file(
        self,
        path: str | Path,
    ) -> bool:
        """
        Check if path is a file.
        """
        ...

    @abstractmethod
    def is_directory(
        self,
        path: str | Path,
    ) -> bool:
        """
        Check if path is a directory.
        """
        ...

    @abstractmethod
    def list_directory(
        self,
        path: str | Path,
    ) -> list[Path]:
        """
        List directory contents.
        """
        ...

    @abstractmethod
    def search(
        self,
        directory: str | Path,
        pattern: str,
        recursive: bool = True,
    ) -> list[Path]:
        """
        Search for files using a glob pattern.

        Example:
            "*.py"
            "*.json"
        """
        ...

    # ==========================================================
    # Metadata
    # ==========================================================

    @abstractmethod
    def info(
        self,
        path: str | Path,
    ) -> dict[str, Any]:
        """
        Return metadata about a file or directory.
        """
        ...

    @abstractmethod
    def size(
        self,
        path: str | Path,
    ) -> int:
        """
        Return file size in bytes.
        """
        ...