# MEMORY.md

# AetherOS Memory Architecture

> **Purpose**
>
> The **Memory** module is the long-term intelligence system of AetherOS. It enables the operating system to remember users, conversations, workflows, documents, preferences, application states, learned behaviors, and past experiences.
>
> Unlike traditional chat history, the Memory module continuously organizes, ranks, compresses, retrieves, and learns from information to provide relevant context for future decisions.
>
> The Memory module is the **long-term brain** of AetherOS.

---

# Design Philosophy

The Memory module should be:

* Persistent
* Hierarchical
* Semantic
* Fast
* Modular
* Provider-independent
* Secure
* Self-learning
* Context-aware
* Scalable

---

# Responsibilities

The Memory module is responsible for:

* Session memory
* Long-term memory
* Semantic search
* Vector embeddings
* Knowledge graph
* User preferences
* Workflow memory
* Document memory
* Learning
* Memory ranking
* Context generation
* Memory compression

The Memory module **does not**:

* Execute workflows
* Control desktop
* Call LLMs directly
* Perform OCR
* Make planning decisions

---

# Architecture

```text id="grvh7u"
User

↓

Session Memory

↓

Memory Manager

↓

Vector Search

↓

Knowledge Graph

↓

Ranking Engine

↓

Context Builder

↓

Agents / LLM
```

---

# Directory Structure

```text id="nvv6kr"
memory/
│
├── __init__.py
│
├── api/
│
├── manager/
│
├── session/
│
├── long_term/
│
├── vector/
│
├── embeddings/
│
├── graph/
│
├── workflow/
│
├── documents/
│
├── preferences/
│
├── learning/
│
├── compression/
│
├── ranking/
│
├── retrieval/
│
├── storage/
│
├── cache/
│
├── analytics/
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

# Memory Manager

Folder

```text id="2gq5ml"
memory/manager/
```

Responsibilities

* Coordinate all memory systems
* Store new memories
* Retrieve memories
* Update records
* Delete memories
* Optimize storage

Acts as the central controller.

---

# Session Memory

Folder

```text id="i2l4m4"
memory/session/
```

Stores

* Active conversation
* Current workflow
* Temporary variables
* Runtime state
* Recent tool calls

Example

```text id="bapvq7"
Open VS Code

↓

Open Project

↓

Run Tests

↓

Generate Report
```

Lifetime

Current session only.

---

# Long-Term Memory

Folder

```text id="d4jqwl"
memory/long_term/
```

Stores

* User preferences
* Frequently used tools
* Learned workflows
* Historical conversations
* Application settings
* Custom instructions

Lifetime

Persistent.

---

# Vector Database

Folder

```text id="v5nblp"
memory/vector/
```

Purpose

Semantic similarity search.

Supported

* ChromaDB
* Qdrant (future)
* Weaviate (future)

Pipeline

```text id="sgh5bd"
Query

↓

Embedding

↓

Vector Search

↓

Top Results
```

---

# Embedding Engine

Folder

```text id="4ojh0y"
memory/embeddings/
```

Responsibilities

Generate embeddings for

* Conversations
* Documents
* Workflows
* Screens
* Notes

Models

* BGE-M3
* Nomic Embed
* OpenAI Embeddings
* Ollama Embeddings

---

# Knowledge Graph

Folder

```text id="btv3hz"
memory/graph/
```

Purpose

Store relationships.

Example

```text id="94lrlx"
Ayush

↓

Uses

↓

VS Code

↓

For

↓

Python

↓

Project

↓

AetherOS
```

Libraries

* NetworkX

Future

* Neo4j

---

# Workflow Memory

Folder

```text id="mv11hc"
memory/workflow/
```

Stores successful workflows.

Example

```text id="q9gl4v"
TradingView

↓

Open BTC

↓

15 Minute Chart

↓

Add Indicators

↓

Screenshot

↓

Analyze
```

Allows future reuse.

---

# Document Memory

Folder

```text id="4kp17g"
memory/documents/
```

Stores

* PDFs
* Markdown
* Notes
* Documentation
* Research papers
* Project files

Capabilities

* Chunking
* Embeddings
* Metadata
* Semantic retrieval

---

# User Preferences

Folder

```text id="s8fdgj"
memory/preferences/
```

Stores

* Favorite applications
* Preferred models
* Coding style
* Language
* Themes
* Frequently used workflows

Example

```text id="jlwmor"
Preferred IDE

↓

VS Code
```

---

# Learning Engine

Folder

```text id="jlwmn9"
memory/learning/
```

Learns from

* Successful tasks
* User corrections
* Reflection reports
* Repeated actions
* Failures

Produces

Improved future retrieval.

---

# Memory Compression

Folder

```text id="1u26cv"
memory/compression/
```

Pipeline

```text id="o2hy9j"
Conversation

↓

Summarization

↓

Embedding

↓

Archive
```

Benefits

* Smaller context
* Faster search
* Lower token usage

---

# Ranking Engine

Folder

```text id="60ztul"
memory/ranking/
```

Ranks memories using

* Similarity
* Importance
* Recency
* Frequency
* User preference

Formula

```text id="9rmbii"
Final Score

=

Similarity

+

Importance

+

Recency

+

Frequency
```

---

# Retrieval Engine

Folder

```text id="wkvqcv"
memory/retrieval/
```

Responsibilities

Retrieve

* Similar memories
* Related workflows
* User preferences
* Documents
* Knowledge graph nodes

Returns only relevant context.

---

# Storage Layer

Folder

```text id="jlwmqa"
memory/storage/
```

Stores

* Metadata
* Embeddings
* Documents
* Preferences
* Graph
* Session snapshots

Technologies

* SQLite
* PostgreSQL (future)

---

# Cache

Folder

```text id="i9syc8"
memory/cache/
```

Stores

* Recent queries
* Recent embeddings
* Frequently used memories

Future

* Redis

---

# Memory API

Folder

```text id="jlwmv2"
memory/api/
```

Functions

```python id="jlwmv3"
store()

retrieve()

search()

update()

delete()

summarize()

embed()

remember()

forget()
```

Every other module communicates only through this API.

---

# Events

Folder

```text id="jlwmv4"
memory/events/
```

Events

```text id="jlwmv5"
MemoryStored

MemoryUpdated

MemoryDeleted

RetrievalCompleted

CompressionFinished

LearningUpdated
```

---

# Models

Folder

```text id="jlwmv6"
memory/models/
```

Contains

* MemoryRecord
* WorkflowRecord
* UserPreference
* KnowledgeNode
* DocumentChunk
* EmbeddingRecord

---

# Analytics

Folder

```text id="jlwmv7"
memory/analytics/
```

Measures

* Retrieval latency
* Embedding time
* Storage growth
* Cache hit ratio
* Memory usage
* Ranking accuracy

---

# Utilities

Folder

```text id="jlwmv8"
memory/utils/
```

Provides

* Chunking helpers
* Embedding helpers
* Metadata utilities
* Similarity calculations
* Storage helpers

---

# Memory Execution Flow

```text id="jlwmv9"
User Request

↓

Retrieve Session Memory

↓

Retrieve Long-Term Memory

↓

Semantic Search

↓

Knowledge Graph

↓

Ranking

↓

Context Builder

↓

LLM

↓

Response

↓

Store New Memory
```

---

# Technology Stack

| Component        | Technology           |
| ---------------- | -------------------- |
| Vector Database  | ChromaDB             |
| Embedding Models | BGE-M3 / Nomic Embed |
| Graph Engine     | NetworkX             |
| Storage          | SQLite               |
| Future Storage   | PostgreSQL           |
| Validation       | Pydantic             |
| Cache            | Redis (future)       |
| Serialization    | JSON                 |
| Async Runtime    | asyncio              |

---

# Memory Hierarchy

```text id="jlwmwa"
Working Memory

↓

Session Memory

↓

Long-Term Memory

↓

Vector Memory

↓

Knowledge Graph

↓

Archived Memory
```

---

# Design Principles

1. Every memory must have metadata.
2. Store once, retrieve many times.
3. Never send all memories to the LLM.
4. Retrieve only relevant memories.
5. Separate session memory from persistent memory.
6. Compress old conversations automatically.
7. Learn from successful workflows.
8. Make every storage backend replaceable through interfaces.

---

# Success Criteria

The Memory module is complete when:

* ✅ Session memory tracks the active workflow.
* ✅ Long-term memory persists across sessions.
* ✅ Semantic search retrieves relevant information.
* ✅ Knowledge graph represents relationships.
* ✅ Workflow memory enables task reuse.
* ✅ User preferences personalize behavior.
* ✅ Memory compression reduces context size.
* ✅ Ranking returns the most relevant memories.
* ✅ New memories are learned continuously.
* ✅ All interactions occur through a unified Memory API.

The **Memory** module is the **persistent knowledge system** of AetherOS. It transforms conversations, documents, workflows, and user interactions into structured, searchable knowledge, allowing the platform to remember the past, personalize future behavior, and continuously improve through experience.
