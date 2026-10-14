# Phase 7 Audit — Terminal-Native Trading Intelligence Workspace

## Reused (not rebuilt)

- **Rich** (`rich.live.Live` / `rich.layout` / `rich.panel` / `rich.table`) —
  already a project dependency; terminal-native, no new dependency added
  (Textual is not installed and was not introduced; the PySide6 HUD is a GUI
  app and deliberately out of scope).
- **The existing CLI architecture** — the workspace is a first-class CLI
  command (`workspace [symbol] [timeframe]`) in `cli/commands.py`, booting the
  same `AetherOSBootstrapper` every other command uses.
- **The production intelligence services** — `MarketDataService`,
  `AnalysisService`, `SignalEngineService`, `MarketIntelService`,
  `HeatmapService` and the shared `EventBus` are what the panels render; the
  TUI contains zero trading logic.
- **The existing logging system** — `WorkspaceLogHandler` is a
  `logging.Handler` tapping the stream that already flows; no second logging
  system.

## New (`src/aetheros/workspace/`)

| Module | Contents |
|---|---|
| `state.py` | `WorkspaceState` + `EventRow`/`LogLine`/`AgentRow`/`SystemMetric` — bounded ring buffers, pure data |
| `panels.py` | the nine `panel_*` builders — one per view, pure reads of state, honest "no data yet" |
| `layout.py` | `build_layout` — the rich Layout grid (the spec's ASCII layout) |
| `adapter.py` | `WorkspaceAdapter` (exact-type EventBus subscription → EventRows; latest payload setters) + `WorkspaceLogHandler` |
| `driver.py` | `build_refresh_fn` — runs the REAL services into the adapter (the only code touching intelligence) |
| `app.py` | `TerminalWorkspace` (render loop + `handle_key`) + `KEYMAP` + `build_workspace` |
| CLI | the `workspace` command + help entry |

## The spec's panels → implementation

MARKET (candles/price/volume/VWAP/structure + liquidity markers), ANALYSIS
(regime/structure/volume/momentum/liquidity/pressure + supporting &
contradicting evidence), LIQUIDITY & HEATMAP (the real `HeatmapService`
surface projection — no faked graphical data), SIGNALS (direction/probability/
confidence/R:R/invalidation from the real assessment), LOGS (the real log
stream, level-styled, filterable by level), AGENTS (only components that
actually exist), DATA SOURCES + SYSTEM HEALTH + MEMORY STATUS (the system
panel; memory is an honest placeholder boundary, NOT implemented).

## Architecture boundary

```
Trading Intelligence → EventBus/adapter → WorkspaceState → panels → renderer
```

The same `WorkspaceState` is the seam a future GUI consumes — the
view-model/state layer is renderer-independent, and the driver writes state,
not pixels.

## Tests

`tests/workspace/test_workspace.py` — 23 tests: state ring buffers/mutations,
all panels initializing on empty (honest), real-data rendering (market/
decision/heatmap/analysis/events/logs/agents/system), layout regions filling,
full-state render, error resilience (poisoned payload degrades one panel),
keyboard navigation (all 8 spec panels + pause/quit/unknown key), adapter
event streaming (real bus publish → EVENTS rows), detail extraction, log
handler tapping real logging, component tracking only-when-real.

## Remaining Phase 8 work

- In-app symbol/timeframe prompt keys (`s`/`t` wiring exists in state).
- Interactive panel resizing (rich layout ratios reflow on terminal resize;
  explicit ratio controls are an extension).
- Full-screen single-panel focus mode.
- A live order-book/tape source for the heatmap panel (currently honest
  "no source" without ccxt wired).
