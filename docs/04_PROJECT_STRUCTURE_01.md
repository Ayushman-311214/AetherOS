# 04_PROJECT_STRUCTURE.md

# Part 1 — Repository Foundation

> **Purpose**
>
> This document defines the purpose and responsibility of every file and folder located at the root of the AetherOS repository.
>
> These files form the foundation of the entire project before any AI modules are implemented.

---

# Repository Overview

```text
AetherOS/
│
├── README.md
├── LICENSE
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── configs/
├── docs/
├── scripts/
├── assets/
├── tests/
├── logs/
│
├── core/
├── agents/
├── engines/
├── llm/
├── desktop/
├── browser/
├── vision/
├── memory/
├── backend/
├── database/
├── integrations/
│
└── data/
```

---

# Repository Philosophy

The repository should follow one simple rule:

> **Every folder owns exactly one domain.**

Example

```text
vision/
```

Owns

* OCR
* Object Detection
* Screen Analysis

Nothing else.

---

```text
desktop/
```

Owns

* Mouse
* Keyboard
* Windows

Nothing else.

---

This makes the project:

* Easier to maintain
* Easier to test
* Easier to replace modules
* Easier for new contributors

---

# Root Directory

Everything inside the root should describe or configure the project.

No business logic belongs here.

---

# README.md

## Purpose

Main entry point for developers.

When someone opens GitHub, this should answer:

* What is AetherOS?
* What does it do?
* How to install?
* How to run?
* How to contribute?

---

## Should Contain

```text
Project Overview

Architecture Diagram

Installation

Quick Start

Features

Folder Structure

Development Guide

Roadmap

License

Contributing
```

---

## Example Structure

```text
README.md

Introduction

Installation

Usage

Architecture

Modules

Development

Documentation

Contributing
```

---

# LICENSE

Purpose

Defines legal permissions.

Recommended

```text
MIT License
```

or

```text
Apache 2.0
```

depending on future plans.

---

# .env

Purpose

Stores sensitive configuration.

Never commit this file.

---

Contains

```text
OPENAI_API_KEY=

OPENROUTER_API_KEY=

GROQ_API_KEY=

DATABASE_URL=

REDIS_URL=

JWT_SECRET=

POSTGRES_USER=

POSTGRES_PASSWORD=
```

---

# .env.example

Purpose

Template for developers.

Example

```text
OPENAI_API_KEY=

DATABASE_URL=

REDIS_URL=
```

No secrets should exist here.

---

# .gitignore

Purpose

Ignore generated files.

Should ignore

```text
venv/

__pycache__/

.pytest_cache/

.env

logs/

data/cache/

*.sqlite

*.db

*.pyc

node_modules/

dist/

build/
```

---

# pyproject.toml

Purpose

Modern Python project configuration.

Should contain

Project metadata

Dependencies

Formatting rules

Build system

Package configuration

---

Example

```toml
[project]

name="aetheros"

version="1.0.0"
```

---

# requirements.txt

Purpose

Python dependencies.

Only runtime packages.

Development tools should live separately.

Example

```text
fastapi

opencv-python

playwright

loguru

pydantic

sqlalchemy

redis

paddleocr
```

---

# Dockerfile

Purpose

Containerize AetherOS.

Responsibilities

* Build image
* Install dependencies
* Configure runtime
* Launch application

---

Should NOT

Contain secrets.

---

# docker-compose.yml

Purpose

Run multiple services.

Example

```text
API

↓

Redis

↓

PostgreSQL

↓

ChromaDB

↓

Dashboard
```

One command should start the development environment.

---

# Makefile

Purpose

Developer shortcuts.

Examples

```bash
make install

make lint

make test

make run

make format

make docs

make docker
```

Makes development consistent.

---

# configs/

Purpose

Centralized configuration.

No hardcoded values inside code.

---

Structure

```text
configs/

app.yaml

models.yaml

logging.yaml

vision.yaml

desktop.yaml

voice.yaml

memory.yaml

database.yaml

security.yaml

trading.yaml
```

---

Example

models.yaml

```yaml
provider: ollama

model: qwen3
```

---

Benefits

Easy configuration

Environment switching

No code changes

---

# docs/

Purpose

Entire engineering documentation.

Contains

Architecture

Vision

Roadmap

API

Agents

Engines

Memory

Desktop

Vision

Examples

Diagrams

Never place implementation code here.

---

Recommended Structure

```text
docs/

architecture/

roadmap/

modules/

guides/

diagrams/

api/

references/
```

---
# scripts/

Purpose
Developer utilities.
Examples
Installation
Migration
Training
Dataset preparation
Environment setup
Cleanup
---

Example

```text
scripts/
install.py
setup.py
download_models.py
train.py
backtest.py
cleanup.py
```
Scripts should never contain application logic.

---

# assets/

Purpose

Static resources.
Contains
```text
icons/
logos/
fonts/
images/
templates/
sounds/
```

Examples

Application icon
Splash screen
Notification sound
Email template

---

# tests/

Purpose
All automated testing.
Structure
```text
tests/

unit/

integration/

vision/

desktop/

browser/

api/

performance/
```

---

Every module must have tests.

Goal

```text
High coverage

Reliable automation

Regression prevention
```

---

# logs/

Purpose
Runtime logs.
Structure
```text
logs/

application/

vision/

desktop/

browser/

trading/

errors/

performance/
```

Never commit logs.

---

# data/

Purpose

Persistent application data.

Contains

```text
cache/

screenshots/

reports/

datasets/

downloads/

exports/

models/
```

---

Guidelines

Temporary files

↓

cache/

Permanent files

↓

reports/

Machine Learning

↓

models/

---

# Root Directory Rules

The repository root should remain clean.

Allowed

Configuration

Documentation

Infrastructure

Build files

Scripts

Forbidden

Business logic

AI reasoning

Desktop automation

Vision processing

Trading algorithms

These belong inside their respective modules.

---

# Naming Conventions

Folders

```text
snake_case
```

Examples

```text
vision_agent

memory_engine

desktop_controller
```

---

Python Files

```text
snake_case.py
```

Examples

```text
screen_capture.py

mouse_controller.py

event_bus.py
```

---

Classes

```text
PascalCase
```

Example

```python
class VisionAgent:
    pass
```

---

Functions

```python
capture_screen()

move_mouse()

analyze_chart()
```

---

Constants

```python
MAX_RETRY

DEFAULT_TIMEOUT

SCREENSHOT_PATH
```

---

# Repository Standards

Every module should include:

```text
README.md

__init__.py

interfaces.py

exceptions.py

models.py

tests/

examples/
```

where applicable.

This keeps modules self-contained and easier to understand.

---

# Root Dependency Rules

```text
README

↓

Core

↓

Agents

↓

Engines

↓

Infrastructure
```

The root should never import project modules.

Its responsibility is organization, not execution.

---

# Development Workflow

```text
Clone Repository

↓

Create Virtual Environment

↓

Install Dependencies

↓

Configure .env

↓

Download Models

↓

Run Tests

↓

Start Backend

↓

Start Dashboard

↓

Begin Development
```

---

# Summary

The repository foundation establishes the organizational rules for AetherOS. By keeping configuration, documentation, infrastructure, scripts, assets, tests, logs, and persistent data clearly separated from business logic, the project remains clean, scalable, and easy to maintain as it grows.

---

## Next Part

**Part 2 — Core Project Structure**

We'll document every folder inside `core/` in detail, including:

* `orchestrator/`
* `planner/`
* `scheduler/`
* `workflow/`
* `event_bus/`
* `message_bus/`
* `task_queue/`
* `reasoning/`
* `state_manager/`
* `execution/`
* `retry/`

Every file in those folders will be explained with its exact responsibility, interactions, and recommended class structure.
