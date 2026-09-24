# Graph Report - AetherOS  (2026-09-24)

## Corpus Check
- 260 files · ~216,344 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5763 nodes · 13113 edges · 224 communities (188 shown, 25 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1380 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b9970f94`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _started
- Image
- answer
- define
- automation/engine.py
- executor.py
- vision/__init__.py
- VoiceConfig
- Scene
- AgentError
- AutomationEngine
- AgentState
- policy.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- OpenCVProvider
- HUDService
- ToolResultRecord
- test_tool_schema.py
- HUDSnapshot
- ErrorContext
- TestActionInvariants
- test_voice_agent_e2e.py
- EventBus
- Event
- ToolCall
- Bootstrapper
- PsutilProcess
- _RecordingProvider
- CommandRegistry
- TextToSpeech
- OpenCVTemplateProvider
- PolicyEngine
- VoiceService
- asyncio
- safe_metadata
- LLMEngine
- VoicePipeline
- ._reject_if_terminal
- voice/service.py
- HUDWindow
- ApplicationService
- DemoScript
- Any
- FileController
- MSSScreen
- .test_the_registered_engine_is_preferred
- PipeReader
- CLIUI
- Win32Window
- wire
- Any
- ProcessController
- MouseService
- VisionError
- _RecordingProvider
- .create
- make_service
- HUDConfig
- LLMToolLoop
- _one
- _state
- observability/__init__.py
- PlaywrightProvider
- get_logger
- vision/main.py
- WindowController
- ClipboardService
- audio.py
- VisionProvider
- ContextBuilder
- FakeLLMProvider
- asyncio
- HUDProcess
- PlanResult
- LLMProvider
- MemoryProvider
- strategy.py
- ProcessService
- asyncio
- ContextBuilder
- tool
- bootstrapper.py
- WindowService
- Detection
- YOLOProvider
- ._bootstrap_desktop
- BrowserProvider
- commands.py
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestEveryRegisteredToolHasAUsableSchema
- test_tools.py
- OpenAICompatibleProvider
- BrowserService
- scene.py
- RecoveryRunner
- asyncio
- FasterWhisperSTT
- tool_calls
- test_cli_agent.py
- ClipboardController
- .from_dict
- FakeKeyboard
- TaskManager
- KeyboardController
- ScreenService
- PyAutoGuiKeyboard
- FakeMouse
- window/tools.py
- tool_calls.py
- make_provider
- VoiceState
- _FakeMouse
- ToolError
- .from_events
- test_agent_execution.py
- ._review
- RenderContext
- FakeHUDProcess
- ToolResult
- PyAutoGuiMouse
- PyAutoGuiClipboard
- process/tools.py
- _RecordingMouse
- resolve_level
- automation/tools.py
- ToolCommandService
- ServiceContainer
- PolicyEvaluation
- Renderer
- Application
- test_interface_contracts.py
- qcolor
- make_vision_service
- PlannerConfig
- test_input.py
- vision/tools.py
- VoiceActivator
- test_agent_planner.py
- LiveTraceUI
- application/tools.py
- TextBlock
- screen/tools.py
- ToolDiscovery
- AgentCore
- DesktopError
- Layer
- FakeScreen
- Message
- MessageQueue
- LLMConfig
- Verifier
- .download
- test_tool_calls.py
- ToolExecutionCoordinator
- ScreenController
- MouseController
- TestNonUnicodeTerminal
- .evaluate
- LLMProviderManager
- ExecutionConfig
- _service
- EdgeTTS
- main
- ._run
- events/__init__.py
- TestMalformedCalls
- bootstrapper
- import_all.py
- .hud
- TestRegisteredToolSurface
- .shutdown
- ToolRegistry
- ParsedResponse
- ExecutionStatus
- asyncio
- Recording
- .voice
- TestDegradation
- TestRawArguments
- real_vision
- TraceCollector
- TestDetectScreenObjects
- Application
- .monitors
- test_ui.py
- TestFinalResponse
- CLIRuntime
- .save
- .test_a_finished_run_executes_nothing
- AetherOS
- coord.py
- TestFailureHandling
- TestEveryToolModuleImports
- TestMSSSave
- .grab
- .to_dict
- .generate
- ._bootstrap_vision
- boot
- _FakeMouseController
- ._live_context
- _summarise_value
- .to_dict
- .to_dict
- .trace
- .__init__
- .tool_schemas
- .drag_relative
- .size

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 200 edges
2. `Image` - 171 edges
3. `AgentState` - 136 edges
4. `tool()` - 105 edges
5. `AgentPlanner` - 102 edges
6. `ToolExecutionCoordinator` - 100 edges
7. `define()` - 99 edges
8. `ToolExecutor` - 93 edges
9. `get_logger()` - 92 edges
10. `AgentContext` - 78 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py
- `agent_parts()` --uses--> `Agent`  [INFERRED]
  tests/agents/test_agent.py → src/aetheros/agents/agent.py
- `TestToolExposure` --uses--> `ContextConfig`  [INFERRED]
  tests/agents/test_agent_context.py → src/aetheros/agents/context.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (224 total, 25 thin omitted)

### Community 0 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 1 - "Image"
Cohesion: 0.04
Nodes (24): ColorSpace, Image, ndarray, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV…, Universal image model for AetherOS. Every vision module should consume and… (+16 more)

### Community 2 - "answer"
Cohesion: 0.09
Nodes (33): answer(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas…, add(), _assert_every_tool_message_is_answerable(), explodes() (+25 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (49): Executes registered AetherOS tools., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes(), asyncio (+41 more)

### Community 4 - "automation/engine.py"
Cohesion: 0.07
Nodes (41): BaseSettings, get_settings(), Singleton Settings object., Settings, _append_recovery_detail(), _backoff_seconds(), The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Run a workflow, or validate it when ``workflow.dry_run`` is set. (+33 more)

### Community 5 - "executor.py"
Cohesion: 0.07
Nodes (29): Level 1+2: import every tool module, report registration. The module list is…, Parameter, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, is_unconstrained(), public_parameters(), Any, Signature, Annotation resolution shared by the schema generator and the validator. Every… (+21 more)

### Community 6 - "vision/__init__.py"
Cohesion: 0.08
Nodes (25): VisionProvider, Vision system for AetherOS. Provides OCR, object detection, template matching,…, Vision domain models., Any, Represents a template match result., TemplateMatch, BaseVisionProvider, DetectionProvider (+17 more)

### Community 7 - "VoiceConfig"
Cohesion: 0.07
Nodes (20): AudioCapture, AudioPlayer, Microphone capture with energy-based silence detection. PortAudio delivers…, Non-blocking playback of mono float32 PCM. Amplitude is measured inside the…, Abort playback immediately., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always…, Configuration for the AetherOS voice subsystem. Values may be supplied directly… (+12 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (20): Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:…, Smoothed audio level, 0..1., Slowly decaying peak, used for the outer bloom., The particles this frame should draw. Intensity and quality both trim from the…, Amplitude history ordered so index 0 is the oldest bin., Adopt a new snapshot, starting a style transition if the state changed. (+12 more)

### Community 9 - "AgentError"
Cohesion: 0.04
Nodes (62): browser_observation(), _mean_confidence(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``…, Observe browser state. The seam the task asks for: there is no browser-state… (+54 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (36): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, Build a workflow from a plain dict, as ``run_workflow`` receives it., Calls, engine(), _failing_state(), _matching_state(), asyncio (+28 more)

### Community 11 - "AgentState"
Cohesion: 0.05
Nodes (22): File a failure in the run's error ledger. Field by field rather than by handing…, AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, Outcome of a single tool execution. Carries failures as data rather than as…, ToolExecutionResult, call(), failed_result() (+14 more)

### Community 12 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 13 - "VerificationResult"
Cohesion: 0.07
Nodes (33): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, What was checked, what was expected, and what was actually observed. The four…, True only for a real, passing check. UNSUPPORTED and SKIPPED are both false…, VerificationResult, ClipboardStrategy, FileStrategy (+25 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (33): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+25 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.09
Nodes (20): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, The request payload, in the order the provider expects. Exactly one system…, Counts and tool names only -- the view the sinks may keep., AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not. (+12 more)

### Community 16 - "OpenCVProvider"
Cohesion: 0.07
Nodes (24): OpenCVProvider, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, EnvelopeResult, _ocr_with(), asyncio, parametrize (+16 more)

### Community 17 - "HUDService"
Cohesion: 0.06
Nodes (23): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+15 more)

### Community 18 - "ToolResultRecord"
Cohesion: 0.17
Nodes (7): Record the outcome, tolerating a run that ended underneath it. The only way…, What came back from one tool call. A failed tool is data, not an exception: the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, Every result recorded against one call id., Record what a tool returned. ``ok=False`` is data, not an error., _render(), ToolResultRecord

### Community 19 - "test_tool_schema.py"
Cohesion: 0.06
Nodes (31): NotAnImportableType, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse(), optionals(), Any (+23 more)

### Community 20 - "HUDSnapshot"
Cohesion: 0.09
Nodes (35): QApplication, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window…, Run driven by a parent process over stdio. This is how HUDService starts the… (+27 more)

### Community 21 - "ErrorContext"
Cohesion: 0.04
Nodes (40): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, BrowserError (+32 more)

### Community 22 - "TestActionInvariants"
Cohesion: 0.07
Nodes (13): Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because…, The action on the wire: ``type`` plus only the fields it uses. Faithful, and…, Log-safe: counts, names and planner-authored reasons only. ``reason`` is… (+5 more)

### Community 23 - "test_voice_agent_e2e.py"
Cohesion: 0.08
Nodes (21): _flag(), _integer(), _number(), Build a configuration from AETHEROS_* environment variables., _text(), EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for… (+13 more)

### Community 24 - "EventBus"
Cohesion: 0.09
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "Event"
Cohesion: 0.05
Nodes (56): Event, Base class for all events in AetherOS. Every event inherits from this class., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM., The LLM produced a response., The LLM requested a tool from the existing ToolRegistry. (+48 more)

### Community 26 - "ToolCall"
Cohesion: 0.04
Nodes (38): AgentExecutionResult, _as_tool_call(), ExecutionBatch, _failure(), Any, A failure in the engine's own currency, for a call the engine never saw.…, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked. (+30 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.09
Nodes (6): Bootstrapper, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Whether Playwright can be imported. find_spec rather than a try/import:…

### Community 28 - "PsutilProcess"
Cohesion: 0.10
Nodes (19): PsutilProcess, Any, Path, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle…, Read one process into a plain dict. Fields that require privileges are filled…, Start a program and return its pid. ``env``, when given, *extends* the current…, Open a file with its registered application. Returns ``0``, which means "no pid… (+11 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.13
Nodes (4): Any, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.09
Nodes (9): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace…, Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal. (+1 more)

### Community 31 - "TextToSpeech"
Cohesion: 0.05
Nodes (25): ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Synthesize and play `text`, returning when playback ends. Must not block the…, Stop playback immediately. Safe to call when nothing is playing. (+17 more)

### Community 32 - "OpenCVTemplateProvider"
Cohesion: 0.07
Nodes (19): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, bgr_image(), A small BGR image whose channels are all different. Uniform grey would hide a…, Scales that would make the template larger than the image are dropped rather… (+11 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.05
Nodes (49): The policy gate consulted before delegation, or ``None`` when the coordinator…, PolicyConfig, Policy configuration: the rules the engine evaluates against. Deliberately…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, The policy engine: evaluates a requested tool call, and never runs it. This is…, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --… (+41 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "asyncio"
Cohesion: 0.10
Nodes (16): _injecting_init(), asyncio, `publisher.publish()` is how code fires an event without holding a bus., Dropping the reference is not enough: the HUD registers bound methods, so a…, A headless or server install must not try to open a window., Nothing should grab the microphone or install a global hotkey hook unless it…, The common case: `aether` on a machine with both flags unset., The gate is the caller's, not HUDService's — the service stays usable from a… (+8 more)

### Community 36 - "safe_metadata"
Cohesion: 0.14
Nodes (9): Any, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, safe_metadata(), truncate_value(), Log-safe projections for trace payloads (PHASES 3, 5, 11). The redaction rules…, TestRedactKeys, TestSafeMetadata (+1 more)

### Community 37 - "LLMEngine"
Cohesion: 0.11
Nodes (14): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, add() (+6 more)

### Community 38 - "VoicePipeline"
Cohesion: 0.10
Nodes (16): Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE., Run one turn under a timeout, mapping failures onto ERROR., Outcome of one voice interaction. (+8 more)

### Community 39 - "._reject_if_terminal"
Cohesion: 0.10
Nodes (12): ErrorRecord, BaseException, Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would…, Open the transcript with the system prompt and the goal., Claim the next iteration, or refuse. Check-then-increment is exactly why the… (+4 more)

### Community 40 - "voice/service.py"
Cohesion: 0.06
Nodes (26): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+18 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (18): QMouseEvent, QPaintEvent, QWidget, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own…, Show the overlay and begin animating. (+10 more)

### Community 42 - "ApplicationService"
Cohesion: 0.13
Nodes (19): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+11 more)

### Community 43 - "DemoScript"
Cohesion: 0.18
Nodes (7): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:…, Coerce a name into a state, defaulting to IDLE. Unknown names must not break…

### Community 44 - "Any"
Cohesion: 0.12
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MSSScreen"
Cohesion: 0.11
Nodes (17): MSSScreen, MSS implementation of the ScreenController interface. Provides high-performance…, Release MSS resources., fake_sct(), FakeSCT, mss_screen(), fixture, parametrize (+9 more)

### Community 47 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.12
Nodes (16): Build a reasoner from whatever LLM layer is registered. The already-built…, add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A caller that built only a provider still gets a working reasoner — it just has…, Better to fail loudly at startup than to answer every spoken turn with an error. (+8 more)

### Community 48 - "PipeReader"
Cohesion: 0.10
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 49 - "CLIUI"
Cohesion: 0.14
Nodes (6): Panel, CLIUI, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI.

### Community 50 - "Win32Window"
Cohesion: 0.10
Nodes (18): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+10 more)

### Community 51 - "wire"
Cohesion: 0.12
Nodes (15): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., A missing optional backend must not cost the caller the OCR result it would… (+7 more)

### Community 52 - "Any"
Cohesion: 0.11
Nodes (12): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly., The transcript in provider wire format, ready to send., ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-…, _reject_unknown() (+4 more)

### Community 53 - "ProcessController"
Cohesion: 0.07
Nodes (18): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+10 more)

### Community 54 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 55 - "VisionError"
Cohesion: 0.09
Nodes (15): Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary)., Grab a region and drop the alpha channel. mss hands back BGRA; slicing to three… (+7 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - ".create"
Cohesion: 0.07
Nodes (20): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,… (+12 more)

### Community 58 - "make_service"
Cohesion: 0.13
Nodes (15): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+7 more)

### Community 59 - "HUDConfig"
Cohesion: 0.09
Nodes (17): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+9 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.05
Nodes (29): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., AgentLoopResult (+21 more)

### Community 61 - "_one"
Cohesion: 0.21
Nodes (7): _one(), SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., Parse a response expected to hold exactly one call, and return it., The OpenAI wire format sends arguments as a JSON *string*., A provider that passes the wire shape through verbatim keeps the name and…, TestWellFormedCalls

### Community 62 - "_state"
Cohesion: 0.13
Nodes (14): Any, A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., One faithful view for auditing, one redacted view for the sinks. (+6 more)

### Community 63 - "observability/__init__.py"
Cohesion: 0.07
Nodes (51): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, trace_context(), TraceSpan (+43 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 65 - "get_logger"
Cohesion: 0.06
Nodes (37): Agent context assembly. One :class:`AgentContext` is everything the model needs…, _planned_to_call(), The agent core loop: the driver that turns a goal into a finished run. This is…, Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, Agent layer. Four pieces so far. :mod:`~aetheros.agents.state` is the explicit,…, ActionType, PlannedAction (+29 more)

### Community 66 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 67 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "audio.py"
Cohesion: 0.07
Nodes (39): Future, LevelCallback, AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed. (+31 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "ContextBuilder"
Cohesion: 0.07
Nodes (24): _clamp(), ContextBuilder, _describe_call(), _describe_result(), IterationInfo, Any, Observation, Where the run is in its budget. Carried explicitly because the model behaves… (+16 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.05
Nodes (25): Whether the far end has gone away., make_unclosable_ocr(), Raises from ``close()``. Shutdown must survive a provider that cannot release…, UnclosableOCRProvider, asyncio, parametrize, Path, skipif (+17 more)

### Community 74 - "HUDProcess"
Cohesion: 0.09
Nodes (14): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+6 more)

### Community 75 - "PlanResult"
Cohesion: 0.08
Nodes (15): PlanResult, No next step exists. ``error_type`` names the kind of wall hit., What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only… (+7 more)

### Community 76 - "LLMProvider"
Cohesion: 0.12
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "strategy.py"
Cohesion: 0.10
Nodes (26): _parse_condition(), Verification — reading state back after a desktop action. The public surface is…, Enum, str, The result contract every desktop tool returns. Before this module every…, Outcome of the verification pass for a single action. ``str`` mixin so the…, VerificationStatus, MatchMode (+18 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.12
Nodes (8): asyncio, parametrize, The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing, TestReadText

### Community 81 - "ContextBuilder"
Cohesion: 0.07
Nodes (38): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call(), asyncio, ContextBuilder (+30 more)

### Community 82 - "tool"
Cohesion: 0.20
Nodes (24): _browser(), browser_back(), browser_forward(), browser_press_key(), browser_reload(), browser_screenshot(), click_element(), close_browser() (+16 more)

### Community 83 - "bootstrapper.py"
Cohesion: 0.11
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 85 - "Detection"
Cohesion: 0.08
Nodes (9): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., FakeDetectionProvider (+1 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.11
Nodes (9): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Whether detection can run without a download., YOLOProvider, Weights are never fetched implicitly: a silent download would put an internet…, The inverse: make one package look installed even when it is not. Lets the…, _show_package() (+1 more)

### Community 87 - "._bootstrap_desktop"
Cohesion: 0.13
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.05
Nodes (18): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page title., Return the current page URL. (+10 more)

### Community 89 - "commands.py"
Cohesion: 0.27
Nodes (6): Execute a parsed command., CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 92 - "parse_llm_response"
Cohesion: 0.23
Nodes (5): parse_llm_response(), Normalise a provider tool-call response. Never raises. Accepts the shape…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn., TestContent

### Community 93 - "TestEveryRegisteredToolHasAUsableSchema"
Cohesion: 0.17
Nodes (6): fixture, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations…, A parameter with no default that is missing from ``required`` lets the model…, An open schema lets a model invent an argument, which arrives as an unexpected…, TestEveryRegisteredToolHasAUsableSchema

### Community 94 - "test_tools.py"
Cohesion: 0.11
Nodes (12): executor(), fixture, parametrize, Tests for the vision tools and their registry integration. These exercise the…, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry… (+4 more)

### Community 95 - "OpenAICompatibleProvider"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 96 - "BrowserService"
Cohesion: 0.09
Nodes (4): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Release the browser if one is still open. Called from…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "scene.py"
Cohesion: 0.13
Nodes (18): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, The interpolated style for this frame., Cross-fade toward the target style., One orbiting mote. Motion is a closed-form function of time rather than an… (+10 more)

### Community 98 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 101 - "tool_calls"
Cohesion: 0.09
Nodes (25): AgentLoopConfig, Bounds and behaviour for a single loop run., tool_calls(), add(), explodes(), HookRecorder, Any, asyncio (+17 more)

### Community 102 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - ".from_dict"
Cohesion: 0.11
Nodes (11): _as_float(), Any, Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., parametrize, Every bound is enforced in a constructor, so an unbounded workflow cannot exist…, "Never create infinite retries" is not satisfied by a large number either: 500…, Unknown keys are rejected rather than ignored. A step that says ``{"method":… (+3 more)

### Community 105 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 106 - "TaskManager"
Cohesion: 0.06
Nodes (37): Any, TaskContext, InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError (+29 more)

### Community 107 - "KeyboardController"
Cohesion: 0.12
Nodes (8): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab

### Community 108 - "ScreenService"
Cohesion: 0.19
Nodes (10): Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, ScreenService, make_fake_screen(), asyncio, A capture failure must surface, not be turned into an empty frame that OCR… (+2 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 113 - "make_provider"
Cohesion: 0.09
Nodes (36): _build(), _CountingExecutor, move_mouse(), Any, asyncio, fixture, Tests for the agent core loop. ``AgentCore`` is the driver that turns a goal…, A core and its counting executor over the same registry. (+28 more)

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 116 - "ToolError"
Cohesion: 0.17
Nodes (11): Exception, ToolError, Sentinel type for "the caller did not specify a timeout". ``None`` cannot serve…, _Unset, Any, Signature, Validates tool arguments before execution. Arguments arriving from an LLM are…, isinstance check with the numeric-tower adjustments JSON requires. (+3 more)

### Community 117 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 118 - "test_agent_execution.py"
Cohesion: 0.09
Nodes (29): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+21 more)

### Community 119 - "._review"
Cohesion: 0.29
Nodes (3): Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read.

### Community 120 - "RenderContext"
Cohesion: 0.10
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "FakeHUDProcess"
Cohesion: 0.11
Nodes (8): FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first., The state of every snapshot sent, in order., Stands in for HUDProcess without launching anything. Records what the service…

### Community 122 - "ToolResult"
Cohesion: 0.16
Nodes (7): Any, Outcome of one desktop action, as the model sees it. Distinct from…, Whether the caller may proceed as if the action happened. False when the…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, The JSON shape the model receives. ``verified`` is lifted to the top level…, ToolResult

### Community 123 - "PyAutoGuiMouse"
Cohesion: 0.11
Nodes (3): PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.13
Nodes (8): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 125 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 126 - "_RecordingMouse"
Cohesion: 0.11
Nodes (4): _fake_mouse(), Bind the ``MouseService`` the tool resolves to a recording controller.…, A ``MouseController`` sitting where PyAutoGUI would. Records every absolute…, _RecordingMouse

### Community 127 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 128 - "automation/tools.py"
Cohesion: 0.15
Nodes (17): describe_strategies(), Recovery — bounded self-healing between step attempts. A retry that changes…, Strategy name to description. Read by the ``run_workflow`` tool description and…, One move within a recovery strategy. Either a tool call, or a pause, or both —…, RecoveryAction, _build(), list_recovery_strategies(), Any (+9 more)

### Community 129 - "ToolCommandService"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 130 - "ServiceContainer"
Cohesion: 0.18
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 131 - "PolicyEvaluation"
Cohesion: 0.11
Nodes (12): PolicyDecision, PolicyEvaluation, Any, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a…, The policy's answer to one request, as data. Returned rather than raised so a… (+4 more)

### Community 132 - "Renderer"
Cohesion: 0.14
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "Application"
Cohesion: 0.19
Nodes (6): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main()

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "qcolor"
Cohesion: 0.10
Nodes (15): QLinearGradient, QPixmap, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., GlowCache, RGB, qcolor() (+7 more)

### Community 136 - "make_vision_service"
Cohesion: 0.13
Nodes (9): make_fake_detector(), make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., No readable text is an outcome, not a failure., Positional wiring is rejected: ``VisionService(ocr, cv)`` and…, TestDetectObjects, TestServiceInitialisation (+1 more)

### Community 137 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 138 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 139 - "vision/tools.py"
Cohesion: 0.40
Nodes (12): analyze_screen(), _blocks(), _capture(), detect_screen_objects(), find_text(), Any, OCR a saved image. Kept separate from read_screen_text so text recognition can…, Capture the screen as a vision Image. ScreenService returns a raw BGR… (+4 more)

### Community 140 - "VoiceActivator"
Cohesion: 0.06
Nodes (18): ABC, WakeCallback, Abstract activation source for the voice pipeline. An activator decides *when*…, Activator name, e.g. "push-to-talk"., Whether the activator is currently armed., Arm the activator. `on_activate` may be invoked from a foreign thread, so…, Disarm the activator and release any OS hooks., VoiceActivator (+10 more)

### Community 141 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 142 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 143 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 144 - "TextBlock"
Cohesion: 0.05
Nodes (24): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, fake_ocr() (+16 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 147 - "AgentCore"
Cohesion: 0.08
Nodes (15): AgentCore, AgentRunResult, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal… (+7 more)

### Community 148 - "DesktopError"
Cohesion: 0.08
Nodes (20): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Application service. An application is not a process, and conflating the two is…, _from_registry(), is_uri(), Application name resolution. The model asks for "notepad", or "calculator", or…, Whether a target is a shell URI (``ms-settings:``, ``mailto:``) rather than a… (+12 more)

### Community 149 - "Layer"
Cohesion: 0.17
Nodes (19): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, ParticleLayer (+11 more)

### Community 150 - "FakeScreen"
Cohesion: 0.21
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 151 - "Message"
Cohesion: 0.13
Nodes (11): Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, decode(), encode(), Frame one message as a single line of JSON. Newline-delimited JSON rather than…, Parse one line, or None if it is not a message. Junk is expected rather than…, Collect whatever the overlay has reported since last time., drain() (+3 more)

### Community 152 - "MessageQueue"
Cohesion: 0.16
Nodes (8): Where the render process sends messages. Routes to the parent when there is…, _Reporter, config_message(), MessageQueue, Any, Protocol, The slice of multiprocessing.Queue the HUD actually uses. Typed as a protocol…, Apply a new configuration to a running overlay. The child rebuilds its window…

### Community 153 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 154 - "Verifier"
Cohesion: 0.17
Nodes (7): Poll a condition until it holds, or until the deadline passes. The single…, Shorthand for the common case: a service already read its own state back., Append polling context to a result without losing what it observed., Dispatches verification requests to the strategy that implements them.…, Method name to one-line description. Used by the health check and by the…, Run one verification. :param force: Ignore ``DESKTOP_VERIFY_ACTIONS``. Used by…, Verifier

### Community 155 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 156 - "test_tool_calls.py"
Cohesion: 0.25
Nodes (3): Parsing of provider tool-call responses. Everything the model emits is…, A tool message whose tool_call_id matches nothing in the assistant turn is a…, TestCallIdentifiers

### Community 157 - "ToolExecutionCoordinator"
Cohesion: 0.13
Nodes (9): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, The agent-layer coordinator used by legacy loop calls., One round, several calls: all answered, in order, one at a time., What counts as a validated call, and what is a programming error. These raise…, TestCallShapes (+1 more)

### Community 158 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 159 - "MouseController"
Cohesion: 0.08
Nodes (11): MouseController, ABC, Drag to an absolute position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y), Move the mouse to an absolute screen position. Named ``x``/``y`` rather than… (+3 more)

### Community 160 - "TestNonUnicodeTerminal"
Cohesion: 0.14
Nodes (10): cp1252_stdout(), fixture, MonkeyPatch, ``errors="replace"`` is the second half of the fix. Without it a single…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, The regression itself: this raised UnicodeEncodeError from _show_logo., Asserts the mechanism, not just the absence of a crash — so that a future…, StringIO has no ``reconfigure``, which is how pytest's own capture and most… (+2 more)

### Community 161 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 163 - "ExecutionConfig"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 164 - "_service"
Cohesion: 0.28
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "EdgeTTS"
Cohesion: 0.16
Nodes (6): EdgeTTS, AmplitudeCallback, Fetch MP3 audio for `text`., Neural speech synthesis via Microsoft Edge's read-aloud voices. Chosen because…, Verify the library is importable. No connection is made here: a network check…, Synthesize and play `text`.

### Community 167 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 170 - "events/__init__.py"
Cohesion: 0.17
Nodes (13): get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application…, Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., set_event_bus(), clear_subscribers(), get_subscribers() (+5 more)

### Community 171 - "TestMalformedCalls"
Cohesion: 0.17
Nodes (4): Valid JSON, but not an object: it cannot be splatted into a signature., A tool message must carry a name, so a nameless call cannot be answered inside…, Dropping it silently would leave the model repeating the same broken call until…, TestMalformedCalls

### Community 172 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out.…

### Community 175 - "TestRegisteredToolSurface"
Cohesion: 0.17
Nodes (7): ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, Asserts against the process-wide registry, which the @tool decorator populates…, TestRegisteredToolSurface

### Community 177 - "ToolRegistry"
Cohesion: 0.06
Nodes (25): Assemble a core from a provider and, optionally, its collaborators. The…, The registry this executor validates and runs tools from., Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _CountingExecutor, The real executor, recording every tool it was actually asked to run. A name…, _CountingExecutor, The real executor, recording every tool it was actually asked to run. A name… (+17 more)

### Community 178 - "ParsedResponse"
Cohesion: 0.22
Nodes (5): ParsedResponse, Normalised view of one provider response., parametrize, A provider that returned plain text still yields a usable answer., TestDegenerateInput

### Community 179 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 180 - "asyncio"
Cohesion: 0.21
Nodes (8): boom(), A tool that always fails, to drive the tool-failure path., Any, asyncio, Best-effort emission and the timed span context (PHASES 2, 5, 12). The contract…, TestEmitTraceIsBestEffort, TestEmitTracePublishes, TestTraceContext

### Community 181 - "Recording"
Cohesion: 0.33
Nodes (4): Captured microphone audio., Recording, _FakeCapture, Stands in for the microphone. Returns one non-silent recording so the pipeline…

### Community 183 - "TestDegradation"
Cohesion: 0.29
Nodes (5): _raising_start(), The child's stderr goes to DEVNULL, so a missing PySide6 would surface only as…, VoiceService.start() raises only when no reasoner can be resolved, which means…, Stand in for a VoiceService whose reasoner cannot be resolved., TestDegradation

### Community 184 - "TestRawArguments"
Cohesion: 0.29
Nodes (3): The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, TestRawArguments

### Community 185 - "real_vision"
Cohesion: 0.29
Nodes (7): ocr_provider(), fixture, One provider for the whole module. Building the models is the expensive part of…, A VisionService with a real OCR backend — no fakes anywhere in the path., The reference image read once, through the whole service., real_vision(), recognised()

### Community 186 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 187 - "TestDetectScreenObjects"
Cohesion: 0.33
Nodes (3): ultralytics and its weights are optional, so the agent has to be told the…, execute() is the raising variant; execute_safe() is the one the agent loop uses., TestDetectScreenObjects

### Community 190 - "test_ui.py"
Cohesion: 0.33
Nodes (3): _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, The terminal UI must not be able to abort the application. Bootstrap succeeding…

### Community 191 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 192 - "CLIRuntime"
Cohesion: 0.32
Nodes (3): CLIRuntime, Read one prompt line without blocking the event loop. `console.input()` blocks…, Interactive AetherOS CLI runtime.

### Community 193 - ".save"
Cohesion: 0.25
Nodes (5): ndarray, Path, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region., Save a captured frame to disk.

### Community 206 - "TestFailureHandling"
Cohesion: 0.29
Nodes (3): A vision tool invoked before bootstrap has run. The agent should get a readable…, The duration is what makes a slow-then-failed tool distinguishable from one…, TestFailureHandling

### Community 207 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 208 - "TestMSSSave"
Cohesion: 0.47
Nodes (3): Path, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame…, TestMSSSave

### Community 209 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 211 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 213 - "boot"
Cohesion: 0.50
Nodes (4): boot(), _clean_env(), fixture, A bootstrapper whose container is isolated from the process-wide one.…

### Community 216 - "_summarise_value"
Cohesion: 0.67
Nodes (3): Any, Trim a tool's return value to something a result can carry., _summarise_value()

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2179 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `automation/tools.py`, `automation/engine.py`, `Application`, `executor.py`, `vision/__init__.py`, `VoiceConfig`, `policy.py`, `VerificationResult`, `PaddleOCRProvider`, `VoiceActivator`, `AgentCore`, `DesktopError`, `Event`, `Verifier`, `Bootstrapper`, `CommandRegistry`, `MouseController`, `ScreenController`, `PolicyEngine`, `TextToSpeech`, `ExecutionConfig`, `voice/service.py`, `Any`, `ProcessController`, `MouseService`, `HUDConfig`, `Application`, `LLMToolLoop`, `observability/__init__.py`, `CLIRuntime`, `WindowController`, `ContextBuilder`, `HUDProcess`, `LLMProvider`, `strategy.py`, `ProcessService`, `bootstrapper.py`, `YOLOProvider`, `._bootstrap_desktop`, `BrowserProvider`, `commands.py`, `LifecycleManager`, `RecoveryRunner`, `FasterWhisperSTT`, `ClipboardController`, `KeyboardController`, `VoiceState`, `ToolError`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Image` connect `Image` to `OpenCVTemplateProvider`, `vision/main.py`, `vision/__init__.py`, `vision/tools.py`, `strategy.py`, `PaddleOCRProvider`, `TextBlock`, `OpenCVProvider`, `TestMSSSave`, `asyncio`, `wire`, `ErrorContext`, `Detection`, `VisionError`, `YOLOProvider`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `HUDConfig` connect `HUDConfig` to `scene.py`, `Scene`, `HUDWindow`, `HUDProcess`, `HUDService`, `bootstrapper.py`, `HUDSnapshot`, `Message`, `MessageQueue`, `Event`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `Image` (e.g. with `VisionService` and `reference_image()`) actually correct?**
  _`Image` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AgentPlanner` (e.g. with `PlannedAction` and `PlanResult`) actually correct?**
  _`AgentPlanner` has 14 INFERRED edges - model-reasoned connections that need verification._