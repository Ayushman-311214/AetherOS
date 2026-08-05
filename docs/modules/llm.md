# LLM.md

# AetherOS Large Language Model (LLM) Architecture

> **Purpose**
>
> The **LLM** module is the cognitive engine of AetherOS. It provides a unified interface for interacting with multiple language models, manages prompts and context, performs tool calling, routes requests to the most appropriate model, and delivers structured AI reasoning to the rest of the system.
>
> The LLM module acts as the **thinking engine** that powers every intelligent decision inside AetherOS.

---

# Design Philosophy

The LLM module should be:

* Provider-independent
* Model-independent
* Modular
* Extensible
* Streaming-first
* Cost-aware
* Fast
* Fault tolerant
* Memory-aware
* Secure

---

# Responsibilities

The LLM module is responsible for:

* Provider abstraction
* Model routing
* Prompt management
* Context building
* Tool calling
* Function execution
* Structured output
* Streaming responses
* Conversation management
* Token estimation
* Cost tracking

The LLM module **does not**:

* Execute tools
* Store long-term memory
* Control the desktop
* Perform OCR
* Manage workflows

Those responsibilities belong to Runtime, Memory, Vision, and Agents.

---

# Architecture

```text
Agents

↓

Context Builder

↓

Prompt Manager

↓

Model Router

↓

LLM Provider

↓

Language Model

↓

Tool Calls / Response

↓

Runtime
```

---

# Directory Structure

```text
llm/
│
├── __init__.py
│
├── api/
│
├── providers/
│
├── models/
│
├── router/
│
├── prompts/
│
├── templates/
│
├── context/
│
├── conversation/
│
├── tools/
│
├── parser/
│
├── streaming/
│
├── embeddings/
│
├── tokenizer/
│
├── cache/
│
├── analytics/
│
├── registry/
│
├── verification/
│
├── events/
│
├── utils/
│
└── tests/
```

---

# LLM API

Folder

```text
llm/api/
```

Responsibilities

Provide a single interface for all AI interactions.

Example

```python
llm.chat()

llm.complete()

llm.stream()

llm.embed()

llm.call_tools()
```

Higher-level modules never communicate directly with providers.

---

# Provider Layer

Folder

```text
llm/providers/
```

Responsibilities

Connect to different providers.

Supported

* OpenAI
* Anthropic
* Google Gemini
* OpenRouter
* Ollama
* Groq
* Together AI
* Azure OpenAI
* Local Models

Every provider implements

```python
generate()

stream()

embeddings()

models()
```

---

# Model Registry

Folder

```text
llm/models/
```

Stores

* Model metadata
* Context length
* Pricing
* Speed
* Capabilities

Example

```text
GPT-5

Claude

Gemini

Qwen

Llama

DeepSeek

Mistral
```

---

# Model Router

Folder

```text
llm/router/
```

Responsibilities

Automatically choose the best model.

Decision Factors

* Cost
* Speed
* Accuracy
* Context length
* Tool support
* Vision capability

Example

```text
Simple Question

↓

Small Model

----------------

Coding Task

↓

GPT-5

----------------

Vision Task

↓

Gemini Vision
```

---

# Prompt Manager

Folder

```text
llm/prompts/
```

Stores

* System prompts
* Agent prompts
* Tool prompts
* Workflow prompts

Supports

* Versioning
* Variables
* Templates

---

# Prompt Templates

Folder

```text
llm/templates/
```

Template Example

```text
System Prompt

↓

User Goal

↓

Memory

↓

Current Screen

↓

Available Tools

↓

Expected Output
```

Engine

* Jinja2

---

# Context Builder

Folder

```text
llm/context/
```

Responsibilities

Build optimized context.

Sources

* User message
* Session memory
* Long-term memory
* Vision
* Runtime state
* Active workflow

Pipeline

```text
Memory

↓

Vision

↓

Workflow

↓

Prompt

↓

LLM
```

---

# Conversation Manager

Folder

```text
llm/conversation/
```

Stores

* Message history
* Roles
* Context windows
* Token usage

Supports

* Truncation
* Compression
* Summarization

---

# Tool Calling

Folder

```text
llm/tools/
```

Responsibilities

Generate tool calls.

Example

```python
Mouse.move()

Browser.open()

Vision.find_text()

Memory.search()
```

Only generates calls.

Runtime executes them.

---

# Structured Output Parser

Folder

```text
llm/parser/
```

Converts model output into

* JSON
* Pydantic Models
* Dataclasses
* Workflow objects

Supports

* Validation
* Retry on invalid output

---

# Streaming Engine

Folder

```text
llm/streaming/
```

Supports

* Token streaming
* Partial responses
* Live tool execution
* Interruptions

---

# Embedding Manager

Folder

```text
llm/embeddings/
```

Responsibilities

Generate embeddings.

Supported

* OpenAI
* BGE
* Nomic
* Ollama
* Sentence Transformers

---

# Tokenizer

Folder

```text
llm/tokenizer/
```

Responsibilities

* Count tokens
* Estimate costs
* Split context
* Optimize prompts

---

# Cache

Folder

```text
llm/cache/
```

Stores

* Prompt cache
* Response cache
* Embeddings
* Tool schemas

Future

* Redis

---

# Analytics

Folder

```text
llm/analytics/
```

Tracks

* Token usage
* Cost
* Latency
* Provider performance
* Cache hit ratio
* Success rate

---

# Registry

Folder

```text
llm/registry/
```

Registers

* Providers
* Models
* Prompt templates
* Tool schemas

Supports

Dynamic discovery.

---

# Verification

Folder

```text
llm/verification/
```

Verifies

* JSON validity
* Tool schema
* Hallucination checks
* Structured output

---

# Events

Folder

```text
llm/events/
```

Events

```text
PromptBuilt

ModelSelected

ResponseGenerated

ToolRequested

StreamingStarted

StreamingFinished
```

---

# Utilities

Folder

```text
llm/utils/
```

Provides

* Retry logic
* Cost estimation
* Prompt formatting
* Response cleaning
* Model helpers

---

# LLM Execution Flow

```text
User Goal

↓

Context Builder

↓

Prompt Manager

↓

Model Router

↓

Provider

↓

LLM

↓

Tool Calls

↓

Runtime

↓

Final Response
```

---

# Technology Stack

| Component         | Technology                                          |
| ----------------- | --------------------------------------------------- |
| LLM Interface     | Custom Provider Abstraction                         |
| Providers         | OpenAI, Anthropic, Gemini, OpenRouter, Ollama, Groq |
| Prompt Templates  | Jinja2                                              |
| Structured Output | Pydantic                                            |
| Token Counting    | tiktoken / provider tokenizer                       |
| Embeddings        | BGE, Nomic, OpenAI                                  |
| Streaming         | Async Generators                                    |
| Validation        | Pydantic                                            |
| Async Runtime     | asyncio                                             |

---

# Design Principles

1. Never tie the system to a single provider.
2. Separate providers from models.
3. Route requests intelligently.
4. Keep prompts versioned and reusable.
5. Build context dynamically from memory and vision.
6. Generate tool calls, but never execute them inside the LLM module.
7. Validate every structured response.
8. Track cost, latency, and token usage for optimization.

---

# Success Criteria

The LLM module is complete when:

* ✅ Multiple providers can be used interchangeably.
* ✅ Model routing selects the optimal model automatically.
* ✅ Prompts are modular and version-controlled.
* ✅ Context is built from memory, vision, and runtime state.
* ✅ Tool calls are generated using structured schemas.
* ✅ Streaming responses work reliably.
* ✅ Structured outputs are validated automatically.
* ✅ Token usage and costs are monitored.
* ✅ Higher-level modules use a single unified LLM API.

The **LLM** module is the **reasoning interface** of AetherOS. It connects the platform to language models while remaining completely provider-agnostic, enabling intelligent planning, tool generation, structured reasoning, and adaptive AI behavior across the entire operating system.
