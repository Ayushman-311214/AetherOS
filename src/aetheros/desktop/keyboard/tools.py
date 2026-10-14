from __future__ import annotations

from ...core.container import container
from ...tools import tool

from .controller import KeyboardService


# ==========================================================
# Typing
# ==========================================================
@tool(
    category="desktop.keyboard",
    description=(
        "Type a string of text at the current cursor position, as if typed on "
        "the keyboard. The target field must already have focus. Use this for "
        "literal text; use press_key for named keys such as Enter or Tab, and "
        "hotkey for shortcuts. Set 'interval' to slow the typing down for "
        "interfaces that drop fast input."
    ),
)
async def type_text(
    text: str,
    interval: float = 0.0,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.write(
        text=text,
        interval=interval,
    )


@tool(
    category="desktop.keyboard",
    description=(
        "Clear the focused text field by selecting all of its content and "
        "deleting it. Use this before typing a replacement value, rather than "
        "pressing Backspace repeatedly. This affects only the focused field, but "
        "note that it selects all content in that field, so it will discard text "
        "that was already there."
    ),
)
async def clear_input() -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.hotkey("ctrl", "a")
    await keyboard.press("delete")


# ==========================================================
# Key Press
# ==========================================================


@tool(
    category="desktop.keyboard",
    description=(
        "Press a single key and release it immediately. Use this for named keys "
        "-- enter, tab, escape, backspace, delete, up, down, left, right, home, "
        "end, pageup, pagedown, f1 through f12 -- and for single characters. For "
        "a key combination use hotkey instead."
    ),
)
async def press_key(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.press(key)


@tool(
    category="desktop.keyboard",
    description=(
        "Hold a key down and leave it held. The key stays down until key_up "
        "releases it, so every following keystroke is modified by it. Only use "
        "this for a sequence that genuinely needs a held key, such as shift-"
        "clicking a range; for an ordinary shortcut use hotkey, which handles "
        "the release for you. Always pair this with key_up: a modifier left "
        "held corrupts all later input."
    ),
)
async def key_down(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.key_down(key)


@tool(
    category="desktop.keyboard",
    description=(
        "Release a key that key_down is holding. Safe to call when the key is "
        "not held -- it does nothing in that case."
    ),
)
async def key_up(
    key: str,
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.key_up(key)


@tool(
    category="desktop.keyboard",
    description=(
        "Release every modifier key (Ctrl, Alt, Shift, Win, both left and "
        "right). Use this to recover after an interrupted key_down or hotkey: a "
        "modifier left stuck down silently changes every keystroke that follows, "
        "so typing appears to work while producing the wrong result. Safe to "
        "call at any time, and safe when nothing is held."
    ),
)
async def clear_modifiers() -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.clear_modifiers()


# ==========================================================
# Hotkeys
# ==========================================================


@tool(
    category="desktop.keyboard",
    description=(
        "Press several keys together as a shortcut, then release them in "
        "reverse order. Give the keys in the order they are held, modifiers "
        "first: ['ctrl', 'c'] to copy, ['ctrl', 'shift', 's'] for save-as, "
        "['alt', 'tab'] to switch window, ['win', 'r'] for the Run dialog. This "
        "is the right tool for any shortcut -- prefer it over key_down/key_up, "
        "because it cannot leave a modifier stuck down."
    ),
)
async def hotkey(
    keys: list[str],
) -> None:

    keyboard = container.resolve(KeyboardService)

    await keyboard.hotkey(*keys)
