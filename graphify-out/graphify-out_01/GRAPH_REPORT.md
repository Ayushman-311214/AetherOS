# Graph Report - AetherOS  (2026-09-02)

## Corpus Check
- 218 files · ~177,036 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4686 nodes · 10279 edges · 196 communities (156 shown, 29 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1003 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Hud Components
- Desktop Components
- Vision Components
- Voice Components
- Vision Components
- Tool Components
- Agents Components
- Llm Components
- Scene Components
- Agents Components
- Vision Components
- Tts Components
- Desktop Components
- Desktop Components
- Desktop Components
- Hud Components
- Vision Components
- Hud Components
- Agents Components
- Context Components
- State Components
- Desktop Components
- Voice Components
- Vision Components
- Voice Components
- Vision Components
- Voice Components
- Vision Components
- Agents Components
- Desktop Components
- Voice Components
- Window Components
- Process Components
- Bootstrap Components
- Bootstrapper Components
- File Components
- Vision Components
- Tools Components
- Screen Components
- Llm Components
- Vision Components
- Agents Components
- Vision Components
- Browser Components
- Browser Components
- Application Components
- Calls Components
- Mouse Components
- Vision Components
- Events Components
- Clipboard Components
- Vision Components
- Hud Components
- Agents Components
- Clipboard Components
- Desktop Components
- Desktop Components
- Hud Components
- Vision Components
- Hud Components
- Interfaces Components
- Llm Components
- Conftest Components
- Tools Components
- Agents Components
- Cli Components
- Interfaces Components
- Window Components
- Voice Components
- Agents Components
- Agents Components
- Desktop Components
- Browser Components
- Hud Components
- Window Components
- Process Components
- Agents Components
- Desktop Components
- Calls Components
- Hud Components
- Cli Components
- Desktop Components
- Bootstrap Components
- Browser Components
- Vision Components
- State Components
- Desktop Components
- Input Components
- Hud Components
- Screen Components
- Stt Components
- Tts Components
- Llm Components
- Tools Components
- Desktop Components
- Screen Components
- Window Components
- Tools Components
- Vision Components
- Desktop Components
- Vision Components
- Keyboard Components
- Mouse Components
- Hud Components
- Agents Components
- Planner Components
- Cli Components
- Desktop Components
- Process Components
- Desktop Components
- Desktop Components
- Hud Components
- Hud Components
- Llm Components
- Hud Components
- Hud Components
- Container Components
- Renderer Components
- Agents Components
- Hud Components
- Interface Components
- Application Components
- Planner Components
- Llm Components
- Tool Components
- Tools Components
- Vision Components
- Mouse Components
- Application Components
- Desktop Components
- Tool Components
- Tools Components
- Vision Components
- Window Components
- Screen Components
- Desktop Components
- Cli Components
- Desktop Components
- Schema Components
- Llm Components
- Cli Components
- Llm Components
- Hud Components
- Cli Components
- Desktop Components
- Desktop Components
- Browser Components
- Interfaces Components
- Llm Components
- Tools Components
- Vision Components
- Hud Components
- Browser Components
- Vision Components
- Vision Components
- Vision Components
- Audit Components
- Hud Components
- Hud Components
- Audit Components
- Audit Components
- Browser Components
- Errors Components
- Llm Components
- Events Components
- Vision Components
- Vision Components
- Audit Components
- Audit Components
- Bootstrapper Components
- Bootstrapper Components
- Browser Components
- Browser Components
- Browser Components
- Interfaces Components
- Interfaces Components
- Interfaces Components
- Interfaces Components
- Mouse Components
- Mouse Components
- Interfaces Components
- Interfaces Components
- Interfaces Components
- Desktop Components
- Pkg Components

## God Nodes (most connected - your core abstractions)
1. `Image` - 171 edges
2. `AgentState` - 109 edges
3. `ToolRegistry` - 108 edges
4. `ContextBuilder` - 107 edges
5. `tool()` - 103 edges
6. `define()` - 92 edges
7. `AgentPlanner` - 91 edges
8. `get_logger()` - 81 edges
9. `DesktopError` - 76 edges
10. `AgentContext` - 75 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py
- `TestToolExposure` --uses--> `ContextConfig`  [INFERRED]
  tests/agents/test_agent_context.py → src/aetheros/agents/context.py
- `TestSerializationAndLogging` --uses--> `IterationInfo`  [INFERRED]
  tests/agents/test_agent_context.py → src/aetheros/agents/context.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **HUD Status and Instruction Display** — hud_zoom_hud_interface, hud_zoom_transcribing, hud_zoom_move_mouse_300_pixels [INFERRED 0.75]
- **Mouse Automation Layered Architecture** — src_aetheros_vision_test_mouse_interface, src_aetheros_vision_test_pyautogui_backend, src_aetheros_vision_test_mouse_service [EXTRACTED 1.00]

## Communities (196 total, 29 thin omitted)

### Community 0 - "Hud Components"
Cohesion: 0.04
Nodes (70): Event, Base class for all events in AetherOS. Every event inherits from this class., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM., The LLM produced a response., The LLM requested a tool from the existing ToolRegistry. (+62 more)

### Community 1 - "Desktop Components"
Cohesion: 0.04
Nodes (59): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not… (+51 more)

### Community 2 - "Vision Components"
Cohesion: 0.04
Nodes (27): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+19 more)

### Community 3 - "Voice Components"
Cohesion: 0.03
Nodes (43): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+35 more)

### Community 4 - "Vision Components"
Cohesion: 0.05
Nodes (43): BaseError, ErrorContext, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, HUDError, HUDProcessError, HUDUnavailableError (+35 more)

### Community 5 - "Tool Components"
Cohesion: 0.06
Nodes (49): Executes registered AetherOS tools., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes(), asyncio (+41 more)

### Community 6 - "Agents Components"
Cohesion: 0.06
Nodes (32): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, _call(), asyncio, The invariant the provider enforces, asserted over the whole payload., Reads are lock-free because state hands back immutable snapshots. (+24 more)

### Community 7 - "Llm Components"
Cohesion: 0.09
Nodes (36): answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas…, add(), _assert_every_tool_message_is_answerable() (+28 more)

### Community 8 - "Scene Components"
Cohesion: 0.04
Nodes (36): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+28 more)

### Community 9 - "Agents Components"
Cohesion: 0.08
Nodes (21): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _answer(), _calls(), Argument names may be logged; argument values may not., A response with prose and no tool calls ends the run. (+13 more)

### Community 10 - "Vision Components"
Cohesion: 0.05
Nodes (32): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+24 more)

### Community 11 - "Tts Components"
Cohesion: 0.05
Nodes (27): Future, ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Synthesize and play `text`, returning when playback ends. Must not block the… (+19 more)

### Community 12 - "Desktop Components"
Cohesion: 0.08
Nodes (39): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, An ordered list of steps and the policy for running them., Build a workflow from a plain dict, as ``run_workflow`` receives it., The same workflow, validated instead of executed., Workflow, Calls, engine() (+31 more)

### Community 13 - "Desktop Components"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 14 - "Desktop Components"
Cohesion: 0.05
Nodes (41): __init__(), Application, Main AetherOS application. Responsible for starting and shutting down the…, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+33 more)

### Community 15 - "Hud Components"
Cohesion: 0.06
Nodes (24): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+16 more)

### Community 16 - "Vision Components"
Cohesion: 0.05
Nodes (18): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., Any (+10 more)

### Community 17 - "Hud Components"
Cohesion: 0.07
Nodes (41): QApplication, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window…, Run driven by a parent process over stdio. This is how HUDService starts the… (+33 more)

### Community 18 - "Agents Components"
Cohesion: 0.08
Nodes (33): ContextBuilder, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, builder(), context(), _FailingProvider, move_mouse(), planner(), provider() (+25 more)

### Community 19 - "Context Components"
Cohesion: 0.07
Nodes (22): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, builder(), Any, fixture, Tests for the agent context layer. The properties under test are the ones the…, A snapshot that can be edited after assembly is not a snapshot., The payload has to be accepted by the engine that already exists. (+14 more)

### Community 20 - "State Components"
Cohesion: 0.07
Nodes (10): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, asyncio, parametrize, TestCompletion, TestErrors, TestInitialState (+2 more)

### Community 21 - "Desktop Components"
Cohesion: 0.07
Nodes (36): BaseSettings, get_settings(), Singleton Settings object., Settings, _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every… (+28 more)

### Community 22 - "Voice Components"
Cohesion: 0.06
Nodes (41): LevelCallback, AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed. (+33 more)

### Community 23 - "Vision Components"
Cohesion: 0.08
Nodes (22): asyncio, Path, Tests for the vision tools and their registry integration. These exercise the…, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error. (+14 more)

### Community 24 - "Voice Components"
Cohesion: 0.06
Nodes (24): Any, Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:… (+16 more)

### Community 25 - "Vision Components"
Cohesion: 0.06
Nodes (26): Build the YOLO detector when its package and weights are both present. Returns…, High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a… (+18 more)

### Community 26 - "Voice Components"
Cohesion: 0.06
Nodes (27): AudioCapture, Microphone capture with energy-based silence detection. PortAudio delivers…, _flag(), _integer(), _number(), Build a configuration from AETHEROS_* environment variables., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always… (+19 more)

### Community 27 - "Vision Components"
Cohesion: 0.06
Nodes (21): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+13 more)

### Community 28 - "Agents Components"
Cohesion: 0.06
Nodes (18): PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because… (+10 more)

### Community 29 - "Desktop Components"
Cohesion: 0.09
Nodes (24): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard(), PsutilProcess, Any, Path (+16 more)

### Community 30 - "Voice Components"
Cohesion: 0.07
Nodes (23): Assemble the context for ``state``'s current iteration. Synchronous and side-…, LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, make_provider(), The scripted provider class, for tests that need it directly. (+15 more)

### Community 31 - "Window Components"
Cohesion: 0.07
Nodes (18): QMouseEvent, QPaintEvent, QWidget, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own…, Show the overlay and begin animating. (+10 more)

### Community 32 - "Process Components"
Cohesion: 0.06
Nodes (20): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+12 more)

### Community 33 - "Bootstrap Components"
Cohesion: 0.07
Nodes (26): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+18 more)

### Community 34 - "Bootstrapper Components"
Cohesion: 0.09
Nodes (6): Bootstrapper, Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Whether Playwright can be imported. find_spec rather than a try/import:…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events.

### Community 35 - "File Components"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 36 - "Vision Components"
Cohesion: 0.13
Nodes (17): EnvelopeResult, _ocr_with(), asyncio, Unit tests for the concrete vision providers. The OpenCV and template providers…, Stands in for a built PaddleOCR pipeline. Records the frame it was handed so a…, A PaddleOCR 3.x result seen through its documented ``json`` accessor. The…, A real provider whose model construction is replaced by a stub. ``_build`` is…, The channel-order regression. PaddleX's reader defaults to ``format="BGR"`` and… (+9 more)

### Community 37 - "Tools Components"
Cohesion: 0.07
Nodes (23): NotAnImportableType, anything(), containers(), mixed_defaults(), optionals(), Any, Tool schema generation. These tests deliberately live in a module that starts…, A tool annotated with a name that is not importable at runtime must still… (+15 more)

### Community 38 - "Screen Components"
Cohesion: 0.10
Nodes (18): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, fake_sct(), FakeSCT, mss_screen(), fixture (+10 more)

### Community 39 - "Llm Components"
Cohesion: 0.09
Nodes (22): AgentLoopConfig, Bounds and behaviour for a single loop run., add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation… (+14 more)

### Community 40 - "Vision Components"
Cohesion: 0.08
Nodes (17): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, parametrize, Scales that would make the template larger than the image are dropped rather…, TestTemplateProvider (+9 more)

### Community 41 - "Agents Components"
Cohesion: 0.08
Nodes (15): ErrorRecord, BaseException, Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would…, Open the transcript with the system prompt and the goal., Claim the next iteration, or refuse. Check-then-increment is exactly why the… (+7 more)

### Community 42 - "Vision Components"
Cohesion: 0.10
Nodes (10): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, A fixed COLOR_BGR2GRAY would weight red and blue the wrong way round for RGB…, TestOpenCVOperations (+2 more)

### Community 43 - "Browser Components"
Cohesion: 0.06
Nodes (15): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page URL., Return the current page HTML. (+7 more)

### Community 44 - "Browser Components"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 45 - "Application Components"
Cohesion: 0.13
Nodes (19): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+11 more)

### Community 46 - "Calls Components"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 47 - "Mouse Components"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 48 - "Vision Components"
Cohesion: 0.10
Nodes (10): make_fake_ocr(), asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText (+2 more)

### Community 49 - "Events Components"
Cohesion: 0.10
Nodes (18): EventHandler, EventBus, Central event bus for AetherOS. Features: - Sync + Async handlers - Multiple…, Register an event handler., Publish an event. Every subscriber receives the event., get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application… (+10 more)

### Community 50 - "Clipboard Components"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 51 - "Vision Components"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 52 - "Hud Components"
Cohesion: 0.09
Nodes (14): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+6 more)

### Community 53 - "Agents Components"
Cohesion: 0.10
Nodes (13): A call the planner refused to pass on, and why. Carries enough to answer the…, Whether a ``tool`` message can carry this rejection back. A provider rejects a…, RejectedToolCall, Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read., A tool the model asked for, tagged with the iteration that asked. Adapts…, Names only. The safe projection for logs — see module docstring. (+5 more)

### Community 54 - "Clipboard Components"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 55 - "Desktop Components"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 56 - "Desktop Components"
Cohesion: 0.09
Nodes (16): _as_float(), _clamp_seconds(), Any, Attempts to make, resolved against configuration and clamped., Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., Coerce a duration to a non-negative float no larger than ``ceiling``., One tool call, with the conditions around it. Fields ------ name Label used in… (+8 more)

### Community 57 - "Hud Components"
Cohesion: 0.09
Nodes (17): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+9 more)

### Community 58 - "Vision Components"
Cohesion: 0.08
Nodes (13): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, The core assertion: the pipeline returns text, not an empty list. (+5 more)

### Community 59 - "Hud Components"
Cohesion: 0.09
Nodes (11): IO, decode(), PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived. (+3 more)

### Community 60 - "Interfaces Components"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 61 - "Llm Components"
Cohesion: 0.11
Nodes (15): LLMToolLoop, Any, Main LLM ↔ ToolExecutor loop., Run the loop and return the model's final answer text., Run the loop and return the full record of what happened., Await an optional progress hook without letting it break the run. A hook…, Rebuild the assistant turn that requested these tool calls., Turn an execution outcome into text the model can read. (+7 more)

### Community 62 - "Conftest Components"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 63 - "Tools Components"
Cohesion: 0.12
Nodes (17): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Agent context assembly. One :class:`AgentContext` is everything the model needs…, Agent planner. One responsibility: ``GOAL -> the next action``. The planner…, public_parameters(), Any, Signature, Annotation resolution shared by the schema generator and the validator. Every… (+9 more)

### Community 64 - "Agents Components"
Cohesion: 0.11
Nodes (14): AgentStatus, Enum, str, Agent execution state. One :class:`AgentState` is the complete, explicit record…, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…, What came back from one tool call. A failed tool is data, not an exception: the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, Every result recorded against one call id. (+6 more)

### Community 65 - "Cli Components"
Cohesion: 0.09
Nodes (12): CLIUI, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI., MonkeyPatch, ``errors="replace"`` is the second half of the fix. Without it a single…, The regression itself: this raised UnicodeEncodeError from _show_logo. (+4 more)

### Community 66 - "Interfaces Components"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 67 - "Window Components"
Cohesion: 0.11
Nodes (12): Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title., Returns the currently active window. (+4 more)

### Community 68 - "Voice Components"
Cohesion: 0.10
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 69 - "Agents Components"
Cohesion: 0.08
Nodes (15): _clamp(), Any, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., The tool name inside a generated schema, or ``""`` if it is malformed. Tolerant…, Shorthand for ``build(state).messages()``. (+7 more)

### Community 70 - "Agents Components"
Cohesion: 0.10
Nodes (14): Agent layer. Three pieces so far. :mod:`~aetheros.agents.state` is the…, ActionType, PlanResult, Enum, str, Planner actions and results. The value types the planner returns. They exist so…, What one planning round produced. The question the planner answers is singular…, What the planner decided. ``str``-valued so a serialized action reads as… (+6 more)

### Community 71 - "Desktop Components"
Cohesion: 0.11
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 72 - "Browser Components"
Cohesion: 0.17
Nodes (25): _browser(), browser_back(), browser_forward(), browser_reload(), browser_screenshot(), click_element(), close_browser(), current_url() (+17 more)

### Community 73 - "Hud Components"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 74 - "Window Components"
Cohesion: 0.10
Nodes (14): Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Poll until a matching window appears, or the timeout expires. Polling rather…, Poll until a matching window holds focus, or the timeout expires. Distinct from…, Poll ``probe`` until it returns a window, bounded by ``timeout``. The bound is…, Synchronous selector matching, for use inside poll probes. (+6 more)

### Community 75 - "Process Components"
Cohesion: 0.13
Nodes (15): Process, _clip(), CommandResult, _decode(), Path, Command execution. Three decisions in here are load-bearing. **A non-zero exit…, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment… (+7 more)

### Community 76 - "Agents Components"
Cohesion: 0.17
Nodes (11): Observation, Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, Something the agent noticed that is not itself a tool result. Kept separate…, The transcript in provider wire format, ready to send., ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-… (+3 more)

### Community 77 - "Desktop Components"
Cohesion: 0.17
Nodes (10): Human-readable condition, used when the caller did not supply one., Any, Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``., A full snapshot, which carries the bounds along with everything else., High-level window service. Backed by a :class:`WindowController`; holds no…, Full snapshot in one call. Uses the backend's ``describe`` when it has one --… (+2 more)

### Community 78 - "Calls Components"
Cohesion: 0.12
Nodes (11): parse_llm_response(), ParsedResponse, Normalised view of one provider response., Normalise a provider tool-call response. Never raises. Accepts the shape…, parametrize, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn. (+3 more)

### Community 79 - "Hud Components"
Cohesion: 0.12
Nodes (16): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+8 more)

### Community 80 - "Cli Components"
Cohesion: 0.09
Nodes (8): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Show LLM provider status and model information., Send a message to the LLM, letting it call AetherOS tools., Render an agent-loop result for the terminal., Register a CLI command., Execute a parsed command.

### Community 81 - "Desktop Components"
Cohesion: 0.12
Nodes (8): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 82 - "Bootstrap Components"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 83 - "Browser Components"
Cohesion: 0.09
Nodes (3): BrowserService, Release the browser if one is still open. Called from…, High-level browser service. Responsible for coordinating browser operations.…

### Community 84 - "Vision Components"
Cohesion: 0.13
Nodes (17): bgr_image(), fake_ocr(), FakeOCRProvider, isolated_container(), make_unclosable_ocr(), fixture, Fixtures for the vision test suite. The fakes here implement the real provider…, A small BGR image whose channels are all different. Uniform grey would hide a… (+9 more)

### Community 85 - "State Components"
Cohesion: 0.14
Nodes (9): call(), failed_result(), ok_result(), _populated_state(), fixture, Tests for the agent execution state. The state layer has no interesting…, state(), TestDescribe (+1 more)

### Community 86 - "Desktop Components"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 87 - "Input Components"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 88 - "Hud Components"
Cohesion: 0.10
Nodes (8): FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first., The state of every snapshot sent, in order., Stands in for HUDProcess without launching anything. Records what the service…

### Community 89 - "Screen Components"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 90 - "Stt Components"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 91 - "Tts Components"
Cohesion: 0.13
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 92 - "Llm Components"
Cohesion: 0.12
Nodes (9): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Release provider resources., Returns True if provider is healthy. (+1 more)

### Community 93 - "Tools Components"
Cohesion: 0.18
Nodes (11): Exception, ToolError, is_unconstrained(), Whether ``annotation`` places no checkable constraint on a value. Covers the…, Any, Signature, Validates tool arguments before execution. Arguments arriving from an LLM are…, isinstance check with the numeric-tower adjustments JSON requires. (+3 more)

### Community 94 - "Desktop Components"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 95 - "Screen Components"
Cohesion: 0.19
Nodes (10): Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, ScreenService, make_fake_screen(), asyncio, A capture failure must surface, not be turned into an empty frame that OCR… (+2 more)

### Community 96 - "Window Components"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 97 - "Tools Components"
Cohesion: 0.12
Nodes (8): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery, AetherOS Tool Framework Public API for tool registration, discovery, schema…, Metadata describing a tool., ToolDefinition

### Community 98 - "Vision Components"
Cohesion: 0.15
Nodes (7): make_fake_detector(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., Positional wiring is rejected: ``VisionService(ocr, cv)`` and…, TestDetectObjects, TestServiceInitialisation, TestShutdown

### Community 99 - "Desktop Components"
Cohesion: 0.22
Nodes (8): Any, Resolve to a handle and confirm the window still exists. Checked on every…, Bring a window to the foreground and give it keyboard focus. Verified rather…, Ask a window to close. ``WM_CLOSE`` is a request, and deliberately so: the…, Move without resizing. ``MoveWindow`` sets position and size together, so the…, Resize without moving. A maximized window ignores this, so it is restored first…, Window control through the Win32 API. Windows are addressed by ``hwnd``…, Win32Window

### Community 100 - "Vision Components"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 101 - "Keyboard Components"
Cohesion: 0.12
Nodes (8): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab

### Community 102 - "Mouse Components"
Cohesion: 0.11
Nodes (3): PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 103 - "Hud Components"
Cohesion: 0.13
Nodes (10): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:…, HUDState, Enum (+2 more)

### Community 104 - "Agents Components"
Cohesion: 0.12
Nodes (9): _describe_call(), _describe_result(), IterationInfo, Where the run is in its budget. Carried explicitly because the model behaves…, The single system message: instructions, goal, budget, digests. Everything that…, One digest line for a call: names, never values. The model already has the…, One digest line for a result: outcome, and why if it failed., Shorten ``text`` to ``limit`` characters, saying so explicitly. (+1 more)

### Community 105 - "Planner Components"
Cohesion: 0.16
Nodes (9): No next step exists. ``error_type`` names the kind of wall hit., Any, Exception, Ask the model what to do next, and describe the answer as an action. The only…, Turn a provider response into a plan. Pure and deterministic. ``response`` is…, Refuse to plan when there is nothing a next action could mean. Only one…, Describe a provider failure as a ``fail`` action. The cause is kept as an…, Attach provenance. Every plan carries the model that produced it, because… (+1 more)

### Community 106 - "Cli Components"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 107 - "Desktop Components"
Cohesion: 0.15
Nodes (14): _parse_condition(), parse_mode(), parse_region(), Any, Parse a caller-supplied comparison mode. Shared by the ``verify_action`` tool…, Parse a ``[left, top, width, height]`` screen region., Coerce the many shapes a coordinate pair arrives in. The model sends ``[800,…, Build a request from a plain dict, as a workflow step carries it. Unknown keys… (+6 more)

### Community 108 - "Process Components"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 109 - "Desktop Components"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 111 - "Hud Components"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, One arc group in the ring system., Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, RingSpec

### Community 112 - "Hud Components"
Cohesion: 0.12
Nodes (8): Wrap a snapshot for transport., snapshot_message(), Adopt a new snapshot, starting a style transition if the state changed., Update the live audio level without changing state., HUDSnapshot, Copy with a new state, clearing fields the new state retires., Rebuild from to_dict(), tolerating missing or malformed keys., Everything the renderer needs to draw one moment. Immutable and picklable: this…

### Community 113 - "Llm Components"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 114 - "Hud Components"
Cohesion: 0.16
Nodes (10): QLinearGradient, QPointF, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side… (+2 more)

### Community 115 - "Hud Components"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 116 - "Container Components"
Cohesion: 0.18
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 117 - "Renderer Components"
Cohesion: 0.14
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 118 - "Agents Components"
Cohesion: 0.18
Nodes (4): Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, The provider-facing shape, matching ``LLMToolLoop`` exactly., TestMessages

### Community 119 - "Hud Components"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, A ring of fine radial graduations. Pure technical texture — the detail that…, TickLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 120 - "Interface Components"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 121 - "Application Components"
Cohesion: 0.19
Nodes (6): main(), Application, Restart the application., Main AetherOS application. Responsible for managing the application's…, Returns whether the application is running., Start the application.

### Community 122 - "Planner Components"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 123 - "Llm Components"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 124 - "Tool Components"
Cohesion: 0.22
Nodes (8): get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, every_scalar(), move_mouse(), Move the mouse by a relative offset., Whatever is generated has to survive the trip to the provider., One parameter per JSON scalar type., TestGetLlmTools

### Community 125 - "Tools Components"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…

### Community 126 - "Vision Components"
Cohesion: 0.40
Nodes (12): analyze_screen(), _blocks(), _capture(), detect_screen_objects(), find_text(), Any, OCR a saved image. Kept separate from read_screen_text so text recognition can…, Capture the screen as a vision Image. ScreenService returns a raw BGR… (+4 more)

### Community 127 - "Mouse Components"
Cohesion: 0.21
Nodes (3): MouseController, ABC, Abstract interface for mouse control. Every mouse implementation must implement…

### Community 128 - "Application Components"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 129 - "Desktop Components"
Cohesion: 0.21
Nodes (7): ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary)., Grab a region and drop the alpha channel. mss hands back BGRA; slicing to three…, Capture the primary monitor. Returns: BGR NumPy image of shape (height, width,…, Capture a rectangular region.

### Community 130 - "Tool Components"
Cohesion: 0.17
Nodes (6): fixture, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations…, A parameter with no default that is missing from ``required`` lets the model…, An open schema lets a model invent an argument, which arrives as an unexpected…, TestEveryRegisteredToolHasAUsableSchema

### Community 131 - "Tools Components"
Cohesion: 0.17
Nodes (7): ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, Asserts against the process-wide registry, which the @tool decorator populates…, TestRegisteredToolSurface

### Community 132 - "Vision Components"
Cohesion: 0.21
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 133 - "Window Components"
Cohesion: 0.18
Nodes (5): ABC, A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 134 - "Screen Components"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 135 - "Desktop Components"
Cohesion: 0.24
Nodes (9): keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every…, _swapped() (+1 more)

### Community 136 - "Cli Components"
Cohesion: 0.38
Nodes (5): CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 137 - "Desktop Components"
Cohesion: 0.22
Nodes (5): Coerce whatever the caller passed into a window handle. Accepts a…, Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, Fail with a dependency error rather than an AttributeError on ``None``., _require()

### Community 138 - "Schema Components"
Cohesion: 0.31
Nodes (5): Any, Generates JSON schemas for LLM function calling., ToolSchemaGenerator, Two generators must agree; the module singleton holds no per-tool state., TestSchemaEnvelope

### Community 139 - "Llm Components"
Cohesion: 0.33
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 140 - "Cli Components"
Cohesion: 0.22
Nodes (6): _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, cp1252_stdout(), fixture, The terminal UI must not be able to abort the application. Bootstrap succeeding…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…

### Community 142 - "Hud Components"
Cohesion: 0.25
Nodes (8): Error State, Executing State, Idle State, AetherOS HUD States Reference, Listening State, Speaking State, Thinking State, Transcribing State

### Community 143 - "Cli Components"
Cohesion: 0.32
Nodes (3): CLIRuntime, Read one prompt line without blocking the event loop. `console.input()` blocks…, Interactive AetherOS CLI runtime.

### Community 144 - "Desktop Components"
Cohesion: 0.25
Nodes (5): ndarray, Path, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region., Save a captured frame to disk.

### Community 145 - "Desktop Components"
Cohesion: 0.25
Nodes (4): Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., The foreground window, or ``None`` when nothing is focused. ``None`` is a real…, Full snapshot of one window. Not on the interface, which exposes title,…

### Community 146 - "Browser Components"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 147 - "Interfaces Components"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 149 - "Tools Components"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 150 - "Vision Components"
Cohesion: 0.47
Nodes (3): Path, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame…, TestMSSSave

### Community 151 - "Hud Components"
Cohesion: 0.40
Nodes (5): HUD Zoom Image, AetherOS, Futuristic HUD Interface, Move the Mouse 300 Pixels, Transcribing Status

### Community 152 - "Browser Components"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 153 - "Vision Components"
Cohesion: 0.70
Nodes (5): Vision Architecture Diagram: Mouse Automation Layers, Mouse Interface (Abstract), MouseService or High-Level API, Mouse Tool Definition, PyAutoGUI Backend

### Community 154 - "Vision Components"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 156 - "Audit Components"
Cohesion: 0.67
Nodes (4): Go Button, Output Display, RELIANCE 2847.65, Symbol Input

### Community 157 - "Hud Components"
Cohesion: 0.67
Nodes (4): HUD Text-Only Screenshot, AetherOS, Move the Mouse 300 Pixels Command, Transcribing Status

### Community 167 - "Vision Components"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out.…

### Community 168 - "Vision Components"
Cohesion: 0.67
Nodes (3): executor(), fixture, An executor over the process-wide registry, which is where @tool registers.

## Knowledge Gaps
- **16 isolated node(s):** `AetherOS`, `AetherOS Sandbox`, `Tool audit sandbox`, `RELIANCE 2847.65`, `Idle State` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1846 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `Desktop Components` to `Desktop Components`, `Voice Components`, `Vision Components`, `Agents Components`, `Cli Components`, `Vision Components`, `Tts Components`, `Desktop Components`, `Cli Components`, `Vision Components`, `Desktop Components`, `Voice Components`, `Voice Components`, `Process Components`, `Bootstrapper Components`, `Events Components`, `Clipboard Components`, `Hud Components`, `Clipboard Components`, `Desktop Components`, `Hud Components`, `Llm Components`, `Tools Components`, `Agents Components`, `Window Components`, `Voice Components`, `Desktop Components`, `Process Components`, `Agents Components`, `Cli Components`, `Bootstrap Components`, `Browser Components`, `Desktop Components`, `Screen Components`, `Stt Components`, `Tts Components`, `Keyboard Components`, `Application Components`, `Planner Components`, `Mouse Components`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `HUDState` connect `Hud Components` to `Hud Components`, `Desktop Components`, `Scene Components`, `Hud Components`, `Hud Components`, `Hud Components`, `Hud Components`, `Hud Components`, `Window Components`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `HUDConfig` connect `Hud Components` to `Hud Components`, `Bootstrap Components`, `Desktop Components`, `Scene Components`, `Hud Components`, `Hud Components`, `Hud Components`, `Hud Components`, `Window Components`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Image` (e.g. with `VisionService` and `reference_image()`) actually correct?**
  _`Image` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `AgentState` (e.g. with `ContextBuilder` and `_started()`) actually correct?**
  _`AgentState` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ContextBuilder` (e.g. with `AgentState` and `Message`) actually correct?**
  _`ContextBuilder` has 22 INFERRED edges - model-reasoned connections that need verification._