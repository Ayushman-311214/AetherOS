# 02_ARCHITECTURE.md

# Part 2 — Core Architecture

> **Purpose**
>
> The **Core** is the brain of AetherOS.
>
> Every user request, every AI decision, every workflow, and every agent communication passes through the Core.
>
> The Core never directly controls the mouse, keyboard, browser, or vision engine. Instead, it coordinates specialized modules.

---

# Table of Contents

1. Core Philosophy
2. Core Components
3. Orchestrator
4. Planner
5. Scheduler
6. Workflow Engine
7. Event Bus
8. Message Bus
9. Task Queue
10. State Manager
11. Coordinator
12. Execution Lifecycle
13. Folder Structure

---

# 1. Core Philosophy

The Core exists to answer one question:

> **"Given the current goal and system state, what should happen next?"**

It does **not**:

* Move the mouse
* Click buttons
* Run OCR
* Execute browser actions

Instead, it decides:

* What should happen
* Which agent should do it
* In what order
* When to retry
* When to stop
* When to learn

---

# Core Responsibilities

The Core owns:

* Goal Management
* Planning
* Workflow Execution
* Scheduling
* Agent Coordination
* Event Routing
* State Management
* Retry Logic
* Failure Recovery

---

# 2. Core Components

```text
core/
│
├── orchestrator/
│
├── planner/
│
├── coordinator/
│
├── scheduler/
│
├── workflow/
│
├── event_bus/
│
├── message_bus/
│
├── task_queue/
│
├── reasoning/
│
├── state_manager/
│
├── retry/
│
├── execution/
│
└── utils/
```

Every folder owns one responsibility.

---

# 3. Orchestrator

## Purpose

The Orchestrator is the **central controller** of AetherOS.

Nothing executes without the Orchestrator.

Think of it as the operating system kernel.

---

## Responsibilities

Receive goals

↓

Collect context

↓

Retrieve memory

↓

Ask planner

↓

Create workflow

↓

Assign tasks

↓

Monitor execution

↓

Handle failures

↓

Finish workflow

---

## Example

User:

> Analyze Bitcoin and email today's report.

The Orchestrator performs:

```text
Receive Goal

↓

Planner

↓

Research Agent

↓

Trading Agent

↓

Report Generator

↓

Email Agent

↓

Verification

↓

Memory Update

↓

Complete
```

---

## Internal Files

```text
orchestrator/

controller.py

manager.py

dispatcher.py

context.py

validator.py

executor.py
```

### controller.py

Entry point.

Receives new workflows.

---

### manager.py

Manages active workflows.

Tracks

* status
* progress
* retries
* completion

---

### dispatcher.py

Chooses which agent receives a task.

---

### context.py

Builds execution context.

Collects

Memory

Current Screen

Running Apps

Open Files

Settings

User Preferences

---

### validator.py

Checks workflow integrity before execution.

---

### executor.py

Starts execution.

Monitors completion.

---

# 4. Planner

## Purpose

Planner converts goals into executable tasks.

Example

Goal

↓

"Open Chrome and search GPT-5"

Planner outputs

```text
Open Chrome

↓

Wait for Window

↓

Focus Search Box

↓

Type Query

↓

Press Enter

↓

Verify
```

---

Planner never executes anything.

It only creates plans.

---

## Planning Pipeline

```text
Goal

↓

Understand

↓

Break Into Tasks

↓

Estimate Dependencies

↓

Order Tasks

↓

Output Task Graph
```

---

## Files

```text
planner/

planner.py

goal_parser.py

task_graph.py

dependency.py

optimizer.py

validator.py
```

---

### planner.py

Main planner.

---

### goal_parser.py

Natural language

↓

Structured goal

---

### task_graph.py

Builds DAG.

Example

```text
Launch Browser

↓

Search

↓

Read Page

↓

Summarize
```

---

### dependency.py

Determines

Task A

must finish before

Task B.

---

### optimizer.py

Removes unnecessary steps.

Combines tasks.

Improves efficiency.

---

# 5. Scheduler

The Scheduler decides

**when**

a task should execute.

Not

**what**

to execute.

---

Examples

Run every minute.

Run tomorrow.

Wait until browser loads.

Wait for user.

Retry after 5 seconds.

---

Scheduler Types

Immediate

Delayed

Periodic

Conditional

Background

---

Files

```text
scheduler/

scheduler.py

timer.py

cron.py

retry.py

conditions.py
```

---

# 6. Workflow Engine

Workflow Engine executes plans.

Example

Planner

↓

Workflow

↓

Task Graph

↓

Execution

---

Workflow Example

```text
Capture Screen

↓

OCR

↓

Find Button

↓

Move Mouse

↓

Click

↓

Verify
```

---

Workflow Features

Nested workflows

Subtasks

Rollback

Resume

Checkpoint

Cancellation

Timeout

Retry

---

Files

```text
workflow/

workflow.py

executor.py

builder.py

steps.py

rollback.py

checkpoint.py
```

---

# 7. Event Bus

Everything important generates an event.

Examples

```text
GoalReceived

WindowOpened

OCRCompleted

MouseMoved

WorkflowStarted

WorkflowFinished

ErrorOccurred

MemoryUpdated
```

---

Event Flow

```text
Vision

↓

Event Bus

↓

Planner

↓

Verification
```

---

Benefits

Loose coupling

Parallel execution

Logging

Replay

Monitoring

---

Files

```text
event_bus/

bus.py

publisher.py

subscriber.py

events.py

handlers.py
```

---

Example Event

```json
{
  "id":"event_1001",
  "type":"OCRCompleted",
  "timestamp":"...",
  "workflow":"wf_01",
  "payload":{
      "text":"TradingView"
  }
}
```

---

# 8. Message Bus

Difference

Event Bus

Broadcast.

Anyone may listen.

---

Message Bus

Direct communication.

Agent A

↓

Agent B

---

Example

Planner

↓

Desktop Agent

↓

Move Mouse

---

Files

```text
message_bus/

router.py

channels.py

messages.py

serializer.py
```

---

# Event Bus vs Message Bus

| Event Bus            | Message Bus  |
| -------------------- | ------------ |
| Broadcast            | Direct       |
| Multiple subscribers | One receiver |
| Async                | Async/Sync   |
| Notifications        | Commands     |

---

# 9. Task Queue

Tasks waiting for execution.

Example

```text
Queue

↓

Capture Screen

↓

OCR

↓

Locate Button

↓

Click

↓

Verify
```

---

Priority Queue

High

Normal

Background

---

Task States

Pending

Running

Waiting

Completed

Failed

Cancelled

Retrying

---

Files

```text
task_queue/

queue.py

priority.py

worker.py

task.py
```

---

# 10. State Manager

Stores the current state of AetherOS.

Example

Current Goal

Current Window

Mouse Position

Clipboard

Running Agents

Memory Context

Open Browser Tabs

System Resources

---

State Types

Global

Workflow

Agent

Application

Session

---

Files

```text
state_manager/

state.py

store.py

context.py

snapshot.py

restore.py
```

---

Snapshot Example

```text
Workflow 18

↓

Browser Open

↓

Tab 3

↓

Cursor

↓

Clipboard

↓

Memory

↓

Agent Status
```

Useful for crash recovery.

---

# 11. Coordinator

The Coordinator manages multiple agents.

Example

Planner

↓

Coordinator

↓

Vision

↓

Desktop

↓

Browser

↓

Trading

↓

Research

↓

Memory

---

Coordinator Responsibilities

Assign work

Monitor progress

Handle dependencies

Prevent conflicts

Synchronize agents

Merge results

---

Files

```text
coordinator/

coordinator.py

routing.py

registry.py

locks.py

monitor.py
```

---

# Example

Research Agent

↓

returns market news

Vision Agent

↓

returns chart

Trading Agent

↓

creates analysis

Coordinator

↓

combines outputs

↓

Planner

---

# 12. Execution Lifecycle

Every workflow follows this sequence.

```text
Receive Goal

↓

Context Collection

↓

Memory Retrieval

↓

Planning

↓

Workflow Creation

↓

Scheduling

↓

Task Queue

↓

Coordinator

↓

Agent

↓

Engine

↓

Tool

↓

Verification

↓

Learning

↓

Memory Update

↓

Completed
```

---

# Failure Recovery

If a step fails:

```text
Failure

↓

Retry

↓

Alternative Plan

↓

Different Agent

↓

Human Confirmation (optional)

↓

Abort
```

Recovery is handled by the Core, not by individual agents.

---

# 13. Folder Structure

```text
core/
│
├── orchestrator/
│   ├── controller.py
│   ├── manager.py
│   ├── dispatcher.py
│   ├── context.py
│   ├── validator.py
│   └── executor.py
│
├── planner/
│   ├── planner.py
│   ├── goal_parser.py
│   ├── task_graph.py
│   ├── dependency.py
│   ├── optimizer.py
│   └── validator.py
│
├── scheduler/
│   ├── scheduler.py
│   ├── timer.py
│   ├── cron.py
│   ├── retry.py
│   └── conditions.py
│
├── workflow/
│   ├── workflow.py
│   ├── executor.py
│   ├── builder.py
│   ├── rollback.py
│   ├── checkpoint.py
│   └── steps.py
│
├── coordinator/
│
├── event_bus/
│
├── message_bus/
│
├── task_queue/
│
├── state_manager/
│
├── reasoning/
│
├── retry/
│
└── execution/
```

---

# Summary

The Core is the **operating intelligence** of AetherOS.

It never performs low-level actions itself. Instead, it:

* Understands goals
* Plans execution
* Coordinates agents
* Tracks workflows
* Routes events
* Manages state
* Handles retries
* Ensures successful completion

All other subsystems—Vision, Desktop, Browser, Memory, Trading, and Learning—operate under the direction of the Core.

---

**Next:** **Part 3 — AI Agents Architecture**, covering every agent (CEO, Planner, Vision, Desktop, Browser, Memory, Research, Coding, Trading, Voice, Learning), their responsibilities, internal folder structures, communication protocols, and collaboration patterns.
