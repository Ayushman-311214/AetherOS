# Unified Terminal ↔ HUD Interaction

> **Purpose**
>
> The Terminal (CLI) and the HUD (voice/desktop overlay) are **two presentation
> layers over one agent**. A request enters the agent system **exactly once**,
> and **both** front ends observe that single run over the shared `EventBus`.
> This document is the architecture of that fix.

---

## The problem this fixes

Before the fix, the Terminal and the HUD behaved as independent systems:

- A command typed in the Terminal ran the agent, but the HUD showed nothing —
  no request, no thinking, no tool activity, no response.
- A voice/HUD request never surfaced in the Terminal.

Each front end was, in effect, driving its own execution and rendering its own
output. There was no single source of truth for a turn.

## The principle

```
                 ┌────────────┐        ┌────────────┐
   Terminal ───▶ │            │        │            │
                 │ Interaction│──────▶ │ AgentCore  │  (ONE agent)
   Voice/HUD ──▶ │  Gateway   │  run() │            │
                 └────────────┘        └─────┬──────┘
                                             │ emit_trace(...)
                                             ▼
                                      ┌────────────┐
                                      │  EventBus  │  (ONE stream)
                                      └─────┬──────┘
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                   Terminal renderer   HUDService        LiveTraceUI
                   (subscriber)        (subscriber)      (dev trace)
```

- **One entry.** Every front end submits through the `InteractionGateway`, which
  calls the *same* `AgentCore.run(...)`. A request enters the agent exactly once.
- **One stream.** The run emits its ordinary `TraceEvent` lifecycle to the shared
  `EventBus`. Every UI is a **subscriber** to that stream.
- **Renderers, not routers.** No front end pulls another's state, and no emit
  site branches on the origin (`if source == "terminal": print()`). The agent
  emits once; each subscriber decides what to draw.

## Components

### `InteractionGateway` — `agents/gateway.py`

The one seam a front end submits a turn through. It plans nothing, chooses no
tools, formats no output. Its whole job is *tag the origin, run the one agent*:

```python
with interaction_scope(source=source, session_id=self._session_id):
    return await self._agent.run(goal, **run_kwargs)
```

It mints one `session_id` for the life of the process (a single-user desktop
runtime is one session) and holds **no** "current request" that two overlapping
turns could clobber — each turn carries its own scope and ids.

### `interaction_scope` / `InteractionContext` — `core/observability/interaction.py`

The scope rides a `contextvars.ContextVar`. Opened around the awaited
`agent.run(...)`, it makes `source` / `session_id` / `request_id` readable by
every `emit_trace(...)` call made *inside* that run — without threading an
argument through the dozen emit sites in the loop. Because the whole turn runs
in one task, the contextvar propagates across every `await`.

> **`source` is a label, never a route.** It tints what a UI shows and lets a
> developer tell terminal turns from voice turns while debugging. It **never**
> decides which UI sees a run.

### `TraceEvent` on the `EventBus`

The run emits its existing lifecycle — `INPUT_RECEIVED`, `AGENT_STARTED`,
`AGENT_ITERATION_STARTED`, `TOOL_SELECTED`, `TOOL_EXECUTION_STARTED/COMPLETED/
FAILED`, `FINAL_RESPONSE_CREATED`, `ERROR` … — through the module-global
publisher to the shared `EventBus`. `run_id` (the agent's `state_id`) correlates
one turn end to end; grouping events by `run_id` cleanly separates concurrent
turns.

### Subscribers

- **Terminal renderer** — observes the stream and renders CLI output.
- **`HUDService`** (`hud/service.py`) — subscribes to `TraceEvent`; `_render_trace`
  maps the lifecycle onto HUD state (`THINKING` → `EXECUTING` → `IDLE`/`ERROR`).
- **`LiveTraceUI`** (`core/observability/ui.py`) — the developer's live dashboard,
  owned by the `TraceRecorder`. Observer-only; downgrades silently on a non-TTY.

## Concurrency

Two overlapping turns stay separate because correlation rests on
`request_id` / `session_id` / `run_id`, **not** on any global mutable "current
request". Each turn opens its own `interaction_scope`, so each run's events carry
their own origin and ids; the shared `session_id` marks that one desktop session
owns both.

## De-duplication (voice)

The HUD's trace handler deliberately **ignores voice-sourced events**
(`if event.source == "voice"`). A spoken turn's visuals are owned by the richer
voice vocabulary rather than being driven twice off the same stream. This is
de-duplication of *rendering*, not routing of *execution* — the one run still
happens, and the Terminal and dev trace still observe it.

## Privacy & safety in the UI

- No hidden chain-of-thought or token-by-token private reasoning is displayed;
  UIs show safe status (e.g. "Understanding request…").
- Tool events carry **argument names only, never values** — arguments may hold
  secrets. The trace record does not retain argument values.
- No API keys or secrets appear in logs or events.

## Acceptance matrix

`tests/test_unified_interaction.py` drives the **real** `EventBus` +
`InteractionGateway` + `AgentCore` (real planner, policy, `ToolExecutor`) with
only a scripted provider, a counting executor, and the HUD process double:

1. A terminal turn runs one agent and both the terminal observer and the real
   `HUDService` settle on the same answer (one `AGENT_STARTED`, one `run_id`).
2. A voice turn is `source`-tagged on every event, and the HUD skips it (de-dup).
3. Two overlapping turns keep distinct `run_id`s and origins under one session —
   no cross-talk.
4. An LLM-only turn produces a final answer and emits **no** tool events.
5. A failing tool surfaces `TOOL_EXECUTION_FAILED` (no exception escapes the run).
6. Opening lifecycle events are delivered **during** execution, not batched at the
   end (a mid-run tool body already sees `AGENT_STARTED` / `TOOL_SELECTED`).
7. Subscribe/unsubscribe is idempotent across an exit/restart; the HUD still
   observes a turn after reconnecting.

## Rules of the road

- Front ends are **presentation/input only**. Agent / Task / LLM execution has
  **one** source of truth: `AgentCore`.
- Submit through the `InteractionGateway`; never call `agent.run` directly from a
  front end when a gateway is available.
- To make a UI reflect a run, **subscribe to the stream** — never reach into
  another UI's private state, and never branch an emit site on `source`.
- Reuse the shared singletons (Agent, EventBus, TaskManager, Planner) via DI;
  do not duplicate them per front end.
