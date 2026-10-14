from __future__ import annotations

from typing import Any

from ...core.container import container
from ...tools import tool

from .controller import ScreenService


# ==========================================================
# Internal helpers
# ==========================================================

def _screen() -> ScreenService:

    return container.resolve(ScreenService)


def _describe(
    image: Any,
    **extra: Any,
) -> dict[str, Any]:
    """
    Summarise a captured frame.

    A capture is a multi-megabyte pixel array. Tool results are JSON-encoded for
    the model, so returning the array itself produced an unusable wall of text
    and no dimensions; the frame's shape is the part a caller can act on. Use
    ``save_screenshot`` when the pixels themselves are the product.
    """

    height, width = image.shape[:2]

    return {
        "width": int(width),
        "height": int(height),
        "channels": int(image.shape[2]) if image.ndim == 3 else 1,
        "color_space": "bgr",
        **extra,
    }


# ==========================================================
# Screen Capture
# ==========================================================

@tool(
    category="desktop.screen",
    description=(
        "Capture the primary monitor and report the frame's dimensions. "
        "Use save_screenshot to write the image to disk."
    ),
)
async def capture_screen() -> dict[str, Any]:

    return _describe(
        await _screen().capture()
    )


@tool(
    category="desktop.screen",
    description="Capture a region of the screen and report its dimensions.",
)
async def capture_region(
    left: int,
    top: int,
    width: int,
    height: int,
) -> dict[str, Any]:

    frame = await _screen().capture_region(
        left=left,
        top=top,
        width=width,
        height=height,
    )

    return _describe(
        frame,
        left=left,
        top=top,
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
) -> dict[str, Any]:

    screen = _screen()

    frame = await screen.capture()

    await screen.save(
        image=frame,
        path=path,
    )

    return _describe(frame, path=path)


@tool(
    category="desktop.screen",
    description=(
        "Capture a rectangular region of the screen and save it to the given "
        "path. Use this instead of save_screenshot when only part of the "
        "screen matters, such as a single chart panel."
    ),
)
async def save_region_screenshot(
    path: str,
    left: int,
    top: int,
    width: int,
    height: int,
) -> dict[str, Any]:

    screen = _screen()

    frame = await screen.capture_region(
        left=left,
        top=top,
        width=width,
        height=height,
    )

    await screen.save(
        image=frame,
        path=path,
    )

    return _describe(
        frame,
        path=path,
        left=left,
        top=top,
    )


# ==========================================================
# Information
# ==========================================================

@tool(
    category="desktop.screen",
    description="Get the primary monitor size."
)
async def screen_size() -> dict[str, int]:

    width, height = await _screen().size()

    return {
        "width": width,
        "height": height,
    }


@tool(
    category="desktop.screen",
    description="List all connected monitors."
)
async def list_monitors() -> list[dict[str, Any]]:

    return await _screen().monitors()
