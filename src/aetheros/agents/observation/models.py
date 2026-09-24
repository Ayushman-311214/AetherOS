"""
Observation: one thing the agent currently knows about the computer.

This layer is deliberately *representational*. An :class:`Observation` records
what was seen -- a tool's result, a screenshot on disk, what the vision layer
read off the screen, and (later) browser state -- together with where it came
from, when, and how sure we are. It does **not** decide what to do about any of
it. Choosing an action from observations is the planner's job; keeping this
layer free of that choice is what lets a critic, a logger or a replay tool read
the same facts without inheriting a decision.

Relationship to ``agents.state.Observation``
--------------------------------------------
``state.Observation`` is a *transcript entry*: one line in the conversation an
agent run built, carrying just text and its provenance. This ``Observation`` is
richer -- structured ``data``, an optional ``artifact_path`` and an optional
``confidence`` -- because it models the agent's knowledge of the environment
rather than a turn of dialogue. The two are bridged, not merged:
:meth:`Observation.to_state_observation` projects this down to the transcript
form, so a run can record it without this package duplicating what ``state``
already owns.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ...core.errors.agent_error import AgentError


def _utc_now() -> str:
    # Defined here rather than imported from agents.state: that module pulls in
    # the llm and tools packages at import time, and this layer is meant to be
    # light enough to build an Observation without them. UTC for the same
    # reason state uses it -- a local-time trail silently reorders across DST.
    return datetime.now(timezone.utc).isoformat()


def _new_observation_id() -> str:
    return f"obs-{uuid.uuid4().hex[:12]}"


class ObservationSource(str, Enum):
    """Where an observation came from.

    ``str`` subclass so the value serialises as itself. ``BROWSER`` has no
    producer yet -- it is the forward-compatible seam the task asks for, so a
    browser-state observation lands in this same abstraction the day that layer
    exists, rather than forcing a new type then.
    """

    TOOL = "tool"
    SCREENSHOT = "screenshot"
    VISION = "vision"
    BROWSER = "browser"
    AGENT = "agent"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def coerce(cls, value: object) -> ObservationSource:
        """Accept a member or its name; reject anything else.

        An unknown source is rejected rather than defaulted: provenance is the
        whole point of the type, so quietly relabelling a mystery reading as
        ``agent`` would launder exactly the distinction a critic relies on.
        """

        if isinstance(value, cls):
            return value

        text = str(value or "").strip().lower()

        # Tolerate an enum rendered via str(), e.g. "ObservationSource.TOOL".
        if "." in text:
            text = text.rsplit(".", 1)[-1]

        try:
            return cls(text)

        except ValueError as exc:
            raise AgentError(
                code="OBSERVATION_INVALID_SOURCE",
                message=f"Unknown observation source {value!r}.",
                hint=f"Use one of: {', '.join(s.value for s in cls)}.",
            ) from exc


_OBSERVATION_FIELDS = frozenset(
    {
        "id",
        "source",
        "data",
        "description",
        "artifact_path",
        "confidence",
        "timestamp",
    }
)


@dataclass(frozen=True, slots=True)
class Observation:
    """A single fact the agent holds about the current state of the computer.

    Frozen and picklable, like the records in ``agents.state``: an observation
    is evidence, and evidence that can be mutated after the fact is not
    evidence. Only :attr:`source` is required -- everything a producer cannot
    supply (a description, an artifact on disk, a confidence) is optional, so a
    bare tool result and a scored vision reading are the same shape.
    """

    source: ObservationSource

    #: Structured payload -- always a dict, even when empty. This is the machine
    #: readable body of the observation; :attr:`description` is its prose gloss.
    data: dict[str, Any] = field(default_factory=dict)

    #: Optional human/model-readable summary of what was observed.
    description: str | None = None

    #: Optional path to a saved artifact (a screenshot, a captured region).
    artifact_path: str | None = None

    #: Optional confidence in ``[0, 1]``. ``None`` means "not applicable",
    #: which is distinct from ``0.0`` ("observed, and certainly nothing").
    confidence: float | None = None

    id: str = field(default_factory=_new_observation_id)
    timestamp: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        # Coerce first so callers may pass the string form of a source.
        object.__setattr__(
            self, "source", ObservationSource.coerce(self.source)
        )

        if not isinstance(self.data, dict):
            raise AgentError(
                code="OBSERVATION_INVALID_DATA",
                message=(
                    "Observation.data must be a dict of structured fields, "
                    f"got {type(self.data).__name__}."
                ),
                hint="Wrap a scalar reading in a dict, e.g. {'value': reading}.",
            )

        if self.description is not None and not isinstance(self.description, str):
            raise AgentError(
                code="OBSERVATION_INVALID_DESCRIPTION",
                message="Observation.description must be a string or None.",
            )

        if self.artifact_path is not None and not isinstance(
            self.artifact_path, str
        ):
            raise AgentError(
                code="OBSERVATION_INVALID_ARTIFACT",
                message="Observation.artifact_path must be a string or None.",
            )

        if self.confidence is not None:
            try:
                value = float(self.confidence)

            except (TypeError, ValueError) as exc:
                raise AgentError(
                    code="OBSERVATION_INVALID_CONFIDENCE",
                    message="Observation.confidence must be a number or None.",
                ) from exc

            if not 0.0 <= value <= 1.0:
                raise AgentError(
                    code="OBSERVATION_INVALID_CONFIDENCE",
                    message=(
                        f"Observation.confidence must be in [0, 1], got {value}."
                    ),
                    hint="Confidence is a probability, not a raw score.",
                )

            object.__setattr__(self, "confidence", value)

    # ==========================================================
    # Projections
    # ==========================================================

    @property
    def summary(self) -> str:
        """A short one-line rendering, used when no description was given.

        Deliberately terse and free of secrets: it names the source and the
        structured field *names*, never their values, so it is safe to log by
        the same rule ``agents.state`` applies to tool arguments.
        """

        if self.description:
            return self.description

        keys = ", ".join(sorted(self.data)) or "no data"
        return f"{self.source.value} observation ({keys})"

    def to_state_observation(self, *, iteration: int = 0) -> Any:
        """Project down to a transcript-level ``agents.state.Observation``.

        The bridge that lets a run *record* this without duplicating the
        transcript type. Imported lazily so importing this module never drags
        in the heavier ``state`` module (and its llm/tools imports) -- see the
        module docstring.
        """

        from ..state import Observation as StateObservation

        metadata: dict[str, Any] = {
            "observation_id": self.id,
            "data": deepcopy(self.data),
        }

        if self.artifact_path is not None:
            metadata["artifact_path"] = self.artifact_path

        if self.confidence is not None:
            metadata["confidence"] = self.confidence

        return StateObservation(
            text=self.description or self.summary,
            iteration=iteration,
            source=self.source.value,
            metadata=metadata,
        )

    # ==========================================================
    # Serialization
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "data": deepcopy(self.data),
            "description": self.description,
            "artifact_path": self.artifact_path,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Observation:
        """Rebuild from :meth:`to_dict`, rejecting unknown fields.

        Unknown keys are an error rather than ignored, matching
        ``agents.state``: silently dropping a field restores an observation
        that is quietly missing part of itself.
        """

        if not isinstance(payload, dict):
            raise AgentError(
                code="OBSERVATION_INVALID_PAYLOAD",
                message=(
                    "Observation payload must be a dict, got "
                    f"{type(payload).__name__}."
                ),
            )

        unknown = sorted(set(payload) - _OBSERVATION_FIELDS)
        if unknown:
            raise AgentError(
                code="OBSERVATION_UNKNOWN_FIELD",
                message=f"Unknown observation field(s): {', '.join(unknown)}.",
                hint="Restoring an observation must be lossless.",
            )

        if "source" not in payload:
            raise AgentError(
                code="OBSERVATION_MISSING_SOURCE",
                message="Observation payload is missing required field 'source'.",
            )

        return cls(
            source=payload["source"],
            data=dict(payload.get("data") or {}),
            description=payload.get("description"),
            artifact_path=payload.get("artifact_path"),
            confidence=payload.get("confidence"),
            id=str(payload.get("id") or _new_observation_id()),
            timestamp=str(payload.get("timestamp") or _utc_now()),
        )


__all__ = [
    "Observation",
    "ObservationSource",
]
