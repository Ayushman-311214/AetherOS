from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from browser.providers.base import BrowserProvider


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
    # Internal
    # ==========================================================

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser has not been launched.")
        return self._page

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

        self._page = await self._context.new_page()

    async def pages(self):

        return self._context.pages

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