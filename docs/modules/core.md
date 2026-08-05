# CORE.md

# AetherOS Core Architecture

> **Purpose**
>
> The **Core** module is the heart of AetherOS. Every other subsystem—Vision, Memory, Desktop, Browser, LLM, Runtime, Agents, Voice, and Trading—depends on it.
>
> The Core does **not** perform AI reasoning or automation itself. Instead, it provides the common infrastructure, abstractions, utilities, lifecycle management, and shared services used by every module.

---

# Design Philosophy

The Core should be:

* Modular
* Lightweight
* Independent
* Extensible
* Thread-safe
* Async-first
* Testable
* Provider-agnostic
* Platform-aware
* Highly reusable

---

# Responsibilities

The Core is responsible for:

* Configuration
* Logging
* Error handling
* Dependency Injection
* Service Container
* Event System
* Interfaces
* Utilities
* Lifecycle Management
* Validation
* Serialization
* Resource Management
* Feature Flags

The Core **never** contains:

* Vision models
* Browser automation
* Desktop controllers
* AI prompts
* Trading logic
* Business logic

---

# Directory Structure

```text
core/
│
├── __init__.py
│
├── config/
│
├── logging/
│
├── errors/
│
├── container/
│
├── events/
│
├── interfaces/
│
├── lifecycle/
│
├── validation/
│
├── serialization/
│
├── resources/
│
├── cache/
│
├── state/
│
├── constants/
│
├── types/
│
├── decorators/
│
├── async/
│
├── concurrency/
│
├── metrics/
│
├── utilities/
│
├── filesystem/
│
├── platform/
│
├── security/
│
└── version/
```

---

# Module Overview

| Folder        | Purpose                     |
| ------------- | --------------------------- |
| config        | Configuration management    |
| logging       | Logging framework           |
| errors        | Exception hierarchy         |
| container     | Dependency Injection        |
| events        | Event Bus                   |
| interfaces    | Abstract interfaces         |
| lifecycle     | Startup & shutdown          |
| validation    | Data validation             |
| serialization | JSON & object serialization |
| resources     | CPU/GPU/RAM management      |
| cache         | Shared cache                |
| state         | Global runtime state        |
| constants     | Global constants            |
| types         | Shared dataclasses & typing |
| decorators    | Common decorators           |
| async         | Async helpers               |
| concurrency   | Thread & process helpers    |
| metrics       | Monitoring                  |
| utilities     | Helper functions            |
| filesystem    | File utilities              |
| platform      | OS abstraction              |
| security      | Core security               |
| version       | Version management          |

---

# Configuration System

Folder

```text
core/config/
```

Files

```text
settings.py

loader.py

constants.py

paths.py

environment.py
```

Responsibilities

* Environment variables
* API keys
* File paths
* Runtime flags
* Development mode
* Production mode

---

# Logging Framework

Folder

```text
core/logging/
```

Files

```text
logger.py

formatter.py

handlers.py

console.py

file_logger.py
```

Capabilities

* Colored logs
* File logs
* JSON logs
* Error logs
* Rotation
* Performance logs

Library

```text
Loguru
```

---

# Error Framework

Folder

```text
core/errors/
```

Base hierarchy

```text
BaseError

↓

ConfigurationError

↓

ProviderError

↓

DesktopError

↓

VisionError

↓

MemoryError

↓

RuntimeError
```

Every error contains

* Error code
* Message
* Recovery suggestion
* Stack trace
* Context

---

# Dependency Injection

Folder

```text
core/container/
```

Responsibilities

* Register services
* Lazy loading
* Singleton creation
* Scoped services
* Dependency resolution

Example

```python
container.register(Logger)

container.resolve(Logger)
```

---

# Event Bus

Folder

```text
core/events/
```

Files

```text
event.py

event_bus.py

publisher.py

subscriber.py
```

Pipeline

```text
Publisher

↓

Event Bus

↓

Subscribers
```

Everything communicates through events.

---

# Interfaces

Folder

```text
core/interfaces/
```

Contains

```text
LLMProvider

MemoryProvider

VisionProvider

DesktopController

BrowserController

SpeechProvider

StorageProvider
```

Every module depends on interfaces instead of implementations.

---

# Lifecycle Manager

Folder

```text
core/lifecycle/
```

Stages

```text
Initialize

↓

Start

↓

Running

↓

Stopping

↓

Shutdown
```

Responsibilities

* Startup order
* Cleanup
* Shutdown hooks
* Health checks

---

# Validation

Folder

```text
core/validation/
```

Responsibilities

* Validate configs
* Validate API responses
* Validate tool inputs
* Validate outputs

Library

* Pydantic

---

# Serialization

Folder

```text
core/serialization/
```

Handles

* JSON
* YAML
* Pickle (internal)
* MessagePack (future)

---

# Resource Manager

Folder

```text
core/resources/
```

Tracks

* CPU
* RAM
* GPU
* VRAM
* Disk
* Threads

Libraries

* psutil
* pynvml

---

# Cache

Folder

```text
core/cache/
```

Types

* Memory cache
* LRU cache
* Temporary cache
* Shared cache

Future

* Redis

---

# Global State

Folder

```text
core/state/
```

Stores

* Active workflow
* Running agents
* Current model
* Current provider
* Runtime status

---

# Constants

Folder

```text
core/constants/
```

Contains

```text
Default Ports

Model Names

Timeouts

Retry Limits

Directories

Environment Names
```

---

# Shared Types

Folder

```text
core/types/
```

Contains

* Dataclasses
* Enums
* TypedDicts
* Shared models

Example

```python
Task

Workflow

BoundingBox

ScreenRegion

MemoryRecord
```

---

# Decorators

Folder

```text
core/decorators/
```

Examples

```python
@retry

@cache

@singleton

@benchmark

@validate

@log_execution
```

---

# Async Utilities

Folder

```text
core/async/
```

Provides

* Async tasks
* Timers
* Await helpers
* Cancellation
* Timeouts

---

# Concurrency

Folder

```text
core/concurrency/
```

Supports

* Threads
* Processes
* Worker pools
* Locks
* Queues

---

# Metrics

Folder

```text
core/metrics/
```

Collects

* Latency
* Memory usage
* CPU
* GPU
* API calls
* Token usage

Future

* Prometheus
* OpenTelemetry

---

# Utilities

Folder

```text
core/utilities/
```

General helpers

* String utilities
* Time utilities
* Retry helpers
* Math helpers
* UUID generation
* Hashing

---

# Filesystem

Folder

```text
core/filesystem/
```

Functions

* Read files
* Write files
* Watch directories
* Safe delete
* Atomic writes

Uses

* pathlib

---

# Platform Layer

Folder

```text
core/platform/
```

Provides

* Windows abstraction
* Linux abstraction
* macOS abstraction

Responsibilities

Hide OS-specific code behind common interfaces.

---

# Security

Folder

```text
core/security/
```

Responsibilities

* Secrets management
* Encryption helpers
* Secure storage
* Permission checking

---

# Version Manager

Folder

```text
core/version/
```

Tracks

* Current version
* Build number
* Git commit
* Compatibility

---

# Initialization Order

```text
Configuration

↓

Logger

↓

Service Container

↓

Event Bus

↓

Cache

↓

Resource Manager

↓

Metrics

↓

Platform Layer

↓

Interfaces

↓

Ready
```

---

# Dependencies

```text
Every Module

↓

Core

↓

Python Standard Library
```

No circular dependencies.

---

# Technology Stack

| Component            | Technology                  |
| -------------------- | --------------------------- |
| Configuration        | Pydantic Settings           |
| Logging              | Loguru                      |
| Validation           | Pydantic                    |
| Dependency Injection | Custom Container            |
| Async Runtime        | asyncio                     |
| Concurrency          | concurrent.futures          |
| Resources            | psutil                      |
| Serialization        | JSON / YAML                 |
| Metrics              | OpenTelemetry (future)      |
| Typing               | Python Typing + Dataclasses |

---

# Core Design Rules

1. Core must never depend on higher-level modules.
2. All shared code belongs in Core.
3. Every subsystem communicates through interfaces or events.
4. Keep Core lightweight and reusable.
5. Avoid business logic inside Core.
6. Everything should be unit-testable.
7. Prefer async APIs where possible.
8. Maintain backward compatibility for shared interfaces.

---

# Success Criteria

The Core is complete when:

* ✅ Configuration loads correctly
* ✅ Logging is centralized
* ✅ Errors are standardized
* ✅ Services resolve through the container
* ✅ Events flow between modules
* ✅ Interfaces define all shared contracts
* ✅ Resources are monitored
* ✅ Validation works consistently
* ✅ Lifecycle management is reliable
* ✅ Every other AetherOS module can build on top of Core without introducing shared infrastructure.

The **Core** is the foundation of AetherOS. If every other module represents organs of the system, the Core is its **spine and nervous system**, providing the common infrastructure that keeps the entire operating system modular, scalable, and maintainable.
