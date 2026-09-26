# Graph Report - AetherOS  (2026-09-26)

## Corpus Check
- 263 files · ~221,291 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5843 nodes · 13405 edges · 199 communities (163 shown, 25 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1455 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9467ae40`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _started
- Image
- answer
- define
- automation/engine.py
- executor.py
- VisionError
- ServiceContainer
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
- EventBus
- get_llm_tools
- app.py
- VisionService
- PlannedAction
- test_voice_agent_e2e.py
- TraceRecorder
- VoicePipeline
- AgentExecutionResult
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- NullTTS
- OpenCVTemplateProvider
- PolicyEngine
- VoiceService
- test_wiring.py
- safe_metadata
- LLMEngine
- Workflow
- observability/pipeline.py
- SpeechToText
- HUDWindow
- ApplicationService
- hud/service.py
- ContextBuilder
- FileController
- scene.py
- .test_the_registered_engine_is_preferred
- PipeReader
- CLIUI
- Win32Window
- wire
- test_unified_interaction.py
- ProcessController
- tool
- Any
- _RecordingProvider
- .create
- asyncio
- hud/config.py
- LLMToolLoop
- _one
- test_agent.py
- TraceEvent
- PlaywrightProvider
- .record
- vision/main.py
- WindowController
- ClipboardService
- SapiTTS
- VisionProvider
- Any
- FakeLLMProvider
- asyncio
- HUDConfig
- application/tools.py
- LLMProvider
- MemoryProvider
- _safe_name
- ProcessService
- asyncio
- _state
- browser/tools.py
- bootstrapper.py
- WindowService
- ContextBuilder
- YOLOProvider
- ._bootstrap_desktop
- BrowserProvider
- cli/main.py
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestRegisteredToolSurface
- TestRegistration
- OpenAICompatibleProvider
- BrowserService
- NullActivator
- RecoveryRunner
- asyncio
- test_ui.py
- HookRecorder
- test_cli_agent.py
- ClipboardController
- Application
- FakeKeyboard
- TaskManager
- KeyboardController
- TestDeterminism
- PyAutoGuiKeyboard
- FakeMouse
- window/tools.py
- MalformedToolCall
- ToolRegistry
- VoiceState
- _FakeMouse
- ToolExecutionResult
- .from_events
- test_agent_execution.py
- ._bootstrap_browser
- RenderContext
- FakeHUDProcess
- Agent
- PyAutoGuiMouse
- PyAutoGuiClipboard
- process/tools.py
- _RecordingMouse
- resolve_level
- ._bootstrap_voice
- ToolCommandService
- ToolCall
- policy/__init__.py
- Renderer
- Application
- test_interface_contracts.py
- .speak
- .start
- PlannerConfig
- test_input.py
- vision/tools.py
- VoiceConfig
- test_agent_planner.py
- _NonTerminalConsole
- .trace
- .name
- screen/tools.py
- get_logger
- window/controller.py
- qcolor
- TextBlock
- test_agent_e2e.py
- tasks/__init__.py
- LLMConfig
- .download
- TestCallIdentifiers
- ToolExecutionCoordinator
- ScreenService
- MouseController
- .evaluate
- LLMProviderManager
- ExecutionConfig
- _service
- main
- ._run
- test_browser_tools_e2e.py
- GlowCache
- import_all.py
- .hud
- test_manager.py
- .test_a_finished_run_executes_nothing
- .from_provider
- asyncio
- emit_trace
- TaskContext
- ExecutionStatus
- TraceCollector
- TestEveryToolModuleImports
- EchoReasoner
- TestFinalResponse
- CLIRuntime
- AetherOS
- AgentLoopResult
- bootstrapper
- MSSScreen
- .voice
- .generate
- ._live_context
- .__init__

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 220 edges
2. `Image` - 171 edges
3. `AgentState` - 136 edges
4. `tool()` - 107 edges
5. `AgentPlanner` - 102 edges
6. `define()` - 102 edges
7. `ToolExecutionCoordinator` - 100 edges
8. `get_logger()` - 94 edges
9. `ToolExecutor` - 94 edges
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

## Communities (199 total, 25 thin omitted)

### Community 0 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 1 - "Image"
Cohesion: 0.04
Nodes (26): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+18 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (50): Executes registered AetherOS tools., The registry this executor validates and runs tools from., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes() (+42 more)

### Community 4 - "automation/engine.py"
Cohesion: 0.07
Nodes (36): BaseSettings, get_settings(), Singleton Settings object., Settings, _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every… (+28 more)

### Community 5 - "executor.py"
Cohesion: 0.04
Nodes (48): Level 1+2: import every tool module, report registration. The module list is…, Parameter, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Exception, ToolError, Recovery — bounded self-healing between step attempts. A retry that changes…, One move within a recovery strategy. Either a tool call, or a pause, or both —…, RecoveryAction (+40 more)

### Community 6 - "VisionError"
Cohesion: 0.04
Nodes (60): Exception, BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,… (+52 more)

### Community 7 - "ServiceContainer"
Cohesion: 0.18
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (20): Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:…, The interpolated style for this frame., Smoothed audio level, 0..1., Slowly decaying peak, used for the outer bloom., Amplitude history ordered so index 0 is the oldest bin., Adopt a new snapshot, starting a style transition if the state changed. (+12 more)

### Community 9 - "AgentError"
Cohesion: 0.04
Nodes (64): browser_observation(), _mean_confidence(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``…, Observe browser state. The seam the task asks for: there is no browser-state… (+56 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (36): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, Build a workflow from a plain dict, as ``run_workflow`` receives it., Calls, engine(), _failing_state(), _matching_state(), asyncio (+28 more)

### Community 11 - "AgentState"
Cohesion: 0.04
Nodes (27): AgentState, ErrorRecord, Message, BaseException, Stop the run on request. Distinct from failure: nothing went wrong., A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, One turn of the conversation, in the shape the providers expect. Frozen: a…, The provider-facing shape, matching ``LLMToolLoop`` exactly. (+19 more)

### Community 12 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (73): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, _parse_condition(), Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only… (+65 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (32): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+24 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.07
Nodes (23): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider… (+15 more)

### Community 16 - "OpenCVProvider"
Cohesion: 0.06
Nodes (27): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, EnvelopeResult, _ocr_with() (+19 more)

### Community 17 - "HUDService"
Cohesion: 0.05
Nodes (24): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+16 more)

### Community 18 - "EventBus"
Cohesion: 0.05
Nodes (56): EventHandler, EventBus, Central event bus for AetherOS. Features: - Sync + Async handlers - Multiple…, Register an event handler., Publish an event. Every subscriber receives the event., Event, Any, Base class for all events in AetherOS. Every event inherits from this class. (+48 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.05
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "app.py"
Cohesion: 0.09
Nodes (32): QApplication, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window…, Run driven by a parent process over stdio. This is how HUDService starts the… (+24 more)

### Community 21 - "VisionService"
Cohesion: 0.06
Nodes (25): High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService (+17 more)

### Community 22 - "PlannedAction"
Cohesion: 0.04
Nodes (37): PlannedAction, PlanResult, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner… (+29 more)

### Community 23 - "test_voice_agent_e2e.py"
Cohesion: 0.07
Nodes (25): Captured microphone audio., Recording, Records what would have been spoken. The test double for speech output: it…, RecordingTTS, _agent_reasoner(), _BlockingReasoner, _CountingExecutor, _FailingTTS (+17 more)

### Community 24 - "TraceRecorder"
Cohesion: 0.12
Nodes (14): Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent., TraceRecorder (+6 more)

### Community 25 - "VoicePipeline"
Cohesion: 0.10
Nodes (17): Speech was converted to text., SpeechTranscribed, Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE. (+9 more)

### Community 26 - "AgentExecutionResult"
Cohesion: 0.06
Nodes (18): AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values…, Log-safe: names, outcomes and timings, never values. ``error`` is included… (+10 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.10
Nodes (5): Bootstrapper, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…

### Community 28 - "DesktopError"
Cohesion: 0.09
Nodes (23): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, PsutilProcess, Any, Path, psutil process backend. Two safety rules are enforced here, in the backend,…, Fetch a psutil handle, translating its errors into DesktopError. psutil's… (+15 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.13
Nodes (4): Any, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.09
Nodes (9): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace…, Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal. (+1 more)

### Community 31 - "NullTTS"
Cohesion: 0.17
Nodes (3): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…

### Community 32 - "OpenCVTemplateProvider"
Cohesion: 0.05
Nodes (22): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, Any, Represents a template match result., TemplateMatch, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in… (+14 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.06
Nodes (36): PolicyConfig, Any, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --…, Release the stop. Deliberately explicit: nothing clears it on the engine's… (+28 more)

### Community 34 - "VoiceService"
Cohesion: 0.06
Nodes (23): The voice service finished initializing., The voice service released all audio resources., VoiceServiceStarted, VoiceServiceStopped, Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:… (+15 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 36 - "safe_metadata"
Cohesion: 0.13
Nodes (12): Any, Log-safe projections for trace payloads. The trace persists to disk and renders…, Redact forbidden keys without shortening the surviving values. For the…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, redact_keys(), safe_metadata(), truncate_value() (+4 more)

### Community 37 - "LLMEngine"
Cohesion: 0.12
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 38 - "Workflow"
Cohesion: 0.06
Nodes (33): describe_strategies(), Strategy name to description. Read by the ``run_workflow`` tool description and…, _build(), list_recovery_strategies(), Any, The automation tools — multi-step desktop work, exposed to the model. Three…, Turn the model's JSON into a validated :class:`Workflow`. Parse errors are re-…, Execute a workflow and return its full execution record. :param name: Label for… (+25 more)

### Community 39 - "observability/pipeline.py"
Cohesion: 0.11
Nodes (23): _accumulate_status(), _apply_event(), _detail(), PipelineStage, PipelineStatus, _presentation_for(), Any, Enum (+15 more)

### Community 40 - "SpeechToText"
Cohesion: 0.05
Nodes (29): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+21 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.10
Nodes (25): ApplicationService, Any, Path, Application service. An application is not a process, and conflating the two is…, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``… (+17 more)

### Community 43 - "hud/service.py"
Cohesion: 0.09
Nodes (22): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+14 more)

### Community 44 - "ContextBuilder"
Cohesion: 0.15
Nodes (11): _FailingProvider, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise., A finished run has no next action, and costs no tokens to say so. (+3 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "scene.py"
Cohesion: 0.13
Nodes (18): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, The particles this frame should draw. Intensity and quality both trim from the…, Cross-fade toward the target style., One orbiting mote. Motion is a closed-form function of time rather than an… (+10 more)

### Community 47 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 48 - "PipeReader"
Cohesion: 0.08
Nodes (13): IO, decode(), encode(), PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Frame one message as a single line of JSON. Newline-delimited JSON rather than… (+5 more)

### Community 49 - "CLIUI"
Cohesion: 0.09
Nodes (14): CLIUI, Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI., cp1252_stdout(), fixture, MonkeyPatch, ``errors="replace"`` is the second half of the fix. Without it a single… (+6 more)

### Community 50 - "Win32Window"
Cohesion: 0.10
Nodes (19): Any, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match… (+11 more)

### Community 51 - "wire"
Cohesion: 0.08
Nodes (24): executor(), asyncio, fixture, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must… (+16 more)

### Community 52 - "test_unified_interaction.py"
Cohesion: 0.13
Nodes (22): InteractionGateway, Submit a goal to the shared agent, tagged with its front end., _boom(), _build_agent(), _CountingExecutor, _mouse_position(), Any, asyncio (+14 more)

### Community 53 - "ProcessController"
Cohesion: 0.07
Nodes (19): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+11 more)

### Community 54 - "tool"
Cohesion: 0.10
Nodes (20): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+12 more)

### Community 55 - "Any"
Cohesion: 0.11
Nodes (12): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The transcript in provider wire format, ready to send., ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-…, _reject_unknown(), _require() (+4 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - ".create"
Cohesion: 0.09
Nodes (15): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Flush and close every open file. Safe to call more than once., TraceFileWriter, The trace event vocabulary (PHASE 1). ``TraceEvent`` is the single class every… (+7 more)

### Community 58 - "asyncio"
Cohesion: 0.08
Nodes (20): make_service(), Build an unstarted service over a fake process., asyncio, The HUD service — voice event in, overlay snapshot out. This is the only place…, Otherwise the overlay shows this turn's question beside the last one's reply., The HUD is one line; a raw LLM reply would break the layout., `speak()` used directly means nothing reasoned, so no response event., The user acting on the system always beats a cosmetic hold. (+12 more)

### Community 59 - "hud/config.py"
Cohesion: 0.23
Nodes (9): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), Any, Coerce and clamp every field. Runs on every construction path — defaults,…, Rebuild from to_dict(), ignoring unknown keys. Values are coerced by… (+1 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.09
Nodes (18): LLMToolLoop, Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text., Run the loop and return the full record of what happened. (+10 more)

### Community 61 - "_one"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 62 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 63 - "TraceEvent"
Cohesion: 0.08
Nodes (32): Panel, Render a model response., Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, trace_context(), TraceSpan (+24 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 65 - ".record"
Cohesion: 0.18
Nodes (11): LevelCallback, _normalize_level(), Any, ndarray, Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is…, Root-mean-square amplitude of a PCM block. (+3 more)

### Community 66 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 67 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "SapiTTS"
Cohesion: 0.06
Nodes (28): Speech synthesis or audio playback failed., TextToSpeechError, decode_mp3(), decode_wav(), _frame_to_mono(), _load_av(), Any, ndarray (+20 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "Any"
Cohesion: 0.08
Nodes (22): _clamp(), _describe_call(), _describe_result(), IterationInfo, Any, Observation, Where the run is in its budget. Carried explicitly because the model behaves…, The tool name inside a generated schema, or ``""`` if it is malformed. Tolerant… (+14 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "HUDConfig"
Cohesion: 0.05
Nodes (23): Popen, HUDConfig, Configuration for the JARVIS-style overlay., Window edge length in logical pixels., Timer interval for the render loop., Quality tier to start at., Whether quality may be reduced automatically., Build a configuration from AETHEROS_HUD_* variables. Unset and blank variables… (+15 more)

### Community 75 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 76 - "LLMProvider"
Cohesion: 0.12
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Initialize provider resources., Release provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "_safe_name"
Cohesion: 0.24
Nodes (5): Append one event to its run's file. Never raises., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,…, _safe_name(), TestSafeName, TextIO

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.07
Nodes (17): make_fake_detector(), make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:… (+9 more)

### Community 81 - "_state"
Cohesion: 0.17
Nodes (11): Any, Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., A state that has not run yet still produces a usable payload., _sample_tools() (+3 more)

### Community 82 - "browser/tools.py"
Cohesion: 0.16
Nodes (23): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+15 more)

### Community 83 - "bootstrapper.py"
Cohesion: 0.11
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 85 - "ContextBuilder"
Cohesion: 0.06
Nodes (41): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call(), asyncio, ContextBuilder (+33 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.06
Nodes (16): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., Any (+8 more)

### Community 87 - "._bootstrap_desktop"
Cohesion: 0.13
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.05
Nodes (18): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page title., Return the current page URL. (+10 more)

### Community 89 - "cli/main.py"
Cohesion: 0.29
Nodes (6): Execute a parsed command., CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 92 - "parse_llm_response"
Cohesion: 0.12
Nodes (11): parse_llm_response(), ParsedResponse, Normalised view of one provider response., Normalise a provider tool-call response. Never raises. Accepts the shape…, parametrize, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn. (+3 more)

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
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "NullActivator"
Cohesion: 0.20
Nodes (3): NullActivator, WakeCallback, An activator that never fires. This is what "always-listening is off" looks…

### Community 98 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "test_ui.py"
Cohesion: 0.33
Nodes (3): _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, The terminal UI must not be able to abort the application. Bootstrap succeeding…

### Community 101 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 102 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 105 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 107 - "KeyboardController"
Cohesion: 0.12
Nodes (8): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "MalformedToolCall"
Cohesion: 0.19
Nodes (13): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object., Best-effort text form of a malformed payload, for the error report. (+5 more)

### Community 113 - "ToolRegistry"
Cohesion: 0.08
Nodes (30): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, move_mouse(), Any, asyncio, fixture (+22 more)

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (13): Queue a state event. The state machine is synchronous, so publishing is…, Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state. (+5 more)

### Community 116 - "ToolExecutionResult"
Cohesion: 0.10
Nodes (19): _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Report a refusal that could not be written down. Reached only when the run is…, Write the outcome into the run, then describe it. The record is built before it…, Record the outcome, tolerating a run that ended underneath it. The only way…, File a failure in the run's error ledger. Field by field rather than by handing…, Build the result. Pure -- no state, no clock beyond the elapsed span. The…, One line per attempt, returning the result unchanged.… (+11 more)

### Community 117 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 118 - "test_agent_execution.py"
Cohesion: 0.09
Nodes (29): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+21 more)

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "FakeHUDProcess"
Cohesion: 0.06
Nodes (21): bus(), fake_process(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything., The double's class, for tests that need a differently configured one. (+13 more)

### Community 122 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 123 - "PyAutoGuiMouse"
Cohesion: 0.10
Nodes (5): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.12
Nodes (10): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file… (+2 more)

### Community 125 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 127 - "resolve_level"
Cohesion: 0.10
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 129 - "ToolCommandService"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 130 - "ToolCall"
Cohesion: 0.12
Nodes (14): _as_tool_call(), Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, Record the request, before anything is checked or run. Ordered first on…, Normalise what the caller handed over into a :class:`ToolCall`. A ``tool_call``…, A tool the model asked for, tagged with the iteration that asked. Adapts…, Names only. The safe projection for logs — see module docstring., Record a call the model asked for. Accepts the parse layer's :class:`ToolCall`… (+6 more)

### Community 131 - "policy/__init__.py"
Cohesion: 0.10
Nodes (13): PolicyDecision, PolicyEvaluation, Any, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a…, The policy's answer to one request, as data. Returned rather than raised so a… (+5 more)

### Community 132 - "Renderer"
Cohesion: 0.15
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "Application"
Cohesion: 0.19
Nodes (6): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main()

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 137 - "PlannerConfig"
Cohesion: 0.20
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 138 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 139 - "vision/tools.py"
Cohesion: 0.40
Nodes (12): analyze_screen(), _blocks(), _capture(), detect_screen_objects(), find_text(), Any, OCR a saved image. Kept separate from read_screen_text so text recognition can…, Capture the screen as a vision Image. ScreenService returns a raw BGR… (+4 more)

### Community 140 - "VoiceConfig"
Cohesion: 0.04
Nodes (60): Future, AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, ABC, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts". (+52 more)

### Community 141 - "test_agent_planner.py"
Cohesion: 0.15
Nodes (19): builder(), context(), move_mouse(), planner(), provider(), Any, fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one… (+11 more)

### Community 142 - "_NonTerminalConsole"
Cohesion: 0.23
Nodes (5): _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and…, A stand-in console that reports it is not a terminal (e.g. a pipe)., TestLifecycle, TestRender

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 147 - "get_logger"
Cohesion: 0.06
Nodes (41): ContextBuilder, Agent context assembly. One :class:`AgentContext` is everything the model needs…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, AgentRunResult, The agent core loop: the driver that turns a goal into a finished run. This is…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, The one entry a front end submits a turn through. Both the terminal and voice… (+33 more)

### Community 148 - "window/controller.py"
Cohesion: 0.20
Nodes (5): Window service. Adds the one thing the raw :class:`WindowController` interface…, Window identity and geometry. A title is not an identity. Two Explorer windows…, A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds

### Community 149 - "qcolor"
Cohesion: 0.12
Nodes (21): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, ParticleLayer (+13 more)

### Community 150 - "TextBlock"
Cohesion: 0.04
Nodes (37): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, bgr_image() (+29 more)

### Community 151 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 152 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 153 - "LLMConfig"
Cohesion: 0.38
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 155 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 157 - "ToolExecutionCoordinator"
Cohesion: 0.13
Nodes (9): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, One round, several calls: all answered, in order, one at a time., What counts as a validated call, and what is a programming error. These raise…, TestCallShapes (+1 more)

### Community 158 - "ScreenService"
Cohesion: 0.06
Nodes (27): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+19 more)

### Community 159 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 161 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 163 - "ExecutionConfig"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 167 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 171 - "test_browser_tools_e2e.py"
Cohesion: 0.23
Nodes (12): _build(), _CountingExecutor, _fake_browser(), Any, asyncio, End-to-end validation of the browser tools through the Agent Core. This mirrors…, The real executor, recording every tool it was actually asked to run. A name…, Bind the ``BrowserService`` the tools resolve to a recording provider. Every… (+4 more)

### Community 172 - "GlowCache"
Cohesion: 0.11
Nodes (13): QLinearGradient, QPixmap, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy… (+5 more)

### Community 175 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 178 - ".from_provider"
Cohesion: 0.22
Nodes (9): ContextBuilder, Assemble a core from a provider and, optionally, its collaborators. The…, _fake_mouse(), _is_ordered_subsequence(), Any, asyncio, Bind the ``MouseService`` the tool resolves to a fixed-position backend., True if every item of ``expected`` occurs in ``actual`` in order. (+1 more)

### Community 180 - "asyncio"
Cohesion: 0.21
Nodes (8): boom(), A tool that always fails, to drive the tool-failure path., Any, asyncio, Best-effort emission and the timed span context (PHASES 2, 5, 12). The contract…, TestEmitTraceIsBestEffort, TestEmitTracePublishes, TestTraceContext

### Community 181 - "emit_trace"
Cohesion: 0.07
Nodes (26): AgentCore, _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, Record a call that was turned away, without the engine being asked. The refusal… (+18 more)

### Community 185 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 186 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 188 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 189 - "EchoReasoner"
Cohesion: 0.08
Nodes (16): EchoReasoner, Any, Exception, Produce a spoken reply to `text` by running the Agent Core. Cancellation raised…, Returns a canned reply, optionally reporting a tool call. The test double for…, Build a reasoner from whatever LLM layer is registered. The already-built…, Produce a spoken reply to `text`., HookRecorder (+8 more)

### Community 191 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 192 - "CLIRuntime"
Cohesion: 0.22
Nodes (5): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…

### Community 207 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out.…

### Community 208 - "MSSScreen"
Cohesion: 0.07
Nodes (25): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., fake_sct(), FakeSCT, mss_screen() (+17 more)

### Community 211 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2202 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `automation/engine.py`, `Application`, `executor.py`, `VisionError`, `VoiceConfig`, `policy.py`, `VerificationResult`, `PaddleOCRProvider`, `EventBus`, `window/controller.py`, `Bootstrapper`, `CommandRegistry`, `MouseController`, `ScreenService`, `PolicyEngine`, `NullTTS`, `ExecutionConfig`, `Workflow`, `SpeechToText`, `ApplicationService`, `emit_trace`, `ProcessController`, `Any`, `LLMToolLoop`, `TraceEvent`, `WindowController`, `HUDConfig`, `LLMProvider`, `ProcessService`, `bootstrapper.py`, `YOLOProvider`, `._bootstrap_desktop`, `BrowserProvider`, `cli/main.py`, `LifecycleManager`, `NullActivator`, `RecoveryRunner`, `ClipboardController`, `Application`, `KeyboardController`, `ToolRegistry`, `VoiceState`, `Agent`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `ToolCommandService`, `answer`, `define`, `automation/engine.py`, `executor.py`, `PlannerConfig`, `AutomationEngine`, `test_agent_planner.py`, `AgentPlanner`, `get_logger`, `get_llm_tools`, `test_agent_e2e.py`, `test_voice_agent_e2e.py`, `ToolExecutionCoordinator`, `PolicyEngine`, `ExecutionConfig`, `test_browser_tools_e2e.py`, `ContextBuilder`, `.from_provider`, `test_unified_interaction.py`, `ExecutionStatus`, `TestFinalResponse`, `FakeLLMProvider`, `LLMProvider`, `_state`, `ContextBuilder`, `RecoveryRunner`, `test_cli_agent.py`, `TestDeterminism`, `test_agent_execution.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `ToolExecutor` connect `define` to `ToolCommandService`, `answer`, `automation/engine.py`, `executor.py`, `AutomationEngine`, `VoiceConfig`, `get_logger`, `VisionService`, `test_agent_e2e.py`, `test_voice_agent_e2e.py`, `ToolExecutionCoordinator`, `PolicyEngine`, `ExecutionConfig`, `LLMEngine`, `main`, `._run`, `test_browser_tools_e2e.py`, `.test_the_registered_engine_is_preferred`, `.from_provider`, `wire`, `test_unified_interaction.py`, `LLMToolLoop`, `vision/main.py`, `bootstrapper.py`, `RecoveryRunner`, `test_cli_agent.py`, `ToolRegistry`, `test_agent_execution.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `Image` (e.g. with `VisionService` and `reference_image()`) actually correct?**
  _`Image` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AgentPlanner` (e.g. with `PlannedAction` and `PlanResult`) actually correct?**
  _`AgentPlanner` has 14 INFERRED edges - model-reasoned connections that need verification._