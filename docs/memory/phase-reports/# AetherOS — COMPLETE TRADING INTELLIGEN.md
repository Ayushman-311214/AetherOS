# AetherOS — COMPLETE TRADING INTELLIGENCE SYSTEM

## Phased Production Implementation

You are working inside the existing AetherOS repository.

Your task is to **implement the complete Trading Intelligence system described by `TRADING.md`**.

`TRADING.md` is the primary specification and source of truth for the Trading module.

This is NOT a mock system.
This is NOT a demo.
This is NOT a toy implementation.
Do NOT hardcode fake market data.
Do NOT create placeholder implementations merely to make tests pass.
Do NOT skip modules because they are complex.

Build the real production-oriented architecture incrementally.

---

# 1. PRIMARY OBJECTIVE

Transform AetherOS into a real Trading Intelligence and Decision Support system capable of:

* market data collection
* historical market data
* live market data
* multi-market support
* multi-timeframe analysis
* chart processing
* technical analysis
* indicators
* market structure
* SMC analysis
* ICT analysis
* pattern recognition
* strategy evaluation
* trade signal generation
* evidence collection
* evidence provenance
* evidence fusion
* risk management
* decision making
* paper trading
* backtesting
* broker abstraction
* broker execution
* portfolio management
* position management
* order management
* trading journal
* market scanning
* alerts
* financial news
* economic calendar
* analytics
* performance evaluation
* AI-assisted reasoning
* screenshot + API hybrid chart analysis
* TradingView integration through existing AetherOS desktop/vision capabilities
* integration with AetherOS Planner/Reasoning/LLM/Memory/Automation infrastructure

The final system must follow the execution flow specified in `TRADING.md`:

Market Data
↓
Analysis
↓
SMC / ICT Detection
↓
Strategy Evaluation
↓
Risk Validation
↓
Trade Signal
↓
Paper Trade / Broker
↓
Portfolio Update
↓
Journal Entry
↓
Memory

---

# 2. CRITICAL RULES
# 2A. CRITICAL RULE — REUSE, OPTIMIZE, AND EXTEND EXISTING IMPLEMENTATION

Before creating ANY new file, class, service, interface, model, utility, provider, repository, engine, or infrastructure component, you MUST first determine whether AetherOS already contains an implementation that can be reused.

The default strategy is:

```text
EXISTING IMPLEMENTATION
        ↓
INSPECT
        ↓
REUSE
        ↓
EXTEND
        ↓
REFACTOR / OPTIMIZE
        ↓
ONLY IF NECESSARY → CREATE NEW
```

NOT:

```text
NEW REQUIREMENT
        ↓
BUILD FROM SCRATCH
```

## Mandatory Existing-Code-First Process

For every requirement:

1. Search the existing repository first.
2. Identify existing classes, functions, interfaces, services, utilities, models, tools, providers, repositories, and infrastructure related to the requirement.
3. Read and understand the existing implementation before deciding what to build.
4. Determine whether the existing implementation:

   * already satisfies the requirement
   * partially satisfies the requirement
   * can be extended
   * can be refactored
   * can be optimized
   * can be adapted through an interface
   * is genuinely unsuitable
5. Prefer modifying and improving the existing implementation over replacing it.
6. Only create a new implementation when the existing implementation genuinely cannot satisfy the requirement without causing architectural problems.
7. If a new implementation is required, explicitly document WHY the existing implementation cannot be reused.

## DO NOT REBUILD EXISTING FUNCTIONALITY

Do NOT create a new implementation merely because:

* the existing implementation is in another folder
* the existing implementation has a different name
* the existing implementation is incomplete
* the existing implementation needs refactoring
* the existing implementation is not perfectly designed
* creating a new implementation appears easier
* a tutorial/reference architecture uses a different structure
* a library provides a similar feature

Instead:

```text
Existing + Good
→ REUSE

Existing + Mostly Good
→ EXTEND

Existing + Needs Improvement
→ REFACTOR / OPTIMIZE

Existing + Architecturally Wrong
→ FIX / MIGRATE CAREFULLY

Existing + Fundamentally Unsuitable
→ REPLACE ONLY AFTER JUSTIFICATION

No Existing Implementation
→ CREATE NEW
```

## Preserve Existing Functionality

When modifying existing code:

* preserve existing public behavior unless the specification requires a change
* preserve existing integrations
* preserve existing tests
* preserve existing interfaces where practical
* avoid unnecessary renaming
* avoid unnecessary file movement
* avoid unnecessary architectural rewrites
* avoid breaking unrelated AetherOS subsystems

Any breaking change must have a clear architectural reason and regression tests.

## Optimization Is Preferred Over Reimplementation

If an existing implementation can be made production-ready, optimize it.

For example:

```text
Existing Candle model
        ↓
validate / improve
        ↓
reuse
```

NOT:

```text
Existing Candle model
        ↓
ignore
        ↓
create NewCandle
```

Likewise:

```text
Existing EventBus
        ↓
extend if necessary
        ↓
Trading uses it
```

NOT:

```text
Existing EventBus
        ↓
create TradingEventBus
```

And:

```text
Existing storage
        ↓
extend/adapt
        ↓
Trading persistence
```

NOT:

```text
Existing storage
        ↓
create completely separate Trading database layer
```

## Required Decision Before Every New Component

Before creating a new component, answer internally:

```text
1. Does something similar already exist?
2. Where is it?
3. Can it be reused?
4. Can it be extended?
5. Can it be optimized?
6. Can it be adapted through an interface?
7. Why is a new component actually necessary?
```

If an existing implementation can reasonably be reused or extended, creating a duplicate implementation is a violation of this instruction.

## Refactoring Existing Code

You ARE allowed and encouraged to improve existing code when required for Trading.

However:

```text
Understand
→ Measure / Test
→ Refactor
→ Verify
```

Do not rewrite working code simply to make it look different.

The goal is:

**integrate Trading into AetherOS, not rebuild AetherOS inside Trading.**

## Repository Search Requirement

Before implementing each phase, search the repository for relevant existing implementations.

Examples:

```text
Candle
EventBus
MarketData
Indicator
Repository
Storage
Tool
ToolRegistry
ToolExecutor
Vision
Screen
Screenshot
LLM
Planner
Risk
Portfolio
Order
Position
Signal
Strategy
Backtest
```

Use the existing implementation whenever technically appropriate.

## Change Minimization Rule

Prefer the smallest correct change that satisfies the specification.

Do NOT make large unrelated changes.

If an existing file can be modified with 20 lines instead of creating a new 200-line implementation, prefer modifying the existing file.

If an existing subsystem can be extended instead of duplicated, extend it.

## Final Verification

At the end of every phase, verify:

* What existing code was reused?
* What existing code was extended?
* What existing code was optimized?
* What new code was actually necessary?
* Were any duplicate implementations created?
* If yes, why was duplication unavoidable?

If unnecessary duplication was introduced, remove it before marking the phase complete.

The primary objective is:

> **Reuse first. Extend second. Optimize third. Replace only when necessary. Build new only when nothing suitable exists.**

# 2B. CRITICAL RULE — USE GRAPHIFY FOR ARCHITECTURE UNDERSTANDING

AetherOS uses **Graphify** as an architecture/codebase understanding tool.

Before modifying or creating significant Trading components, use the existing Graphify graph/output to understand the current AetherOS architecture and relationships.

Graphify is an **architecture understanding aid**, not the source of truth for implementation details.

The actual source of truth remains:

1. Existing source code
2. Tests
3. `TRADING.md`
4. Existing configuration/interfaces/contracts
5. Graphify architecture graph

## Mandatory Architecture Discovery Flow

Before implementing each major phase:

```text
TRADING.md
    ↓
Graphify Architecture Graph
    ↓
Existing Repository
    ↓
Existing Implementations
    ↓
Dependencies / Call Graph
    ↓
Reuse / Extend / Optimize Decision
    ↓
Implementation
```

Do NOT start implementation by creating new files.

First understand how the requested functionality fits into the existing AetherOS graph.

## Use Graphify to Identify

Use the Graphify graph to understand, where available:

* module relationships
* package relationships
* imports
* dependency direction
* class relationships
* function relationships
* service boundaries
* infrastructure dependencies
* entry points
* bootstrap flow
* ToolRegistry relationships
* ToolExecutor relationships
* ServiceContainer relationships
* EventBus relationships
* LLM relationships
* Planner/Agent relationships
* Desktop relationships
* Vision relationships
* Storage relationships
* existing Trading-related components
* potential circular dependencies
* duplicate implementations
* integration points

## Graphify Must Be Used Before Architectural Decisions

Before deciding:

```text
"create a new class"
"create a new service"
"create a new interface"
"create a new repository"
"create a new infrastructure layer"
"create a new event system"
"create a new tool system"
"create a new storage layer"
```

first inspect the Graphify architecture and existing code to determine whether an equivalent component already exists.

Do NOT infer that something is missing merely because it is not obvious from the folder structure.

## Graphify + Source Code Verification

Graphify may be stale or incomplete.

Therefore:

```text
Graphify
   ↓
Architecture hypothesis
   ↓
Source-code verification
   ↓
Actual implementation decision
```

Never blindly trust Graphify over the actual source code.

If Graphify says:

```text
A → B
```

verify the relationship in the source code before making architectural changes.

If Graphify does not show something that exists in the source code, trust the source code and note that Graphify may need regeneration.

## Existing Graphify Output

If a Graphify-generated graph/file already exists in the repository:

* inspect it
* use it
* do not regenerate it unnecessarily
* do not delete it
* do not replace it merely because another architecture visualization would look cleaner

If the graph is stale, update/regenerate it only when necessary and only after understanding the current source tree.

## Architecture Impact Analysis

Before modifying an existing component, determine its impact through Graphify and source inspection.

For example:

```text
Existing Component
       ↓
Who imports it?
       ↓
Who calls it?
       ↓
What depends on it?
       ↓
What events does it publish?
       ↓
What services consume it?
       ↓
What tests depend on it?
```

Do not modify a shared AetherOS component without understanding its downstream impact.

## Trading Integration Mapping

Before Phase 1 implementation, use Graphify + source inspection to create a conceptual map similar to:

```text
                    AetherOS
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   Bootstrap       Agent/Planner      Runtime
        │              │
        ↓              ↓
 ServiceContainer   ToolRegistry
        │              │
        ├──────────────┼───────────────┐
        ↓              ↓               ↓
    EventBus          LLM            Trading
        │                              │
        │              ┌───────────────┤
        │              ↓               ↓
        │         Market Data       Analysis
        │                              │
        │                         SMC / ICT
        │                              │
        │                         Strategies
        │                              │
        │                           Signals
        │                              │
        │                             Risk
        │                              │
        │                          Execution
        │                              │
        └──────────────────────── Portfolio
                                       │
                                     Journal
                                       │
                                     Memory
```

This is an example of the type of relationship to understand.

Do NOT blindly create this exact architecture if the existing Graphify graph/source code shows a better or already-existing structure.

## Graphify Is for Understanding, Not Reimplementation

The purpose of Graphify is:

```text
UNDERSTAND THE EXISTING SYSTEM
```

not:

```text
SEE THE SYSTEM
→ REBUILD THE SYSTEM
```

The existing AetherOS architecture should be treated as the foundation.

## Mandatory Decision Record

For each major Trading subsystem, determine:

```text
Subsystem:
Existing implementation:
Graphify location/relationship:
Current capability:
Reusable? YES/NO
Can extend? YES/NO
Can optimize? YES/NO
New implementation required? YES/NO
Reason:
Affected dependencies:
Tests affected:
```

Only after this analysis should implementation begin.

## If Graphify Reveals Existing Trading Code

If Graphify shows that a Trading-related component already exists:

**DO NOT create another implementation.**

Instead:

1. inspect it
2. test it
3. understand its dependencies
4. compare it with `TRADING.md`
5. extend it
6. refactor it
7. optimize it
8. replace only if fundamentally unsuitable

The goal is to evolve the existing system.

## Architecture Preservation Rule

Never introduce a new component that duplicates an existing component discovered through:

* Graphify
* repository search
* source inspection
* tests
* configuration
* dependency injection
* ToolRegistry
* EventBus

unless there is a documented architectural reason.

## Phase 0 Requirement

Phase 0 MUST use Graphify as part of the architecture audit.

The Phase 0 report must include:

* current architecture discovered through Graphify
* important dependency relationships
* existing Trading-related components
* reusable infrastructure
* existing implementations that should be extended
* components that require optimization
* components that genuinely need to be created
* potential duplicate implementations
* potential circular dependencies
* Trading integration points
* Graphify/source-code discrepancies, if any

Do not proceed to Phase 1 until the architecture is understood sufficiently to avoid unnecessary reimplementation.

## Core Principle

The implementation priority is:

```text
1. UNDERSTAND
2. REUSE
3. EXTEND
4. OPTIMIZE
5. REFACTOR
6. REPLACE IF NECESSARY
7. CREATE NEW ONLY WHEN REQUIRED
```

Never reverse this order merely because building from scratch is easier.



## Rule 1 — READ BEFORE MODIFYING

Before writing code:

1. Read `TRADING.md` completely.
2. Inspect the existing AetherOS repository.
3. Understand the current architecture.
4. Locate existing:

   * dependency injection
   * ServiceContainer
   * ToolRegistry
   * ToolExecutor
   * EventBus
   * configuration
   * logging
   * errors
   * LLM infrastructure
   * planner
   * agent infrastructure
   * desktop infrastructure
   * vision infrastructure
   * storage/database infrastructure
   * tests
5. Identify existing functionality that Trading should reuse.

Do NOT immediately create a new independent architecture.

---

# 3. EXISTING AETHEROS ARCHITECTURE MUST BE RESPECTED

Trading must integrate into AetherOS.

Prefer:

Interface / ABC
↓
Backend
↓
Service
↓
Tool
↓
Agent / Planner

where appropriate.

Reuse existing:

* ServiceContainer
* EventBus
* ToolRegistry
* ToolExecutor
* configuration
* logging
* error hierarchy
* LLM providers
* desktop services
* screen capture
* vision
* grounding
* planner
* runtime
* storage

Do NOT create duplicate versions of existing infrastructure.

If an existing AetherOS component is incomplete or architecturally wrong, document the issue first and fix the foundation where necessary.

---

# 4. DO NOT VIOLATE TRADING BOUNDARIES

The Trading module must NOT:

* directly control the desktop
* independently implement OCR
* independently implement screen capture when AetherOS already provides it
* own long-term memory
* manage authentication
* make unrestricted autonomous financial decisions without configured policies

Trading should consume those capabilities through proper interfaces.

---

# 5. IMPLEMENTATION PHILOSOPHY

Every phase must be:

* production-oriented
* typed
* testable
* asynchronous where appropriate
* modular
* observable
* explainable
* deterministic where deterministic behavior is expected
* failure-aware
* provider-independent
* extensible

Avoid:

* giant classes
* circular dependencies
* hidden global state
* hardcoded credentials
* hardcoded API keys
* fake market data
* fake broker responses
* silent failures
* swallowing exceptions
* unnecessary abstractions
* duplicate infrastructure
* TODO-only implementations
* empty methods
* `pass` placeholders
* magic numbers
* hardcoded monitor coordinates

---

# 6. PHASED EXECUTION

You MUST work sequentially.

Do NOT implement everything in one giant change.

Complete one phase.
Run tests.
Verify acceptance criteria.
Then mark that phase complete.

At the end of every completed phase, output exactly:

PHASE X — DONE

Also provide:

* what was implemented
* files changed
* tests executed
* test result
* remaining risks
* next phase

Do NOT say a phase is DONE if its acceptance criteria have not been met.

---

# PHASE 0 — REPOSITORY + ARCHITECTURE AUDIT

Before implementing Trading:

1. Read the complete `TRADING.md`.
2. Audit the repository.
3. Map existing AetherOS infrastructure.
4. Identify where Trading belongs.
5. Identify duplicate infrastructure that must NOT be recreated.
6. Identify integration points.
7. Identify missing foundation dependencies.
8. Produce an implementation map.

Inspect at minimum:

* `src/aetheros/`
* bootstrap
* container
* tools
* agents
* planner
* llm
* desktop
* vision
* events
* configuration
* storage
* tests

Do not implement the Trading system yet unless a foundation fix is required.

### Acceptance Criteria

You must know:

* where `trading/` belongs
* how Trading gets dependencies
* how Trading publishes/subscribes to events
* how Trading exposes tools/API
* how Trading connects to LLM
* how Trading connects to Vision
* how Trading connects to Desktop
* how Trading connects to storage
* how Trading eventually connects to Memory
* how tests will be structured
- Existing implementations have been identified for every major Trading dependency.
- Reuse/extend/optimize decisions have been documented.
- No unnecessary duplicate infrastructure will be created.
- Existing working Trading-related code has been preserved and incorporated where possible.

Then output:

PHASE 0 — DONE

---

# PHASE 1 — TRADING DOMAIN FOUNDATION

Implement the domain foundation.

Create the Trading module structure according to `TRADING.md`.

Core areas include:

```text
trading/
├── api/
├── market/
├── charts/
├── analysis/
├── indicators/
├── smc/
├── ict/
├── strategies/
├── signals/
├── risk/
├── execution/
├── brokers/
├── portfolio/
├── positions/
├── orders/
├── journal/
├── backtesting/
├── simulation/
├── scanner/
├── alerts/
├── news/
├── calendar/
├── analytics/
├── models/
├── events/
├── utils/
└── tests/
```

Implement the core domain models specified by the document:

* Candle
* TradeSignal
* Order
* Position
* Strategy
* Portfolio
* RiskProfile

Use strong domain types and enums where appropriate.

Models must have valid invariants.

For example, Candle must reject impossible OHLC relationships.

Do not put API calls, database code, strategy logic, or LLM logic inside domain models.

Implement Trading events:

* MarketOpened
* SignalGenerated
* OrderSubmitted
* OrderFilled
* PositionClosed
* RiskLimitReached

Reuse the existing AetherOS EventBus.

### Acceptance Criteria

* Domain models exist.
* Models are validated.
* Invalid domain states are rejected.
* Events are defined.
* Existing EventBus is reused.
* Unit tests cover the domain models.
* No duplicate event infrastructure exists.

Then output:

PHASE 1 — DONE

---

# PHASE 2 — MARKET DATA ENGINE

Implement `trading/market/`.

The system must support the capabilities specified by `TRADING.md`:

* live prices
* historical candles
* volume
* order book
* tick data
* multi-exchange support

Markets must be architected for:

* Forex
* Crypto
* Stocks
* Indices
* Commodities

Create provider-independent interfaces.

For example:

MarketDataProvider
MarketDataService
MarketDataRepository where appropriate.

Implement adapters rather than putting provider-specific code throughout the system.

The technology stack specified by `TRADING.md` includes CCXT and broker APIs.

Do not fake responses.

Handle:

* connection failure
* rate limits
* malformed data
* stale data
* missing candles
* duplicate candles
* timestamp issues
* provider errors
* retries where appropriate

### Acceptance Criteria

The system can:

* request historical candles
* request current market information
* normalize provider data into Trading domain models
* support multiple providers through interfaces
* detect invalid/stale data
* test provider failures
* test data normalization

Then:

PHASE 2 — DONE

---

# PHASE 3 — CHART ENGINE

Implement `trading/charts/`.

Support:

* candlestick data
* timeframe management
* multi-chart synchronization
* screenshot generation
* chart annotations

Supported timeframes:

```text
1m
5m
15m
30m
1H
4H
1D
1W
1M
```

Create proper timeframe/domain types.

The Chart Engine should not own desktop interaction.

It should consume screen/screenshot capabilities through existing AetherOS infrastructure.

### Acceptance Criteria

* Timeframes are strongly represented.
* Candle series can be transformed into chart data.
* Chart state can be represented.
* Screenshot generation integrates with existing screen infrastructure.
* Chart annotations have a structured representation.
* Tests cover timeframe handling and chart transformations.

Then:

PHASE 3 — DONE

---

# PHASE 4 — TECHNICAL ANALYSIS + INDICATORS

Implement:

```text
trading/analysis/
trading/indicators/
```

Technical analysis must include:

* trend analysis
* market structure
* volume analysis
* liquidity analysis
* volatility analysis
* momentum analysis

Indicators required by `TRADING.md`:

* EMA
* SMA
* RSI
* MACD
* VWAP
* ATR
* Bollinger Bands
* SuperTrend
* ADX
* Volume Profile

Support custom indicators.

Use the specified ecosystem where appropriate:

* pandas
* NumPy
* pandas-ta
* TA-Lib

Do not blindly add dependencies if existing AetherOS infrastructure already provides equivalent functionality.

Analysis must return structured results rather than unstructured strings.

### Acceptance Criteria

For a supplied candle series:

* indicators can be calculated
* analysis can be performed
* results contain structured values
* insufficient-data conditions are handled
* invalid data is rejected
* tests verify calculations against known cases

Then:

PHASE 4 — DONE

---

# PHASE 5 — MARKET STRUCTURE + SMC

Implement `trading/smc/`.

Support the concepts specified by `TRADING.md`:

* BOS
* CHoCH
* Order Blocks
* Liquidity Sweeps
* Mitigation Blocks
* Fair Value Gaps
* Premium/Discount Zones
* Equal Highs/Lows

Do not make the implementation merely keyword-based.

The system must derive these concepts from market data according to clearly defined rules.

Every detected structure should contain:

* type
* timestamp
* price/zone
* timeframe
* confidence where applicable
* supporting evidence
* provenance

Create tests using deterministic historical candle sequences.

### Acceptance Criteria

SMC detectors work on actual candle data.

No hardcoded detection results.

No LLM-generated fake detections.

Then:

PHASE 5 — DONE

---

# PHASE 6 — ICT ENGINE

Implement `trading/ict/`.

Support the concepts specified by the document:

* Daily Bias
* Market Structure Shift
* Kill Zones
* OTE
* Liquidity Pools
* Judas Swing
* Power of Three
* Session Models

Use actual market/session/time information.

Keep ICT detection modular.

Each detected concept must have structured evidence.

### Acceptance Criteria

* ICT components have independent detectors/services.
* Session/time logic is testable.
* Signals contain supporting evidence.
* No hardcoded market outcomes.
* Tests cover important ICT rules.

Then:

PHASE 6 — DONE

---

# PHASE 7 — STRATEGY ENGINE

Implement `trading/strategies/`.

The engine must support:

* strategy creation
* strategy loading
* strategy comparison
* strategy optimization

Initial strategy categories from `TRADING.md`:

* scalping
* swing
* trend following
* mean reversion
* ICT
* SMC
* breakout

Strategies must be modular.

A strategy must receive structured market/analysis context and produce structured strategy evaluation results.

Do not allow strategies to directly execute broker orders.

### Acceptance Criteria

* Strategy interface exists.
* Strategies are independently testable.
* Strategies can consume analysis/SMC/ICT outputs.
* Strategy results contain reasoning/evidence.
* Strategy comparison is possible.

Then:

PHASE 7 — DONE

---

# PHASE 8 — SIGNAL ENGINE

Implement `trading/signals/`.

Signals must support:

* BUY
* SELL
* EXIT
* PARTIAL EXIT
* STOP-LOSS UPDATE

Every signal must include:

* direction
* confidence
* risk
* reasoning
* supporting evidence

The signal engine must combine:

* market data
* technical analysis
* market structure
* SMC
* ICT
* strategy output

Signals must NOT directly execute trades.

Generate `SignalGenerated` events.

### Acceptance Criteria

A complete signal can be produced from actual market data and analysis.

Signals are explainable and evidence-backed.

Then:

PHASE 8 — DONE

---

# PHASE 9 — RISK MANAGEMENT

Implement `trading/risk/`.

Required capabilities:

* position sizing
* stop-loss calculation
* take-profit calculation
* risk/reward
* daily loss limits
* maximum exposure
* risk validation

Risk Manager must sit BEFORE execution.

Required flow:

Signal
↓
Risk Validation
↓
Approved / Rejected
↓
Execution

A signal must never bypass risk validation.

Risk rejection must produce useful reasons.

Generate `RiskLimitReached` where appropriate.

### Acceptance Criteria

Test:

* valid trade
* excessive position size
* excessive exposure
* daily loss breach
* invalid stop loss
* unacceptable R:R
* risk rejection

Then:

PHASE 9 — DONE

---

# PHASE 10 — ORDER + POSITION + PORTFOLIO MANAGEMENT

Implement:

```text
trading/orders/
trading/positions/
trading/portfolio/
```

Order Manager must support:

* pending
* filled
* cancelled
* rejected
* order history

Position Manager must support:

* open positions
* closed positions
* entry price
* exit price
* stop-loss
* take-profit

Portfolio Manager must track:

* balance
* equity
* margin
* PnL
* holdings
* performance

Implement correct state transitions.

Do not allow impossible state transitions.

### Acceptance Criteria

* Order lifecycle works.
* Position lifecycle works.
* Portfolio updates correctly.
* PnL calculations are tested.
* State transitions are tested.

Then:

PHASE 10 — DONE

---

# PHASE 11 — BROKER ABSTRACTION + PAPER TRADING

Implement:

```text
trading/brokers/
trading/simulation/
```

Broker abstraction must provide a common interface.

The specification mentions:

* Interactive Brokers
* Binance
* Bybit
* Alpaca
* MetaTrader as future
* Paper Trading

Do not tightly couple the system to one broker.

Implement Paper Trading using REAL market data but VIRTUAL MONEY.

Paper trading must simulate:

* order submission
* fills
* positions
* PnL
* SL/TP
* portfolio updates
* order lifecycle

Do not fake market data.

### Acceptance Criteria

A complete signal can go through:

Market Data
→ Signal
→ Risk
→ Paper Order
→ Fill
→ Position
→ Portfolio
→ Journal

without real financial execution.

Then:

PHASE 11 — DONE

---

# PHASE 12 — EXECUTION ENGINE

Implement:

```text
trading/execution/
```

Responsibilities:

* validate order
* submit order
* modify order
* cancel order
* retry failed operations
* market orders
* limit orders
* stop orders
* stop-limit orders

Execution must only receive risk-approved orders.

Required architecture:

Decision
↓
Risk
↓
Execution
↓
Broker

Execution must not contain strategy logic.

Generate:

* OrderSubmitted
* OrderFilled

and relevant failure events.

### Acceptance Criteria

* Execution is broker-independent.
* Order validation works.
* Retry behavior is controlled.
* Failures are observable.
* Paper broker can be used for integration tests.

Then:

PHASE 12 — DONE

---

# PHASE 13 — BACKTESTING ENGINE

Implement:

```text
trading/backtesting/
```

Support:

* historical testing
* walk-forward testing
* strategy comparison
* performance metrics

Metrics:

* Win Rate
* Profit Factor
* Sharpe Ratio
* Max Drawdown
* Expectancy

The technology specification mentions:

* Backtesting.py
* vectorbt

Use an appropriate engine while preserving AetherOS's domain architecture.

Backtesting must use historical market data.

Do not leak future information into past decisions.

Prevent look-ahead bias.

### Acceptance Criteria

A strategy can be run against historical data.

Results are reproducible.

Metrics are calculated.

Backtesting does not use future candles for current decisions.

Then:

PHASE 13 — DONE

---

# PHASE 14 — MARKET SCANNER

Implement `trading/scanner/`.

Scanner must support:

* multiple symbols
* multiple timeframes
* pattern detection
* SMC opportunities
* ICT setups

Scanner should reuse:

* Market Data
* Indicators
* Analysis
* SMC
* ICT
* Strategies
* Signals

Do not duplicate analysis logic.

### Acceptance Criteria

Scanner can scan multiple instruments/timeframes and return structured opportunities.

Then:

PHASE 14 — DONE

---

# PHASE 15 — NEWS + ECONOMIC CALENDAR

Implement:

```text
trading/news/
trading/calendar/
```

News:

* financial news
* earnings
* crypto news
* sentiment
* LLM summarization

Calendar:

* CPI
* FOMC
* NFP
* interest rates
* GDP
* employment data

High-impact events must be represented structurally.

News and calendar data must have timestamps and provenance.

Do not invent news.

### Acceptance Criteria

News and economic events can be represented and consumed by Trading Intelligence.

Then:

PHASE 15 — DONE

---

# PHASE 16 — PROVENANCE + EVIDENCE FUSION

This is a critical part of the system.

Implement evidence provenance.

Supported source categories include:

```text
MARKET_API
TECHNICAL_ENGINE
VISION
SCREENSHOT
USER
NEWS_API
FUNDAMENTAL_API
DERIVED
```

Every important observation should identify its source.

Example:

RSI = 64.2
source = TECHNICAL_ENGINE
timestamp = ...

Visual observation:

possible ascending triangle
source = VISION
confidence = 0.71

The system must distinguish:

* hard numerical evidence
* derived evidence
* visual observations
* uncertain observations

Implement Evidence Fusion.

Inputs:

Market API
Technical Analysis
Vision
Chart State
News
Fundamentals

↓

Evidence Fusion

↓

Unified Trading Intelligence Context

If sources disagree:

DO NOT silently overwrite.

Represent the disagreement.

Example:

API:
resistance = 114700

Vision:
visible resistance ≈ 114800

status:
minor disagreement

The LLM must receive material conflicts.

### Acceptance Criteria

The unified context preserves:

* source
* timestamp
* confidence
* evidence
* conflicts
* provenance

Then:

PHASE 16 — DONE

---

# PHASE 17 — SCREENSHOT + VISION INTEGRATION

Use existing AetherOS Vision and Desktop infrastructure.

Do NOT create duplicate OCR/screen systems.

Vision should be able to extract where technically possible:

* symbol
* timeframe
* visible price
* indicators
* indicator labels
* chart type
* candlesticks
* volume panel
* support/resistance drawings
* trendlines
* text
* annotations
* UI state

Every visual observation must contain:

* observation
* confidence
* bounding box where applicable
* source
* timestamp

Do not assume Vision can perfectly extract numerical values.

Visual uncertainty must remain visible.

### Acceptance Criteria

Vision observations can enter Trading Intelligence as evidence with provenance.

Then:

PHASE 17 — DONE

---

# PHASE 18 — TRADINGVIEW INTEGRATION

Integrate TradingView through existing AetherOS:

* Desktop
* Mouse
* Keyboard
* Screen
* Vision
* Grounding

Implement abstractions:

```text
open_chart()
select_symbol()
select_timeframe()
capture_chart()
read_chart_state()
```

Do NOT rely exclusively on brittle coordinates.

Do not hardcode one monitor resolution.

Do not hardcode coordinates unless they are configurable fallback behavior.

Prefer visual grounding.

### Acceptance Criteria

TradingView interaction is abstracted from Trading Intelligence.

Chart state can be captured and passed into the analysis pipeline.

Then:

PHASE 18 — DONE

---

# PHASE 19 — HYBRID API + SCREENSHOT ANALYSIS

This is one of the most important phases.

Create a unified:

`HybridChartContext`

It should combine:

```text
market_state
chart_state
technical_state
visual_state
news_state
fundamental_state
metadata
```

The LLM must receive BOTH:

## Numerical evidence

* OHLCV
* indicators
* levels
* volume
* volatility
* market structure

AND

## Visual evidence

* chart screenshot
* visual observations
* UI/chart context

The LLM must not treat a visual guess as equal to an API-derived numerical fact.

Use provenance and confidence.

### Acceptance Criteria

A single analysis request can combine:

API data
+
technical analysis
+
market structure
+
screenshot
+
vision observations
+
news
+
fundamentals

into one unified Trading Intelligence context.

Then:

PHASE 19 — DONE

---

# PHASE 20 — TRADING INTELLIGENCE DECISION ENGINE

Implement the decision layer.

It must consume:

* market state
* technical state
* SMC
* ICT
* strategy evaluations
* risk constraints
* news
* economic events
* visual evidence
* provenance
* evidence conflicts

It should produce a structured decision.

The decision must include:

* market view
* setup
* direction
* confidence
* supporting evidence
* contradictory evidence
* entry
* stop loss
* take profit
* risk/reward
* invalidation
* reasoning
* uncertainty
* provenance

The LLM is an intelligence/reasoning component.

It must NOT directly execute broker orders.

Execution remains deterministic and policy-controlled.

### Acceptance Criteria

The system can produce an explainable trading decision from real evidence.

Then:

PHASE 20 — DONE

---

# PHASE 21 — TRADING JOURNAL

Implement `trading/journal/`.

Automatically record:

* screenshots
* entry reason
* exit reason
* optional emotions
* risk
* P/L
* lessons learned

Every trade should be traceable from:

Market Evidence
→ Analysis
→ Signal
→ Risk Decision
→ Order
→ Position
→ Result
→ Journal

Journal records must preserve provenance and timestamps.

### Acceptance Criteria

Paper trades can automatically create complete journal entries.

Then:

PHASE 21 — DONE

---

# PHASE 22 — ANALYTICS + PERFORMANCE

Implement `trading/analytics/`.

Track:

* win rate
* average R:R
* monthly return
* strategy performance
* execution latency
* slippage

Also support performance analysis across:

* strategy
* symbol
* timeframe
* market
* broker
* period

Do not calculate metrics from incomplete data without clearly indicating limitations.

### Acceptance Criteria

Trading performance can be measured from actual journal/order/position data.

Then:

PHASE 22 — DONE

---

# PHASE 23 — ALERTS

Implement `trading/alerts/`.

Support:

* price alerts
* pattern alerts
* signal alerts
* news alerts
* portfolio alerts

Delivery architecture should support:

* Desktop
* Email
* Mobile
* Discord
* Telegram

Do not tightly couple alert generation to delivery.

Use:

Alert
→ Alert Router
→ Delivery Provider

### Acceptance Criteria

Trading events can generate alerts without coupling Trading logic to a specific notification provider.

Then:

PHASE 23 — DONE

---

# PHASE 24 — TRADING API

Implement:

```text
trading/api/
```

Expose the high-level functions specified by `TRADING.md`:

```python
analyze()
scan()
signal()
backtest()
paper_trade()
execute()
portfolio()
journal()
```

Higher-level modules should use this API rather than reaching into internal implementation details.

The API should provide stable boundaries.

### Acceptance Criteria

The complete Trading system can be accessed through a clean public API.

Then:

PHASE 24 — DONE

---

# PHASE 25 — AETHEROS TOOL + AGENT INTEGRATION

Integrate Trading with the existing AetherOS ToolRegistry and agent architecture.

Expose appropriate tools for:

* market analysis
* scanning
* signals
* backtesting
* paper trading
* portfolio
* journal
* alerts

Do not expose unsafe broker execution without appropriate policy/risk controls.

The LLM should use Trading tools through the existing AetherOS tool infrastructure.

Do not create a second tool system.

### Acceptance Criteria

AetherOS agent can request Trading Intelligence through the existing tool architecture.

Then:

PHASE 25 — DONE

---

# PHASE 26 — POLICY + EXECUTION SAFETY

Implement explicit execution policies.

Examples:

* analysis-only mode
* paper-trading mode
* live-trading mode
* maximum risk per trade
* maximum daily loss
* maximum exposure
* allowed brokers
* allowed instruments
* allowed strategies
* confirmation requirements

No live execution should happen merely because an LLM generated a BUY/SELL response.

Required flow:

LLM/Strategy Decision
↓
Policy
↓
Risk Validation
↓
Execution Validation
↓
Broker
↓
Portfolio

### Acceptance Criteria

Unsafe execution paths are blocked.

Policy violations produce explicit errors/reasons.

Then:

PHASE 26 — DONE

---

# PHASE 27 — STORAGE + PERSISTENCE

Implement proper persistence for Trading state.

Persist where required:

* market metadata
* candles where appropriate
* signals
* orders
* positions
* portfolio state
* journal
* backtest results
* analytics
* alerts
* provenance
* evidence

Use the storage technology appropriate to the existing AetherOS architecture.

`TRADING.md` specifies SQLite/PostgreSQL as storage options.

Do not create a separate unrelated database architecture.

### Acceptance Criteria

Trading state survives process restarts.

Data models can be migrated/versioned appropriately.

Then:

PHASE 27 — DONE

---

# PHASE 28 — END-TO-END TRADING PIPELINE

Now connect everything.

Required complete pipeline:

```text
Market Data
↓
Chart Engine
↓
Technical Analysis
↓
SMC
↓
ICT
↓
Strategy
↓
Signal
↓
Risk
↓
Decision
↓
Paper Trading / Broker
↓
Portfolio
↓
Position
↓
Journal
↓
Analytics
↓
Alerts
↓
Memory integration
```

Run this against REAL market data.

Paper trading must use virtual capital.

No fake candles.

No fake signal results.

No fake broker execution.

### Acceptance Criteria

A complete end-to-end paper trade can be generated and tracked.

Then:

PHASE 28 — DONE

---

# PHASE 29 — FULL TESTING

Create comprehensive tests.

Test:

## Domain

* Candle
* Signal
* Order
* Position
* Portfolio
* Risk

## Market

* providers
* normalization
* stale data
* failures

## Analysis

* indicators
* trend
* structure
* volume
* volatility

## SMC

* BOS
* CHoCH
* Order Blocks
* FVG
* liquidity sweeps

## ICT

* sessions
* liquidity
* MSS
* OTE
* other supported concepts

## Strategy

* strategy evaluation
* comparison
* invalid inputs

## Risk

* position sizing
* daily loss
* exposure
* R:R

## Execution

* order lifecycle
* retries
* rejection

## Backtesting

* no look-ahead
* metrics
* reproducibility

## Paper Trading

* fills
* positions
* PnL
* portfolio

## Evidence

* provenance
* conflicts
* confidence

## Vision

* observations
* confidence
* integration

## API

* all public Trading functions

## Integration

* complete end-to-end pipeline

Run the complete test suite.

Fix actual failures rather than weakening tests.

Then:

PHASE 29 — DONE

---

# PHASE 30 — FINAL PRODUCTION AUDIT

Perform a final audit against every requirement in `TRADING.md`.

Verify:

* every specified module exists
* every required responsibility is implemented
* architecture is integrated into AetherOS
* no duplicate infrastructure exists
* no fake market data exists
* no fake broker logic exists
* no unsafe execution bypass exists
* risk validation is mandatory
* paper trading works
* backtesting works
* broker abstraction works
* journal works
* analytics works
* scanner works
* alerts work
* news/calendar integration exists
* hybrid API + screenshot analysis works
* provenance works
* evidence fusion works
* Trading API exists
* AetherOS tool integration works
* tests pass

Search the repository for:

```text
TODO
FIXME
pass
NotImplemented
mock
fake
placeholder
hardcoded
```

Review every result.

Do not blindly remove legitimate abstractions, but eliminate incomplete production functionality.

Run:

* unit tests
* integration tests
* end-to-end tests
* type checking if configured
* linting if configured

Then produce a final implementation report.

Finally output:

PHASE 30 — DONE

TRADING INTELLIGENCE SYSTEM — COMPLETE

---

# 7. IMPORTANT IMPLEMENTATION RULE

Do NOT jump directly to later phases.

If a dependency required by a later phase is missing, implement the minimum correct foundation in the current phase.

If you discover an architectural problem in AetherOS:

1. Explain it.
2. Show why Trading depends on it.
3. Fix it without breaking existing functionality.
4. Add regression tests.
5. Continue the phase.

Do not hide architectural problems just to make the phase appear complete.

---

# 8. CODE QUALITY REQUIREMENTS

Use:

* Python type hints
* dataclasses/value objects where appropriate
* protocols/ABCs for provider boundaries
* dependency injection
* clear domain boundaries
* structured errors
* structured logging
* async I/O where appropriate
* deterministic tests
* explicit state transitions
* configuration instead of magic constants

Do not over-engineer.

Do not create abstractions that have no real purpose.

---

# 9. FINANCIAL SAFETY

This system is a trading intelligence and execution system.

Therefore:

NEVER allow:

LLM
↓
BUY/SELL
↓
Broker

The required path is:

LLM/Strategy
↓
Decision
↓
Policy
↓
Risk Manager
↓
Execution Validation
↓
Broker

Every executable trade must have:

* instrument
* side
* quantity
* entry
* stop loss where required
* take profit where required
* risk
* risk/reward
* strategy
* evidence
* reason
* policy approval
* risk approval

If these are missing, execution must be rejected.

---

# 10. NO MOCK/DEMO SHORTCUT

A mock provider may ONLY be used inside isolated automated tests where a deterministic fake provider is required to test infrastructure.

It must NEVER be used as the actual Trading Intelligence implementation.

The actual system must use real provider interfaces and real market data.

Paper trading means:

REAL MARKET DATA
+
VIRTUAL MONEY

It does NOT mean:

FAKE MARKET DATA
+
FAKE TRADING

---

# 11. DO NOT BUILD MEMORY INSIDE TRADING

Trading should produce the information that Memory can later consume.

For example:

* trade decision
* evidence
* outcome
* strategy
* confidence
* prediction
* actual result
* lessons
* performance

But long-term Memory remains an AetherOS subsystem.

Integrate with Memory only through the proper AetherOS boundary.

---

# 12. FINAL EXPECTATION

At the end of the implementation, AetherOS should have a real Trading Intelligence subsystem capable of:

```text
REAL MARKET DATA
        ↓
MARKET ANALYSIS
        ↓
TECHNICAL ANALYSIS
        ↓
SMC / ICT
        ↓
STRATEGY
        ↓
EVIDENCE FUSION
        ↓
TRADING INTELLIGENCE
        ↓
SIGNAL
        ↓
RISK VALIDATION
        ↓
DECISION
        ↓
PAPER TRADING
        ↓
PORTFOLIO
        ↓
JOURNAL
        ↓
ANALYTICS
```

and, only when explicitly configured and permitted:

```text
RISK VALIDATION
        ↓
EXECUTION
        ↓
BROKER
```

The system must also support:

```text
API DATA
+
CHART SCREENSHOT
+
VISION
+
TECHNICAL ANALYSIS
+
NEWS
+
FUNDAMENTALS
+
MARKET STRUCTURE
        ↓
EVIDENCE FUSION
        ↓
UNIFIED TRADING INTELLIGENCE
```

This must integrate into the existing AetherOS architecture rather than becoming a separate application.

Start with PHASE 0.

Do not skip phases.

Do not claim completion without verification.

After each completed phase, explicitly output:

PHASE X — DONE
