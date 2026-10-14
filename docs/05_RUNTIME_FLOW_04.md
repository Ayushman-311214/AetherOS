# 05_RUNTIME_FLOW.md

# Part 4 — Tool Calling & Engine Routing Architecture

> **Purpose**
>
> The Tool Calling System is the bridge between **AI reasoning** and **real-world execution**.
>
> Agents never interact directly with controllers or operating system APIs. Instead, they invoke standardized tools through the Tool Calling Framework, which validates requests, routes them to the correct engine, executes them safely, verifies results, and returns structured responses.
>
> This architecture makes AetherOS modular, extensible, secure, and provider-independent.

---

# Complete Tool Calling Architecture

```text
                      Agent
                        │
                        ▼
                 Tool Call Request
                        │
                        ▼
                 Tool Middleware
                        │
                        ▼
                 Argument Validator
                        │
                        ▼
                  Permission Check
                        │
                        ▼
                  Tool Registry
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
 Desktop Engine   Browser Engine   Vision Engine
        │               │               │
        ▼               ▼               ▼
   Controllers      Controllers     Controllers
        │               │               │
        ▼               ▼               ▼
               Operating System
                        │
                        ▼
                 Verification Layer
                        │
                        ▼
                Structured Response
                        │
                        ▼
                     Executor
```

---

# Tool Philosophy

A tool should:

* Perform one responsibility
* Be deterministic
* Return structured output
* Validate inputs
* Never perform reasoning
* Never access memory directly
* Never plan workflows

---

# Tool Execution Lifecycle

```text
Agent

↓

Tool Request

↓

Validation

↓

Permission Check

↓

Registry Lookup

↓

Engine Routing

↓

Controller

↓

Verification

↓

Result

↓

Agent
```

---

# Tool Categories

```text
Desktop Tools

Browser Tools

Vision Tools

Memory Tools

System Tools

Trading Tools

Coding Tools

Communication Tools

Plugin Tools
```

---

# Tool Call Object

Every tool request follows one schema.

```json
{
    "tool": "move_mouse",
    "arguments": {
        "x": 420,
        "y": 310
    },
    "timeout": 10,
    "verify": true,
    "priority": 1
}
```

---

# Tool Registry

Purpose

Central registry of every executable capability.

Structure

```text
Tool Name

↓

Metadata

↓

Engine

↓

Controller

↓

Schema

↓

Permission
```

Example

```python
TOOL_REGISTRY = {

    "move_mouse": MouseController.move,

    "click": MouseController.click,

    "capture_screen": Vision.capture,

    "open_browser": Browser.launch
}
```

---

# Registry Responsibilities

* Register tools
* Discover tools
* Validate uniqueness
* Resolve names
* Load plugins
* Version tracking

---

# Tool Metadata

Every tool contains metadata.

Example

```python
Tool(

    name="move_mouse",

    category="desktop",

    version="1.0",

    engine="desktop",

    requires_verification=True,

    permissions=["desktop.control"]
)
```

---

# Dynamic Tool Discovery

At startup

```text
Project

↓

Scan tool folders

↓

Import modules

↓

Register decorators

↓

Build registry
```

Example

```python
@tool
def click():

    ...
```

Registration happens automatically.

---

# Tool Namespaces

```text
desktop.mouse.move

desktop.keyboard.type

browser.open

browser.click

vision.capture

vision.ocr

memory.search

memory.store

system.shutdown
```

Namespaces prevent conflicts.

---

# Tool Middleware

Every request passes through middleware.

```text
Tool Request

↓

Logging

↓

Validation

↓

Permission

↓

Metrics

↓

Dispatch
```

Middleware can modify execution.

---

# Argument Validation

Arguments are validated before execution.

Example

```json
{
    "x": 500,
    "y": 300
}
```

Validation

* Required fields
* Type checking
* Range checking
* Enum validation
* Custom rules

---

# Schema Definition

Example

```python
MoveMouseSchema

x : int

y : int

duration : float
```

Uses

* Pydantic

or

* Dataclasses

---

# Permission System

Some tools require permissions.

Example

```text
Desktop Control

Clipboard

Microphone

Camera

Filesystem

Browser

Network
```

Unauthorized tools never execute.

---

# Engine Routing

Registry returns engine.

Example

```text
move_mouse

↓

Desktop Engine

------------------

take_screenshot

↓

Vision Engine

------------------

goto_url

↓

Browser Engine
```

---

# Engine Dispatcher

Purpose

Dispatch tools to engines.

```text
Registry

↓

Dispatcher

↓

Correct Engine

↓

Controller
```

Dispatcher never executes business logic.

---

# Controller Resolution

Example

```text
desktop.mouse.move

↓

Desktop Engine

↓

Mouse Controller

↓

PyAutoGUI

↓

Windows API
```

Controllers remain hidden from agents.

---

# Tool Chaining

Some workflows require multiple tools.

Example

```text
Open Browser

↓

Open URL

↓

Wait Page

↓

Screenshot

↓

OCR
```

Planner creates chains.

Individual tools remain atomic.

---

# Tool Response

Every tool returns the same structure.

```json
{
    "success": true,
    "output": {},
    "duration": 0.15,
    "verification": true,
    "error": null
}
```

Never return free-form strings.

---

# Verification Hook

After execution

```text
Tool

↓

Verification Strategy

↓

Verified?

↓

Yes

↓

Return

No

↓

Retry
```

Verification strategies are tool-specific.

---

# Tool Versioning

Every tool has a version.

Example

```text
move_mouse

v1.0

v1.1

v2.0
```

Allows backward compatibility.

---

# Plugin Tools

External plugins may register tools.

```text
Plugin

↓

Discovery

↓

Validation

↓

Registry

↓

Available
```

Plugins cannot override system tools.

---

# Tool Security

Protected tools

```text
Shutdown PC

Delete File

Registry Edit

Task Manager

PowerShell

Network Settings
```

Require

* Elevated permission
* User confirmation
* Policy approval

---

# Tool Timeout

Each tool has a timeout.

Example

```yaml
move_mouse: 5s

ocr: 15s

browser_load: 60s

download: 300s
```

Timeout triggers cancellation.

---

# Tool Retry

Retries depend on tool type.

```text
Click Failed

↓

Retry

↓

Alternative Method

↓

Verification

↓

Success
```

---

# Tool Metrics

Collected automatically.

* Duration
* Success Rate
* Retry Count
* Failure Count
* CPU
* RAM
* GPU
* Latency

---

# Tool Logging

Example

```text
10:15:12

Tool Selected

move_mouse

10:15:12

Arguments Validated

10:15:13

Executed

10:15:13

Verification Passed

10:15:13

Completed
```

---

# Tool Cache

Some tools cache results.

Example

```text
OCR

↓

Same Screenshot

↓

Reuse Previous Result
```

Reduces unnecessary computation.

---

# Tool Failure Types

| Error               | Action           |
| ------------------- | ---------------- |
| Invalid Arguments   | Abort            |
| Permission Denied   | Escalate         |
| Tool Missing        | Planner Re-plan  |
| Verification Failed | Retry            |
| Timeout             | Retry            |
| Engine Offline      | Switch Engine    |
| Controller Failure  | Alternative Tool |

---

# Multi-Provider Tool Calling

Different LLMs support different tool APIs.

```text
GPT

↓

OpenAI Tool Schema

-------------------

Claude

↓

Anthropic Tool Schema

-------------------

Gemini

↓

Google Function Calling

-------------------

Ollama

↓

Native Tool API
```

AetherOS converts them into **one internal format**.

---

# Internal Tool Schema

Regardless of provider

```json
{
    "tool": "...",
    "arguments": {},
    "metadata": {}
}
```

The rest of the system never depends on provider-specific formats.

---

# Complete Routing Flow

```text
Planner Agent
      │
      ▼
Executor
      │
      ▼
Tool Registry
      │
      ▼
Validation
      │
      ▼
Permission
      │
      ▼
Dispatcher
      │
      ▼
Engine
      │
      ▼
Controller
      │
      ▼
Operating System
      │
      ▼
Verification
      │
      ▼
Structured Result
      │
      ▼
Executor
```

---

# Dependency Rules

The Tool System may depend on

* Engines
* Schemas
* Validators
* Controllers
* Permission Manager
* Logging

The Tool System must **not** depend directly on

* LLM Providers
* Planner Logic
* Memory Storage
* Vision Models
* Business Logic

All execution happens through interfaces.

---

# Runtime Guarantees

Every tool guarantees:

* Atomic execution
* Input validation
* Permission enforcement
* Engine abstraction
* Controller isolation
* Structured responses
* Verification
* Logging
* Metrics
* Retry support
* Version compatibility

---

# Future Enhancements

Planned improvements include:

* Dynamic tool loading at runtime
* Remote tool execution
* Distributed tool workers
* Sandboxed plugin tools
* Tool dependency graphs
* AI-generated tool schemas
* Automatic capability discovery
* Tool health monitoring
* Cross-device tool execution
* Marketplace-based tool installation

---

# Summary

The Tool Calling & Engine Routing Architecture forms the execution bridge between intelligent reasoning and physical actions within AetherOS. By standardizing tool definitions, validation, permissions, engine routing, controller isolation, and structured responses, it creates a secure and extensible execution framework. This design allows any supported LLM provider to invoke capabilities consistently while keeping the underlying implementation modular, testable, and independent of model-specific function-calling APIs.

---

## Next Part

**05_RUNTIME_FLOW.md — Part 5 — Memory Runtime Flow**

Topics include:

* Working memory lifecycle
* Session memory updates
* Long-term memory storage
* Embedding generation
* Vector search pipeline
* Memory ranking
* Context injection
* Memory compression
* Forgetting strategies
* Learning loop integration
