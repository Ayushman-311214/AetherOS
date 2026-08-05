# DASHBOARD.md

# AetherOS Dashboard Architecture

> **Purpose**
>
> The **Dashboard** is the primary user interface for AetherOS. It provides real-time visibility into the operating system, allowing users to monitor AI agents, workflows, desktop automation, system resources, memory, trading activity, logs, and runtime state from a single centralized interface.
>
> The Dashboard acts as the **command center** of AetherOS.

---

# Design Philosophy

The Dashboard should be:

* Modern
* Real-time
* Responsive
* Modular
* Customizable
* Data-driven
* Interactive
* Extensible
* Lightweight
* Beautiful

---

# Responsibilities

The Dashboard is responsible for:

* Monitoring system status
* Visualizing workflows
* Managing AI agents
* Displaying runtime logs
* Monitoring resources
* Controlling automations
* Managing memory
* Viewing desktop state
* Monitoring trading activity
* Configuring settings

The Dashboard **does not**:

* Execute AI reasoning
* Store memories
* Perform automation
* Run desktop actions
* Process OCR

---

# Architecture

```text
Browser / Desktop App

↓

Dashboard Frontend

↓

REST API + WebSocket

↓

Runtime

↓

All Modules

↓

Real-Time Updates
```

---

# Directory Structure

```text
dashboard/
│
├── __init__.py
│
├── api/
│
├── frontend/
│
├── backend/
│
├── websocket/
│
├── pages/
│
├── widgets/
│
├── charts/
│
├── layouts/
│
├── themes/
│
├── settings/
│
├── notifications/
│
├── logs/
│
├── analytics/
│
├── authentication/
│
├── assets/
│
├── models/
│
├── events/
│
├── utils/
│
└── tests/
```

---

# Dashboard Backend

Folder

```text
dashboard/backend/
```

Responsibilities

* Serve dashboard data
* Handle API requests
* Authenticate users
* Stream updates
* Store UI preferences

Technology

* FastAPI

---

# Dashboard Frontend

Folder

```text
dashboard/frontend/
```

Responsibilities

* Render UI
* Display widgets
* Manage pages
* Handle user interactions

Technology

* React
* TypeScript
* Vite

---

# API Layer

Folder

```text
dashboard/api/
```

Provides

```python
/system

/agents

/workflows

/runtime

/memory

/trading

/settings

/logs
```

---

# WebSocket Server

Folder

```text
dashboard/websocket/
```

Streams

* Runtime updates
* Agent state
* Logs
* CPU usage
* Memory usage
* Trading data
* Notifications

Target latency

<100ms

---

# Dashboard Pages

Folder

```text
dashboard/pages/
```

Contains

```text
Home

Overview

Agents

Desktop

Vision

Memory

Runtime

Automation

Browser

Trading

Analytics

Logs

Settings
```

---

# Home Dashboard

Displays

* System status
* Active workflow
* Current task
* Active agents
* CPU
* RAM
* GPU
* Notifications

Example

```text
────────────────────────────

AetherOS

Running

CPU 18%

RAM 4.2GB

GPU 32%

Agents 5

Current Task

Analyzing BTC Chart

────────────────────────────
```

---

# Agent Monitor

Shows

* Active agents
* Current task
* Status
* Queue
* Response time

Example

```text
CEO Agent

Running

------------------

Vision Agent

Idle

------------------

Planner

Working

------------------

Trading Agent

Analyzing
```

---

# Runtime Monitor

Displays

* Running tasks
* Queue
* Events
* Threads
* Background jobs

Supports

Pause

Resume

Cancel

---

# Desktop Monitor

Shows

* Current screen
* Active window
* Mouse position
* Keyboard status
* Running applications

Future

Live desktop streaming.

---

# Vision Dashboard

Displays

* OCR results
* Detected UI
* Bounding boxes
* Scene graph
* Detection confidence
* Screen FPS

Useful for debugging.

---

# Memory Dashboard

Shows

* Session memory
* Long-term memory
* Knowledge graph
* Embeddings
* Recent memories

Supports

Search

Delete

Export

---

# Trading Dashboard

Displays

* Portfolio
* Open trades
* Signals
* Charts
* Risk
* Journal
* Performance

Widgets

```text
PnL

Balance

Win Rate

Open Positions

Daily Profit

Risk Exposure
```

---

# Workflow Dashboard

Displays

```text
Current Workflow

↓

Completed Tasks

↓

Current Task

↓

Remaining Tasks

↓

Progress
```

Supports

Visualization using DAG.

---

# Logs Viewer

Displays

* Runtime logs
* Agent logs
* Browser logs
* Desktop logs
* Errors
* Warnings

Features

* Search
* Filter
* Export

---

# Analytics Dashboard

Visualizes

* CPU usage
* Memory usage
* Token usage
* API costs
* Execution time
* Success rate
* Agent performance

Charts

* Line charts
* Bar charts
* Pie charts
* Heatmaps

---

# Widgets

Folder

```text
dashboard/widgets/
```

Reusable components

Examples

* CPU Widget
* GPU Widget
* Memory Widget
* Workflow Widget
* Trading Widget
* Notification Widget
* Clock Widget
* Agent Widget

---

# Layout System

Folder

```text
dashboard/layouts/
```

Supports

* Drag & Drop
* Resize
* Multiple layouts
* Saved layouts
* Custom dashboards

---

# Theme Engine

Folder

```text
dashboard/themes/
```

Themes

* Dark
* Light
* AMOLED
* Cyberpunk
* Glassmorphism

Supports

Custom themes.

---

# Notification Center

Folder

```text
dashboard/notifications/
```

Displays

* Errors
* Completed tasks
* Alerts
* Trading signals
* Downloads
* AI notifications

Priority

* Critical
* Warning
* Info

---

# Authentication

Folder

```text
dashboard/authentication/
```

Supports

* Local login
* OAuth
* API Keys
* Session management

Future

Multi-user support.

---

# Settings

Folder

```text
dashboard/settings/
```

Configure

* Models
* Providers
* Agents
* Themes
* API Keys
* Memory
* Desktop
* Trading
* Automation

---

# Dashboard API

Folder

```text
dashboard/api/
```

Functions

```python
get_system()

get_agents()

get_runtime()

get_memory()

get_trading()

get_logs()

get_settings()
```

---

# Events

Folder

```text
dashboard/events/
```

Events

```text
DashboardOpened

WidgetUpdated

WorkflowStarted

NotificationSent

ThemeChanged

SettingsUpdated
```

---

# Models

Folder

```text
dashboard/models/
```

Contains

* DashboardState
* Widget
* Notification
* Theme
* UserSettings
* Layout

---

# Analytics

Folder

```text
dashboard/analytics/
```

Measures

* UI FPS
* Response time
* API latency
* Widget rendering
* User interactions

---

# Utilities

Folder

```text
dashboard/utils/
```

Provides

* Chart helpers
* Formatting
* Theme helpers
* Widget utilities
* Export helpers

---

# Dashboard Execution Flow

```text
Runtime

↓

Events

↓

WebSocket

↓

Dashboard Backend

↓

Frontend

↓

Widgets

↓

User
```

---

# Technology Stack

| Component               | Technology                |
| ----------------------- | ------------------------- |
| Frontend                | React + TypeScript        |
| Build Tool              | Vite                      |
| UI Library              | Mantine / ShadCN UI       |
| Styling                 | Tailwind CSS              |
| Backend                 | FastAPI                   |
| Real-time Communication | WebSockets                |
| Charts                  | Recharts / Apache ECharts |
| State Management        | Zustand                   |
| Routing                 | React Router              |
| Authentication          | JWT / OAuth               |
| Icons                   | Lucide Icons              |
| Desktop Packaging       | Tauri (Future)            |

---

# Integration With Other Modules

| Module     | Purpose                                          |
| ---------- | ------------------------------------------------ |
| Runtime    | Live task execution status                       |
| Agents     | Agent monitoring and control                     |
| Desktop    | Active windows and input state                   |
| Vision     | OCR, UI detection, and scene graph visualization |
| Browser    | Browser sessions and automation status           |
| Memory     | Memory search and visualization                  |
| LLM        | Token usage, providers, and model statistics     |
| Planner    | Workflow visualization                           |
| Automation | Running workflows and schedules                  |
| Trading    | Portfolio, signals, and performance              |
| Security   | Authentication and permissions                   |

---

# Design Principles

1. Everything updates in real time.
2. Every module has its own dashboard page.
3. Widgets are reusable and configurable.
4. The interface should remain responsive under heavy workloads.
5. Critical alerts must always be visible.
6. Users should be able to customize layouts.
7. APIs and UI should remain independent.
8. Dashboard components communicate through events rather than direct coupling.

---

# Success Criteria

The Dashboard module is complete when:

* ✅ Real-time system monitoring is available.
* ✅ All core modules expose visual dashboards.
* ✅ Workflows and agents can be monitored live.
* ✅ Trading activity and analytics are visualized.
* ✅ Memory and logs are searchable.
* ✅ Notifications provide actionable updates.
* ✅ Layouts and themes are customizable.
* ✅ WebSocket updates keep the UI synchronized with the Runtime.
* ✅ A unified Dashboard API powers all frontend views.

The **Dashboard** module is the **command center** of AetherOS. It unifies operational monitoring, AI agent management, workflow visualization, analytics, and configuration into a single, extensible interface that gives users complete visibility and control over the entire autonomous operating system.
