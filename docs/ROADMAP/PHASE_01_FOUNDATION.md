# ROADMAP.md

# Phase 1 — Foundation & Core Infrastructure (Weeks 1–6)

> **Goal**
>
> Build the foundation of AetherOS. At the end of this phase, the project should have a modular architecture, core infrastructure, basic desktop control, provider abstraction, logging, configuration, and a working CLI assistant.
>
> **Deliverable:** A stable developer platform that every future AI component will build upon.

---

# Phase Overview

Phase 1
   ↓
Project Foundation
   ↓
Core Infrastructure
   ↓
Desktop Controllers
   ↓
LLM Integration
   ↓
Tool System
   ↓
CLI Assistant
   ↓
Ready for Phase 2
```

---

# Objectives

By the end of Phase 1, AetherOS should be able to:

* Start successfully
* Load configuration
* Initialize all services
* Connect to LLM providers
* Execute desktop tools
* Register tools automatically
* Process CLI commands
* Log everything
* Handle errors gracefully

No Vision, Memory, Browser, or AI Planning yet.

---

# Milestone 1 — Repository Setup

## Goals

Create a clean, scalable project.

Tasks

* Create Git repository
* Configure `.gitignore`
* Configure `README.md`
* Configure license
* Configure development branch
* Configure semantic versioning

Project layout

```text
AetherOS/

docs/

core/

desktop/

browser/

vision/

memory/

llm/

agents/

runtime/

tools/

config/

tests/

scripts/

logs/
```

Deliverable

> Professional repository structure.

---

# Milestone 2 — Python Environment

Tasks

* Python 3.12+
* uv or pip
* Virtual environment
* Dependency manager
* Requirements
* Development dependencies

Install

```text
Python

uv

Git

VS Code

CUDA Toolkit (optional)
```

Deliverable

> Reproducible development environment.

---

# Milestone 3 — Configuration System

Folder

```text
config/
```
Files

```text
settings.py
config_loader.py
env.py
constants.py
```

Responsibilities

* Environment variables
* Paths
* Feature flags
* API keys
* Runtime settings

Libraries

* Pydantic Settings
* python-dotenv

Deliverable

Central configuration.

---

# Milestone 4 — Logging System

Folder

```text
core/logging/
```

Components

```text
logger.py

formatter.py

handlers.py
```

Requirements

* Colored console logs
* File logging
* Error logging
* Debug logging
* Rotation
* JSON logs

Library

```text
Loguru
```

Deliverable

Central logging framework.

---

# Milestone 5 — Exception Framework

Folder

```text
core/errors/
```

Files

```text
base_error.py

desktop_error.py

browser_error.py

vision_error.py

llm_error.py
```

Responsibilities

* Standard error format
* Error codes
* Recovery hints
* Stack traces

Deliverable

Unified error handling.

---

# Milestone 6 — Dependency Injection

Purpose

Remove tight coupling.

Create

```text
Service Container
```

Responsibilities

* Register services
* Lazy loading
* Singleton management

Folder

```text
core/container/
```

Deliverable

Central dependency management.

---

# Milestone 7 — Event Bus

Folder

```text
runtime/events/
```

Components

```text
publisher.py

subscriber.py

event_bus.py

events.py
```

Capabilities

* Publish
* Subscribe
* Async events
* Event filtering

Deliverable

Inter-module communication.

---

# Milestone 8 — Base Interfaces

Create abstract interfaces.

Examples

```text
MouseController

KeyboardController

BrowserProvider

LLMProvider

MemoryProvider

VisionProvider
```

Folder

```text
core/interfaces/
```

Deliverable

Loose coupling.

---

# Milestone 9 — Provider System

Folder

```text
llm/providers/
```

Implement

```text
OpenRouter

OpenAI

Ollama
```

Common interface

```python
generate()

stream()

tool_call()
```

Deliverable

Provider abstraction.

---

# Milestone 10 — Tool Registry

Folder

```text
tools/
```

Components

```text
registry.py

decorators.py

loader.py

schema.py
```

Capabilities

* Auto-discovery
* Dynamic registration
* JSON schema generation
* Tool validation

Deliverable

Dynamic tool system.

---

# Milestone 11 — Desktop Controllers

Folder

```text
desktop/
```

Implement

```text
Mouse

Keyboard

Clipboard

Window

Screen

File

Process
```

Each controller should expose

```python
move()

click()

type()

copy()

paste()

launch()

close()
```

Deliverable

Desktop automation foundation.

---

# Milestone 12 — CLI Runtime

Folder

```text
cli/
```

Components

```text
main.py

parser.py

commands.py
```

Example

```bash
> aether

You:
Open Notepad

Aether:
Opening Notepad...
```

Deliverable

Interactive terminal assistant.

---

# Milestone 13 — Runtime Bootstrap

Create startup sequence.

```text
Load Config

↓

Initialize Logger

↓

Register Services

↓

Load Providers

↓

Register Tools

↓

Initialize Controllers

↓

Ready
```

Folder

```text
runtime/bootstrap/
```

Deliverable

Single startup pipeline.

---

# Milestone 14 — Health Checks

Every module reports

* Status
* Version
* Dependencies
* Errors

Example

```text
Desktop

Healthy

Browser

Not Loaded

LLM

Healthy
```

Deliverable

System diagnostics.

---

# Milestone 15 — Testing Framework

Setup

```text
pytest

coverage

mocking
```

Tests

* Configuration
* Controllers
* Tool Registry
* Providers
* Bootstrap

Deliverable

Reliable codebase.

---

# Folder Status After Phase 1

```text
AetherOS/

core/
config/
desktop/
llm/
runtime/
tools/
cli/
tests/
docs/
logs/
scripts/
```

Most folders exist but are still minimal.

---

# Recommended Tech Stack

| Category             | Technology                      |
| -------------------- | ------------------------------- |
| Language             | Python 3.12                     |
| Package Manager      | uv                              |
| Configuration        | Pydantic Settings               |
| Logging              | Loguru                          |
| Validation           | Pydantic                        |
| Async                | asyncio                         |
| Dependency Injection | dependency-injector (or custom) |
| Testing              | pytest                          |
| Formatting           | Ruff + Black                    |
| Type Checking        | mypy                            |
| Git Hooks            | pre-commit                      |

---

# Success Criteria

Phase 1 is complete when:

* ✅ Project structure finalized
* ✅ Configuration system works
* ✅ Logging works
* ✅ Error handling works
* ✅ Tool registry loads tools
* ✅ Desktop controllers execute commands
* ✅ OpenRouter/OpenAI/Ollama providers work
* ✅ CLI assistant accepts commands
* ✅ Bootstrap initializes all services
* ✅ Unit tests pass

---

# Estimated Timeline

| Week   | Focus                                 |
| ------ | ------------------------------------- |
| Week 1 | Repository, Environment, Config       |
| Week 2 | Logging, Errors, Dependency Injection |
| Week 3 | Event Bus, Interfaces                 |
| Week 4 | LLM Providers, Tool Registry          |
| Week 5 | Desktop Controllers                   |
| Week 6 | CLI Runtime, Bootstrap, Testing       |

---

# Deliverable

At the end of **Phase 1**, AetherOS is no longer just a collection of folders—it becomes a functioning software platform with a solid architectural foundation. All future phases (Vision, Browser, Memory, Agents, and Autonomous Execution) will build on this infrastructure without requiring major refactoring.
