# PLANNER.md

# AetherOS Planning & Task Orchestration Architecture

> **Purpose**
>
> The **Planner** module is responsible for transforming a high-level user goal into an optimized, executable workflow. It analyzes objectives, decomposes them into smaller tasks, determines dependencies, estimates resources, selects appropriate tools and agents, and produces a structured execution plan.
>
> The Planner is the **strategic brain** of AetherOS.

---

# Design Philosophy

The Planner should be:

* Goal-driven
* Deterministic
* Explainable
* Modular
* Adaptive
* Memory-aware
* Resource-aware
* Fault tolerant
* Extensible
* Provider-independent

---

# Responsibilities

The Planner module is responsible for:

* Goal analysis
* Task decomposition
* Dependency analysis
* Workflow generation
* Tool selection
* Agent assignment
* Priority estimation
* Resource estimation
* Risk assessment
* Execution planning
* Re-planning after failures

The Planner **does not**:

* Execute tools
* Control hardware
* Perform OCR
* Store long-term memory
* Verify execution

Those responsibilities belong to Runtime, Desktop, Vision, Memory, and Verification.

---

# Architecture

```text
User Goal

↓

Goal Analyzer

↓

Task Decomposer

↓

Dependency Graph

↓

Tool Selector

↓

Agent Selector

↓

Execution Planner

↓

Workflow Graph

↓

Runtime
```

---

# Directory Structure

```text
planner/
│
├── __init__.py
│
├── api/
│
├── analyzer/
│
├── decomposition/
│
├── dependencies/
│
├── workflows/
│
├── graph/
│
├── scheduler/
│
├── tools/
│
├── agents/
│
├── priorities/
│
├── estimation/
│
├── optimizer/
│
├── recovery/
│
├── templates/
│
├── validation/
│
├── events/
│
├── models/
│
├── analytics/
│
├── utils/
│
└── tests/
```

---

# Goal Analyzer

Folder

```text
planner/analyzer/
```

Responsibilities

* Understand user intent
* Detect objectives
* Extract constraints
* Identify required outputs
* Estimate complexity

Example

```
User

↓

"Analyze BTC chart and email report."

↓

Objectives

• Open TradingView
• Analyze chart
• Generate report
• Send email
```

---

# Task Decomposer

Folder

```text
planner/decomposition/
```

Purpose

Break one large goal into atomic tasks.

Example

```
Create Presentation

↓

Research

↓

Collect Images

↓

Generate Slides

↓

Review Slides

↓

Export PDF
```

Each task should be independently executable.

---

# Dependency Engine

Folder

```text
planner/dependencies/
```

Determines

* Parent tasks
* Child tasks
* Blocking tasks
* Parallel tasks

Example

```
Open Browser

↓

Login

↓

Dashboard

↓

Download Report
```

Login cannot happen before Browser opens.

---

# Workflow Generator

Folder

```text
planner/workflows/
```

Creates reusable workflow definitions.

Example

```
Open Gmail

↓

Compose Mail

↓

Attach File

↓

Send

↓

Verify
```

Workflow outputs

* DAG
* JSON
* YAML

---

# Task Graph

Folder

```text
planner/graph/
```

Represents workflows as Directed Acyclic Graphs (DAG).

Example

```
        Research
         /     \
Collect Data  Find Images
        \     /
      Write Report
            |
        Export PDF
```

Benefits

* Parallel execution
* Dependency tracking
* Retry management

---

# Scheduler

Folder

```text
planner/scheduler/
```

Responsibilities

* Task ordering
* Parallel execution
* Queue management
* Retry scheduling
* Timeout handling

Scheduling Factors

* Priority
* Dependencies
* Available agents
* Available tools

---

# Tool Selector

Folder

```text
planner/tools/
```

Purpose

Choose the best tool for each task.

Example

```
Find Text

↓

Vision API

---------------

Open Browser

↓

Browser API

---------------

Move Mouse

↓

Desktop API
```

---

# Agent Selector

Folder

```text
planner/agents/
```

Responsibilities

Assign specialized agents.

Example

```
Coding Task

↓

Coding Agent

---------------

Research Task

↓

Research Agent

---------------

Trading Task

↓

Trading Agent
```

---

# Priority Manager

Folder

```text
planner/priorities/
```

Priority Levels

```
Critical

High

Normal

Low

Background
```

Factors

* User urgency
* Dependencies
* Risk
* Estimated duration

---

# Estimation Engine

Folder

```text
planner/estimation/
```

Estimates

* Execution time
* API usage
* Token usage
* CPU usage
* GPU usage
* Memory usage

Output

```
Estimated Time

↓

2 minutes

Estimated Cost

↓

$0.01

Estimated Tokens

↓

4,500
```

---

# Optimization Engine

Folder

```text
planner/optimizer/
```

Optimizes

* Parallel execution
* Tool selection
* Agent allocation
* Workflow ordering
* Resource usage

Goal

Fastest reliable execution.

---

# Recovery Planner

Folder

```text
planner/recovery/
```

Handles failures.

Strategies

* Retry
* Alternative tool
* Alternative agent
* Skip optional task
* Ask user
* Abort workflow

Example

```
Browser Failed

↓

Retry

↓

Still Failed

↓

Use Desktop Automation
```

---

# Workflow Templates

Folder

```text
planner/templates/
```

Reusable plans.

Examples

* Generate Report
* Send Email
* Build Project
* Trading Analysis
* Research Topic
* Create Presentation

---

# Validation

Folder

```text
planner/validation/
```

Verifies

* No circular dependencies
* Valid tools
* Available agents
* Reachable workflow
* Complete execution graph

---

# Planner API

Folder

```text
planner/api/
```

Functions

```python
plan()

optimize()

schedule()

replan()

validate()

estimate()
```

All higher-level modules use this API.

---

# Events

Folder

```text
planner/events/
```

Events

```
GoalReceived

PlanCreated

TaskScheduled

WorkflowOptimized

PlanUpdated

PlanCompleted
```

---

# Models

Folder

```text
planner/models/
```

Contains

* Goal
* Task
* Workflow
* Dependency
* ExecutionPlan
* ResourceEstimate

---

# Analytics

Folder

```text
planner/analytics/
```

Tracks

* Planning latency
* Task count
* Workflow complexity
* Retry frequency
* Optimization efficiency
* Resource prediction accuracy

---

# Utilities

Folder

```text
planner/utils/
```

Provides

* Graph utilities
* Dependency helpers
* Cost estimation
* Time estimation
* Workflow visualization

---

# Planning Execution Flow

```text
User Goal

↓

Goal Analysis

↓

Memory Retrieval

↓

Task Decomposition

↓

Dependency Graph

↓

Tool Selection

↓

Agent Assignment

↓

Optimization

↓

Execution Plan

↓

Runtime
```

---

# Technology Stack

| Component         | Technology                 |
| ----------------- | -------------------------- |
| Workflow Graph    | NetworkX                   |
| Structured Models | Pydantic                   |
| Prompt Templates  | Jinja2                     |
| Async Scheduling  | asyncio                    |
| Graph Algorithms  | Python graphlib / NetworkX |
| Validation        | Pydantic                   |
| Serialization     | JSON / YAML                |
| Logging           | Loguru                     |

---

# Design Principles

1. Plans should be deterministic whenever possible.
2. Break every goal into atomic tasks.
3. Prefer parallel execution when dependencies allow.
4. Every task must have an assigned tool and agent.
5. Plans must be validated before execution.
6. Always estimate resources before starting.
7. Support dynamic re-planning during execution.
8. Keep planning independent from execution.

---

# Success Criteria

The Planner module is complete when:

* ✅ User goals are converted into executable workflows.
* ✅ Tasks are decomposed into atomic operations.
* ✅ Dependencies are represented as a DAG.
* ✅ Appropriate tools and agents are assigned automatically.
* ✅ Workflows are optimized for speed and reliability.
* ✅ Resource and time estimates are generated.
* ✅ Failures trigger automatic re-planning.
* ✅ Plans are validated before execution.
* ✅ A single Planner API is used by the Runtime and Agents.

The **Planner** module is the **strategic coordinator** of AetherOS. It bridges high-level intent and low-level execution by producing optimized, verifiable execution plans that allow autonomous agents to work together efficiently and reliably.
