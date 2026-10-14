# ROADMAP.md

# Phase 2 — Vision Intelligence & Perception System (Weeks 7–12)

> **Goal**
>
> Build the complete perception system of AetherOS. At the end of this phase, AetherOS should be able to see the screen like a human, understand UI layouts, read text, detect objects, recognize applications, track changes, and produce structured screen understanding.
>
> **Deliverable:** A fully functional Vision Engine capable of powering autonomous desktop interaction.

---

# Phase Overview

```text
Phase 2

↓

Screen Capture

↓

OCR

↓

UI Detection

↓

Object Detection

↓

Layout Analysis

↓

Scene Graph

↓

Vision API

↓

Ready for Phase 3
```

---

# Objectives

By the end of Phase 2, AetherOS should:

* Capture desktop continuously
* Detect windows
* Read text (OCR)
* Detect UI components
* Understand layouts
* Build scene graphs
* Detect screen changes
* Locate buttons visually
* Export structured screen state

No autonomous planning yet.

---

# Milestone 1 — Vision Module Foundation

Folder

```text
vision/

capture/

ocr/

detectors/

layout/

scene/

tracker/

cache/

models/

api/
```

Responsibilities

* Screen understanding
* Image processing
* Visual APIs
* Object detection

Deliverable

Vision module skeleton.

---

# Milestone 2 — Screen Capture Engine

Folder

```text
vision/capture/
```

Files

```text
capture.py

monitor.py

screen.py

region.py
```

Capabilities

* Full desktop capture
* Active window capture
* Region capture
* Multi-monitor capture
* High FPS capture

Libraries

* MSS
* DXCam (preferred for Windows)

Deliverable

High-speed screen capture.

---

# Milestone 3 — Image Processing Pipeline

Folder

```text
vision/image/
```

Tasks

* Resize
* Crop
* Normalize
* Color conversion
* Noise reduction
* Contrast enhancement

Libraries

* OpenCV
* NumPy

Deliverable

Optimized image preprocessing.

---

# Milestone 4 — OCR Engine

Folder

```text
vision/ocr/
```

Implement

```text
OCR Manager

OCR Cache

Language Detection

Confidence Filtering
```

Primary Engine

* PaddleOCR

Future

* EasyOCR
* Tesseract

Output

```json
{
  "text":"Open",
  "confidence":0.99,
  "bbox":[120,250,200,280]
}
```

Deliverable

Reliable text extraction.

---

# Milestone 5 — UI Element Detection

Folder

```text
vision/detectors/ui/
```

Detect

* Buttons
* Icons
* Input fields
* Menus
* Checkboxes
* Tables
* Toolbars
* Dialogs

Model

* YOLOv11

Deliverable

Structured UI detection.

---

# Milestone 6 — Object Detection

Folder

```text
vision/detectors/object/
```

Detect

* Browser
* Terminal
* VS Code
* TradingView
* File Explorer
* Calculator
* Desktop icons

Libraries

* YOLO
* ONNX Runtime

Deliverable

Application awareness.

---

# Milestone 7 — Layout Understanding

Folder

```text
vision/layout/
```

Tasks

* Split screen into regions
* Detect panels
* Detect navigation bars
* Detect content areas
* Detect dialogs

Output

```text
Header

Sidebar

Content

Footer
```

Deliverable

Semantic UI layout.

---

# Milestone 8 — Scene Graph Generator

Folder

```text
vision/scene/
```

Responsibilities

Build structured representation.

Example

```text
Desktop

└── Chrome

     ├── Toolbar

     ├── Search Box

     ├── BTC Chart

     └── Buy Button
```

Deliverable

Scene graph generation.

---

# Milestone 9 — Vision Cache

Folder

```text
vision/cache/
```

Responsibilities

* Cache OCR
* Cache detections
* Avoid redundant inference
* Improve FPS

Deliverable

Fast perception.

---

# Milestone 10 — Change Detection

Folder

```text
vision/tracker/
```

Detect

* Button changed
* Window moved
* Popup appeared
* Chart updated
* Cursor movement

Pipeline

```text
Frame A

↓

Frame B

↓

Difference

↓

Changed Regions
```

Deliverable

Incremental updates.

---

# Milestone 11 — Window Recognition

Capabilities

Identify

* Active window
* Window title
* Executable
* Process ID
* Screen coordinates

Libraries

* pywin32
* pygetwindow

Deliverable

Window awareness.

---

# Milestone 12 — Visual Search API

Folder

```text
vision/api/
```

Functions

```python
find_text()

find_button()

find_icon()

find_object()

find_region()
```

Returns

Bounding boxes with confidence.

Deliverable

Reusable Vision API.

---

# Milestone 13 — Coordinate Mapper

Purpose

Convert

```text
Vision Coordinates

↓

Desktop Coordinates

↓

Mouse Coordinates
```

Supports

* Multi-monitor
* Scaling
* DPI awareness

Deliverable

Accurate clicking.

---

# Milestone 14 — Vision Benchmark

Measure

* FPS
* OCR latency
* Detection latency
* GPU usage
* Accuracy

Target

| Metric    | Goal      |
| --------- | --------- |
| OCR       | <200 ms   |
| Detection | <100 ms   |
| Capture   | 30–60 FPS |
| Memory    | <2 GB     |

Deliverable

Performance report.

---

# Milestone 15 — Testing

Tests

* OCR
* Detection
* Layout
* Scene graph
* Coordinate mapping
* Change detection

Framework

* pytest

Deliverable

Reliable Vision Engine.

---

# Folder Status After Phase 2

```text
vision/

capture/

ocr/

detectors/

layout/

scene/

tracker/

cache/

models/

api/

tests/
```

---

# Recommended Tech Stack

| Category            | Technology   |
| ------------------- | ------------ |
| Screen Capture      | DXCam, MSS   |
| Image Processing    | OpenCV       |
| Numerical Computing | NumPy        |
| OCR                 | PaddleOCR    |
| Object Detection    | YOLOv11      |
| Inference           | ONNX Runtime |
| Window Detection    | pywin32      |
| GPU                 | CUDA         |
| Testing             | pytest       |

---

# Success Criteria

Phase 2 is complete when:

* ✅ Desktop captured in real time
* ✅ OCR works accurately
* ✅ UI elements detected
* ✅ Applications recognized
* ✅ Layout understood
* ✅ Scene graph generated
* ✅ Coordinate mapping accurate
* ✅ Change detection works
* ✅ Vision APIs available
* ✅ Performance targets achieved

---

# Estimated Timeline

| Week    | Focus                  |
| ------- | ---------------------- |
| Week 7  | Capture Engine         |
| Week 8  | OCR                    |
| Week 9  | UI & Object Detection  |
| Week 10 | Layout & Scene Graph   |
| Week 11 | Tracking & APIs        |
| Week 12 | Optimization & Testing |

---

# Deliverable

At the end of **Phase 2**, AetherOS gains **eyes**. It can observe the desktop in real time, recognize applications and UI components, understand layouts, detect changes, and expose structured visual information that later phases (Browser Automation, Planning, and Autonomous Agents) will use for intelligent decision-making.

