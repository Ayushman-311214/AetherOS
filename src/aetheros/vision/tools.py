from __future__ import annotations

from ..core.container import container
from ..tools import tool

from ..desktop.screen.controller import ScreenService
from .controller import VisionService


# ==========================================================
# OCR
# ==========================================================

@tool(
    category="vision",
    description="Read all visible text from the current screen.",
)
async def read_screen_text():

    screen = container.resolve(ScreenService)
    vision = container.resolve(VisionService)

    image = await screen.capture()

    return await vision.read_text(image)


# ==========================================================
# Object Detection
# ==========================================================

@tool(
    category="vision",
    description="Detect visible objects on the current screen.",
)
async def detect_screen_objects():

    screen = container.resolve(ScreenService)
    vision = container.resolve(VisionService)

    image = await screen.capture()

    return await vision.detect_objects(image)


# ==========================================================
# Find Text
# ==========================================================

@tool(
    category="vision",
    description="Find text on the screen.",
)
async def find_text(
    query: str,
):

    screen = container.resolve(ScreenService)
    vision = container.resolve(VisionService)

    image = await screen.capture()

    blocks = await vision.read_text(image)

    return [
        block
        for block in blocks
        if query.lower() in block.text.lower()
    ]


# ==========================================================
# Capture Screen
# ==========================================================

@tool(
    category="vision",
    description="Capture the current screen.",
)
async def capture_screen():

    screen = container.resolve(ScreenService)

    return await screen.capture()


# ==========================================================
# Analyze Screen
# ==========================================================

@tool(
    category="vision",
    description="Capture the screen and return OCR and object detection results.",
)
async def analyze_screen():

    screen = container.resolve(ScreenService)
    vision = container.resolve(VisionService)

    image = await screen.capture()

    return {
        "text": await vision.read_text(image),
        "objects": await vision.detect_objects(image),
    }