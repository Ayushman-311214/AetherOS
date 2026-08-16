from __future__ import annotations

from core.logging import get_logger
from browser.providers.base import BrowserProvider


class BrowserService:
    """
    High-level browser service.

    Responsible for coordinating browser operations.
    Delegates all browser interactions to the configured
    BrowserProvider implementation.
    """

    def __init__(
        self,
        provider: BrowserProvider,
    ) -> None:

        self._provider = provider
        self._logger = get_logger("browser")

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def launch(
        self,
        *,
        headless: bool = False,
    ) -> None:

        self._logger.info("Launching browser.")

        await self._provider.launch(
            headless=headless,
        )

    async def close(self) -> None:

        self._logger.info("Closing browser.")

        await self._provider.close()

    # ==========================================================
    # Navigation
    # ==========================================================

    async def goto(
        self,
        url: str,
    ) -> None:

        self._logger.info(
            "Navigating to %s",
            url,
        )

        await self._provider.goto(url)

    async def back(self) -> None:
        await self._provider.back()

    async def forward(self) -> None:
        await self._provider.forward()

    async def reload(self) -> None:
        await self._provider.reload()

    async def wait_for_load(self) -> None:
        await self._provider.wait_for_load()

    # ==========================================================
    # DOM
    # ==========================================================

    async def click(
        self,
        selector: str,
    ) -> None:

        await self._provider.click(selector)

    async def fill(
        self,
        selector: str,
        text: str,
    ) -> None:

        await self._provider.fill(
            selector,
            text,
        )

    async def press(
        self,
        selector: str,
        key: str,
    ) -> None:

        await self._provider.press(
            selector,
            key,
        )

    async def hover(
        self,
        selector: str,
    ) -> None:

        await self._provider.hover(selector)

    # ==========================================================
    # Information
    # ==========================================================

    async def title(self) -> str:
        return await self._provider.title()

    async def url(self) -> str:
        return await self._provider.url()

    async def html(self) -> str:
        return await self._provider.html()

    # ==========================================================
    # Screenshots
    # ==========================================================

    async def screenshot(
        self,
        path: str,
    ) -> None:

        await self._provider.screenshot(path)

    # ==========================================================
    # JavaScript
    # ==========================================================

    async def evaluate(
        self,
        script: str,
    ):

        return await self._provider.evaluate(script)