"""
Factories that turn what a subsystem produced into an :class:`Observation`.

Each factory *adapts* an existing result -- a ``ToolExecutionResult`` from the
executor, a saved frame from ``ScreenService``, the ``TextBlock`` / ``Detection``
/ ``TemplateMatch`` records from ``VisionService`` -- into the common
observation shape. Nothing here captures a screen or runs OCR itself: the task
is to *reuse* the screenshot and vision infrastructure, so these take those
subsystems' outputs as arguments rather than re-implementing them, and no new
vision algorithm is introduced.

Like the models module, these functions only describe; they never decide an
action from what they wrap.
"""

from __future__ import annotations

from typing import Any, Sequence

from ...tools.executor import ToolExecutionResult
from ...vision.models import Detection, TemplateMatch, TextBlock
from ..state import ToolResultRecord
from .models import Observation, ObservationSource


def _mean_confidence(values: Sequence[float]) -> float | None:
    """Average of the confidences a producer supplied, or ``None`` if none.

    ``None`` rather than ``0.0`` on an empty input: no readings means we cannot
    speak to confidence, which is not the same as reading something and being
    certain it was nothing.
    """

    numbers = [float(v) for v in values if v is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


# ==============================================================
# Tools
# ==============================================================

def tool_observation(
    result: ToolExecutionResult | ToolResultRecord,
    *,
    description: str | None = None,
    confidence: float | None = None,
) -> Observation:
    """Observe the outcome of one tool call.

    Accepts either the raw ``ToolExecutionResult`` from the executor or the
    already-recorded ``ToolResultRecord`` from a run's transcript, so a caller
    on either side of the state layer can build the same observation. A failed
    tool is still an observation -- ``ok`` and ``error`` are part of what the
    agent now knows.
    """

    if isinstance(result, ToolResultRecord):
        data: dict[str, Any] = {
            "tool": result.name,
            "ok": result.ok,
            "content": result.content,
            "error": result.error,
            "error_type": result.error_type,
            "duration_ms": result.duration_ms,
        }
        default_description = (
            f"tool {result.name} {'succeeded' if result.ok else 'failed'}"
        )

    elif isinstance(result, ToolExecutionResult):
        data = {
            "tool": result.name,
            "ok": result.ok,
            "value": result.value,
            "error": result.error,
            "error_type": result.error_type,
            "duration_ms": result.duration_ms,
        }
        default_description = (
            f"tool {result.name} {'succeeded' if result.ok else 'failed'}"
        )

    else:  # Reject an unrelated object rather than silently observing junk.
        raise TypeError(
            "tool_observation expects a ToolExecutionResult or "
            f"ToolResultRecord, got {type(result).__name__}."
        )

    return Observation(
        source=ObservationSource.TOOL,
        data=data,
        description=description or default_description,
        confidence=confidence,
    )


# ==============================================================
# Screenshots
# ==============================================================

def screenshot_observation(
    *,
    path: str,
    width: int,
    height: int,
    region: tuple[int, int, int, int] | None = None,
    description: str | None = None,
) -> Observation:
    """Observe that a screenshot exists on disk.

    Reuses ``ScreenService``: the caller captures and ``save``\\ s the frame,
    then hands us the path and dimensions that capture produced. The pixels are
    the artifact; the structured ``data`` is only what is knowable without
    interpreting them -- interpretation is the vision layer's job, and its
    result is a separate observation.
    """

    data: dict[str, Any] = {"width": int(width), "height": int(height)}

    if region is not None:
        left, top, region_w, region_h = region
        data["region"] = {
            "left": int(left),
            "top": int(top),
            "width": int(region_w),
            "height": int(region_h),
        }

    return Observation(
        source=ObservationSource.SCREENSHOT,
        data=data,
        description=description or f"screenshot {width}x{height}",
        artifact_path=path,
    )


# ==============================================================
# Vision
# ==============================================================

def vision_observation(
    *,
    text_blocks: Sequence[TextBlock] | None = None,
    detections: Sequence[Detection] | None = None,
    matches: Sequence[TemplateMatch] | None = None,
    artifact_path: str | None = None,
    description: str | None = None,
) -> Observation:
    """Observe what the vision layer read off an image.

    Consumes ``VisionService`` outputs -- ``TextBlock`` / ``Detection`` /
    ``TemplateMatch`` -- via their own ``to_dict``; it does not run OCR or
    detection here. Confidence is the mean of whatever the readings carried, so
    a low-confidence OCR pass produces a low-confidence observation the critic
    can weigh, rather than an unmarked assertion.
    """

    blocks = list(text_blocks or ())
    boxes = list(detections or ())
    hits = list(matches or ())

    data: dict[str, Any] = {
        "text_blocks": [b.to_dict() for b in blocks],
        "detections": [d.to_dict() for d in boxes],
        "matches": [m.to_dict() for m in hits],
    }

    confidence = _mean_confidence(
        [b.confidence for b in blocks]
        + [d.confidence for d in boxes]
        + [m.confidence for m in hits]
    )

    if description is None:
        # Names/counts only, never the recognised text itself -- a screen may
        # hold a password, and this string is log-bound.
        description = (
            f"vision read {len(blocks)} text block(s), "
            f"{len(boxes)} detection(s), {len(hits)} match(es)"
        )

    return Observation(
        source=ObservationSource.VISION,
        data=data,
        description=description,
        artifact_path=artifact_path,
        confidence=confidence,
    )


# ==============================================================
# Browser (forward-compatible seam)
# ==============================================================

def browser_observation(
    *,
    url: str,
    title: str | None = None,
    data: dict[str, Any] | None = None,
    description: str | None = None,
) -> Observation:
    """Observe browser state.

    The seam the task asks for: there is no browser-state producer wired yet,
    but a future one lands in this same abstraction by calling here, so nothing
    downstream -- serialization, the log, the transcript bridge -- has to change
    when it arrives.
    """

    payload: dict[str, Any] = {"url": url}

    if title is not None:
        payload["title"] = title

    if data:
        payload.update(data)

    return Observation(
        source=ObservationSource.BROWSER,
        data=payload,
        description=description or f"browser at {url}",
    )


__all__ = [
    "browser_observation",
    "screenshot_observation",
    "tool_observation",
    "vision_observation",
]
