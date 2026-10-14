from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from aetheros.agents.agent import Agent
from aetheros.agents.state import AgentStatus
from aetheros.agents.tasks.manager import TaskManager
from aetheros.agents.tasks.state import TaskStatus


class RecordingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    async def plan(self, state, context):
        self.calls += 1
        return SimpleNamespace()


class CompletingLoop:
    def __init__(self) -> None:
        self.calls = []
        self.contexts = []

    async def run_state(self, state, context_builder, planner, coordinator):
        self.calls.append((state, planner, coordinator))
        self.contexts.append(context_builder.build(state))
        await planner.plan(state, self.contexts[-1])
        await state.complete("done")


class CancellingLoop:
    async def run_state(self, state, context_builder, planner, coordinator):
        raise asyncio.CancelledError


class FailingLoop:
    async def run_state(self, state, context_builder, planner, coordinator):
        raise RuntimeError("provider failed")


class ContextBuilder:
    def build(self, state):
        return {"state_id": state.state_id}


@pytest.fixture
def agent_parts():
    manager = TaskManager()
    planner = RecordingPlanner()
    loop = CompletingLoop()
    coordinator = object()
    agent = Agent(
        task_manager=manager,
        planner=planner,
        context_builder=ContextBuilder(),
        llm_loop=loop,
        execution_coordinator=coordinator,
    )
    return agent, manager, planner, loop, coordinator


@pytest.mark.asyncio
async def test_agent_rejects_empty_goal(agent_parts):
    agent, manager, *_ = agent_parts

    with pytest.raises(ValueError, match="cannot be empty"):
        await agent.run("   ")

    assert manager.list_tasks() == []


@pytest.mark.asyncio
async def test_agent_runs_one_state_and_completes_task(agent_parts):
    agent, manager, planner, loop, coordinator = agent_parts

    state = await agent.run("finish the task", metadata={"source": "test"})

    task = manager.list_tasks()[0]
    assert task.goal == "finish the task"
    assert task.plan_id == f"plan_{state.state_id}"
    assert task.status is TaskStatus.COMPLETED
    assert state.status is AgentStatus.COMPLETED
    assert state.final_response == "done"
    assert planner.calls == 1
    assert loop.calls[0][0] is state
    assert loop.calls[0][2] is coordinator
    assert loop.contexts[0]["state_id"] == state.state_id


@pytest.mark.asyncio
async def test_agent_creates_a_new_state_for_each_run(agent_parts):
    agent, manager, *_ = agent_parts

    first = await agent.run("first")
    second = await agent.run("second")

    assert first is not second
    assert first.state_id != second.state_id
    assert first.goal == "first"
    assert second.goal == "second"
    assert len(manager.list_tasks()) == 2


@pytest.mark.asyncio
async def test_cancellation_marks_state_and_task(agent_parts):
    agent, manager, *_ = agent_parts
    agent._llm_loop = CancellingLoop()

    with pytest.raises(asyncio.CancelledError):
        await agent.run("cancel me")

    task = manager.list_tasks()[0]
    assert task.status is TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_loop_failure_marks_state_and_task(agent_parts):
    agent, manager, *_ = agent_parts
    agent._llm_loop = FailingLoop()

    with pytest.raises(RuntimeError, match="provider failed"):
        await agent.run("fail me")

    task = manager.list_tasks()[0]
    assert task.status is TaskStatus.FAILED
