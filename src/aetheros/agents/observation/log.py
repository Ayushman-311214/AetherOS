"""
ObservationLog: the ordered set of what the agent currently knows.

A run accumulates observations; this holds them. It is the answer to "what has
the agent seen so far", nothing more -- it stores, filters and serialises, and
pointedly offers no method that turns observations into a decision. Deciding is
the planner's job, and keeping the knowledge store free of it is what lets the
same log feed a planner, a critic and an audit trail without any of them
inheriting another's choice.

Ownership follows ``agents.state``: one log belongs to one run on one event
loop. Reads hand back tuples, so a caller walking the history cannot mutate it
in place.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator

from ...core.errors.agent_error import AgentError
from .models import Observation, ObservationSource


class ObservationLog:
    """An append-only, ordered collection of :class:`Observation`."""

    __slots__ = ("_observations",)

    def __init__(
        self,
        observations: Iterable[Observation] | None = None,
    ) -> None:
        self._observations: list[Observation] = []
        for observation in observations or ():
            self.record(observation)

    # ==========================================================
    # Recording
    # ==========================================================

    def record(self, observation: Observation) -> Observation:
        """Append one observation, rejecting anything that is not one.

        The type guard is deliberate: a log that will accept a bare dict makes
        ``by_source`` and serialization fail far from the mistake, so the
        wrong-shaped entry is refused at the point it is added.
        """

        if not isinstance(observation, Observation):
            raise AgentError(
                code="OBSERVATION_INVALID_ENTRY",
                message=(
                    "ObservationLog holds Observation instances, got "
                    f"{type(observation).__name__}."
                ),
                hint="Build one with the observation factories first.",
            )

        self._observations.append(observation)
        return observation

    def extend(self, observations: Iterable[Observation]) -> None:
        for observation in observations:
            self.record(observation)

    # ==========================================================
    # Reading
    # ==========================================================

    def __len__(self) -> int:
        return len(self._observations)

    def __iter__(self) -> Iterator[Observation]:
        return iter(tuple(self._observations))

    def __bool__(self) -> bool:
        return bool(self._observations)

    def all(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    def by_source(
        self,
        source: ObservationSource | str,
    ) -> tuple[Observation, ...]:
        """Every observation from one source, oldest first."""

        wanted = ObservationSource.coerce(source)
        return tuple(o for o in self._observations if o.source is wanted)

    def latest(
        self,
        count: int | None = None,
    ) -> tuple[Observation, ...]:
        """The most recent observations, newest last.

        ``latest(1)`` is the freshest single reading; ``latest()`` is the whole
        history. A non-positive count is empty, not an error -- "give me the
        last zero observations" is a coherent, if odd, request.
        """

        if count is None:
            return tuple(self._observations)

        if count <= 0:
            return ()

        return tuple(self._observations[-count:])

    # ==========================================================
    # Serialization
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        return {"observations": [o.to_dict() for o in self._observations]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ObservationLog:
        if not isinstance(payload, dict):
            raise AgentError(
                code="OBSERVATION_INVALID_PAYLOAD",
                message=(
                    "ObservationLog payload must be a dict, got "
                    f"{type(payload).__name__}."
                ),
            )

        raw = payload.get("observations") or ()
        return cls(Observation.from_dict(item) for item in raw)


__all__ = [
    "ObservationLog",
]
