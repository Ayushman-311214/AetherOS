# Graph Report - AetherOS  (2026-09-24)

## Corpus Check
- 258 files · ~213,841 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5710 nodes · 12983 edges · 217 communities (180 shown, 26 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1370 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b9970f94`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolExecutionCoordinator
- Image
- define
- ToolExecutor
- automation/engine.py
- agents/core.py
- VisionError
- VoiceConfig
- Scene
- test_agent_observation.py
- AutomationEngine
- AgentState
- policy.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- asyncio
- HUDService
- ToolCall
- get_llm_tools
- Message
- VisionService
- PlannedAction
- test_voice_agent_e2e.py
- EventBus
- Event
- AgentExecutionResult
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- TextToSpeech
- OpenCVTemplateProvider
- PolicyEngine
- VoiceService
- asyncio
- safe_preview
- LLMEngine
- VoicePipeline
- AgentError
- voice/service.py
- HUDWindow
- ApplicationService
- HUDSnapshot
- test_agent_planner.py
- FileController
- MSSScreen
- .test_the_registered_engine_is_preferred
- PipeReader
- CLIUI
- Win32Window
- wire
- Any
- ProcessController
- tool
- OpenCVProvider
- _RecordingProvider
- .create
- FakeHUDProcess
- HUDConfig
- LLMToolLoop
- _one
- _state
- emit_trace
- PlaywrightProvider
- get_logger
- vision/main.py
- WindowController
- ClipboardService
- renderer.py
- VisionProvider
- ContextBuilder
- FakeLLMProvider
- asyncio
- HUDProcess
- PlanResult
- LLMProvider
- MemoryProvider
- verification/tools.py
- ProcessService
- asyncio
- ContextBuilder
- browser/tools.py
- bootstrapper.py
- WindowInfo
- test_agent_e2e.py
- YOLOProvider
- TerminalService
- BrowserProvider
- cli/main.py
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestRegisteredToolSurface
- TestRegistration
- OpenAICompatibleProvider
- BrowserService
- WindowService
- RecoveryRunner
- asyncio
- FasterWhisperSTT
- tool_calls
- test_cli_agent.py
- ClipboardController
- Step
- FakeKeyboard
- TaskManager
- KeyboardController
- ScreenService
- PyAutoGuiKeyboard
- FakeMouse
- window/tools.py
- tool_calls.py
- ToolRegistry
- VoiceStateMachine
- _FakeMouse
- test_agent.py
- Agent
- test_agent_execution.py
- RejectedToolCall
- RenderContext
- tasks/__init__.py
- verification/__init__.py
- PyAutoGuiMouse
- PyAutoGuiClipboard
- process/tools.py
- _RecordingMouse
- resolve_level
- Any
- ToolCommandService
- ServiceContainer
- policy/__init__.py
- Renderer
- Application
- test_interface_contracts.py
- GlowCache
- make_vision_service
- PlannerConfig
- test_input.py
- vision/tools.py
- VoiceActivator
- test_manager.py
- TraceEvent
- application/tools.py
- TextBlock
- screen/tools.py
- ToolDiscovery
- agents/__init__.py
- WindowBounds
- Layer
- FakeScreen
- ._await_exit
- TaskContext
- LLMConfig
- .open_file
- .download
- TestCallIdentifiers
- .executor
- ScreenController
- MouseController
- .messages
- .evaluate
- LLMProviderManager
- ExecutionConfig
- _service
- .test_open_navigate_and_read_title_through_the_agent
- main
- builder
- recorder.py
- test_screen.py
- bootstrapper
- import_all.py
- .hud
- qcolor
- .shutdown
- AgentCore
- AgentLoopResult
- ExecutionStatus
- asyncio
- _win32_clipboard
- .voice
- .close
- .copy_files
- .copy_image
- TraceCollector
- test_tools.py
- persistence.py
- .monitors
- test_ui.py
- TestFinalResponse
- CLIRuntime
- .save
- .pid
- AetherOS
- TestFailureHandling
- TestEveryToolModuleImports
- TestMSSSave
- .grab
- Panel
- .generate
- PulseLayer
- boot
- _FakeMouseController
- ._live_context
- .trace
- .__init__

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
- `test_from_dict_rejects_unknown_field()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_from_dict_requires_source()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (217 total, 26 thin omitted)

### Community 0 - "ToolExecutionCoordinator"
Cohesion: 0.12
Nodes (21): Runs one planned tool call through the engine and records what happened. Holds…, ToolExecutionCoordinator, _call(), _journalled(), Any, asyncio, An async tool that brackets its own run in ``journal``. Two entries rather than…, Argument names may be logged. Argument values may not. ``type_text`` and… (+13 more)

### Community 1 - "Image"
Cohesion: 0.04
Nodes (27): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+19 more)

### Community 2 - "define"
Cohesion: 0.09
Nodes (38): answer(), define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas…, add() (+30 more)

### Community 3 - "ToolExecutor"
Cohesion: 0.04
Nodes (55): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…, Executes registered AetherOS tools. (+47 more)

### Community 4 - "automation/engine.py"
Cohesion: 0.07
Nodes (40): BaseSettings, get_settings(), Singleton Settings object., Settings, _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every… (+32 more)

### Community 5 - "agents/core.py"
Cohesion: 0.06
Nodes (44): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Agent context assembly. One :class:`AgentContext` is everything the model needs…, The agent core loop: the driver that turns a goal into a finished run. This is…, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, Agent planner. One responsibility: ``GOAL -> the next action``. The planner…, Agent execution state. One :class:`AgentState` is the complete, explicit record…, Exception (+36 more)

### Community 6 - "VisionError"
Cohesion: 0.05
Nodes (49): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError (+41 more)

### Community 7 - "VoiceConfig"
Cohesion: 0.06
Nodes (24): AudioCapture, Microphone capture with energy-based silence detection. PortAudio delivers…, _flag(), _integer(), _number(), Build a configuration from AETHEROS_* environment variables., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always… (+16 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (36): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+28 more)

### Community 9 - "test_agent_observation.py"
Cohesion: 0.04
Nodes (59): Record one :class:`Observation` per delegated tool result. A refused call…, browser_observation(), _mean_confidence(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``… (+51 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (39): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, An ordered list of steps and the policy for running them., Build a workflow from a plain dict, as ``run_workflow`` receives it., The same workflow, validated instead of executed., Workflow, Calls, engine() (+31 more)

### Community 11 - "AgentState"
Cohesion: 0.05
Nodes (20): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, call(), failed_result(), ok_result(), _populated_state(), asyncio (+12 more)

### Community 12 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 13 - "VerificationResult"
Cohesion: 0.05
Nodes (41): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, What was checked, what was expected, and what was actually observed. The four…, True only for a real, passing check. UNSUPPORTED and SKIPPED are both false… (+33 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (30): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+22 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.08
Nodes (20): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not. (+12 more)

### Community 16 - "asyncio"
Cohesion: 0.13
Nodes (17): EnvelopeResult, _ocr_with(), asyncio, Unit tests for the concrete vision providers. The OpenCV and template providers…, Stands in for a built PaddleOCR pipeline. Records the frame it was handed so a…, A PaddleOCR 3.x result seen through its documented ``json`` accessor. The…, A real provider whose model construction is replaced by a stub. ``_build`` is…, The channel-order regression. PaddleX's reader defaults to ``format="BGR"`` and… (+9 more)

### Community 17 - "HUDService"
Cohesion: 0.06
Nodes (23): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+15 more)

### Community 18 - "ToolCall"
Cohesion: 0.08
Nodes (20): _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Record a call that was turned away, without the engine being asked. The refusal…, Report a refusal that could not be written down. Reached only when the run is…, Write the outcome into the run, then describe it. The record is built before it…, File a failure in the run's error ledger. Field by field rather than by handing…, Build the result. Pure -- no state, no clock beyond the elapsed span. The…, One line per attempt, returning the result unchanged.… (+12 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "Message"
Cohesion: 0.08
Nodes (38): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window… (+30 more)

### Community 21 - "VisionService"
Cohesion: 0.06
Nodes (27): High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService (+19 more)

### Community 22 - "PlannedAction"
Cohesion: 0.05
Nodes (21): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim. (+13 more)

### Community 23 - "test_voice_agent_e2e.py"
Cohesion: 0.06
Nodes (32): Captured microphone audio., Recording, EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, HookRecorder, Any, The voice reasoner — the seam between a spoken turn and the LLM tool loop.… (+24 more)

### Community 24 - "EventBus"
Cohesion: 0.09
Nodes (18): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent., TraceRecorder (+10 more)

### Community 25 - "Event"
Cohesion: 0.04
Nodes (63): Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM. (+55 more)

### Community 26 - "AgentExecutionResult"
Cohesion: 0.05
Nodes (24): AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values…, Log-safe: names, outcomes and timings, never values. ``error`` is included… (+16 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.08
Nodes (7): Bootstrapper, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…, Whether Playwright can be imported. find_spec rather than a try/import:…

### Community 28 - "DesktopError"
Cohesion: 0.09
Nodes (23): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, PsutilProcess, Any, Path, psutil process backend. Two safety rules are enforced here, in the backend,…, Fetch a psutil handle, translating its errors into DesktopError. psutil's… (+15 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.13
Nodes (4): Any, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.09
Nodes (9): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace…, Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal. (+1 more)

### Community 31 - "TextToSpeech"
Cohesion: 0.03
Nodes (50): Speech synthesis or audio playback failed., TextToSpeechError, ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources. (+42 more)

### Community 32 - "OpenCVTemplateProvider"
Cohesion: 0.05
Nodes (23): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, Any, Represents a template match result., TemplateMatch, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in… (+15 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.06
Nodes (36): PolicyConfig, Any, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --…, Release the stop. Deliberately explicit: nothing clears it on the engine's… (+28 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "asyncio"
Cohesion: 0.07
Nodes (22): _injecting_init(), asyncio, _raising_start(), `publisher.publish()` is how code fires an event without holding a bus., Dropping the reference is not enough: the HUD registers bound methods, so a…, A headless or server install must not try to open a window., Nothing should grab the microphone or install a global hotkey hook unless it…, The common case: `aether` on a machine with both flags unset. (+14 more)

### Community 36 - "safe_preview"
Cohesion: 0.09
Nodes (16): Run one goal to a terminal state and report the outcome. Creates and seeds a…, Any, Log-safe projections for trace payloads. The trace persists to disk and renders…, Redact forbidden keys without shortening the surviving values. For the…, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, redact_keys() (+8 more)

### Community 37 - "LLMEngine"
Cohesion: 0.12
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 38 - "VoicePipeline"
Cohesion: 0.11
Nodes (15): Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE., Run one turn under a timeout, mapping failures onto ERROR., Outcome of one voice interaction. (+7 more)

### Community 39 - "AgentError"
Cohesion: 0.07
Nodes (21): _as_tool_call(), Normalise what the caller handed over into a :class:`ToolCall`. A ``tool_call``…, Accept a member or its name; reject anything else. An unknown source is…, ErrorRecord, BaseException, Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state… (+13 more)

### Community 40 - "voice/service.py"
Cohesion: 0.04
Nodes (50): Future, LevelCallback, AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Base exception for all voice-subsystem errors. Examples: - Microphone… (+42 more)

### Community 41 - "HUDWindow"
Cohesion: 0.08
Nodes (17): QMouseEvent, QPaintEvent, QWidget, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own…, Show the overlay and begin animating. (+9 more)

### Community 42 - "ApplicationService"
Cohesion: 0.11
Nodes (23): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+15 more)

### Community 43 - "HUDSnapshot"
Cohesion: 0.07
Nodes (22): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+14 more)

### Community 44 - "test_agent_planner.py"
Cohesion: 0.08
Nodes (32): builder(), context(), _FailingProvider, move_mouse(), planner(), provider(), Any, asyncio (+24 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MSSScreen"
Cohesion: 0.15
Nodes (10): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, FakeSCT, parametrize, ``np.asarray`` over an mss ScreenShot aliases a buffer mss reuses, so the next…, Stands in for an ``mss.mss()`` session. Returns BGRA, the way mss does, so the…, TestMSSCapture (+2 more)

### Community 47 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 48 - "PipeReader"
Cohesion: 0.09
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 49 - "CLIUI"
Cohesion: 0.11
Nodes (11): CLIUI, Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI., MonkeyPatch, ``errors="replace"`` is the second half of the fix. Without it a single…, The regression itself: this raised UnicodeEncodeError from _show_logo., Asserts the mechanism, not just the absence of a crash — so that a future… (+3 more)

### Community 50 - "Win32Window"
Cohesion: 0.11
Nodes (17): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+9 more)

### Community 51 - "wire"
Cohesion: 0.12
Nodes (15): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., A missing optional backend must not cost the caller the OCR result it would… (+7 more)

### Community 52 - "Any"
Cohesion: 0.13
Nodes (8): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly., The transcript in provider wire format, ready to send., _reject_unknown(), _require()

### Community 53 - "ProcessController"
Cohesion: 0.11
Nodes (10): ProcessController, ABC, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running., Wait for a process to exit., Open a URL in the default browser. (+2 more)

### Community 54 - "tool"
Cohesion: 0.10
Nodes (20): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+12 more)

### Community 55 - "OpenCVProvider"
Cohesion: 0.10
Nodes (11): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, parametrize, A fixed COLOR_BGR2GRAY would weight red and blue the wrong way round for RGB… (+3 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (4): Any, Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - ".create"
Cohesion: 0.10
Nodes (13): Build an event, defaulting the stage label from the type., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Flush and close every open file. Safe to call more than once., TraceFileWriter, The trace event vocabulary (PHASE 1). ``TraceEvent`` is the single class every…, TestTraceEventCreate, TestTraceEventToDict (+5 more)

### Community 58 - "FakeHUDProcess"
Cohesion: 0.06
Nodes (23): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+15 more)

### Community 59 - "HUDConfig"
Cohesion: 0.07
Nodes (22): main(), Run driven by a parent process over stdio. This is how HUDService starts the…, Standalone entry point. Exists so the HUD can be developed and visually…, _run_ipc(), _as_bool(), _as_float(), _as_int(), _as_text() (+14 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.09
Nodes (20): LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text. (+12 more)

### Community 61 - "_one"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 62 - "_state"
Cohesion: 0.17
Nodes (11): Any, Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., A state that has not run yet still produces a usable payload., _sample_tools() (+3 more)

### Community 63 - "emit_trace"
Cohesion: 0.16
Nodes (19): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, trace_context(), TraceSpan (+11 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 65 - "get_logger"
Cohesion: 0.06
Nodes (34): __init__(), Application, Main AetherOS application. Responsible for starting and shutting down the…, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+26 more)

### Community 66 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 67 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, A ring of fine radial graduations. Pure technical texture — the detail that…, TickLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "ContextBuilder"
Cohesion: 0.05
Nodes (30): _clamp(), ContextBuilder, _describe_call(), _describe_result(), IterationInfo, Any, Observation, Where the run is in its budget. Carried explicitly because the model behaves… (+22 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 75 - "PlanResult"
Cohesion: 0.09
Nodes (13): PlanResult, What one planning round produced. The question the planner answers is singular…, Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only…, Emit LLM_RESPONSE_RECEIVED from observable response data only. Reads…, Emit PLANNER_DECISION from the log-safe ``describe`` projection. (+5 more)

### Community 76 - "LLMProvider"
Cohesion: 0.13
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "verification/tools.py"
Cohesion: 0.11
Nodes (20): _parse_condition(), MatchMode, parse_mode(), parse_region(), PositionStrategy, Any, Enum, str (+12 more)

### Community 79 - "ProcessService"
Cohesion: 0.14
Nodes (7): ProcessService, Any, Path, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching…, High-level process operations., Resolve a name to exactly one process, or explain why it could not. Refuses to…

### Community 80 - "asyncio"
Cohesion: 0.12
Nodes (8): asyncio, parametrize, The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing, TestReadText

### Community 81 - "ContextBuilder"
Cohesion: 0.07
Nodes (37): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, An assistant turn, optionally carrying the calls the model asked for.…, _call(), asyncio, ContextBuilder, Tests for the agent context layer. The properties under test are the ones the…, A snapshot that can be edited after assembly is not a snapshot. (+29 more)

### Community 82 - "browser/tools.py"
Cohesion: 0.14
Nodes (24): _browser(), browser_back(), browser_forward(), browser_press_key(), browser_reload(), browser_screenshot(), click_element(), close_browser() (+16 more)

### Community 83 - "bootstrapper.py"
Cohesion: 0.10
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 84 - "WindowInfo"
Cohesion: 0.10
Nodes (14): Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Poll until a matching window appears, or the timeout expires. Polling rather…, Poll until a matching window holds focus, or the timeout expires. Distinct from…, Poll ``probe`` until it returns a window, bounded by ``timeout``. The bound is…, Synchronous selector matching, for use inside poll probes. (+6 more)

### Community 85 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.06
Nodes (18): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., Any (+10 more)

### Community 87 - "TerminalService"
Cohesion: 0.14
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
Cohesion: 0.09
Nodes (4): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Release the browser if one is still open. Called from…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "WindowService"
Cohesion: 0.17
Nodes (10): Human-readable condition, used when the caller did not supply one., Any, Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``., A full snapshot, which carries the bounds along with everything else., High-level window service. Backed by a :class:`WindowController`; holds no…, Full snapshot in one call. Uses the backend's ``describe`` when it has one --… (+2 more)

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
Cohesion: 0.10
Nodes (22): AgentLoopConfig, Bounds and behaviour for a single loop run., tool_calls(), add(), explodes(), HookRecorder, Any, asyncio (+14 more)

### Community 102 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 103 - "ClipboardController"
Cohesion: 0.10
Nodes (10): ClipboardController, ABC, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"…, Copy text to the clipboard., Returns clipboard text. (+2 more)

### Community 104 - "Step"
Cohesion: 0.09
Nodes (16): _as_float(), _clamp_seconds(), Any, Attempts to make, resolved against configuration and clamped., Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., Coerce a duration to a non-negative float no larger than ``ceiling``., One tool call, with the conditions around it. Fields ------ name Label used in… (+8 more)

### Community 105 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

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

### Community 113 - "ToolRegistry"
Cohesion: 0.08
Nodes (30): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, move_mouse(), Any, asyncio, fixture (+22 more)

### Community 114 - "VoiceStateMachine"
Cohesion: 0.12
Nodes (8): Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal…, Force the machine back to IDLE. Used by shutdown and cancellation paths, where…, VoiceStateMachine, StateListener

### Community 116 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 117 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 118 - "test_agent_execution.py"
Cohesion: 0.09
Nodes (28): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), move_mouse(), fixture (+20 more)

### Community 119 - "RejectedToolCall"
Cohesion: 0.18
Nodes (6): A call the planner refused to pass on, and why. Carries enough to answer the…, Whether a ``tool`` message can carry this rejection back. A provider rejects a…, RejectedToolCall, Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read.

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 122 - "verification/__init__.py"
Cohesion: 0.18
Nodes (10): Verification — reading state back after a desktop action. The public surface is…, Enum, str, The result contract every desktop tool returns. Before this module every…, Outcome of one desktop action, as the model sees it. Distinct from…, Whether the caller may proceed as if the action happened. False when the…, The JSON shape the model receives. ``verified`` is lifted to the top level…, Outcome of the verification pass for a single action. ``str`` mixin so the… (+2 more)

### Community 123 - "PyAutoGuiMouse"
Cohesion: 0.10
Nodes (5): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.18
Nodes (6): Path, PyAutoGuiClipboard, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 125 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 127 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 128 - "Any"
Cohesion: 0.22
Nodes (5): Any, Returns process information. Example: name pid cpu_percent memory_usage…, Returns all running processes., Find a process by PID., Find processes by executable name.

### Community 129 - "ToolCommandService"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 130 - "ServiceContainer"
Cohesion: 0.18
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 131 - "policy/__init__.py"
Cohesion: 0.10
Nodes (15): Policy configuration: the rules the engine evaluates against. Deliberately…, PolicyDecision, PolicyEvaluation, Any, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a… (+7 more)

### Community 132 - "Renderer"
Cohesion: 0.14
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "Application"
Cohesion: 0.19
Nodes (6): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main()

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 136 - "make_vision_service"
Cohesion: 0.12
Nodes (10): make_fake_detector(), make_fake_ocr(), make_unclosable_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., No readable text is an outcome, not a failure., Positional wiring is rejected: ``VisionService(ocr, cv)`` and…, TestDetectObjects (+2 more)

### Community 137 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 138 - "test_input.py"
Cohesion: 0.24
Nodes (9): keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every…, _swapped() (+1 more)

### Community 139 - "vision/tools.py"
Cohesion: 0.40
Nodes (12): analyze_screen(), _blocks(), _capture(), detect_screen_objects(), find_text(), Any, OCR a saved image. Kept separate from read_screen_text so text recognition can…, Capture the screen as a vision Image. ScreenService returns a raw BGR… (+4 more)

### Community 140 - "VoiceActivator"
Cohesion: 0.06
Nodes (19): ABC, WakeCallback, Abstract activation source for the voice pipeline. An activator decides *when*…, Activator name, e.g. "push-to-talk"., Whether the activator is currently armed., Arm the activator. `on_activate` may be invoked from a foreign thread, so…, Disarm the activator and release any OS hooks., VoiceActivator (+11 more)

### Community 141 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 142 - "TraceEvent"
Cohesion: 0.10
Nodes (17): Any, One observed moment in a run, safe to log and to persist. Only observable, log-…, A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., TraceEvent, A copy of the buffered events, newest last., LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises. (+9 more)

### Community 143 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 144 - "TextBlock"
Cohesion: 0.04
Nodes (26): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, fake_ocr() (+18 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 147 - "agents/__init__.py"
Cohesion: 0.09
Nodes (17): AgentRunResult, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, Agent layer. Four pieces so far. :mod:`~aetheros.agents.state` is the explicit,…, ActionType, Enum, str, Planner actions and results. The value types the planner returns. They exist so…, What the planner decided. ``str``-valued so a serialized action reads as… (+9 more)

### Community 148 - "WindowBounds"
Cohesion: 0.22
Nodes (4): A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 149 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, One arc group in the ring system., Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, RingSpec

### Community 150 - "FakeScreen"
Cohesion: 0.21
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 151 - "._await_exit"
Cohesion: 0.29
Nodes (4): Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Poll until the process is gone, returning whether it went. Returns a bool…

### Community 153 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 154 - ".open_file"
Cohesion: 0.40
Nodes (3): Path, Start a new process. Returns: Process ID (PID), Open a file with its default application. Returns: Process ID if available.

### Community 155 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 158 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

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
Cohesion: 0.28
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - ".test_open_navigate_and_read_title_through_the_agent"
Cohesion: 0.21
Nodes (9): _build(), _CountingExecutor, _fake_browser(), asyncio, The real executor, recording every tool it was actually asked to run. A name…, Bind the ``BrowserService`` the tools resolve to a recording provider. Every…, Copy production tool definitions into an isolated registry., TestBrowserTitleE2E (+1 more)

### Community 167 - "builder"
Cohesion: 0.67
Nodes (3): builder(), fixture, A builder over an isolated registry, never the process-wide one.

### Community 170 - "recorder.py"
Cohesion: 0.15
Nodes (14): The single trace subscriber (PHASES 2, 6, 8, 9). ``TraceRecorder`` is the one…, get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application…, Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., set_event_bus(), clear_subscribers() (+6 more)

### Community 171 - "test_screen.py"
Cohesion: 0.22
Nodes (7): fake_sct(), mss_screen(), fixture, Tests for the screen capture layer. Screen capture is where the vision…, mss raises on construction without a display, so the DI container would…, A real MSSScreen backed by a fake session instead of a display., TestMSSBackendInitialisation

### Community 172 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out.…

### Community 175 - "qcolor"
Cohesion: 0.16
Nodes (10): QLinearGradient, QPointF, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side… (+2 more)

### Community 177 - "AgentCore"
Cohesion: 0.14
Nodes (12): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Assemble a core from a provider and, optionally, its collaborators. The…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, _fake_mouse(), _is_ordered_subsequence(), Any (+4 more)

### Community 179 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 180 - "asyncio"
Cohesion: 0.21
Nodes (8): boom(), A tool that always fails, to drive the tool-failure path., Any, asyncio, Best-effort emission and the timed span context (PHASES 2, 5, 12). The contract…, TestEmitTraceIsBestEffort, TestEmitTracePublishes, TestTraceContext

### Community 181 - "_win32_clipboard"
Cohesion: 0.25
Nodes (4): Any, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard()

### Community 184 - ".copy_files"
Cohesion: 0.40
Nodes (3): Path, Copy one or more files/folders to the clipboard., Returns copied file paths. Returns: Empty list if clipboard contains no files.

### Community 185 - ".copy_image"
Cohesion: 0.40
Nodes (3): Any, Copy an image to the clipboard., Returns an image from the clipboard. Returns: None if clipboard doesn't contain…

### Community 186 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 187 - "test_tools.py"
Cohesion: 0.18
Nodes (7): executor(), fixture, Tests for the vision tools and their registry integration. These exercise the…, ultralytics and its weights are optional, so the agent has to be told the…, execute() is the raising variant; execute_safe() is the one the agent loop uses., An executor over the process-wide registry, which is where @tool registers., TestDetectScreenObjects

### Community 188 - "persistence.py"
Cohesion: 0.20
Nodes (6): Persist a run's trace as JSON Lines. One file per run at…, Append one event to its run's file. Never raises., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,…, _safe_name(), TestSafeName, TextIO

### Community 190 - "test_ui.py"
Cohesion: 0.22
Nodes (6): _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, cp1252_stdout(), fixture, The terminal UI must not be able to abort the application. Bootstrap succeeding…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…

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

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2165 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `policy/__init__.py`, `automation/engine.py`, `agents/core.py`, `Application`, `VisionError`, `VoiceConfig`, `PlannerConfig`, `policy.py`, `VerificationResult`, `VoiceActivator`, `agents/__init__.py`, `Bootstrapper`, `CommandRegistry`, `MouseController`, `ScreenController`, `PolicyEngine`, `TextToSpeech`, `ExecutionConfig`, `LLMEngine`, `voice/service.py`, `recorder.py`, `AgentCore`, `ProcessController`, `HUDConfig`, `persistence.py`, `CLIRuntime`, `WindowController`, `ContextBuilder`, `HUDProcess`, `ProcessService`, `bootstrapper.py`, `YOLOProvider`, `TerminalService`, `BrowserProvider`, `cli/main.py`, `LifecycleManager`, `RecoveryRunner`, `FasterWhisperSTT`, `ClipboardController`, `KeyboardController`, `VoiceStateMachine`, `Agent`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `Image` connect `Image` to `OpenCVTemplateProvider`, `vision/main.py`, `automation/engine.py`, `VisionError`, `vision/tools.py`, `PaddleOCRProvider`, `TextBlock`, `asyncio`, `TestMSSSave`, `asyncio`, `wire`, `VisionService`, `YOLOProvider`, `OpenCVProvider`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `DesktopError` connect `DesktopError` to `automation/engine.py`, `VisionError`, `AutomationEngine`, `policy.py`, `VerificationResult`, `WindowBounds`, `MouseController`, `ApplicationService`, `Win32Window`, `_win32_clipboard`, `get_logger`, `verification/tools.py`, `ProcessService`, `WindowInfo`, `TerminalService`, `Step`, `KeyboardController`, `PyAutoGuiKeyboard`, `PyAutoGuiMouse`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `Image` (e.g. with `VisionService` and `reference_image()`) actually correct?**
  _`Image` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AgentPlanner` (e.g. with `PlannedAction` and `PlanResult`) actually correct?**
  _`AgentPlanner` has 14 INFERRED edges - model-reasoned connections that need verification._