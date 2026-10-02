# Graph Report - AetherOS  (2026-09-28)

## Corpus Check
- 345 files · ~273,276 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 7107 nodes · 17113 edges · 242 communities (206 shown, 24 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1961 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ddd675e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _started
- Image
- define
- ToolExecutor
- automation/engine.py
- HUDSnapshot
- VisionError
- WakeWordActivator
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
- _state
- test_tool_schema.py
- Message
- asyncio
- RejectedToolCall
- Event
- EventBus
- CriticService
- AgentExecutionResult
- Bootstrapper
- PsutilProcess
- _RecordingProvider
- CommandRegistry
- HUDProcess
- events/events.py
- PolicyEngine
- VoiceService
- test_wiring.py
- safe_preview
- LLMEngine
- SourceTier
- TextBlock
- test_critic.py
- HUDWindow
- ApplicationService
- Detection
- _FakeMouseController
- FileController
- get_logger
- Any
- PipeReader
- CLIUI
- Win32Window
- wire
- AgentCore
- ProcessController
- tool
- indicators/core.py
- _RecordingProvider
- .create
- FrameCache
- test_grounding_tools.py
- LLMToolLoop
- asyncio
- ContextBuilder
- ToolCall
- PlaywrightProvider
- ContextBuilder
- vision/main.py
- WindowController
- ClipboardService
- ._touch
- VisionProvider
- ContextConfig
- FakeLLMProvider
- asyncio
- test_agent_context.py
- application/tools.py
- LLMProvider
- MemoryProvider
- quant/__init__.py
- ProcessService
- asyncio
- TraceEvent
- browser/tools.py
- KeyboardService
- WindowInfo
- make_market_data
- YOLOProvider
- DesktopError
- BrowserProvider
- Any
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestRegisteredToolSurface
- TestRegistration
- OpenAICompatibleProvider
- BrowserService
- get_settings
- RecoveryRunner
- asyncio
- vision/tools.py
- WindowService
- _build
- ClipboardController
- TestSerialization
- PyAutoGuiMouse
- test_agent.py
- enums.py
- FasterWhisperSTT
- PyAutoGuiKeyboard
- FakeHUDProcess
- window/tools.py
- HUDConfig
- ToolRegistry
- VoiceState
- _FakeMouse
- commands
- .from_events
- test_agent_execution.py
- .test_the_registered_engine_is_preferred
- RenderContext
- .test_a_finished_run_executes_nothing
- Agent
- make_vision_service
- PyAutoGuiClipboard
- process/tools.py
- bootstrapper.py
- resolve_level
- _settings
- ObservationLog
- cli/main.py
- ServiceContainer
- Renderer
- Application
- test_interface_contracts.py
- .assistant
- FakeOCRProvider
- PlannerConfig
- MarketData
- test_indicators.py
- voice/service.py
- PlanResult
- test_probability.py
- test_agent_planner.py
- tools/registry.py
- screen/tools.py
- ProbabilityService
- errors.py
- PolicyEvaluation
- Application
- ErrorContext
- Instrument
- MarketStructureService
- test_orchestration.py
- LogisticRegression
- VoiceConfig
- TestSerializationAndLogging
- Direction
- ScreenService
- MouseController
- ._guard
- ToolExecutionCoordinator
- .test_move_flows_through_the_full_chain_with_arguments
- ExecutionConfig
- _service
- text_match_score
- main
- test_backtest.py
- TaskManager
- NullTTS
- _feature_columns
- import_all.py
- TTLCache
- .record
- ToolExecutionResult
- Any
- TestFinalResponse
- _settings
- emit_trace
- tasks/__init__.py
- test_trading_tools.py
- .test_speech_moves_the_mouse_through_the_agent
- LLMProviderManager
- ._format_tool_signature
- TraceCollector
- tool_calls.py
- Box
- RecordingTTS
- FakeKeyboard
- _RecordingMouse
- spatial.py
- LLMConfig
- test_vision_engine.py
- AetherOS
- Layer
- TextToSpeech
- GlowCache
- LiveTraceUI
- .hud
- ExecutionStatus
- .open_file
- .generate
- ToolDiscovery
- TestToolsCommand
- TestEveryToolModuleImports
- renderer.py
- MSSScreen
- .to_dict
- WindowBounds
- TestServiceInitialisation
- FakeMouse
- .open_url
- _one
- .pid
- test_manager.py
- run_workflow_from_file.py
- qcolor
- test_ui.py
- test_input.py
- AgentLoopResult
- .shutdown
- TestPromptCursor
- TaskContext
- ._ask
- workflow_believer_run.py
- PulseLayer
- bootstrapper
- TickLayer
- coord.py
- .drag_relative

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 242 edges
2. `Image` - 183 edges
3. `AgentState` - 138 edges
4. `tool()` - 123 edges
5. `get_logger()` - 106 edges
6. `define()` - 106 edges
7. `AgentPlanner` - 102 edges
8. `ToolExecutionCoordinator` - 100 edges
9. `ToolExecutor` - 97 edges
10. `EventBus` - 88 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `test_from_dict_rejects_unknown_field()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_from_dict_requires_source()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (242 total, 24 thin omitted)

### Community 0 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 1 - "Image"
Cohesion: 0.03
Nodes (32): ColorSpace, High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a… (+24 more)

### Community 2 - "define"
Cohesion: 0.06
Nodes (61): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), define(), fixture, Factory for ToolDefinition objects (the factory-as-fixture pattern)., tool_calls(), make_loop() (+53 more)

### Community 3 - "ToolExecutor"
Cohesion: 0.04
Nodes (56): The injected execution engine used for delegated tool calls., Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are… (+48 more)

### Community 4 - "automation/engine.py"
Cohesion: 0.04
Nodes (63): _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Run a step's read-back, polling when it declared a timeout. Returns ``None``… (+55 more)

### Community 5 - "HUDSnapshot"
Cohesion: 0.14
Nodes (6): Adopt a new snapshot, starting a style transition if the state changed., Update the live audio level without changing state., HUDSnapshot, Copy with a new state, clearing fields the new state retires., Everything the renderer needs to draw one moment. Immutable and picklable: this…, Adopt a new state snapshot.

### Community 6 - "VisionError"
Cohesion: 0.07
Nodes (16): Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, Path, Write the image to disk with its colours intact., Load an image file, normalised to 3-channel BGR ``uint8``. Pillow decodes to…, OpenCVProvider, ndarray (+8 more)

### Community 7 - "WakeWordActivator"
Cohesion: 0.11
Nodes (6): NullActivator, WakeCallback, Register the global hotkey. Never raises: a hotkey that cannot be registered is…, An activator that never fires. This is what "always-listening is off" looks…, Placeholder for always-listening wake-word detection. The abstraction exists so…, WakeWordActivator

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (35): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+27 more)

### Community 9 - "test_agent_observation.py"
Cohesion: 0.05
Nodes (52): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``… (+44 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.07
Nodes (42): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, ExecutionStatus, Enum, str, Build a workflow from a plain dict, as ``run_workflow`` receives it., What became of one step. ``RECOVERED`` is kept distinct from ``SUCCEEDED`` on…, What became of the workflow as a whole. (+34 more)

### Community 11 - "AgentState"
Cohesion: 0.05
Nodes (12): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,…, asyncio, parametrize, TestCompletion, TestErrors (+4 more)

### Community 12 - "policy.py"
Cohesion: 0.07
Nodes (37): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+29 more)

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (71): Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, Outcome of one desktop action, as the model sees it. Distinct from… (+63 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.04
Nodes (38): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+30 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.10
Nodes (18): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not., One well-formed call for a known tool is planned, not executed., A provider that supports parallel calls gets one action per call. (+10 more)

### Community 16 - "asyncio"
Cohesion: 0.09
Nodes (22): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, _ocr_with(), asyncio, parametrize (+14 more)

### Community 17 - "HUDService"
Cohesion: 0.05
Nodes (24): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+16 more)

### Community 18 - "_state"
Cohesion: 0.15
Nodes (11): Any, Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., A state that has not run yet still produces a usable payload., _sample_tools() (+3 more)

### Community 19 - "test_tool_schema.py"
Cohesion: 0.07
Nodes (23): NotAnImportableType, anything(), containers(), mixed_defaults(), optionals(), Any, Tool schema generation. These tests deliberately live in a module that starts…, A tool annotated with a name that is not importable at runtime must still… (+15 more)

### Community 20 - "Message"
Cohesion: 0.05
Nodes (58): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the… (+50 more)

### Community 21 - "asyncio"
Cohesion: 0.15
Nodes (11): asyncio, Path, The same picture declared RGB must produce the same reading. BGR-to-RGB is its…, A single-channel image must be expanded, not rejected: preprocessing chains…, A blank frame is an empty result, not an error — and not a hallucinated block…, A 2x2 frame is smaller than the detector's receptive field. Whatever the engine…, The full production path minus the display: registry -> executor -> validator…, A round trip through PNG must not change what OCR reads. If save() and open()… (+3 more)

### Community 22 - "RejectedToolCall"
Cohesion: 0.05
Nodes (19): Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because…, The action on the wire: ``type`` plus only the fields it uses. Faithful, and…, Log-safe: counts, names and planner-authored reasons only. ``reason`` is… (+11 more)

### Community 23 - "Event"
Cohesion: 0.05
Nodes (57): Event, Base class for all events in AetherOS. Every event inherits from this class., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM., The LLM produced a response., The LLM requested a tool from the existing ToolRegistry. (+49 more)

### Community 24 - "EventBus"
Cohesion: 0.08
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "CriticService"
Cohesion: 0.11
Nodes (16): CriticCheck, CriticReport, Any, datetime, Critic / validation value objects. A :class:`CriticReport` is the adversary's…, One named check the critic ran, its outcome and a human-readable reason., Deterministic go/no-go verdict on a proposed signal, with its reasoning., True only for an outright APPROVE -- never for REJECT/INSUFFICIENT. (+8 more)

### Community 26 - "AgentExecutionResult"
Cohesion: 0.05
Nodes (21): A stable identity for *what this call did*, for loop detection. Two calls share…, AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``… (+13 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.08
Nodes (7): Bootstrapper, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…, Whether Playwright can be imported. find_spec rather than a try/import:…

### Community 28 - "PsutilProcess"
Cohesion: 0.18
Nodes (11): PsutilProcess, Any, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Read one process into a plain dict. Fields that require privileges are filled…, Every process the current user can see. ``process_iter`` with an explicit…, Every process whose name matches, case-insensitively. Matched with and without…, Whether a process exists *and* has not become a zombie. Distinct from…, Block until a process exits. ``timeout=None`` waits indefinitely, which is why… (+3 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.10
Nodes (7): CommandHandler, CommandRegistry, Execute a parsed command., Registry for AetherOS CLI commands., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace…, Register a CLI command.

### Community 31 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 32 - "events/events.py"
Cohesion: 0.14
Nodes (16): get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application…, Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., set_event_bus(), clear_subscribers(), get_subscribers() (+8 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.05
Nodes (47): PolicyConfig, Any, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --…, Release the stop. Deliberately explicit: nothing clears it on the engine's… (+39 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 36 - "safe_preview"
Cohesion: 0.10
Nodes (15): Any, Log-safe projections for trace payloads. The trace persists to disk and renders…, Redact forbidden keys without shortening the surviving values. For the…, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, redact_keys(), safe_metadata() (+7 more)

### Community 37 - "LLMEngine"
Cohesion: 0.07
Nodes (22): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, add() (+14 more)

### Community 38 - "SourceTier"
Cohesion: 0.04
Nodes (66): Any, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, _utcnow(), VolumeAnalysis (+58 more)

### Community 39 - "TextBlock"
Cohesion: 0.06
Nodes (23): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, Map box coordinates from a downscaled frame back to the original image. Pure… (+15 more)

### Community 40 - "test_critic.py"
Cohesion: 0.30
Nodes (30): CheckStatus, CriticVerdict, Outcome of one critic check. SKIPPED is first-class: a check the current build…, The critic's go/no-go decision on a proposed signal. INSUFFICIENT_EVIDENCE is…, _analysis(), _backtest(), _evidence(), _prov() (+22 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (18): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+10 more)

### Community 42 - "ApplicationService"
Cohesion: 0.13
Nodes (19): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+11 more)

### Community 43 - "Detection"
Cohesion: 0.04
Nodes (40): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+32 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "get_logger"
Cohesion: 0.04
Nodes (57): _clamp(), _describe_call(), Agent context assembly. One :class:`AgentContext` is everything the model needs…, One digest line for a call: names, never values. The model already has the…, Coerce a configured limit into range, or refuse it. Clamping rather than…, AgentRunResult, _planned_to_call(), The agent core loop: the driver that turns a goal into a finished run. This is… (+49 more)

### Community 47 - "Any"
Cohesion: 0.12
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 48 - "PipeReader"
Cohesion: 0.10
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 49 - "CLIUI"
Cohesion: 0.11
Nodes (9): Panel, CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen. (+1 more)

### Community 50 - "Win32Window"
Cohesion: 0.11
Nodes (17): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+9 more)

### Community 51 - "wire"
Cohesion: 0.07
Nodes (27): executor(), asyncio, fixture, Path, Tests for the vision tools and their registry integration. These exercise the…, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in… (+19 more)

### Community 52 - "AgentCore"
Cohesion: 0.10
Nodes (25): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, InteractionGateway, Submit a goal to the shared agent, tagged with its front end., _boom(), _build_agent(), _CountingExecutor (+17 more)

### Community 53 - "ProcessController"
Cohesion: 0.10
Nodes (11): ProcessController, ABC, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running., Wait for a process to exit., Open a URL in the default browser. (+3 more)

### Community 54 - "tool"
Cohesion: 0.10
Nodes (20): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+12 more)

### Community 55 - "indicators/core.py"
Cohesion: 0.17
Nodes (33): adx(), _as_float_array(), atr(), bollinger(), ema(), last_finite(), macd(), _nan_prefix() (+25 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - ".create"
Cohesion: 0.07
Nodes (20): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,… (+12 more)

### Community 58 - "FrameCache"
Cohesion: 0.12
Nodes (15): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, _Clock, _make_capture(), asyncio, Tests for the short-lived screen-frame cache. The clock is injected so time… (+7 more)

### Community 59 - "test_grounding_tools.py"
Cohesion: 0.09
Nodes (17): _block(), executor(), asyncio, fixture, parametrize, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received… (+9 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.09
Nodes (20): LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text. (+12 more)

### Community 61 - "asyncio"
Cohesion: 0.09
Nodes (19): make_service(), Build an unstarted service over a fake process., asyncio, The HUD service — voice event in, overlay snapshot out. This is the only place…, A sample that arrives after capture ended would make a resting overlay twitch., The visualizer scales by this directly; an out-of-range value would draw…, The user acting on the system always beats a cosmetic hold., Deliberately not restarted: a HUD that crashes on startup would otherwise be… (+11 more)

### Community 62 - "ContextBuilder"
Cohesion: 0.17
Nodes (12): asyncio, ContextBuilder, Reads are lock-free because state hands back immutable snapshots., A plain back-and-forth reaches the provider unchanged., Observations are not transcript turns, so the context has to carry them., A running, seeded state on its first iteration., The context tracks where the run is in its budget., Determinism: no clock, no registry order, no set iteration. (+4 more)

### Community 63 - "ToolCall"
Cohesion: 0.11
Nodes (14): _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, Record a call that was turned away, without the engine being asked. The refusal…, Report a refusal that could not be written down. Reached only when the run is…, Write the outcome into the run, then describe it. The record is built before it…, Record the request, before anything is checked or run. Ordered first on… (+6 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 65 - "ContextBuilder"
Cohesion: 0.08
Nodes (22): ContextBuilder, _describe_result(), Any, Observation, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep. (+14 more)

### Community 66 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 67 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "._touch"
Cohesion: 0.09
Nodes (13): ErrorRecord, BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Finish the run unsuccessfully, recording the unrecoverable error., Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, Open the transcript with the system prompt and the goal. (+5 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "ContextConfig"
Cohesion: 0.17
Nodes (7): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., ``tool_categories`` narrows the menu to the relevant tools for a run. Left…, Limits are clamped, not trusted., TestConfiguration, TestToolCategoryScoping

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (16): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per…, Build a provider response requesting the given ``(name, arguments)`` calls.… (+8 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "test_agent_context.py"
Cohesion: 0.11
Nodes (15): builder(), _call(), fixture, Tests for the agent context layer. The properties under test are the ones the…, The payload has to be accepted by the engine that already exists., The invariant the provider enforces, asserted over the whole payload., Tool rounds keep the shape the provider layer already accepts., A tool message whose assistant turn was trimmed fails the request. The provider… (+7 more)

### Community 75 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 76 - "LLMProvider"
Cohesion: 0.13
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "quant/__init__.py"
Cohesion: 0.13
Nodes (20): accuracy(), brier_score(), CalibrationReport, _clip01(), expected_calibration_error(), log_loss(), PlattScaler, Any (+12 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.08
Nodes (12): make_fake_detector(), asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestDetectObjects, TestFindTemplate (+4 more)

### Community 81 - "TraceEvent"
Cohesion: 0.08
Nodes (40): _default_stage(), Enum, str, The trace event vocabulary. One concrete :class:`TraceEvent` class (not a class…, One observed moment in a run, safe to log and to persist. Only observable, log-…, Every stage of the live execution pipeline. ``str``-valued so a serialized…, How the stage an event reports is doing. Kept small and orthogonal to…, TraceEvent (+32 more)

### Community 82 - "browser/tools.py"
Cohesion: 0.16
Nodes (23): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+15 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowInfo"
Cohesion: 0.10
Nodes (14): Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Poll until a matching window appears, or the timeout expires. Polling rather…, Poll until a matching window holds focus, or the timeout expires. Distinct from…, Poll ``probe`` until it returns a window, bounded by ``timeout``. The bound is…, Synchronous selector matching, for use inside poll probes. (+6 more)

### Community 85 - "make_market_data"
Cohesion: 0.13
Nodes (35): DataQualityStatus, downtrend_data(), FakeProvider, flat_data(), make_invalid_market_data(), make_market_data(), _provenance(), datetime (+27 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (16): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Tests for the vision providers' performance-oriented internals. These pin the… (+8 more)

### Community 87 - "DesktopError"
Cohesion: 0.08
Nodes (25): Process, DesktopError, Base exception for all desktop automation errors. Examples: - Mouse movement…, _from_registry(), is_uri(), Application name resolution. The model asks for "notepad", or "calculator", or…, Whether a target is a shell URI (``ms-settings:``, ``mailto:``) rather than a…, Look one executable up in App Paths, returning its full path. The value is the… (+17 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.04
Nodes (25): BrowserProvider, ABC, Any, Path, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element. (+17 more)

### Community 89 - "Any"
Cohesion: 0.16
Nodes (11): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly., The transcript in provider wire format, ready to send., PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would…, ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-… (+3 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 92 - "parse_llm_response"
Cohesion: 0.10
Nodes (12): parse_llm_response(), ParsedResponse, Normalised view of one provider response., Normalise a provider tool-call response. Never raises. Accepts the shape…, parametrize, Dropping it silently would leave the model repeating the same broken call until…, A tool message whose tool_call_id matches nothing in the assistant turn is a…, Models often narrate before calling a tool. (+4 more)

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

### Community 97 - "get_settings"
Cohesion: 0.11
Nodes (19): PolicyDecision, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a…, The policy engine: evaluates a requested tool call, and never runs it. This is…, get_settings(), Singleton Settings object. (+11 more)

### Community 98 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "vision/tools.py"
Cohesion: 0.09
Nodes (33): get_profiler(), Opt-in per-stage timing for the vision pipeline. Vision is the one subsystem…, A profiler configured from the shared settings object. ``get_settings`` is…, Accumulated per-stage timings for one vision request. A plain name ->…, Times named stages when profiling is enabled, and is a no-op otherwise.…, Time the wrapped block. Used around an ``await`` -- ``with…, StageTimings, VisionProfiler (+25 more)

### Community 101 - "WindowService"
Cohesion: 0.17
Nodes (10): Human-readable condition, used when the caller did not supply one., Any, Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``., A full snapshot, which carries the bounds along with everything else., High-level window service. Backed by a :class:`WindowController`; holds no…, Full snapshot in one call. Uses the backend's ``describe`` when it has one --… (+2 more)

### Community 102 - "_build"
Cohesion: 0.19
Nodes (12): _ask(), _build(), _CountingExecutor, Any, asyncio, Parse and execute one raw CLI line, exactly as the input loop would., The real engine, recording every tool it was actually asked to run. ``asked``…, A command registry whose ``ask`` runs through a real agent core. (+4 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - "TestSerialization"
Cohesion: 0.14
Nodes (9): call(), failed_result(), ok_result(), _populated_state(), fixture, Tests for the agent execution state. The state layer has no interesting…, state(), TestDescribe (+1 more)

### Community 105 - "PyAutoGuiMouse"
Cohesion: 0.11
Nodes (3): PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 106 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 107 - "enums.py"
Cohesion: 0.07
Nodes (37): BaseSettings, Settings, Enumerations shared across the Trading Intelligence domain. Every enum inherits…, Qualitative risk level for a trade plan. Never a probability. UNKNOWN is first-…, Bump one level toward HIGH; UNKNOWN becomes MEDIUM, HIGH is capped., RiskBand, datetime, Provenance and data-quality value objects. Every important trading observation… (+29 more)

### Community 108 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 110 - "FakeHUDProcess"
Cohesion: 0.07
Nodes (18): bus(), fake_process(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything., The double's class, for tests that need a differently configured one. (+10 more)

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "HUDConfig"
Cohesion: 0.07
Nodes (21): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+13 more)

### Community 113 - "ToolRegistry"
Cohesion: 0.05
Nodes (68): Assemble a core from a provider and, optionally, its collaborators. The…, AgentStatus, Enum, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…, Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, boom() (+60 more)

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
Cohesion: 0.09
Nodes (29): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+21 more)

### Community 119 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.10
Nodes (18): add(), HookRecorder, make_reasoner(), Any, asyncio, fixture, The voice reasoner — the seam between a spoken turn and the LLM tool loop.…, Bootstrap registers an LLMEngine whose tool_provider is bound to the live… (+10 more)

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 122 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 123 - "make_vision_service"
Cohesion: 0.21
Nodes (15): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+7 more)

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.12
Nodes (8): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 125 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 126 - "bootstrapper.py"
Cohesion: 0.06
Nodes (44): Register the deterministic Trading Intelligence core. Self-contained: it…, Map ATR-as-fraction-of-price to a volatility band (deterministic)., Resolve a user/tool string to a Timeframe, raising ValueError if unknown., InvalidSymbolError, MarketDataError, A market-data operation could not be completed., The instrument symbol could not be resolved., AnalysisService (+36 more)

### Community 127 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "ObservationLog"
Cohesion: 0.15
Nodes (9): ObservationLog, Any, Observation, An append-only, ordered collection of :class:`Observation`., Append one observation, rejecting anything that is not one. The type guard is…, Every observation from one source, oldest first., The most recent observations, newest last. ``latest(1)`` is the freshest single…, test_log_rejects_non_observation_entry() (+1 more)

### Community 130 - "cli/main.py"
Cohesion: 0.05
Nodes (26): Agent policy layer. The gate that sits before tool execution. It answers one…, CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…, CommandParser, ParsedCommand (+18 more)

### Community 131 - "ServiceContainer"
Cohesion: 0.18
Nodes (6): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer

### Community 132 - "Renderer"
Cohesion: 0.15
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "Application"
Cohesion: 0.17
Nodes (8): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal()

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - ".assistant"
Cohesion: 0.15
Nodes (6): An assistant turn, optionally carrying the calls the model asked for.…, A long run must not produce an unbounded prompt., `[-0:]` is the whole list, so zero has to be handled explicitly., Nothing in the window announced this id, so the provider would reject it., The property that matters: a longer run is not a bigger prompt., TestSizeLimits

### Community 136 - "FakeOCRProvider"
Cohesion: 0.06
Nodes (20): Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), bgr_image(), fake_ocr(), FakeDetectionProvider, FakeOCRProvider, isolated_container(), make_unclosable_ocr() (+12 more)

### Community 137 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 138 - "MarketData"
Cohesion: 0.07
Nodes (22): SignalFn, BacktestResult, Any, datetime, Backtest value objects. A :class:`BacktestResult` is the deterministic product…, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome (+14 more)

### Community 140 - "voice/service.py"
Cohesion: 0.04
Nodes (49): Future, ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources. (+41 more)

### Community 141 - "PlanResult"
Cohesion: 0.08
Nodes (15): PlanResult, No next step exists. ``error_type`` names the kind of wall hit., What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only… (+7 more)

### Community 142 - "test_probability.py"
Cohesion: 0.25
Nodes (19): _learnable_closes(), asyncio, ndarray, _random_walk_closes(), ProbabilityService: deterministic, calibrated, look-ahead-safe probability.…, A bar's feature vector must not change when future bars are appended., Build a valid OHLCV series from a list/array of closes., A smooth multi-cycle series: recent momentum genuinely predicts the next few… (+11 more)

### Community 143 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 144 - "tools/registry.py"
Cohesion: 0.06
Nodes (35): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Exception, ToolError, is_unconstrained(), public_parameters(), Any, Signature (+27 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "ProbabilityService"
Cohesion: 0.16
Nodes (11): CalibrationMetrics, ProbabilityEstimate, Any, datetime, Probability-estimate value objects (spec sections 3, 6, 8).…, Out-of-sample calibration/accuracy measures over one evaluation slice., A calibrated directional probability with its full audit trail., _utcnow() (+3 more)

### Community 147 - "errors.py"
Cohesion: 0.06
Nodes (36): BollingerReading, MACDReading, Any, datetime, Technical-analysis value objects. TechnicalSnapshot holds the *latest* scalar…, _utcnow(), AnalysisError, BacktestError (+28 more)

### Community 148 - "PolicyEvaluation"
Cohesion: 0.16
Nodes (7): PolicyEvaluation, Any, The policy's answer to one request, as data. Returned rather than raised so a…, Any, Answer ALLOW / DENY / REQUIRE_CONFIRMATION for one call. First match wins, in…, Run global validators then the per-tool one; first objection wins. Returns…, Advisory per-call budget the evaluation reports. The engine holds no clock --…

### Community 150 - "ErrorContext"
Cohesion: 0.04
Nodes (52): Exception, BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,… (+44 more)

### Community 151 - "Instrument"
Cohesion: 0.06
Nodes (60): AsyncClient, Supported candle timeframes., Timeframe, Instrument, Any, Instrument identity. A tradable thing AetherOS can analyse. Symbol…, A tradable instrument (equity, crypto pair, index, ...)., Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``. Raises ValueError for an empty… (+52 more)

### Community 152 - "MarketStructureService"
Cohesion: 0.18
Nodes (12): MarketStructureService, ndarray, Swing/level/trend detection over a candle series., MarketStructureService: swings, levels, trend and structural signals., test_downtrend_detected(), test_insufficient_bars_raises(), test_levels_ranked_by_proximity(), test_pattern_flags_consistent() (+4 more)

### Community 153 - "test_orchestration.py"
Cohesion: 0.24
Nodes (12): Union every stage's limitations, de-duplicated and order-preserving. The…, _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_publishes_trading_report_generated(), test_report_has_full_section_27_shape(), test_report_is_deterministic(), test_report_is_no_trade_on_mock_data() (+4 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.23
Nodes (7): LogisticRegression, ndarray, Deterministic logistic regression in pure numpy. A small, fully reproducible…, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "VoiceConfig"
Cohesion: 0.05
Nodes (32): AudioCapture, AudioPlayer, Microphone capture with energy-based silence detection. PortAudio delivers…, Non-blocking playback of mono float32 PCM. Amplitude is measured inside the…, Abort playback immediately., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always…, Configuration for the AetherOS voice subsystem. Values may be supplied directly… (+24 more)

### Community 156 - "TestSerializationAndLogging"
Cohesion: 0.17
Nodes (5): IterationInfo, Where the run is in its budget. Carried explicitly because the model behaves…, One faithful view for auditing, one redacted view for the sinks., A snapshot that can be edited after assembly is not a snapshot., TestSerializationAndLogging

### Community 157 - "Direction"
Cohesion: 0.26
Nodes (24): Direction, Directional bias of a signal or piece of evidence., _levels(), _make_analysis(), _prov(), asyncio, parametrize, RiskService: deterministic risk geometry from a TradingAnalysis. Every number… (+16 more)

### Community 158 - "ScreenService"
Cohesion: 0.04
Nodes (40): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms., ABC, Any (+32 more)

### Community 159 - "MouseController"
Cohesion: 0.08
Nodes (11): MouseController, ABC, Drag to an absolute position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y), Move the mouse to an absolute screen position. Named ``x``/``y`` rather than… (+3 more)

### Community 160 - "._guard"
Cohesion: 0.19
Nodes (7): Path, Refuse to act on a process that must not be stopped. Returns the psutil handle…, Start a program and return its pid. ``env``, when given, *extends* the current…, Open a file with its registered application. Returns ``0``, which means "no pid…, Ask a process to exit. On Windows psutil's ``terminate`` maps to…, Stop a process immediately, with no opportunity to save. Use only after…, Stop a process and start its executable again, returning the new pid. The…

### Community 161 - "ToolExecutionCoordinator"
Cohesion: 0.13
Nodes (9): Runs one planned tool call through the engine and records what happened. Holds…, The policy gate consulted before delegation, or ``None`` when the coordinator…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, One round, several calls: all answered, in order, one at a time., What counts as a validated call, and what is a programming error. These raise…, TestCallShapes (+1 more)

### Community 162 - ".test_move_flows_through_the_full_chain_with_arguments"
Cohesion: 0.17
Nodes (13): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, Bind the ``MouseService`` the tools resolve to a recording controller. The real…, Copy one *production* tool definition into an isolated registry. (+5 more)

### Community 163 - "ExecutionConfig"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.14
Nodes (9): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, Score a detection ``label`` against a desired element ``target_type``., text_match_score(), _tokens(), type_match_score(), Unit tests for the deterministic match scoring. The scale is graded on purpose…, TestTextMatchScore (+1 more)

### Community 167 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 171 - "NullTTS"
Cohesion: 0.17
Nodes (3): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…

### Community 172 - "_feature_columns"
Cohesion: 0.27
Nodes (9): build_features(), _feature_columns(), FeatureMatrix, _momentum(), ndarray, Causal feature construction for probability estimation. Turns an OHLCV series…, close[t]/close[t-period] - 1, NaN for the first ``period`` positions., Stack the causal feature columns into an (n, n_features) matrix. (+1 more)

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - ".record"
Cohesion: 0.12
Nodes (15): LevelCallback, _normalize_level(), Any, ndarray, Captured microphone audio., Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is… (+7 more)

### Community 176 - "ToolExecutionResult"
Cohesion: 0.13
Nodes (10): Record the outcome, tolerating a run that ended underneath it. The only way…, File a failure in the run's error ledger. Field by field rather than by handing…, What came back from one tool call. A failed tool is data, not an exception: the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, Every result recorded against one call id., _render(), ToolResultRecord, Outcome of a single tool execution. Carries failures as data rather than as… (+2 more)

### Community 177 - "Any"
Cohesion: 0.22
Nodes (5): Any, Returns process information. Example: name pid cpu_percent memory_usage…, Returns all running processes., Find a process by PID., Find processes by executable name.

### Community 178 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "emit_trace"
Cohesion: 0.07
Nodes (29): Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, Run ``goal`` on the shared agent, labelling the turn with ``source``.…, emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.… (+21 more)

### Community 181 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 182 - "test_trading_tools.py"
Cohesion: 0.18
Nodes (18): asyncio, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_instrument_tool_is_labelled_mock(), test_analyze_market_structure_tool(), test_assess_risk_tool_is_labelled_mock(), test_assess_risk_tool_position_sizing(), test_assess_risk_tool_rejects_bad_direction(), test_backtest_signal_tool_is_never_reliable_on_mock() (+10 more)

### Community 183 - ".test_speech_moves_the_mouse_through_the_agent"
Cohesion: 0.28
Nodes (5): _agent_reasoner(), _CountingExecutor, Any, Wrap a real ``AgentCore`` in the production ``AgentReasoner`` adapter., The real executor, recording every tool it was actually asked to run. A name…

### Community 185 - "._format_tool_signature"
Cohesion: 0.29
Nodes (3): Render one tool as ``name(arg: type, arg: type = default)``. Names, types, and…, A readable type name for a resolved annotation, or "" when there is no usable…, Render a parameter's default value for display.

### Community 186 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 187 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 188 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 189 - "RecordingTTS"
Cohesion: 0.09
Nodes (15): EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, Records what would have been spoken. The test double for speech output: it…, RecordingTTS, _BlockingReasoner, _FailingTTS, _pipeline() (+7 more)

### Community 190 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 191 - "_RecordingMouse"
Cohesion: 0.11
Nodes (4): _fake_mouse(), Bind the ``MouseService`` the tool resolves to a recording controller.…, A ``MouseController`` sitting where PyAutoGUI would. Records every absolute…, _RecordingMouse

### Community 192 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 193 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 194 - "test_vision_engine.py"
Cohesion: 0.11
Nodes (10): asyncio, skipif, Tests for the Vision Engine. Run with: pytest tests/vision/, test_opencv_provider_metadata(), test_paddleocr_provider_metadata(), test_yolo_provider_metadata(), TestDetection, TestTemplateMatching (+2 more)

### Community 205 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 206 - "TextToSpeech"
Cohesion: 0.05
Nodes (42): AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed., Base exception for all voice-subsystem errors. Examples: - Microphone…, The wake-word engine failed to initialize or detect. (+34 more)

### Community 207 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 208 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 209 - ".hud"
Cohesion: 0.20
Nodes (3): The running HUD service, or None when the overlay is not up., The running voice service, or None when voice is not up., The live execution-trace recorder, or None when tracing is off.

### Community 210 - "ExecutionStatus"
Cohesion: 0.22
Nodes (6): ExecutionStatus, Enum, str, How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 211 - ".open_file"
Cohesion: 0.40
Nodes (3): Path, Start a new process. Returns: Process ID (PID), Open a file with its default application. Returns: Process ID if available.

### Community 212 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 213 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 214 - "TestToolsCommand"
Cohesion: 0.13
Nodes (4): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., The list is read live from the registry, so a tool registered after the command…, TestToolsCommand

### Community 215 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 216 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 217 - "MSSScreen"
Cohesion: 0.05
Nodes (32): MSSScreen, ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Capture a specific monitor (1 = primary). (+24 more)

### Community 219 - "WindowBounds"
Cohesion: 0.22
Nodes (4): A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 223 - "_one"
Cohesion: 0.08
Nodes (15): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+7 more)

### Community 226 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 228 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 230 - "test_ui.py"
Cohesion: 0.11
Nodes (13): cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, ``errors="replace"`` is the second half of the fix. Without it a single…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, The regression itself: this raised UnicodeEncodeError from _show_logo. (+5 more)

### Community 233 - "test_input.py"
Cohesion: 0.24
Nodes (9): keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every…, _swapped() (+1 more)

### Community 238 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 240 - "._ask"
Cohesion: 0.33
Nodes (3): Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal.

### Community 242 - "workflow_believer_run.py"
Cohesion: 0.38
Nodes (6): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows.

### Community 246 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2568 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `cli/main.py`, `automation/engine.py`, `Application`, `WakeWordActivator`, `voice/service.py`, `policy.py`, `VerificationResult`, `PaddleOCRProvider`, `tools/registry.py`, `errors.py`, `Application`, `ErrorContext`, `Bootstrapper`, `VoiceConfig`, `CommandRegistry`, `MouseController`, `ScreenService`, `PolicyEngine`, `HUDProcess`, `ExecutionConfig`, `LLMEngine`, `SourceTier`, `NullTTS`, `AgentCore`, `ProcessController`, `tool`, `WindowController`, `ProcessService`, `TraceEvent`, `KeyboardService`, `YOLOProvider`, `DesktopError`, `BrowserProvider`, `LifecycleManager`, `get_settings`, `RecoveryRunner`, `vision/tools.py`, `ClipboardController`, `enums.py`, `FasterWhisperSTT`, `HUDConfig`, `VoiceState`, `Agent`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `cli/main.py`, `ToolExecutor`, `automation/engine.py`, `define`, `.assistant`, `PlannerConfig`, `AutomationEngine`, `voice/service.py`, `test_agent_planner.py`, `tools/registry.py`, `AgentPlanner`, `_state`, `TestSerializationAndLogging`, `ToolExecutionCoordinator`, `PolicyEngine`, `ExecutionConfig`, `.test_move_flows_through_the_full_chain_with_arguments`, `LLMEngine`, `get_logger`, `Any`, `TestFinalResponse`, `AgentCore`, `.test_speech_moves_the_mouse_through_the_agent`, `ContextBuilder`, `ContextConfig`, `FakeLLMProvider`, `test_agent_context.py`, `ExecutionStatus`, `RecoveryRunner`, `_build`, `test_agent_execution.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Image` connect `Image` to `VisionError`, `FakeOCRProvider`, `VerificationResult`, `PaddleOCRProvider`, `asyncio`, `asyncio`, `ErrorContext`, `ScreenService`, `TextBlock`, `Detection`, `wire`, `FrameCache`, `vision/main.py`, `test_vision_engine.py`, `asyncio`, `YOLOProvider`, `MSSScreen`, `get_settings`, `vision/tools.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `get_logger()` (e.g. with `.__init__()` and `__init__()`) actually correct?**
  _`get_logger()` has 20 INFERRED edges - model-reasoned connections that need verification._