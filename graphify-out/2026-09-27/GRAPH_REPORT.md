# Graph Report - AetherOS  (2026-09-27)

## Corpus Check
- 285 files · ~236,095 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6248 nodes · 14331 edges · 268 communities (223 shown, 34 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1538 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ddd675e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _started
- Image
- answer
- define
- automation/engine.py
- HUDSnapshot
- VisionError
- VoiceConfig
- Scene
- test_agent_observation.py
- AutomationEngine
- AgentState
- PathGuard
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- asyncio
- HUDService
- ContextBuilder
- test_tool_schema.py
- Message
- VisionService
- PlannedAction
- Event
- EventBus
- PlanResult
- AgentExecutionResult
- Bootstrapper
- PsutilProcess
- _RecordingProvider
- CommandRegistry
- HUDProcess
- OpenCVTemplateProvider
- PolicyEngine
- VoiceService
- test_wiring.py
- safe_preview
- LLMEngine
- get_settings
- OpenCVProvider
- voice/service.py
- HUDWindow
- ApplicationService
- grounding/engine.py
- Any
- FileController
- ToolCall
- .test_the_registered_engine_is_preferred
- PipeReader
- CLIUI
- Win32Window
- wire
- test_unified_interaction.py
- ProcessController
- MouseService
- Any
- _RecordingProvider
- .create
- FrameCache
- wire
- LLMToolLoop
- _one
- test_agent.py
- observability/pipeline.py
- PlaywrightProvider
- .record
- VisionVerifier
- WindowController
- ClipboardService
- EdgeTTS
- VisionProvider
- ContextBuilder
- FakeLLMProvider
- asyncio
- HUDConfig
- application/tools.py
- LLMProvider
- MemoryProvider
- qcolor
- ProcessService
- asyncio
- TraceEvent
- tool
- bootstrapper.py
- WindowInfo
- asyncio
- YOLOProvider
- DesktopError
- BrowserProvider
- ._reject_if_terminal
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestRegisteredToolSurface
- TestRegistration
- OpenAICompatibleProvider
- BrowserService
- WakeWordActivator
- RecoveryRunner
- asyncio
- verification/tools.py
- HookRecorder
- test_cli_agent.py
- ClipboardController
- Application
- PyAutoGuiMouse
- TaskManager
- KeyboardController
- parse_target
- PyAutoGuiKeyboard
- FasterWhisperSTT
- window/tools.py
- window/controller.py
- make_provider
- VoiceState
- _FakeMouse
- commands
- .from_events
- test_agent_execution.py
- ._review
- RenderContext
- FakeHUDProcess
- Agent
- make_vision_service
- PyAutoGuiClipboard
- process/tools.py
- _RecordingMouse
- resolve_level
- _settings
- ToolCommandService
- CLIRuntime
- ObservationLog
- Renderer
- bootstrap/application.py
- test_interface_contracts.py
- renderer.py
- SapiTTS
- PlannerConfig
- test_agent_policy.py
- vision/tools.py
- NullTTS
- test_agent_planner.py
- LiveTraceUI
- .hud
- ToolError
- screen/tools.py
- ScreenService
- get_logger
- Detection
- Layer
- TextBlock
- test_agent_e2e.py
- tasks/__init__.py
- make_fake_detector
- ._derive
- .download
- TestCallIdentifiers
- ToolExecutionCoordinator
- ScreenController
- MouseController
- ContextConfig
- .evaluate
- ToolRegistry
- _CountingExecutor
- _service
- text_match_score
- main
- ._run
- cli/main.py
- TestToolsCommand
- GlowCache
- import_all.py
- WindowService
- test_manager.py
- PolicyEvaluation
- BaseError
- AgentCore
- _settings
- asyncio
- interaction.py
- TaskContext
- FakeKeyboard
- LLMProviderManager
- FakeMouse
- TraceCollector
- tool_calls.py
- Box
- ScriptedSTT
- ServiceContainer
- test_input.py
- spatial.py
- LLMConfig
- ToolDiscovery
- AetherOS
- AgentLoopResult
- factory.py
- test_vision_engine.py
- TestSerialization
- _candidate
- ._qt_available
- FakeScreen
- .generate
- ToolExecutionResult
- TestServiceInitialisation
- vision/main.py
- TestToolFailure
- MSSScreen
- AgentStatus
- grounding/tools.py
- .__init__
- .to_dict
- executor
- TestWellFormedCalls
- TestEveryToolModuleImports
- ._grab
- set_event_bus
- ExecutionStatus
- PulseLayer
- TickLayer
- ._bootstrap_browser
- TestImageDisk
- TestSerializationAndLogging
- screenshot_observation
- ._bootstrap_voice
- .trace
- parametrize
- ParsedResponse
- TestFinalResponse
- EnvelopeResult
- .from_dict
- ._describe
- main
- ._loop
- PolicyDecision
- _win32_clipboard
- type_match_score
- TestDetectorBootstrap
- _safe_name
- TestProviderCompatibility
- TestInvalidArguments
- FakeDetectionProvider
- TestMSSSave
- .by_source
- .copy_files
- .copy_image
- .open_file
- .start
- RecordingMouse
- .grab
- RecordingKeyboard
- ._live_context
- .speak
- .start
- Path
- bootstrapper
- .has_text
- .name

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 223 edges
2. `Image` - 183 edges
3. `AgentState` - 136 edges
4. `tool()` - 111 edges
5. `define()` - 104 edges
6. `AgentPlanner` - 102 edges
7. `ToolExecutionCoordinator` - 100 edges
8. `get_logger()` - 96 edges
9. `ToolExecutor` - 96 edges
10. `AgentContext` - 78 edges

## Surprising Connections (you probably didn't know these)
- `test_vision_observation_with_no_readings_has_no_confidence()` --calls--> `vision_observation()`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/agents/observation/factory.py
- `test_from_dict_rejects_unknown_field()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_from_dict_requires_source()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (268 total, 34 thin omitted)

### Community 0 - "_started"
Cohesion: 0.17
Nodes (10): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., One round, several calls: all answered, in order, one at a time., _started(), TestLogSafety (+2 more)

### Community 1 - "Image"
Cohesion: 0.05
Nodes (14): Image, Universal image model for AetherOS. Every vision module should consume and…, Unit tests for the vision Image model. Image is the type every other vision…, A single-channel array has no channel order, so it should not need one spelled…, The double-swap regression: calling rgb() twice must not swap back., Luminance is weighted per channel, so a BGR array read as RGB produces a…, test_repr_is_informative(), TestColorConversion (+6 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (49): Executes registered AetherOS tools., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes(), asyncio (+41 more)

### Community 4 - "automation/engine.py"
Cohesion: 0.04
Nodes (67): _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran… (+59 more)

### Community 5 - "HUDSnapshot"
Cohesion: 0.08
Nodes (13): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:…, Adopt a new snapshot, starting a style transition if the state changed., Update the live audio level without changing state. (+5 more)

### Community 6 - "VisionError"
Cohesion: 0.06
Nodes (40): Exception, ErrorContext, Additional information about an error., Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, VisionProvider, Short-lived screen-frame cache. A desktop agent frequently runs several vision… (+32 more)

### Community 7 - "VoiceConfig"
Cohesion: 0.04
Nodes (36): PushToTalkActivator, Release the keyboard hook., Global hotkey activation. Push-to-talk is the default because it is…, AudioCapture, AudioPlayer, Microphone capture with energy-based silence detection. PortAudio delivers…, Non-blocking playback of mono float32 PCM. Amplitude is measured inside the…, Abort playback immediately. (+28 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (35): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+27 more)

### Community 9 - "test_agent_observation.py"
Cohesion: 0.13
Nodes (19): Observe the outcome of one tool call. Accepts either the raw…, tool_observation(), Observation, Something the agent noticed that is not itself a tool result. Kept separate…, test_confidence_out_of_range_is_rejected(), test_from_dict_rejects_unknown_field(), test_from_dict_requires_source(), test_invalid_source_is_rejected() (+11 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (36): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, Build a workflow from a plain dict, as ``run_workflow`` receives it., Calls, engine(), _failing_state(), _matching_state(), asyncio (+28 more)

### Community 11 - "AgentState"
Cohesion: 0.05
Nodes (12): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, Every result recorded against one call id., asyncio, parametrize, TestCompletion, TestErrors (+4 more)

### Community 12 - "PathGuard"
Cohesion: 0.11
Nodes (21): PathLike, PathAccess, PathGuard, PathVerdict, Enum, Path, str, Path validation for the filesystem and application tools. A model that can… (+13 more)

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (56): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not… (+48 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (33): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+25 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.10
Nodes (18): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not., One well-formed call for a known tool is planned, not executed., A provider that supports parallel calls gets one action per call. (+10 more)

### Community 16 - "asyncio"
Cohesion: 0.15
Nodes (14): _ocr_with(), asyncio, Stands in for a built PaddleOCR pipeline. Records the frame it was handed so a…, A real provider whose model construction is replaced by a stub. ``_build`` is…, The channel-order regression. PaddleX's reader defaults to ``format="BGR"`` and…, The native recognition model reads the buffer directly; a view with negative or…, The empty-result regression: fields live under ``json["res"]``, so a provider…, ``rec_boxes`` comes back empty when document preprocessing is disabled — which… (+6 more)

### Community 17 - "HUDService"
Cohesion: 0.05
Nodes (25): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+17 more)

### Community 18 - "ContextBuilder"
Cohesion: 0.15
Nodes (13): Any, ContextBuilder, A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools. (+5 more)

### Community 19 - "test_tool_schema.py"
Cohesion: 0.06
Nodes (31): NotAnImportableType, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse(), optionals(), Any (+23 more)

### Community 20 - "Message"
Cohesion: 0.06
Nodes (50): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the… (+42 more)

### Community 21 - "VisionService"
Cohesion: 0.06
Nodes (27): High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService (+19 more)

### Community 22 - "PlannedAction"
Cohesion: 0.06
Nodes (19): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim. (+11 more)

### Community 23 - "Event"
Cohesion: 0.03
Nodes (82): Event, Base class for all events in AetherOS. Every event inherits from this class., Returns the event class name., get_event_bus(), publish(), Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., clear_subscribers() (+74 more)

### Community 24 - "EventBus"
Cohesion: 0.09
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "PlanResult"
Cohesion: 0.08
Nodes (15): PlanResult, No next step exists. ``error_type`` names the kind of wall hit., What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only… (+7 more)

### Community 26 - "AgentExecutionResult"
Cohesion: 0.06
Nodes (19): AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values…, Log-safe: names, outcomes and timings, never values. ``error`` is included… (+11 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.10
Nodes (4): Bootstrapper, Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…

### Community 28 - "PsutilProcess"
Cohesion: 0.12
Nodes (16): PsutilProcess, Any, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle…, Read one process into a plain dict. Fields that require privileges are filled…, Open a URL in the default browser. Returns ``0`` for the same reason as…, Every process the current user can see. ``process_iter`` with an explicit…, Every process whose name matches, case-insensitively. Matched with and without… (+8 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.13
Nodes (4): Any, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.08
Nodes (12): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Render one tool as ``name(arg: type, arg: type = default)``. Names, types, and…, A readable type name for a resolved annotation, or "" when there is no usable…, Render a parameter's default value for display., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace… (+4 more)

### Community 31 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 32 - "OpenCVTemplateProvider"
Cohesion: 0.11
Nodes (11): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, bgr_image(), A small BGR image whose channels are all different. Uniform grey would hide a…, Scales that would make the template larger than the image are dropped rather… (+3 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.09
Nodes (15): PolicyConfig, Any, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --…, Release the stop. Deliberately explicit: nothing clears it on the engine's… (+7 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 36 - "safe_preview"
Cohesion: 0.13
Nodes (11): Any, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, safe_metadata(), safe_preview(), truncate_value(), Log-safe projections for trace payloads (PHASES 3, 5, 11). The redaction rules… (+3 more)

### Community 37 - "LLMEngine"
Cohesion: 0.11
Nodes (14): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, add() (+6 more)

### Community 38 - "get_settings"
Cohesion: 0.11
Nodes (22): BaseSettings, get_settings(), Singleton Settings object., Settings, Attempts to make, resolved against configuration and clamped., Safety — the gates every destructive desktop action passes through. Two…, Capability, Decision (+14 more)

### Community 39 - "OpenCVProvider"
Cohesion: 0.14
Nodes (9): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, parametrize, TestOpenCVProviderMetadata (+1 more)

### Community 40 - "voice/service.py"
Cohesion: 0.04
Nodes (55): Future, AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed. (+47 more)

### Community 41 - "HUDWindow"
Cohesion: 0.08
Nodes (18): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+10 more)

### Community 42 - "ApplicationService"
Cohesion: 0.13
Nodes (19): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+11 more)

### Community 43 - "grounding/engine.py"
Cohesion: 0.10
Nodes (15): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+7 more)

### Community 44 - "Any"
Cohesion: 0.12
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "ToolCall"
Cohesion: 0.10
Nodes (15): _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, Record a call that was turned away, without the engine being asked. The refusal…, Report a refusal that could not be written down. Reached only when the run is…, Write the outcome into the run, then describe it. The record is built before it…, Record the request, before anything is checked or run. Ordered first on… (+7 more)

### Community 47 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 48 - "PipeReader"
Cohesion: 0.10
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 49 - "CLIUI"
Cohesion: 0.07
Nodes (19): Panel, CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI. (+11 more)

### Community 50 - "Win32Window"
Cohesion: 0.14
Nodes (14): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real…, Bring a window to the foreground and give it keyboard focus. Verified rather…, Ask a window to close. ``WM_CLOSE`` is a request, and deliberately so: the… (+6 more)

### Community 51 - "wire"
Cohesion: 0.08
Nodes (23): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., ultralytics and its weights are optional, so the agent has to be told the… (+15 more)

### Community 52 - "test_unified_interaction.py"
Cohesion: 0.13
Nodes (22): InteractionGateway, Submit a goal to the shared agent, tagged with its front end., _boom(), _build_agent(), _CountingExecutor, _mouse_position(), Any, asyncio (+14 more)

### Community 53 - "ProcessController"
Cohesion: 0.07
Nodes (17): ProcessController, ABC, Any, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running., Wait for a process to exit. (+9 more)

### Community 54 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 55 - "Any"
Cohesion: 0.11
Nodes (11): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly., A tool the model asked for, tagged with the iteration that asked. Adapts…, Names only. The safe projection for logs — see module docstring., The transcript in provider wire format, ready to send. (+3 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - ".create"
Cohesion: 0.08
Nodes (17): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., TraceFileWriter (+9 more)

### Community 58 - "FrameCache"
Cohesion: 0.12
Nodes (15): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, _Clock, _make_capture(), asyncio, Tests for the short-lived screen-frame cache. The clock is injected so time… (+7 more)

### Community 59 - "wire"
Cohesion: 0.25
Nodes (9): _block(), executor(), asyncio, fixture, Register the services the grounding tools resolve, with fake edges. Mirrors…, TestClickGroundedTarget, TestGroundTarget, TestTypeIntoGroundedTarget (+1 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.09
Nodes (20): LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text. (+12 more)

### Community 61 - "_one"
Cohesion: 0.15
Nodes (9): _one(), Parsing of provider tool-call responses. Everything the model emits is…, The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature., A tool message must carry a name, so a nameless call cannot be answered inside…, TestMalformedCalls (+1 more)

### Community 62 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 63 - "observability/pipeline.py"
Cohesion: 0.10
Nodes (25): _accumulate_status(), _apply_event(), _detail(), ExecutionPipeline, PipelineStage, PipelineStatus, _presentation_for(), Any (+17 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 65 - ".record"
Cohesion: 0.18
Nodes (11): LevelCallback, _normalize_level(), Any, ndarray, Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is…, Root-mean-square amplitude of a PCM block. (+3 more)

### Community 66 - "VisionVerifier"
Cohesion: 0.24
Nodes (5): Drive OCR through the tool registry, the way an agent would., Runs the verification stages and collects their results., VisionVerifier, The canonical verification image containing :data:`REFERENCE_LINES`., reference_image()

### Community 67 - "WindowController"
Cohesion: 0.11
Nodes (12): Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title., Returns the currently active window. (+4 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "EdgeTTS"
Cohesion: 0.10
Nodes (17): decode_mp3(), decode_wav(), _frame_to_mono(), _load_av(), Any, ndarray, pyav_available(), Decode RIFF/WAVE bytes into mono float32 PCM. Uses the standard library, so it… (+9 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "ContextBuilder"
Cohesion: 0.07
Nodes (20): ContextBuilder, Any, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., The tool name inside a generated schema, or ``""`` if it is malformed. Tolerant…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are… (+12 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.07
Nodes (18): Whether the far end has gone away., asyncio, parametrize, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools…, Vision's screen-reading tools are useless without capture tools beside them,… (+10 more)

### Community 74 - "HUDConfig"
Cohesion: 0.06
Nodes (21): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+13 more)

### Community 75 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 76 - "LLMProvider"
Cohesion: 0.12
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Initialize provider resources., Release provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.10
Nodes (9): asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing (+1 more)

### Community 81 - "TraceEvent"
Cohesion: 0.10
Nodes (29): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), TraceSpan (+21 more)

### Community 82 - "tool"
Cohesion: 0.15
Nodes (29): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+21 more)

### Community 83 - "bootstrapper.py"
Cohesion: 0.11
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 84 - "WindowInfo"
Cohesion: 0.10
Nodes (14): Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Poll until a matching window appears, or the timeout expires. Polling rather…, Poll until a matching window holds focus, or the timeout expires. Distinct from…, Poll ``probe`` until it returns a window, bounded by ``timeout``. The bound is…, Synchronous selector matching, for use inside poll probes. (+6 more)

### Community 85 - "asyncio"
Cohesion: 0.11
Nodes (19): _call(), asyncio, Tests for the agent context layer. The properties under test are the ones the…, A plain back-and-forth reaches the provider unchanged., Tool rounds keep the shape the provider layer already accepts., A tool message whose assistant turn was trimmed fails the request. The provider…, The digest must stay safe to log; the history carries the values., Observations are not transcript turns, so the context has to carry them. (+11 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (16): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Tests for the vision providers' performance-oriented internals. These pin the… (+8 more)

### Community 87 - "DesktopError"
Cohesion: 0.08
Nodes (24): Process, DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Application service. An application is not a process, and conflating the two is…, _from_registry(), is_uri(), Application name resolution. The model asks for "notepad", or "calculator", or… (+16 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.05
Nodes (18): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page title., Return the current page URL. (+10 more)

### Community 89 - "._reject_if_terminal"
Cohesion: 0.09
Nodes (15): ErrorRecord, BaseException, Finish the run unsuccessfully, recording the unrecoverable error., Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would…, Open the transcript with the system prompt and the goal. (+7 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "_RecordingMouse"
Cohesion: 0.11
Nodes (3): A ``MouseController`` sitting where PyAutoGUI would. Reports a fixed position…, _RecordingMouse, The list is read live from the registry, so a tool registered after the command…

### Community 92 - "parse_llm_response"
Cohesion: 0.19
Nodes (6): parse_llm_response(), Normalise a provider tool-call response. Never raises. Accepts the shape…, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn., TestContent

### Community 93 - "TestRegisteredToolSurface"
Cohesion: 0.08
Nodes (13): fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations… (+5 more)

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "OpenAICompatibleProvider"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 96 - "BrowserService"
Cohesion: 0.07
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "WakeWordActivator"
Cohesion: 0.12
Nodes (5): NullActivator, WakeCallback, An activator that never fires. This is what "always-listening is off" looks…, Placeholder for always-listening wake-word detection. The abstraction exists so…, WakeWordActivator

### Community 98 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "verification/tools.py"
Cohesion: 0.16
Nodes (16): MatchMode, parse_mode(), parse_region(), Any, Enum, str, Parse a caller-supplied comparison mode. Shared by the ``verify_action`` tool…, Parse a ``[left, top, width, height]`` screen region. (+8 more)

### Community 101 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 102 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 103 - "ClipboardController"
Cohesion: 0.12
Nodes (9): ClipboardController, ABC, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"…, Copy text to the clipboard., Returns clipboard text. (+1 more)

### Community 105 - "PyAutoGuiMouse"
Cohesion: 0.10
Nodes (5): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 107 - "KeyboardController"
Cohesion: 0.12
Nodes (8): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab

### Community 108 - "parse_target"
Cohesion: 0.12
Nodes (14): _clean(), _find_element_type(), _find_ordinal(), _find_relation(), parse_target(), Parse a natural-language target into a :class:`GroundingTarget`. Deterministic,…, Return the canonical element type mentioned, longest phrase first., Parse ``query`` into a structured :class:`GroundingTarget`. The residual text… (+6 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.11
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 110 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "window/controller.py"
Cohesion: 0.16
Nodes (7): ABC, Window service. Adds the one thing the raw :class:`WindowController` interface…, Window identity and geometry. A title is not an identity. Two Explorer windows…, A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 113 - "make_provider"
Cohesion: 0.11
Nodes (30): _build(), _CountingExecutor, move_mouse(), Any, asyncio, fixture, Tests for the agent core loop. ``AgentCore`` is the driver that turns a goal…, A core and its counting executor over the same registry. (+22 more)

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 116 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 117 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 118 - "test_agent_execution.py"
Cohesion: 0.10
Nodes (27): add_async(), coordinator(), executor(), explodes(), journal(), _journalled(), move_mouse(), Any (+19 more)

### Community 119 - "._review"
Cohesion: 0.29
Nodes (3): Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read.

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "FakeHUDProcess"
Cohesion: 0.06
Nodes (23): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+15 more)

### Community 122 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 123 - "make_vision_service"
Cohesion: 0.21
Nodes (15): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+7 more)

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.22
Nodes (5): PyAutoGuiClipboard, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 125 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 127 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "ToolCommandService"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 130 - "CLIRuntime"
Cohesion: 0.20
Nodes (5): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…

### Community 131 - "ObservationLog"
Cohesion: 0.17
Nodes (8): ObservationLog, Any, Observation, An append-only, ordered collection of :class:`Observation`., Append one observation, rejecting anything that is not one. The type guard is…, The most recent observations, newest last. ``latest(1)`` is the freshest single…, test_log_rejects_non_observation_entry(), test_observation_log_round_trips()

### Community 132 - "Renderer"
Cohesion: 0.15
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "bootstrap/application.py"
Cohesion: 0.21
Nodes (6): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main()

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 136 - "SapiTTS"
Cohesion: 0.14
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 137 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 138 - "test_agent_policy.py"
Cohesion: 0.16
Nodes (21): _call(), _coordinator(), _CountingExecutor, executor(), move_mouse(), Any, asyncio, fixture (+13 more)

### Community 139 - "vision/tools.py"
Cohesion: 0.10
Nodes (29): get_profiler(), Opt-in per-stage timing for the vision pipeline. Vision is the one subsystem…, A profiler configured from the shared settings object. ``get_settings`` is…, Accumulated per-stage timings for one vision request. A plain name ->…, Times named stages when profiling is enabled, and is a no-op otherwise.…, Time the wrapped block. Used around an ``await`` -- ``with…, StageTimings, VisionProfiler (+21 more)

### Community 140 - "NullTTS"
Cohesion: 0.10
Nodes (5): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…, Records what would have been spoken. The test double for speech output: it…, RecordingTTS

### Community 141 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 142 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 144 - "ToolError"
Cohesion: 0.07
Nodes (31): Parameter, Exception, ToolError, is_unconstrained(), public_parameters(), Any, Signature, Annotation resolution shared by the schema generator and the validator. Every… (+23 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "ScreenService"
Cohesion: 0.12
Nodes (15): ndarray, Path, Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region. (+7 more)

### Community 147 - "get_logger"
Cohesion: 0.04
Nodes (59): Level 1+2: import every tool module, report registration. The module list is…, _clamp(), _describe_call(), _describe_result(), Observation, Agent context assembly. One :class:`AgentContext` is everything the model needs…, The single system message: instructions, goal, budget, digests. Everything that…, One digest line for a call: names, never values. The model already has the… (+51 more)

### Community 148 - "Detection"
Cohesion: 0.10
Nodes (8): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., TestDetection

### Community 149 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 150 - "TextBlock"
Cohesion: 0.05
Nodes (24): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, Map box coordinates from a downscaled frame back to the original image. Pure… (+16 more)

### Community 151 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 152 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 153 - "make_fake_detector"
Cohesion: 0.19
Nodes (7): isolated_container(), make_fake_detector(), make_unclosable_ocr(), fixture, Yield the process-wide container with its registrations saved and restored.…, TestDetectObjects, TestShutdown

### Community 154 - "._derive"
Cohesion: 0.09
Nodes (11): ColorSpace, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV…, Write the image to disk with its colours intact. (+3 more)

### Community 155 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 157 - "ToolExecutionCoordinator"
Cohesion: 0.11
Nodes (12): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, A name the registry has never heard of is refused before delegation., Once a run has ended, nothing executes and nothing is written. (+4 more)

### Community 158 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 159 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 160 - "ContextConfig"
Cohesion: 0.13
Nodes (10): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, An assistant turn, optionally carrying the calls the model asked for.…, A long run must not produce an unbounded prompt., `[-0:]` is the whole list, so zero has to be handled explicitly., Nothing in the window announced this id, so the provider would reject it., The property that matters: a longer run is not a bigger prompt., Limits are clamped, not trusted. (+2 more)

### Community 161 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 162 - "ToolRegistry"
Cohesion: 0.09
Nodes (14): The registry this executor validates and runs tools from., Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, _fake_browser(), Any, asyncio (+6 more)

### Community 163 - "_CountingExecutor"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, _CountingExecutor, Defaults, and the invariant the class docstring states., The real engine, counting how often it was asked. A subclass rather than a…, TestConstruction

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.20
Nodes (6): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, text_match_score(), _tokens(), Unit tests for the deterministic match scoring. The scale is graded on purpose…, TestTextMatchScore

### Community 167 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 170 - "cli/main.py"
Cohesion: 0.27
Nodes (6): Execute a parsed command., CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 171 - "TestToolsCommand"
Cohesion: 0.17
Nodes (3): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., TestToolsCommand

### Community 172 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 174 - "WindowService"
Cohesion: 0.17
Nodes (10): Human-readable condition, used when the caller did not supply one., Any, Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``., A full snapshot, which carries the bounds along with everything else., High-level window service. Backed by a :class:`WindowController`; holds no…, Full snapshot in one call. Uses the backend's ``describe`` when it has one --… (+2 more)

### Community 175 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 176 - "PolicyEvaluation"
Cohesion: 0.16
Nodes (7): PolicyEvaluation, Any, The policy's answer to one request, as data. Returned rather than raised so a…, Any, Answer ALLOW / DENY / REQUIRE_CONFIRMATION for one call. First match wins, in…, Run global validators then the per-tool one; first objection wins. Returns…, Advisory per-call budget the evaluation reports. The engine holds no clock --…

### Community 177 - "BaseError"
Cohesion: 0.10
Nodes (15): BaseError, Any, Exception, Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError, HUDProcessError, HUDUnavailableError (+7 more)

### Community 178 - "AgentCore"
Cohesion: 0.12
Nodes (13): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Assemble a core from a provider and, optionally, its collaborators. The…, _fake_mouse(), _FakeMouseController, _is_ordered_subsequence(), Any (+5 more)

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "asyncio"
Cohesion: 0.21
Nodes (8): boom(), A tool that always fails, to drive the tool-failure path., Any, asyncio, Best-effort emission and the timed span context (PHASES 2, 5, 12). The contract…, TestEmitTraceIsBestEffort, TestEmitTracePublishes, TestTraceContext

### Community 181 - "interaction.py"
Cohesion: 0.20
Nodes (10): Run ``goal`` on the shared agent, labelling the turn with ``source``.…, interaction_scope(), InteractionContext, new_request_id(), new_session_id(), The interaction context that tags a run with where it came from. A single…, Where the in-flight turn came from and how to correlate it. Immutable: a turn's…, A fresh per-turn correlation id. (+2 more)

### Community 183 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 186 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 187 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 188 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 189 - "ScriptedSTT"
Cohesion: 0.05
Nodes (33): Captured microphone audio., Recording, EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, Returns queued phrases in order. This is the test double that lets the whole…, ScriptedSTT, HookRecorder (+25 more)

### Community 190 - "ServiceContainer"
Cohesion: 0.16
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 191 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 192 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 193 - "LLMConfig"
Cohesion: 0.38
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 194 - "ToolDiscovery"
Cohesion: 0.22
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 206 - "factory.py"
Cohesion: 0.16
Nodes (15): _mean_confidence(), Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe what the vision layer read off an image. Consumes ``VisionService``…, Average of the confidences a producer supplied, or ``None`` if none. ``None``…, vision_observation(), Agent observation layer. A small, representational model of what the agent…, ObservationLog: the ordered set of what the agent currently knows. A run…, Observation (+7 more)

### Community 207 - "test_vision_engine.py"
Cohesion: 0.11
Nodes (8): skipif, Tests for the Vision Engine. Run with: pytest tests/vision/, test_opencv_provider_metadata(), test_paddleocr_provider_metadata(), test_yolo_provider_metadata(), TestImage, TestTextBlock, TestVisionPackageStructure

### Community 208 - "TestSerialization"
Cohesion: 0.17
Nodes (9): call(), failed_result(), ok_result(), _populated_state(), fixture, Tests for the agent execution state. The state layer has no interesting…, state(), TestDescribe (+1 more)

### Community 209 - "_candidate"
Cohesion: 0.33
Nodes (4): _candidate(), Unit tests for the grounding data models. The models carry the public contract,…, TestCandidateGeometry, TestResult

### Community 211 - "FakeScreen"
Cohesion: 0.16
Nodes (6): FakeScreen, Any, Exception, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 212 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 213 - "ToolExecutionResult"
Cohesion: 0.23
Nodes (6): File a failure in the run's error ledger. Field by field rather than by handing…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, _render(), Outcome of a single tool execution. Carries failures as data rather than as…, ToolExecutionResult, TestToolResults

### Community 215 - "vision/main.py"
Cohesion: 0.18
Nodes (12): Check, main(), Vision engine verification entry point. Run with:: python -m…, Run every verification stage., start(), expected_words(), Deterministic images for verifying the vision pipeline. The OCR path cannot be…, Render lines of text onto a white background. Returns a BGR :class:`Image`.… (+4 more)

### Community 217 - "MSSScreen"
Cohesion: 0.09
Nodes (19): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., fake_sct(), FakeSCT, mss_screen() (+11 more)

### Community 218 - "AgentStatus"
Cohesion: 0.17
Nodes (6): AgentRunResult, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, AgentStatus, Enum, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…

### Community 219 - "grounding/tools.py"
Cohesion: 0.29
Nodes (12): get_frame_cache(), Process-wide frame cache, sized from the shared settings object. Built once…, click_grounded_target(), _engine(), ground_target(), Any, Grounding tools: the agent-facing surface of the grounding layer. These are the…, type_into_grounded_target() (+4 more)

### Community 222 - "executor"
Cohesion: 0.67
Nodes (3): executor(), fixture, An executor over the process-wide registry, which is where @tool registers.

### Community 223 - "TestWellFormedCalls"
Cohesion: 0.15
Nodes (5): SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The OpenAI wire format sends arguments as a JSON *string*., A provider that passes the wire shape through verbatim keeps the name and…, TestWellFormedCalls

### Community 224 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 225 - "._grab"
Cohesion: 0.21
Nodes (7): ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary)., Grab a region and drop the alpha channel. mss hands back BGRA; slicing to three…, Capture the primary monitor. Returns: BGR NumPy image of shape (height, width,…, Capture a rectangular region.

### Community 226 - "set_event_bus"
Cohesion: 0.33
Nodes (5): Set the global EventBus instance. This should be called once during application…, set_event_bus(), fixture, Install a fresh bus as the global publisher target, restored afterwards.…, wired()

### Community 227 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 231 - "TestImageDisk"
Cohesion: 0.25
Nodes (3): Path, The end-to-end check for the colour-space contract. Pillow writes RGB, so a…, TestImageDisk

### Community 232 - "TestSerializationAndLogging"
Cohesion: 0.22
Nodes (4): IterationInfo, Where the run is in its budget. Carried explicitly because the model behaves…, One faithful view for auditing, one redacted view for the sinks., TestSerializationAndLogging

### Community 233 - "screenshot_observation"
Cohesion: 0.20
Nodes (10): browser_observation(), Any, Observation, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe browser state. The seam the task asks for: there is no browser-state…, screenshot_observation(), test_browser_observation_seam(), test_observation_log_records_and_filters_by_source() (+2 more)

### Community 236 - "parametrize"
Cohesion: 0.27
Nodes (3): parametrize, TestRegistration, TestSchema

### Community 237 - "ParsedResponse"
Cohesion: 0.22
Nodes (5): ParsedResponse, Normalised view of one provider response., parametrize, A provider that returned plain text still yields a usable answer., TestDegenerateInput

### Community 238 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 239 - "EnvelopeResult"
Cohesion: 0.25
Nodes (5): EnvelopeResult, Any, Exception, ndarray, A PaddleOCR 3.x result seen through its documented ``json`` accessor. The…

### Community 240 - ".from_dict"
Cohesion: 0.25
Nodes (5): _new_observation_id(), Any, Project down to a transcript-level ``agents.state.Observation``. The bridge…, Rebuild from :meth:`to_dict`, rejecting unknown fields. Unknown keys are an…, _utc_now()

### Community 241 - "._describe"
Cohesion: 0.25
Nodes (4): Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Full snapshot of one window. Not on the interface, which exposes title,…, The process that owns the window, as best we know it.

### Community 242 - "main"
Cohesion: 0.43
Nodes (6): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms.

### Community 243 - "._loop"
Cohesion: 0.29
Nodes (3): Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…

### Community 244 - "PolicyDecision"
Cohesion: 0.33
Nodes (5): PolicyDecision, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a…

### Community 245 - "_win32_clipboard"
Cohesion: 0.29
Nodes (4): Any, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard()

### Community 246 - "type_match_score"
Cohesion: 0.43
Nodes (3): Score a detection ``label`` against a desired element ``target_type``., type_match_score(), TestTypeMatchScore

### Community 247 - "TestDetectorBootstrap"
Cohesion: 0.29
Nodes (3): Path, ultralytics downloads weights on first use, so detection stays off until a path…, TestDetectorBootstrap

### Community 248 - "_safe_name"
Cohesion: 0.47
Nodes (3): Reduce a run id to a filename-safe token. ``state_id`` values are already tame,…, _safe_name(), TestSafeName

### Community 249 - "TestProviderCompatibility"
Cohesion: 0.33
Nodes (4): The payload has to be accepted by the engine that already exists., The invariant the provider enforces, asserted over the whole payload., Reads are lock-free because state hands back immutable snapshots., TestProviderCompatibility

### Community 252 - "TestMSSSave"
Cohesion: 0.47
Nodes (3): Path, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame…, TestMSSSave

### Community 254 - ".copy_files"
Cohesion: 0.40
Nodes (3): Path, Copy one or more files/folders to the clipboard., Returns copied file paths. Returns: Empty list if clipboard contains no files.

### Community 255 - ".copy_image"
Cohesion: 0.40
Nodes (3): Any, Copy an image to the clipboard., Returns an image from the clipboard. Returns: None if clipboard doesn't contain…

### Community 256 - ".open_file"
Cohesion: 0.40
Nodes (3): Path, Start a new process. Returns: Process ID (PID), Open a file with its default application. Returns: Process ID if available.

### Community 257 - ".start"
Cohesion: 0.40
Nodes (3): Path, Start a program and return its pid. ``env``, when given, *extends* the current…, Open a file with its registered application. Returns ``0``, which means "no pid…

### Community 259 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 265 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2308 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `CLIRuntime`, `answer`, `automation/engine.py`, `bootstrap/application.py`, `VisionError`, `VoiceConfig`, `vision/tools.py`, `NullTTS`, `VerificationResult`, `PaddleOCRProvider`, `ToolError`, `Event`, `Bootstrapper`, `CommandRegistry`, `MouseController`, `ScreenController`, `PolicyEngine`, `HUDProcess`, `_CountingExecutor`, `get_settings`, `voice/service.py`, `cli/main.py`, `AgentCore`, `ProcessController`, `MouseService`, `ServiceContainer`, `WindowController`, `ClipboardService`, `ContextBuilder`, `HUDConfig`, `LLMProvider`, `ProcessService`, `TraceEvent`, `bootstrapper.py`, `YOLOProvider`, `DesktopError`, `BrowserProvider`, `LifecycleManager`, `BrowserService`, `WakeWordActivator`, `RecoveryRunner`, `ClipboardController`, `Application`, `KeyboardController`, `FasterWhisperSTT`, `window/controller.py`, `VoiceState`, `Agent`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `Image` connect `Image` to `VisionError`, `vision/tools.py`, `VerificationResult`, `PaddleOCRProvider`, `asyncio`, `Detection`, `VisionService`, `TextBlock`, `._derive`, `OpenCVTemplateProvider`, `OpenCVProvider`, `grounding/engine.py`, `wire`, `FrameCache`, `VisionVerifier`, `test_vision_engine.py`, `asyncio`, `YOLOProvider`, `vision/main.py`, `grounding/tools.py`, `TestImageDisk`, `main`, `FakeDetectionProvider`, `TestMSSSave`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `_started`, `ToolCommandService`, `answer`, `define`, `automation/engine.py`, `PlannerConfig`, `test_agent_policy.py`, `AutomationEngine`, `test_agent_planner.py`, `AgentPlanner`, `ToolError`, `ContextBuilder`, `get_logger`, `test_agent_e2e.py`, `ContextConfig`, `_CountingExecutor`, `LLMEngine`, `Any`, `AgentCore`, `test_unified_interaction.py`, `ScriptedSTT`, `ContextBuilder`, `FakeLLMProvider`, `LLMProvider`, `asyncio`, `TestToolFailure`, `RecoveryRunner`, `ExecutionStatus`, `test_cli_agent.py`, `TestSerializationAndLogging`, `TestFinalResponse`, `make_provider`, `test_agent_execution.py`, `TestProviderCompatibility`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 85 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 101 inferred relationships involving `define()` (e.g. with `_sample_tools()` and `tools()`) actually correct?**
  _`define()` has 101 INFERRED edges - model-reasoned connections that need verification._