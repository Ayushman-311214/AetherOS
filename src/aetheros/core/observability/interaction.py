"""
The interaction context that tags a run with where it came from.

A single request enters the agent exactly once, from one of several front
ends (the terminal, voice, ...). Both front ends are *presentation* layers over
the one shared :class:`~aetheros.agents.core.AgentCore`; neither owns the run.
So the origin of a turn is not a routing decision -- it must never pick which UI
sees the run -- it is only a *label* every UI can read to tint what it shows.

That label rides a :class:`contextvars.ContextVar`. The gateway opens a scope
around ``agent.run(...)`` and every :func:`~aetheros.core.observability.emitter.emit_trace`
call made *inside* that awaited run reads the scope and stamps the event with
``source``/``session_id``/``request_id``. Because the whole turn runs in one
task, the contextvar propagates across every ``await`` without threading an
argument through the dozen emit sites inside the loop.

``request_id`` correlates one turn end to end and is the value the agent already
uses as ``run_id`` (the ``AgentState.state_id``); ``session_id`` is stable for
the life of one front-end session. Concurrency-safety (PHASE 13) rests on these
ids, not on any global "current request": two overlapping turns each carry their
own scope.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InteractionContext:
    """Where the in-flight turn came from and how to correlate it.

    Immutable: a turn's identity does not change once it has started, and a
    record that can be edited afterwards is not a correlation key.
    """

    #: The front end that submitted the turn, e.g. ``"terminal"`` / ``"voice"``.
    #: A label only -- it never decides which UI renders the turn.
    source: str

    #: Stable for the life of one front-end session.
    session_id: str

    #: Unique per submitted turn. Mirrors the agent's ``run_id`` so every
    #: trace event of the turn shares one correlation id.
    request_id: str


# The one slot. Defaults to None: outside any scope (early bootstrap, a unit
# test, a direct agent.run) there simply is no origin to report, and the
# emitter treats that as "unsourced" rather than failing.
_CURRENT: contextvars.ContextVar[InteractionContext | None] = contextvars.ContextVar(
    "aetheros_interaction",
    default=None,
)


def current_interaction() -> InteractionContext | None:
    """The context of the turn running in this task, or None outside a scope."""

    return _CURRENT.get()


def new_request_id() -> str:
    """A fresh per-turn correlation id."""

    return uuid.uuid4().hex


def new_session_id() -> str:
    """A fresh per-session id for a front end that owns one gateway."""

    return uuid.uuid4().hex


@contextmanager
def interaction_scope(
    *,
    source: str,
    session_id: str,
    request_id: str | None = None,
) -> Iterator[InteractionContext]:
    """Tag everything emitted inside the block with one interaction context.

    Wrap the awaited ``agent.run(...)`` so the run's trace events carry the
    origin. The token is reset on exit -- including on an exception -- so a
    turn's label never leaks into the next one, and nested scopes restore the
    enclosing one.
    """

    context = InteractionContext(
        source=source,
        session_id=session_id,
        request_id=request_id or new_request_id(),
    )

    token = _CURRENT.set(context)

    try:
        yield context

    finally:
        _CURRENT.reset(token)


__all__ = [
    "InteractionContext",
    "current_interaction",
    "interaction_scope",
    "new_request_id",
    "new_session_id",
]
