# DESKTOP.md

# AetherOS Desktop Automation Architecture

> **Purpose**
>
> The **Desktop** module is responsible for all interactions with the operating system. It provides human-like control over the mouse, keyboard, windows, clipboard, files, applications, and system resources while exposing a clean, platform-independent API to the Runtime and Agent layers.
>
> The Desktop module is the **hands** of AetherOS.

---

# Design Philosophy

The Desktop module should be:

* Human-like
* Reliable
* Modular
* Platform-independent
* Event-driven
* Verifiable
* Safe
* Extensible
* High-performance
* Async-compatible

---

# Responsibilities

The Desktop module is responsible for:

* Mouse control
* Keyboard control
* Window management
* Clipboard
* File operations
* Process management
* Application launching
* Screen information
* Monitor management
* Notifications
* Audio control
* Power management

The Desktop module **does not**:

* Perform AI reasoning
* Make decisions
* Execute workflows
* Read OCR
* Detect UI objects

Those responsibilities belong to the Agents, Runtime, and Vision modules.

---

# Architecture

```text
Agents
    │
    ▼
Runtime
    │
    ▼
Desktop API
    │
────────────────────────────────────
│ Mouse
│ Keyboard
│ Window
│ Clipboard
│ Process
│ Files
│ Audio
│ Monitor
│ Power
│ Notification
────────────────────────────────────
    │
Windows API / Linux API / macOS API
```

---

# Directory Structure

```text
desktop/
│
├── __init__.py
│
├── api/
│
├── mouse/
│
├── keyboard/
│
├── window/
│
├── clipboard/
│
├── monitor/
│
├── filesystem/
│
├── process/
│
├── application/
│
├── notification/
│
├── audio/
│
├── power/
│
├── automation/
│
├── verification/
│
├── recording/
│
├── permissions/
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

# Desktop API

Folder

```text
desktop/api/
```

Provides a unified interface for every controller.

Example

```python
desktop.mouse.move()

desktop.keyboard.type()

desktop.window.focus()

desktop.clipboard.copy()
```

No module should directly access controllers.

---

# Mouse Controller

Folder

```text
desktop/mouse/
```

Responsibilities

* Move cursor
* Relative movement
* Absolute movement
* Left click
* Right click
* Double click
* Middle click
* Drag
* Drop
* Scroll
* Smooth movement

Functions

```python
move()

move_relative()

click()

double_click()

drag()

drop()

scroll()

position()
```

Libraries

* PyAutoGUI
* Win32 API

---

# Keyboard Controller

Folder

```text
desktop/keyboard/
```

Responsibilities

* Type text
* Press key
* Hold key
* Hotkeys
* Key combinations
* Media keys

Functions

```python
press()

release()

hotkey()

type()

write()

copy()

paste()
```

Libraries

* keyboard
* pyautogui

---

# Window Manager

Folder

```text
desktop/window/
```

Responsibilities

* Find windows
* Focus
* Maximize
* Restore
* Minimize
* Resize
* Move
* Close

Functions

```python
find()

focus()

close()

maximize()

restore()

move()

resize()
```

Libraries

* pywin32
* pygetwindow

---

# Clipboard

Folder

```text
desktop/clipboard/
```

Responsibilities

* Copy
* Paste
* Read clipboard
* Clear clipboard
* Clipboard history

Libraries

* pyperclip

---

# File System

Folder

```text
desktop/filesystem/
```

Capabilities

* Read files
* Write files
* Copy
* Move
* Rename
* Delete
* Search
* Watch folders

Uses

* pathlib
* shutil
* watchdog

---

# Process Manager

Folder

```text
desktop/process/
```

Responsibilities

* Start processes
* Stop processes
* Kill processes
* Restart
* Monitor resource usage

Functions

```python
start()

stop()

restart()

kill()

running()

list()
```

Libraries

* psutil
* subprocess

---

# Application Manager

Folder

```text
desktop/application/
```

Responsibilities

* Launch applications
* Detect installation
* Open documents
* Associate file types
* Manage application lifecycle

Example

```python
launch("code")

launch("chrome")

launch("notepad")
```

---

# Monitor Manager

Folder

```text
desktop/monitor/
```

Responsibilities

* Detect displays
* Screen resolution
* DPI scaling
* Active monitor
* Multi-monitor support

Libraries

* screeninfo

---

# Audio Manager

Folder

```text
desktop/audio/
```

Responsibilities

* Change volume
* Mute
* Device selection
* Input device
* Output device

Libraries

* pycaw

---

# Notification Manager

Folder

```text
desktop/notification/
```

Responsibilities

* Toast notifications
* Progress updates
* Alerts
* Errors
* Workflow completion

---

# Power Manager

Folder

```text
desktop/power/
```

Capabilities

* Shutdown
* Restart
* Sleep
* Lock
* Hibernate

Safety

Requires confirmation unless explicitly authorized.

---

# Automation Layer

Folder

```text
desktop/automation/
```

Purpose

Combine multiple controllers into reusable desktop actions.

Example

```text
Launch VS Code

↓

Focus Window

↓

Open Folder

↓

Run Terminal

↓

Execute Command
```

---

# Verification Layer

Folder

```text
desktop/verification/
```

Responsibilities

Verify

* Mouse click succeeded
* Window focused
* Text entered
* Application opened
* File created

Methods

* Vision
* OCR
* Windows API
* Process checks

---

# Recording Module

Folder

```text
desktop/recording/
```

Capabilities

* Record mouse actions
* Record keyboard actions
* Save macros
* Replay workflows

Future

Convert recordings into reusable Skills.

---

# Permission Manager

Folder

```text
desktop/permissions/
```

Controls

* Allowed applications
* Restricted folders
* Dangerous operations
* Confirmation prompts

---

# Event System

Folder

```text
desktop/events/
```

Events

```text
MouseMoved

MouseClicked

WindowFocused

ClipboardChanged

ApplicationStarted

ProcessExited
```

---

# Models

Folder

```text
desktop/models/
```

Contains

* WindowInfo
* MousePosition
* ScreenInfo
* ProcessInfo
* FileInfo
* ClipboardData

---

# Utilities

Folder

```text
desktop/utils/
```

Provides

* Coordinate conversion
* DPI scaling
* Timing helpers
* Retry helpers
* Screen calculations

---

# Execution Flow

```text
Planner Agent

↓

Executor Agent

↓

Runtime

↓

Desktop API

↓

Controller

↓

Operating System

↓

Verification

↓

Result
```

---

# Technology Stack

| Component          | Technology            |
| ------------------ | --------------------- |
| Mouse Automation   | PyAutoGUI             |
| Keyboard Input     | keyboard              |
| Window Management  | pywin32 + pygetwindow |
| Clipboard          | pyperclip             |
| File Operations    | pathlib + shutil      |
| Process Management | psutil + subprocess   |
| Monitor Info       | screeninfo            |
| Audio Control      | pycaw                 |
| File Watching      | watchdog              |
| Async Execution    | asyncio               |

---

# Design Principles

1. Controllers should perform only one responsibility.
2. Desktop APIs must be platform-independent.
3. Every critical action should be verified.
4. Dangerous operations require explicit authorization.
5. Controllers should be stateless whenever possible.
6. Retry transient failures automatically.
7. Higher-level automation belongs in `desktop/automation`, not individual controllers.
8. All interactions should be logged for debugging and replay.

---

# Success Criteria

The Desktop module is complete when:

* ✅ Mouse and keyboard control are reliable.
* ✅ Windows can be managed programmatically.
* ✅ Applications launch and close correctly.
* ✅ File and process management work consistently.
* ✅ Multi-monitor environments are supported.
* ✅ Automation sequences can be composed from controllers.
* ✅ Verification confirms action success.
* ✅ Recording and replay support workflow automation.
* ✅ Platform-specific implementations remain hidden behind a unified API.

The **Desktop** module provides the **physical execution layer** of AetherOS. It converts high-level AI decisions into safe, verifiable operating system actions, allowing the rest of the platform to interact with the desktop through a clean and consistent interface.
