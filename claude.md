# AetherOS

## 1. Project Mission

AetherOS is an autonomous **Trading Intelligence and Decision Support System**.

The primary purpose of AetherOS is to analyze financial markets and provide evidence-based trading intelligence.

AetherOS should be capable of:

* analyzing stocks and other supported financial instruments
* analyzing market conditions
* performing technical analysis
* performing fundamental analysis
* analyzing volume and price action
* analyzing news and events
* analyzing market sentiment
* detecting market regimes
* generating trading signals
* estimating directional probabilities
* calculating risk/reward
* performing historical backtesting
* calibrating probability predictions
* explaining why a signal was generated
* monitoring positions and market conditions
* continuously evaluating whether previous predictions were correct
* learning from historical performance

The system may also use desktop automation, browser automation, computer vision, LLMs, memory, and tools to collect information and execute workflows.

However:

> **Trading intelligence is the core product.**

All supporting systems must serve this primary objective.

---

# 2. Core Philosophy

AetherOS must NOT behave like a chatbot that guesses whether a stock will rise or fall.

For example, the system must NOT produce:

> "I think RELIANCE has an 80% chance of going up."

without a quantitative basis.

Instead, probabilities must be generated from measurable evidence, models, historical data, and calibrated prediction systems.

Example:

```text
RELIANCE

Direction:
BULLISH

Estimated probability:
UP        78%
SIDEWAYS  14%
DOWN       8%

Confidence:
HIGH

Evidence:
- Price above major moving averages
- Positive momentum
- Increasing volume
- Positive sector strength
- Positive news sentiment

Risk:
MEDIUM
```

The probability must be traceable to the underlying analysis.

---

# 3. Probability Is Not a Guarantee

AetherOS must clearly distinguish between:

* prediction
* probability
* confidence
* risk
* uncertainty
* historical performance

A probability such as:

```text
P(up) = 0.78
```

means the model estimates a 78% probability under the defined prediction conditions.

It does NOT mean:

```text
The stock WILL go up.
```

Never represent probabilistic predictions as guarantees.

---

# 4. Primary Architecture

The high-level architecture should follow:

```text
                         USER
                           |
                           v
                +----------------------+
                |   TRADING CEO        |
                |   ORCHESTRATOR       |
                +----------+-----------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   Market Analysis   Fundamental       News/Sentiment
       Agent            Agent               Agent
          |                |                |
          +----------------+----------------+
                           |
                           v
                    +-------------+
                    | Quant Agent |
                    +------+------+
                           |
                  +--------+--------+
                  |                 |
                  v                 v
             Signal Model      Probability
                               Calibration
                  |                 |
                  +--------+--------+
                           |
                           v
                     Risk Engine
                           |
                           v
                   Critic / Validator
                           |
                           v
                   Trading Report
```

Supporting infrastructure:

```text
LLM Layer
Tool Registry
Memory
Event Bus
Configuration
Logging
Desktop Automation
Browser Automation
Vision
Data Providers
Storage
Backtesting
Monitoring
```

---

# 5. Agent Architecture

AetherOS should use specialized agents rather than one giant agent.

## Trading CEO / Orchestrator

Responsibilities:

* understand the user's trading-analysis request
* determine what information is required
* delegate tasks
* combine analytical results
* detect conflicting signals
* request additional analysis when necessary
* invoke the risk engine
* invoke the critic/validator
* generate the final report

The CEO should orchestrate.

It should NOT contain all analytical logic.

---

## Market Analysis Agent

Responsibilities:

* price analysis
* technical indicators
* trend detection
* support/resistance
* momentum
* volatility
* volume
* price action
* market regime

Example indicators may include:

* SMA
* EMA
* RSI
* MACD
* ATR
* Bollinger Bands
* ADX
* VWAP
* volume indicators

Indicators should be implemented in analytical modules rather than hard-coded inside the LLM prompt.

---

## Fundamental Analysis Agent

Responsibilities:

* revenue
* earnings
* margins
* debt
* cash flow
* valuation
* growth
* financial ratios
* company health

The agent should use structured financial data whenever possible.

---

## News and Sentiment Agent

Responsibilities:

* retrieve relevant news
* identify important events
* classify sentiment
* detect positive/negative catalysts
* detect earnings/events
* identify potential market-moving information

LLMs may be used for language understanding.

However, the source data must remain traceable.

---

## Quant Agent

The Quant Agent is one of the most important components.

Responsibilities:

* feature engineering
* statistical analysis
* signal generation
* probability estimation
* model evaluation
* backtesting
* probability calibration
* performance measurement

The Quant Agent should NOT blindly trust an LLM-generated probability.

---

## Risk Agent

Responsibilities:

* risk/reward analysis
* stop-loss calculation
* position sizing
* volatility risk
* drawdown risk
* exposure
* invalidation conditions

The risk engine should use deterministic calculations whenever possible.

---

## Critic / Validation Agent

The Critic exists to challenge the proposed signal.

It should ask:

* Is the evidence sufficient?
* Are indicators conflicting?
* Is the probability calibrated?
* Is the market regime compatible?
* Is the data stale?
* Is there a major upcoming event?
* Is the risk/reward acceptable?
* Is the prediction outside the model's historical reliability?
* Is there insufficient evidence?

The Critic must be able to reject a weak signal.

Example:

```text
Signal:
BULLISH

Quant probability:
82%

Critic:
REJECT

Reason:
Major earnings event within 24 hours and historical
model performance is unreliable around earnings events.
```

---

# 6. Probability and Calibration

Probability estimation is a core AetherOS capability.

The system should distinguish:

```text
Raw Model Probability
        |
        v
Calibration
        |
        v
Calibrated Probability
```

Possible calibration techniques may include:

* Platt scaling
* isotonic regression
* temperature scaling
* other statistically appropriate calibration methods

The implementation must be selected based on empirical validation.

AetherOS must track:

* predicted probability
* actual outcome
* calibration error
* accuracy
* precision
* recall
* ROC-AUC where appropriate
* Brier score
* expected calibration error
* strategy returns
* drawdown
* Sharpe ratio where appropriate

---

# 7. Backtesting Is Mandatory

No trading prediction system should be trusted without historical validation.

Whenever a predictive model is introduced:

1. Define the prediction target.
2. Define the prediction horizon.
3. Create historical features.
4. Prevent look-ahead bias.
5. Split training and validation data correctly.
6. Backtest.
7. Measure performance.
8. Calibrate probabilities.
9. Perform out-of-sample validation.
10. Monitor performance after deployment.

Avoid:

* look-ahead bias
* survivorship bias
* data leakage
* overfitting
* unrealistic transaction assumptions

Backtesting logic must be deterministic and reproducible.

---

# 8. Prediction Contract

Every prediction should have a clearly defined:

```text
Instrument
Prediction timestamp
Prediction horizon
Direction
Probability
Confidence
Features/evidence
Risk
Invalidation condition
Model version
Data version
```

Example:

```text
Instrument: RELIANCE
Timestamp: 2026-08-18 10:30
Horizon: 1 trading day

P(UP): 0.78
P(SIDEWAYS): 0.14
P(DOWN): 0.08

Model: momentum_v3
Model version: 3.2.1

Confidence: HIGH
```

This makes predictions auditable.

---

# 9. Data Is More Important Than the LLM

AetherOS must prioritize reliable market data.

The system should separate:

```text
Data Acquisition
        |
        v
Data Validation
        |
        v
Feature Engineering
        |
        v
Analysis
        |
        v
Prediction
```

Never silently use stale, incomplete, or invalid data.

Every important market-data operation should have:

* timestamp
* source
* symbol/instrument identifier
* timeframe
* data quality status

---

# 10. LLM Architecture

LLMs are reasoning and orchestration components.

They are NOT the sole source of truth for quantitative predictions.

All LLM providers must implement:

```python
LLMProvider
```

Agents should depend on the interface rather than concrete providers.

Possible providers:

* Anthropic
* OpenAI
* Ollama
* OpenRouter
* ScaleMax
* future providers

Architecture:

```text
Agent
  |
  v
LLMProvider
  |
  +---- Anthropic
  +---- OpenAI
  +---- Ollama
  +---- OpenRouter
  +---- ScaleMax
```

Never tightly couple trading agents to a single provider.

---

# 11. Tool Architecture

All tools must use the central ToolRegistry.

Architecture:

```text
Tool Interface
      |
      v
Tool Service
      |
      v
Tool Definition
      |
      v
Tool Registry
      |
      v
Agent
```

Tools must:

* have explicit schemas
* validate arguments
* return predictable results
* be independently testable
* provide useful error messages
* avoid hidden side effects

Do not bypass ToolRegistry from agents.

---

# 12. Desktop Automation

Desktop automation is a supporting capability.

Architecture:

```text
Interface
    |
    v
Backend
    |
    v
Service
    |
    v
Tool
    |
    v
Agent
```

Example:

```text
MouseInterface
      |
      v
PyAutoGUIBackend
      |
      v
MouseService
      |
      v
MouseTool
      |
      v
Agent
```

Do not directly call PyAutoGUI from high-level agents.

---

# 13. Vision

Vision should support:

* chart understanding
* UI understanding
* screen observation
* TradingView interaction
* visual verification
* UI state detection

Vision should not replace structured market data when structured data is available.

For example:

```text
Market Price
    -> use structured market API

Chart screenshot
    -> use Vision
```

Use the most reliable data source available for each task.

---

# 14. TradingView / Browser Automation

Browser and desktop automation can be used for:

* opening TradingView
* navigating charts
* adding indicators
* reading visual information
* drawing analysis objects
* monitoring UI state
* validating that an action occurred

Automation should not be considered the primary source of quantitative market data when an authoritative structured API is available.

---

# 15. Memory

AetherOS memory should preserve useful trading intelligence such as:

* previous analyses
* model performance
* historical predictions
* user-defined analysis preferences
* successful/failed workflows
* market observations
* model versions
* signal outcomes

Memory must distinguish between:

```text
FACT
PREDICTION
ASSUMPTION
OBSERVATION
MODEL OUTPUT
USER INPUT
```

Never store a model prediction as a fact.

---

# 16. Event-Driven Architecture

AetherOS should use events for important state changes.

Examples:

```text
MarketDataUpdated
SignalGenerated
PredictionCreated
PredictionResolved
RiskLimitTriggered
NewsDetected
MarketRegimeChanged
ToolExecuted
AgentStarted
AgentCompleted
AnalysisCompleted
```

The EventBus should remain decoupled from individual implementations.

---

# 17. Model Selection

Model selection should be configurable.

Example:

```python
CEO_MODEL = "..."
PLANNER_MODEL = "..."
RESEARCH_MODEL = "..."
VISION_MODEL = "..."
CRITIC_MODEL = "..."
```

Do not hard-code a single model throughout the application.

Use stronger reasoning models for:

* orchestration
* difficult reasoning
* architecture
* complex research
* validation

Use faster models for:

* simple extraction
* classification
* summarization
* routine tool execution

The exact model identifiers must come from the configured provider.

---

# 18. Configuration

All environment-specific values must come from configuration.

Never hard-code:

* API keys
* secrets
* URLs
* model credentials
* database credentials
* user-specific configuration

Use environment variables and the existing configuration system.

Never commit secrets.

---

# 19. Logging

AetherOS must provide structured logging.

Important operations should log:

* agent
* task
* tool
* model
* provider
* request ID
* execution time
* success/failure
* errors

Trading predictions should be auditable.

Do not log API keys or sensitive credentials.

---

# 20. Error Handling

Use domain-specific errors.

Examples:

```text
LLMError
ProviderError
ToolError
DesktopError
VisionError
MarketDataError
PredictionError
RiskError
BacktestError
ConfigurationError
```

Errors should preserve useful context without exposing secrets.

---

# 21. Testing Requirements

Important components must have tests.

Minimum testing areas:

```text
LLM
Tools
Agents
Market Data
Indicators
Feature Engineering
Prediction Models
Probability Calibration
Backtesting
Risk Engine
Memory
Events
Configuration
Desktop Services
Vision
```

For quantitative systems, tests should include deterministic numerical test cases.

Backtesting tests must verify that look-ahead bias is not introduced.

---

# 22. Coding Standards

Use:

* Python type hints
* async where appropriate
* dataclasses where appropriate
* small focused classes
* dependency injection
* clear interfaces
* domain-oriented modules
* deterministic calculations
* reproducible tests

Avoid:

* giant classes
* global mutable state
* circular dependencies
* unnecessary abstractions
* hidden side effects
* duplicated business logic
* provider-specific logic inside core interfaces

---

# 23. Architectural Boundaries

Maintain clear separation:

```text
Core
 |
 +-- Domain
 |
 +-- Agents
 |
 +-- Services
 |
 +-- Tools
 |
 +-- Infrastructure
 |
 +-- Providers
```

Business logic must not depend directly on infrastructure implementations.

Use dependency inversion.

---

# 24. Change Management

Before modifying a significant subsystem:

1. Inspect the existing implementation.
2. Understand dependencies.
3. Identify affected modules.
4. Explain the proposed architecture.
5. Identify risks.
6. Implement incrementally.
7. Run tests.
8. Review the diff.
9. Update documentation.
10. Update the roadmap.

Never rewrite large parts of AetherOS without explicit justification.

Do not modify unrelated files.

Preserve working behavior unless the task explicitly requires changing it.

---

# 25. Development Workflow

For every feature:

```text
Understand
    |
    v
Plan
    |
    v
Implement
    |
    v
Test
    |
    v
Review
    |
    v
Document
    |
    v
Commit
```

Claude Code should follow this workflow.

Do not immediately start coding when the requested task is ambiguous.

First inspect the repository and existing architecture.

---

# 26. Trading Analysis Workflow

A typical stock-analysis request should follow:

```text
User Request
     |
     v
Trading CEO
     |
     v
Determine required data
     |
     +--------------------+
     |                    |
     v                    v
Market Data          News/Events
     |                    |
     v                    v
Technical            Sentiment
Analysis             Analysis
     |                    |
     +---------+----------+
               |
               v
       Fundamental Analysis
               |
               v
          Quant Analysis
               |
               v
       Probability Model
               |
               v
          Calibration
               |
               v
           Risk Engine
               |
               v
          Critic Agent
               |
               v
       Final Trading Report
```

The system should be able to explain the reasoning behind the final result.

---

# 27. Final Trading Report

A final report should contain:

```text
Instrument
Current price
Market regime
Trend
Technical analysis
Fundamental analysis
News/sentiment
Key levels
Signal
Probability
Confidence
Risk/reward
Invalidation condition
Prediction horizon
Major risks
Evidence
Model/version
```

Example:

```text
RELIANCE

Signal:
BULLISH

Probability:
UP: 78%
SIDEWAYS: 14%
DOWN: 8%

Horizon:
1 trading day

Confidence:
HIGH

Key reasons:
1. Positive momentum
2. Price above major trend levels
3. Increasing volume
4. Positive sector strength
5. Positive news sentiment

Invalidation:
Close below specified support level.

Risk:
MEDIUM
```

Always clearly communicate that probabilities are estimates, not guarantees.

---

# 28. Financial Safety

AetherOS is a decision-support and trading-intelligence system.

It must:

* expose uncertainty
* explain evidence
* avoid claiming certainty
* distinguish analysis from fact
* provide risk information
* avoid hiding contradictory evidence
* maintain prediction history
* measure prediction performance

Never manipulate evidence to produce a desired trading conclusion.

If evidence is insufficient:

```text
NO TRADE / INSUFFICIENT EVIDENCE
```

is a valid result.

AetherOS should prefer **"I don't have enough evidence"** over a fabricated signal.

---

# 29. Autonomous Operation

AetherOS should eventually support:

```text
Observe
   |
Analyze
   |
Plan
   |
Predict
   |
Validate
   |
Act
   |
Observe Result
   |
Evaluate
   |
Learn
```

However, autonomous operation must remain bounded by:

* risk limits
* permissions
* validation
* audit logs
* failure recovery
* user-defined constraints

Autonomy should be introduced incrementally.

---

# 30. Current Priority

When deciding what to build next, prioritize in this order:

1. Reliable market data
2. Market analysis
3. Quantitative signals
4. Probability estimation
5. Probability calibration
6. Backtesting
7. Risk engine
8. Trading CEO / orchestration
9. News and sentiment
10. Memory
11. Vision
12. Desktop/browser automation
13. Autonomous execution

Do not prioritize visual polish or complex autonomous computer control over the correctness of the trading-analysis core.

---

# 31. Definition of Done

A feature is not complete merely because the code runs.

A feature is complete when:

* architecture is consistent
* implementation is complete
* tests exist
* tests pass
* errors are handled
* logging exists where appropriate
* configuration is correct
* documentation is updated
* no secrets are exposed
* existing functionality is preserved
* the implementation is explainable

For quantitative/trading features, also require:

* reproducible results
* historical validation
* no obvious data leakage
* appropriate performance metrics
* documented assumptions

---

# 32. Claude Code Behavior

When working on AetherOS, act as a senior software engineer and quantitative-systems engineer.

Before coding:

* inspect existing code
* understand architecture
* identify dependencies
* identify existing abstractions
* avoid duplicating functionality

During coding:

* make small changes
* preserve architecture
* use existing interfaces
* add tests
* avoid unnecessary dependencies

After coding:

* run tests
* inspect failures
* fix regressions
* review the implementation
* explain changes

Never blindly follow a request if it would violate the architecture defined in this document.

If an architectural conflict exists, explain it before implementing the change.

The primary goal is not to produce the most code.

The primary goal is to build a **reliable, explainable, testable, modular Trading Intelligence System**.
