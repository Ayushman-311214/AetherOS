from __future__ import annotations

from ..core.logging import get_logger
from .providers.base import BrowserProvider


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

        # Tracked so shutdown can tell "never launched" from "still open" without
        # asking the provider, which raises once its page is gone.
        self._launched = False

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

        self._launched = True

    async def close(self) -> None:

        self._logger.info("Closing browser.")

        await self._provider.close()

        self._launched = False

    async def shutdown(self) -> None:
        """
        Release the browser if one is still open.

        Called from ``Bootstrapper._shutdown_browser``. Without it a session that
        called ``open_browser`` and never ``close_browser`` left a Chromium
        process and its user-data directory behind after the application exited.
        """

        if not self._launched:
            return

        try:
            await self.close()

        except Exception:
            # Shutdown continues regardless: a browser that refuses to close
            # must not stop the remaining subsystems from tearing down. Logged
            # rather than swallowed, so the leaked process is diagnosable.
            self._logger.exception(
                "Browser did not close cleanly during shutdown."
            )

    # ==========================================================
    # Navigation
    # ==========================================================

    async def goto(
        self,
        url: str,
    ) -> None:

        # bind(), not %-style args: loguru formats with str.format, so
        # logger.info("Navigating to %s", url) silently dropped the url.
        self._logger.bind(url=url).info("Navigating.")

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

    async def text(
        self,
        selector: str,
    ) -> str:

        return await self._provider.text(selector)

    # ==========================================================
    # Waiting
    # ==========================================================

    async def wait_for_selector(
        self,
        selector: str,
    ) -> None:

        await self._provider.wait_for_selector(selector)

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