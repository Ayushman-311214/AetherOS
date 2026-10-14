# AetherOS Vision Engine

Screen understanding for AetherOS: OCR, object detection, template matching and
image processing behind one service.

Vision is a **supporting capability**. When an authoritative structured source
exists for a number, use it — read the price from a market-data API, not from a
screenshot of a chart. Vision is for the things that only exist on screen: chart
annotations, broker terminals, UI state, visual confirmation that an automated
action actually happened.

---

## Architecture

```text
Agent
  |
  v
Tool Registry ......... read_screen_text, read_image_text,
  |                     detect_screen_objects, find_text, analyze_screen
  v
VisionService ......... aetheros/vision/controller.py
  |
  +-- OCRProvider ............ PaddleOCRProvider
  +-- VisionProvider ......... OpenCVProvider        (always available)
  +-- DetectionProvider ...... YOLOProvider          (optional)
  +-- TemplateProvider ....... OpenCVTemplateProvider

ScreenService ......... aetheros/desktop/screen/controller.py
  |
  +-- ScreenController ....... MSSScreen
```

Two rules the layering enforces:

* Agents never touch a provider. They call a tool, the tool resolves
  `VisionService` from the DI container.
* **Screen capture is not part of vision.** It lives in
  `aetheros/desktop/screen/` because it is an OS capability, and vision consumes
  it through `ScreenService`. That is what lets the whole engine run headless:
  `read_image_text` needs no display at all.

---

## Colour space

Every `Image` carries its channel order in `color_space` (`"bgr"`, `"rgb"` or
`"gray"`), and **BGR is the pipeline default** — it is what `cv2.imread`, mss and
PaddleOCR all produce or expect from a bare `ndarray`.

This matters more than it looks. `cvtColor(BGR2RGB)` and `cvtColor(RGB2BGR)` are
the *same permutation*, so code that decides whether to swap by counting channels
double-swaps without any error. The failure then shows up as slightly worse OCR
accuracy on coloured input, which is close to undiagnosable. So: declare the
colour space at construction, and let `Image.rgb()` / `.bgr()` / `.gray()` do the
conversions.

---

## Quick start

### Through the tools (what an agent does)

```python
from aetheros.tools.executor import ToolExecutor

result = await ToolExecutor().execute_safe("read_screen_text")

if result.ok:
    print(result.value["text"])
else:
    print(result.error)
```

`execute_safe` never raises: a missing display, an unavailable OCR model or a
malformed image all arrive as `result.ok is False` with a readable `error`, which
is what the agent loop needs. `execute()` is the raising variant.

### Through the service (what a tool does)

```python
from aetheros.core.container import container
from aetheros.vision.controller import VisionService
from aetheros.vision.image import Image

vision: VisionService = container.resolve(VisionService)

blocks = await vision.read_text(Image.open("chart.png"))

for block in blocks:
    print(f"{block.text!r} {block.confidence:.2f} at {block.center}")
```

An empty list means "no readable text" — a valid answer. A broken backend raises
`VisionError`.

### Capabilities

Optional backends are optional. Ask before you use them:

```python
vision.capabilities()
# {"ocr": True, "detection": False, "template": True, "image_processing": True}

if vision.has_detector:
    detections = await vision.detect_objects(image)
```

Calling `detect_objects` with no detector configured raises
`VISION_DETECTION_UNAVAILABLE` rather than returning `[]` — an empty list would
be read as "nothing on screen", which is a different and much worse claim.

---

## The `Image` model

`aetheros.vision.image.Image` is the only image type crossing a module boundary.
Construction validates, so a malformed frame fails at the boundary that produced
it instead of somewhere inside OpenCV.

```python
from aetheros.vision.image import Image

image = Image.open("chart.png")            # -> 3-channel BGR uint8, always
image = Image.from_numpy(frame, source="screen", color_space="bgr")

image.width, image.height, image.channels, image.shape
image.has_alpha
image.color_space                          # never None after construction

image.rgb()                                # colour-space conversions
image.bgr()
image.gray()
image.without_alpha()

image.resize(width=800, height=600)
image.crop(x=100, y=100, width=400, height=300)
image.copy()

image.save("out.png")                      # colours preserved
image.to_numpy()
image.to_pillow()
```

Every operation returns a **new** `Image` carrying `source` and `metadata`
forward, so provenance survives a preprocessing chain.

`Image.open()` normalises whatever the file contained — palette, greyscale,
16-bit, RGBA — to 3-channel BGR `uint8`, so no consumer has to branch on it.

---

## Domain models

`TextBlock`, `Detection` and `TemplateMatch` (in `aetheros.vision.models`) are
rectangles with a payload:

```python
block.text, block.confidence
block.left, block.top, block.right, block.bottom
block.width, block.height, block.area
block.center                # (x, y) — what you click
block.bbox
block.contains(x, y)
block.matches("RELIANCE", case_sensitive=False)
block.to_dict()             # JSON-encodable, for tool results
```

---

## Providers

| Provider | Interface | Dependency | Available when |
|---|---|---|---|
| `OpenCVProvider` | `VisionProvider` | opencv | always |
| `OpenCVTemplateProvider` | `TemplateProvider` | opencv | always |
| `PaddleOCRProvider` | `OCRProvider` | `paddleocr` + `paddlepaddle` | both installed |
| `YOLOProvider` | `DetectionProvider` | `ultralytics` | installed **and** weights present |

Every provider exposes `name`, `version` and `available`. `available` is what
makes graceful degradation possible: it is checked with
`importlib.util.find_spec` so a missing optional package costs neither an
`ImportError` at import time nor the several seconds it takes to import paddle or
torch.

### PaddleOCRProvider

```python
PaddleOCRProvider(language="en", use_angle_cls=False)
```

The model is built **lazily**, on first `read_text`, and cached — so registering
the provider during bootstrap is free, and a process that never reads text never
loads a model.

Three version-specific details worth knowing, because each one either silently
returns nothing or fails on every single image:

* PaddleOCR 3.x results subclass `dict` and expose `rec_texts` / `rec_scores` /
  `rec_polys`. The `.json` property wraps everything in a `{"res": ...}`
  envelope, so `result.json.get("rec_texts")` is *always* empty. The provider
  reads the fields directly and falls back to the envelope, then to the 2.x
  nested-list format.
* `use_angle_cls` was renamed `use_textline_orientation`.
* **oneDNN is disabled** via `enable_mkldnn=False`. PaddleOCR enables it by
  default on CPU, and on paddlepaddle 3.x the detection model then fails to
  lower under the PIR executor:

  ```
  NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute
  not support [pir::ArrayAttribute<pir::DoubleAttribute>]
  ```

  Every `read_text` call raises `VISION_OCR_FAILED` until it is turned off.
  Setting `FLAGS_use_mkldnn=0` in the environment does **not** work — PaddleX
  passes `run_mode="mkldnn"` to the predictor explicitly, and an explicit
  `run_mode` beats the global flag. The constructor argument is the only switch
  that takes effect. It selects the plain CPU executor, which also keeps results
  reproducible across machines.

The provider also sets `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK` (with
`setdefault`, so an operator's own value wins) before importing paddleocr.
PaddleX otherwise probes its model hosts on every construction even when the
models are already cached, which costs a few seconds per process and makes a
machine with no route to those hosts wait on a request that cannot succeed.
Genuinely missing models are still downloaded; only the reachability probe is
skipped.

### YOLOProvider

```python
YOLOProvider(model="yolo11n.pt", allow_download=False)
```

`allow_download` defaults to `False` and bootstrap never overrides it: startup
must not reach for the network. Detection therefore stays **off** unless
`AETHEROS_YOLO_WEIGHTS` points at a weights file that exists.

---

## Tools

All five are registered in the `vision` category and are async.

| Tool | Arguments | Returns |
|---|---|---|
| `read_screen_text` | — | `width, height, count, text, blocks` |
| `read_image_text` | `path: str` | `path, width, height, count, text, blocks` |
| `detect_screen_objects` | — | `width, height, count, objects` |
| `find_text` | `query: str` | `query, found, count, matches` |
| `analyze_screen` | — | `width, height, text, blocks, capabilities, objects` |

Every result is JSON-encodable — it is serialised for the model, so a stray
dataclass or ndarray in the payload would break the whole turn.

`analyze_screen` captures **once** and runs both analyses on that frame: two
grabs would be two different moments in a moving market. It degrades rather than
fails — no detector means `objects: []` alongside the OCR result you would
otherwise have lost.

`read_image_text` is the headless path. It never resolves `ScreenService`.

Registration happens at **import time**, via the `@tool` decorator;
`Bootstrapper._bootstrap_tools()` imports the module. Nothing else is needed.

---

## Screen capture

Lives in `aetheros/desktop/screen/`:

```python
from aetheros.core.container import container
from aetheros.desktop.screen.controller import ScreenService

screen: ScreenService = container.resolve(ScreenService)

frame = await screen.capture()                                   # BGR ndarray
frame = await screen.capture_region(left=0, top=0, width=800, height=600)
await screen.save(frame, "shot.png")
await screen.size()                                              # (width, height)
await screen.monitors()
```

`MSSScreen` slices BGRA down to BGR and returns a contiguous **copy**: mss hands
back a view on a buffer it reuses, so the next grab would mutate a frame the
caller still holds. `monitors()` drops mss's index 0, which is the virtual
bounding box spanning every screen rather than a monitor.

---

## Bootstrap and DI

`Bootstrapper.start()` wires vision in `_bootstrap_vision()`:

```text
container.register_singleton(OpenCVProvider,         ...)
container.register_singleton(OpenCVTemplateProvider, ...)
container.register_singleton(PaddleOCRProvider,      ...)
container.register_singleton(VisionService,          ...)   # lazy factory
```

Registration is **lazy** by design. An eagerly constructed `VisionService` would
drag in the OCR provider, and shutdown would then have to load a model purely in
order to close it.

`_bootstrap_desktop()` registers `ScreenService`, and treats a `VisionError` from
`MSSScreen()` as "no display": it logs a warning and continues, because the
trading-analysis core does not need a screen. Any other exception propagates —
that is a real defect, not a headless machine.

Shutdown closes each provider independently, so one backend failing to release a
model does not leave the others loaded.

---

## Errors

Everything raises `aetheros.core.errors.vision_error.VisionError`, which prefixes
its codes with `VISION_`:

| Code | Raised when |
|---|---|
| `VISION_INVALID_IMAGE` | data is None, not an ndarray, or the wrong rank |
| `VISION_EMPTY_IMAGE` | zero-sized array |
| `VISION_INVALID_COLOR_SPACE` | declared colour space contradicts the channel count |
| `VISION_INVALID_ARGUMENT` | bad geometry, kernel, threshold or empty query |
| `VISION_IMAGE_NOT_FOUND` | file does not exist |
| `VISION_IMAGE_LOAD_FAILED` | file is not a decodable image |
| `VISION_SAVE_FAILED` | target directory missing, or the encoder refused |
| `VISION_OCR_UNAVAILABLE` | paddleocr or paddlepaddle not installed |
| `VISION_OCR_INIT_FAILED` | model construction failed |
| `VISION_OCR_FAILED` | recognition raised |
| `VISION_DETECTION_UNAVAILABLE` | no detector configured, or ultralytics missing |
| `VISION_DETECTION_MODEL_MISSING` | weights path does not exist |
| `VISION_DETECTION_INIT_FAILED` | model load failed |
| `VISION_DETECTION_FAILED` | inference raised |
| `VISION_TEMPLATE_UNAVAILABLE` | no template provider configured |
| `VISION_TEMPLATE_TOO_LARGE` | template is bigger than the image |
| `VISION_TEMPLATE_MATCH_FAILED` | matching raised |
| `VISION_SCREEN_UNAVAILABLE` | mss could not open a display |
| `VISION_INVALID_REGION` | non-positive capture width or height |
| `VISION_INVALID_MONITOR` | monitor index out of range |
| `VISION_CAPTURE_FAILED` | the grab itself failed |

Each carries `code`, `message`, an actionable `hint`, an `ErrorContext`
(`module`, `operation`, `details`) and the original `cause`. Note what is *not*
an error: an empty OCR result. "No readable text" is a valid answer, and turning
it into an exception would make blank screens indistinguishable from broken
models.

---

## Verifying it actually works

An OCR backend that imports cleanly and returns `[]` for every image passes every
mocked test in the suite. So there is a real check:

```bash
python -m aetheros.vision.main
```

It reports PASS / FAIL / SKIP for AetherOS startup, service registration, tool
registration and discovery, image processing, OCR against a known image, error
handling, screenshot capture, the end-to-end flow through the tool registry, and
clean shutdown — and exits non-zero if anything failed. Checks that need a
display or an optional package report SKIP rather than FAIL, so a headless
machine gets a truthful result instead of a misleading failure.

The known image comes from `aetheros.vision.selfcheck`, which renders
`AETHEROS / VISION TEST / HELLO WORLD` as high-contrast black-on-white capitals:

```python
from aetheros.vision import selfcheck

image = selfcheck.reference_image()
selfcheck.expected_words()               # {"AETHEROS", "VISION", "TEST", ...}
selfcheck.recognised_words(ocr_output)   # normalised for comparison
```

Generating it in code rather than committing a PNG keeps the check reproducible,
and the same module backs both `main` and the integration tests, so the two agree
on what "working" means.

---

## Tests

```bash
# Fast, offline, no display, no model downloads
pytest tests/vision

# Real PaddleOCR against the reference image
pytest -m integration tests/vision
```

The default run is fully offline. Only two seams are faked — the OCR model
(`provider._build`) and the OS screen grab (`mss.mss`) — so `_prepare`, `_parse`,
every tool body and the whole service layer are the real code under test.

The `integration` tests are gated on `paddleocr` **and** `paddle` being
importable and are skipped otherwise. The first run may download recognition
models, which needs network access; nothing else in the suite does.

---

## Dependencies

Required: `opencv-python`, `numpy`, `pillow`, `mss`.

Optional: `paddleocr` + `paddlepaddle` for OCR, `ultralytics` for detection.
Without them the engine still starts, `capabilities()` reports the gap, and the
affected tools fail individually with a clear code.

---

## Known limitations

* `aetheros/core/interfaces/vision_provider.py` is a second, unused provider
  abstraction predating this one. Nothing imports it; it should be removed.
* `aetheros/desktop/screenshot/` imports `core.interfaces.screenshot_controller`,
  which does not exist. It is superseded by `aetheros/desktop/screen/` and is
  dead on import.
* Detection is untested against real weights — `YOLOProvider` is covered only
  with a stubbed model, since shipping or downloading weights in CI is not
  something the test suite should do.
