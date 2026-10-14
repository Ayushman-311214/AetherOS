# LOGGING.md

# AetherOS Logging & Observability Architecture

> **Purpose**
>
> The **Logging** module provides complete visibility into every action performed by AetherOS. It records system events, agent activities, API requests, workflows, desktop automation, browser interactions, AI reasoning, errors, and performance metrics to enable debugging, monitoring, auditing, and continuous improvement.
>
> The Logging module is the **observability system** of AetherOS.

---

# Design Philosophy

The Logging module should be:

* Structured
* Centralized
* Asynchronous
* Searchable
* Scalable
* Secure
* Low-overhead
* Real-time
* Extensible
* Audit-friendly

---

# Responsibilities

The Logging module is responsible for:

* Application logging
* Agent logging
* Runtime logging
* API logging
* Error tracking
* Performance monitoring
* Audit logging
* Event recording
* Log aggregation
* Log rotation
* Metrics collection
* Distributed tracing

The Logging module **does not**:

* Execute workflows
* Perform reasoning
* Store user memory
* Control desktop
* Execute automation

---

# Architecture

```text
Application

↓

Logger

↓

Event Bus

↓

Log Manager

↓

Storage

↓

Dashboard

↓

Analytics
```

---

# Directory Structure

```text
logging/
│
├── __init__.py
│
├── api/
│
├── manager/
│
├── logger/
│
├── handlers/
│
├── formatters/
│
├── filters/
│
├── audit/
│
├── metrics/
│
├── tracing/
│
├── exporters/
│
├── rotation/
│
├── storage/
│
├── dashboard/
│
├── analytics/
│
├── alerts/
│
├── events/
│
├── models/
│
├── utils/
│
└── tests/
```

---

# Log Manager

Folder

```text
logging/manager/
```

Responsibilities

* Initialize logging
* Configure handlers
* Manage log levels
* Dispatch logs
* Control retention
* Coordinate exporters

Acts as the central logging controller.

---

# Logger

Folder

```text
logging/logger/
```

Provides unified logging APIs.

Example

```python
logger.debug()

logger.info()

logger.warning()

logger.error()

logger.critical()

logger.exception()
```

Every module uses the same logger.

---

# Log Handlers

Folder

```text
logging/handlers/
```

Supported Handlers

* Console
* File
* JSON
* Database
* Dashboard
* Remote Server

Future

* Elasticsearch
* Loki
* Cloud Logging

---

# Log Formatters

Folder

```text
logging/formatters/
```

Formats

* Plain text
* JSON
* Colored console
* Structured logs

Example

```json
{
  "timestamp":"2026-08-05T12:30:15Z",
  "level":"INFO",
  "module":"planner",
  "event":"PlanCreated",
  "workflow_id":"wf_001"
}
```

---

# Filters

Folder

```text
logging/filters/
```

Filter by

* Log level
* Module
* Agent
* Workflow
* User
* Session
* Event type

---

# Audit Logs

Folder

```text
logging/audit/
```

Stores

* Login events
* Permission changes
* Configuration updates
* API access
* Trade execution
* Workflow execution

Audit logs cannot be modified.

---

# Metrics

Folder

```text
logging/metrics/
```

Collects

* CPU usage
* RAM usage
* GPU usage
* Token usage
* API latency
* Workflow duration
* Agent performance

---

# Distributed Tracing

Folder

```text
logging/tracing/
```

Tracks

```text
User Request

↓

Planner

↓

Reasoning

↓

Automation

↓

Runtime

↓

Completed
```

Each request receives a unique Trace ID.

---

# Exporters

Folder

```text
logging/exporters/
```

Exports logs to

* File
* Database
* Dashboard
* Remote API

Future

* Grafana Loki
* OpenTelemetry
* Elasticsearch

---

# Log Rotation

Folder

```text
logging/rotation/
```

Supports

* Daily rotation
* Weekly rotation
* File size rotation
* Compression
* Automatic cleanup

Example

```text
logs/

runtime.log

runtime.log.1

runtime.log.2.gz
```

---

# Storage

Folder

```text
logging/storage/
```

Stores

* Runtime logs
* Error logs
* Audit logs
* Metrics
* Event history

Development

* Files

Production

* PostgreSQL
* Loki
* Elasticsearch (Future)

---

# Dashboard Integration

Folder

```text
logging/dashboard/
```

Provides

* Live log viewer
* Search
* Filters
* Timeline
* Error tracking

Updates through WebSockets.

---

# Analytics

Folder

```text
logging/analytics/
```

Measures

* Error frequency
* API latency
* Workflow success rate
* Average execution time
* Agent performance
* System health

---

# Alerts

Folder

```text
logging/alerts/
```

Triggers alerts for

* Critical errors
* High CPU usage
* Memory leaks
* Failed workflows
* Security events
* Trading failures

Delivery

* Dashboard
* Email
* Discord
* Telegram

---

# Logging API

Folder

```text
logging/api/
```

Functions

```python
log()

debug()

info()

warning()

error()

critical()

exception()

trace()

metric()
```

Every module communicates only through this API.

---

# Events

Folder

```text
logging/events/
```

Events

```text
LogCreated

LogExported

AlertTriggered

MetricCollected

RotationCompleted

TraceFinished
```

---

# Models

Folder

```text
logging/models/
```

Contains

* LogEntry
* AuditEntry
* Metric
* Trace
* Alert
* LogFilter

---

# Utilities

Folder

```text
logging/utils/
```

Provides

* Time formatting
* Context injection
* Trace ID generation
* Correlation IDs
* Serialization helpers

---

# Log Levels

| Level    | Purpose                     |
| -------- | --------------------------- |
| TRACE    | Detailed execution flow     |
| DEBUG    | Development diagnostics     |
| INFO     | Normal application events   |
| SUCCESS  | Completed operations        |
| WARNING  | Recoverable issues          |
| ERROR    | Operation failures          |
| CRITICAL | System-threatening failures |

---

# Log Categories

```text
SYSTEM

API

RUNTIME

AGENTS

PLANNER

REASONING

MEMORY

VISION

DESKTOP

BROWSER

AUTOMATION

TRADING

DATABASE

SECURITY

DASHBOARD
```

---

# Logging Flow

```text
Application Event

↓

Logger

↓

Formatter

↓

Handler

↓

Storage

↓

Dashboard

↓

Analytics

↓

Alerts
```

---

# Technology Stack

| Component           | Technology                   |
| ------------------- | ---------------------------- |
| Logging Framework   | Loguru                       |
| Structured Logging  | JSON                         |
| Metrics             | Prometheus                   |
| Tracing             | OpenTelemetry                |
| Dashboard Streaming | WebSockets                   |
| File Rotation       | Loguru Rotation              |
| Storage             | Files + PostgreSQL           |
| Future Log Storage  | Grafana Loki / Elasticsearch |

---

# Integration With Other Modules

| Module    | Logging Purpose                     |
| --------- | ----------------------------------- |
| Runtime   | Task execution logs                 |
| Planner   | Plan creation and optimization      |
| Reasoning | Decision and reflection logs        |
| Memory    | Retrieval and storage events        |
| Vision    | OCR and detection logs              |
| Desktop   | Input actions and automation        |
| Browser   | Navigation and DOM events           |
| Trading   | Orders, positions, and signals      |
| API       | Requests, responses, authentication |
| Dashboard | Live log visualization              |
| Database  | Queries, transactions, migrations   |
| Security  | Authentication and audit events     |

---

# Design Principles

1. Every important action must generate a structured log.
2. Never log sensitive information such as passwords or API secrets.
3. Use correlation IDs to trace requests across modules.
4. Separate audit logs from operational logs.
5. Log asynchronously to minimize performance impact.
6. Rotate and archive logs automatically.
7. Make logs searchable and filterable.
8. Integrate metrics and traces with logs for full observability.

---

# Success Criteria

The Logging module is complete when:

* ✅ All modules use a unified logging API.
* ✅ Structured JSON logs are generated consistently.
* ✅ Runtime, API, agent, and workflow events are recorded.
* ✅ Distributed tracing links requests across modules.
* ✅ Metrics and logs are available in real time.
* ✅ Critical failures generate alerts automatically.
* ✅ Logs are rotated and archived automatically.
* ✅ Dashboard provides searchable live log visualization.
* ✅ Audit logs ensure accountability and security.

The **Logging** module is the **observability backbone** of AetherOS. It provides complete insight into system behavior through structured logs, metrics, traces, alerts, and analytics, enabling developers and users to monitor, debug, optimize, and audit every aspect of the autonomous operating system.

---

# Run Directories & Retention (implemented)

How the current build actually lays out a run's logs on disk, where traces
live, and how many runs are kept. Everything below is driven by
`aetheros.core.logging.handlers` / `logger.py` — the single logging entry
point. Do not call `logger.remove()`/`logger.add()`/`create_run_directory()`
from other modules; they are the one authoritative setup path.

## One run folder per process

A single AetherOS startup produces **exactly one** run directory, named with
the wall-clock timestamp **and the process id** so two startups in the same
second can never collide:

```text
logs/
└── run_YYYYMMDD_HHMMSS_<pid>/
    ├── app.log          # INFO+
    ├── error.log        # ERROR+ (backtraces, no variable dumps)
    ├── debug.log        # DEBUG+
    ├── events.jsonl     # structured, one JSON object per line
    └── traces/          # this run's trace/diagnostic artifacts
        └── <run_id>.jsonl
```

Initialization is **lazy and idempotent**. `get_logger(module)` lazily calls
`setup_logging()` on first use, which runs `configure_handlers()` once and
records the run in `_ACTIVE_RUN`. Every later `setup_logging()` call returns
the *same* run directory and reuses the existing sinks — repeated imports,
bootstrap components, services, or threads never mint a second folder and
never stack duplicate sinks. A module merely importing the logging package
creates **no** directory.

## Traces belong to the run

`trace_dir()` resolves to `<active_run>/traces`, derived from the live run
directory rather than a fresh timestamp. Trace/debug/diagnostic artifacts are
written beside the run's own logs — **never** a top-level `logs/traces/`
folder shared across runs. `TraceFileWriter` opens its per-run `.jsonl`
lazily on the first event, so an idle run leaves no empty file.

## Retention

After a new run folder is created, `cleanup_old_runs()` prunes the oldest
`run_*` directories so at most the configured count remains:

- **Default: 3 runs** (`LOG_RUNS_TO_KEEP = 3`).
- Configurable via `LOG_RETENTION_RUNS` (primary), `AETHEROS_LOG_RUNS_TO_KEEP`,
  or `LOG_RUNS_TO_KEEP` — all map to the same setting.
- The **live run is never deleted**, even if its mtime would sort it out of
  the newest-N (a long process can't age out its own folder).
- Only `run_*` folders under `LOG_DIR` are touched; nothing outside the
  run-log directories is removed. Retention applies after crashes/restarts
  too — a fresh startup re-evaluates the whole `logs/` tree.

## Console sink

The stderr console sink is **off by default** (the CLI renders its own UI;
interleaved log lines would corrupt it). `enable_console_logging()` /
`disable_console_logging()` toggle exactly that one sink idempotently — they
never re-run the file-sink setup or create a new run.

## Configuration keys

| Key | Default | Purpose |
|-----|---------|---------|
| `LOG_DIR` | `<root>/logs` | Root directory for all run folders |
| `LOG_LEVEL` | `INFO` | Console sink level |
| `LOG_ROTATION` | `10 MB` | Per-file rotation size |
| `LOG_COMPRESSION` | `zip` | Rotated-file compression |
| `LOG_RETENTION_RUNS` / `LOG_RUNS_TO_KEEP` | `3` | Completed run folders retained |
| `TRACE_LEVEL` | `verbose` | Live trace dashboard verbosity |
| `TRACE_PERSIST` | `False` | Persist each run's trace under `run_*/traces/` |

## Startup ordering

Logging initializes on the first `get_logger`/`setup_logging` call — early
enough to capture startup errors, but only ever once. Importing the bootstrap
or a service does not create a run; the folder appears when the first log
record is actually needed.
