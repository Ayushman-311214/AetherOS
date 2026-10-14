"""
Phase 20 — Agent + Planner memory integration tests.

Drive the real AgentCore (scripted provider, real executor, isolated registry)
with the real ManagerAgentMemory over an in-memory MemoryManager, and pin the
lifecycle the spec names: recall before planning, graceful behaviour with no
memory / memory disabled / memory failing, and automatic episode + failure +
recovery recording after a run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from aetheros.agents.core import AgentCore
from aetheros.agents.memory_port import AgentMemory, MemoryContext, NullAgentMemory
from aetheros.agents.state import AgentState, AgentStatus
from aetheros.memory.config import MemoryConfig
from aetheros.memory.domain import MemoryType, Procedure, ProcedureStep
from aetheros.memory.integration.agent_memory import ManagerAgentMemory
from aetheros.memory.services.manager import MemoryManager
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


# -- tool doubles ------------------------------------------------------------

def echo(text: str) -> str:
    """A tool that succeeds."""
    return f"echo: {text}"


def boom() -> str:
    """A tool that always fails."""
    raise RuntimeError("tool exploded")


# -- fixtures ----------------------------------------------------------------

@pytest.fixture
def tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    registry.register(define(echo, category="general"))
    registry.register(define(boom, category="general"))
    return registry


@pytest_asyncio.fixture
async def mem():
    config = MemoryConfig.for_memory_db(Path(":memory:"), embedding_dim=64)
    manager = MemoryManager(config)
    await manager.initialize()
    try:
        yield manager, ManagerAgentMemory(manager, config)
    finally:
        await manager.shutdown()


def _build(provider: Any, registry: ToolRegistry, memory: AgentMemory) -> AgentCore:
    return AgentCore.from_provider(
        provider,
        registry=registry,
        executor=ToolExecutor(registry),
        memory=memory,
        system_prompt="Test system prompt.",
        recall_max_chars=1500,
    )


def _memory_observation(state: AgentState) -> str | None:
    for obs in state.observations:
        if obs.source == "memory":
            return obs.text
    return None


# -- Test 1: recall before planning -----------------------------------------

@pytest.mark.asyncio
async def test_recall_injects_relevant_memory(mem, make_provider, tools, answer) -> None:
    manager, agent_mem = mem
    await manager.remember(
        "The user plays songs on YouTube in the Brave browser.",
        entities=["YouTube", "Brave"],
        tags=["youtube"],
    )
    provider = make_provider([answer("Playing the song.")])
    core = _build(provider, tools, agent_mem)

    result = await core.run("Play a song on YouTube")

    assert result.ok
    injected = _memory_observation(result.state)
    assert injected is not None
    assert "YouTube" in injected
    # Advisory framing is present (current state takes precedence over memory).
    assert "take precedence" in injected


# -- Test 2: no relevant memory ----------------------------------------------

@pytest.mark.asyncio
async def test_no_memory_still_plans_normally(mem, make_provider, tools, answer) -> None:
    _, agent_mem = mem
    provider = make_provider([answer("Done.")])
    core = _build(provider, tools, agent_mem)

    result = await core.run("Some entirely unrelated goal about quantum frogs")

    assert result.ok
    assert _memory_observation(result.state) is None


# -- Test 3: memory disabled (null object) -----------------------------------

@pytest.mark.asyncio
async def test_memory_disabled_runs_normally(make_provider, tools, answer) -> None:
    provider = make_provider([answer("Done.")])
    core = _build(provider, tools, NullAgentMemory())

    result = await core.run("Do the thing")

    assert result.ok
    assert _memory_observation(result.state) is None


# -- Test 4: memory failure must not break the task --------------------------

class _FailingMemory(AgentMemory):
    async def recall(self, goal, *, session_id=None, context=None) -> MemoryContext:
        raise RuntimeError("recall exploded")

    async def record_run(self, state) -> None:
        raise RuntimeError("record exploded")


@pytest.mark.asyncio
async def test_memory_failure_does_not_break_task(make_provider, tools, answer) -> None:
    provider = make_provider([answer("Still done.")])
    core = _build(provider, tools, _FailingMemory())

    result = await core.run("Carry on despite memory errors")

    assert result.ok
    assert result.final_response == "Still done."
    assert _memory_observation(result.state) is None


# -- Test 5: successful task creates an episode ------------------------------

@pytest.mark.asyncio
async def test_successful_task_creates_episode(mem, make_provider, tools, tool_calls, answer) -> None:
    manager, agent_mem = mem
    provider = make_provider(
        [tool_calls(("echo", {"text": "hi"})), answer("All done.")]
    )
    core = _build(provider, tools, agent_mem)

    result = await core.run("Echo a greeting")
    assert result.ok

    episodes = await manager._repo.list_by(memory_type="episodic")
    assert len(episodes) == 1
    episode_data = episodes[0].data["episode"]
    assert episode_data["goal"] == "Echo a greeting"
    assert episode_data["outcome"]["status"] == "success"
    assert any(a["name"] == "echo" for a in episode_data["actions"])
    # Argument values are not stored -- names only (secret hygiene, Phase 20G).
    assert episode_data["actions"][0]["arguments"] == {"argument_names": ["text"]}


# -- Test 6: failed tool creates a failure record ----------------------------

@pytest.mark.asyncio
async def test_failed_tool_creates_failure_record(mem, make_provider, tools, tool_calls, answer) -> None:
    manager, agent_mem = mem
    provider = make_provider([tool_calls(("boom", {})), answer("Gave up on that.")])
    core = _build(provider, tools, agent_mem)

    result = await core.run("Run the broken tool")
    assert result.ok  # the model recovered by answering

    failures = await manager._repo.list_by(memory_type="failure")
    assert len(failures) == 1
    failure_data = failures[0].data["failure"]
    assert failure_data["action"] == "boom"
    assert "exploded" in failure_data["error"]


# -- Test 7: recovery relationship is recorded -------------------------------

@pytest.mark.asyncio
async def test_recovery_relationship_recorded(mem, make_provider, tools, tool_calls, answer) -> None:
    manager, agent_mem = mem
    provider = make_provider(
        [
            tool_calls(("boom", {})),           # fails
            tool_calls(("echo", {"text": "ok"})),  # recovers
            answer("Recovered and done."),
        ]
    )
    core = _build(provider, tools, agent_mem)

    result = await core.run("Fail then recover")
    assert result.ok

    failures = await manager._repo.list_by(memory_type="failure")
    assert len(failures) == 1
    failure = failures[0]
    assert failure.data["failure"]["successful_recovery"] == "echo"
    assert failure.data["failure"]["recovery_status"] == "success"

    # The failure is linked to the episode it happened in.
    episodes = await manager._repo.list_by(memory_type="episodic")
    episode_id = episodes[0].id
    neighbours = await manager._repo.linked_ids(failure.id)
    assert any(nid == episode_id for nid, _, _ in neighbours)


# -- Test 8: a relevant procedure is available in recall ---------------------

@pytest.mark.asyncio
async def test_procedure_is_recalled(mem) -> None:
    manager, agent_mem = mem
    await manager.remember_procedure(
        Procedure(
            name="add_rsi_tradingview",
            goal="Add the RSI indicator on TradingView",
            steps=[ProcedureStep(action="open_indicators"), ProcedureStep(action="search_rsi")],
            success_count=5,
        )
    )
    ctx = await agent_mem.recall("How do I add RSI to TradingView?")
    assert not ctx.is_empty
    assert any(i.memory_type == MemoryType.PROCEDURAL.value for i in ctx.items)


# -- Test 9: current reality overrides stale memory --------------------------

@pytest.mark.asyncio
async def test_recall_frames_stale_ui_as_advisory(mem) -> None:
    manager, agent_mem = mem
    await manager.remember(
        "The TradingView Indicators button was at coordinate 742,185.",
        entities=["TradingView"],
        tags=["ui"],
    )
    ctx = await agent_mem.recall("click the Indicators button on TradingView")
    lines = ctx.to_observation_lines(max_chars=1500)
    text = "\n".join(lines)
    # The stale coordinate is surfaced, but explicitly as historical guidance
    # that current vision/state overrides -- never as an instruction to replay.
    assert "742,185" in text
    assert "take precedence" in text
    assert "verify against" in text


# -- Test 10: duplicate prevention -------------------------------------------

@pytest.mark.asyncio
async def test_recording_same_run_twice_does_not_duplicate(mem, make_provider, tools, tool_calls, answer) -> None:
    manager, agent_mem = mem
    provider = make_provider([tool_calls(("echo", {"text": "hi"})), answer("done")])
    core = _build(provider, tools, agent_mem)
    result = await core.run("Echo once")

    # Re-record the same finished run: deterministic ids make this a REPLACE.
    await agent_mem.record_run(result.state)

    episodes = await manager._repo.list_by(memory_type="episodic")
    assert len(episodes) == 1


# -- auto_remember gate ------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_remember_off_skips_recording(make_provider, tools, tool_calls, answer) -> None:
    import dataclasses

    config = MemoryConfig.for_memory_db(Path(":memory:"), embedding_dim=64)
    config = dataclasses.replace(config, auto_remember=False)
    manager = MemoryManager(config)
    await manager.initialize()
    try:
        agent_mem = ManagerAgentMemory(manager, config)
        provider = make_provider([tool_calls(("echo", {"text": "hi"})), answer("done")])
        core = _build(provider, tools, agent_mem)
        await core.run("Echo without recording")

        episodes = await manager._repo.list_by(memory_type="episodic")
        assert episodes == []
    finally:
        await manager.shutdown()
