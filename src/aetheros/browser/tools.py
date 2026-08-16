from __future__ import annotations

from core.container import container
from tools import tool

from browser.controller import BrowserService


# ==========================================================
# Browser Lifecycle
# ==========================================================

@tool(
    category="browser",
    description="Launch a browser instance.",
)
async def open_browser(
    headless: bool = False,
) -> None:

    browser = container.resolve(BrowserService)

    await browser.launch(
        headless=headless,
    )


@tool(
    category="browser",
    description="Close the browser.",
)
async def close_browser() -> None:

    browser = container.resolve(BrowserService)

    await browser.close()


# ==========================================================
# Navigation
# ==========================================================

@tool(
    category="browser",
    description="Navigate to a URL.",
)
async def goto_url(
    url: str,
) -> None:

    browser = container.resolve(BrowserService)

    await browser.goto(url)


@tool(
    category="browser",
    description="Go back.",
)
async def browser_back() -> None:

    browser = container.resolve(BrowserService)

    await browser.back()


@tool(
    category="browser",
    description="Go forward.",
)
async def browser_forward() -> None:

    browser = container.resolve(BrowserService)

    await browser.forward()


@tool(
    category="browser",
    description="Reload the current page.",
)
async def browser_reload() -> None:

    browser = container.resolve(BrowserService)

    await browser.reload()


# ==========================================================
# DOM Actions
# ==========================================================

@tool(
    category="browser",
    description="Click an element using a CSS selector.",
)
async def click_element(
    selector: str,
) -> None:

    browser = container.resolve(BrowserService)

    await browser.click(selector)


@tool(
    category="browser",
    description="Fill an input element.",
)
async def fill_input(
    selector: str,
    text: str,
) -> None:

    browser = container.resolve(BrowserService)

    await browser.fill(
        selector,
        text,
    )


@tool(
    category="browser",
    description="Hover over an element.",
)
async def hover_element(
    selector: str,
) -> None:

    browser = container.resolve(BrowserService)

    await browser.hover(selector)


# ==========================================================
# Information
# ==========================================================

@tool(
    category="browser",
    description="Get the page title.",
)
async def page_title() -> str:

    browser = container.resolve(BrowserService)

    return await browser.title()


@tool(
    category="browser",
    description="Get the current URL.",
)
async def current_url() -> str:

    browser = container.resolve(BrowserService)

    return await browser.url()


@tool(
    category="browser",
    description="Get the HTML source.",
)
async def page_html() -> str:

    browser = container.resolve(BrowserService)

    return await browser.html()


# ==========================================================
# Screenshot
# ==========================================================

@tool(
    category="browser",
    description="Take a browser screenshot.",
)
async def browser_screenshot(
    path: str,
) -> str:

    browser = container.resolve(BrowserService)

    await browser.screenshot(path)

    return path


# ==========================================================
# JavaScript
# ==========================================================

@tool(
    category="browser",
    description="Execute JavaScript.",
)
async def execute_javascript(
    script: str,
):

    browser = container.resolve(BrowserService)

    return await browser.evaluate(script)