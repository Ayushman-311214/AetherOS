"""
Agent observation layer.

A small, representational model of what the agent currently knows about the
computer. :class:`Observation` is the clean abstraction -- source, timestamp,
structured data, and optional description / artifact path / confidence -- and
the factories build one from each source the agent has: tool results,
screenshots, vision readings, and a forward-compatible seam for browser state.
:class:`ObservationLog` holds the set of them for one run.

This layer only records what was seen. It never decides an action from it --
that separation is what lets a planner, a critic and an audit trail read the
same evidence. See :mod:`aetheros.agents.observation.models` for how this
relates to, and bridges into, the transcript-level ``agents.state.Observation``.
"""

from .factory import (
    browser_observation,
    screenshot_observation,
    tool_observation,
    vision_observation,
)
from .log import ObservationLog
from .models import Observation, ObservationSource

__all__ = [
    "Observation",
    "ObservationLog",
    "ObservationSource",
    "browser_observation",
    "screenshot_observation",
    "tool_observation",
    "vision_observation",
]
