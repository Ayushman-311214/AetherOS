# AetherOS Trading Intelligence System

## 1. Purpose of Trading Intelligence

AetherOS Trading Intelligence is an evidence-based trading-intelligence and decision-support system.

It is not primarily a conversational interface. The conversation is only the entry point. The actual product is a chain of transformations:

```text
Natural-language question
    ↓
Structured analysis task
    ↓
Validated market and contextual data
    ↓
Technical, fundamental, event and regime intelligence
    ↓
Evidence objects
    ↓
Scenario analysis
    ↓
Risk analysis
    ↓
Probability and confidence
    ↓
Validation and criticism
    ↓
Explainable decision support
    ↓
Prediction tracking and evaluation
```

The system should answer questions such as:

- What is the current market state?
- What are the plausible paths from here?
- What evidence supports each path?
- What would invalidate each path?
- Is there a tradable setup?
- Is the reward justified by the risk?
- How reliable is the probability estimate?
- What historical evidence supports the setup?
- What information is missing?
- How has AetherOS performed on similar predictions before?

The proper output is often:

```text
NO TRADE — INSUFFICIENT EVIDENCE
```

That is a successful result when the system cannot establish a sufficiently reliable case.

---

## 2. Evidence-Based Trading Intelligence Concept

AetherOS Trading Intelligence is not a simple chatbot that says:

> Buy this stock.
>
> This stock will go up.

It must be capable of systematically gathering, analyzing, combining, validating and explaining information for requests such as:

- “Analyze RELIANCE for the next 1–5 days.”
- “Is there a high-probability trading setup on BTCUSDT?”

Every important conclusion should be grounded in measurable evidence, historical validation, explicit assumptions, model limitations and risk analysis.

The system must distinguish between:

- Facts
- Observations
- Calculations
- Inferences
- Predictions
- Probabilities
- Confidence
- Risk
- Uncertainty

A probability is an estimate under stated conditions. It is never a guarantee.

---

## 3. Repository Trading Intelligence Foundation

The existing Trading Intelligence subsystem contains a substantial deterministic foundation under:

- `src/aetheros/trading/domain`
- `src/aetheros/trading/services`
- `src/aetheros/trading/providers`
- `src/aetheros/trading/quant`
- `src/aetheros/trading/indicators`
- `src/aetheros/trading/tools.py`
- Trading-related CLI commands and tests

### Existing data and domain models

The subsystem already models:

- Instruments and timeframes
- OHLCV candles and quotes
- Data quality
- Source provenance
- Technical snapshots
- Market structure
- Evidence objects
- Fundamentals
- News and sentiment
- Event calendars
- Market regimes
- Relative strength
- Macro context
- Multi-timeframe alignment
- Risk assessments
- Backtest results
- Probability estimates
- Prediction records
- Prediction outcomes
- Prediction performance
- Final trading reports
- Critic reports

### Existing services

The existing services include:

- `MarketDataService`
- `TechnicalAnalysisService`
- `MarketStructureService`
- `EvidenceService`
- `AnalysisService`
- `RiskService`
- `BacktestService`
- `ProbabilityService`
- `NewsSentimentService`
- `EventCalendarService`
- `FundamentalAnalysisService`
- `RegimeService`
- `RelativeStrengthService`
- `MacroContextService`
- `MultiTimeframeService`
- `AnomalyService`
- `HistoricalAnalogueService`
- `CriticService`
- `OrchestrationService`
- `PredictionEvaluator`
- `PredictionPerformanceService`
- `PredictionTrackRecordService`

### Existing end-to-end flow

The main deterministic pipeline is approximately:

```text
Market data
    ↓
Technical analysis
    ↓
Market structure
    ↓
Evidence construction
    ↓
Directional analysis
    ↓
Risk geometry
    ↓
Probability estimation
    ↓
Optional backtest
    ↓
News, events, fundamentals, regime, macro and multi-timeframe context
    ↓
Critic / validator
    ↓
Trading report
    ↓
Prediction record
```

The numerical core is explicitly designed to be LLM-free. An LLM may sit above it to interpret requests, orchestrate tools and explain results, but it should not replace the quantitative calculations.

### Current limitations

The existing foundation is strong, but the complete conceptual system is broader than the current implementation. The following areas are either incomplete or not directly present in the Trading Intelligence package:

- A dedicated natural-language trading-intent contract
- Explicit bullish, bearish and neutral scenario objects
- Full conditional setup modeling with trigger-based entry zones
- Order-flow and market-microstructure data
- Market breadth data
- Portfolio-level exposure and correlation-aware risk
- Social sentiment and positioning data
- A dedicated chart-screenshot/visual-evidence pipeline
- Realistic execution modeling with transaction costs, slippage and stop/target fill rules
- Durable prediction and outcome storage
- Continuous monitoring
- A continuous learning engine
- A formal strategy registry and model promotion process

The current prediction store is in-memory and the current track-record evaluation is on demand. It measures outcomes but does not yet constitute a persistent learning loop.

---

## 4. User Intent

A natural-language request must first be converted into a structured trading-analysis task.

For example:

> Analyze RELIANCE for the next 1–5 days.

should become an analysis contract containing:

- Instrument: RELIANCE
- Asset class: equity
- Exchange: resolved explicitly
- Analysis timestamp
- Prediction horizon: 1–5 trading days
- Base timeframe: for example, daily or 4-hour
- Entry timeframe: perhaps 1-hour or 4-hour
- Trading style: short-term swing unless clarified
- Direction: unbiased unless the user asks long or short
- Risk tolerance: unknown unless supplied
- Account equity: optional
- Maximum risk per trade: optional
- Requested analysis:
  - Technical
  - Fundamentals
  - News
  - Events
  - Market regime
  - Risk/reward
  - Probability
  - Setup generation
- Required output:
  - Broad analysis
  - Possible trade
  - Entry and exit plan
  - Scenarios
  - Or simply information

The intent layer must distinguish between:

### Forecast intent

“What is likely to happen?”

### Setup intent

“Is there a trade I can take?”

### Risk intent

“How large should the position be?”

### Investment intent

“Is this company attractive over a longer period?”

### Monitoring intent

“Has the previous prediction worked?”

These are different tasks.

A company can have strong long-term fundamentals but no valid five-day trading setup. Conversely, a short-term breakout can exist even when valuation is expensive.

Critical ambiguity should not be hidden. If the user does not provide a timeframe, risk budget or trading style, the system should either ask for clarification or clearly state the assumptions it used.

---

## 5. Market Data Intelligence

Market Data Intelligence is the foundation of every later conclusion.

### Core data

The system should consume:

- OHLCV candles
- Real-time quotes
- Historical prices
- Volume
- Bid and ask when available
- Market session information
- Trading calendar
- Corporate-action adjustments
- Instrument metadata
- Exchange and timezone information

The existing market-data service performs important validation:

- Candle ordering
- Monotonic timestamps
- OHLC consistency
- Non-negative volume
- Missing values
- Partial results
- Staleness
- Provider errors
- Cache handling

A stale candle must not silently appear current.

### Additional market context

A more complete system should also include:

- Order-flow imbalance
- Trade aggressor information
- Bid/ask depth
- Open interest
- Funding rates for crypto
- Liquidations
- Market breadth
- Advance/decline statistics
- Sector indices
- Broad-market indices
- Volatility indices
- Currency and rates context
- Correlated instruments
- Commodity inputs where relevant
- Benchmark-relative performance

The existing repository has partial cross-market functionality through:

- Benchmark relative strength
- Macro posture
- Benchmark comparison
- Market regime analysis
- Multi-timeframe analysis

However, it does not yet provide a complete order-flow, breadth or portfolio-correlation layer.

### Why raw price is insufficient

A price series alone cannot answer:

- Whether a move has meaningful participation
- Whether a breakout is supported by volume
- Whether the entire market is moving in the same direction
- Whether the instrument is outperforming its sector
- Whether volatility makes the setup too dangerous
- Whether the move is caused by a scheduled event
- Whether the market is trending or merely oscillating
- Whether the instrument is highly correlated with existing positions
- Whether the displayed price is stale or incomplete

Market data should therefore pass through:

```text
Acquisition
    ↓
Normalization
    ↓
Validation
    ↓
Freshness assessment
    ↓
Quality classification
    ↓
Feature construction
```

Every data object should carry:

- Source
- Retrieval time
- Instrument
- Timeframe
- Data version
- Quality state
- Known limitations

---

## 6. Technical Intelligence

Technical Intelligence should analyze price behavior in context.

It should cover:

- Trend
- Market structure
- Support and resistance
- Moving averages
- Momentum
- Volatility
- Volume
- Price action
- Breakouts
- Breakdowns
- Candlestick structures
- Chart patterns
- Multi-timeframe alignment
- Relative strength

### Trend

Trend analysis may combine:

- Higher highs and higher lows
- Lower highs and lower lows
- Moving-average relationships
- Slope
- Directional movement
- Breakout persistence
- Trend strength

### Indicators

The existing technical layer computes:

- SMA
- EMA
- RSI
- MACD
- ATR
- Bollinger Bands
- VWAP
- ADX
- Volume moving average
- Returns
- Volatility

These are useful measurements, but an indicator value is not automatically a signal.

For example:

- RSI above 70 does not always mean “short”
- MACD above zero does not always mean “buy”
- Price above VWAP does not always mean “long”
- A breakout does not always mean continuation
- High volume does not automatically mean bullishness

The meaning depends on:

- Trend direction
- Market regime
- Location relative to support and resistance
- Whether the instrument is extended
- Whether volume confirms the move
- Whether the move is occurring into an event
- Whether higher timeframes agree
- Whether the expected reward justifies the stop

### Evidence families

Indicators should be grouped into evidence families.

#### Trend family

- Moving-average relationships
- Structure
- ADX
- Slope

#### Momentum family

- RSI
- MACD
- Rate of change
- Momentum acceleration

#### Volatility family

- ATR
- Bollinger width
- Realized volatility
- Volatility expansion or contraction

#### Participation family

- Volume
- Relative volume
- Volume trend
- Order-flow confirmation

#### Location family

- Support
- Resistance
- VWAP
- Prior highs and lows
- Gaps
- Anchored reference levels

The system should avoid counting five highly correlated momentum indicators as five independent confirmations.

A better approach is:

```text
Raw measurements
    ↓
Evidence family interpretation
    ↓
Family-level directional read
    ↓
Cross-family confirmation
    ↓
Contradiction analysis
```

The existing repository has an `Evidence` object with:

- Evidence type
- Assertion type
- Direction
- Detail
- Weight
- Confidence
- Provenance
- Data quality

This is a strong foundation for contextual technical intelligence.

---

## 7. Fundamental Intelligence

Fundamental Intelligence analyzes the economic and financial condition of the instrument or issuer.

It may include:

- Revenue
- Revenue growth
- Earnings
- Earnings growth
- Profitability
- Margins
- Return on equity
- Debt
- Debt-to-equity
- Liquidity
- Free cash flow
- Capital expenditure
- Valuation
- Guidance
- Management commentary
- Competitive position
- Sector performance
- Company events
- Macro sensitivity

The existing repository includes a fundamental provider abstraction and a deterministic fundamental scoring service. It produces a derived health and valuation read with provenance and reliability limitations.

### Point-in-time correctness

Fundamental analysis must use information that was actually available at the prediction timestamp.

It must not use:

- Restated financial data that was published later
- Future earnings that were not yet known
- Revised guidance from a later date
- Survivorship-biased company data

This is especially important during backtesting.

### Timeframe dependence

Fundamental relevance changes with the prediction horizon.

#### Intraday

Fundamentals usually matter indirectly through:

- Scheduled announcements
- Earnings releases
- Macro data
- Guidance changes
- Large analyst revisions
- Unexpected company events

#### One to five trading days

Fundamentals matter mainly through:

- Earnings expectations
- Guidance
- Valuation sensitivity
- Recent company announcements
- Sector catalysts

Technical structure and news freshness usually dominate.

#### Weeks to months

Fundamentals become more influential:

- Earnings trends
- Revenue growth
- Margin changes
- Debt and cash flow
- Valuation
- Sector cycle
- Management guidance

A fundamental “bullish” reading should therefore not automatically override a short-term bearish technical setup.

---

## 8. News and Event Intelligence

News Intelligence should not be a simple headline summarizer. It should build a structured, time-aware event record.

### Source collection

The system should collect from:

- Regulatory filings
- Company announcements
- Exchange notices
- Earnings releases
- Central banks
- Government sources
- Economic calendars
- Established financial news providers
- Analyst research
- Sector publications
- Carefully filtered social sources

The existing repository includes news and calendar provider interfaces, Yahoo-backed adapters and explicit mock providers.

### Every news item should contain

- Source
- Source tier
- Headline
- Summary
- Published timestamp
- Updated timestamp if available
- Retrieval timestamp
- Instrument links
- Sector links
- Event type
- Event importance
- Freshness
- Reliability
- Duplicate or related-story identifiers

### Duplicate detection

Multiple outlets may report the same event.

The system should distinguish between:

- A unique event
- Repeated reporting of the same event
- Follow-up analysis
- New information
- Contradictory information

Ten copies of one press release should not be counted as ten independent confirmations.

### Relevance and impact

Each item should be assessed for:

- Instrument relevance
- Sector relevance
- Market relevance
- Expected price sensitivity
- Time horizon
- Surprise relative to expectations
- Whether the information is already priced in
- Whether it changes the underlying thesis

### Fact, interpretation and trading implication

The system should separate:

#### Fact

“Company announced a new contract.”

#### Interpretation

“The contract may improve future revenue visibility.”

#### Trading implication

“This could support a short-term bullish catalyst if the announcement is material and not already priced in.”

The final interpretation should include uncertainty.

### Conflicting news

If one reliable source says an event is positive and another says the event has negative implications, the system should not force a single sentiment label.

It should report:

- What is known
- What is disputed
- Which source is stronger
- How fresh each source is
- Which scenarios each interpretation supports

A reliable high-impact event can be a risk veto even when its direction is unknown.

The existing critic treats reliable high-impact scheduled events as a possible hard failure. This is appropriate because event risk can invalidate historical price-based assumptions.

---

## 9. Sentiment Intelligence

Sentiment is evidence, not truth.

It can be derived from:

- News headlines
- Full news articles
- Analyst commentary
- Earnings-call language
- Social sources
- Market positioning
- Options positioning
- Funding rates
- Volume and price response

The system should ask not merely:

> Is the text positive or negative?

It should ask:

- Is the source reliable?
- Is the source independent?
- Is the information new?
- Is the information relevant to this instrument?
- Is the market reacting in the same direction?
- Is the sentiment already reflected in price?
- Is sentiment extreme or crowded?
- Is the sentiment direction consistent across sources?

The existing repository implements deterministic finance-lexicon sentiment over sourced headlines. That is useful as a baseline, but it is not a complete sentiment system because it does not fully incorporate:

- Social data
- Analyst revisions
- Positioning
- Narrative saturation
- Crowding
- Price-response confirmation

A sentiment result should carry:

- Positive, negative and neutral counts
- Aggregate score
- Source quality
- Number of independent sources
- Freshness
- Contradictory items
- Reliability status

---

## 10. Market Regime Detection

A market regime describes the character of price behavior, not the next price direction.

Possible regimes include:

- Trending upward
- Trending downward
- Ranging
- High volatility
- Low volatility
- Transitioning
- Risk-on
- Risk-off
- Unknown

The same setup can behave differently depending on the regime.

For example:

- A breakout strategy may work well in a strong trend
- The same breakout may fail repeatedly in a range
- Mean reversion may work in a range
- Mean reversion may be dangerous during a trend
- Tight stops may work in low volatility
- Tight stops may be repeatedly hit in high volatility

The existing repository has:

- `RegimeService`
- ADX-based trend strength
- ATR-relative volatility
- Trending, ranging and volatile classifications
- Benchmark-to-macro posture mapping
- Risk-on, risk-off and neutral context

The regime layer should be used as a conditioning variable:

```text
Setup performance = f(setup, timeframe, regime, volatility, event state)
```

A regime detector should not say:

> The market is trending up, therefore price will rise.

It should say:

> The current environment is more compatible with trend-following long setups than with counter-trend mean reversion.

Regime transitions deserve special treatment because transitional environments often produce unstable signals.

---

## 11. Chart and Vision Intelligence

Chart screenshots are useful, but they should not replace structured market data.

### A. Structured market/API data

This is the numerical source of truth for:

- Prices
- OHLCV
- Time
- Indicators
- Returns
- Volatility
- Quantitative features
- Historical labels
- Backtests

It is precise, machine-readable and suitable for mathematical analysis.

### B. Chart screenshots

A screenshot can provide:

- The visual chart context
- User-drawn support and resistance
- Trend lines
- Visible chart patterns
- Indicator panel configuration
- Selected symbol and timeframe
- Annotations
- Gaps or visual structures not represented in the API response
- Confirmation of what a human trader is actually looking at

A screenshot is not inherently precise. It may be cropped, stale, distorted or missing historical context.

### C. Vision, OCR and grounding

Vision systems can:

- Identify the chart region
- Read symbol and timeframe labels
- Detect visible indicators
- Read price labels
- Locate trend lines
- Detect annotations
- Map pixels to approximate price/time coordinates
- Identify chart patterns
- Report visual uncertainty

A visual conclusion should be represented as a separate evidence item containing:

- Evidence type: visual or chart
- Screenshot timestamp
- Source
- Detected object
- Pixel region
- Estimated price/time mapping
- Vision confidence
- Whether it agrees with structured data

The correct combination is:

```text
Structured API data
    = quantitative canonical source

Chart screenshot
    = visual context and annotation source

Vision/OCR/grounding
    = interpretation of the screenshot
```

If the screenshot contradicts API data, the system should report a conflict rather than silently choose one.

The Trading Intelligence package is deliberately independent of Vision. It reserves visual evidence categories in its domain model, but does not yet contain a direct chart-screenshot intelligence service.

---

## 12. Evidence Model

Evidence is the atomic unit of Trading Intelligence.

An evidence item is a traceable claim such as:

- “Price is above the 50-day moving average.”
- “Volume is 1.8 times its recent average.”
- “A high-impact event falls within the prediction horizon.”
- “The broad market is risk-off.”
- “The latest news sentiment is negative.”

Each evidence item should contain:

- Instrument
- Evidence type
- Assertion type
- Directional lean
- Detail
- Weight
- Confidence
- Source
- Source tier
- Timestamp
- Data quality
- Underlying values
- Calculation or interpretation details
- Reliability status
- Stable identifier

Evidence must distinguish between:

- Observed
- Calculated
- Detected
- Inferred
- Uncertain

The existing repository already has an `Evidence` object with:

- Evidence type
- Assertion type
- Direction
- Detail
- Weight
- Confidence
- Provenance
- Data quality

Evidence should be content-addressed or otherwise stable enough to be referenced by a prediction and later audited.

---

## 13. Evidence Fusion

Evidence combination should have four stages.

### Stage 1: Validate

Discard or downgrade:

- Invalid data
- Stale data
- Mock data
- Unverifiable claims
- Duplicate news
- Incomplete observations

### Stage 2: Group

Group evidence into families:

- Technical
- Structure
- Momentum
- Volume
- Volatility
- Fundamentals
- News
- Sentiment
- Regime
- Macro
- Relative strength
- Historical analogues
- Visual

### Stage 3: Weight

Weights should reflect:

- Reliability
- Freshness
- Relevance to the horizon
- Source quality
- Historical predictive value
- Regime compatibility
- Independence
- Evidence family diversity

### Stage 4: Adjudicate

Determine:

- Supporting evidence
- Contradicting evidence
- Hard constraints
- Soft warnings
- Missing evidence
- Scenario implications

A final direction should never be the result of an unexamined sum.

The system must avoid:

- Double-counting correlated indicators
- Treating all evidence as equally reliable
- Treating stale evidence as current
- Treating a scheduled event as directional proof
- Treating sentiment as fact
- Treating a pattern as a guarantee
- Letting a weak module override a strong hard constraint

A candidate setup should be treated as a hypothesis supported by an evidence ledger, not as a guaranteed outcome.

---

## 14. Signal and Setup Generation

Signal generation should create candidate hypotheses from evidence.

A candidate setup might be supported by:

```text
Market structure
    +
Trend
    +
Momentum
    +
Volume
    +
Support/resistance
    +
News
    +
Market regime
    +
Relative strength
    +
Fundamentals
    +
Historical analogue behavior
```

This does not mean adding all numbers together.

A candidate setup should contain:

- Thesis
- Direction
- Timeframe
- Trigger
- Entry zone
- Stop or invalidation
- Target
- Expected reward
- Expected risk
- Supporting evidence
- Contradicting evidence
- Relevant regime
- Relevant catalysts
- Historical validation
- Probability, if validated
- Confidence
- Conditions under which the setup should be discarded

The existing repository creates a technical evidence set and performs a transparent weighted fusion for the directional lean. The broader contextual modules are generally advisory and are passed to the critic rather than blindly merged into the primary technical score.

That is safer than allowing every module to vote equally.

---

## 15. Scenario Analysis

The system should not produce only one directional prediction. It should construct at least three scenarios.

### Bullish scenario

Contains:

- Supporting evidence
- Required trigger
- Expected behavior
- Entry zone
- Stop or invalidation
- Target zones
- Catalyst
- Contradicting evidence
- Risk/reward
- Probability
- Confidence

Example concept:

```text
Bullish case:
Price holds above support and breaks resistance with expanding volume.

Trigger:
A confirmed close above resistance.

Invalidation:
Price closes back below the breakout level.

Expected behavior:
Continuation toward the next resistance zone.

Risks:
Broad market is risk-off and an earnings event is near.
```

### Bearish scenario

Contains:

- Failed breakout or support break
- Confirmation condition
- Short entry zone
- Stop above invalidation
- Downside target
- Negative catalysts
- Counter-evidence
- Probability
- Confidence

### Neutral/range scenario

Contains:

- Boundaries of the range
- Conditions that keep price inside the range
- Mean-reversion opportunities if appropriate
- Breakout conditions that terminate the neutral case
- Probability
- Confidence

The probabilities should either:

- Sum to approximately 100% across mutually exclusive scenarios, or
- Be clearly labeled as separate conditional probabilities

A scenario can be more useful than a simple directional label because it tells the user what must happen next.

---

## 16. Probability and Confidence

A statement such as:

```text
Bullish scenario: 78%
Bearish scenario: 22%
```

must represent an empirically defined event.

For example:

> Under these data conditions, with this feature state, timeframe and horizon, the historical probability of the price closing higher over the next five bars was approximately 78%.

It must not mean:

> The system feels 78% confident that the stock will rise.

### Probability estimation

A proper probability pipeline includes:

1. Define the target
2. Define the horizon
3. Build causal features
4. Construct historical labels
5. Split chronologically
6. Train on earlier data
7. Calibrate on a separate slice
8. Evaluate on untouched holdout data
9. Test against a naive baseline
10. Report sample size and limitations
11. Monitor future outcomes

The target must be explicit. Examples include:

- Probability that the close is higher after five bars
- Probability that a target is reached before a stop
- Probability of a breakout holding for two sessions
- Probability of a three-way outcome: up, sideways or down

These are different probabilities:

```text
P(close higher)
≠
P(target reached before stop)
≠
P(trade is profitable after costs)
```

### Existing probability foundation

The repository already has a meaningful probability layer containing:

- Causal feature construction
- Time-ordered train/calibration/holdout splitting
- Logistic model
- Platt calibration
- Brier score
- Log loss
- Accuracy
- Expected Calibration Error
- Naive base-rate comparison
- Reliability gating
- Explicit suppression of unreliable probabilities

The report surfaces a probability only when the estimate passes its reliability gate.

### Confidence versus probability

#### Probability

A statistical estimate of how often an explicitly defined outcome occurs under similar conditions.

#### Confidence

A qualitative assessment of how much trust should be placed in the analysis or estimate.

Confidence depends on:

- Data quality
- Sample size
- Freshness
- Model stability
- Regime similarity
- Agreement between evidence families
- Calibration quality
- Missing information
- Conflicting evidence

A system can produce:

```text
P(up) = 58%
Confidence = high
```

if the estimate is well calibrated and based on excellent data, even though the edge is small.

It can also produce:

```text
P(up) = 78%
Confidence = low
```

if that estimate comes from a tiny sample or a regime that has not been validated.

A probability is never a guarantee.

---

## 17. Risk Intelligence

Trading Intelligence must ask two different questions:

1. Can price move in the anticipated direction?
2. Is the potential reward justified by the risk?

Risk Intelligence covers:

- Stop placement
- ATR and volatility
- Maximum loss
- Position sizing
- Risk/reward
- Drawdown
- Gap risk
- Liquidity
- Slippage
- Event risk
- Correlation
- Portfolio exposure
- Concentration
- Leverage
- Aggregate risk limits

Conceptually:

```text
Allowed loss
    ÷
Loss per unit at invalidation
    =
Position size
```

The stop must reflect:

- Market noise
- Structure
- Volatility
- Liquidity
- Gap behavior
- The actual thesis invalidation

A mathematically attractive target is not useful if it is unreachable under the expected volatility or blocked by nearby resistance.

The existing risk engine calculates:

- Entry
- ATR-based or structural stop
- Target
- Risk per unit
- Reward per unit
- Reward/risk ratio
- Position size when account equity is supplied
- Invalidation language
- Overall risk band

That is a strong risk-geometry foundation. A fuller system should add conditional entry zones and realistic execution assumptions.

The broader risk engine should know:

- Existing positions
- Correlated positions
- Sector exposure
- Market exposure
- Total portfolio drawdown
- Event concentration
- Maximum daily or weekly loss

The current repository has instrument-level risk, but not a complete portfolio-level risk engine.

---

## 18. Backtesting

Every recurring setup concept should eventually be testable against historical data.

A backtest must define:

- Dataset
- Instrument universe
- Point-in-time information
- Strategy rules
- Feature definitions
- Entry rule
- Trigger
- Stop
- Target
- Exit rule
- Holding horizon
- Position sizing
- Transaction costs
- Slippage
- Spread
- Gaps
- Partial fills
- Trading sessions
- Corporate actions
- Delistings
- Survivorship treatment

The correct walk-forward process is:

```text
At time t:
    use only information available at t
    generate the signal
    simulate the entry
    advance through future bars
    apply stop, target or time exit
    record the result
```

The signal must never see future candles.

The existing backtest service is look-ahead-safe because it passes only candles available up to each prediction bar. It reports:

- Evaluated observations
- Directional calls
- Hits
- Accuracy
- Coverage
- Up and down accuracy
- Base rate
- Average return
- Cumulative return
- Maximum drawdown
- Sharpe-like per-trade statistic

It also rejects mock results as reliable evidence and flags thin samples.

However, the current backtest is primarily a close-to-close directional backtest. A production setup backtest should also model:

- Stops
- Targets
- Transaction costs
- Slippage
- Order types
- Intrabar ordering
- Gaps
- Liquidity
- Portfolio interactions
- Sortino or other downside-sensitive metrics where appropriate

Important metrics include:

- Win rate
- Profit factor
- Expectancy
- Average win
- Average loss
- Maximum drawdown
- Recovery factor
- Sharpe ratio
- Sortino ratio
- Tail loss
- Exposure
- Coverage
- Stability across time
- Stability across regimes
- Sample size

---

## 19. Calibration

Calibration determines whether a stated probability corresponds to observed frequency.

If a system repeatedly predicts 70%, then outcomes in that probability range should occur approximately 70% of the time over a sufficiently large and comparable sample.

The calibration process should include:

- Separate model training data
- Separate calibration data
- Untouched holdout data
- Time-ordered splits
- Reliability diagrams or reliability bins
- Brier score
- Log loss
- Expected Calibration Error
- Sample-size reporting
- Regime-specific evaluation
- Baseline comparison

Calibration should be monitored after deployment because probability quality can drift when:

- Market regimes change
- Volatility changes
- Instruments change
- Data sources change
- Feature distributions change
- Market participants adapt

An unreliable probability should be withheld from the final user-facing signal, even if the raw model produces a precise-looking number.

---

## 20. Prediction Tracking

Every produced prediction should be recorded as a prediction, not as a fact.

A prediction record should contain:

- Instrument
- Timestamp
- Timeframe
- Horizon
- Direction
- Scenario probabilities
- Confidence
- Entry assumptions
- Stop
- Target
- Risk/reward
- Invalidation
- Evidence identifiers
- Data source and version
- Model version
- Pipeline version
- Regime
- Limitations
- Whether the prediction was actionable

Example:

```text
Prediction:
BTCUSDT bullish

Probability:
72%

Horizon:
24 hours

Model:
momentum_regime_model_v3

Data:
Exchange candles, retrieved at stated timestamp

Invalidation:
Close below defined support
```

The prediction must later be compared with what actually happened.

---

## 21. Prediction Evaluation

Later, the evaluator should record:

```text
Actual result:
BTCUSDT moved down over the 24-hour horizon

Outcome:
Resolved

Correct:
No

Realized return:
Negative

Brier contribution:
Recorded if a reliable probability existed
```

The evaluator should distinguish between:

- Pending predictions
- Resolved predictions
- Unresolvable predictions
- Directional predictions
- Non-directional predictions
- Real-data outcomes
- Mock-data outcomes
- Reliable and unreliable samples

A prediction whose horizon has not elapsed must not be marked correct or incorrect.

A prediction with an unavailable entry bar or unusable later data must be unresolvable rather than fabricated into a hit or miss.

The existing repository already contains:

- `PredictionRecord`
- `PredictionStore`
- `PredictionEvaluator`
- `PredictionOutcome`
- `PredictionPerformanceService`
- `PredictionTrackRecordService`

Prediction tracking enables:

- Performance measurement
- Calibration
- Error analysis
- Strategy evaluation
- Confidence evaluation
- Model improvement

At present, the default store is in-memory and track-record evaluation is on demand. A complete system would persist both predictions and outcomes durably.

---

## 22. Learning System

Learning has two distinct meanings.

### Knowledge acquisition

The system can ingest:

- Trading books
- Research papers
- Strategy documents
- Articles
- YouTube transcripts
- Earnings-call transcripts
- Exchange documentation
- Academic studies
- User-provided rules

This produces knowledge such as:

- Definitions
- Hypotheses
- Strategy descriptions
- Feature ideas
- Risk concepts
- Market mechanics
- Known failure modes

Every item requires:

- Source
- Timestamp
- Author
- Context
- Reliability
- Whether it is a fact, claim, hypothesis or opinion

### Empirical strategy learning

A model or strategy has learned something operationally only when it has been:

1. Formalized
2. Converted into explicit features and rules
3. Tested on historical data
4. Evaluated out of sample
5. Calibrated
6. Tested across regimes
7. Compared against baselines
8. Monitored in shadow mode
9. Validated after deployment

Storing a document does not mean the model has learned the strategy inside it.

The proper learning loop is:

```text
Research or outcome
    ↓
Hypothesis
    ↓
Formal strategy definition
    ↓
Historical testing
    ↓
Out-of-sample validation
    ↓
Calibration
    ↓
Shadow evaluation
    ↓
Controlled promotion
    ↓
Continuous monitoring
```

Failed predictions are especially valuable for:

- Regime-specific error analysis
- Overconfidence detection
- News-event failures
- False breakouts
- Poor stop placement
- Feature drift
- Calibration drift
- Source reliability problems

The current repository records and evaluates outcomes, but does not yet implement a persistent strategy-learning or model-promotion layer.

---

## 23. Knowledge Acquisition and Knowledge Ingestion

Knowledge acquisition is the process of obtaining trading-related material.

Knowledge ingestion is the process of turning that material into traceable, usable knowledge.

The ingestion process should preserve:

- Source
- Timestamp
- Author
- Original context
- Reliability
- Claims
- Definitions
- Hypotheses
- Opinions
- Conflicting claims

A research paper may suggest a feature. A strategy document may describe a setup. A YouTube transcript may contain an opinion. None of these automatically proves that a strategy works.

The material must be separated into:

```text
Knowledge
    ↓
Hypothesis
    ↓
Formal rule or feature
    ↓
Historical validation
    ↓
Calibrated and monitored strategy
```

Knowledge acquisition should support trading intelligence, but it must not replace market data, backtesting or prediction evaluation.

---

## 24. Evidence Provenance

Every important conclusion should be traceable.

The chain should be:

```text
Conclusion
    ↓
Scenario or decision
    ↓
Evidence item
    ↓
Calculation or interpretation
    ↓
Underlying data
    ↓
Source
    ↓
Timestamp
    ↓
Data version
    ↓
Model and pipeline version
```

For example:

```text
Conclusion:
Bullish breakout scenario is supported

Evidence:
Price closed above resistance with elevated volume

Source:
Exchange OHLCV provider

Timestamp:
Specific candle close time

Data:
High, low, close and volume values

Analysis:
Resistance clustering plus relative-volume calculation

Model:
Technical pipeline version

Limitations:
Higher timeframe conflicts and event risk
```

The existing repository already has important provenance mechanisms:

- `Provenance`
- `DataQuality`
- Source tiers
- Retrieval timestamps
- Evidence identifiers
- Content-addressed evidence IDs
- Prediction pipeline versions
- Limitation lists
- Stable prediction IDs

This is essential for explainable and auditable Trading Intelligence.

---

## 25. Conflict Resolution

The system must not blindly average all modules.

Consider:

```text
Technical analysis: bullish
News: bearish
Fundamentals: neutral
Market regime: bearish
```

The correct response is not:

```text
Bullish + bearish + neutral + bearish = average bullish/bearish score
```

Instead, the system should ask:

### What is the timeframe?

For a five-day trade:

- Technical structure may be highly relevant
- News freshness may be highly relevant
- Market regime is important context
- Fundamentals may be slower-moving context

### How reliable is each source?

- Primary filing: high source reliability
- Anonymous social post: low source reliability
- Fresh event calendar: potentially high
- Old analyst article: lower freshness
- Mock data: not reliable for production conclusions

### Is the conflict directional or risk-related?

A bearish news item may not prove price will fall, but it may increase event risk.

A bearish regime may not invalidate a long setup, but it may require:

- Stronger confirmation
- Smaller size
- Better reward/risk
- A shorter holding period
- A breakout confirmation instead of anticipatory entry

### Is there a hard constraint?

Examples of hard constraints:

- Invalid data
- No defined stop
- High-impact event inside the horizon
- Probability model contradicts the setup
- Historical validation fails
- Portfolio risk limit exceeded

The existing critic follows a sensible hierarchy:

- Technical evidence conflict can produce a hard failure
- Reliable calibrated probability disagreement can produce a hard failure
- News and fundamentals usually create warnings
- Regime conflict usually creates warnings
- Reliable high-impact event risk can produce a hard failure
- Mock or unusable data produces insufficient evidence

For the example above, the system might conclude:

```text
Short-term bullish technical structure exists, but the higher timeframe is
conflicting and the setup is opposed by fresh bearish news.

Decision:
Wait for confirmed breakout and news stabilization, or no trade.

Reason:
The bullish technical case is not strong enough to overcome the event and
risk-regime conflict under the current horizon.
```

The answer depends on the quality, freshness, horizon and predictive history of each evidence source.

---

## 26. Decision Engine

The complete decision flow is:

```text
User Request
    ↓
Trading Intent Normalization
    ↓
Analysis Task
    ↓
Data Collection Plan
    ↓
Market Data Acquisition
    ↓
Data Validation and Quality Gate
    ↓
Technical Intelligence
    ↓
Market Structure
    ↓
Fundamental Intelligence
    ↓
News and Event Intelligence
    ↓
Sentiment Intelligence
    ↓
Market Regime
    ↓
Cross-Market and Relative Strength
    ↓
Multi-Timeframe Confirmation
    ↓
Optional Chart/Vision Evidence
    ↓
Evidence Ledger
    ↓
Evidence Fusion
    ↓
Scenario Generation
    ↓
Trade Setup Construction
    ↓
Risk Analysis
    ↓
Historical Validation / Backtest
    ↓
Probability Estimation
    ↓
Calibration and Sample-Size Gate
    ↓
Critic / Conflict Resolution
    ↓
Decision Recommendation
    ↓
Explanation and Evidence Report
    ↓
Prediction Record
    ↓
Future Outcome Evaluation
```

Some data-collection steps can run in parallel. The important point is that later stages depend on validated outputs, not raw unverified text.

---

## 27. End-to-End Workflow

A typical Trading Intelligence request follows this sequence:

```text
Observe
    ↓
Normalize user intent
    ↓
Collect data
    ↓
Validate data
    ↓
Analyze price and context
    ↓
Create evidence
    ↓
Detect contradictions
    ↓
Generate scenarios
    ↓
Construct possible setups
    ↓
Assess risk
    ↓
Backtest and validate
    ↓
Estimate and calibrate probabilities
    ↓
Critique the proposal
    ↓
Produce the report
    ↓
Record the prediction
    ↓
Observe the later result
    ↓
Evaluate performance
    ↓
Improve calibration and strategy knowledge
```

---

## 28. Example Analysis Lifecycle: NVDA for Five Trading Days

User request:

> Analyze NVDA for the next 5 trading days.

### Step 1: Normalize intent

The system resolves:

- Instrument: NVDA
- Exchange and asset class
- Prediction horizon: five trading days
- Likely style: short-term swing
- Direction: unbiased
- Required output: full analysis and possible setup
- Default risk assumptions, if any
- Analysis timestamp

If a key assumption is not supplied, the report must disclose it.

### Step 2: Build the data plan

The planner requests:

- Daily NVDA candles
- Intraday NVDA candles for entry context
- Current quote
- Volume
- Relevant benchmark data
- Nasdaq or technology-sector data
- Volatility context
- News
- Earnings calendar
- Company announcements
- Latest available fundamentals
- Optional chart screenshot if supplied

The historical window must be long enough for:

- Moving-average warm-up
- Volatility estimates
- Market structure
- Historical analogues
- Probability model training
- Holdout evaluation

### Step 3: Validate data

The data layer checks:

- Correct NVDA identity
- Correct exchange
- Timezone
- Missing bars
- Stale bars
- Adjusted versus unadjusted prices
- Timestamp ordering
- Provider reliability
- Event timestamp consistency

If the latest market data is stale, the system should say so before analyzing.

### Step 4: Analyze technical structure

The technical layer calculates:

- Trend
- Moving averages
- RSI
- MACD
- ATR
- Bollinger position
- VWAP
- ADX
- Volume behavior
- Recent returns
- Volatility

The structure layer identifies:

- Recent swing highs
- Recent swing lows
- Support zones
- Resistance zones
- Higher highs and higher lows
- Lower highs and lower lows
- Breakout or breakdown conditions
- Range conditions

### Step 5: Check multiple timeframes

The system may compare:

- Daily trend
- Four-hour trend
- One-hour entry structure
- Weekly context

It asks:

- Does the five-day trade agree with the higher timeframe?
- Is this a counter-trend trade?
- Is the entry timeframe confirming or contradicting the daily view?

### Step 6: Analyze fundamentals

The system examines:

- Revenue and earnings growth
- Margins
- Cash flow
- Valuation
- Debt
- Guidance
- Semiconductor-sector conditions
- AI-related demand
- Company-specific catalysts

For a five-day horizon, fundamentals are mainly used as:

- Catalyst context
- Event context
- Valuation pressure
- Longer-term backdrop

They should not be treated as a precise five-day price forecast.

### Step 7: Analyze news and events

The system searches for:

- Earnings announcements
- Guidance changes
- Regulatory developments
- Product announcements
- Supply-chain news
- Semiconductor-sector news
- Analyst revisions
- Macro events affecting technology stocks
- Central-bank decisions
- Relevant geopolitical developments

It removes duplicates, timestamps each item, classifies relevance and identifies conflicts.

If earnings fall within the five-day horizon, the report should identify that as major event risk even if the direction is unknown.

### Step 8: Analyze market regime and context

The system determines:

- Whether NVDA is trending or ranging
- Whether volatility is high or low
- Whether the broad market is risk-on or risk-off
- Whether NVDA is outperforming or underperforming its benchmark
- Whether the semiconductor sector confirms the move

A bullish NVDA chart inside a broad risk-off regime is not equivalent to the same chart in a broad risk-on regime.

### Step 9: Create evidence objects

Examples:

```text
Price is above the 50-day moving average
```

```text
Recent structure shows higher highs and higher lows
```

```text
Volume expanded on the latest breakout attempt
```

```text
Technology benchmark is weakening
```

```text
An earnings event is inside the five-day horizon
```

```text
Fundamental valuation is elevated
```

Each evidence item receives:

- Type
- Direction
- Weight
- Confidence
- Source
- Timestamp
- Data quality
- Calculation details
- Reliability status

### Step 10: Generate scenarios

#### Bullish scenario

Possible condition:

- NVDA holds above support
- Breaks resistance
- Volume expands
- Nasdaq and semiconductor benchmarks confirm
- No adverse event occurs

The report defines:

- Trigger
- Entry zone
- Stop
- Target
- Invalidation
- Evidence
- Probability
- Confidence

#### Bearish scenario

Possible condition:

- Breakout fails
- Price loses support
- Sector weakens
- Broad market remains risk-off
- Negative catalyst emerges

The report defines the bearish trigger and invalidation separately.

#### Neutral scenario

Possible condition:

- Price remains between support and resistance
- Volume contracts
- Momentum loses direction
- No catalyst produces a breakout

This scenario may be the highest-probability outcome even when the directional scenarios have attractive reward/risk.

### Step 11: Estimate probability

The quant layer defines a precise target, such as:

> Will NVDA close higher five trading bars from the analysis timestamp?

It then:

- Builds causal features
- Uses historical labels
- Splits data chronologically
- Trains the model
- Calibrates it
- Tests on holdout data
- Compares it with a naive baseline
- Reports sample size and calibration metrics

If the model is unreliable, the report must not surface a confident percentage.

### Step 12: Construct risk geometry

The risk engine determines:

- Entry assumption
- ATR or structural stop
- Target levels
- Risk per share
- Reward per share
- Reward/risk ratio
- Position size if account equity is supplied
- Maximum loss
- Event-risk adjustment
- Correlation and portfolio exposure if available

If there is no acceptable risk/reward, the setup is rejected regardless of directional optimism.

### Step 13: Critic and conflict resolution

The critic checks:

- Data quality
- Data source
- Evidence sufficiency
- Directional agreement
- Risk/reward
- Historical validation
- Probability calibration
- News
- Fundamentals
- Regime
- Relative strength
- Macro posture
- Multi-timeframe alignment
- Event risk

The critic may conclude:

```text
Technical structure is bullish, but the higher timeframe is conflicting,
the broad market is risk-off, and earnings are within the horizon.

Decision:
WAIT / NO TRADE until the trigger confirms and event risk is resolved.
```

### Step 14: Produce report and record prediction

The system returns the report and records:

- What was believed
- When it was believed
- Why it was believed
- Which model produced it
- Which data supported it
- What would invalidate it
- What horizon will be used for evaluation

### Step 15: Evaluate later

After five trading days:

- Fetch later NVDA candles
- Locate the prediction entry bar
- Measure the realized return
- Determine realized direction
- Mark the prediction resolved
- Score the directional prediction
- Score the probability if one was reliable
- Add the result to performance statistics

---

## 29. Final Output Structure

The user should receive a structured report containing:

### Instrument

- Symbol
- Exchange
- Asset class
- Current price
- Analysis timestamp

### Market context

- Broad-market posture
- Sector performance
- Relative strength
- Correlations
- Market session
- Volatility

### Market regime

- Trending, ranging, volatile or unknown
- Bullish, bearish, neutral or transitioning posture
- Regime confidence
- Regime limitations

### Technical structure

- Trend
- Market structure
- Support
- Resistance
- Breakout or breakdown state
- Moving-average context
- Momentum
- Volume
- Volatility
- Multi-timeframe alignment

### Fundamental context

- Earnings
- Revenue
- Margins
- Debt
- Cash flow
- Valuation
- Guidance
- Sector context
- Fundamental freshness

### News and events

- Relevant headlines
- Event calendar
- Source quality
- Freshness
- Sentiment
- Upcoming catalysts
- Conflicting information

### Scenarios

For each bullish, bearish and neutral scenario:

- Thesis
- Trigger
- Expected behavior
- Invalidation
- Targets
- Risk
- Reward
- Probability
- Confidence
- Supporting evidence
- Contradicting evidence

### Potential setup

- Direction
- Entry zone
- Trigger
- Stop
- Target
- Risk/reward
- Position sizing assumptions
- Maximum loss
- Event risk
- Correlation risk

### Validation

- Backtest period
- Sample size
- Out-of-sample result
- Win rate
- Expectancy
- Drawdown
- Calibration metrics
- Regime-specific behavior
- Limitations

### Final conclusion

Possible conclusions include:

```text
APPROVED SETUP
```

```text
REJECTED SETUP
```

```text
WAIT FOR TRIGGER
```

```text
NO TRADE — INSUFFICIENT EVIDENCE
```

The report must explicitly state:

- Probabilities are estimates
- They are conditional on the stated horizon and data
- They are not guarantees
- Historical performance does not guarantee future performance

---

## 30. Complete Layered Architecture

```text
┌────────────────────────────────────────────┐
│ Presentation Layer                         │
│ Reports, explanations, CLI/API, charts     │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Decision Layer                              │
│ Scenarios, setup selection, risk, critic    │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Analysis Layer                              │
│ Technical, fundamental, news, regime,      │
│ sentiment, cross-market, vision            │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Intelligence / Evidence Layer               │
│ Features, evidence, provenance, fusion      │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Data Layer                                  │
│ Providers, normalization, validation,       │
│ freshness, sessions, historical data        │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ External Sources                            │
│ Exchanges, vendors, filings, calendars,     │
│ news, benchmarks, charts                    │
└────────────────────────────────────────────┘

Parallel feedback systems:

Validation Layer
    Backtesting, calibration, outcomes, performance

Learning Layer
    Research knowledge, strategy hypotheses,
    error analysis, drift detection, model updates
```

### Data Layer

Responsibilities:

- Acquire market and contextual data
- Normalize instruments, timestamps and sessions
- Validate data
- Assess freshness
- Track source provenance
- Surface limitations
- Provide historical and current datasets

### Intelligence Layer

Responsibilities:

- Compute technical features
- Analyze fundamentals
- Analyze news and events
- Derive sentiment
- Detect regimes
- Analyze benchmarks and relative strength
- Compare timeframes
- Interpret optional visual chart evidence

### Analysis Layer

Responsibilities:

- Convert measurements into evidence
- Group evidence into families
- Fuse evidence
- Detect contradictions
- Generate scenarios
- Construct candidate setups

### Decision Layer

Responsibilities:

- Assess risk
- Apply account and portfolio constraints
- Evaluate risk/reward
- Apply critic rules
- Approve, reject or defer a setup
- Produce the decision recommendation

### Validation Layer

Responsibilities:

- Backtest setups
- Prevent look-ahead bias
- Calibrate probabilities
- Track predictions
- Resolve outcomes
- Measure performance
- Detect reliability and sample-size problems

### Learning Layer

Responsibilities:

- Acquire research knowledge
- Store claims and hypotheses
- Analyze prediction failures
- Monitor drift
- Improve calibration
- Test new features and strategies
- Promote only validated changes

### Presentation Layer

Responsibilities:

- Produce the final report
- Explain evidence
- Show contradictions
- Show limitations
- Show scenarios and risks
- Expose probabilities and confidence correctly
- Preserve auditability

---

## 31. Major Component Responsibilities

| Module | Consumes | Produces |
|---|---|---|
| Intent normalizer | User request | Structured analysis task |
| Instrument resolver | Symbol text, exchange context | Canonical instrument |
| Market data gateway | Instrument, timeframe, provider | Validated OHLCV and quotes |
| Data-quality layer | Raw data | Quality status, freshness, limitations |
| Technical analysis | OHLCV | Indicators and technical snapshot |
| Market structure | OHLCV | Swings, levels, trend, breakouts |
| Volume analysis | Volume and price | Participation and confirmation read |
| Fundamental analysis | Financial statements and guidance | Health, growth, valuation factors |
| News analysis | Sourced news | Events, relevance, sentiment and evidence |
| Event calendar | Scheduled events | Catalyst and event-risk context |
| Sentiment analysis | News, social and positioning | Sentiment distribution and uncertainty |
| Regime detector | Price, volatility and breadth | Market character and regime |
| Cross-market context | Benchmarks and related instruments | Macro, relative-strength and correlation context |
| Multi-timeframe layer | Multiple timeframe analyses | Alignment or conflict |
| Vision layer | Screenshots or chart images | Visual evidence and grounding |
| Evidence layer | All analysis outputs | Traceable weighted evidence |
| Fusion layer | Evidence ledger | Directional reads and contradictions |
| Scenario engine | Evidence and market state | Bullish, bearish and neutral scenarios |
| Risk engine | Scenarios, levels, volatility, account constraints | Stop, target, sizing and exposure |
| Probability engine | Features, labels and historical outcomes | Raw and calibrated probabilities |
| Backtest engine | Strategy definition and historical data | Historical performance |
| Critic | Analysis, scenarios, risk and validation | Approve, reject or insufficient evidence |
| Report builder | All validated outputs | Explainable final report |
| Prediction recorder | Final report | Immutable prediction contract |
| Outcome evaluator | Prediction and later market data | Resolved outcome |
| Performance aggregator | Outcomes | Accuracy, calibration and track record |
| Learning layer | Research and outcomes | Validated hypotheses, model updates and error analysis |

---

## 32. Module Communication

Modules should communicate through typed domain objects rather than unstructured prose.

The primary communication objects are:

- Analysis task
- Market data
- Data-quality assessment
- Technical snapshot
- Fundamental analysis
- News analysis
- Event calendar
- Regime analysis
- Evidence
- Scenario
- Risk assessment
- Probability estimate
- Backtest result
- Critic report
- Trading report
- Prediction record
- Prediction outcome
- Performance summary

An event bus may announce state changes such as:

- Market data updated
- Analysis completed
- Regime detected
- News analyzed
- Risk assessed
- Backtest completed
- Probability estimated
- Signal critiqued
- Prediction created
- Prediction resolved
- Performance evaluated

The event bus is useful for monitoring and audit, but the primary analytical result should remain available as an explicit structured response.

---

## 33. What Trading Intelligence is NOT

AetherOS Trading Intelligence is not:

### A simple stock chatbot

A chatbot can produce fluent opinions. Trading Intelligence must produce traceable evidence and measurable uncertainty.

### An indicator calculator

Indicators are measurements. The system must understand context, regime, interaction and contradictions.

### A news summarizer

News must be linked to instruments, events, time horizons, reliability and market impact.

### A chart screenshot analyzer

Screenshots are supplemental visual evidence. Structured market data remains the quantitative foundation.

### A signal generator alone

A signal without risk, invalidation, probability, validation and tracking is incomplete.

### An LLM guessing market direction

The LLM may interpret and explain. It must not invent quantitative probabilities.

### A collection of disconnected tools

The modules must share:

- Canonical data contracts
- Provenance
- Evidence
- Time horizons
- Risk assumptions
- Model versions
- Validation results
- Prediction outcomes

What makes it a true Trading Intelligence System is the closed loop:

```text
Observe
    ↓
Analyze
    ↓
Construct evidence
    ↓
Generate scenarios
    ↓
Assess risk
    ↓
Validate
    ↓
Explain
    ↓
Record prediction
    ↓
Observe outcome
    ↓
Evaluate
    ↓
Calibrate and improve
```

The system should always prefer:

```text
I do not have enough reliable evidence.
```

over:

```text
The market will definitely go up.
```

---

## 34. Future Evolution

The conceptual build order is:

### Build first

1. Canonical instrument and timeframe handling
2. Reliable historical and current market data
3. Data validation and freshness
4. Provenance and data-quality contracts
5. Technical indicators
6. Market structure
7. Evidence objects
8. Deterministic risk geometry
9. Basic critic and no-trade behavior
10. Explainable report format
11. Prediction contract
12. Look-ahead-safe backtesting

### Build next

1. Reliable news and event providers
2. Point-in-time fundamentals
3. Market regime detection
4. Benchmark and sector context
5. Multi-timeframe analysis
6. Calibrated probabilities
7. Durable prediction records
8. Outcome resolution
9. Performance and calibration reporting
10. Scenario analysis
11. Conditional entry and trigger logic

### Build later

1. Order-flow intelligence
2. Market breadth
3. Options and positioning
4. Portfolio-level correlation and exposure
5. Realistic execution simulation
6. Chart screenshot intelligence
7. Social and analyst sentiment
8. Continuous monitoring
9. Regime-specific model selection
10. Research-document ingestion
11. Strategy registry
12. Controlled model promotion
13. Continuous learning and drift detection

The important order is:

```text
Reliable data
    ↓
Deterministic analysis
    ↓
Evidence
    ↓
Risk
    ↓
Backtesting
    ↓
Calibration
    ↓
Prediction tracking
    ↓
Scenario intelligence
    ↓
Advanced sources and learning
```

---

## 35. Design Principles

The Trading Intelligence System should be:

### Evidence-driven

Every important conclusion must be supported by measurable or traceable evidence.

### Multi-source

No single data source should be treated as the complete truth when relevant independent sources are available.

### Multi-timeframe

A short-term setup should be evaluated against higher-timeframe structure and context.

### Context-aware

Indicators and events must be interpreted according to the instrument, horizon and market context.

### Regime-aware

The same strategy can perform differently in trending, ranging, volatile or transitional markets.

### Risk-aware

The system must evaluate the potential loss and reward, not only the direction.

### Probabilistic

Predictions must be expressed as estimates under defined conditions, not certainties.

### Backtestable

Recurring setup concepts must be testable on historical data without look-ahead bias.

### Calibrated

A stated probability must be evaluated against observed outcomes.

### Explainable

The user must understand why the system reached its conclusion.

### Traceable

Conclusions must link back to evidence, data, sources, timestamps and model versions.

### Continuously evaluated

Predictions must be recorded, resolved and measured over time.

### Conservative under uncertainty

Missing, stale, contradictory or insufficient data must reduce confidence or produce a no-trade result.

### Honest about limitations

The system must expose model limitations, sample size, source quality, regime dependence and uncertainty rather than hiding them.

---

## 36. Core Principle

AetherOS Trading Intelligence is a closed-loop evidence system:

```text
User intent
    ↓
Validated information
    ↓
Contextual intelligence
    ↓
Evidence
    ↓
Scenarios
    ↓
Risk-aware decision support
    ↓
Prediction record
    ↓
Outcome evaluation
    ↓
Calibration and learning
```

Its purpose is not to sound certain.

Its purpose is to produce the most evidence-backed, risk-aware, probabilistically honest and auditable analysis possible under the available information.
