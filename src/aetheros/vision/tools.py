from __future__ import annotations

from typing import Any

from ..config.config_loader import get_settings
from ..core.container import container
from ..tools import tool

from ..desktop.screen.controller import ScreenService
from .controller import VisionService
from .frame_cache import get_frame_cache
from .image import Image
from .profiling import StageTimings, get_profiler


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

async def _capture_fresh() -> Image:
    """
    Grab the screen right now and wrap it as a vision Image.

    ScreenService returns a raw BGR ``ndarray``; every vision entry point needs
    an :class:`Image`. Converting in one place keeps the boundary explicit --
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


async def _capture(*, fresh: bool = False) -> Image:
    """
    Return a screen frame, reusing a very recent one when allowed.

    Read-only ops share the short-lived frame cache, so a "find X" immediately
    followed by "read Y" captures once, not twice. ``fresh=True`` bypasses the
    cache and captures at the moment of the call -- grounded actions use it so a
    click never lands on a stale frame.
    """

    cache = get_frame_cache()

    image, _from_cache = await cache.get_or_capture(_capture_fresh, force=fresh)

    return image


async def _capture_region(
    left: int,
    top: int,
    width: int,
    height: int,
) -> Image:
    """
    Capture a single rectangle instead of the whole screen (ROI).

    Not cached: a region grab is already small, and the frame cache holds
    full-screen frames keyed by nothing but time -- mixing regions into it would
    hand a caller a crop when it asked for the screen.
    """

    screen: ScreenService = container.resolve(ScreenService)

    frame = await screen.capture_region(
        left=left,
        top=top,
        width=width,
        height=height,
    )

    return Image.from_numpy(
        frame,
        source="screen-region",
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


def _timings(timings: StageTimings) -> dict[str, dict[str, float]]:
    """
    Attach stage timings to a result only when profiling is on.

    Off (the default) this returns an empty dict, so a tool result is
    byte-for-byte what it was before profiling existed.
    """

    profiler = get_profiler()

    if not profiler.enabled:
        return {}

    return {"timings_ms": timings.as_dict()}


# ==========================================================
# OCR
# ==========================================================

@tool(
    category="vision",
    description="Read all visible text from the current screen.",
    timeout_seconds=_VISION_TIMEOUT,
)
async def read_screen_text() -> dict[str, Any]:

    profiler = get_profiler()
    timings = StageTimings()

    with profiler.stage("capture", timings):
        image = await _capture()

    with profiler.stage("ocr", timings):
        blocks = await _vision().read_text(image)

    return {
        "width": image.width,
        "height": image.height,
        "count": len(blocks),
        "text": " ".join(block.text for block in blocks),
        "blocks": _blocks(blocks),
        **_timings(timings),
    }


@tool(
    category="vision",
    description=(
        "Read text from a rectangular region of the screen (ROI). Give the "
        "region as left, top, width, height in pixels. Reading only the panel "
        "you care about is far faster than reading the whole screen -- prefer "
        "this when you already know where the text is."
    ),
    timeout_seconds=_VISION_TIMEOUT,
)
async def read_screen_region(
    left: int,
    top: int,
    width: int,
    height: int,
) -> dict[str, Any]:

    profiler = get_profiler()
    timings = StageTimings()

    with profiler.stage("capture_region", timings):
        image = await _capture_region(left, top, width, height)

    with profiler.stage("ocr", timings):
        blocks = await _vision().read_text(image)

    return {
        "region": {"left": left, "top": top, "width": width, "height": height},
        "width": image.width,
        "height": image.height,
        "count": len(blocks),
        "text": " ".join(block.text for block in blocks),
        "blocks": _blocks(blocks),
        **_timings(timings),
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

    profiler = get_profiler()
    timings = StageTimings()

    with profiler.stage("capture", timings):
        image = await _capture()

    with profiler.stage("detection", timings):
        detections = await _vision().detect_objects(image)

    return {
        "width": image.width,
        "height": image.height,
        "count": len(detections),
        "objects": _blocks(detections),
        **_timings(timings),
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

    profiler = get_profiler()
    timings = StageTimings()

    with profiler.stage("capture", timings):
        image = await _capture()

    with profiler.stage("ocr", timings):
        matches = await _vision().find_text(image, query)

    return {
        "query": query,
        "found": bool(matches),
        "count": len(matches),
        "matches": _blocks(matches),
        **_timings(timings),
    }


# ==========================================================
# Analyze Screen
# ==========================================================

@tool(
    category="vision",
    description=(
        "Give a fast overview of the current screen: its dimensions and which "
        "vision capabilities (OCR, object detection) are available. By default "
        "this is LIGHTWEIGHT -- it does NOT run full-screen OCR or object "
        "detection, both of which are slow. Use it to answer 'what is on the "
        "screen?' cheaply, then reach for a targeted tool: read_screen_text (or "
        "read_screen_region) to read text, detect_screen_objects to detect "
        "objects, find_text or ground_target to locate something. Pass "
        "include_text=true and/or include_objects=true only when you truly want "
        "the heavy passes bundled into this one call."
    ),
    timeout_seconds=_VISION_TIMEOUT,
)
async def analyze_screen(
    include_text: bool = False,
    include_objects: bool = False,
) -> dict[str, Any]:
    """
    Lightweight by default; heavy passes are opt-in.

    The previous behaviour ran OCR *and* detection on every call -- the single
    most expensive thing the vision layer could do, on a request ("what's on
    screen?") that usually wants neither. It now returns a cheap summary and
    only runs a heavy stage when the caller explicitly asks, so the FAST vs
    ACCURATE choice is explicit rather than paid unconditionally.
    """

    profiler = get_profiler()
    timings = StageTimings()

    with profiler.stage("capture", timings):
        image = await _capture()

    vision = _vision()

    result: dict[str, Any] = {
        "width": image.width,
        "height": image.height,
        "capabilities": vision.capabilities(),
        "included": {
            "text": bool(include_text),
            "objects": bool(include_objects),
        },
    }

    if include_text and vision.has_ocr:
        with profiler.stage("ocr", timings):
            blocks = await vision.read_text(image)

        result["text"] = " ".join(block.text for block in blocks)
        result["blocks"] = _blocks(blocks)

    if include_objects and vision.has_detector:
        with profiler.stage("detection", timings):
            result["objects"] = _blocks(await vision.detect_objects(image))

    result.update(_timings(timings))

    return result
