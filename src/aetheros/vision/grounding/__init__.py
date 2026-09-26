"""
Vision grounding: resolve a natural-language target into screen coordinates.

This package sits *on top of* the existing Vision subsystem. It adds no new
perception -- it reuses :class:`~aetheros.vision.controller.VisionService`
(OCR + object detection) and the screen-capture seam the vision tools already
own -- and contributes only the missing layer: turning a request like
"the Search button" or "the button below Login" into a ranked visual match
with a bounding box, a safe click point, a confidence band and the evidence
for why that element was chosen.

The engine is deliberately pure: it takes an already-captured image and a
resolved :class:`VisionService`, so it is fully testable with mocked frames and
recorded OCR/detection results. Screen capture and mouse/keyboard actuation
stay in the tool layer, exactly like the existing vision tools.
"""

from __future__ import annotations

from .engine import GroundingEngine
from .models import GroundingCandidate, GroundingResult, GroundingTarget

__all__ = [
    "GroundingEngine",
    "GroundingCandidate",
    "GroundingResult",
    "GroundingTarget",
]
