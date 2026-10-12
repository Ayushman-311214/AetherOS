# Trading Intelligence — Documentation Map

The AetherOS Trading Intelligence system is documented in three tiers:

1. **`docs/TRADING_INTELLIGENCE_COMPLETE.md`** — the single top-level reference.
   What the system does, the governing invariants (no look-ahead, no fake
   probability, honesty flags), the pipeline stage-by-stage, the event surface,
   configuration, the TUI, the Memory seam, and known limitations. **Start here.**

2. **This directory** — per-subject deep-dives, organised by the layer they
   describe.

3. **`docs/trading_intelligence.md`** — the original design narrative (the
   "why" and the transformation chain); complementary to the reference.

## Subject map

Every subject the build brief called out is covered — the table maps each
subject to where it actually lives so coverage is navigable, not duplicated.

| Subject | Where |
|---|---|
| **Top-level architecture** | `01-architecture.md` |
| **Domain models** | `02-domain-models.md` |
| **Event contracts** | `03-event-contracts.md` |
| **Data flow (end-to-end)** | `04-data-flow.md` |
| **Market data** | `04-data-flow.md` + `COMPLETE.md §3` (sources, providers, `MarketData.window`) |
| **Market structure** | `market-intel/` (composition) + `COMPLETE.md §4.4` |
| **Technical analysis** | `market-intel/indicators.md` + `trading/indicators/` code |
| **Market regime (6 states)** | `market-intel/regime.md` + `COMPLETE.md §4.4` |
| **Liquidity (zones/sweeps/absorption)** | `liquidity/` |
| **Heatmap (one grid, six lenses)** | `heatmaps/` |
| **Signals / evidence model** | `05-evidence-model.md`, `06-signal-model.md`, `signal-engine/` |
| **Probability / risk / explanation** | `signal-engine/probability.md`, `signal-engine/risk.md`, `signal-engine/explanation.md` |
| **Backtesting / look-ahead / metrics / calibration** | `backtest/` |
| **TUI (terminal workspace)** | `workspace/` + `COMPLETE.md §8` |
| **Configuration** | `COMPLETE.md §7` (every `TRADING_*` knob, grouped) |
| **Future Memory integration** | `07-future-memory-integration.md` + `COMPLETE.md §9` |
| **Per-phase audit trail** | `00-audit.md` + each package's `00-audit.md` |

## Package deep-dives

| Directory | Layer |
|---|---|
| `liquidity/` | Order-book + tape microstructure: observations, zones, sweeps, absorption, replenishment, events, features, persistence |
| `heatmaps/` | The time×price grid and its six read-only views (liquidity, persistence, flow, sweep, absorption, pressure) + the 3-D surface |
| `market-intel/` | Non-liquidity reads: market structure, price action, volume, the 6-state regime, the feature layer |
| `signal-engine/` | Evidence aggregation, signal scoring, calibrated probability, risk, contradictions, explanation |
| `backtest/` | Look-ahead-safe pipeline, methodology, metrics, calibration, limitations |
| `workspace/` | The terminal multi-pane TUI (view layer only) |

## Reading order for a newcomer

1. `../TRADING_INTELLIGENCE_COMPLETE.md` — the whole picture.
2. `01-architecture.md` + `04-data-flow.md` — how the pieces connect.
3. The package dir for whichever layer you're changing.
4. `07-future-memory-integration.md` — before touching the event surface or
   adding a store.
