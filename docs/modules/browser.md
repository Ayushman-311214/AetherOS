# BROWSER.md

# AetherOS Browser Automation Architecture

> **Purpose**
>
> The **Browser** module enables AetherOS to interact with web applications as a human would, while taking advantage of browser automation capabilities whenever possible. It provides reliable, high-performance automation through **DOM interaction, Accessibility APIs, and Vision-based fallback**, making it capable of automating nearly any website.

The Browser module is the **web execution layer** of AetherOS.

---

# Design Philosophy

The Browser module should be:

- Fast
- Reliable
- Human-like
- Verifiable
- Multi-browser
- Secure
- Session-aware
- Async-first
- Extensible
- Cross-platform

---

# Responsibilities

The Browser module is responsible for:

- Browser lifecycle
- Page navigation
- DOM interaction
- Form automation
- Authentication
- Downloads & uploads
- Cookie management
- Session persistence
- Screenshots
- Browser verification

The Browser module **does not**:

- Perform AI reasoning
- Execute desktop automation
- Store long-term memory
- Analyze OCR
- Plan workflows

---

# Architecture

```text
Agents
    │
    ▼
Runtime
    │
    ▼
Browser API
    │
─────────────────────────────────────────────
│ Browser │ Context │ DOM │ Network │ Storage │
─────────────────────────────────────────────
    │
Playwright Runtime
    │
Chromium / Chrome / Edge / Firefox
```

---

# Directory Structure

```text
browser/
│
├── __init__.py
│
├── api/
│
├── core/
│
├── contexts/
│
├── pages/
│
├── tabs/
│
├── navigation/
│
├── dom/
│
├── selectors/
│
├── javascript/
│
├── cookies/
│
├── storage/
│
├── downloads/
│
├── uploads/
│
├── screenshots/
│
├── network/
│
├── authentication/
│
├── accessibility/
│
├── verification/
│
├── automation/
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

# Browser Runtime

Folder

```text
browser/core/
```

Responsibilities

- Launch browser
- Close browser
- Restart browser
- Headless mode
- Headed mode
- Persistent profiles

Supported Browsers

- Chromium
- Google Chrome
- Microsoft Edge
- Firefox

Technology

- Playwright

---

# Browser Contexts

Folder

```text
browser/contexts/
```

Responsibilities

- Create contexts
- Isolated sessions
- Multiple users
- Permission management
- Session persistence

Example

```text
Context 1 → Gmail

Context 2 → TradingView

Context 3 → GitHub
```

---

# Page Manager

Folder

```text
browser/pages/
```

Responsibilities

- Active page
- Page history
- URL tracking
- Lifecycle events
- Loading status

---

# Tab Manager

Folder

```text
browser/tabs/
```

Functions

```python
new_tab()

close_tab()

switch_tab()

duplicate_tab()

list_tabs()
```

Supports unlimited browser tabs.

---

# Navigation Engine

Folder

```text
browser/navigation/
```

Functions

```python
goto()

back()

forward()

reload()

refresh()

wait_for_load()

wait_until_network_idle()
```

Capabilities

- Smart waiting
- Redirect handling
- Timeout recovery

---

# DOM Engine

Folder

```text
browser/dom/
```

Responsibilities

- Click
- Fill forms
- Read text
- Select dropdowns
- Checkbox handling
- Radio buttons
- Hover
- Drag & Drop

Methods

```python
click()

fill()

text()

exists()

hover()

drag()
```

---

# Selector Engine

Folder

```text
browser/selectors/
```

Supports

- CSS
- XPath
- Text
- ARIA
- Role
- Label
- Placeholder
- Test IDs

Priority

```text
ARIA

↓

Role

↓

CSS

↓

XPath
```

---

# JavaScript Engine

Folder

```text
browser/javascript/
```

Responsibilities

Execute JavaScript safely.

Functions

```python
evaluate()

inject()

wait_function()

scroll()
```

---

# Authentication

Folder

```text
browser/authentication/
```

Supports

- Login automation
- MFA workflow support
- Session reuse
- Cookie restoration
- OAuth flows

---

# Cookie Manager

Folder

```text
browser/cookies/
```

Responsibilities

- Save cookies
- Restore cookies
- Delete cookies
- Export cookies

---

# Storage Manager

Folder

```text
browser/storage/
```

Supports

- Local Storage
- Session Storage
- IndexedDB (future)

---

# Download Manager

Folder

```text
browser/downloads/
```

Responsibilities

- Track downloads
- Rename files
- Verify completion
- Resume downloads

---

# Upload Manager

Folder

```text
browser/uploads/
```

Responsibilities

- File upload
- Multiple uploads
- Drag-and-drop uploads
- Directory uploads

---

# Screenshot Manager

Folder

```text
browser/screenshots/
```

Supports

- Full page
- Visible viewport
- Element screenshot
- Region screenshot

Formats

- PNG
- JPEG

---

# Network Manager

Folder

```text
browser/network/
```

Capabilities

- Intercept requests
- Block requests
- Modify headers
- Monitor traffic
- Capture responses

Useful for

- API testing
- Performance
- Debugging

---

# Accessibility Layer

Folder

```text
browser/accessibility/
```

Purpose

Use browser accessibility tree when DOM selectors are unreliable.

Benefits

- More resilient automation
- Better compatibility
- Improved UI understanding

---

# Verification Engine

Folder

```text
browser/verification/
```

Verify

- Element clicked
- Text entered
- Page loaded
- Download completed
- Login successful

Methods

- DOM verification
- Accessibility tree
- Screenshot comparison
- Vision fallback

---

# Automation Layer

Folder

```text
browser/automation/
```

Reusable workflows

Example

```text
Open Website

↓

Login

↓

Navigate Dashboard

↓

Download Report

↓

Logout
```

---

# Events

Folder

```text
browser/events/
```

Examples

```text
BrowserStarted

PageLoaded

DownloadFinished

UploadCompleted

NavigationFailed

LoginSucceeded
```

---

# Models

Folder

```text
browser/models/
```

Contains

- BrowserInfo
- PageInfo
- CookieData
- DownloadInfo
- UploadInfo
- ElementInfo

---

# Utilities

Folder

```text
browser/utils/
```

Provides

- URL helpers
- Retry logic
- Timeout helpers
- Cookie utilities
- Screenshot helpers

---

# Hybrid Automation Strategy

AetherOS always chooses the most reliable automation method.

```text
DOM Available?

↓

YES

↓

DOM Automation

──────────────

NO

↓

Accessibility Tree

──────────────

Still Not Found

↓

Vision Detection

↓

Desktop Click
```

Priority

1. DOM
2. Accessibility
3. Vision
4. Coordinate-based click

---

# Browser Execution Flow

```text
Planner Agent

↓

Executor Agent

↓

Runtime

↓

Browser API

↓

Playwright

↓

Website

↓

Verification

↓

Result
```

---

# Technology Stack

| Component            | Technology                      |
| -------------------- | ------------------------------- |
| Browser Automation   | Playwright                      |
| Browser Engines      | Chromium, Chrome, Edge, Firefox |
| JavaScript Execution | Playwright Evaluate API         |
| Network Interception | Playwright Route API            |
| Authentication       | Playwright Storage State        |
| Downloads            | Playwright Download API         |
| Screenshots          | Playwright Screenshot API       |
| Verification         | DOM + Vision + OCR              |
| Async Runtime        | asyncio                         |

---

# Design Principles

1. Prefer semantic selectors over XPath.
2. Always verify important actions.
3. Reuse browser contexts whenever possible.
4. Avoid fixed delays; use smart waits.
5. Keep browser sessions isolated.
6. Fall back to Vision only when DOM or Accessibility cannot complete the task.
7. Expose a single Browser API to higher-level modules.
8. Log every automation step for debugging and replay.

---

# Success Criteria

The Browser module is complete when:

- ✅ Multiple browsers are supported.
- ✅ Sessions persist across executions.
- ✅ DOM automation is reliable.
- ✅ Authentication workflows are reusable.
- ✅ Downloads and uploads are fully automated.
- ✅ Network requests can be monitored and intercepted.
- ✅ Verification confirms every important action.
- ✅ Hybrid DOM + Accessibility + Vision automation works seamlessly.
- ✅ Browser automation integrates cleanly with the Runtime and Agent systems.

The **Browser** module provides the **web interaction layer** of AetherOS. It combines modern browser automation with accessibility information and computer vision to execute reliable, human-like interactions across virtually any web application while exposing a clean API to the rest of the system.
