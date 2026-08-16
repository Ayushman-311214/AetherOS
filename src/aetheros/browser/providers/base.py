from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BrowserProvider(ABC):
    """
    Abstract interface for browser automation backends.

    The rest of AetherOS depends on this interface rather than
    directly depending on Playwright, Selenium, CDP, etc.
    """

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the provider version."""
        raise NotImplementedError

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def launch(
        self,
        *,
        headless: bool = False,
    ) -> None:
        """Launch the browser."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the browser and release resources."""
        raise NotImplementedError

    # ==========================================================
    # Navigation
    # ==========================================================

    @abstractmethod
    async def goto(
        self,
        url: str,
    ) -> None:
        """Navigate to a URL."""
        raise NotImplementedError

    @abstractmethod
    async def back(self) -> None:
        """Navigate back."""
        raise NotImplementedError

    @abstractmethod
    async def forward(self) -> None:
        """Navigate forward."""
        raise NotImplementedError

    @abstractmethod
    async def reload(self) -> None:
        """Reload the current page."""
        raise NotImplementedError

    @abstractmethod
    async def wait_for_load(self) -> None:
        """Wait until the page finishes loading."""
        raise NotImplementedError

    # ==========================================================
    # DOM Interaction
    # ==========================================================

    @abstractmethod
    async def click(
        self,
        selector: str,
    ) -> None:
        """Click an element."""
        raise NotImplementedError

    @abstractmethod
    async def fill(
        self,
        selector: str,
        text: str,
    ) -> None:
        """Fill an input element."""
        raise NotImplementedError

    @abstractmethod
    async def press(
        self,
        selector: str,
        key: str,
    ) -> None:
        """Press a keyboard key on an element."""
        raise NotImplementedError

    @abstractmethod
    async def hover(
        self,
        selector: str,
    ) -> None:
        """Hover over an element."""
        raise NotImplementedError

    @abstractmethod
    async def text(
        self,
        selector: str,
    ) -> str:
        """Return the text content of an element."""
        raise NotImplementedError

    # ==========================================================
    # Page Information
    # ==========================================================

    @abstractmethod
    async def title(self) -> str:
        """Return the current page title."""
        raise NotImplementedError

    @abstractmethod
    async def url(self) -> str:
        """Return the current page URL."""
        raise NotImplementedError

    @abstractmethod
    async def html(self) -> str:
        """Return the current page HTML."""
        raise NotImplementedError

    # ==========================================================
    # Screenshots
    # ==========================================================

    @abstractmethod
    async def screenshot(
        self,
        path: str | Path,
    ) -> None:
        """Capture a screenshot of the current page."""
        raise NotImplementedError

    @abstractmethod
    async def element_screenshot(
        self,
        selector: str,
        path: str | Path,
    ) -> None:
        """Capture a screenshot of a specific element."""
        raise NotImplementedError

    # ==========================================================
    # JavaScript
    # ==========================================================

    @abstractmethod
    async def evaluate(
        self,
        script: str,
    ) -> Any:
        """Execute JavaScript in the current page."""
        raise NotImplementedError

    # ==========================================================
    # Waiting
    # ==========================================================

    @abstractmethod
    async def wait_for_selector(
        self,
        selector: str,
    ) -> None:
        """Wait until an element appears."""
        raise NotImplementedError

    @abstractmethod
    async def wait(
        self,
        milliseconds: int,
    ) -> None:
        """Wait for a specified amount of time."""
        raise NotImplementedError

    # ==========================================================
    # Tabs
    # ==========================================================

    @abstractmethod
    async def new_tab(self) -> None:
        """Create a new browser tab."""
        raise NotImplementedError

    @abstractmethod
    async def pages(self) -> list[Any]:
        """Return currently available browser pages."""
        raise NotImplementedError

    # ==========================================================
    # Downloads
    # ==========================================================

    @abstractmethod
    async def download(
        self,
        selector: str,
        path: str | Path,
    ) -> None:
        """Click a download element and save the resulting file."""
        raise NotImplementedError