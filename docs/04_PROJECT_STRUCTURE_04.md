# 04_PROJECT_STRUCTURE.md

# Part 4 — Engines Project Structure

> **Purpose**
>
> The `engines/` directory contains the execution layer of AetherOS.
>
> While **Agents think**, **Engines execute**.
>
> Every Engine exposes a clean API that hides implementation details from the rest of the system.

---

# Directory Structure

```text
engines/
│
├── __init__.py
├── base_engine.py
├── interfaces.py
├── registry.py
├── manager.py
├── context.py
├── metrics.py
├── factory.py
│
├── vision/
├── desktop/
├── browser/
├── llm/
├── memory/
├── trading/
├── execution/
├── verification/
├── learning/
│
└── utils/
```

---

# Engine Philosophy

The Engine Layer is responsible for **execution only**.

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

The Engine should never:

* Make decisions
* Plan workflows
* Choose tools
* Coordinate agents

---

# Standard Engine Interface

Every engine inherits from BaseEngine.

```python
class BaseEngine:

    async def initialize(self):
        ...

    async def execute(self, command):
        ...

    async def verify(self):
        ...

    async def shutdown(self):
        ...
```

---

# base_engine.py

Contains common functionality shared by every engine.

Responsibilities

* Logging
* Metrics
* Configuration
* Initialization
* Error Handling
* Retry Hooks

---

# interfaces.py

Defines contracts.

Example

```python
class VisionEngineInterface:

    async def analyze(image):
        ...
```

Every engine should follow its interface.

---

# registry.py

Registers every engine.

Example

```python
ENGINES = {

    "vision": VisionEngine,

    "desktop": DesktopEngine,

    "browser": BrowserEngine,

    "memory": MemoryEngine,

    "llm": LLMEngine,

    "verification": VerificationEngine,

    "execution": ExecutionEngine,

    "learning": LearningEngine
}
```

---

# manager.py

Responsible for

* Engine lifecycle
* Resource allocation
* Health monitoring
* Restart failed engines

---

# factory.py

Creates engines dynamically.

```python
factory.create("vision")
```

instead of

```python
VisionEngine()
```

---

# context.py

Provides engine-specific execution context.

Example

Vision Engine

```text
Screenshot

OCR Cache

Detection Models

Configuration
```

Desktop Engine

```text
Mouse Position

Focused Window

Display Information
```

---

# metrics.py

Collects

* Execution Time
* Success Rate
* Failure Rate
* Retry Count
* CPU Usage
* Memory Usage

---

# Vision Engine

## Purpose

The Vision Engine enables AetherOS to understand everything visible on the screen.

---

## Directory

```text
vision/
│
├── engine.py
├── capture.py
├── preprocessing.py
├── ocr.py
├── detection.py
├── segmentation.py
├── ui_detection.py
├── layout.py
├── charts.py
├── matcher.py
├── cache.py
├── models.py
├── config.py
└── utils.py
```

---

### capture.py

Captures

* Full Screen
* Window
* Region
* Multi Monitor

---

### preprocessing.py

Image enhancements

* Resize
* Denoise
* Sharpen
* Contrast
* Threshold

---

### ocr.py

Handles

* PaddleOCR
* EasyOCR
* Tesseract

Returns structured text.

---

### detection.py

Uses

* YOLO
* OpenCV

Detects

* Icons
* Buttons
* Images
* Windows

---

### segmentation.py

Uses

* SAM

Separates UI components.

---

### ui_detection.py

Detects

* Buttons
* Input Fields
* Checkboxes
* Menus
* Tabs
* Lists

---

### charts.py

Specialized chart analysis.

Supports

* TradingView
* Candlesticks
* Indicators
* Trendlines

---

### matcher.py

Template matching.

Useful when OCR is unavailable.

---

# Desktop Engine

## Directory

```text
desktop/
│
├── engine.py
├── mouse.py
├── keyboard.py
├── window.py
├── clipboard.py
├── display.py
├── process.py
├── filesystem.py
├── automation.py
├── verification.py
└── config.py
```

---

### mouse.py

Provides

* Move
* Click
* Scroll
* Drag
* Hover

---

### keyboard.py

Provides

* Type
* Shortcut
* Hold Keys
* Release Keys

---

### window.py

Controls

* Focus
* Resize
* Maximize
* Restore
* Enumerate Windows

---

### display.py

Handles

* Resolution
* Monitor Layout
* Scaling
* Screen Coordinates

---

### process.py

Controls

* Start Process
* Stop Process
* Process List

---

### filesystem.py

Provides

* Copy
* Move
* Rename
* Delete
* Search Files

---

# Browser Engine

## Directory

```text
browser/
│
├── engine.py
├── playwright.py
├── tabs.py
├── pages.py
├── forms.py
├── cookies.py
├── downloads.py
├── uploads.py
├── javascript.py
├── screenshots.py
└── sessions.py
```

---

Capabilities

* Open Website
* Login
* Search
* Fill Forms
* Upload Files
* Download Files
* Generate PDFs

---

# LLM Engine

## Directory

```text
llm/
│
├── engine.py
├── router.py
├── providers/
├── prompts/
├── parser.py
├── tools.py
├── stream.py
├── memory.py
├── cache.py
├── tokenizer.py
└── config.py
```

---

### router.py

Chooses

* Ollama
* OpenRouter
* OpenAI
* Gemini
* Claude
* Groq

---

### providers/

Each provider has its own implementation.

```text
providers/

ollama.py

openai.py

openrouter.py

groq.py

gemini.py

claude.py
```

---

### parser.py

Converts model responses into structured objects.

Supports

* JSON
* Tool Calls
* Markdown

---

### tools.py

Tool execution layer.

Responsibilities

* Register tools
* Validate tools
* Execute tools
* Return results

---

# Memory Engine

## Directory

```text
memory/
│
├── engine.py
├── retrieval.py
├── storage.py
├── embeddings.py
├── vector_store.py
├── ranking.py
├── compression.py
├── cache.py
├── indexing.py
└── cleanup.py
```

---

Responsibilities

* Store Knowledge
* Retrieve Context
* Rank Memories
* Compress History

Supports

* Working Memory
* Session Memory
* Long-Term Memory

---

# Trading Engine

## Directory

```text
trading/
│
├── engine.py
├── indicators.py
├── market_structure.py
├── ict.py
├── smc.py
├── strategies.py
├── probability.py
├── risk.py
├── reports.py
└── validator.py
```

---

Capabilities

* Technical Analysis
* Smart Money Concepts
* ICT Concepts
* Probability Analysis
* Risk Management

---

# Execution Engine

## Directory

```text
execution/
│
├── engine.py
├── executor.py
├── queue.py
├── scheduler.py
├── timeout.py
├── rollback.py
├── history.py
└── retry.py
```

---

Responsibilities

* Execute Commands
* Retry Failed Operations
* Maintain History
* Rollback Failed Tasks

---

# Verification Engine

## Directory

```text
verification/
│
├── engine.py
├── ocr.py
├── desktop.py
├── browser.py
├── vision.py
├── comparator.py
├── validator.py
└── retry.py
```

---

Responsibilities

* Verify Screen
* Verify Window
* Verify OCR
* Verify Browser
* Detect Failures
* Trigger Retries

---

# Learning Engine

## Directory

```text
learning/
│
├── engine.py
├── feedback.py
├── optimizer.py
├── trainer.py
├── metrics.py
├── patterns.py
├── evaluation.py
└── ranking.py
```

---

Responsibilities

* Learn from Success
* Learn from Failure
* Improve Tool Selection
* Optimize Workflows
* Detect Patterns

---

# utils/

Contains helper functions shared across engines.

Examples

```text
image.py

geometry.py

timers.py

json_utils.py

validators.py
```

Avoid placing business logic here.

---

# Engine Communication

```text
Agent

↓

Engine

↓

Controller

↓

Operating System
```

Never

```text
Vision Engine

↓

Desktop Engine
```

Communication always flows back through the Agent and Core layers.

---

# Dependency Rules

Allowed

```text
Engine

↓

Controller

↓

Operating System
```

Not Allowed

```text
Engine

↓

Another Engine
```

or

```text
Engine

↓

Agent
```

This prevents circular dependencies.

---

# Engine Development Standards

Each engine should include:

```text
README.md

engine.py

config.py

models.py

exceptions.py

tests/

examples/
```

Every engine should be independently testable and replaceable.

---

# Complete Engine Flow

```text
Task

↓

Agent

↓

Engine

↓

Controller

↓

OS/API

↓

Verification

↓

Engine Result

↓

Agent

↓

Core
```

This ensures a clean separation between intelligence and execution.

---

# Summary

The `engines/` directory provides the execution capabilities of AetherOS. Each engine encapsulates a single technical domain—vision, desktop control, browser automation, memory, LLM interaction, trading analysis, verification, execution management, or learning—and exposes a consistent interface to the Agent layer. By isolating implementation details inside engines, the architecture remains modular, maintainable, and easy to extend as new technologies become available.

---

## Next Part

**Part 5 — `desktop/` Project Structure**

This will document the complete desktop automation subsystem, including:

* Mouse controller
* Keyboard controller
* Window manager
* Screen capture
* Clipboard
* File system
* Process manager
* Audio control
* Accessibility
* Automation workflows
* Verification system
* Tool wrappers
* Complete file-by-file architecture

This is one of the largest modules in AetherOS and will serve as the foundation for autonomous desktop control.
