from __future__ import annotations

from ...core.container import container
from ...tools import tool

from .controller import ScreenshotService


@tool(
    category="desktop.screenshot",
    description="Capture the entire computer screen.",
)
async def screenshot_capture() -> str:

    screenshot = container.resolve(
        ScreenshotService
    )

    path = await screenshot.capture()

    return str(path)


@tool(
    category="desktop.screenshot",
    description="Capture a rectangular region of the computer screen.",
)
async def screenshot_region(
    x: int,
    y: int,
    width: int,
    height: int,
) -> str:

    screenshot = container.resolve(
        ScreenshotService
    )

    path = await screenshot.capture_region(
        x=x,
        y=y,
        width=width,
        height=height,
    )

    return str(path)


@tool(
    category="desktop.screenshot",
    description="Get the current screen width and height.",
)
async def screen_size() -> dict[str, int]:

    screenshot = container.resolve(
        ScreenshotService
    )

    width, height = (
        await screenshot.screen_size()
    )

    return {
        "width": width,
        "height": height,
    }