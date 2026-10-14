# 04_PROJECT_STRUCTURE.md

# Part 6 — Vision Project Structure

> **Purpose**
>
> The `vision/` module is the perception system of AetherOS. It enables the AI to observe, interpret, and understand everything visible on the user's screen.
>
> It transforms raw pixels into structured information that agents can reason about.
>
> **Rule:** The Vision module observes only. It never performs actions such as moving the mouse or clicking.

---

# Vision Architecture

```text
                Screen
                   │
                   ▼
          Screen Capture
                   │
                   ▼
          Image Preprocessing
                   │
     ┌─────────────┼─────────────┐
     │             │             │
     ▼             ▼             ▼
    OCR      Object Detection   UI Analysis
     │             │             │
     └─────────────┼─────────────┘
                   ▼
          Layout Understanding
                   ▼
          Scene Understanding
                   ▼
         Structured Observation
                   ▼
            Vision Agent
```

---

# Folder Structure

```text
vision/
│
├── __init__.py
│
├── capture/
├── preprocessing/
├── ocr/
├── detection/
├── segmentation/
├── ui/
├── layout/
├── charts/
├── matching/
├── parsing/
├── models/
├── cache/
├── pipelines/
├── datasets/
├── benchmarking/
├── utils/
│
├── config.py
├── constants.py
├── registry.py
├── interfaces.py
├── manager.py
└── exceptions.py
```

---

# Vision Philosophy

Vision should answer:

* What is on the screen?
* Where is it?
* What does it contain?
* Which window is active?
* Which button is clickable?
* Which chart is visible?
* Has anything changed?
* Is the previous action successful?

It should **never** decide what to do next.

---

# 1. capture/

Purpose

Capture pixels from the operating system.

---

Structure

```text
capture/
│
├── screen.py
├── window.py
├── monitor.py
├── region.py
├── stream.py
└── recorder.py
```

---

### screen.py

Captures

* Entire desktop
* Multi-monitor
* High DPI

---

### window.py

Captures only one application window.

Example

Chrome

VS Code

TradingView

Explorer

---

### region.py

Captures a rectangle.

Useful for

* OCR
* Button Detection
* Performance

---

### stream.py

Provides continuous frame capture.

Used for

* Live Monitoring
* Screen Recording
* Real-Time Agents

---

### recorder.py

Creates videos.

Future

Training datasets

Replay

Debugging

---

# 2. preprocessing/

Purpose

Improve image quality before AI analysis.

---

Structure

```text
preprocessing/
│
├── resize.py
├── grayscale.py
├── threshold.py
├── denoise.py
├── sharpen.py
├── normalize.py
├── rotate.py
└── filters.py
```

---

Capabilities

* Contrast Enhancement
* Brightness Correction
* Rotation
* Scaling
* Noise Removal

---

# 3. ocr/

Purpose

Extract text from images.

---

Structure

```text
ocr/
│
├── engine.py
├── paddle.py
├── easyocr.py
├── tesseract.py
├── parser.py
├── formatter.py
├── language.py
├── confidence.py
└── cache.py
```

---

Supported Engines

Primary

* PaddleOCR

Secondary

* EasyOCR

Fallback

* Tesseract

---

Output

```json
{
  "text":"Login",
  "x":240,
  "y":520,
  "width":96,
  "height":30,
  "confidence":0.99
}
```

---

# 4. detection/

Purpose

Detect visual objects.

---

Structure

```text
detection/
│
├── engine.py
├── yolo.py
├── icons.py
├── buttons.py
├── windows.py
├── cursors.py
├── objects.py
└── confidence.py
```

---

Detects

* Buttons
* Icons
* Images
* Dialogs
* Notifications
* Menus
* Toolbars

---

# 5. segmentation/

Purpose

Separate UI into regions.

---

Structure

```text
segmentation/
│
├── sam.py
├── masks.py
├── regions.py
├── grouping.py
└── hierarchy.py
```

---

Uses

* Segment Anything Model (SAM)

Useful for

* Complex UI
* Unknown layouts
* Object boundaries

---

# 6. ui/

Purpose

Understand graphical interfaces.

---

Structure

```text
ui/
│
├── analyzer.py
├── controls.py
├── forms.py
├── menus.py
├── tables.py
├── dialogs.py
├── navigation.py
└── accessibility.py
```

---

Detects

* Buttons
* Checkboxes
* Radio Buttons
* Input Fields
* Sliders
* Tabs
* Lists
* Trees
* Dialogs

---

# 7. layout/

Purpose

Understand screen structure.

---

Structure

```text
layout/
│
├── analyzer.py
├── hierarchy.py
├── grouping.py
├── alignment.py
├── spacing.py
└── templates.py
```

---

Produces

```text
Window

├── Toolbar

├── Sidebar

├── Main Panel

└── Status Bar
```

This helps agents navigate unfamiliar applications.

---

# 8. charts/

Purpose

Financial chart understanding.

---

Structure

```text
charts/
│
├── candles.py
├── indicators.py
├── trendlines.py
├── support_resistance.py
├── patterns.py
├── market_structure.py
├── ict.py
└── smc.py
```

---

Capabilities

* Candlestick Detection
* Swing High/Low
* BOS
* CHoCH
* Fair Value Gaps
* Order Blocks
* Liquidity
* Trendlines
* Indicators

---

# 9. matching/

Purpose

Template matching.

---

Structure

```text
matching/
│
├── templates.py
├── matcher.py
├── similarity.py
├── hashing.py
└── cache.py
```

---

Useful when

OCR fails

UI Automation unavailable

Image comparison required

---

# 10. parsing/

Purpose

Convert vision outputs into structured objects.

---

Structure

```text
parsing/
│
├── parser.py
├── serializer.py
├── validator.py
└── schema.py
```

---

Output Example

```json
{
    "type":"button",
    "label":"Login",
    "position":[100,250],
    "confidence":0.98
}
```

---

# 11. models/

Purpose

Manage AI models.

---

Structure

```text
models/
│
├── loader.py
├── manager.py
├── downloader.py
├── updater.py
├── registry.py
└── config.py
```

---

Responsibilities

* Download Models
* Load Models
* GPU Detection
* Version Management
* Hot Reload

---

Supported Models

* PaddleOCR
* YOLO
* SAM
* GroundingDINO
* Florence
* OmniParser (Future)

---

# 12. cache/

Purpose

Reduce repeated computation.

---

Stores

* OCR Results
* Object Detection
* Model Outputs
* Image Embeddings
* Parsed Layouts

---

Structure

```text
cache/
│
├── memory.py
├── disk.py
├── embeddings.py
└── eviction.py
```

---

# 13. pipelines/

Purpose

Reusable processing pipelines.

---

Structure

```text
pipelines/
│
├── ocr_pipeline.py
├── ui_pipeline.py
├── chart_pipeline.py
├── desktop_pipeline.py
└── benchmark.py
```

Example

```text
Capture

↓

Preprocess

↓

OCR

↓

Detection

↓

Parsing

↓

Return Result
```

---

# 14. datasets/

Purpose

Training and testing datasets.

---

Contains

```text
datasets/

ocr/

icons/

buttons/

charts/

screenshots/
```

Used for

* Benchmarking
* Regression Testing
* Fine-tuning

---

# 15. benchmarking/

Purpose

Measure model performance.

---

Metrics

* FPS
* OCR Accuracy
* Detection Accuracy
* GPU Usage
* CPU Usage
* Memory Usage
* Latency

---

# 16. utils/

Shared helper functions.

Examples

```text
image.py

geometry.py

drawing.py

colors.py

coordinates.py
```

---

# registry.py

Registers every vision pipeline.

Example

```python
VISION_PIPELINES = {

"ocr": OCRPipeline,

"ui": UIPipeline,

"charts": ChartPipeline
}
```

---

# manager.py

Responsibilities

* Load Models
* Initialize GPU
* Allocate Memory
* Monitor Health
* Shutdown Models

---

# interfaces.py

Defines contracts.

Example

```python
class OCRInterface:

    recognize()

class DetectorInterface:

    detect()
```

---

# config.py

Example

```yaml
ocr:

  engine: paddle

  language: en

detection:

  model: yolo11

gpu:

  enabled: true
```

---

# constants.py

```python
OCR_CONFIDENCE=0.75

YOLO_CONFIDENCE=0.50

MAX_IMAGE_SIZE=4096
```

---

# exceptions.py

Contains

```text
OCRException

DetectionException

ModelNotLoaded

InvalidImage

GPUNotAvailable
```

---

# Vision Pipeline

```text
Screen

↓

Capture

↓

Preprocess

↓

OCR

↓

Object Detection

↓

UI Detection

↓

Layout Analysis

↓

Scene Understanding

↓

Structured JSON

↓

Vision Agent
```

---

# Dependency Rules

Vision may use

* OpenCV
* PaddleOCR
* YOLO
* SAM
* NumPy
* Pillow
* ONNX Runtime

Vision must NOT import

* Desktop Controllers
* Browser Module
* Agents
* LLM Providers
* Trading Logic

---

# Recommended Libraries

| Capability           | Library      |
| -------------------- | ------------ |
| Image Processing     | OpenCV       |
| OCR                  | PaddleOCR    |
| Secondary OCR        | EasyOCR      |
| Object Detection     | YOLO         |
| Segmentation         | SAM          |
| Image Processing     | Pillow       |
| Numerical Operations | NumPy        |
| Screen Capture       | mss          |
| GPU Inference        | ONNX Runtime |

---

# Future Vision Roadmap

Future capabilities include:

* GUI Foundation Models
* Vision-Language Models
* OmniParser integration
* Multi-screen reasoning
* Video understanding
* Handwriting recognition
* Document intelligence
* Native UI semantic understanding
* Real-time scene graphs
* Autonomous UI exploration

---

# Summary

The `vision/` module is the eyes of AetherOS. It converts raw screen pixels into structured semantic information through image capture, preprocessing, OCR, object detection, UI analysis, layout understanding, and specialized pipelines such as financial chart recognition. By isolating perception from reasoning and execution, the module remains highly modular, scalable, and capable of adopting future computer vision technologies without changing the overall system architecture.

---

## Next Part

**Part 7 — `llm/` Project Structure**

This section will design the complete AI brain of AetherOS, including:

* Multi-provider architecture
* Prompt management
* Tool calling system
* Function registry
* Conversation manager
* Context builder
* Memory injection
* Model router
* Streaming
* Structured output parser
* Token management
* Local + Cloud model orchestration

This is the intelligence core that connects every other module.
