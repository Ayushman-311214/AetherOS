# 04_PROJECT_STRUCTURE.md

# Part 5 — Desktop Project Structure

> **Purpose**
>
> The `desktop/` module is the execution layer responsible for controlling the operating system. It provides reliable, low-level access to the mouse, keyboard, windows, clipboard, files, audio, monitors, and system processes.
>
> It acts as the **hands** of AetherOS.

---

# Desktop Architecture

```text
                    Desktop Agent
                          │
                          ▼
                  Desktop Engine
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     Mouse          Keyboard          Window
        │                 │                 │
        ├──────────────┬──┴──────────────┬──┤
        │              │                 │
 Clipboard      Filesystem        Screen Capture
        │              │                 │
        ├──────────────┼─────────────────┤
        │              │                 │
 Process Manager   Audio Control   Accessibility
        │
        ▼
     Windows API
```

---

# Folder Structure

```text
desktop/
│
├── __init__.py
│
├── mouse/
├── keyboard/
├── window/
├── monitor/
├── clipboard/
├── filesystem/
├── process/
├── audio/
├── screenshot/
├── accessibility/
├── automation/
├── verification/
├── tools/
├── wrappers/
├── utils/
│
├── config.py
├── constants.py
├── exceptions.py
├── interfaces.py
├── registry.py
└── manager.py
```

---

# Desktop Design Principles

The Desktop module should:

- Be platform abstraction layer
- Hide OS-specific APIs
- Return structured results
- Verify every action
- Never contain AI reasoning
- Never communicate with LLMs
- Never know user goals

---

# 1. mouse/

Purpose

Complete mouse control.

---

Structure

```text
mouse/
│
├── controller.py
├── movement.py
├── click.py
├── drag.py
├── scroll.py
├── position.py
├── verification.py
├── calibration.py
└── utils.py
```

---

## controller.py

Public API.

Example

```python
mouse.move(500,300)

mouse.click()

mouse.drag()

mouse.scroll(-200)
```

All requests pass through this file.

---

## movement.py

Responsible for

- Absolute Move
- Relative Move
- Smooth Movement
- Bezier Movement
- Human-like Movement

Future

AI-generated natural mouse movement.

---

## click.py

Implements

- Left Click
- Right Click
- Double Click
- Triple Click
- Hold Click
- Release Click

---

## drag.py

Implements

- Drag
- Drag & Drop
- Selection
- Multi-step dragging

---

## scroll.py

Supports

- Vertical
- Horizontal
- Smooth scrolling

---

## position.py

Returns

```python
mouse.position()

mouse.screen_size()

mouse.monitor()
```

---

## verification.py

Confirms

Mouse actually moved.

Button clicked.

Cursor reached target.

---

# 2. keyboard/

Structure

```text
keyboard/
│
├── controller.py
├── typing.py
├── shortcuts.py
├── keys.py
├── clipboard.py
├── verification.py
└── layouts.py
```

---

Capabilities

Typing

Hotkeys

Key Hold

Release

Paste

Unicode

IME Support

---

Example

```python
keyboard.write("Hello")

keyboard.press("enter")

keyboard.hotkey("ctrl","c")
```

---

# 3. window/

Purpose

Manage application windows.

---

Structure

```text
window/
│
├── manager.py
├── search.py
├── focus.py
├── resize.py
├── position.py
├── state.py
├── screenshots.py
└── verification.py
```

---

Capabilities

Open

Close

Focus

Restore

Minimize

Maximize

Move

Resize

Enumerate

---

Example

```python
window.focus("Chrome")

window.maximize()

window.close()
```

---

# 4. monitor/

Purpose

Handle multiple monitors.

---

Structure

```text
monitor/
│
├── manager.py
├── resolution.py
├── scaling.py
├── coordinates.py
└── detection.py
```

Supports

- Multiple Displays
- DPI Scaling
- Resolution Detection
- Coordinate Translation

---

# 5. clipboard/

Purpose

Clipboard management.

---

Structure

```text
clipboard/
│
├── controller.py
├── text.py
├── images.py
├── files.py
└── history.py
```

Capabilities

Copy

Paste

Images

Files

Clipboard History

---

# 6. filesystem/

Purpose

Interact with files.

---

Structure

```text
filesystem/
│
├── read.py
├── write.py
├── copy.py
├── move.py
├── delete.py
├── search.py
├── watcher.py
└── metadata.py
```

Supports

- Read
- Write
- Rename
- Move
- Delete
- Watch Directories
- File Metadata

---

# 7. process/

Purpose

Manage operating system processes.

---

Structure

```text
process/
│
├── manager.py
├── launch.py
├── terminate.py
├── monitor.py
├── services.py
└── priority.py
```

Capabilities

Launch

Kill

Restart

Monitor

Service Management

---

Example

```python
process.start("chrome.exe")

process.kill("notepad.exe")
```

---

# 8. audio/

Purpose

Control system audio.

---

Structure

```text
audio/
│
├── volume.py
├── devices.py
├── microphone.py
├── speakers.py
└── sessions.py
```

Capabilities

Volume

Mute

Device Selection

Microphone Control

Audio Sessions

---

# 9. screenshot/

Purpose

Capture screen data.

---

Structure

```text
screenshot/
│
├── capture.py
├── region.py
├── window.py
├── monitor.py
└── recorder.py
```

Supports

- Full Screen
- Region
- Window
- Multi Monitor
- Screen Recording

---

# 10. accessibility/

Purpose

Access native accessibility APIs.

---

Structure

```text
accessibility/
│
├── ui_automation.py
├── elements.py
├── inspector.py
├── tree.py
└── search.py
```

Capabilities

- UI Tree
- Button Detection
- Text Extraction
- Native Controls
- Automation IDs

More reliable than OCR when available.

---

# 11. automation/

Purpose

Reusable desktop workflows.

---

Structure

```text
automation/
│
├── login.py
├── installer.py
├── explorer.py
├── startup.py
├── dialogs.py
└── workflows.py
```

Examples

Open Explorer

Save File

Open Application

Install Software

---

# 12. verification/

Purpose

Verify desktop actions.

---

Structure

```text
verification/
│
├── click.py
├── typing.py
├── movement.py
├── window.py
├── screenshot.py
└── comparison.py
```

Responsibilities

Verify

Mouse

Keyboard

Windows

Files

Screenshots

---

# 13. tools/

Purpose

Expose desktop functions as AI tools.

---

Structure

```text
tools/
│
├── mouse_tools.py
├── keyboard_tools.py
├── window_tools.py
├── clipboard_tools.py
├── process_tools.py
└── filesystem_tools.py
```

These are registered inside the LLM Tool Registry.

Example

```python
@tool
def move_mouse(x,y):
    ...
```

---

# 14. wrappers/

Purpose

Provide abstraction over third-party libraries.

---

Example

```text
wrappers/
│
├── pyautogui_wrapper.py
├── pywin32_wrapper.py
├── pygetwindow_wrapper.py
└── mss_wrapper.py
```

Why?

If PyAutoGUI changes, only the wrapper changes.

The rest of AetherOS remains untouched.

---

# 15. utils/

Contains reusable utilities.

Examples

```text
utils/
│
├── geometry.py
├── delays.py
├── random.py
├── validation.py
└── coordinates.py
```

No business logic belongs here.

---

# registry.py

Registers every desktop controller.

Example

```python
CONTROLLERS = {

"mouse":MouseController,

"keyboard":KeyboardController,

"window":WindowManager,

"clipboard":ClipboardController,

"filesystem":FilesystemController
}
```

---

# interfaces.py

Defines interfaces.

Example

```python
class MouseInterface:

    move()

    click()

    drag()

    scroll()
```

---

# manager.py

Central desktop manager.

Responsibilities

- Initialize controllers
- Share configuration
- Health monitoring
- Shutdown sequence

---

# config.py

Desktop configuration.

Example

```yaml
mouse: smooth:true

keyboard: typing_delay:0.03

verification: enabled:true
```

---

# exceptions.py

Contains

```text
MouseError

WindowNotFound

ClipboardError

PermissionDenied

FileOperationError
```

---

# constants.py

Example

```python
DOUBLE_CLICK_DELAY=0.2

DEFAULT_TIMEOUT=5

MAX_RETRY=3
```

---

# Desktop Execution Flow

```text
Planner

↓

Desktop Agent

↓

Desktop Engine

↓

Mouse Controller

↓

PyAutoGUI Wrapper

↓

Windows API

↓

Verification

↓

Result
```

---

# Dependency Rules

Desktop module may use

- pyautogui
- pywin32
- pygetwindow
- pyperclip
- psutil
- mss

Desktop module must NOT import

- Agents
- Planner
- LLM
- Memory
- Trading

---

# Recommended Libraries

| Capability         | Library      |
| ------------------ | ------------ |
| Mouse & Keyboard   | PyAutoGUI    |
| Windows API        | pywin32      |
| UI Automation      | UIAutomation |
| Clipboard          | pyperclip    |
| Process Management | psutil       |
| Screen Capture     | mss          |
| Window Management  | pygetwindow  |
| Image Matching     | OpenCV       |

---

# Summary

The `desktop/` module is the operating system interface of AetherOS. It provides a clean abstraction over low-level Windows APIs and automation libraries, enabling reliable interaction with the desktop while keeping implementation details hidden behind stable controllers and wrappers. Its strict separation from AI reasoning ensures that desktop automation remains deterministic, testable, and easily replaceable.

---

## Next Part

**Part 6 — `vision/` Project Structure**

This will cover:

- OCR
- Object Detection
- UI Detection
- Layout Analysis
- Chart Analysis
- Image Matching
- Screen Understanding
- Model Management
- Vision Pipelines
- Caching
- GPU Optimization
- Complete file-by-file architecture

This is one of the most advanced modules in AetherOS and forms the perception system of the entire platform.
