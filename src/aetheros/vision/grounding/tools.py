"""
Grounding tools: the agent-facing surface of the grounding layer.

These are the only new tools the layer adds, and they deliberately reuse the
existing subsystems rather than re-implementing any of them:

* screen capture and the ``VisionService`` come from the vision tools' own
  ``_capture`` / ``_vision`` helpers,
* clicking reuses :class:`~aetheros.desktop.mouse.controller.MouseService`,
* typing reuses :class:`~aetheros.desktop.keyboard.controller.KeyboardService`.

``ground_target`` resolves a phrase to a location and stops there -- the model
decides what to do with it. ``click_grounded_target`` and
``type_into_grounded_target`` fold capture -> ground -> act into one call: the
coordinate is used the instant it is produced, so it cannot go stale between a
separate "find" and "click", and neither will act on a match below the safe
band.
"""

from __future__ import annotations

from typing import Any

from ...config.config_loader import get_settings
from ...core.container import container
from ...tools import tool
from ..frame_cache import get_frame_cache
from ..tools import _capture, _vision
from .engine import GroundingEngine

# Grounding runs the same OCR/detection pass the vision tools do, so it inherits
# their (much larger) timeout rather than the default 30s tool budget.
_GROUNDING_TIMEOUT = get_settings().VISION_TOOL_TIMEOUT_SECONDS


def _engine() -> GroundingEngine:
    settings = get_settings()
    return GroundingEngine(
        _vision(),
        high_threshold=settings.GROUNDING_CONFIDENCE_HIGH,
        medium_threshold=settings.GROUNDING_CONFIDENCE_MEDIUM,
    )


# ==========================================================
# Grounding
# ==========================================================

@tool(
    category="vision.grounding",
    description=(
        "Resolve a natural-language on-screen target into real screen "
        "coordinates using OCR and object detection. Describe the target "
        "semantically -- e.g. 'the Search button', 'the Chrome icon', 'the "
        "button below Login', 'the leftmost result' -- and this returns the "
        "matched element's bounding box, a centre click point, a confidence "
        "band (HIGH/MEDIUM/LOW) and the evidence for the match. Use this to "
        "locate an element instead of guessing pixel coordinates, then click "
        "or type at the returned centre. Only HIGH matches are marked "
        "safe_to_act."
    ),
    timeout_seconds=_GROUNDING_TIMEOUT,
)
async def ground_target(
    target: str,
) -> dict[str, Any]:

    image = await _capture()

    result = await _engine().ground(target, image)

    return result.to_dict()


# ==========================================================
# Grounded actions (capture -> ground -> act, atomically)
# ==========================================================

@tool(
    category="vision.grounding",
    description=(
        "Locate a natural-language on-screen target and click it in one step. "
        "Captures the screen, grounds the target with OCR and object "
        "detection, and clicks the matched element's centre only when the "
        "match is safe (HIGH confidence and unambiguous). If the target is not "
        "found, ambiguous, or low-confidence, it does NOT click and returns why "
        "-- so a click never lands on a guessed location. Prefer this over a "
        "separate find-then-click: the coordinate is used the instant it is "
        "produced and cannot go stale."
    ),
    timeout_seconds=_GROUNDING_TIMEOUT,
)
async def click_grounded_target(
    target: str,
    button: str = "left",
) -> dict[str, Any]:

    from ...desktop.mouse.controller import MouseService

    # fresh=True: a click must be placed on the screen as it is at the instant
    # of acting, never on a frame the cache happened to still hold.
    image = await _capture(fresh=True)
    result = await _engine().ground(target, image)
    payload = result.to_dict()

    if not result.safe_to_act or result.center is None:
        payload["action"] = "none"
        payload["action_reason"] = (
            "Not clicked: the target was not resolved with high enough "
            "confidence to act on safely."
        )
        return payload

    mouse: MouseService = container.resolve(MouseService)
    await mouse.move(result.center["x"], result.center["y"])
    await mouse.click(button=button)

    # The click likely changed the screen; drop the cached frame so the next
    # read captures the new state rather than the pre-click one.
    get_frame_cache().invalidate()

    payload["action"] = "click"
    payload["action_reason"] = (
        f"Clicked '{result.matched_text}' at "
        f"({result.center['x']}, {result.center['y']})."
    )
    return payload


@tool(
    category="vision.grounding",
    description=(
        "Locate a natural-language on-screen target, click it to give it "
        "focus, and type text into it -- in one step. Grounds the target with "
        "OCR and object detection and only acts when the match is safe (HIGH "
        "confidence and unambiguous); otherwise it types nothing and returns "
        "why. Use this to fill a field described semantically, e.g. 'the search "
        "box', without guessing its coordinates."
    ),
    timeout_seconds=_GROUNDING_TIMEOUT,
)
async def type_into_grounded_target(
    target: str,
    text: str,
    interval: float = 0.0,
) -> dict[str, Any]:

    from ...desktop.keyboard.controller import KeyboardService
    from ...desktop.mouse.controller import MouseService

    # fresh=True for the same reason as click: focus and typing must target the
    # field where it is now, not where a cached frame last saw it.
    image = await _capture(fresh=True)
    result = await _engine().ground(target, image)
    payload = result.to_dict()

    if not result.safe_to_act or result.center is None:
        payload["action"] = "none"
        payload["action_reason"] = (
            "Nothing typed: the target field was not resolved with high enough "
            "confidence to act on safely."
        )
        return payload

    mouse: MouseService = container.resolve(MouseService)
    keyboard: KeyboardService = container.resolve(KeyboardService)

    await mouse.move(result.center["x"], result.center["y"])
    await mouse.click(button="left")
    await keyboard.write(text=text, interval=interval)

    # Typing changed the screen; the cached frame is now stale.
    get_frame_cache().invalidate()

    payload["action"] = "type"
    # The typed text itself is not echoed back: it routinely carries secrets.
    payload["action_reason"] = (
        f"Typed {len(text)} character(s) into '{result.matched_text}' at "
        f"({result.center['x']}, {result.center['y']})."
    )
    return payload


__all__ = [
    "ground_target",
    "click_grounded_target",
    "type_into_grounded_target",
]

