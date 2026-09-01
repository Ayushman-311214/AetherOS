from __future__ import annotations

from typing import Any

from ..config.config_loader import get_settings
from ..core.container import container
from ..tools import tool

from ..desktop.screen.controller import ScreenService
from .controller import VisionService
from .image import Image


# Every tool in this module is measured in tens of seconds, not the fraction of a
# second a desktop or clipboard tool takes: a full-screen PaddleOCR pass on CPU
# took 136s cold and 92s warm on a 1920x1080 display, against an executor
# default of 30s. So all five of these ran correctly and were cancelled anyway,
# and the agent saw "timed out" for a subsystem that was working.
#
# Declared per tool rather than by raising the global default, which would let a
# wedged mouse click stall an agent for five minutes. Read from configuration
# rather than pinned, because the right number is hardware: the same pass on a
# CUDA build finishes in single-digit seconds.
_VISION_TIMEOUT = get_settings().VISION_TOOL_TIMEOUT_SECONDS


# ==========================================================
# Internal helpers
# ==========================================================

async def _capture() -> Image:
    """
    Capture the screen as a vision Image.

    ScreenService returns a raw BGR ``ndarray``; every vision entry point needs
    an :class:`Image`. Converting in one place keeps the boundary explicit —
    passing the bare array through used to fail inside a provider with an
    ``AttributeError`` about a missing ``.data`` attribute.
    """

    screen: ScreenService = container.resolve(ScreenService)

    frame = await screen.capture()

    return Image.from_numpy(
        frame,
        source="screen",
        color_space="bgr",
    )


def _vision() -> VisionService:

    return container.resolve(VisionService)


def _blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    """
    Serialise domain objects for the tool result.

    Tool results are JSON-encoded for the model, and a TextBlock or Detection
    would otherwise be stringified into an unparseable repr.
    """

    return [block.to_dict() for block in blocks]


# ==========================================================
# OCR
# ==========================================================

@tool(
    category="vision",
    description="Read all visible text from the current screen.",
    timeout_seconds=_VISION_TIMEOUT,
)
async def read_screen_text() -> dict[str, Any]:

    image = await _capture()

    blocks = await _vision().read_text(image)

    return {
        "width": image.width,
        "height": image.height,
        "count": len(blocks),
        "text": " ".join(block.text for block in blocks),
        "blocks": _blocks(blocks),
    }


@tool(
    category="vision",
    description="Read text from an image file on disk.",
    timeout_seconds=_VISION_TIMEOUT,
)
async def read_image_text(
    path: str,
) -> dict[str, Any]:
    """
    OCR a saved image.

    Kept separate from read_screen_text so text recognition can be exercised on
    a machine with no display, and so an already-captured chart can be re-read
    without grabbing the screen again.
    """

    image = Image.open(path)

    blocks = await _vision().read_text(image)

    return {
        "path": path,
        "width": image.width,
        "height": image.height,
        "count": len(blocks),
        "text": " ".join(block.text for block in blocks),
        "blocks": _blocks(blocks),
    }


# ==========================================================
# Object Detection
# ==========================================================

@tool(
    category="vision",
    description="Detect visible objects on the current screen.",
    timeout_seconds=_VISION_TIMEOUT,
)
async def detect_screen_objects() -> dict[str, Any]:

    image = await _capture()

    detections = await _vision().detect_objects(image)

    return {
        "width": image.width,
        "height": image.height,
        "count": len(detections),
        "objects": _blocks(detections),
    }


# ==========================================================
# Find Text
# ==========================================================

@tool(
    category="vision",
    description="Find text on the screen and report where it is.",
    timeout_seconds=_VISION_TIMEOUT,
)
async def find_text(
    query: str,
) -> dict[str, Any]:

    image = await _capture()

    matches = await _vision().find_text(image, query)

    return {
        "query": query,
        "found": bool(matches),
        "count": len(matches),
        "matches": _blocks(matches),
    }


# ==========================================================
# Analyze Screen
# ==========================================================

@tool(
    category="vision",
    description="Capture the screen and return OCR and object detection results.",
    # The heaviest tool here: OCR *and* detection on one capture, so it needs at
    # least what read_screen_text needs.
    timeout_seconds=_VISION_TIMEOUT,
)
async def analyze_screen() -> dict[str, Any]:

    image = await _capture()

    vision = _vision()

    blocks = await vision.read_text(image)

    result: dict[str, Any] = {
        "width": image.width,
        "height": image.height,
        "text": " ".join(block.text for block in blocks),
        "blocks": _blocks(blocks),
        "capabilities": vision.capabilities(),
    }

    # Detection is optional — ultralytics and its weights may not be present.
    # Reporting the text we did read beats failing the whole analysis.
    if vision.has_detector:
        result["objects"] = _blocks(
            await vision.detect_objects(image)
        )
    else:
        result["objects"] = []

    return result
