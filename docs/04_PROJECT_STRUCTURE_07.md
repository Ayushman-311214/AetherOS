# 04_PROJECT_STRUCTURE.md

# Part 7 — LLM Project Structure

> **Purpose**
>
> The `llm/` module is the cognitive layer of AetherOS. It provides a unified interface for interacting with multiple language models, managing prompts, routing requests, executing tools, maintaining conversations, and generating structured outputs.
>
> It is designed to be **provider-agnostic**, allowing models to be swapped without changing the rest of the system.

---

# LLM Architecture

```text
                         Core
                           │
                           ▼
                     LLM Manager
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        Context Builder  Router    Prompt Manager
              │            │            │
              └────────────┼────────────┘
                           ▼
                     Provider Layer
      ┌──────────┬──────────┬──────────┬──────────┐
      ▼          ▼          ▼          ▼
   Ollama   OpenRouter   OpenAI    Gemini...
                           │
                           ▼
                    Tool Calling Layer
                           │
                           ▼
                     Structured Output
                           │
                           ▼
                      Core / Agents
```

---

# Directory Structure

```text
llm/
│
├── __init__.py
│
├── providers/
├── router/
├── prompts/
├── conversations/
├── context/
├── tools/
├── parser/
├── streaming/
├── embeddings/
├── memory/
├── cache/
├── tokenization/
├── models/
├── benchmarking/
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

# Design Principles

The LLM module should:

* Support multiple providers
* Support local + cloud models
* Be provider-independent
* Support tool calling
* Support structured outputs
* Manage conversations
* Inject memory automatically
* Handle retries and fallbacks
* Optimize latency and cost

---

# 1. providers/

Purpose

Every LLM provider has its own implementation.

---

Structure

```text
providers/
│
├── base_provider.py
├── ollama_provider.py
├── openai_provider.py
├── openrouter_provider.py
├── gemini_provider.py
├── groq_provider.py
├── claude_provider.py
└── mock_provider.py
```

---

Each provider implements:

```python
class BaseProvider:

    generate()

    stream()

    tool_call()

    embeddings()

    models()
```

---

Responsibilities

* API calls
* Authentication
* Error handling
* Streaming
* Tool calling
* Rate limiting

---

# 2. router/

Purpose

Automatically select the best model.

---

Structure

```text
router/
│
├── router.py
├── fallback.py
├── selector.py
├── latency.py
├── cost.py
├── health.py
└── policies.py
```

---

Example

```text
Simple Question

↓

Small Local Model

----------------------

Complex Coding

↓

Claude

----------------------

Vision Reasoning

↓

GPT-5

----------------------

Offline

↓

Ollama
```

---

Responsibilities

* Cost optimization
* Latency optimization
* Model fallback
* Provider health
* Dynamic routing

---

# 3. prompts/

Purpose

Central prompt management.

---

Structure

```text
prompts/
│
├── system/
├── agents/
├── tools/
├── workflows/
├── templates/
└── loaders.py
```

---

Example

```text
prompts/

system/

ceo.md

planner.md

vision.md

coding.md

research.md
```

---

Benefits

* Version control
* Easy editing
* Reusable prompts
* No hardcoded strings

---

# 4. conversations/

Purpose

Conversation lifecycle management.

---

Structure

```text
conversations/
│
├── manager.py
├── session.py
├── history.py
├── compression.py
├── summarizer.py
└── storage.py
```

---

Responsibilities

* Message history
* Session state
* Compression
* Context trimming
* Conversation summaries

---

# 5. context/

Purpose

Build model context.

---

Structure

```text
context/
│
├── builder.py
├── memory.py
├── desktop.py
├── vision.py
├── workflow.py
├── user.py
└── limits.py
```

---

Example Context

```text
System Prompt

↓

Memory

↓

Current Goal

↓

Desktop State

↓

Vision Result

↓

Conversation

↓

Tool Results
```

---

# 6. tools/

Purpose

Tool Calling System.

---

Structure

```text
tools/
│
├── registry.py
├── executor.py
├── validator.py
├── schemas.py
├── formatter.py
├── wrappers.py
└── discovery.py
```

---

Responsibilities

* Register tools
* Validate arguments
* Execute functions
* Return structured responses
* Retry failed tools

---

Example

```python
TOOLS = {

"move_mouse": move_mouse,

"capture_screen": capture_screen,

"search_memory": search_memory
}
```

---

# 7. parser/

Purpose

Convert model responses into structured objects.

---

Structure

```text
parser/
│
├── json_parser.py
├── markdown.py
├── xml.py
├── tool_calls.py
├── validator.py
└── repair.py
```

---

Supports

* JSON
* Markdown
* XML
* YAML
* Function Calls

---

Example

```json
{
  "tool":"move_mouse",
  "arguments":{
      "x":200,
      "y":400
  }
}
```

---

# 8. streaming/

Purpose

Real-time token streaming.

---

Structure

```text
streaming/
│
├── stream.py
├── websocket.py
├── events.py
├── handlers.py
└── buffer.py
```

---

Supports

* Live generation
* Token callbacks
* Streaming UI
* Interrupt generation

---

# 9. embeddings/

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
├── openai.py
├── nomic.py
└── cache.py
```

---

Used for

* Semantic Search
* Memory Retrieval
* Similarity Search
* Knowledge Ranking

---

# 10. memory/

Purpose

Bridge between LLM and Memory module.

---

Structure

```text
memory/
│
├── injector.py
├── retrieval.py
├── compression.py
├── ranking.py
└── summaries.py
```

---

Responsibilities

* Fetch relevant memories
* Compress context
* Rank memories
* Inject into prompts

---

# 11. cache/

Purpose

Reduce repeated LLM calls.

---

Stores

* Prompt cache
* Response cache
* Embedding cache
* Token statistics

---

Structure

```text
cache/
│
├── memory.py
├── redis.py
├── disk.py
└── eviction.py
```

---

# 12. tokenization/

Purpose

Track and optimize token usage.

---

Structure

```text
tokenization/
│
├── tokenizer.py
├── estimator.py
├── counter.py
├── truncation.py
└── budgeting.py
```

---

Responsibilities

* Token counting
* Context limits
* Cost estimation
* Prompt trimming

---

# 13. models/

Purpose

Model metadata.

---

Structure

```text
models/
│
├── registry.py
├── metadata.py
├── capabilities.py
├── pricing.py
└── availability.py
```

---

Tracks

* Context Window
* Vision Support
* Tool Calling
* Streaming
* Pricing
* Speed

---

# 14. benchmarking/

Purpose

Evaluate model performance.

---

Metrics

* Latency
* Cost
* Tokens
* Tool Accuracy
* JSON Accuracy
* Success Rate

---

# 15. utils/

Reusable helper functions.

Examples

```text
utils/

json.py

retry.py

timers.py

validators.py

formatting.py
```

---

# manager.py

Central entry point.

Responsibilities

* Initialize providers
* Load prompts
* Create sessions
* Route requests
* Execute tools
* Return structured results

---

# registry.py

Registers

* Providers
* Models
* Tools
* Prompt Templates

---

# interfaces.py

Defines contracts.

Example

```python
class LLMProvider:

    chat()

    stream()

    embeddings()

    tool_call()
```

---

# config.py

Example

```yaml
default_provider: ollama

default_model: qwen3

fallback_provider: openrouter

streaming: true

tool_calling: true

memory_enabled: true
```

---

# constants.py

```python
MAX_CONTEXT_TOKENS = 128000

MAX_TOOL_CALLS = 20

DEFAULT_TIMEOUT = 60
```

---

# exceptions.py

Contains

```text
ProviderUnavailable

ToolExecutionError

InvalidResponse

RateLimitExceeded

TokenLimitExceeded

StreamingError
```

---

# LLM Execution Flow

```text
User Goal
    │
    ▼
Context Builder
    │
    ▼
Memory Injection
    │
    ▼
Prompt Selection
    │
    ▼
Model Router
    │
    ▼
Provider
    │
    ▼
Tool Calls (Optional)
    │
    ▼
Parser
    │
    ▼
Structured Response
    │
    ▼
Core
```

---

# Dependency Rules

The LLM module may depend on:

* Memory
* Tool Registry
* Provider SDKs
* Tokenizers

The LLM module must **not** depend on:

* Desktop Controllers
* Vision Controllers
* Browser Controllers
* Agents
* Core Workflow Logic

Execution of tools should occur through well-defined interfaces, not direct imports of unrelated modules.

---

# Recommended Libraries

| Capability     | Library      |
| -------------- | ------------ |
| OpenAI API     | openai       |
| Ollama         | ollama       |
| Google Gemini  | google-genai |
| Anthropic      | anthropic    |
| Groq           | groq         |
| Token Counting | tiktoken     |
| Validation     | Pydantic     |
| Templates      | Jinja2       |
| Async HTTP     | httpx        |

---

# Future Roadmap

Future capabilities include:

* Mixture-of-Experts routing
* Multi-model parallel reasoning
* Self-reflection loops
* Automatic prompt optimization
* Dynamic tool discovery
* Model fine-tuning support
* On-device specialized models
* Agent-to-agent LLM communication
* Autonomous prompt evolution

---

# Summary

The `llm/` module is the intelligence gateway of AetherOS. It abstracts multiple language model providers behind a unified interface, manages prompts, conversations, tool calling, context construction, memory integration, and structured parsing. Its modular design ensures that new models or providers can be added with minimal impact on the rest of the architecture while enabling scalable, reliable, and cost-efficient AI reasoning.

---

## Next Part

**Part 8 — `memory/` Project Structure**

We'll design the complete memory architecture of AetherOS, including:

* Working Memory
* Short-Term Memory
* Long-Term Memory
* Semantic Memory
* Episodic Memory
* Vector Database
* Knowledge Graph
* Memory Retrieval
* Memory Compression
* Forgetting Strategies
* Embeddings Pipeline
* Learning Integration

This module will function as the persistent knowledge system for AetherOS.
