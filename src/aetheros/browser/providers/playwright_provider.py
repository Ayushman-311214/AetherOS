from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from .base import BrowserProvider


class PlaywrightProvider(BrowserProvider):
    """
    Playwright implementation of BrowserProvider.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ==========================================================
    # Provider information
    # ==========================================================

    @property
    def name(self) -> str:
        return "playwright"

    @property
    def version(self) -> str:
        """
        The installed Playwright version.

        Read from package metadata rather than hard-coded: a pinned string goes
        stale on the next upgrade, and this value ends up in audit logs where a
        wrong version is worse than no version.
        """

        try:
            return package_version("playwright")

        except PackageNotFoundError:
            # Importable but not installed as a distribution — a vendored or
            # editable checkout. The provider still works; only the version is
            # unknown, and saying so beats inventing a number.
            return "unknown"

    # ==========================================================
    # Internal
    # ==========================================================

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser has not been launched.")
        return self._page

    @property
    def _live_context(self) -> BrowserContext:
        """
        The browser context, or a diagnosable error.

        Reaching through ``self._context`` directly gives
        ``AttributeError: 'NoneType' object has no attribute 'new_page'``, which
        tells an agent nothing. This mirrors :attr:`page` so every entry point
        fails the same legible way.
        """

        if self._context is None:
            raise RuntimeError("Browser has not been launched.")

        return self._context

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def launch(
        self,
        *,
        headless: bool = False,
    ) -> None:

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
        )

        self._context = await self._browser.new_context()

        self._page = await self._context.new_page()

    async def close(self) -> None:

        if self._context:
            await self._context.close()

        if self._browser:
            await self._browser.close()

        if self._playwright:
            await self._playwright.stop()

        # Cleared, not just closed: leaving the handles set means `page` hands
        # back a dead Page, so the next tool call fails somewhere inside
        # Playwright instead of saying "Browser has not been launched." It also
        # makes close() idempotent, which shutdown relies on.
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    # ==========================================================
    # Navigation
    # ==========================================================

    async def goto(
        self,
        url: str,
    ) -> None:

        await self.page.goto(
            url,
            wait_until="networkidle",
        )

    async def back(self) -> None:
        await self.page.go_back()

    async def forward(self) -> None:
        await self.page.go_forward()

    async def reload(self) -> None:
        await self.page.reload()

    async def wait_for_load(self) -> None:
        await self.page.wait_for_load_state("networkidle")

    # ==========================================================
    # DOM
    # ==========================================================

    async def click(
        self,
        selector: str,
    ) -> None:

        await self.page.locator(selector).click()

    async def fill(
        self,
        selector: str,
        text: str,
    ) -> None:

        await self.page.locator(selector).fill(text)

    async def press(
        self,
        selector: str,
        key: str,
    ) -> None:

        await self.page.locator(selector).press(key)

    async def hover(
        self,
        selector: str,
    ) -> None:

        await self.page.locator(selector).hover()

    # ==========================================================
    # Information
    # ==========================================================

    async def title(self) -> str:
        return await self.page.title()

    async def url(self) -> str:
        return self.page.url

    async def html(self) -> str:
        return await self.page.content()

    async def text(
        self,
        selector: str,
    ) -> str:

        return await self.page.locator(selector).inner_text()

    # ==========================================================
    # Screenshots
    # ==========================================================

    async def screenshot(
        self,
        path: str | Path,
    ) -> None:

        await self.page.screenshot(
            path=str(path),
            full_page=True,
        )

    async def element_screenshot(
        self,
        selector: str,
        path: str | Path,
    ) -> None:

        await self.page.locator(selector).screenshot(
            path=str(path),
        )

    # ==========================================================
    # JavaScript
    # ==========================================================

    async def evaluate(
        self,
        script: str,
    ) -> Any:

        return await self.page.evaluate(script)

    # ==========================================================
    # Waiting
    # ==========================================================

    async def wait_for_selector(
        self,
        selector: str,
    ) -> None:

        await self.page.wait_for_selector(selector)

    async def wait(
        self,
        milliseconds: int,
    ) -> None:

        await self.page.wait_for_timeout(milliseconds)

    # ==========================================================
    # Tabs
    # ==========================================================

    async def new_tab(self) -> None:

        self._page = await self._live_context.new_page()

    async def pages(self) -> list[Any]:

        return list(self._live_context.pages)

    # ==========================================================
    # Downloads
    # ==========================================================

    async def download(
        self,
        selector: str,
        path: str | Path,
    ) -> None:

        async with self.page.expect_download() as download_info:

            await self.page.locator(selector).click()

        download = await download_info.value

        await download.save_as(str(path))