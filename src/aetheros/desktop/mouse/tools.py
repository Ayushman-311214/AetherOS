from __future__ import annotations

from ...tools import tool
from ...core.container import container

from .controller import MouseService


# ==========================================================
# Movement
# ==========================================================

@tool(
    category="desktop.mouse",
    description="Move the mouse cursor to an absolute screen position.",
)
async def move_mouse(
    dx: int,
    dy: int,
    duration: float = 0.0,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.move(
        dx=dx,
        dy=dy,
        duration=duration,
    )


@tool(
    category="desktop.mouse",
    description="Move the mouse cursor relative to its current position.",
)
async def move_relative(
    dx: int,
    dy: int,
    duration: float = 0.0,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.move_relative(
        dx=dx,
        dy=dy,
        duration=duration,
    )


# ==========================================================
# Clicks
# ==========================================================

@tool(
    category="desktop.mouse",
    description="Click a mouse button.",
)
async def click(
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.0,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.click(
        button=button,
        clicks=clicks,
        interval=interval,
    )


@tool(
    category="desktop.mouse",
    description="Double-click the mouse.",
)
async def double_click(
    button: str = "left",
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.double_click(
        button=button,
    )


@tool(
    category="desktop.mouse",
    description="Right-click the mouse.",
)
async def right_click() -> None:

    mouse = container.resolve(MouseService)

    await mouse.right_click()


@tool(
    category="desktop.mouse",
    description="Middle-click the mouse.",
)
async def middle_click() -> None:

    mouse = container.resolve(MouseService)

    await mouse.middle_click()


# ==========================================================
# Drag
# ==========================================================

@tool(
    category="desktop.mouse",
    description="Drag the mouse to a screen position.",
)
async def drag_to(
    x: int,
    y: int,
    duration: float = 0.2,
    button: str = "left",
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.drag_to(
        x=x,
        y=y,
        duration=duration,
        button=button,
    )


# ==========================================================
# Scroll
# ==========================================================

@tool(
    category="desktop.mouse",
    description="Scroll the mouse wheel vertically.",
)
async def scroll(
    amount: int,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.scroll(amount)


# ==========================================================
# Information
# ==========================================================

@tool(
    category="desktop.mouse",
    description="Get the current mouse position.",
)
async def mouse_position() -> dict[str, int]:

    mouse = container.resolve(MouseService)

    x, y = await mouse.position()

    return {
        "x": x,
        "y": y,
    }