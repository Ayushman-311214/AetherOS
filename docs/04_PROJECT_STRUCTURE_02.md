# 04_PROJECT_STRUCTURE.md

# Part 2 — Core Project Structure

> **Purpose**
>
> The `core/` directory is the heart of AetherOS. It contains the orchestration, planning, scheduling, coordination, workflow execution, reasoning, and state management logic.
>
> **Rule:** Nothing inside `core/` directly controls the mouse, keyboard, browser, OCR, or external APIs. It coordinates other modules.

---

# Directory Structure

```text
core/
│
├── orchestrator/
├── planner/
├── coordinator/
├── scheduler/
├── workflow/
├── reasoning/
├── event_bus/
├── message_bus/
├── task_queue/
├── state_manager/
├── execution/
├── retry/
├── interfaces/
├── exceptions/
├── models/
├── utils/
│
├── __init__.py
└── constants.py
```

---

# Core Principles

The Core is responsible for:

- Understanding goals
- Building execution plans
- Managing workflows
- Coordinating agents
- Tracking execution
- Recovering from failures
- Updating system state

The Core **never**:

- Runs OCR
- Clicks the mouse
- Opens browsers
- Calls Playwright directly
- Calls PyAutoGUI directly

---

# Execution Flow

```text
User Goal
      │
      ▼
Orchestrator
      │
      ▼
Planner
      │
      ▼
Workflow Builder
      │
      ▼
Scheduler
      │
      ▼
Coordinator
      │
      ▼
Agents
      │
      ▼
Engines
      │
      ▼
Verification
      │
      ▼
Memory Update
```

---

# 1. orchestrator/

## Purpose

The Orchestrator is the central controller of AetherOS.

Every user request begins here.

---

## Folder Structure

```text
orchestrator/
│
├── controller.py
├── manager.py
├── dispatcher.py
├── context.py
├── validator.py
├── executor.py
├── lifecycle.py
└── metrics.py
```

---

### controller.py

The main entry point.

Responsibilities:

- Receive new goals
- Start workflows
- Stop workflows
- Pause workflows
- Resume workflows

Should expose methods like:

```python
start(goal)

pause(workflow_id)

resume(workflow_id)

cancel(workflow_id)
```

---

### manager.py

Tracks all active workflows.

Stores:

- Status
- Owner
- Priority
- Progress
- Execution Time
- Retry Count

Think of this as the operating system's process manager.

---

### dispatcher.py

Responsible for task routing.

Example:

```text
Need OCR

↓

Vision Agent
```

```text
Need Mouse

↓

Desktop Agent
```

Never hardcode agent logic elsewhere.

---

### context.py

Builds execution context.

Collects:

- Memory
- Current Screen
- Active Window
- Clipboard
- User Preferences
- Running Applications
- Current Workflow

Everything required for reasoning.

---

### validator.py

Checks that workflows are valid before execution.

Example:

- Missing dependencies
- Circular tasks
- Invalid priorities

---

### executor.py

Starts execution.

Monitors completion.

Returns structured results.

---

### lifecycle.py

Manages workflow lifecycle.

States:

```text
Created

↓

Planning

↓

Running

↓

Paused

↓

Completed

↓

Failed
```

---

### metrics.py

Collects:

- Execution Time
- Success Rate
- Retry Count
- Agent Usage
- Failure Statistics

---

# 2. planner/

## Purpose

Convert goals into executable task graphs.

---

## Folder

```text
planner/
│
├── planner.py
├── goal_parser.py
├── task_graph.py
├── dependency.py
├── optimizer.py
├── validator.py
├── estimator.py
└── templates.py
```

---

### planner.py

Main planning engine.

Input:

```text
Analyze BTC Market
```

Output:

```text
Open Browser

↓

TradingView

↓

Capture Chart

↓

Analyze

↓

Generate Report
```

---

### goal_parser.py

Natural language

↓

Structured Goal Object

Example:

```json
{
  "goal": "Analyze BTC",
  "priority": "high",
  "deadline": null
}
```

---

### task_graph.py

Creates Directed Acyclic Graph (DAG).

Example

```text
Launch Browser

↓

Open TradingView

↓

Analyze

↓

Generate Report
```

---

### dependency.py

Finds task dependencies.

Example:

Cannot capture screenshot before browser opens.

---

### optimizer.py

Improves workflow.

Removes unnecessary steps.

Combines similar actions.

Chooses fastest execution.

---

### validator.py

Ensures:

- No circular dependencies
- Valid task order
- Reachable end state

---

### estimator.py

Estimates:

- Execution Time
- Resource Usage
- Token Cost
- Tool Usage

---

### templates.py

Stores reusable workflows.

Example:

- Open Website
- Login
- Download File
- Create Report

---

# 3. coordinator/

## Purpose

Coordinates all AI agents.

---

Structure

```text
coordinator/
│
├── coordinator.py
├── registry.py
├── routing.py
├── monitor.py
├── locks.py
├── priority.py
└── load_balancer.py
```

---

### coordinator.py

Central communication hub.

Responsibilities:

- Assign tasks
- Collect results
- Resolve conflicts

---

### registry.py

Keeps track of available agents.

Example:

```python
VisionAgent

DesktopAgent

BrowserAgent

MemoryAgent
```

---

### routing.py

Decides which agent receives which task.

---

### monitor.py

Tracks:

- Running Agents
- Busy Agents
- Failed Agents

---

### locks.py

Prevents two agents from controlling the same resource simultaneously.

Example:

Two agents cannot move the mouse at once.

---

### priority.py

Handles task priority.

Levels:

- Critical
- High
- Normal
- Background

---

### load_balancer.py

Future cloud feature.

Distributes work across multiple AI workers.

---

# 4. scheduler/

## Purpose

Decides **when** tasks execute.

---

Folder

```text
scheduler/
│
├── scheduler.py
├── timer.py
├── cron.py
├── retry.py
├── timeout.py
└── conditions.py
```

---

Supports:

- Immediate
- Delayed
- Scheduled
- Conditional
- Repeating tasks

---

# 5. workflow/

## Purpose

Executes task graphs.

---

Folder

```text
workflow/
│
├── workflow.py
├── builder.py
├── executor.py
├── checkpoint.py
├── rollback.py
├── state.py
└── history.py
```

---

Supports:

- Nested workflows
- Resume
- Rollback
- Pause
- Retry
- Cancellation

---

# 6. reasoning/

## Purpose

Decision making.

This folder is intentionally isolated so reasoning strategies can evolve independently.

---

Folder

```text
reasoning/
│
├── engine.py
├── planner.py
├── reflection.py
├── evaluator.py
├── critic.py
├── confidence.py
├── strategy.py
└── context.py
```

---

Responsibilities:

- Tool selection
- Plan evaluation
- Reflection
- Confidence scoring
- Alternative generation

---

# 7. event_bus/

## Purpose

Broadcast events across the system.

---

Folder

```text
event_bus/
│
├── bus.py
├── publisher.py
├── subscriber.py
├── handlers.py
├── events.py
└── logger.py
```

---

Example events:

- WorkflowStarted
- OCRCompleted
- WindowOpened
- TaskFailed

---

# 8. message_bus/

## Purpose

Direct communication between components.

---

Folder

```text
message_bus/
│
├── router.py
├── messages.py
├── channels.py
├── serializer.py
└── protocol.py
```

Unlike the Event Bus, messages have one intended recipient.

---

# 9. task_queue/

## Purpose

Stores tasks waiting for execution.

---

Folder

```text
task_queue/
│
├── queue.py
├── worker.py
├── priority.py
├── retry.py
├── task.py
└── monitor.py
```

Supports:

- FIFO
- Priority Queue
- Retry Queue
- Delayed Queue

---

# 10. state_manager/

## Purpose

Maintains the current state of the entire system.

---

Folder

```text
state_manager/
│
├── state.py
├── store.py
├── snapshot.py
├── restore.py
├── context.py
└── cache.py
```

Tracks:

- Current Workflow
- Active Window
- Running Agents
- Session Data
- Resource Usage

---

# 11. execution/

## Purpose

Responsible for reliable execution management.

---

Folder

```text
execution/
│
├── executor.py
├── history.py
├── retry.py
├── metrics.py
├── timeout.py
└── rollback.py
```

Responsibilities:

- Retry failed actions
- Record execution history
- Handle timeouts
- Roll back workflows

---

# 12. retry/

## Purpose

Centralized retry strategies.

---

Folder

```text
retry/
│
├── strategy.py
├── exponential.py
├── fixed.py
├── adaptive.py
└── policies.py
```

Retry strategies:

- Fixed Delay
- Exponential Backoff
- Adaptive Retry
- Immediate Retry

---

# 13. interfaces/

## Purpose

Defines contracts used throughout the Core.

Example:

```python
class PlannerInterface:
    def create_plan(self, goal):
        ...
```

Using interfaces allows components to be replaced without changing the rest of the system.

---

# 14. exceptions/

Contains custom exceptions only.

Examples:

```text
PlanningError

WorkflowError

SchedulingError

DependencyError

RetryLimitExceeded
```

---

# 15. models/

Contains shared data models.

Examples:

- Workflow
- Task
- Goal
- Event
- ExecutionResult
- Context

Prefer Pydantic models for validation and serialization.

---

# 16. utils/

Contains small helper functions that are generic to the Core.

Examples:

- UUID generation
- Time utilities
- Serialization helpers
- Formatting
- Common validators

Business logic should **not** be placed here.

---

# constants.py

Stores shared constants such as:

```python
MAX_RETRIES = 3

DEFAULT_TIMEOUT = 30

MAX_WORKFLOW_DEPTH = 10
```

Avoid magic numbers throughout the Core.

---

# Core Dependency Rules

```text
Core
 │
 ├── Agents
 ├── Memory
 ├── LLM
 └── Event Bus

Core

✗ Desktop API

✗ OCR Library

✗ Playwright

✗ PyAutoGUI
```

The Core should coordinate capabilities, not implement them.

---

# Summary

The `core/` directory is the command center of AetherOS. It transforms user goals into structured workflows, coordinates specialized agents, manages execution, tracks state, and ensures reliable operation through retries, scheduling, and event-driven communication—all while remaining independent of low-level implementation details.

---

## Next Part

**Part 3 — `agents/` Project Structure**

We'll document every agent directory in depth, including:

- `base_agent.py`
- `registry.py`
- CEO Agent
- Planner Agent
- Vision Agent
- Desktop Agent
- Browser Agent
- Research Agent
- Memory Agent
- Coding Agent
- Trading Agent
- Voice Agent
- Learning Agent

Each folder will include recommended files, responsibilities, interfaces, lifecycle, and design rules.
