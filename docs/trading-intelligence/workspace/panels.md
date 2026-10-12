# Workspace — Panel Responsibilities & Keyboard Shortcuts

## The default layout

```
┌───────────────── AETHEROS | symbol | tf | LIVE/PAUSED | clock ──────────┐
├────────────── LIVE MARKET ──────────────┬── AETHEROS DECISION ─────────┤
│  sparkline, OHLC, VWAP, trend, markers  │  direction, probability,     │
│                                         │  confidence, R:R, invalid.  │
├──────────────── LIQUIDITY HEATMAP ──────┴──────────────────────────────┤
│  the real HeatmapService surface projection (time x price intensity)   │
├───────── EVIDENCE / ANALYSIS ───────────┬──────── LIVE EVENTS ─────────┤
│  regime, features, supporting and       │  real bus events, newest     │
│  contradicting evidence split           │  first, mock-tagged          │
├──────────────── LOGS ───────────────────┼──────── AGENTS ──────────────┤
│  the existing application log stream    │  real component status only  │
└─────────────────────────────────────────┴──────────────────────────────┘
```

## Panel responsibilities

| Panel (key) | Shows | Source |
|---|---|---|
| **market** (`1`) | candles sparkline, OHLC, VWAP, structure trend, sweep/absorption markers | `MarketDataService` + intel technical/structure |
| **analysis** (`2`) | regime, trend/momentum/volume/flow features, supporting + contradicting evidence | `MarketIntelService` + `SignalEngineService` |
| **liquidity** (`3`) | the time×price liquidity heatmap (zones/persistence/sweeps encoded in the projection) | `HeatmapService` surface |
| **heatmap** (`4`) | the same liquidity heatmap view | `HeatmapService` |
| **signals / decision** (`5`) | direction, probability (only when reliable), confidence, R:R, invalidation, mock tag | `SignalEngineService` assessment |
| **logs** (`6`) | the existing application log stream, level-styled | `WorkspaceLogHandler` (a `logging.Handler`) |
| **agents** (`7`) | only components that actually exist and run | adapter-set component status |
| **system** (`8`) | market data / event bus / trading intelligence / memory status + health metrics | `SystemMetric` rows |

## Keyboard shortcuts

| Key | Action |
|---|---|
| `1`–`8` | focus panel (market/analysis/liquidity/heatmap/signals/logs/agents/system) |
| `p` / space | pause / resume the stream |
| `r` | force a refresh |
| `q` | quit |
| `s` | change symbol (via the CLI prompt before launch; in-app symbol switching is an extension point) |
| `t` | change timeframe (as above) |

`KEYMAP` (in `app.py`) is a plain dict — the shortcuts are configurable by
construction, and every handler routes through `TerminalWorkspace.handle_key`
(one place to remap or extend).

## Navigation model

Panel focus is a state field (`state.active_panel`), not a modal switch: the
layout always renders every region; focus marks which panel the header
highlights and which a future full-screen mode would expand. Resize comes free
from Rich's layout ratios — the terminal resize reflows the same grid.
