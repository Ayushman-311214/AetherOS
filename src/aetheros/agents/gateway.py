"""
The one entry a front end submits a turn through.

Both the terminal and voice are presentation layers over the single shared
:class:`~aetheros.agents.core.AgentCore`. Neither runs the agent directly:
they hand the goal to this gateway, which opens an
:func:`~aetheros.core.observability.interaction.interaction_scope` tagged with
the front end's ``source`` and then calls the *same* ``agent.run(...)``. So a
request enters the agent exactly once, and every trace event of that run is
stamped with where it came from -- which is what lets both UIs observe the one
run over the shared bus.

The gateway owns no orchestration of its own: it does not plan, choose tools, or
format output. It is a thin seam whose whole job is "tag the origin, run the one
agent". ``source`` is a label, never a route -- the gateway does not decide
which UI sees the run, and it holds no "current request" that two overlapping
turns could clobber (each turn carries its own scope and ids).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.logging import get_logger
from ..core.observability.interaction import interaction_scope, new_session_id

if TYPE_CHECKING:
    from .core import AgentCore, AgentRunResult


class InteractionGateway:
    """Submit a goal to the shared agent, tagged with its front end."""

    def __init__(
        self,
        agent: AgentCore,
        *,
        session_id: str | None = None,
    ) -> None:

        self._agent = agent

        # One session id for the life of the process: a single-user desktop
        # runtime is one session, and every turn from either front end shares
        # it. A future multi-session host would mint one per session instead.
        self._session_id = session_id or new_session_id()

        self._logger = get_logger("interaction.gateway")

    @property
    def session_id(self) -> str:
        return self._session_id

    async def submit(
        self,
        goal: str,
        *,
        source: str,
        **run_kwargs,
    ) -> AgentRunResult:
        """Run ``goal`` on the shared agent, labelling the turn with ``source``.

        ``run_kwargs`` pass straight through to :meth:`AgentCore.run`
        (``system_prompt``, ``max_iterations``, ...), so a front end with its
        own run parameters -- voice's spoken-style prompt, say -- keeps them
        without the gateway knowing what they mean. The scope is opened *around*
        the awaited run, so every event the run emits is source-tagged.
        """

        self._logger.bind(source=source, goal_chars=len(goal)).debug(
            "Interaction submitted."
        )

        with interaction_scope(source=source, session_id=self._session_id):
            return await self._agent.run(goal, **run_kwargs)


__all__ = ["InteractionGateway"]
