# TRADING.md

# AetherOS Trading Intelligence Architecture

> **Purpose**
>
> The **Trading** module transforms AetherOS into an autonomous trading research and execution assistant. It continuously monitors financial markets, understands price action, analyzes technical structures, generates trade ideas, manages risk, performs backtesting, and can optionally execute trades through supported brokers.
>
> The Trading module is the **financial intelligence system** of AetherOS.

---

# Design Philosophy

The Trading module should be:

* Data-driven
* Modular
* Explainable
* Risk-first
* Event-driven
* Multi-market
* Multi-timeframe
* AI-assisted
* Backtestable
* Extensible

---

# Responsibilities

The Trading module is responsible for:

* Market data collection
* Chart analysis
* Technical analysis
* Smart Money Concepts (SMC)
* ICT strategy detection
* Pattern recognition
* Trade planning
* Risk management
* Portfolio monitoring
* Order execution
* Performance analytics
* Trading journal

The Trading module **does not**:

* Control the desktop directly
* Perform OCR independently
* Store long-term memory
* Manage user authentication
* Make unrestricted autonomous financial decisions without configured policies

---

# Architecture

```text
Market Data

↓

Chart Engine

↓

Analysis Engine

↓

Strategy Engine

↓

Risk Manager

↓

Decision Engine

↓

Execution Engine

↓

Broker API

↓

Portfolio Manager
```

---

# Directory Structure

```text
trading/
│
├── __init__.py
│
├── api/
│
├── market/
│
├── charts/
│
├── analysis/
│
├── indicators/
│
├── smc/
│
├── ict/
│
├── strategies/
│
├── signals/
│
├── risk/
│
├── execution/
│
├── brokers/
│
├── portfolio/
│
├── positions/
│
├── orders/
│
├── journal/
│
├── backtesting/
│
├── simulation/
│
├── scanner/
│
├── alerts/
│
├── news/
│
├── calendar/
│
├── analytics/
│
├── models/
│
├── events/
│
├── utils/
│
└── tests/
```

---

# Market Data Engine

Folder

```text
trading/market/
```

Responsibilities

* Live prices
* Historical candles
* Volume
* Order book
* Tick data
* Multi-exchange support

Supported Markets

* Forex
* Crypto
* Stocks
* Indices
* Commodities

---

# Chart Engine

Folder

```text
trading/charts/
```

Responsibilities

* Candlestick data
* Timeframe management
* Multi-chart synchronization
* Screenshot generation
* Chart annotations

Supported Timeframes

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

---

# Analysis Engine

Folder

```text
trading/analysis/
```

Performs

* Trend analysis
* Market structure
* Volume analysis
* Liquidity analysis
* Volatility analysis
* Momentum analysis

Output

Structured market report.

---

# Indicators

Folder

```text
trading/indicators/
```

Built-in Indicators

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

Supports custom indicators.

---

# Smart Money Concepts (SMC)

Folder

```text
trading/smc/
```

Detects

* Break of Structure (BOS)
* Change of Character (CHoCH)
* Order Blocks
* Liquidity Sweeps
* Mitigation Blocks
* Fair Value Gaps (FVG)
* Premium & Discount Zones
* Equal Highs / Lows

---

# ICT Engine

Folder

```text
trading/ict/
```

Analyzes

* Daily Bias
* Market Structure Shift
* Kill Zones
* Optimal Trade Entry (OTE)
* Liquidity Pools
* Judas Swing
* Power of Three
* Session Models

Provides ICT-based trade setups.

---

# Strategy Engine

Folder

```text
trading/strategies/
```

Responsibilities

* Build strategies
* Load strategies
* Compare strategies
* Optimize parameters

Examples

* Scalping
* Swing Trading
* Trend Following
* Mean Reversion
* ICT
* SMC
* Breakout

---

# Signal Engine

Folder

```text
trading/signals/
```

Generates

* Buy signals
* Sell signals
* Exit signals
* Partial exit signals
* Stop-loss updates

Every signal contains

* Confidence
* Risk
* Reasoning
* Supporting evidence

---

# Risk Manager

Folder

```text
trading/risk/
```

Responsibilities

* Position sizing
* Stop-loss calculation
* Take-profit calculation
* Risk-reward ratio
* Daily loss limits
* Maximum exposure

Example

```text
Risk

1%

↓

Position Size

↓

Stop Loss

↓

Take Profit
```

---

# Execution Engine

Folder

```text
trading/execution/
```

Responsibilities

* Validate orders
* Submit orders
* Modify orders
* Cancel orders
* Retry failed requests

Supports

* Market Orders
* Limit Orders
* Stop Orders
* Stop-Limit Orders

---

# Broker Layer

Folder

```text
trading/brokers/
```

Responsibilities

Connect to

* Interactive Brokers
* Binance
* Bybit
* Alpaca
* MetaTrader (future)
* Paper Trading

Every broker implements a common interface.

---

# Portfolio Manager

Folder

```text
trading/portfolio/
```

Tracks

* Balance
* Equity
* Margin
* PnL
* Holdings
* Performance

---

# Position Manager

Folder

```text
trading/positions/
```

Stores

* Open positions
* Closed positions
* Entry price
* Exit price
* Stop-loss
* Take-profit

---

# Order Manager

Folder

```text
trading/orders/
```

Handles

* Pending orders
* Filled orders
* Cancelled orders
* Rejected orders
* Order history

---

# Trading Journal

Folder

```text
trading/journal/
```

Automatically records

* Screenshots
* Entry reason
* Exit reason
* Emotions (optional)
* Risk
* Profit/Loss
* Lessons learned

---

# Backtesting Engine

Folder

```text
trading/backtesting/
```

Responsibilities

* Historical testing
* Walk-forward testing
* Performance metrics
* Strategy comparison

Metrics

* Win Rate
* Profit Factor
* Sharpe Ratio
* Max Drawdown
* Expectancy

---

# Paper Trading

Folder

```text
trading/simulation/
```

Provides

* Virtual account
* Live market simulation
* Strategy testing
* No financial risk

Recommended before live execution.

---

# Market Scanner

Folder

```text
trading/scanner/
```

Scans

* Multiple symbols
* Multiple timeframes
* Pattern detection
* SMC opportunities
* ICT setups

---

# Alerts

Folder

```text
trading/alerts/
```

Supports

* Price alerts
* Pattern alerts
* Signal alerts
* News alerts
* Portfolio alerts

Delivery

* Desktop
* Email
* Mobile
* Discord
* Telegram

---

# News Engine

Folder

```text
trading/news/
```

Tracks

* Financial news
* Earnings
* Crypto news
* Market sentiment

Can be summarized by the LLM.

---

# Economic Calendar

Folder

```text
trading/calendar/
```

Tracks

* CPI
* FOMC
* NFP
* Interest Rates
* GDP
* Employment Data

Warns before high-impact events.

---

# Trading API

Folder

```text
trading/api/
```

Functions

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

Higher-level modules use only this API.

---

# Events

Folder

```text
trading/events/
```

Examples

```text
MarketOpened

SignalGenerated

OrderSubmitted

OrderFilled

PositionClosed

RiskLimitReached
```

---

# Models

Folder

```text
trading/models/
```

Contains

* Candle
* TradeSignal
* Order
* Position
* Strategy
* Portfolio
* RiskProfile

---

# Analytics

Folder

```text
trading/analytics/
```

Measures

* Win rate
* Average R:R
* Monthly return
* Strategy performance
* Execution latency
* Slippage

---

# Execution Flow

```text
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
```

---

# Technology Stack

| Component            | Technology                |
| -------------------- | ------------------------- |
| Market Data          | CCXT, Broker APIs         |
| Chart Processing     | pandas, NumPy             |
| Technical Indicators | pandas-ta / TA-Lib        |
| Backtesting          | Backtesting.py / vectorbt |
| Portfolio Analytics  | pandas                    |
| AI Analysis          | LLM Module                |
| OCR Support          | Vision Module             |
| Storage              | SQLite / PostgreSQL       |
| Visualization        | Plotly                    |
| Async Runtime        | asyncio                   |

---

# Integration With Other Modules

| Module     | Purpose                                             |
| ---------- | --------------------------------------------------- |
| Vision     | Analyze TradingView screenshots and UI              |
| Browser    | Control TradingView or broker web platforms         |
| Desktop    | Native application automation                       |
| Memory     | Store trade history and learned strategies          |
| Planner    | Build trading workflows                             |
| Reasoning  | Evaluate trade quality and scenarios                |
| Automation | Schedule market scans and reports                   |
| Runtime    | Execute trading pipelines                           |
| LLM        | Explain setups, summarize markets, generate reports |

---

# Design Principles

1. Separate market analysis from trade execution.
2. Never execute trades without passing risk validation.
3. Every trade must have a documented rationale.
4. Support both paper trading and live trading.
5. Strategies should be modular and independently testable.
6. Every signal should include confidence and supporting evidence.
7. Keep broker integrations behind a common abstraction layer.
8. Learn from completed trades through journaling and memory.

---

# Success Criteria

The Trading module is complete when:

* ✅ Live and historical market data are available.
* ✅ Technical, SMC, and ICT analyses are generated automatically.
* ✅ Risk management validates every proposed trade.
* ✅ Strategies can be backtested and compared.
* ✅ Paper trading simulates live execution safely.
* ✅ Broker integrations support live order execution.
* ✅ Portfolio and journal update automatically.
* ✅ Alerts notify users of important market events.
* ✅ The Trading API integrates seamlessly with the Planner, Reasoning, Memory, and Automation modules.

The **Trading** module is the **financial decision system** of AetherOS. It combines market data, technical analysis, AI reasoning, structured risk management, and automated execution to create an intelligent trading assistant capable of research, simulation, and, when configured, live market participation.
