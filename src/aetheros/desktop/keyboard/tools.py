from __future__ import annotations

print("[DEBUG KEYBOARD TOOLS] IMPORT START")
from ...core.container import container
from ...tools import tool

from .controller import KeyboardService

print("[DEBUG KEYBOARD TOOLS] CORE IMPORTS OK")

# ==========================================================
# Typing
# ==========================================================
@tool(
    category="desktop.keyboard",
    description="Type text using the keyboard."
)
async def type_text(
    text: str,
    interval: float = 0.0,
) -> None:
    print("[DEBUG KEYBOARD TOOLS] type_text registered")

    keyboard = container.resolve(KeyboardService)

    await keyboard.write(
        text=text,
        interval=interval,
    )


# ==========================================================
# Key Press
# ==========================================================

@tool(
    category="desktop.keyboard",
    description="Press and hold a keyboard key."
)
async def key_down(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.press(key)


@tool(
    category="desktop.keyboard",
    description="Release a keyboard key."
)
async def key_up(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.release(key)


@tool(
    category="desktop.keyboard",
    description="Press a keyboard key."
)
async def press_key(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.tap(key)


# ==========================================================
# Hotkeys
# ==========================================================

@tool(
    category="desktop.keyboard",
    description="Execute a keyboard shortcut."
)
async def hotkey(
    keys: list[str],
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.hotkey(*keys)

print("[DEBUG KEYBOARD TOOLS] IMPORT END")