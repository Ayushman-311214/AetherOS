# 04_PROJECT_STRUCTURE.md

# Part 8 — Memory Project Structure

> **Purpose**
>
> The `memory/` module is the long-term knowledge system of AetherOS. It stores, retrieves, organizes, compresses, and evolves information gathered during execution, allowing the system to learn from previous experiences instead of starting from scratch every time.
>
> **Rule:** Memory stores knowledge. It never makes decisions. Reasoning belongs to the Agent layer.

---

# Memory Architecture

```text
                User Interaction
                       │
                       ▼
                Memory Manager
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
 Working Memory   Session Memory   Long-Term Memory
     │                 │                 │
     └─────────────────┼─────────────────┘
                       ▼
               Memory Retrieval
                       ▼
               Semantic Search
                       ▼
                Vector Database
                       ▼
              Embedding Pipeline
                       ▼
                  LLM Context
```

---

# Directory Structure

```text
memory/
│
├── __init__.py
│
├── working/
├── session/
├── long_term/
├── semantic/
├── episodic/
├── procedural/
├── vector_store/
├── embeddings/
├── retrieval/
├── ranking/
├── compression/
├── summarization/
├── indexing/
├── persistence/
├── forgetting/
├── synchronization/
├── analytics/
├── cache/
├── utils/
│
├── manager.py
├── interfaces.py
├── registry.py
├── config.py
├── constants.py
└── exceptions.py
```

---

# Memory Philosophy

Memory should answer:

* What happened previously?
* What did the user prefer?
* What tools worked?
* What failed?
* What should be remembered?
* What should be forgotten?
* What knowledge is relevant now?

Memory should **never**:

* Execute code
* Control desktop
* Plan workflows
* Make autonomous decisions

---

# Memory Layers

```text
Immediate Context
        │
        ▼
Working Memory
        │
        ▼
Session Memory
        │
        ▼
Long-Term Memory
        │
        ▼
Knowledge Archive
```

---

# 1. working/

Purpose

Stores temporary execution state.

---

Structure

```text
working/
│
├── manager.py
├── state.py
├── context.py
├── variables.py
└── cleanup.py
```

---

Stores

* Current task
* Current workflow
* Current desktop state
* Active windows
* Current tool outputs

Lifetime

Current workflow only.

---

# 2. session/

Purpose

Stores everything during one conversation/session.

---

Structure

```text
session/
│
├── manager.py
├── history.py
├── snapshots.py
├── summaries.py
└── expiration.py
```

---

Contains

* Conversation
* Executed Tasks
* Generated Reports
* User Commands
* Temporary Preferences

Destroyed after session ends unless promoted.

---

# 3. long_term/

Purpose

Permanent memory.

---

Structure

```text
long_term/
│
├── manager.py
├── storage.py
├── retrieval.py
├── update.py
├── archive.py
└── cleanup.py
```

---

Stores

* User Preferences
* Learned Workflows
* Stable Facts
* Frequent Commands
* Tool Statistics

---

# 4. semantic/

Purpose

Meaning-based knowledge retrieval.

---

Structure

```text
semantic/
│
├── search.py
├── similarity.py
├── clustering.py
├── ranking.py
└── embeddings.py
```

---

Example

Search

```text
Open browser
```

Returns

```text
Launch Chrome

Open Edge

Open Firefox
```

instead of exact text matching.

---

# 5. episodic/

Purpose

Store experiences.

---

Structure

```text
episodic/
│
├── events.py
├── timelines.py
├── replay.py
├── indexing.py
└── retrieval.py
```

---

Example

```text
Yesterday

↓

Opened TradingView

↓

Analyzed BTC

↓

Generated Report
```

Allows replaying past workflows.

---

# 6. procedural/

Purpose

Store learned procedures.

---

Structure

```text
procedural/
│
├── workflows.py
├── templates.py
├── automation.py
├── optimization.py
└── execution.py
```

---

Stores

* Login Workflow
* Report Workflow
* Browser Workflow
* Trading Workflow

Acts like "muscle memory."

---

# 7. vector_store/

Purpose

Store embeddings.

---

Structure

```text
vector_store/
│
├── chroma.py
├── faiss.py
├── qdrant.py
├── manager.py
└── indexing.py
```

---

Supported Backends

* ChromaDB
* FAISS
* Qdrant (future)

---

Responsibilities

* Similarity Search
* Vector Storage
* Fast Retrieval

---

# 8. embeddings/

Purpose

Generate embeddings.

---

Structure

```text
embeddings/
│
├── engine.py
├── bge.py
├── e5.py
├── nomic.py
├── openai.py
└── cache.py
```

---

Used for

* Semantic Search
* Ranking
* Context Retrieval

---

# 9. retrieval/

Purpose

Retrieve memories.

---

Structure

```text
retrieval/
│
├── search.py
├── filters.py
├── ranking.py
├── scoring.py
└── aggregator.py
```

---

Retrieval Pipeline

```text
Query

↓

Embedding

↓

Vector Search

↓

Ranking

↓

Filtering

↓

Top Results
```

---

# 10. ranking/

Purpose

Score memory importance.

---

Ranking Factors

* Similarity
* Age
* Frequency
* User Importance
* Confidence
* Recency

---

# 11. compression/

Purpose

Reduce memory size.

---

Structure

```text
compression/
│
├── summarizer.py
├── merge.py
├── deduplicate.py
└── optimizer.py
```

---

Example

100 conversations

↓

One summary

↓

Store summary

Delete duplicates

---

# 12. summarization/

Purpose

Generate summaries.

---

Types

* Daily
* Weekly
* Workflow
* Project
* Conversation

---

Example

```text
Today's Activity

Created Vision Module

Added OCR

Fixed Tool Registry

Implemented Desktop Controller
```

---

# 13. indexing/

Purpose

Fast retrieval.

---

Maintains indexes by

* User
* Project
* Topic
* Workflow
* Tags
* Date

---

# 14. persistence/

Purpose

Database layer.

---

Responsibilities

* Save Memory
* Load Memory
* Backup
* Restore

---

Supports

SQLite

PostgreSQL

Cloud Storage (future)

---

# 15. forgetting/

Purpose

Prevent unlimited memory growth.

---

Policies

* Time-based
* Frequency-based
* Confidence-based
* Duplicate Removal

---

Example

Unused memory

↓

Archive

↓

Delete after 6 months

---

# 16. synchronization/

Purpose

Synchronize memory.

---

Future

Desktop

Laptop

Cloud

Multiple Devices

---

# 17. analytics/

Purpose

Analyze stored memories.

---

Statistics

* Most Used Tools
* Common Commands
* Failure Patterns
* Workflow Frequency

---

# 18. cache/

Purpose

Fast access.

Stores

* Recent Retrievals
* Recent Embeddings
* Query Cache

---

# manager.py

Central controller.

Responsibilities

* Initialize memory
* Coordinate storage
* Manage retrieval
* Cleanup
* Synchronization

---

# registry.py

Registers

* Memory Providers
* Embedding Models
* Vector Stores
* Compression Strategies

---

# interfaces.py

Example

```python
class MemoryInterface:

    store()

    retrieve()

    update()

    delete()
```

---

# config.py

Example

```yaml
vector_database: chromadb

embedding_model: bge-large

working_memory_limit: 100

session_summary: true

compression: enabled
```

---

# constants.py

```python
MAX_WORKING_MEMORY = 100

MAX_SESSION_HISTORY = 500

SIMILARITY_THRESHOLD = 0.82
```

---

# exceptions.py

Contains

```text
MemoryNotFound

EmbeddingError

VectorStoreError

RetrievalError

CompressionError

PersistenceError
```

---

# Memory Lifecycle

```text
New Information
        │
        ▼
Working Memory
        │
        ▼
Session Memory
        │
        ▼
Embedding
        │
        ▼
Vector Store
        │
        ▼
Long-Term Memory
        │
        ▼
Compression
        │
        ▼
Archive
```

---

# Dependency Rules

Memory may use

* ChromaDB
* FAISS
* SQLite
* PostgreSQL
* Embedding Models

Memory must NOT import

* Desktop Controllers
* Browser Controllers
* Vision Controllers
* Agent Logic
* Workflow Planning

---

# Recommended Technologies

| Capability             | Technology    |
| ---------------------- | ------------- |
| Vector Database        | ChromaDB      |
| Secondary Vector Store | FAISS         |
| Embeddings             | BGE Large     |
| Database               | PostgreSQL    |
| Development Database   | SQLite        |
| Cache                  | Redis         |
| Serialization          | Pydantic      |
| Compression            | LLM Summaries |

---

# Future Roadmap

Future enhancements include:

* Knowledge Graph (Neo4j)
* Cross-project memory
* Automatic memory categorization
* Self-organizing knowledge
* Memory confidence scoring
* Lifelong learning
* Personalized user profiles
* Collaborative shared memory
* Temporal reasoning
* Memory versioning

---

# Summary

The `memory/` module serves as the persistent knowledge system of AetherOS. By organizing information into working, session, long-term, semantic, episodic, and procedural memories, it enables the system to recall relevant knowledge, learn from experience, optimize workflows, and provide context-aware reasoning. Its modular design ensures that storage, retrieval, compression, and synchronization evolve independently while supporting scalable and efficient AI memory management.

---

## Next Part

**Part 9 — `browser/` Project Structure**

We'll design the complete browser automation subsystem, including:

* Playwright architecture
* Browser lifecycle
* Tabs and windows
* Forms and authentication
* Downloads and uploads
* JavaScript execution
* Network interception
* Cookie/session management
* DOM understanding
* Browser verification
* Human-like browsing
* Multi-browser support

This module will become the web interaction layer of AetherOS.
