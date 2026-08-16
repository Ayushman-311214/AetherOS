from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ProcessController(ABC):
    """
    Abstract interface for process management.

    Every implementation (psutil, subprocess, Win32 API, etc.)
    must implement this interface.
    """

    # ==========================================================
    # Process Creation
    # ==========================================================

    @abstractmethod
    def start(
        self,
        command: str | list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> int:
        """
        Start a new process.

        Returns:
            Process ID (PID)
        """
        ...

    @abstractmethod
    def open_file(
        self,
        path: str | Path,
    ) -> int:
        """
        Open a file with its default application.

        Returns:
            Process ID if available.
        """
        ...

    @abstractmethod
    def open_url(
        self,
        url: str,
    ) -> int:
        """
        Open a URL in the default browser.
        """
        ...

    # ==========================================================
    # Process Discovery
    # ==========================================================

    @abstractmethod
    def list_processes(self) -> list[Any]:
        """
        Returns all running processes.
        """
        ...

    @abstractmethod
    def find_by_pid(
        self,
        pid: int,
    ) -> Any | None:
        """
        Find a process by PID.
        """
        ...

    @abstractmethod
    def find_by_name(
        self,
        name: str,
    ) -> list[Any]:
        """
        Find processes by executable name.
        """
        ...

    # ==========================================================
    # Process Control
    # ==========================================================

    @abstractmethod
    def terminate(
        self,
        pid: int,
    ) -> None:
        """
        Gracefully terminate a process.
        """
        ...

    @abstractmethod
    def kill(
        self,
        pid: int,
    ) -> None:
        """
        Force kill a process.
        """
        ...

    @abstractmethod
    def restart(
        self,
        pid: int,
    ) -> int:
        """
        Restart a process.

        Returns:
            New PID.
        """
        ...

    # ==========================================================
    # Process Information
    # ==========================================================

    @abstractmethod
    def exists(
        self,
        pid: int,
    ) -> bool:
        """
        Returns True if process exists.
        """
        ...

    @abstractmethod
    def is_running(
        self,
        pid: int,
    ) -> bool:
        """
        Returns True if process is running.
        """
        ...

    @abstractmethod
    def wait(
        self,
        pid: int,
        timeout: float | None = None,
    ) -> None:
        """
        Wait for a process to exit.
        """
        ...

    @abstractmethod
    def info(
        self,
        pid: int,
    ) -> dict[str, Any]:
        """
        Returns process information.

        Example:
            name
            pid
            cpu_percent
            memory_usage
            executable
            status
        """
        ...