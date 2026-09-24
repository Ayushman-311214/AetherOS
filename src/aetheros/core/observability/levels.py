"""
Trace verbosity levels and the per-event-type filter.

``TraceLevel`` is an ordered scale: a recorder configured at a given level shows
every event whose own minimum level is at or below it. The mapping in
:data:`_EVENT_LEVEL` is the single source of truth for "how noisy is this stage",
so PHASE 8's NORMAL-vs-VERBOSE split lives here rather than being scattered
through the emit sites.
"""

from __future__ import annotations

from enum import IntEnum

from .events import TraceEventType, TraceStatus


class TraceLevel(IntEnum):
    """Ordered verbosity. Higher shows strictly more.

    ``IntEnum`` so ``event_level <= configured_level`` is a plain comparison and
    a config string maps onto a number without a lookup table at every call.
    """

    OFF = 0
    ERROR = 1
    MINIMAL = 2
    NORMAL = 3
    DEBUG = 4
    VERBOSE = 5


_ALIASES: dict[str, TraceLevel] = {
    "off": TraceLevel.OFF,
    "none": TraceLevel.OFF,
    "error": TraceLevel.ERROR,
    "errors": TraceLevel.ERROR,
    "minimal": TraceLevel.MINIMAL,
    "min": TraceLevel.MINIMAL,
    "normal": TraceLevel.NORMAL,
    "default": TraceLevel.NORMAL,
    "debug": TraceLevel.DEBUG,
    "verbose": TraceLevel.VERBOSE,
    "all": TraceLevel.VERBOSE,
}


def resolve_level(value: str | TraceLevel | int | None) -> TraceLevel:
    """Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.

    Tolerant on purpose: the value arrives from ``TRACE_LEVEL`` in the
    environment or from a ``trace level <x>`` CLI command, and an unknown string
    should fall back to NORMAL rather than crash a run over a typo.
    """

    if value is None:
        return TraceLevel.NORMAL
    if isinstance(value, TraceLevel):
        return value
    if isinstance(value, int):
        try:
            return TraceLevel(value)
        except ValueError:
            return TraceLevel.NORMAL
    return _ALIASES.get(str(value).strip().lower(), TraceLevel.NORMAL)


# The minimum level at which each event type is shown. Everything not listed is
# treated as NORMAL. This is the PHASE 8 contract:
#   NORMAL   -> input, major stages, LLM response, planner decision, tool
#               calls/results, final response
#   VERBOSE  -> schema generation, argument validation, per-iteration bookkeeping,
#               normalized payloads, fine timings
_EVENT_LEVEL: dict[TraceEventType, TraceLevel] = {
    TraceEventType.INPUT_RECEIVED: TraceLevel.MINIMAL,
    TraceEventType.AGENT_STARTED: TraceLevel.MINIMAL,
    TraceEventType.FINAL_RESPONSE_CREATED: TraceLevel.MINIMAL,
    TraceEventType.TTS_STARTED: TraceLevel.NORMAL,
    TraceEventType.TTS_COMPLETED: TraceLevel.NORMAL,
    TraceEventType.STT_STARTED: TraceLevel.NORMAL,
    TraceEventType.STT_COMPLETED: TraceLevel.NORMAL,
    TraceEventType.AGENT_REQUEST_RECEIVED: TraceLevel.NORMAL,
    TraceEventType.LLM_REQUEST_STARTED: TraceLevel.NORMAL,
    TraceEventType.LLM_RESPONSE_RECEIVED: TraceLevel.NORMAL,
    TraceEventType.PLANNER_DECISION: TraceLevel.NORMAL,
    TraceEventType.TOOL_SELECTED: TraceLevel.NORMAL,
    TraceEventType.TOOL_EXECUTION_STARTED: TraceLevel.NORMAL,
    TraceEventType.TOOL_EXECUTION_COMPLETED: TraceLevel.NORMAL,
    TraceEventType.OBSERVATION_CREATED: TraceLevel.NORMAL,
    # Verbose bookkeeping.
    TraceEventType.AGENT_ITERATION_STARTED: TraceLevel.DEBUG,
    TraceEventType.AGENT_ITERATION_COMPLETED: TraceLevel.DEBUG,
    TraceEventType.LLM_REQUEST_COMPLETED: TraceLevel.DEBUG,
    TraceEventType.PLANNER_STARTED: TraceLevel.DEBUG,
    TraceEventType.PLANNER_COMPLETED: TraceLevel.DEBUG,
    TraceEventType.ACTION_CREATED: TraceLevel.VERBOSE,
    TraceEventType.ACTION_NORMALIZED: TraceLevel.VERBOSE,
    TraceEventType.TOOL_SCHEMA_GENERATED: TraceLevel.VERBOSE,
    TraceEventType.TOOL_ARGUMENTS_VALIDATED: TraceLevel.VERBOSE,
    # Failures ride the ERROR floor so they surface even at low verbosity.
    TraceEventType.TOOL_EXECUTION_FAILED: TraceLevel.ERROR,
    TraceEventType.ERROR: TraceLevel.ERROR,
    TraceEventType.WARNING: TraceLevel.MINIMAL,
}


def level_for_event(event_type: TraceEventType, status: TraceStatus) -> TraceLevel:
    """The minimum level at which an event of this type/status is shown.

    A ``FAILED``/``ERROR`` status pulls any event down to the ERROR floor, so a
    tool failure is visible even when the configured level would otherwise hide
    that stage -- PHASE 12's "any error appears in the live trace".
    """

    if status in (TraceStatus.FAILED, TraceStatus.ERROR):
        return TraceLevel.ERROR
    return _EVENT_LEVEL.get(event_type, TraceLevel.NORMAL)


__all__ = ["TraceLevel", "resolve_level", "level_for_event"]
