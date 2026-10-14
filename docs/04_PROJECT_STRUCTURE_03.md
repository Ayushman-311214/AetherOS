# 04_PROJECT_STRUCTURE.md

# Part 3 — Agents Project Structure

> **Purpose**
>
> The `agents/` directory contains every intelligent decision-making component in AetherOS.
>
> An **Agent** is responsible for reasoning within a specific domain. Agents coordinate with the Core, use Engines to perform actions, and collaborate through the Coordinator.
>
> **Rule:** An Agent decides *what* to do within its domain. It never directly implements low-level execution.

---

# Directory Structure

```text
agents/
│
├── __init__.py
├── base_agent.py
├── interfaces.py
├── registry.py
├── coordinator.py
├── factory.py
├── context.py
├── manager.py
├── lifecycle.py
│
├── ceo_agent/
├── planner_agent/
├── vision_agent/
├── desktop_agent/
├── browser_agent/
├── memory_agent/
├── research_agent/
├── coding_agent/
├── trading_agent/
├── voice_agent/
├── learning_agent/
└── verification_agent/
```

---

# Agent Layer Philosophy

Agents transform plans into intelligent decisions.

```text
User Goal

↓

Core

↓

Agent

↓

Engine

↓

Controller

↓

Operating System
```

Example

```text
User

↓

Analyze Bitcoin

↓

Trading Agent

↓

Trading Engine

↓

Indicators

↓

Analysis
```

---

# Standard Agent Interface

Every agent inherits from `BaseAgent`.

```python
class BaseAgent:

    async def initialize(self):
        ...

    async def execute(self, task):
        ...

    async def verify(self):
        ...

    async def pause(self):
        ...

    async def resume(self):
        ...

    async def shutdown(self):
        ...
```

Every new agent automatically supports the same lifecycle.

---

# base_agent.py

## Purpose

Defines the common functionality shared by every agent.

Responsibilities

* Agent lifecycle
* Logging
* Context handling
* Metrics
* Event publishing
* Error handling

Never place domain-specific logic here.

---

# interfaces.py

Contains abstract interfaces.

Example

```python
class AgentInterface:

    async def execute(self, task):
        pass
```

Benefits

* Easier testing
* Swappable implementations
* Cleaner architecture

---

# registry.py

Registers every available agent.

Example

```python
AGENTS = {

    "vision": VisionAgent,

    "desktop": DesktopAgent,

    "browser": BrowserAgent,

    "memory": MemoryAgent,

    "research": ResearchAgent,

    "coding": CodingAgent,

    "trading": TradingAgent,

    "voice": VoiceAgent,

    "learning": LearningAgent,

    "verification": VerificationAgent
}
```

The Core discovers agents through this registry.

---

# coordinator.py

Coordinates communication between agents.

Responsibilities

* Route requests
* Merge results
* Prevent conflicts
* Track running agents

Agents never call each other directly.

---

# factory.py

Creates agent instances.

Example

```python
factory.create("vision")
```

Instead of

```python
VisionAgent()
```

This makes dependency injection much easier.

---

# context.py

Builds agent-specific context.

Example

Vision Agent receives

```text
Screenshot

Current Window

OCR Cache

Previous Detection

Memory Context
```

Desktop Agent receives

```text
Mouse Position

Focused Window

Clipboard

Keyboard State
```

---

# manager.py

Tracks

* Active Agents
* Idle Agents
* Busy Agents
* Failed Agents
* Agent Metrics

---

# lifecycle.py

Tracks agent states.

```text
Created

↓

Initialized

↓

Idle

↓

Running

↓

Paused

↓

Completed

↓

Shutdown
```

---

# CEO Agent

Directory

```text
ceo_agent/

agent.py

decision.py

strategy.py

planning.py

metrics.py

policies.py
```

---

Purpose

Highest-level reasoning.

Responsibilities

* Long-term objectives
* Strategy
* Priorities
* Resource allocation
* Global decisions

Never executes tools.

---

# Planner Agent

Directory

```text
planner_agent/

planner.py

goal_parser.py

workflow.py

optimizer.py

validator.py
```

Responsibilities

* Parse goals
* Create workflows
* Estimate execution
* Build task graph

Produces executable plans.

---

# Vision Agent

Directory

```text
vision_agent/

agent.py

observer.py

ocr.py

layout.py

icons.py

objects.py

charts.py

verification.py
```

Responsibilities

* Observe screen
* OCR
* Detect objects
* Understand UI
* Detect charts
* Return structured observations

Never moves the mouse.

---

# Desktop Agent

Directory

```text
desktop_agent/

agent.py

mouse.py

keyboard.py

windows.py

clipboard.py

monitor.py

verification.py
```

Responsibilities

* Decide desktop actions
* Select desktop tools
* Verify desktop state

Execution is delegated to the Desktop Engine.

---

# Browser Agent

Directory

```text
browser_agent/

agent.py

navigation.py

forms.py

cookies.py

downloads.py

tabs.py

sessions.py
```

Responsibilities

* Navigate websites
* Fill forms
* Manage tabs
* Login
* Download files
* Scrape pages

Uses Browser Engine internally.

---

# Memory Agent

Directory

```text
memory_agent/

agent.py

retrieval.py

storage.py

ranking.py

compression.py

summaries.py

cleanup.py
```

Responsibilities

* Store memories
* Retrieve context
* Compress history
* Forget irrelevant information
* Rank memories

Supports

* Working Memory
* Session Memory
* Long-Term Memory
* Semantic Memory

---

# Research Agent

Directory

```text
research_agent/

agent.py

search.py

reader.py

extractor.py

ranking.py

summarizer.py

sources.py
```

Responsibilities

* Search information
* Read documentation
* Compare sources
* Extract facts
* Summarize findings

Future

Academic papers

News

PDFs

Documentation

---

# Coding Agent

Directory

```text
coding_agent/

agent.py

generator.py

reviewer.py

debugger.py

tester.py

documentation.py

refactor.py
```

Responsibilities

* Generate code
* Review code
* Explain code
* Debug issues
* Write tests
* Generate documentation

Supports

Python

TypeScript

C++

Rust

SQL

---

# Trading Agent

Directory

```text
trading_agent/

agent.py

market.py

indicators.py

smc.py

ict.py

risk.py

strategies.py

validator.py

reports.py
```

Responsibilities

* Market analysis
* ICT
* SMC
* Indicators
* Risk
* Position sizing
* Report generation

Never executes trades directly.

---

# Voice Agent

Directory

```text
voice_agent/

agent.py

stt.py

tts.py

vad.py

stream.py

wake_word.py
```

Responsibilities

* Speech Recognition
* Voice Synthesis
* Wake Word
* Streaming Audio
* Voice Commands

---

# Learning Agent

Directory

```text
learning_agent/

agent.py

feedback.py

optimizer.py

trainer.py

metrics.py

patterns.py

evaluation.py
```

Responsibilities

* Learn from failures
* Learn from successes
* Improve workflows
* Rank tools
* Detect bottlenecks

Future

Self-improving workflows

Adaptive planning

---

# Verification Agent

Directory

```text
verification_agent/

agent.py

vision.py

desktop.py

browser.py

ocr.py

comparison.py

validator.py
```

Responsibilities

* Confirm actions completed
* Detect failures
* Trigger retries
* Compare expected vs actual state

Acts as the quality assurance layer for AetherOS.

---

# Agent Communication

Agents communicate only through the Coordinator.

```text
Vision Agent

↓

Coordinator

↓

Desktop Agent
```

Never

```text
Vision Agent

↓

Desktop Agent
```

This avoids tight coupling.

---

# Agent Context

Every agent receives:

```text
Task

↓

Memory Context

↓

Current State

↓

Available Tools

↓

Configuration

↓

Execution History
```

No agent should operate without context.

---

# Dependency Rules

Agents may depend on:

* Core
* Engines
* Memory
* LLM
* Event Bus

Agents must **not** depend on:

* Other Agents
* UI Components
* Dashboard
* Database Drivers
* Low-level Controllers

---

# Agent Design Standards

Each agent should contain:

```text
README.md

agent.py

config.py

models.py

exceptions.py

tests/

examples/
```

This keeps every agent modular and independently testable.

---

# Folder Dependency Diagram

```text
Core
 │
 ▼
Agents
 │
 ▼
Engines
 │
 ▼
Controllers
 │
 ▼
Operating System
```

Dependencies should only flow downward.

---

# Summary

The `agents/` directory is the intelligence layer of AetherOS. Each agent is responsible for a single domain, communicates through the Coordinator, delegates execution to Engines, and follows a common lifecycle and interface. This modular design enables parallel execution, independent testing, and easy replacement of individual agents without affecting the rest of the system.

---

## Next Part

**Part 4 — `engines/` Project Structure**

We'll cover every engine in detail:

* `vision/`
* `desktop/`
* `browser/`
* `llm/`
* `memory/`
* `trading/`
* `verification/`
* `execution/`
* `learning/`

including every file, pipeline, interfaces, dependencies, and internal architecture.
