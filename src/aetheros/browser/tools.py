from __future__ import annotations

from typing import Any

from ..core.container import container
from ..core.errors.browser_error import BrowserError
from ..tools import tool

from .controller import BrowserService


# ==========================================================
# Internal helpers
# ==========================================================

def _browser() -> BrowserService:
    """
    Resolve the browser service, or explain why it is missing.

    The container raises ``KeyError: Service '<class ...BrowserService>' is not
    registered``, which tells an agent nothing it can act on. Playwright being an
    optional extra is the one realistic reason for that, so it becomes a domain
    error carrying the install command.
    """

    try:
        return container.resolve(BrowserService)

    except KeyError as exc:
        raise BrowserError(
            code="UNAVAILABLE",
            message="Browser automation is not available in this environment.",
            hint=(
                "Install the browser extra and its runtime: "
                "pip install aetheros[browser] && playwright install chromium"
            ),
            cause=exc,
        ) from exc


# ==========================================================
# Browser Lifecycle
# ==========================================================

@tool(
    category="browser",
    description=(
        "Launch a browser instance. Must be called before any other browser "
        "tool. Set headless to true to run without a visible window."
    ),
)
async def open_browser(
    headless: bool = False,
) -> None:

    await _browser().launch(
        headless=headless,
    )


@tool(
    category="browser",
    description="Close the browser and release its process.",
)
async def close_browser() -> None:

    await _browser().close()


# ==========================================================
# Navigation
# ==========================================================

@tool(
    category="browser",
    description="Navigate to a URL. Requires open_browser first.",
)
async def goto_url(
    url: str,
) -> None:

    await _browser().goto(url)


@tool(
    category="browser",
    description="Go back to the previous page in the browser history.",
)
async def browser_back() -> None:

    await _browser().back()


@tool(
    category="browser",
    description="Go forward to the next page in the browser history.",
)
async def browser_forward() -> None:

    await _browser().forward()


@tool(
    category="browser",
    description="Reload the current page.",
)
async def browser_reload() -> None:

    await _browser().reload()


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

    await _browser().click(selector)


@tool(
    category="browser",
    description=(
        "Replace the contents of an input element with the given text, "
        "addressed by CSS selector."
    ),
)
async def fill_input(
    selector: str,
    text: str,
) -> None:

    await _browser().fill(
        selector,
        text,
    )


@tool(
    category="browser",
    description="Hover the pointer over an element, addressed by CSS selector.",
)
async def hover_element(
    selector: str,
) -> None:

    await _browser().hover(selector)


# ==========================================================
# Information
# ==========================================================

@tool(
    category="browser",
    description="Get the title of the current page.",
)
async def page_title() -> str:

    return await _browser().title()


@tool(
    category="browser",
    description="Get the URL of the current page.",
)
async def current_url() -> str:

    return await _browser().url()


@tool(
    category="browser",
    description=(
        "Get the full HTML source of the current page. This can be very large; "
        "prefer element_text when only one element's content is needed."
    ),
)
async def page_html() -> str:

    return await _browser().html()


@tool(
    category="browser",
    description=(
        "Get the visible text of a single element, addressed by CSS selector. "
        "Cheaper and more focused than page_html."
    ),
)
async def element_text(
    selector: str,
) -> str:

    return await _browser().text(selector)


# ==========================================================
# Waiting
# ==========================================================

@tool(
    category="browser",
    description=(
        "Wait until an element matching the CSS selector appears on the page. "
        "Use this after a navigation or click instead of a fixed delay."
    ),
)
async def wait_for_element(
    selector: str,
) -> None:

    await _browser().wait_for_selector(selector)


# ==========================================================
# Screenshot
# ==========================================================

@tool(
    category="browser",
    description="Save a full-page screenshot of the browser to the given path.",
)
async def browser_screenshot(
    path: str,
) -> str:

    await _browser().screenshot(path)

    return path


# ==========================================================
# JavaScript
# ==========================================================

@tool(
    category="browser",
    description=(
        "Evaluate a JavaScript expression in the current page and return its "
        "result. The script runs with the page's full privileges, including any "
        "logged-in session, so prefer the dedicated click, fill and text tools "
        "for ordinary interaction."
    ),
)
async def execute_javascript(
    script: str,
) -> Any:

    return await _browser().evaluate(script)
