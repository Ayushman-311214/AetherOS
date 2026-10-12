# Workspace — Event-to-Panel Mapping & Performance

## Event-to-panel mapping

`WorkspaceAdapter` subscribes its handler to each concrete event class (the
bus dispatches by exact type) and turns every event into an `EventRow`:

| Event class | Panel(s) it reaches |
|---|---|
| `LiquiditySwept` / `LiquidityAbsorbed` / `LiquidityConsumed` / `LiquidityReplenished` / `LiquidityZone*` / `LiquidityImbalanceChanged` / `LiquidityRemoved` | EVENTS (row) + heatmap context |
| `MarketRegimeChanged` / `MarketRegimeDetected` | EVENTS (row) + analysis regime line |
| `SignalGenerated` / `SignalCritiqued` | EVENTS (row) + decision panel refresh |
| `PredictionCreated` / `PredictionResolved` / `PredictionPerformanceEvaluated` | EVENTS (row) |
| `AnalysisCompleted` / `ProbabilityEstimated` / `RiskAssessed` | EVENTS (row) + analysis/decision refresh |
| `MarketDataReceived` / `CandleClosed` / `MarketDataUpdated` | EVENTS (row) + market panel candles |
| `NewsSentimentAnalyzed` / `FundamentalsAnalyzed` / `MarketEventsDetected` | EVENTS (row) |
| `TradingReportGenerated` / `BacktestCompleted` / `PositionClosed` | EVENTS (row) |

Each row carries the event's own `timestamp`, `instrument_key` and `is_mock`
(mock events are tagged `[m]`) — the panel never invents a time or a source.

## Log streaming

`WorkspaceLogHandler` is a standard `logging.Handler` attached to the root
logger. It **taps the existing logging system** — it does not create a second
one. Every record the application already logs flows into the LOGS ring
buffer (bounded, `max_logs` default 200) with its level, logger name and
message, styled per level (INFO white, WARNING yellow, ERROR bold red, DEBUG
dim).

## Performance rules

- **No full-app redraw per tick.** `rich.live.Live` refreshes only the
  renderables that changed; the layout regions are rebuilt from state but the
  terminal diff is Rich's, which repaints only differing lines.
- **Analysis never blocks the renderer.** The render loop calls the driver's
  `refresh()` coroutine *between* renders — a slow market-data fetch delays
  the next refresh, it never freezes the UI thread. Panel builders are pure
  functions of state, so a render is always fast.
- **Bounded memory.** Events (60) and logs (200) are ring buffers; candles
  keep the last 20; the rest is the latest payload only. A day-long session
  uses the same RAM as the first minute.
- **Error isolation.** Each panel build is wrapped: a poisoned payload
  degrades that one panel to an error box, never crashing the workspace
  (pinned by `test_panel_error_never_crashes_workspace`).

## Extension points

- **A future GUI** consumes `WorkspaceState` exactly as the terminal does —
  the state and adapters contain no rendering.
- **New panels**: add a `panel_*` builder, register it in `_PANEL_BUILDERS`,
  and (optionally) a layout region + `KEYMAP` entry.
- **New event coverage**: extend the adapter's subscription list; the EVENTS
  panel renders whatever rows arrive.
- **In-app symbol/timeframe switching**: `WorkspaceState.set_symbol` /
  `set_timeframe` exist; wiring a prompt key is a small, isolated addition.
- **A second renderer** (web dashboard) can reuse `driver.build_refresh_fn`
  unchanged — it writes state, not pixels.
