# 02_ARCHITECTURE.md

# Part 4 — Engines Architecture

> **Purpose**
>
> The **Engine Layer** is responsible for actual execution.
>
> Agents make intelligent decisions.
>
> Engines perform the work.
>
> If the Agent Layer is the **brain**, the Engine Layer is the **muscle**.

---

# Table of Contents

1. Engine Philosophy
2. Engine Architecture
3. Engine Hierarchy
4. Vision Engine
5. Desktop Engine
6. Browser Engine
7. LLM Engine
8. Memory Engine
9. Trading Engine
10. Verification Engine
11. Execution Engine
12. Learning Engine
13. Engine Communication
14. Folder Structure

---

# 1. Engine Philosophy

An Engine is responsible for **executing capabilities**, not making decisions.

Example

User:

> Click Login Button

Wrong

```text
Vision Engine

↓

Click Mouse
```

Correct

```text
Planner

↓

Desktop Agent

↓

Desktop Engine

↓

Mouse Controller
```

The Engine never asks *what* to do.

It only knows *how* to do it.

---

# Engine Responsibilities

Every engine should:

* Execute requests
* Hide implementation details
* Return structured results
* Report failures
* Collect metrics
* Expose a stable interface

---

# 2. Engine Architecture

```text
               AI Agents
                    │
                    ▼
              Engine Manager
                    │
      ┌─────────────┼──────────────┐
      │             │              │
 Vision Engine  Desktop Engine Browser Engine
      │             │              │
      ├─────────────┼──────────────┤
      │             │              │
 Memory Engine  Trading Engine  LLM Engine
      │             │              │
      └─────────────┼──────────────┘
                    │
          Verification Engine
                    │
             Execution Engine
                    │
            Operating System
```

---

# Engine Rules

Every Engine:

* Owns one domain
* Never calls another engine directly
* Never communicates with UI
* Never communicates with users
* Never performs planning

---

# 3. Engine Hierarchy

```text
Engine Manager

↓

Vision Engine

↓

OCR

↓

OpenCV

↓

YOLO

↓

SAM

↓

Desktop Engine

↓

Mouse

↓

Keyboard

↓

Windows API

↓

Browser Engine

↓

Playwright

↓

Chromium

↓

Trading Engine

↓

Indicators

↓

Strategies

↓

Risk
```

---

# 4. Vision Engine

## Purpose

The Vision Engine gives AetherOS the ability to understand the screen.

---

## Responsibilities

* Capture Screen
* OCR
* UI Detection
* Icon Detection
* Object Detection
* Window Detection
* Layout Analysis
* Image Matching
* Chart Analysis

---

## Internal Pipeline

```text
Capture Screen

↓

Image Preprocessing

↓

OCR

↓

Object Detection

↓

Layout Analysis

↓

Visual Context

↓

Result
```

---

## Internal Structure

```text
vision/

capture/

ocr/

object_detection/

icon_detection/

layout/

charts/

preprocessing/

matching/

utils/
```

---

## Capture Module

Responsible for

* Full Screen
* Window
* Region
* Multi Monitor
* Video Frames

---

## OCR Module

Supports

* PaddleOCR
* EasyOCR
* Tesseract

Future:

Cloud OCR

---

## UI Detection

Detects

Buttons

Textboxes

Menus

Tabs

Icons

Checkboxes

Lists

Tables

Trees

---

## Object Detection

Uses

YOLO

GroundingDINO

SAM

OpenCV

---

## Output Example

```json
{
    "window":"Chrome",
    "button":"Search",
    "position":[530,211],
    "confidence":0.98
}
```

---

# 5. Desktop Engine

Purpose

Interact with Windows.

---

Responsibilities

Mouse

Keyboard

Clipboard

Windows

Accessibility

Processes

File System

---

Pipeline

```text
Move Mouse

↓

Windows API

↓

Verify

↓

Result
```

---

Structure

```text
desktop/

mouse/

keyboard/

clipboard/

windows/

monitor/

audio/

process/

filesystem/

automation/

verification/
```

---

Mouse Module

* Move
* Drag
* Scroll
* Click
* Double Click
* Relative Move
* Absolute Move

---

Keyboard Module

* Write
* Shortcut
* Key Down
* Key Up
* Hold

---

Window Module

* Open
* Close
* Resize
* Focus
* Maximize
* Restore
* Enumerate

---

# 6. Browser Engine

Purpose

Browser automation.

---

Responsibilities

* Playwright
* Sessions
* Downloads
* Cookies
* Authentication
* JavaScript
* Forms
* Tabs

---

Pipeline

```text
Open Browser

↓

Open Page

↓

Wait

↓

Interact

↓

Screenshot

↓

Result
```

---

Folder

```text
browser/

playwright/

sessions/

cookies/

downloads/

tabs/

forms/

javascript/
```

---

Capabilities

* Open URLs
* Login
* Upload files
* Download files
* Scraping
* Screenshots
* PDF generation

---

# 7. LLM Engine

Purpose

Provide AI reasoning capability through multiple providers.

---

Responsibilities

* Prompt execution
* Tool calling
* Streaming
* Routing
* Context building
* Model fallback
* Token accounting

---

Architecture

```text
Prompt

↓

Router

↓

Provider

↓

Model

↓

Response
```

---

Folder

```text
llm/

providers/

router/

prompts/

memory/

tools/

parser/

stream/

cache/
```

---

Providers

* Ollama
* OpenAI
* Gemini
* Groq
* OpenRouter
* Anthropic

---

Future

Local reasoning models

Hybrid routing

Automatic benchmarking

---

# 8. Memory Engine

Purpose

Persistent knowledge.

---

Memory Types

Working Memory

↓

Session Memory

↓

Long Term Memory

↓

Semantic Memory

↓

Procedural Memory

---

Pipeline

```text
Question

↓

Embedding

↓

Vector Search

↓

Ranking

↓

Compression

↓

Return
```

---

Folder

```text
memory/

short_term/

long_term/

vector_store/

embeddings/

ranking/

compression/

retrieval/
```

---

Supports

SQLite

PostgreSQL

Chroma

FAISS

Redis

---

# 9. Trading Engine

Purpose

Financial analysis.

---

Responsibilities

Indicators

Risk

Strategies

Market Structure

Probability

Validation

Execution

---

Structure

```text
trading/

indicators/

market_structure/

ict/

smc/

strategies/

probability/

risk/

validator/

reports/
```

---

Pipeline

```text
Market Data

↓

Indicators

↓

Strategy

↓

Probability

↓

Risk

↓

Decision
```

---

Future

Broker APIs

Portfolio Management

Live Trading

---

# 10. Verification Engine

Purpose

Never assume execution succeeded.

Always verify.

---

Responsibilities

Screen Verification

OCR Verification

Window Verification

Mouse Verification

Browser Verification

File Verification

---

Pipeline

```text
Execute

↓

Observe

↓

Compare

↓

Passed?

↓

Yes

↓

Continue

↓

No

↓

Retry
```

---

Verification Sources

OCR

Vision

Accessibility API

Window State

DOM

Files

Clipboard

---

Folder

```text
verification/

ocr/

vision/

browser/

desktop/

comparison/

retry/
```

---

# 11. Execution Engine

Purpose

Execute commands reliably.

---

Receives

```text
Click

↓

Desktop Engine

↓

Mouse Controller

↓

Verification

↓

Completed
```

---

Responsibilities

Retries

Timeouts

Cancellation

Rollback

Execution History

Metrics

---

Folder

```text
execution/

executor.py

queue.py

history.py

retry.py

metrics.py

rollback.py
```

---

# 12. Learning Engine

Purpose

Improve AetherOS over time.

---

Learns

Successful plans

↓

Failures

↓

UI changes

↓

Performance

↓

Tool selection

↓

User preferences

---

Pipeline

```text
Workflow

↓

Analyze

↓

Extract Patterns

↓

Generate Improvements

↓

Store Knowledge
```

---

Folder

```text
learning/

metrics/

optimizer/

feedback/

trainer/

patterns/

evaluation/
```

---

Future

Automatic workflow optimization

Adaptive planning

Tool ranking

---

# 13. Engine Communication

Engines never communicate directly.

Wrong

```text
Vision Engine

↓

Browser Engine
```

Correct

```text
Vision Engine

↓

Vision Agent

↓

Coordinator

↓

Browser Agent

↓

Browser Engine
```

---

Communication Flow

```text
Engine

↓

Agent

↓

Coordinator

↓

Agent

↓

Engine
```

This prevents tight coupling.

---

# Error Handling

Every engine returns a standard response.

Example

```json
{
    "success": true,
    "data": {},
    "execution_time": 0.18,
    "error": null
}
```

On failure

```json
{
    "success": false,
    "error": "Window not found",
    "retryable": true,
    "details": {}
}
```

---

# Performance Metrics

Every engine should record:

* Execution Time
* Success Rate
* Failure Rate
* Retry Count
* CPU Usage
* Memory Usage
* Queue Time

These metrics feed the Learning Engine.

---

# 14. Folder Structure

```text
engines/
│
├── vision/
│
├── desktop/
│
├── browser/
│
├── llm/
│
├── memory/
│
├── trading/
│
├── verification/
│
├── execution/
│
├── learning/
│
├── registry.py
│
├── base_engine.py
│
├── interfaces.py
│
└── manager.py
```

---

# Design Principles

Every Engine must:

* Own one domain.
* Expose a stable interface.
* Hide implementation details.
* Return structured results.
* Never perform planning.
* Never call other engines directly.
* Be independently testable.
* Be replaceable without affecting agents.

---

# Summary

The Engine Layer provides the concrete capabilities that allow AetherOS to interact with the world. By separating decision-making (Agents) from execution (Engines), the architecture remains modular, testable, and extensible. New technologies—such as a different OCR engine, browser automation library, or LLM provider—can be introduced by replacing an engine implementation without changing the higher-level AI logic.

---

## Next Part — Part 5: Infrastructure & Runtime Architecture

The final part will cover:

* Runtime lifecycle
* Memory architecture
* Database layer
* API architecture
* Plugin system
* Tool registry
* Configuration management
* Security model
* Logging & monitoring
* Deployment (Docker/Kubernetes)
* Distributed agents
* Cloud architecture
* Complete end-to-end runtime sequence
* Final production architecture
