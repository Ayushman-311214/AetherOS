# DATABASE.md

# AetherOS Database Architecture

> **Purpose**
>
> The **Database** module is the persistent storage layer of AetherOS. It manages structured data, vector embeddings, workflow history, user preferences, analytics, logs, trading records, and system configuration while providing reliable, scalable, and secure data access for every module.
>
> The Database module is the **persistent storage backbone** of AetherOS.

---

# Design Philosophy

The Database module should be:

* Reliable
* Modular
* Scalable
* Transaction-safe
* Secure
* Fast
* Extensible
* Backup-friendly
* Query optimized
* Storage independent

---

# Responsibilities

The Database module is responsible for:

* Persistent storage
* CRUD operations
* Transactions
* Vector storage
* Metadata storage
* Backup & Restore
* Database migrations
* Index management
* Connection pooling
* Data validation
* Query optimization

The Database module **does not**:

* Execute AI models
* Perform reasoning
* Control desktop
* Execute workflows
* Process OCR

---

# Architecture

```text id="c5yw2l"
Modules

↓

Repository Layer

↓

ORM

↓

Database Manager

↓

SQLite / PostgreSQL

↓

Disk Storage
```

---

# Directory Structure

```text id="q0s6vv"
database/
│
├── __init__.py
│
├── api/
│
├── manager/
│
├── connection/
│
├── repositories/
│
├── models/
│
├── schemas/
│
├── migrations/
│
├── queries/
│
├── indexes/
│
├── vector/
│
├── cache/
│
├── backup/
│
├── restore/
│
├── analytics/
│
├── events/
│
├── utils/
│
└── tests/
```

---

# Database Manager

Folder

```text id="h7q6ca"
database/manager/
```

Responsibilities

* Initialize database
* Open connections
* Close connections
* Manage transactions
* Health checks

Acts as the central controller.

---

# Connection Manager

Folder

```text id="7n8jzf"
database/connection/
```

Responsibilities

* Connection pooling
* Retry failed connections
* Async connections
* Timeout handling

Supports

* SQLite
* PostgreSQL

Future

* MySQL

---

# Repository Layer

Folder

```text id="v67i4t"
database/repositories/
```

Purpose

Hide SQL from business logic.

Example

```python id="z7h6go"
UserRepository

MemoryRepository

WorkflowRepository

TradeRepository

LogRepository
```

Every module interacts through repositories.

---

# Database Models

Folder

```text id="5wjlwm"
database/models/
```

Contains

* User
* Memory
* Workflow
* Agent
* Trade
* Portfolio
* Settings
* Log
* Session
* Event

Uses SQLAlchemy ORM models.

---

# Schemas

Folder

```text id="gnd6y9"
database/schemas/
```

Contains

* Request schemas
* Response schemas
* Validation schemas

Technology

* Pydantic

---

# Migrations

Folder

```text id="hf1v9e"
database/migrations/
```

Responsibilities

* Create tables
* Update schema
* Rollback migrations
* Version tracking

Technology

* Alembic

---

# Query Layer

Folder

```text id="j5y8yf"
database/queries/
```

Stores reusable queries.

Examples

```text id="2wyjdn"
Recent Workflows

Most Used Tools

Today's Trades

Latest Memories

Agent Statistics
```

---

# Index Manager

Folder

```text id="zc7m8r"
database/indexes/
```

Creates indexes for

* User IDs
* Workflow IDs
* Memory IDs
* Trade IDs
* Timestamps
* Search fields

Purpose

Fast query performance.

---

# Vector Storage

Folder

```text id="cjlwm4"
database/vector/
```

Stores

* Embeddings
* Semantic memory
* Document vectors
* Workflow vectors

Technology

* ChromaDB

Future

* Qdrant
* Weaviate
* pgvector

---

# Cache Layer

Folder

```text id="6wjlwm"
database/cache/
```

Caches

* Frequent queries
* Session data
* Settings
* User profiles

Future

* Redis

---

# Backup System

Folder

```text id="uwjlwm"
database/backup/
```

Responsibilities

* Scheduled backups
* Manual backups
* Incremental backups
* Compression
* Encryption

Supports

```text id="ijlwm"
Daily

Weekly

Monthly
```

---

# Restore System

Folder

```text id="mjlwm"
database/restore/
```

Responsibilities

* Restore backups
* Validate integrity
* Rollback failed restores

Supports

Point-in-time recovery.

---

# Database API

Folder

```text id="ajlwm"
database/api/
```

Functions

```python id="bjlwm"
create()

read()

update()

delete()

backup()

restore()

transaction()

health()
```

All modules access storage through this API.

---

# Events

Folder

```text id="djlwm"
database/events/
```

Events

```text id="ejlwm"
DatabaseConnected

MigrationCompleted

BackupCreated

RestoreCompleted

TransactionCommitted

TransactionRolledBack
```

---

# Analytics

Folder

```text id="fjlwm"
database/analytics/
```

Measures

* Query latency
* Transaction count
* Cache hit ratio
* Storage growth
* Connection usage
* Backup duration

---

# Utilities

Folder

```text id="gjlwm"
database/utils/
```

Provides

* Connection helpers
* Query builders
* Serialization
* Encryption helpers
* Pagination utilities

---

# Database Design

## Core Tables

```text id="hjlwm"
users

sessions

agents

workflows

workflow_steps

memories

documents

embeddings

tools

logs

events

settings

tasks

notifications

trades

orders

positions

portfolio

analytics
```

---

# Entity Relationships

```text id="ijjlwm"
User

│

├── Sessions

├── Workflows

├── Memories

├── Settings

├── Notifications

└── Trades

Trades

├── Orders

├── Positions

└── Journal
```

---

# Transaction Flow

```text id="jjlwm"
API Request

↓

Repository

↓

Transaction

↓

Database

↓

Commit

↓

Response
```

Rollback occurs automatically if an error is detected.

---

# Database Technologies

| Component           | Technology              |
| ------------------- | ----------------------- |
| ORM                 | SQLAlchemy 2.0          |
| Primary Database    | SQLite (Development)    |
| Production Database | PostgreSQL              |
| Migrations          | Alembic                 |
| Validation          | Pydantic                |
| Vector Database     | ChromaDB                |
| Cache               | Redis (Future)          |
| Connection Pool     | SQLAlchemy Async Engine |
| Serialization       | JSON                    |
| Async Runtime       | asyncio                 |

---

# Integration With Other Modules

| Module    | Database Usage                      |
| --------- | ----------------------------------- |
| Memory    | Long-term storage and vector search |
| Runtime   | Workflow state                      |
| Planner   | Saved execution plans               |
| Agents    | Agent configuration                 |
| Dashboard | Analytics and monitoring            |
| Trading   | Orders, positions, journal          |
| Browser   | Browser sessions and history        |
| Desktop   | Automation history                  |
| Vision    | OCR history and cached detections   |
| LLM       | Prompt history and token usage      |

---

# Design Principles

1. Separate business logic from SQL.
2. Use repositories instead of raw queries.
3. Keep database engines replaceable.
4. Every table should have indexes where appropriate.
5. Support migrations from day one.
6. Back up data automatically.
7. Store vectors separately from relational data.
8. Keep all database access asynchronous.

---

# Success Criteria

The Database module is complete when:

* ✅ Persistent storage is available for all core modules.
* ✅ SQLAlchemy repositories abstract database operations.
* ✅ SQLite supports development and PostgreSQL supports production.
* ✅ Alembic manages schema migrations.
* ✅ ChromaDB stores vector embeddings.
* ✅ Automated backup and restore mechanisms are implemented.
* ✅ Query performance is optimized through indexing.
* ✅ Analytics monitor database health and performance.
* ✅ A unified Database API provides consistent access across AetherOS.

The **Database** module is the **persistent storage foundation** of AetherOS. It combines relational storage, vector databases, repository abstractions, migrations, backups, and analytics to provide a reliable, scalable, and maintainable data layer for every intelligent subsystem in the platform.
