from __future__ import annotations

import asyncio
from typing import Any

from ..core.logging import get_logger
from ..llm.agent_loop import LLMToolLoop
from .context import ContextBuilder
from .execution import ToolExecutionCoordinator
from .planner import AgentPlanner
from .state import AgentState
from .tasks.manager import TaskManager
from .tasks.models import Task
from .tasks.state import TaskStatus


class Agent:
    """High-level orchestrator for one task and one runtime state."""

    def __init__(
        self,
        *,
        task_manager: TaskManager,
        planner: AgentPlanner,
        context_builder: ContextBuilder,
        llm_loop: LLMToolLoop,
        execution_coordinator: ToolExecutionCoordinator,
    ) -> None:
        self._task_manager = task_manager
        self._planner = planner
        self._context_builder = context_builder
        self._llm_loop = llm_loop
        self._execution_coordinator = execution_coordinator
        self._logger = get_logger("agent")

    async def run(
        self,
        goal: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> AgentState:
        """Execute ``goal`` and return the state owned by this run."""

        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("Agent goal cannot be empty.")

        task = self._task_manager.create_task(
            normalized_goal,
            metadata=metadata,
        )
        state = AgentState(
            normalized_goal,
            agent="agent",
            metadata={"task_id": task.id, **(metadata or {})},
        )

        try:
            await state.start()
            await state.seed_conversation()

            self._task_manager.start_task(task.id)
            self._task_manager.set_plan(task.id, f"plan_{state.state_id}")
            self._task_manager.set_status(task.id, TaskStatus.READY)
            self._task_manager.set_status(task.id, TaskStatus.EXECUTING)

            await self._llm_loop.run_state(
                state,
                self._context_builder,
                self._planner,
                self._execution_coordinator,
            )

        except asyncio.CancelledError:
            if not state.is_terminal:
                await state.cancel()
            self._cancel_task(task)
            raise

        except Exception as exc:
            if not state.is_terminal:
                await state.fail(exc)
            self._fail_task(task, exc)
            self._logger.bind(
                task_id=task.id,
                error_type=type(exc).__name__,
            ).exception("Agent run failed.")
            raise

        if not state.is_terminal:
            await state.complete(
                state.final_response or "",
                stopped_reason="final_answer",
            )

        if state.status.value == "completed":
            self._task_manager.complete_task(task.id)
        elif state.status.value == "failed":
            self._fail_task(task, state.last_error.message if state.last_error else "Agent run failed.")

        return state

    def build_context(self, state: AgentState):
        """Build the bounded model projection for ``state``."""

        return self._context_builder.build(state)

    def _fail_task(self, task: Task, error: Exception | str) -> None:
        if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}:
            return
        self._task_manager.fail_task(task.id, str(error))

    def _cancel_task(self, task: Task) -> None:
        if task.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}:
            self._task_manager.cancel_task(task.id)

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    @property
    def planner(self) -> AgentPlanner:
        return self._planner

    @property
    def context_builder(self) -> ContextBuilder:
        return self._context_builder

    @property
    def llm_loop(self) -> LLMToolLoop:
        return self._llm_loop

    @property
    def execution_coordinator(self) -> ToolExecutionCoordinator:
        return self._execution_coordinator
