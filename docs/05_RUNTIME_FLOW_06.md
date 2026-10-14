# 05_RUNTIME_FLOW.md

# Part 6 — Vision Runtime Flow

> **Purpose**
>
> The Vision Runtime is the **eyes of AetherOS**.
>
> It continuously observes the desktop, understands graphical interfaces, detects UI elements, reads text, recognizes objects, builds a structured representation of the screen, and provides perception data to other agents.
>
> Unlike OCR alone, the Vision Runtime combines **computer vision, OCR, UI understanding, object detection, and reasoning-friendly representations** into one perception pipeline.

---

# Complete Vision Runtime

```text id="4q6jzw"
               Desktop Screen
                     │
                     ▼
            Screen Capture Engine
                     │
                     ▼
           Image Preprocessing
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
    OCR         Object Detection   UI Detection
      │              │              │
      └──────────────┼──────────────┘
                     ▼
             Layout Analysis
                     │
                     ▼
             Scene Graph Builder
                     │
                     ▼
            Vision Knowledge Base
                     │
                     ▼
        Planner / Executor / Memory
```

---

# Vision Philosophy

Vision should:

* Observe
* Detect
* Recognize
* Understand
* Verify

Vision should never:

* Click
* Move mouse
* Type
* Plan
* Execute tools

Vision is **read-only**.

---

# Vision Sources

AetherOS can receive visual information from:

* Primary monitor
* Multiple monitors
* Browser screenshots
* Window capture
* Camera (future)
* Mobile stream (future)
* Remote desktop (future)

---

# Vision Pipeline

```text id="5xzkj1"
Capture

↓

Preprocess

↓

OCR

↓

Detection

↓

Layout

↓

Scene Graph

↓

Knowledge

↓

Verification
```

---

# Step 1 — Screen Capture

Capture sources

```text id="63iblf"
Entire Desktop

Current Window

Region

Monitor

Browser

Application
```

Capture frequency

* On demand
* Scheduled
* Continuous
* Event-driven

---

# Capture Manager

Responsibilities

* Multi-monitor support
* Frame synchronization
* Region cropping
* Resolution scaling
* Compression

---

# Capture Output

```text id="e7x4p2"
Screenshot

↓

PNG

↓

NumPy Array

↓

OpenCV Image
```

The raw image enters preprocessing.

---

# Step 2 — Image Preprocessing

Improve image quality.

Pipeline

```text id="52h1m9"
Resize

↓

Denoise

↓

Contrast

↓

Sharpen

↓

Normalize
```

Optional

* Grayscale
* Threshold
* Perspective correction

---

# Step 3 — Screen Classification

Determine screen type.

Examples

```text id="mfq4e5"
Desktop

Browser

TradingView

VS Code

Terminal

Settings

Explorer
```

This helps downstream models.

---

# Step 4 — OCR Runtime

Extract visible text.

Pipeline

```text id="mivp2z"
Image

↓

OCR Engine

↓

Bounding Boxes

↓

Confidence

↓

Structured Text
```

Example

```json id="kp3jrv"
{
  "text":"Login",
  "confidence":0.99,
  "box":[420,210,500,250]
}
```

---

# OCR Technologies

Primary

* PaddleOCR

Future

* EasyOCR
* TrOCR
* Microsoft OCR
* Cloud OCR

---

# Step 5 — Object Detection

Detect visual objects.

Examples

```text id="yvn2dc"
Button

Textbox

Chart

Icon

Scrollbar

Menu

Image
```

Pipeline

```text id="v9spqf"
Image

↓

YOLO

↓

Bounding Boxes

↓

Labels
```

---

# Step 6 — UI Element Detection

Understand interface components.

Recognizes

* Buttons
* Checkboxes
* Radio buttons
* Sliders
* Dropdowns
* Tabs
* Tables
* Input fields

Output

```json id="vgixd9"
{
  "type":"button",
  "text":"Submit",
  "enabled":true
}
```

---

# Step 7 — Window Understanding

Identify

* Active window
* Window title
* Focus state
* Position
* Size
* Application

Example

```text id="jjxgx2"
Window

TradingView

Position

(0,0)

Focused

True
```

---

# Step 8 — Layout Analysis

Convert pixels into structure.

Example

```text id="jlwm0y"
Header

Sidebar

Toolbar

Main Content

Footer
```

Planner uses layout instead of pixels.

---

# Step 9 — Scene Graph Generation

Vision converts the screen into relationships.

Example

```text id="bb5w6v"
Window

│

├── Toolbar

│     ├── Save

│     ├── Open

│

├── Sidebar

│

└── Content Area
```

Scene graphs simplify reasoning.

---

# Step 10 — Semantic Understanding

Vision identifies context.

Example

Instead of

```text id="rq7smr"
Rectangle
```

Vision returns

```text id="0wqu9g"
TradingView Buy Button
```

Meaning matters more than pixels.

---

# Vision Knowledge Object

Every capture becomes structured data.

Example

```json id="z0khfu"
{
  "window":"TradingView",
  "elements":[...],
  "texts":[...],
  "objects":[...],
  "layout":{},
  "timestamp":"..."
}
```

---

# Step 11 — Planner Interaction

Planner requests

```text id="g54n3d"
Find Login Button
```

Vision returns

```json id="z76tf5"
{
  "found":true,
  "x":520,
  "y":300
}
```

Planner never analyzes pixels.

---

# Step 12 — Verification Runtime

Vision verifies execution.

Example

```text id="6v2tpk"
Click

↓

Capture

↓

Button Gone?

↓

Success
```

Verification methods

* OCR
* Pixel comparison
* UI detection
* Window detection
* Object detection

---

# Continuous Observation

Vision can monitor changes.

```text id="0qqw6m"
Frame 1

↓

Frame 2

↓

Difference

↓

Event
```

Examples

* New popup
* Button enabled
* Chart updated
* Window closed

---

# Change Detection

Pipeline

```text id="u9y0q4"
Previous Frame

↓

Current Frame

↓

Difference

↓

Threshold

↓

Event
```

Only significant changes generate events.

---

# Multi-Monitor Runtime

```text id="smw2j8"
Monitor 1

||

Monitor 2

||

Monitor 3

↓

Merge Context
```

Each monitor has an independent capture pipeline.

---

# Browser Vision

Browser pages may be analyzed using:

* DOM
* Screenshot
* Hybrid mode

Hybrid mode provides the highest accuracy.

---

# Trading Chart Runtime

Specialized vision pipeline.

Recognizes

* Candlesticks
* Trendlines
* Indicators
* Price labels
* Volume
* Drawing tools

Future

Dedicated financial vision models.

---

# OCR Cache

Repeated screenshots reuse OCR.

```text id="jnhd6h"
Same Image

↓

Cached OCR

↓

Return Immediately
```

Reduces latency.

---

# Vision Cache

Stores

* Recent screenshots
* OCR
* UI elements
* Scene graphs

Used by verification and memory.

---

# Vision Events

Generated automatically.

Examples

```text id="dr3rj2"
Popup Appeared

↓

Window Closed

↓

Chart Updated

↓

Download Finished

↓

Dialog Opened
```

Planner subscribes to these events.

---

# Failure Handling

If vision fails

```text id="n2g0k2"
Retry Capture

↓

Alternative OCR

↓

Lower Resolution

↓

Fallback Detection

↓

Failure
```

Execution continues whenever possible.

---

# Runtime Metrics

Collected

* Capture FPS
* OCR latency
* Detection latency
* Cache hit ratio
* Recognition accuracy
* Verification accuracy
* GPU utilization
* Memory consumption

---

# Vision Security

Vision cannot

* Modify desktop
* Execute clicks
* Store screenshots permanently without policy
* Access protected applications without permission

Sensitive captures can be automatically masked.

---

# Complete Vision Runtime Flow

```text id="p8d4ko"
Desktop Screen
      │
      ▼
Capture
      │
      ▼
Preprocessing
      │
      ▼
OCR
      │
      ▼
Object Detection
      │
      ▼
UI Detection
      │
      ▼
Layout Analysis
      │
      ▼
Scene Graph
      │
      ▼
Knowledge Object
      │
      ▼
Planner / Executor
      │
      ▼
Verification
      │
      ▼
Memory
```

---

# Recommended Technology Stack

| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| Screen Capture   | MSS, DXCam                          |
| Image Processing | OpenCV                              |
| OCR              | PaddleOCR                           |
| Object Detection | YOLOv11 / YOLOv12 (future)          |
| UI Detection     | OmniParser / UI-TARS / Custom Model |
| Embeddings       | CLIP / SigLIP                       |
| Layout Analysis  | LayoutParser                        |
| GPU Runtime      | ONNX Runtime / TensorRT             |
| Array Processing | NumPy                               |

---

# Future Enhancements

Future Vision capabilities include:

* Live video understanding
* Hand gesture recognition
* Webcam perception
* 3D desktop understanding
* AI-generated UI descriptions
* Multi-modal vision-language models
* Autonomous UI exploration
* Predictive screen understanding
* Eye-tracking integration
* AR/VR interface perception

---

# Summary

The Vision Runtime is the perception layer of AetherOS. It continuously transforms raw pixels into structured knowledge through screen capture, preprocessing, OCR, object detection, UI analysis, layout understanding, and scene graph generation. This allows every other subsystem to reason over semantic information instead of pixels, enabling reliable desktop automation, verification, and intelligent decision-making while keeping the Vision layer strictly read-only.

---

## Next Part

**05_RUNTIME_FLOW.md — Part 7 — Desktop Runtime Flow**

Topics include:

* Mouse execution pipeline
* Keyboard execution pipeline
* Window management
* Clipboard runtime
* File system operations
* Audio and notification control
* Process management
* Desktop verification
* Safety mechanisms
* Human-like interaction engine
