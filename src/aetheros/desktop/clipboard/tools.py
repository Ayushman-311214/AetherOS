from __future__ import annotations

from pathlib import Path
from typing import Any

from ...core.container import container
from ...tools import tool

from .controller import ClipboardService


# ==========================================================
# Text
# ==========================================================

@tool(
    category="desktop.clipboard",
    description="Copy text to the system clipboard.",
)
async def copy_text(
    text: str,
) -> None:

    clipboard = container.resolve(
        ClipboardService
    )

    await clipboard.copy_text(
        text=text,
    )


@tool(
    category="desktop.clipboard",
    description="Get text from the system clipboard.",
)
async def paste_text() -> str:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.paste_text()


# ==========================================================
# Images
# ==========================================================

@tool(
    category="desktop.clipboard",
    description="Copy an image to the system clipboard.",
)
async def copy_image(
    image: Any,
) -> None:

    clipboard = container.resolve(
        ClipboardService
    )

    await clipboard.copy_image(
        image=image,
    )


@tool(
    category="desktop.clipboard",
    description="Get an image from the system clipboard.",
)
async def paste_image() -> Any | None:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.paste_image()


# ==========================================================
# Files
# ==========================================================

@tool(
    category="desktop.clipboard",
    description="Copy files or folders to the system clipboard.",
)
async def copy_files(
    paths: list[str],
) -> None:

    clipboard = container.resolve(
        ClipboardService
    )

    await clipboard.copy_files(
        paths=paths,
    )


@tool(
    category="desktop.clipboard",
    description="Get file paths from the system clipboard.",
)
async def paste_files() -> list[str]:

    clipboard = container.resolve(
        ClipboardService
    )

    paths = await clipboard.paste_files()

    return [
        str(path)
        for path in paths
    ]


# ==========================================================
# Clipboard State
# ==========================================================

@tool(
    category="desktop.clipboard",
    description="Clear the system clipboard.",
)
async def clear_clipboard() -> None:

    clipboard = container.resolve(
        ClipboardService
    )

    await clipboard.clear()


@tool(
    category="desktop.clipboard",
    description="Check whether the clipboard contains text.",
)
async def has_text() -> bool:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.has_text()


@tool(
    category="desktop.clipboard",
    description="Check whether the clipboard contains an image.",
)
async def has_image() -> bool:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.has_image()


@tool(
    category="desktop.clipboard",
    description="Check whether the clipboard contains files.",
)
async def has_files() -> bool:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.has_files()


@tool(
    category="desktop.clipboard",
    description="Check whether the clipboard is empty.",
)
async def is_empty() -> bool:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.is_empty()


# ==========================================================
# Utilities
# ==========================================================

@tool(
    category="desktop.clipboard",
    description="Get the current clipboard content type.",
)
async def get_content_type() -> str:

    clipboard = container.resolve(
        ClipboardService
    )

    return await clipboard.get_content_type()