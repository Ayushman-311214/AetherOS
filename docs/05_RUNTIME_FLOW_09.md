# 05_RUNTIME_FLOW.md

# Part 9 — LLM Runtime Flow

> **Purpose**
>
> The LLM Runtime is the cognitive layer of AetherOS. It transforms user intent into structured reasoning by combining prompts, memory, vision, tools, and execution history before communicating with one or more Large Language Models.
>
> Unlike the Planner or Executor, the LLM Runtime **does not directly execute actions**. It is responsible for reasoning, decision-making, tool selection, and natural language understanding.

---

# Complete LLM Runtime

```text id="a1g9kz"
                  User Request
                        │
                        ▼
               Input Processor
                        │
                        ▼
               Context Builder
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
   Memory          Vision State      Runtime State
       │                │                │
       └────────────────┼────────────────┘
                        ▼
               Prompt Generator
                        │
                        ▼
               Model Router
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
     OpenAI        Anthropic       Local Models
        │               │                │
        └───────────────┼────────────────┘
                        ▼
              Response Parser
                        │
                        ▼
               Tool Dispatcher
                        │
                        ▼
             Planner / Executor
```

---

# LLM Philosophy

The LLM should

* Understand language
* Reason
* Plan
* Select tools
* Generate responses
* Analyze context

The LLM should never

* Move the mouse
* Execute controllers
* Modify the database
* Access the operating system directly

---

# LLM Runtime Pipeline

```text id="b7r2mw"
Input

↓

Context Assembly

↓

Prompt Generation

↓

Model Selection

↓

Inference

↓

Tool Calls

↓

Structured Output

↓

Planner
```

---

# Supported Providers

```text id="f6x8ny"
OpenAI

Anthropic

Google Gemini

OpenRouter

Groq

Ollama

LM Studio

vLLM

Future Providers
```

All providers are abstracted behind one interface.

---

# Provider Architecture

```text id="h3n4ut"
Planner

↓

LLM Manager

↓

Provider Adapter

↓

API

↓

Model
```

Every provider implements the same interface.

---

# Provider Interface

```python id="t5v7qa"
generate()

stream()

tool_call()

embeddings()

health()

models()
```

The Planner never communicates with providers directly.

---

# Model Router

Purpose

Choose the best model for the task.

Example

```text id="n8c2ke"
Coding

↓

DeepSeek

----------------

General Chat

↓

GPT

----------------

Reasoning

↓

Claude

----------------

Fast Tasks

↓

Groq
```

Routing is dynamic.

---

# Routing Factors

The router considers

* Cost
* Latency
* Accuracy
* Context length
* Tool support
* Model health
* User preferences

---

# Prompt Assembly

Prompt consists of

```text id="m9w4ds"
System Prompt

↓

Current Goal

↓

Relevant Memory

↓

Vision State

↓

Desktop State

↓

Conversation

↓

Tool Definitions

↓

Instructions
```

Everything is assembled dynamically.

---

# System Prompt

Contains

* AI identity
* Rules
* Capabilities
* Limitations
* Security policies

Example

```text id="r2p6lv"
You are the reasoning engine of AetherOS.
```

---

# Memory Injection

Memory Manager returns

* User preferences
* Relevant workflows
* Historical context
* Learned procedures

Only the highest-ranked memories are injected.

---

# Vision Injection

Vision contributes

* Current screen
* UI elements
* Active window
* OCR results
* Scene graph

Example

```text id="e7k5aj"
Current Window

VS Code

Cursor

main.py

Selected Text

42 lines
```

---

# Runtime Context

Additional runtime information

```text id="g5t8wr"
Current Task

Running Workflows

Available Tools

OS Status

Time

Permissions
```

---

# Token Budget Manager

Controls context size.

Pipeline

```text id="w1d6qm"
Context

↓

Estimate Tokens

↓

Trim

↓

Compress

↓

Send
```

Prevents context overflow.

---

# Context Compression

Large histories become summaries.

```text id="n6x3jo"
100 Pages

↓

Summary

↓

Prompt
```

Compression is automatic.

---

# Prompt Generation

Example

```text id="j4b9fv"
Identity

+

Goal

+

Memory

+

Vision

+

Tools

+

Conversation
```

↓

Final Prompt

---

# Inference

Pipeline

```text id="q8p2ha"
Prompt

↓

LLM

↓

Reasoning

↓

Response
```

The LLM does not directly access controllers.

---

# Tool Calling

Model may request tools.

Example

```json id="u2n5we"
{
    "tool":"open_browser",
    "arguments":{
        "url":"https://tradingview.com"
    }
}
```

Tool calls are parsed before execution.

---

# Tool Call Lifecycle

```text id="l9r7yb"
LLM

↓

Tool Request

↓

Validator

↓

Executor

↓

Verification

↓

Tool Result

↓

LLM
```

The model can perform multiple tool calls.

---

# Structured Output

Preferred format

```json id="d4k8zm"
{
    "reasoning":"...",

    "tool_calls":[...],

    "response":"..."
}
```

Never rely on plain text parsing.

---

# Streaming Runtime

Supports

```text id="k7y1pf"
Token

↓

Token

↓

Token

↓

Complete
```

Benefits

* Lower perceived latency
* Live UI updates

---

# Reflection Loop

Optional reasoning improvement.

Pipeline

```text id="x5m4sa"
Initial Answer

↓

Self Review

↓

Improve

↓

Final Answer
```

Used only for complex tasks.

---

# Self-Critique

Model checks

* Missing steps
* Logical errors
* Hallucinations
* Tool misuse

Planner receives improved output.

---

# Multi-Model Collaboration

Future architecture

```text id="p6c3vh"
Planner

↓

General Model

||

Reasoning Model

||

Vision Model

↓

Merge Results
```

Different models specialize in different domains.

---

# Fallback Runtime

If provider fails

```text id="v4h8lt"
Primary Model

↓

Unavailable

↓

Secondary Model

↓

Continue
```

Example

```text id="y1q5ok"
GPT

↓

Claude

↓

Ollama
```

---

# Provider Health Monitoring

Tracks

* Availability
* Latency
* Token limits
* Error rate
* Cost
* Context limits

Unhealthy providers are temporarily removed.

---

# Cost Optimizer

Chooses models intelligently.

Example

```text id="c2f9gw"
Simple Math

↓

Local Model

----------------

Research

↓

Claude

----------------

Coding

↓

GPT
```

Reduces API costs.

---

# Response Parser

Parses

* Tool calls
* JSON
* Structured outputs
* Markdown
* Errors

Invalid outputs trigger retries.

---

# Safety Layer

Before execution

Checks

* Policy compliance
* Tool permissions
* Dangerous requests
* Prompt integrity

Unsafe responses are blocked.

---

# Runtime Metrics

Collected

* Prompt size
* Completion size
* Token usage
* Latency
* Cost
* Tool calls
* Success rate
* Retry count

---

# Logging

Example

```text id="s8u3nx"
Prompt Generated

↓

Model Selected

↓

Tool Call Generated

↓

Response Parsed

↓

Completed
```

---

# Complete LLM Runtime Flow

```text id="f3r6kp"
User Request
      │
      ▼
Context Builder
      │
      ▼
Memory Injection
      │
      ▼
Vision Injection
      │
      ▼
Prompt Generator
      │
      ▼
Model Router
      │
      ▼
Provider
      │
      ▼
LLM
      │
      ▼
Tool Calls
      │
      ▼
Executor
      │
      ▼
Verification
      │
      ▼
Tool Results
      │
      ▼
LLM
      │
      ▼
Final Response
```

---

# Dependency Rules

LLM Runtime may depend on

* Provider adapters
* Prompt builder
* Memory Manager
* Vision Manager
* Tool Registry
* Model Router

LLM Runtime must **not** depend directly on

* Mouse Controller
* Keyboard Controller
* Browser Controller
* File System
* Database writes

All external actions are delegated.

---

# Recommended Technology Stack

| Component         | Technology                        |
| ----------------- | --------------------------------- |
| Provider SDK      | OpenAI SDK                        |
| Local Models      | Ollama / vLLM / LM Studio         |
| Prompt Templates  | Jinja2 / LangChain PromptTemplate |
| Structured Output | Pydantic                          |
| Streaming         | Server-Sent Events / WebSockets   |
| Token Counting    | tiktoken                          |
| Routing           | Custom Model Router               |
| Retry             | Tenacity                          |
| Caching           | Redis                             |
| Monitoring        | Langfuse / OpenTelemetry          |

---

# Future Enhancements

Planned improvements include:

* Hierarchical reasoning
* Tree-of-Thought execution
* Multi-agent debate
* Autonomous prompt optimization
* Long-context memory streaming
* Dynamic provider benchmarking
* Fine-tuned routing policies
* Speculative decoding
* On-device reasoning acceleration
* Self-improving prompt libraries

---

# Summary

The LLM Runtime is the reasoning core of AetherOS. It assembles context from memory, vision, runtime state, and tool definitions, selects the optimal model, generates structured reasoning, coordinates tool calls, and produces verified responses. By separating reasoning from execution and abstracting all model providers behind a unified interface, AetherOS remains scalable, provider-independent, and capable of leveraging both local and cloud-based language models efficiently.

---

## Next Part

**05_RUNTIME_FLOW.md — Part 10 — Error Recovery, Retry & Self-Healing Runtime**

Topics include:

* Error classification
* Retry engine
* Rollback manager
* Recovery planner
* Alternative tool selection
* Self-healing workflows
* Failure prediction
* Checkpoint and resume
* Circuit breakers
* Runtime resilience architecture
