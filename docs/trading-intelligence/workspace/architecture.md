# Workspace — TUI Architecture

The terminal-native multi-window AetherOS workspace (Phase 7): one application,
multiple synchronized panels over the same live Trading Intelligence state.

## Not a GUI, not N processes

The workspace lives **inside the terminal** (Rich `Live` on the existing CLI
architecture — Rich is already a project dependency; the PySide6 HUD is a
separate GUI app and deliberately not used here). It is ONE AetherOS process
with ONE shared state — the panels are synchronized because they read the
same `WorkspaceState`, not because they coordinate with each other.

## The layering (the spec's critical rule)

```
Trading Intelligence            (services: market data, analysis, signal
        │                        engine, market-intel, heatmap — unchanged)
        ▼
EventBus / WorkspaceAdapter     (events -> EventRow; reads -> state fields)
        ▼
WorkspaceState                  (pure data: ring buffers + latest payloads)
        ▼
Panel builders                  (state -> rich renderables; no trading logic)
        ▼
Layout + TerminalWorkspace      (rich.layout grid + rich.live renderer)
        ▼
Terminal
```

**The TUI contains no trading logic.** Every number a panel shows was produced
by the intelligence layer; the panels only format. The same `WorkspaceState` a
future GUI would consume is exactly what the terminal renders — the
intelligence-to-presentation seam is renderer-independent.

## Module map

```
workspace/
  state.py     WorkspaceState + EventRow/LogLine/AgentRow/SystemMetric
  panels.py    panel_* builders -- one per view, pure read of state
  layout.py    build_layout -- the rich Layout grid (regions only)
  adapter.py   WorkspaceAdapter (EventBus -> state) + WorkspaceLogHandler
  driver.py    build_refresh_fn -- runs the REAL services into the adapter
  app.py       TerminalWorkspace + KEYMAP + build_workspace
```

## Launch

`workspace [symbol] [timeframe]` from the CLI (`cli/commands.py`) boots the
application, builds the workspace with the live `EventBus`, and runs the
render loop with the driver's refresh function wired.

## Honesty

- Every panel shows **real** data — an empty panel reads "no data yet",
  never a fabricated read.
- `is_mock` is surfaced (mock-tagged rows, `[mock data]` in the decision
  panel) so synthetic reads can never be drawn as real.
- The AGENTS panel shows only components that actually exist and are wired
  (Trading Intelligence, Market Analysis, Liquidity Analyzer, Prediction
  Monitor) — no fabricated agent status.
- Memory is a **status/placeholder boundary only** in the SYSTEM panel
  ("placeholder (not implemented)") — not implemented, per the phase rules.
