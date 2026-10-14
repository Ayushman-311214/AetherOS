# VISION.md

# AetherOS Vision Intelligence Architecture

> **Purpose**
>
> The **Vision** module gives AetherOS the ability to **see and understand the desktop like a human**. It continuously observes the screen, detects UI elements, recognizes applications, extracts text, tracks changes, builds semantic scene representations, and provides structured visual information to the rest of the system.
>
> The Vision module is the **eyes** of AetherOS.

---

# Design Philosophy

The Vision module should be:

* Real-time
* Accurate
* GPU Accelerated
* Modular
* Extensible
* Multi-monitor aware
* AI-driven
* Cache optimized
* Verifiable
* Provider independent

---

# Responsibilities

The Vision module is responsible for:

* Screen Capture
* OCR
* UI Detection
* Object Detection
* Icon Recognition
* Layout Analysis
* Window Recognition
* Scene Graph Generation
* Screen Tracking
* Visual Search
* Coordinate Mapping
* Image Understanding

The Vision module **does not**:

* Control the mouse
* Execute automation
* Make decisions
* Store long-term memory
* Plan workflows

---

# Architecture

```text id="n1trgk"
Desktop

↓

Screen Capture

↓

Image Processing

↓

OCR

↓

Object Detection

↓

UI Detection

↓

Layout Analysis

↓

Scene Graph

↓

Vision API

↓

Agents
```

---

# Directory Structure

```text id="0q5vka"
vision/
│
├── __init__.py
│
├── api/
│
├── capture/
│
├── preprocessing/
│
├── ocr/
│
├── detectors/
│   ├── ui/
│   ├── object/
│   ├── icon/
│   └── window/
│
├── segmentation/
│
├── layout/
│
├── scene/
│
├── tracker/
│
├── coordinates/
│
├── cache/
│
├── models/
│
├── datasets/
│
├── embeddings/
│
├── verification/
│
├── events/
│
├── analytics/
│
├── utils/
│
└── tests/
```

---

# Screen Capture

Folder

```text id="zk4id2"
vision/capture/
```

Responsibilities

* Full desktop capture
* Active window capture
* Region capture
* Multi-monitor capture
* High FPS streaming

Libraries

* DXCam
* MSS

Target

* 30–60 FPS

---

# Image Preprocessing

Folder

```text id="rxmjlwm"
vision/preprocessing/
```

Pipeline

```text id="nxcy6z"
Raw Image

↓

Resize

↓

Normalize

↓

Color Correction

↓

Noise Reduction

↓

Processed Frame
```

Libraries

* OpenCV
* NumPy

---

# OCR Engine

Folder

```text id="d1o6kb"
vision/ocr/
```

Responsibilities

* Text detection
* Text recognition
* Language detection
* Confidence scoring
* OCR caching

Primary Engine

* PaddleOCR

Future

* EasyOCR
* Tesseract

Output

```json id="esyv3x"
{
    "text":"Settings",
    "confidence":0.99,
    "bbox":[110,85,210,120]
}
```

---

# UI Detection

Folder

```text id="chjk7g"
vision/detectors/ui/
```

Detect

* Buttons
* Input fields
* Dropdowns
* Menus
* Toolbars
* Tables
* Tabs
* Checkboxes
* Radio buttons

Models

* YOLOv11

---

# Object Detection

Folder

```text id="szxv6q"
vision/detectors/object/
```

Recognize

* Browser
* VS Code
* Terminal
* File Explorer
* Calculator
* TradingView
* Desktop Icons

Libraries

* YOLO
* ONNX Runtime

---

# Icon Detection

Folder

```text id="lymn4t"
vision/detectors/icon/
```

Detect

* Application icons
* Toolbar icons
* Navigation icons
* Custom symbols

Methods

* CNN
* CLIP Embeddings

---

# Window Recognition

Folder

```text id="whpjlwm"
vision/detectors/window/
```

Recognize

* Window title
* Active window
* Window borders
* Window regions

Combines

* Windows API
* Vision Detection

---

# Image Segmentation

Folder

```text id="4ll2mx"
vision/segmentation/
```

Purpose

Separate UI regions.

Example

```text id="hl4lzn"
Toolbar

Sidebar

Content

Status Bar
```

Future

* SAM (Segment Anything)

---

# Layout Analysis

Folder

```text id="wttgux"
vision/layout/
```

Responsibilities

Understand

* Header
* Sidebar
* Navigation
* Main Content
* Footer
* Floating Panels

Output

Semantic layout map.

---

# Scene Graph

Folder

```text id="sk6o7x"
vision/scene/
```

Example

```text id="8zg7xb"
Desktop

└── Chrome

     ├── Toolbar

     ├── Search Box

     ├── BTC Chart

     └── Buy Button
```

Purpose

Represent screen structure.

---

# Screen Tracker

Folder

```text id="n6zgu7"
vision/tracker/
```

Detect

* Changed pixels
* New windows
* Popups
* Notifications
* Cursor movement
* UI updates

Pipeline

```text id="h4snwb"
Frame A

↓

Frame B

↓

Difference

↓

Changed Regions
```

---

# Coordinate Mapper

Folder

```text id="m0cd3l"
vision/coordinates/
```

Responsibilities

Convert

```text id="zbqkgj"
Bounding Box

↓

Desktop Coordinates

↓

Mouse Coordinates
```

Supports

* Multi-monitor
* DPI scaling
* Window offsets

---

# Vision Cache

Folder

```text id="3w7ywg"
vision/cache/
```

Stores

* OCR results
* Detections
* Embeddings
* Recent frames

Purpose

Avoid unnecessary inference.

---

# Embedding Engine

Folder

```text id="a64n3u"
vision/embeddings/
```

Generate

* Image embeddings
* Icon embeddings
* UI embeddings

Models

* CLIP
* SigLIP (future)

---

# Vision API

Folder

```text id="y5f6o0"
vision/api/
```

Functions

```python id="17a84l"
find_text()

find_button()

find_icon()

find_object()

find_window()

capture()

analyze()

locate()
```

Every other module uses this API.

---

# Verification

Folder

```text id="5p4w3c"
vision/verification/
```

Verify

* Button exists
* Window opened
* Text visible
* Dialog appeared
* Loading finished

Supports

* Automation verification
* Workflow verification

---

# Events

Folder

```text id="n55qgv"
vision/events/
```

Examples

```text id="v9vbzc"
ScreenCaptured

OCRFinished

ObjectDetected

WindowChanged

PopupDetected

TrackingUpdated
```

---

# Analytics

Folder

```text id="wv4f6r"
vision/analytics/
```

Measures

* FPS
* OCR latency
* Detection latency
* GPU utilization
* Cache hit ratio

---

# Models

Folder

```text id="h20ezn"
vision/models/
```

Contains

* YOLO models
* OCR models
* CLIP models
* ONNX models

---

# Utilities

Folder

```text id="7q8rbl"
vision/utils/
```

Provides

* Bounding box helpers
* Coordinate utilities
* Image conversion
* Color utilities
* Screenshot helpers

---

# Vision Execution Flow

```text id="oj88hm"
Desktop

↓

Capture

↓

Preprocessing

↓

Detection

↓

OCR

↓

Layout Analysis

↓

Scene Graph

↓

Vision API

↓

Agents
```

---

# Technology Stack

| Component           | Technology                |
| ------------------- | ------------------------- |
| Screen Capture      | DXCam, MSS                |
| Image Processing    | OpenCV                    |
| Numerical Computing | NumPy                     |
| OCR                 | PaddleOCR                 |
| Object Detection    | YOLOv11                   |
| Image Embeddings    | CLIP                      |
| Inference Runtime   | ONNX Runtime              |
| Segmentation        | Segment Anything (Future) |
| GPU                 | CUDA                      |
| Testing             | pytest                    |

---

# Design Principles

1. Capture once, analyze many times.
2. Cache expensive inference results.
3. Separate detection, OCR, and layout analysis.
4. Always expose structured outputs through the Vision API.
5. Support multi-monitor and high-DPI displays.
6. Keep models interchangeable through abstraction layers.
7. Prefer GPU acceleration when available.
8. Never let higher-level modules access models directly.

---

# Success Criteria

The Vision module is complete when:

* ✅ Real-time screen capture runs at 30–60 FPS.
* ✅ OCR accurately extracts on-screen text.
* ✅ UI elements and application windows are detected.
* ✅ Layout analysis produces semantic screen regions.
* ✅ Scene graphs represent desktop structure.
* ✅ Coordinate mapping is accurate across displays.
* ✅ Visual search APIs locate UI elements reliably.
* ✅ Screen changes are tracked efficiently.
* ✅ Verification supports downstream automation.
* ✅ All functionality is accessible through a unified Vision API.

The **Vision** module is the **perception system** of AetherOS. It converts raw pixels into structured knowledge, allowing higher-level modules to understand applications, interfaces, and visual context in the same way a human observes a computer screen.
