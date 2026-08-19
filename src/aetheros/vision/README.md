# AetherOS Vision Engine

Complete computer vision system for AetherOS trading intelligence platform.

## Overview

The vision engine provides:

* **Screen capture** — capture full screen, windows, or regions
* **OCR** — extract text from images using multiple providers
* **Object detection** — detect UI elements, buttons, charts
* **Template matching** — find UI patterns and visual elements
* **Image processing** — resize, crop, annotate, filter
* **Provider architecture** — pluggable backends for each capability

## Architecture

```
Vision Engine
    |
    +-- Image (core data model)
    +-- Providers
    |     +-- Screen Capture (MSS)
    |     +-- OCR (EasyOCR, PaddleOCR, Tesseract)
    |     +-- Detection (YOLOv8)
    |     +-- Template Matching (OpenCV)
    +-- Processing (filters, transforms, annotations)
    +-- Models (TextRegion, Detection, TemplateMatch)
```

## Quick Start

### Screen Capture

```python
from aetheros.vision import MSSCaptureProvider, Image

provider = MSSCaptureProvider()

# Capture full screen
screenshot = await provider.capture()

# Capture specific region
region = await provider.capture_region(
    x=100, y=100,
    width=800, height=600,
)

# Capture window by title
window = await provider.capture_window("TradingView")
```

### OCR (Text Extraction)

```python
from aetheros.vision import EasyOCRProvider, Image

provider = EasyOCRProvider(languages=['en'])

# Extract all text
regions = await provider.extract_text(image)

for region in regions:
    print(f"{region.text} @ ({region.x}, {region.y})")
    print(f"Confidence: {region.confidence:.2f}")

# Search for specific text
price_regions = await provider.find_text(image, "RELIANCE")
```

### Object Detection

```python
from aetheros.vision import YOLOProvider

provider = YOLOProvider(model_size='n')  # nano, small, medium, large

# Detect objects
detections = await provider.detect(image, confidence=0.5)

for det in detections:
    print(f"{det.label}: {det.confidence:.2f}")
    print(f"Box: ({det.left}, {det.top}, {det.right}, {det.bottom})")
```

### Template Matching

```python
from aetheros.vision import OpenCVTemplateProvider

provider = OpenCVTemplateProvider()

# Find template in image
matches = await provider.find(
    image=screenshot,
    template=button_template,
    threshold=0.90,
)

for match in matches:
    print(f"Found at ({match.x}, {match.y})")
    print(f"Confidence: {match.confidence:.2f}")
```

### Image Processing

```python
from aetheros.vision import Image

# Load image
image = Image.from_file("chart.png")

# Resize
resized = image.resize(width=800, height=600)

# Crop region
cropped = image.crop(x=100, y=100, width=400, height=300)

# Convert to grayscale
gray = image.to_grayscale()

# Draw annotations
annotated = image.draw_box(
    x=100, y=100, width=200, height=150,
    color=(0, 255, 0), thickness=2,
)

# Save
annotated.save("output.png")
```

## Core Components

### Image Model

Central data model for all vision operations:

```python
from aetheros.vision import Image
import numpy as np

# Create from file
img = Image.from_file("screenshot.png")

# Create from NumPy array
data = np.zeros((480, 640, 3), dtype=np.uint8)
img = Image(data=data, source="generated")

# Properties
print(f"Size: {img.width}x{img.height}")
print(f"Channels: {img.channels}")
print(f"Format: {img.format}")

# Operations
img_resized = img.resize(width=800, height=600)
img_gray = img.to_grayscale()
img_cropped = img.crop(x=0, y=0, width=400, height=300)

# Annotations
img_annotated = img.draw_box(100, 100, 200, 150)
img_annotated = img_annotated.draw_text("BUY SIGNAL", 50, 50)

# Save
img.save("output.png")
```

### Provider System

All providers implement standard interfaces:

```python
# Screen Capture Provider Interface
class ScreenCaptureProvider(Protocol):
    async def capture(self) -> Image: ...
    async def capture_region(self, x, y, width, height) -> Image: ...
    async def capture_window(self, title: str) -> Image: ...

# OCR Provider Interface
class OCRProvider(Protocol):
    async def extract_text(self, image: Image) -> list[TextRegion]: ...
    async def find_text(self, image: Image, text: str) -> list[TextRegion]: ...

# Detection Provider Interface  
class DetectionProvider(Protocol):
    async def detect(self, image: Image, confidence: float) -> list[Detection]: ...

# Template Provider Interface
class TemplateProvider(Protocol):
    async def find(self, image: Image, template: Image, threshold: float) -> list[TemplateMatch]: ...
```

## Available Providers

### Screen Capture

**MSS** (Multi-Screen Shot)
* Fast cross-platform screen capture
* Supports multiple monitors
* Window capture
* Region capture

### OCR

**EasyOCR**
* 80+ languages
* Deep learning based
* High accuracy
* GPU acceleration

**PaddleOCR**
* Optimized for production
* Fast inference
* Chinese/English specialized
* Lightweight models

**Tesseract**
* Classic OCR engine
* 100+ languages
* Good for printed text
* No GPU required

### Object Detection

**YOLOv8**
* State-of-the-art object detection
* Real-time performance
* Multiple model sizes (nano to xlarge)
* 80 COCO classes
* Custom training support

### Template Matching

**OpenCV**
* Fast template matching
* Multi-scale search
* Rotation-invariant matching
* Sub-pixel accuracy

## Configuration

### Provider Selection

```python
from aetheros.vision import (
    MSSCaptureProvider,
    EasyOCRProvider,
    YOLOProvider,
    OpenCVTemplateProvider,
)

# Initialize providers
capture = MSSCaptureProvider()
ocr = EasyOCRProvider(languages=['en'])
detector = YOLOProvider(model_size='n')
matcher = OpenCVTemplateProvider()
```

### Model Paths

```python
# YOLO custom model
detector = YOLOProvider(
    model_path="models/custom_ui_detector.pt"
)

# EasyOCR custom model directory
ocr = EasyOCRProvider(
    languages=['en'],
    model_storage_directory="models/easyocr",
)
```

## Use Cases for Trading

### Chart Analysis

```python
# Capture TradingView chart
screenshot = await capture.capture_window("TradingView")

# Extract price from chart
price_regions = await ocr.find_text(screenshot, "₹")

# Detect chart patterns
detections = await detector.detect(screenshot)

# Find specific UI elements
buy_button = await matcher.find(screenshot, buy_button_template)
```

### Market Data Extraction

```python
# Capture trading terminal
terminal = await capture.capture_window("Trading Terminal")

# Extract all visible text
regions = await ocr.extract_text(terminal)

# Filter for numeric values
prices = [r for r in regions if r.text.replace('.', '').isdigit()]
```

### UI Automation Support

```python
# Find login button
matches = await matcher.find(screen, login_button_template)

if matches:
    button = matches[0]
    # Coordinates for automation
    click_x = button.x + button.width // 2
    click_y = button.y + button.height // 2
```

### Visual Monitoring

```python
# Continuous monitoring
while trading_active:
    screenshot = await capture.capture_region(
        x=alert_area_x,
        y=alert_area_y,
        width=alert_area_width,
        height=alert_area_height,
    )
    
    # Check for alerts
    alert_text = await ocr.find_text(screenshot, "ALERT")
    
    if alert_text:
        # Handle alert
        await handle_trading_alert(alert_text)
    
    await asyncio.sleep(1.0)
```

## Testing

```bash
# Run all vision tests
pytest tests/vision -v

# Run specific provider tests
pytest tests/vision/test_vision_engine.py::TestOCR -v

# Run with coverage
pytest tests/vision --cov=aetheros.vision
```

## Dependencies

### Required

* `opencv-python` — image processing, template matching
* `numpy` — array operations
* `pillow` — image I/O

### Optional (per provider)

* `mss` — screen capture
* `easyocr` — OCR provider
* `paddleocr` — OCR provider (requires `paddlepaddle`)
* `pytesseract` — OCR provider (requires Tesseract binary)
* `ultralytics` — YOLOv8 detection

Install all:

```bash
pip install opencv-python numpy pillow mss easyocr paddleocr ultralytics pytesseract
```

Install selectively:

```bash
# Just screen capture and basic processing
pip install opencv-python numpy pillow mss

# Add OCR
pip install easyocr

# Add detection
pip install ultralytics
```

## Performance

### Screen Capture

* Full HD capture: ~5-10ms
* 4K capture: ~15-30ms
* Window capture: similar to region

### OCR

* EasyOCR: ~200-500ms per image (GPU), ~1-3s (CPU)
* PaddleOCR: ~100-300ms per image (optimized)
* Tesseract: ~50-200ms per image

### Object Detection

* YOLOv8n (nano): ~10-30ms (GPU), ~100-300ms (CPU)
* YOLOv8s (small): ~20-50ms (GPU), ~200-500ms (CPU)
* YOLOv8m (medium): ~30-80ms (GPU), ~500ms-1s (CPU)

### Template Matching

* Simple match: ~1-10ms
* Multi-scale: ~10-100ms
* Large images: proportional to search area

## Error Handling

All providers raise specific exceptions:

```python
from aetheros.vision.errors import (
    VisionError,           # Base exception
    CaptureError,          # Screen capture failed
    OCRError,              # Text extraction failed
    DetectionError,        # Object detection failed
    TemplateMatchError,    # Template matching failed
    ProcessingError,       # Image processing failed
)

try:
    screenshot = await capture.capture()
    text = await ocr.extract_text(screenshot)
except CaptureError as e:
    logger.error(f"Failed to capture screen: {e}")
except OCRError as e:
    logger.error(f"Failed to extract text: {e}")
```

## Logging

```python
import logging

# Enable vision logging
logging.getLogger("aetheros.vision").setLevel(logging.DEBUG)

# Provider-specific logging
logging.getLogger("aetheros.vision.providers.easyocr").setLevel(logging.INFO)
```

## Integration with AetherOS

The vision engine integrates with:

* **Desktop automation** — provides visual feedback
* **Tool system** — exposes vision capabilities as tools
* **Agents** — enables visual analysis in agent workflows
* **Memory** — stores visual observations
* **Events** — emits vision-related events

```python
# Example: Agent using vision
from aetheros.agents import Agent
from aetheros.vision import MSSCaptureProvider, EasyOCRProvider

class TradingScreenAgent(Agent):
    def __init__(self):
        self.capture = MSSCaptureProvider()
        self.ocr = EasyOCRProvider(languages=['en'])
    
    async def analyze_screen(self) -> dict:
        screenshot = await self.capture.capture()
        text_regions = await self.ocr.extract_text(screenshot)
        
        return {
            "screenshot": screenshot,
            "text": [r.text for r in text_regions],
            "timestamp": datetime.now(),
        }
```

## Roadmap

- [x] Core image model
- [x] Screen capture (MSS)
- [x] OCR (EasyOCR, PaddleOCR, Tesseract)
- [x] Object detection (YOLOv8)
- [x] Template matching (OpenCV)
- [x] Image processing and annotations
- [ ] Chart pattern recognition
- [ ] Candlestick detection
- [ ] Price axis extraction
- [ ] Trading UI element detection
- [ ] Screenshot diff/monitoring
- [ ] GPU acceleration optimizations
- [ ] Real-time video stream processing
- [ ] Custom model training workflows

## Contributing

When adding new providers:

1. Implement the appropriate protocol interface
2. Add to `__init__.py` exports
3. Document in this README
4. Add tests in `tests/vision/`
5. Update dependencies in `pyproject.toml`

## License

Part of AetherOS. See project LICENSE.
