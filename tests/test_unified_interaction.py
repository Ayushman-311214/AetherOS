"""
Phase 15 -- the unified Terminal <-> HUD interaction acceptance matrix.

This file is the proof the interaction fix demands: a request enters the one
shared :class:`~aetheros.agents.core.AgentCore` *exactly once*, through the
:class:`~aetheros.agents.gateway.InteractionGateway`, and *both* front ends
observe that single run over the shared :class:`EventBus`. Nothing here reaches
into a UI's private state to make it update -- the gateway opens an interaction
scope, the agent emits its ordinary trace lifecycle, and the same
:class:`TraceEvent` stream drives a terminal-style renderer and the real
:class:`HUDService` alike (PHASE 10: Agent -> EventBus -> both renderers, never
``if source == ...: print()``).

The doubles are the same two the CLI agent tests use -- a scripted provider so a
turn is deterministic with no model, and a counting executor that witnesses
every delegation -- plus the HUD's own child-process double. Everything else is
the real thing: real planner, real policy gate, real ToolExecutor, real bus,
real gateway, real HUD subscription.

``emit_trace`` publishes through the module-global publisher, so each test
installs its bus with :func:`set_event_bus` (restored afterwards) -- otherwise
the agent's events would have nowhere to go.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import pytest_asyncio

from aetheros.agents.core import AgentCore
from aetheros.agents.gateway import InteractionGateway
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.core.observability.events import (
    TraceEvent,
    TraceEventType,
    TraceStatus,
)
from aetheros.hud.config import HUDConfig
from aetheros.hud.service import HUDService
from aetheros.hud.state import HUDState
from aetheros.runtime.events.event_bus import EventBus
from aetheros.runtime.events.publisher import set_event_bus
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry

from hud_support import FakeHUDProcess

# ==============================================================
# Doubles and helpers
# ==============================================================


class _CountingExecutor(ToolExecutor):
    """The real executor, recording every tool it was actually asked to run.

    A name in ``asked`` is proof the call reached ``ToolExecutor`` -- which the
    coordinator does only after the policy returns ALLOW -- rather than being
    skipped or short-circuited.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


class _Renderer:
    """A terminal-style observer.

    It subscribes to the same bus a real terminal renderer would and keeps every
    trace event it is handed, in order. It stands in for "the terminal is
    watching the shared stream" without asserting on printed characters.
    """

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    async def handle(self, event: TraceEvent) -> None:
        self.events.append(event)

    def of_type(self, kind: TraceEventType) -> list[TraceEvent]:
        return [e for e in self.events if e.event_type is kind]

    def run_ids(self) -> set[str]:
        return {e.run_id for e in self.events if e.run_id is not None}


def _build_agent(
    provider: Any,
    registry: ToolRegistry,
    *,
    policy: PolicyEngine | None = None,
) -> tuple[AgentCore, _CountingExecutor]:
    """The one shared agent, built over the real planner/policy/executor."""

    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Test system prompt.",
    )
    return core, executor


# -- tool bodies the turns drive --------------------------------------------


def _mouse_position() -> str:
    """A read-only tool: report a fixed cursor position."""

    return "position: x=7, y=11"


def _boom() -> str:
    """A tool that fails, so the failure path has something to surface."""

    raise RuntimeError("the tool exploded")


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def wired():
    """Install a fresh bus as the global publisher target, restored afterwards.

    ``emit_trace`` reaches subscribers only through the module-global publisher,
    so the bus the agent publishes to and the bus the UIs subscribe to must be
    one and the same. The previous global is restored so a bus leaked from one
    test never changes how another test's ``emit_trace`` behaves.
    """

    import aetheros.runtime.events.publisher as publisher_mod

    previous = publisher_mod._event_bus
    bus = EventBus()
    set_event_bus(bus)
    try:
        yield bus
    finally:
        publisher_mod._event_bus = previous


@pytest_asyncio.fixture
async def hud(wired):
    """A started :class:`HUDService` subscribed to the wired bus.

    Uses the process double so nothing Qt or subprocess exists; stopped again on
    teardown so its pump task does not outlive the test's event loop.
    """

    service = HUDService(
        config=HUDConfig(enabled=True),
        event_bus=wired,
        process=FakeHUDProcess(),
    )
    assert await service.start() is True
    try:
        yield service
    finally:
        await service.stop()


# ==============================================================
# 1. A terminal turn runs one agent and lights BOTH UIs
# ==============================================================


class TestTerminalTurnEntersOnceAndBothObserve:
    @pytest.mark.asyncio
    async def test_one_agent_run_is_observed_by_terminal_and_hud(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        define: Any,
        tool_calls: Any,
        answer: Any,
        wired: EventBus,
        hud: HUDService,
    ) -> None:
        renderer = _Renderer()
        await wired.subscribe(TraceEvent, renderer.handle)

        policy = PolicyEngine(PolicyConfig())
        registry.register(
            define(_mouse_position, name="mouse_position", category="desktop")
        )
        provider = make_provider(
            [
                tool_calls(("mouse_position", {})),
                answer("The cursor is at 7, 11."),
            ]
        )
        core, executor = _build_agent(provider, registry, policy=policy)
        gateway = InteractionGateway(core)

        result = await gateway.submit("where is my mouse?", source="terminal")

        # Entered the agent exactly once: a single AGENT_STARTED, and one
        # correlation id across the whole stream (PHASE 13).
        assert len(renderer.of_type(TraceEventType.AGENT_STARTED)) == 1
        assert len(renderer.run_ids()) == 1

        # The terminal-side observer saw the whole lifecycle over the bus...
        assert renderer.of_type(TraceEventType.INPUT_RECEIVED)
        assert renderer.of_type(TraceEventType.TOOL_SELECTED)
        assert renderer.of_type(TraceEventType.FINAL_RESPONSE_CREATED)

        # ...and the HUD, from the *same* stream, settled with the same answer.
        assert hud.snapshot.state is HUDState.IDLE
        assert "The cursor is at 7, 11." in hud.snapshot.response

        # The one run actually did the work, gate included.
        assert core.policy is policy
        assert executor.asked == ["mouse_position"]
        assert result.final_response == "The cursor is at 7, 11."


# ==============================================================
# 2. A voice turn is source-tagged, and the HUD does not double-drive
# ==============================================================


class TestVoiceTurnIsTaggedAndNotDoubleRendered:
    @pytest.mark.asyncio
    async def test_voice_events_are_tagged_and_hud_skips_them(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        wired: EventBus,
        hud: HUDService,
    ) -> None:
        renderer = _Renderer()
        await wired.subscribe(TraceEvent, renderer.handle)

        provider = make_provider(generate_result="Spoken reply.")
        core, _executor = _build_agent(provider, registry)
        gateway = InteractionGateway(core)

        await gateway.submit("hello", source="voice")

        # Every event of the turn is labelled voice -- the interaction scope
        # stamped them, without any emit site passing ``source`` itself.
        assert renderer.events
        assert all(e.source == "voice" for e in renderer.events)

        # De-duplication (PHASE 10, and still not routing): the HUD's trace
        # handler deliberately ignores voice-sourced events, so the spoken-turn
        # visuals stay owned by the richer voice vocabulary rather than being
        # driven twice. With no voice handler firing in this test, the HUD's
        # trace-driven fields stay exactly as ``start()`` left them.
        assert hud.snapshot.state is HUDState.OFFLINE
        assert hud.snapshot.response == ""


# ==============================================================
# 3. Concurrent turns do not cross-talk
# ==============================================================


class TestConcurrentTurnsDoNotCrossTalk:
    @pytest.mark.asyncio
    async def test_two_overlapping_turns_keep_distinct_ids_and_origins(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        wired: EventBus,
    ) -> None:
        renderer = _Renderer()
        await wired.subscribe(TraceEvent, renderer.handle)

        # One shared agent, two overlapping turns: the real test of PHASE 13's
        # "no global current request" -- each turn must carry its own scope and
        # ids rather than clobbering a shared slot.
        provider = make_provider(generate_result="ok")
        core, _executor = _build_agent(provider, registry)
        gateway = InteractionGateway(core)

        await asyncio.gather(
            gateway.submit("from the terminal", source="terminal"),
            gateway.submit("from voice", source="voice"),
        )

        by_run: dict[str, set[str]] = {}
        for event in renderer.events:
            if event.run_id is None:
                continue
            by_run.setdefault(event.run_id, set()).add(event.source or "")

        # Two turns => two correlation ids, and neither turn's events borrowed
        # the other's origin: each run id maps to exactly one source.
        assert len(by_run) == 2
        assert all(len(sources) == 1 for sources in by_run.values())
        assert {next(iter(sources)) for sources in by_run.values()} == {
            "terminal",
            "voice",
        }

        # One desktop session owns both turns: the session id is shared while the
        # per-turn ids differ.
        sessions = {e.session_id for e in renderer.events if e.session_id}
        assert len(sessions) == 1


# ==============================================================
# 4. An LLM-only turn emits a final answer and no tool events
# ==============================================================


class TestLLMOnlyTurn:
    @pytest.mark.asyncio
    async def test_no_tool_turn_has_a_final_response_and_no_tool_events(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        wired: EventBus,
        hud: HUDService,
    ) -> None:
        renderer = _Renderer()
        await wired.subscribe(TraceEvent, renderer.handle)

        # Empty registry: the agent advertises no tools, so the first answer ends
        # the run without any tool selection or execution.
        provider = make_provider(generate_result="Just a sentence.")
        core, executor = _build_agent(provider, registry)
        gateway = InteractionGateway(core)

        await gateway.submit("say something", source="terminal")

        assert renderer.of_type(TraceEventType.FINAL_RESPONSE_CREATED)
        assert renderer.of_type(TraceEventType.TOOL_SELECTED) == []
        assert renderer.of_type(TraceEventType.TOOL_EXECUTION_STARTED) == []
        assert executor.asked == []

        assert hud.snapshot.state is HUDState.IDLE
        assert "Just a sentence." in hud.snapshot.response


# ==============================================================
# 5. A failing tool surfaces as a failed tool event
# ==============================================================


class TestToolFailureSurfaces:
    @pytest.mark.asyncio
    async def test_a_failing_tool_emits_tool_execution_failed(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        define: Any,
        tool_calls: Any,
        answer: Any,
        wired: EventBus,
    ) -> None:
        renderer = _Renderer()
        await wired.subscribe(TraceEvent, renderer.handle)

        policy = PolicyEngine(PolicyConfig())
        registry.register(define(_boom, name="boom", category="test"))
        provider = make_provider(
            [
                tool_calls(("boom", {})),
                answer("I could not run that."),
            ]
        )
        core, executor = _build_agent(provider, registry, policy=policy)
        gateway = InteractionGateway(core)

        await gateway.submit("run the tool", source="terminal")

        # The failure is observable on the shared stream, tagged FAILED and named
        # by the tool that failed -- no exception escaped the run.
        failures = renderer.of_type(TraceEventType.TOOL_EXECUTION_FAILED)
        assert failures
        assert failures[0].status is TraceStatus.FAILED
        assert failures[0].message == "boom"
        # The executor was still asked (the gate allowed it); the failure came
        # from the tool body, not from the call being skipped.
        assert executor.asked == ["boom"]


# ==============================================================
# 6. Events are delivered DURING execution, not only at the end
# ==============================================================


class TestLiveUpdatesDuringExecution:
    @pytest.mark.asyncio
    async def test_the_bus_delivers_opening_events_before_the_run_finishes(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        define: Any,
        tool_calls: Any,
        answer: Any,
        wired: EventBus,
    ) -> None:
        seen: list[TraceEvent] = []

        async def collect(event: TraceEvent) -> None:
            seen.append(event)

        await wired.subscribe(TraceEvent, collect)

        # The probe tool inspects, from inside the still-running turn, what the
        # subscriber has already received. If the bus batched events until the
        # run returned, none of the opening lifecycle would be visible yet.
        witnessed: dict[str, bool] = {}

        def probe() -> str:
            witnessed["agent_started_seen"] = any(
                e.event_type is TraceEventType.AGENT_STARTED for e in seen
            )
            witnessed["tool_selected_seen"] = any(
                e.event_type is TraceEventType.TOOL_SELECTED for e in seen
            )
            return "probed"

        policy = PolicyEngine(PolicyConfig())
        registry.register(define(probe, name="probe", category="test"))
        provider = make_provider(
            [
                tool_calls(("probe", {})),
                answer("Done."),
            ]
        )
        core, _executor = _build_agent(provider, registry, policy=policy)
        gateway = InteractionGateway(core)

        await gateway.submit("go", source="terminal")

        # The tool body ran mid-turn and already saw the run's opening events:
        # the bus delivered them live (PHASE 9), not batched at completion.
        assert witnessed.get("agent_started_seen") is True
        assert witnessed.get("tool_selected_seen") is True


# ==============================================================
# 7. Subscribe/unsubscribe is idempotent across an exit/restart
# ==============================================================


class TestReconnectIsIdempotent:
    @pytest.mark.asyncio
    async def test_restart_leaves_one_subscription_and_still_observes(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        wired: EventBus,
    ) -> None:
        service = HUDService(
            config=HUDConfig(enabled=True),
            event_bus=wired,
            process=FakeHUDProcess(),
        )

        assert await service.start() is True
        assert wired.listener_count(TraceEvent) == 1

        # A redundant start must not double-subscribe.
        assert await service.start() is True
        assert wired.listener_count(TraceEvent) == 1

        await service.stop()
        assert wired.listener_count(TraceEvent) == 0

        # Restart: one subscription again, and the HUD still observes a turn from
        # the shared stream (PHASE 15: exit/restart reconnect).
        assert await service.start() is True
        assert wired.listener_count(TraceEvent) == 1

        provider = make_provider(generate_result="Back online.")
        core, _executor = _build_agent(provider, registry)
        gateway = InteractionGateway(core)

        await gateway.submit("still there?", source="terminal")

        assert service.snapshot.state is HUDState.IDLE
        assert "Back online." in service.snapshot.response

        await service.stop()



