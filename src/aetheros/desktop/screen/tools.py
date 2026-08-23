from __future__ import annotations

from ...core.container import container
from ...tools import tool

from .controller import ScreenService


# ==========================================================
# Screen Capture
# ==========================================================

@tool(
    category="desktop.screen",
    description="Capture the primary monitor."
)
async def capture_screen():

    screen = container.resolve(ScreenService)

    return await screen.capture()


@tool(
    category="desktop.screen",
    description="Capture a region of the screen."
)
async def capture_region(
    left: int,
    top: int,
    width: int,
    height: int,
):

    screen = container.resolve(ScreenService)

    return await screen.capture_region(
        left=left,
        top=top,
        width=width,
        height=height,
    )


# ==========================================================
# Save
# ==========================================================

@tool(
    category="desktop.screen",
    description="Capture and save a screenshot."
)
async def save_screenshot(
    path: str,
) -> str:

    screen = container.resolve(ScreenService)

    image = await screen.capture()

    await screen.save(
        image=image,
        path=path,
    )

    return path


# ==========================================================
# Information
# ==========================================================

@tool(
    category="desktop.screen",
    description="Get the primary monitor size."
)
async def screen_size():

    screen = container.resolve(ScreenService)

    width, height = await screen.size()

    return {
        "width": width,
        "height": height,
    }


@tool(
    category="desktop.screen",
    description="List all connected monitors."
)
async def list_monitors():

    screen = container.resolve(ScreenService)

    return await screen.monitors()