# 02_ARCHITECTURE.md

# Part 1 — System Architecture Foundation

> **Purpose**
>
> This document defines the architectural principles, layers, communication model, dependency rules, and overall system design of AetherOS.
>
> Every module in the project should follow the architecture defined here.

---

# Table of Contents

1. Architecture Philosophy
2. System Overview
3. Architectural Goals
4. Layered Architecture
5. Component Hierarchy
6. Communication Flow
7. Data Flow
8. Dependency Rules
9. Event Driven Design
10. Design Patterns
11. Project Boundaries
12. Scalability Strategy

---

# 1. Architecture Philosophy

AetherOS is **not** a chatbot.

It is an **AI Operating System**.

Instead of generating text only, the system continuously:

* Observe
* Understand
* Plan
* Reason
* Execute
* Verify
* Learn

Every architectural decision supports this continuous loop.

---

## Guiding Principle

The system must always answer one question:

> **"Given the current state of the computer, what is the best next action?"**

Everything exists to solve this problem.

---

# 2. System Overview

```text
                  User
                    │
     ┌──────────────┴──────────────┐
     │                             │
 Voice Interface            Desktop Dashboard
     │                             │
     └──────────────┬──────────────┘
                    │
              API Gateway
                    │
              Core Orchestrator
                    │
        ┌───────────┼────────────┐
        │           │            │
    Planner     Memory      Reasoning
        │           │            │
        └───────────┼────────────┘
                    │
           Multi-Agent Coordinator
                    │
 ┌──────────┬──────────┬──────────┬──────────┐
 │          │          │          │          │
Vision   Desktop   Browser   Research   Trading
 Agent     Agent      Agent      Agent      Agent
 │          │          │          │          │
 └──────────┴──────────┴──────────┴──────────┘
                    │
             Execution Engine
                    │
            Verification Engine
                    │
              Learning Engine
                    │
                 Memory
```

---

# 3. Architectural Goals

The architecture is designed around the following goals.

---

## A. Modular

Every subsystem is independent.

Example:

Vision should never depend directly on Trading.

Desktop should never depend directly on Browser.

Memory should never depend directly on Vision.

Everything communicates through interfaces.

---

## B. Scalable

The architecture should support

* one AI agent
* ten agents
* hundreds of tools
* cloud execution
* distributed workers

without redesign.

---

## C. Replaceable

Every major component should be replaceable.

Example

Replace

OpenAI

↓

Gemini

↓

Ollama

↓

Anthropic

without changing other modules.

The same applies to

OCR

Browser

Database

Desktop Controller

Embedding Models

Everything.

---

## D. Testable

Every module should be independently testable.

Bad

Planner imports Desktop directly.

Good

Planner calls an interface.

Desktop implements that interface.

---

## E. Observable

Every decision should be logged.

Every tool call recorded.

Every failure explainable.

Every execution reproducible.

---

# 4. Layered Architecture

The project is divided into logical layers.

```text
+------------------------------------------------+
|                  Presentation                  |
|----------------------------------------------- |
| Desktop UI                                    |
| Web Dashboard                                 |
| Voice                                         |
+------------------------------------------------+

+------------------------------------------------+
|                Application Layer               |
|----------------------------------------------- |
| API                                            |
| Commands                                       |
| Sessions                                       |
+------------------------------------------------+

+------------------------------------------------+
|               Intelligence Layer               |
|----------------------------------------------- |
| CEO Agent                                      |
| Planner                                        |
| Memory                                          |
| Reasoning                                      |
| Workflow Engine                                |
+------------------------------------------------+

+------------------------------------------------+
|                  Agent Layer                   |
|----------------------------------------------- |
| Vision Agent                                   |
| Desktop Agent                                  |
| Browser Agent                                  |
| Trading Agent                                  |
| Research Agent                                 |
+------------------------------------------------+

+------------------------------------------------+
|                 Engine Layer                   |
|----------------------------------------------- |
| Vision Engine                                  |
| Desktop Engine                                 |
| Browser Engine                                 |
| OCR                                             |
| Trading Engine                                 |
+------------------------------------------------+

+------------------------------------------------+
|               Infrastructure Layer            |
|----------------------------------------------- |
| Database                                       |
| Redis                                          |
| File System                                    |
| Docker                                         |
| Logging                                        |
+------------------------------------------------+
```

---

# Layer Responsibilities

## Presentation Layer

Responsible for

* user interaction
* displaying information
* receiving commands

Contains

Desktop Dashboard

Voice

REST API

Web UI

---

## Application Layer

Transforms user requests into internal commands.

Does not perform reasoning.

Example

Receive

"Open TradingView"

↓

Create command

↓

Send to planner

---

## Intelligence Layer

The brain.

Contains

Planning

Reasoning

Memory

Scheduling

Decision making

Task decomposition

Nothing in this layer touches the mouse or keyboard directly.

---

## Agent Layer

Specialized workers.

Each agent owns exactly one domain.

Vision

Desktop

Trading

Browser

Coding

Research

Memory

---

## Engine Layer

Implements capabilities.

Examples

OCR

Mouse Controller

Playwright

YOLO

OpenCV

Embedding Engine

These are low-level implementations.

---

## Infrastructure Layer

Responsible for

Storage

Networking

Configuration

Logging

Databases

Queues

Docker

Nothing here contains AI logic.

---

# 5. Component Hierarchy

```text
User
 │
 ▼
Dashboard
 │
 ▼
API
 │
 ▼
CEO Agent
 │
 ▼
Planner
 │
 ▼
Reasoning
 │
 ▼
Workflow Engine
 │
 ▼
Task Graph
 │
 ▼
Agent Coordinator
 │
 ▼
Agents
 │
 ▼
Engines
 │
 ▼
Tools
 │
 ▼
Operating System
```

Every level has exactly one responsibility.

---

# 6. Communication Flow

Modules never communicate randomly.

Allowed communication

```text
Planner

↓

Coordinator

↓

Vision Agent

↓

Vision Engine

↓

OCR
```

Forbidden

```text
Planner

↓

OCR
```

Planner should never know OCR exists.

---

Another example

Good

```text
Planner

↓

Desktop Agent

↓

Desktop Engine

↓

Mouse Controller
```

Bad

```text
Planner

↓

Mouse.move()
```

This rule keeps the architecture maintainable.

---

# 7. Data Flow

Every request follows the same lifecycle.

```text
User Goal

↓

Context Collection

↓

Memory Retrieval

↓

Reasoning

↓

Planning

↓

Task Graph

↓

Agent Selection

↓

Tool Selection

↓

Execution

↓

Verification

↓

Learning

↓

Memory Update

↓

Finished
```

Every workflow follows this pipeline.

---

# Example

User

> Open TradingView and analyze BTC.

Pipeline

```text
Goal

↓

Planner

↓

Memory

↓

Desktop Agent

↓

Browser Agent

↓

Vision Agent

↓

Trading Agent

↓

Verification

↓

Memory
```

---

# 8. Dependency Rules

The project follows strict dependency rules.

High-level modules never depend on low-level implementations.

Correct

```text
Planner

↓

Desktop Interface

↓

Desktop Engine

↓

Mouse
```

Wrong

```text
Planner

↓

PyAutoGUI
```

---

Only interfaces move upward.

Implementations remain below.

---

# 9. Event Driven Design

AetherOS communicates primarily using events.

Example

```text
Window Opened

↓

Event Bus

↓

Vision Agent

↓

Planner

↓

Memory
```

Another example

```text
OCR Finished

↓

Event Bus

↓

Reasoning

↓

Verification
```

Advantages

* loose coupling
* asynchronous execution
* scalability
* replay capability
* easier debugging

---

# Event Types

Typical events include:

* GoalReceived
* TaskCreated
* PlanGenerated
* ToolStarted
* ToolCompleted
* ToolFailed
* ScreenshotCaptured
* OCRCompleted
* VerificationPassed
* VerificationFailed
* MemoryUpdated
* WorkflowCompleted

Every event should contain:

* unique ID
* timestamp
* source
* payload
* correlation ID

---

# 10. Design Patterns

The architecture intentionally combines several software design patterns.

### Factory Pattern

Creates LLM providers dynamically.

```text
ProviderFactory

↓

OpenAI

Gemini

Ollama

Groq
```

---

### Strategy Pattern

Used for:

* planning algorithms
* OCR engines
* routing logic
* reasoning strategies

---

### Adapter Pattern

Wraps external APIs.

Example

OpenAI Adapter

Playwright Adapter

Windows Adapter

Redis Adapter

---

### Observer Pattern

Event Bus

↓

Subscribers

↓

React automatically

---

### Command Pattern

Every action becomes a command.

Examples

MoveMouse

Click

TypeText

CaptureScreen

Scroll

OpenBrowser

Commands can be:

* queued
* cancelled
* retried
* logged

---

### Dependency Injection

Modules receive dependencies rather than creating them.

Benefits:

* testing
* flexibility
* replaceable implementations

---

# 11. Project Boundaries

Every folder owns a domain.

Examples:

* `vision/` owns image understanding.
* `desktop/` owns OS interaction.
* `browser/` owns browser automation.
* `memory/` owns persistence and retrieval.
* `llm/` owns provider integration.
* `agents/` own decision making within their domain.
* `core/` owns orchestration.

Cross-domain logic belongs in `core/`, not inside domain modules.

---

# 12. Scalability Strategy

The architecture is designed to evolve without major rewrites.

### Stage 1 — Local MVP

* Single process
* Local LLM
* SQLite
* Local memory

---

### Stage 2 — Multi-Agent

* Multiple concurrent agents
* Redis event bus
* Background workers

---

### Stage 3 — Team Deployment

* PostgreSQL
* Docker Compose
* Shared memory
* Central API

---

### Stage 4 — Cloud Native

* Kubernetes
* Distributed workers
* Cloud object storage
* Horizontal scaling
* Remote execution

---

# Architecture Principles Summary

Every new module added to AetherOS should satisfy these principles:

* Single responsibility
* Interface-first design
* Dependency inversion
* Event-driven communication
* Asynchronous execution where appropriate
* Verifiable actions
* Comprehensive logging
* Independent testing
* Replaceable implementations
* Clear ownership of responsibilities

Following these rules ensures that AetherOS remains maintainable as it grows from a local AI assistant into a distributed autonomous operating system.

---

**Next:** **Part 2 — Core Architecture**, covering the Orchestrator, Planner, Scheduler, Event Bus, Workflow Engine, State Manager, Task Queue, and Message Bus in detail.
