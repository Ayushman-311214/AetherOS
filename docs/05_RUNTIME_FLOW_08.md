# 05_RUNTIME_FLOW.md

# Part 8 — Browser Runtime Flow

> **Purpose**
>
> The Browser Runtime enables AetherOS to autonomously interact with websites, web applications, dashboards, and cloud services. It provides reliable, secure, and verifiable browser automation while combining **DOM understanding**, **vision perception**, and **LLM reasoning**.
>
> Unlike traditional browser automation frameworks, the Browser Runtime is designed to behave like an intelligent human operator.

---

# Complete Browser Runtime

```text id="7kd31f"
                  Planner Agent
                        │
                        ▼
                 Executor Agent
                        │
                        ▼
                 Browser Engine
                        │
      ┌─────────────────┼──────────────────┐
      ▼                 ▼                  ▼
Navigation         DOM Runtime       Vision Runtime
      │                 │                  │
      └─────────────────┼──────────────────┘
                        ▼
                Browser Controller
                        │
                        ▼
                  Chromium Engine
                        │
                        ▼
                 Verification Layer
                        │
                        ▼
                Structured Response
```

---

# Browser Philosophy

Browser Runtime should

* Navigate websites
* Read web pages
* Fill forms
* Upload files
* Download files
* Verify actions
* Behave like a human

Browser Runtime should never

* Plan workflows
* Perform reasoning
* Store long-term memory
* Modify unrelated browser sessions

---

# Browser Lifecycle

```text id="w8j2na"
Launch

↓

Initialize Context

↓

Open Tab

↓

Navigate

↓

Interact

↓

Verify

↓

Close

↓

Cleanup
```

---

# Browser Components

```text id="k4o8ru"
Browser Manager

Context Manager

Tab Manager

DOM Runtime

Navigation Runtime

Network Runtime

Download Runtime

Upload Runtime

Cookie Manager

Storage Manager

Verification Runtime
```

---

# Browser Manager

Responsibilities

* Launch browser
* Close browser
* Manage instances
* Reuse sessions
* Resource cleanup

---

# Supported Browsers

Primary

* Chromium

Supported

* Chrome
* Edge
* Brave

Future

* Firefox
* Safari

---

# Browser Launch Pipeline

```text id="v5q9pe"
Launch Request

↓

Configuration

↓

Browser Process

↓

Context

↓

Ready
```

---

# Browser Context

Every workflow gets an isolated context.

Contains

* Cookies
* Local Storage
* Session Storage
* Permissions
* Cache

Contexts prevent workflow interference.

---

# Multi-Context Runtime

```text id="b7u4mk"
Workflow A

↓

Context A

----------------

Workflow B

↓

Context B

----------------

Workflow C

↓

Context C
```

Independent execution.

---

# Tab Runtime

Capabilities

* Create tab
* Close tab
* Switch tab
* Pin tab
* Duplicate tab
* Detect active tab

---

# Navigation Runtime

Pipeline

```text id="m3t6fz"
URL

↓

Navigate

↓

Wait

↓

DOM Ready

↓

Verification
```

Wait strategies

* DOM Loaded
* Network Idle
* Custom Event
* Timeout

---

# DOM Runtime

Reads page structure.

Extracts

* Buttons
* Links
* Forms
* Inputs
* Tables
* Text
* Images

Output

```json id="p9x4cv"
{
  "tag":"button",
  "text":"Login",
  "enabled":true
}
```

---

# DOM Query Engine

Supports

```text id="n2k8lr"
CSS Selectors

XPath

Text Search

ARIA Labels

Role Attributes
```

---

# Hybrid Runtime

Browser Runtime combines

```text id="g6r3ha"
DOM

+

Vision

+

LLM
```

Example

If DOM cannot find button

↓

Vision searches

↓

Planner continues

---

# Form Automation

Pipeline

```text id="y5v8ob"
Locate Form

↓

Fill Fields

↓

Validate

↓

Submit

↓

Verify
```

Supports

* Text fields
* Dropdowns
* Checkboxes
* Radio buttons
* Date pickers
* File uploads

---

# Authentication Runtime

Handles

* Login forms
* MFA workflows
* Session reuse
* Cookie restoration
* OAuth redirects

Future

Password vault integration.

---

# Download Runtime

Pipeline

```text id="r4n7we"
Download Request

↓

Monitor Progress

↓

Verify File

↓

Store Metadata
```

Tracks

* File name
* Size
* Path
* MIME type

---

# Upload Runtime

Pipeline

```text id="c8m1xy"
Locate Input

↓

Attach File

↓

Upload

↓

Verification
```

Supports

* Single file
* Multiple files
* Drag & drop (future)

---

# Network Runtime

Monitors

* Requests
* Responses
* Status codes
* Headers
* Redirects
* Errors

Useful for

* API debugging
* Authentication
* Verification

---

# Cookie Manager

Responsibilities

* Read cookies
* Write cookies
* Export
* Import
* Delete
* Expiration handling

---

# Local Storage Manager

Controls

* Local Storage
* Session Storage
* IndexedDB (future)

---

# Browser Events

Generated automatically.

Examples

```text id="q6z5uf"
Page Loaded

↓

Download Finished

↓

Popup Opened

↓

Navigation Failed

↓

Dialog Appeared
```

Planner subscribes.

---

# Popup Runtime

Detects

* Alerts
* Confirm dialogs
* Prompts
* Permission popups

Automatically routes to planner.

---

# Browser Vision Integration

If DOM fails

↓

Take Screenshot

↓

Vision Detection

↓

Locate UI

↓

Continue

This allows automation even on canvas-based applications.

---

# Verification Runtime

Every browser action is verified.

Navigation

```text id="d3j9ap"
Navigate

↓

Correct URL?

↓

Success
```

Click

```text id="x7b4lo"
Click

↓

DOM Changed?

↓

Success
```

Form

```text id="s5n2ki"
Submit

↓

Confirmation Visible?

↓

Success
```

---

# Retry Pipeline

If verification fails

```text id="f1r8ez"
Retry

↓

Alternative Selector

↓

Vision Detection

↓

Keyboard Navigation

↓

Failure
```

---

# Browser State

Maintains

```text id="u9m6qh"
Open Tabs

Current URL

Focused Element

Cookies

Downloads

History

Permissions
```

---

# Resource Management

Tracks

* RAM
* CPU
* Active tabs
* Idle tabs
* Network usage

Unused contexts are automatically closed.

---

# Security Rules

Browser Runtime cannot

* Access unauthorized websites
* Ignore security policies
* Leak cookies across contexts
* Execute unsafe scripts
* Bypass permission manager

---

# Runtime Metrics

Collected

* Page load time
* DOM query latency
* Click latency
* Download speed
* Upload speed
* Verification success
* Retry count
* Memory usage

---

# Technology Stack

| Component          | Technology                     |
| ------------------ | ------------------------------ |
| Browser Automation | Playwright                     |
| Browser Engine     | Chromium                       |
| DOM Parsing        | Playwright API                 |
| Network Monitoring | CDP (Chrome DevTools Protocol) |
| Vision Backup      | Vision Engine                  |
| Downloads          | Playwright Download API        |
| Uploads            | Playwright FileChooser API     |
| Authentication     | Playwright Contexts            |
| Storage            | Browser Context Storage        |

---

# Complete Browser Runtime Flow

```text id="t4k7yu"
Planner
      │
      ▼
Executor
      │
      ▼
Browser Engine
      │
      ▼
Browser Manager
      │
      ▼
Context Manager
      │
      ▼
Navigation
      │
      ▼
DOM Runtime
      │
      ▼
Vision Backup
      │
      ▼
Verification
      │
      ▼
Structured Result
      │
      ▼
Memory Update
```

---

# Future Enhancements

Future Browser capabilities include:

* Multi-browser orchestration
* Cloud browser execution
* CAPTCHA assistance workflows
* AI-powered web exploration
* Autonomous website mapping
* Browser extension management
* Persistent authenticated profiles
* Distributed browser clusters
* Mobile browser automation
* WebAssembly inspection

---

# Summary

The Browser Runtime is the web execution subsystem of AetherOS. It manages browser lifecycles, isolated contexts, navigation, DOM interaction, forms, authentication, downloads, uploads, and verification while seamlessly integrating with the Vision Runtime for applications that cannot be controlled through the DOM alone. This hybrid architecture enables robust, human-like automation across modern websites and complex web applications while maintaining security, isolation, and reliability.

---

## Next Part

**05_RUNTIME_FLOW.md — Part 9 — LLM Runtime Flow**

Topics include:

* Multi-provider architecture
* Prompt assembly pipeline
* Context injection
* Memory retrieval integration
* Tool calling lifecycle
* Model routing
* Streaming responses
* Structured output parsing
* Reflection and self-critique
* Cost and latency optimization
