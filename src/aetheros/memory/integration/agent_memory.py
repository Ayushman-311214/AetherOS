"""
Concrete AgentMemory implementation (spec Phase 20).

Implements the agent-package port (:class:`aetheros.agents.memory_port.AgentMemory`)
on top of the existing :class:`MemoryManager`. This is the one place that
translates between the agent's run record (:class:`AgentState`) and the memory
domain (episodes, failures): the agent stays ignorant of memory internals, and
memory stays ignorant of the agent loop.

Dependency direction is memory -> agents (this module imports the agent port and
``AgentState``); the agent never imports memory, so there is no import cycle.
Both recall and recording are defensive: any failure degrades to "no memory"
rather than propagating into the run (spec Phase 20L).
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from ...agents.memory_port import AgentMemory, MemoryContext, MemoryItemView
from ...agents.state import (
    STOP_LOOP_GUARD,
    STOP_MAX_ITERATIONS,
    AgentState,
    AgentStatus,
)
from ...core.logging import get_logger
from ..config import MemoryConfig
from .._clock import utcnow
from ..domain.enums import OutcomeStatus
from ..domain.episode import ActionRecord, Episode, Outcome
from ..domain.preference import FailureRecord
from ..services.manager import MemoryManager

logger = get_logger("memory.agent")

# Cap how many failure records one run may emit, so a run that failed every tool
# call cannot write an unbounded batch of memories.
_MAX_FAILURE_RECORDS = 10
# How much of a tool result is kept in an action's summary (names/values hygiene
# aside, an episode is a summary, not a transcript).
_RESULT_SUMMARY_CHARS = 200


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class ManagerAgentMemory(AgentMemory):
    """Recall + record over the shared MemoryManager."""

    def __init__(self, manager: MemoryManager, config: MemoryConfig) -> None:
        self._manager = manager
        self._config = config

    # ------------------------------------------------------------------
    # Recall (spec Phase 20C/20N)
    # ------------------------------------------------------------------

    async def recall(
        self,
        goal: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        started = time.perf_counter()
        try:
            results = await self._manager.retrieve(
                goal,
                limit=self._config.agent_recall_limit,
                context=context or {},
                record_access=False,  # a read for context, not a usage signal
            )
        except Exception as exc:  # noqa: BLE001 - degrade to "no memory"
            logger.warning("Agent memory recall failed: %s", exc)
            return MemoryContext(query=goal, error=str(exc))

        min_score = self._config.agent_recall_min_score
        items = [
            MemoryItemView(
                id=r.memory.id,
                memory_type=r.memory.memory_type.value,
                content=r.memory.content,
                confidence=r.memory.confidence,
                score=r.score,
                reasons=tuple(r.explanation.reasons),
            )
            for r in results
            if r.score >= min_score
        ]
        latency_ms = (time.perf_counter() - started) * 1000.0
        return MemoryContext(query=goal, items=items, latency_ms=latency_ms)

    # ------------------------------------------------------------------
    # Recording (spec Phase 20F-20I)
    # ------------------------------------------------------------------

    async def record_run(self, state: AgentState) -> None:
        if not self._config.auto_remember:
            return
        if state.status is AgentStatus.CANCELLED:
            return
        # Only record meaningful runs: one that used a tool, or one that failed.
        if not state.tool_calls and state.status is not AgentStatus.FAILED:
            return

        episode = self._build_episode(state)
        await self._manager.remember_episode(episode)
        await self._record_failures(state, episode)

    def _build_episode(self, state: AgentState) -> Episode:
        actions = self._build_actions(state)
        outcome = self._build_outcome(state)
        return Episode(
            # Deterministic id = run id, so re-recording the same run REPLACES
            # rather than duplicates (spec Phase 20M).
            id=state.state_id,
            goal=state.goal,
            task_id=state.metadata.get("task_id"),
            session_id=state.session_id,
            environment={"agent": state.agent},
            actions=actions,
            outcome=outcome,
            lessons=self._lessons(state),
            started_at=_parse_iso(state.started_at) or utcnow(),
            ended_at=_parse_iso(state.completed_at),
        )

    def _build_actions(self, state: AgentState) -> list[ActionRecord]:
        results_by_call: dict[str, Any] = {}
        for r in state.tool_results:
            results_by_call[r.call_id] = r  # last result for a call wins

        actions: list[ActionRecord] = []
        for call in state.tool_calls:
            result = results_by_call.get(call.id)
            if result is None:
                status = OutcomeStatus.PENDING
                summary = ""
                error = None
                duration = None
            else:
                status = OutcomeStatus.SUCCESS if result.ok else OutcomeStatus.FAILURE
                summary = (result.content or "")[:_RESULT_SUMMARY_CHARS]
                error = result.error
                duration = result.duration_ms
            actions.append(
                ActionRecord(
                    name=call.name,
                    # Argument NAMES only -- never values (secret hygiene, Phase 20G).
                    arguments={"argument_names": list(call.argument_names)},
                    status=status,
                    result_summary=summary,
                    error=error,
                    duration_ms=duration,
                )
            )
        return actions

    @staticmethod
    def _build_outcome(state: AgentState) -> Outcome:
        if state.status is AgentStatus.FAILED:
            status = OutcomeStatus.FAILURE
        elif state.stopped_reason in (STOP_LOOP_GUARD, STOP_MAX_ITERATIONS):
            status = OutcomeStatus.PARTIAL
        elif state.status is AgentStatus.COMPLETED:
            status = OutcomeStatus.SUCCESS
        else:
            status = OutcomeStatus.UNKNOWN
        return Outcome(
            status=status,
            detail=state.stopped_reason or "",
            metrics=dict(state.metrics),
        )

    @staticmethod
    def _lessons(state: AgentState) -> list[str]:
        last = state.last_error
        return [last.message] if last is not None else []

    async def _record_failures(self, state: AgentState, episode: Episode) -> None:
        """
        Store a FailureRecord per failed tool call, with recovery (spec Phase 20I).

        A failure is "recovered" when a later successful tool result exists after
        it in the run; the recovering action's name is captured and the failure
        memory is linked to the episode. Recovery is only credited when the run
        did not itself end in failure. Ids are deterministic (run id + call id)
        so re-recording the same run replaces rather than duplicates (Phase 20M).
        """
        results = list(state.tool_results)
        run_failed = state.status is AgentStatus.FAILED

        recorded = 0
        for index, result in enumerate(results):
            if result.ok:
                continue
            if recorded >= _MAX_FAILURE_RECORDS:
                break

            # Recovery = the first successful tool result after this failure.
            recovery_name = ""
            recovery_status = OutcomeStatus.UNKNOWN
            if not run_failed:
                for later in results[index + 1 :]:
                    if later.ok:
                        recovery_name = later.name
                        recovery_status = OutcomeStatus.SUCCESS
                        break

            failure = FailureRecord(
                id=f"{state.state_id}:{result.call_id}",
                failure_type=result.error_type or "ToolError",
                error=result.error or "tool reported failure",
                action=result.name,
                context={"iteration": result.iteration, "goal": state.goal[:200]},
                environment={"agent": state.agent},
                attempted_recovery=recovery_name,
                successful_recovery=recovery_name,
                recovery_status=recovery_status,
            )
            failure_memory = await self._manager.remember_failure(failure)
            # Link the failure to the episode it occurred in, so retrieval can
            # expand from one to the other (spec Phase 7 graph expansion).
            await self._manager.link(
                failure_memory.id,
                episode.id,
                link_type="derived_from",
                metadata={"kind": "failure_in_episode"},
            )
            recorded += 1


def build_agent_memory(manager: MemoryManager, config: MemoryConfig) -> ManagerAgentMemory:
    """Factory used by the bootstrapper to wire the agent memory port."""
    return ManagerAgentMemory(manager, config)
