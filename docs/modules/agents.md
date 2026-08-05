# AGENTS.md

# AetherOS Multi-Agent Architecture

> **Purpose**
>
> The **Agents** module is the intelligence layer of AetherOS. While the Runtime executes tasks and the Desktop/Browser modules interact with the operating system, the Agents decide **what should be done, how it should be done, when it should be done, and which tools should be used.**
>
> Every complex workflow inside AetherOS is executed by one or more specialized AI agents working together.

---

# Design Philosophy

The Agent System should be:

* Autonomous
* Modular
* Event-driven
* Goal-oriented
* Cooperative
* Verifiable
* Memory-aware
* Provider-independent
* Extensible
* Fault tolerant

---

# Responsibilities

The Agents module is responsible for:

* Goal understanding
* Task planning
* Tool selection
* Workflow execution
* Decision making
* Agent communication
* Memory utilization
* Verification
* Reflection
* Learning

The Agents module **does not** directly:

* Control the mouse
* Click buttons
* Perform OCR
* Capture the screen
* Access hardware

Those responsibilities belong to Runtime, Desktop, Vision, and Browser modules.

---

# Architecture Overview

```text
User Goal
    │
    ▼
CEO Agent
    │
    ▼
Planner Agent
    │
    ▼
Task Graph
    │
    ▼
Scheduler
    │
 ┌──┼───────────────┐
 ▼  ▼               ▼
Desktop Agent   Browser Agent   Memory Agent
 │      │               │
 └──────┼───────────────┘
        ▼
Verification Agent
        │
        ▼
Reflection Agent
        │
        ▼
Final Response
```

---

# Directory Structure

```text
agents/
│
├── __init__.py
│
├── base/
│
├── ceo/
│
├── planner/
│
├── executor/
│
├── verifier/
│
├── reflection/
│
├── decision/
│
├── communication/
│
├── router/
│
├── registry/
│
├── prompts/
│
├── workflows/
│
├── context/
│
├── state/
│
├── models/
│
├── tools/
│
├── events/
│
├── analytics/
│
└── learning/
```

---

# Agent Hierarchy

```text
CEO Agent
│
├── Planner Agent
│
├── Executor Agent
│
├── Decision Agent
│
├── Verification Agent
│
├── Reflection Agent
│
├── Memory Agent
│
├── Vision Agent
│
├── Browser Agent
│
├── Desktop Agent
│
├── Voice Agent
│
├── Trading Agent
│
├── Coding Agent
│
├── Research Agent
│
└── Communication Agent
```

---

# Base Agent

Folder

```text
agents/base/
```

Every agent inherits from:

```python
BaseAgent
```

Common methods

```python
initialize()

plan()

execute()

verify()

reflect()

shutdown()
```

Responsibilities

* Lifecycle
* Logging
* Memory access
* Event publishing
* Context loading

---

# CEO Agent

Folder

```text
agents/ceo/
```

Purpose

Acts as the executive controller of AetherOS.

Responsibilities

* Receive user goals
* Estimate complexity
* Allocate resources
* Select specialized agents
* Approve execution plans
* Monitor workflow progress

Example

```text
User:
Build a presentation.

↓

CEO

↓

Planner

↓

Executor
```

---

# Planner Agent

Folder

```text
agents/planner/
```

Responsibilities

* Break goals into tasks
* Build dependency graphs
* Estimate execution order
* Assign priorities
* Select tools

Example

```text
Create Presentation

↓

Research

↓

Collect Images

↓

Generate Slides

↓

Export PDF
```

---

# Executor Agent

Folder

```text
agents/executor/
```

Responsibilities

* Execute task graph
* Call Runtime
* Invoke tools
* Monitor execution
* Report progress

Pipeline

```text
Task

↓

Tool

↓

Runtime

↓

Result
```

---

# Decision Agent

Folder

```text
agents/decision/
```

Responsibilities

* Evaluate strategies
* Compare alternatives
* Select optimal path
* Estimate costs
* Predict success probability

Factors

* Time
* Resources
* Complexity
* Accuracy

---

# Verification Agent

Folder

```text
agents/verifier/
```

Responsibilities

* Verify execution
* Compare expected vs actual
* Detect failures
* Trigger retries

Verification methods

* OCR
* Vision
* DOM
* File system
* Process state

---

# Reflection Agent

Folder

```text
agents/reflection/
```

Responsibilities

* Analyze completed workflows
* Detect mistakes
* Suggest improvements
* Generate lessons learned

Pipeline

```text
Execution

↓

Review

↓

Improvement

↓

Memory
```

---

# Memory Agent

Responsibilities

* Retrieve memories
* Store results
* Rank memories
* Build execution context

Works with

* Session Memory
* Long-term Memory
* Vector Database
* Knowledge Graph

---

# Vision Agent

Responsibilities

* Understand screen
* Detect UI
* Locate objects
* Read text
* Build scene graph

Uses

* OCR
* YOLO
* OpenCV

---

# Browser Agent

Responsibilities

* Navigate websites
* Control Playwright
* Handle downloads
* Manage sessions
* Extract web data

---

# Desktop Agent

Responsibilities

* Mouse
* Keyboard
* Clipboard
* Windows
* Processes
* File system

Works through Desktop Runtime.

---

# Voice Agent

Responsibilities

* Speech recognition
* Voice synthesis
* Conversation management
* Wake word handling

---

# Trading Agent

Responsibilities

* Analyze charts
* Detect ICT structures
* Generate trade ideas
* Risk analysis
* Strategy generation

---

# Coding Agent

Responsibilities

* Generate code
* Debug
* Refactor
* Review
* Write tests
* Build projects

---

# Research Agent

Responsibilities

* Search documents
* Read papers
* Summarize information
* Compare sources
* Generate reports

---

# Communication Agent

Responsibilities

* Email
* Notifications
* Slack
* Discord
* Teams
* Reports

---

# Agent Communication

Folder

```text
agents/communication/
```

Agents never call each other directly.

Instead

```text
Planner

↓

Event Bus

↓

Executor

↓

Event Bus

↓

Verifier
```

Loose coupling.

---

# Context Manager

Folder

```text
agents/context/
```

Builds execution context.

Sources

* Memory
* User goal
* Vision
* Runtime state
* Current workflow

---

# Prompt Library

Folder

```text
agents/prompts/
```

Stores prompts for

* CEO
* Planner
* Reflection
* Verification
* Coding
* Trading

Supports

* Templates
* Variables
* Versioning

---

# Workflow Manager

Folder

```text
agents/workflows/
```

Stores reusable workflows.

Example

```text
Create Report

↓

Research

↓

Write

↓

Export

↓

Email
```

---

# Registry

Folder

```text
agents/registry/
```

Registers all available agents.

Example

```python
CEOAgent

PlannerAgent

TradingAgent

CodingAgent
```

Supports

* Discovery
* Registration
* Dynamic loading

---

# Agent State

Folder

```text
agents/state/
```

Tracks

* Running
* Waiting
* Paused
* Failed
* Completed

---

# Events

Folder

```text
agents/events/
```

Examples

```text
GoalReceived

PlanGenerated

TaskAssigned

TaskCompleted

VerificationPassed

ReflectionFinished
```

---

# Learning

Folder

```text
agents/learning/
```

Learns from

* Successful workflows
* User corrections
* Reflection reports
* Tool usage
* Failures

Output

Improved future planning.

---

# Analytics

Folder

```text
agents/analytics/
```

Measures

* Planning time
* Success rate
* Token usage
* Tool usage
* Retry rate
* Reflection quality

---

# Agent Lifecycle

```text
Initialize

↓

Load Context

↓

Retrieve Memory

↓

Reason

↓

Plan

↓

Execute

↓

Verify

↓

Reflect

↓

Store Memory

↓

Shutdown
```

---

# Technology Stack

| Component          | Technology                                              |
| ------------------ | ------------------------------------------------------- |
| LLM Interface      | Provider Abstraction (OpenAI, Ollama, OpenRouter, etc.) |
| Workflow Execution | asyncio                                                 |
| State Machine      | transitions                                             |
| Prompt Templates   | Jinja2                                                  |
| Structured Output  | Pydantic                                                |
| Event System       | asyncio Event Bus                                       |
| Memory Access      | ChromaDB + Memory Module                                |
| Logging            | Loguru                                                  |

---

# Design Principles

1. Every agent has a single responsibility.
2. Agents communicate only through the Event Bus.
3. Reasoning and execution are separated.
4. Every action must be verifiable.
5. Agents always use memory before reasoning.
6. Reflection happens after every completed workflow.
7. Agents are stateless between executions; persistent knowledge belongs in the Memory module.
8. New agents can be added without changing existing agents.

---

# Success Criteria

The Agents module is complete when:

* ✅ Goals are converted into executable plans.
* ✅ Specialized agents collaborate through events.
* ✅ Tool selection is autonomous.
* ✅ Workflows execute reliably.
* ✅ Results are verified automatically.
* ✅ Reflection improves future executions.
* ✅ Memory is integrated into planning.
* ✅ New agents can be plugged into the system with minimal changes.

The **Agents** module is the **brain** of AetherOS. It transforms high-level user goals into coordinated, intelligent actions by combining planning, reasoning, execution, verification, and continuous learning through a modular multi-agent architecture.
