from __future__ import annotations

from ...tools import tool
from ...core.container import container

from .controller import MouseService


# ==========================================================
# Movement
# ==========================================================

@tool(
    category="desktop.mouse",
    description=(
        "Move the mouse cursor to an absolute screen position, where (0, 0) is "
        "the top-left corner of the primary monitor. Use move_relative to "
        "shift the cursor by an offset instead."
    ),
)
async def move_mouse(
    x: int,
    y: int,
    duration: float = 0.0,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.move(
        x=x,
        y=y,
        duration=duration,
    )


@tool(
    category="desktop.mouse",
    description=(
        "Move the mouse cursor by an offset from its current position. "
        "Positive dx moves right, positive dy moves down."
    ),
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
# Button State
# ==========================================================

@tool(
    category="desktop.mouse",
    description=(
        "Press a mouse button and leave it held down at the current position. "
        "The button stays down until mouse_up releases it. Use this to build a "
        "press-move-release sequence that drag_to cannot express -- selecting a "
        "range of text, dragging a scrollbar, drawing a path through several "
        "points. For a straight drag between two points, prefer drag_to. Always "
        "pair this with mouse_up: a button left held makes every later move a "
        "drag. 'button' is 'left', 'right' or 'middle'."
    ),
)
async def mouse_down(
    button: str = "left",
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.mouse_down(button=button)


@tool(
    category="desktop.mouse",
    description=(
        "Release a mouse button that mouse_down is holding, at the current "
        "position. 'button' is 'left', 'right' or 'middle', and must match the "
        "button that was pressed."
    ),
)
async def mouse_up(
    button: str = "left",
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.mouse_up(button=button)


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


@tool(
    category="desktop.mouse",
    description=(
        "Drag the mouse by an offset from wherever it currently is, holding a "
        "button down for the movement. Positive 'dx' moves right, positive 'dy' "
        "moves down. Use this when the distance matters but the destination "
        "coordinates are not known -- nudging a slider, resizing by a fixed "
        "amount. Use drag_to when you know the target position."
    ),
)
async def drag_relative(
    dx: int,
    dy: int,
    duration: float = 0.2,
    button: str = "left",
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.drag_relative(
        dx=dx,
        dy=dy,
        duration=duration,
        button=button,
    )


# ==========================================================
# Scroll
# ==========================================================

@tool(
    category="desktop.mouse",
    description=(
        "Scroll the mouse wheel vertically at the current pointer position. "
        "Positive 'amount' scrolls up, negative scrolls down; the unit is wheel "
        "clicks, so 3 is a small nudge and 15 is a page. Scrolling applies to "
        "whatever is under the pointer, so move the mouse over the target region "
        "first."
    ),
)
async def scroll(
    amount: int,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.scroll(amount)


@tool(
    category="desktop.mouse",
    description=(
        "Scroll horizontally at the current pointer position. Positive 'amount' "
        "scrolls right, negative scrolls left, in wheel clicks. Use this for wide "
        "tables, timelines and code that runs off the right edge. Not every "
        "application handles horizontal scroll -- verify the view actually moved "
        "rather than assuming it did."
    ),
)
async def horizontal_scroll(
    amount: int,
) -> None:

    mouse = container.resolve(MouseService)

    await mouse.hscroll(amount)


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