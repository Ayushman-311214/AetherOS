# Graph Report - AetherOS  (2026-09-30)

## Corpus Check
- 401 files · ~326,853 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 8089 nodes · 20939 edges · 287 communities (243 shown, 31 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 2606 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ddd675e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolExecutionCoordinator
- Image
- answer
- define
- test_backtest.py
- agents/__init__.py
- ContextBuilder
- TextBlock
- Scene
- WindowController
- AutomationEngine
- AgentState
- MarketData
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- voice_error.py
- HUDService
- test_agent_planner.py
- test_tool_schema.py
- Message
- vision/main.py
- PlannedAction
- Event
- EventBus
- trading/tools.py
- ToolExecutionResult
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- PredictionOutcome
- ._touch
- PolicyEngine
- VoiceService
- asyncio
- safe_preview
- LLMEngine
- ProcessController
- TradingAnalysis
- Direction
- HUDWindow
- ApplicationService
- agents/state.py
- test_news.py
- FileController
- asyncio
- Instrument
- PlanResult
- CLIUI
- Win32Window
- wire
- test_unified_interaction.py
- get_settings
- MouseService
- indicators/core.py
- _RecordingProvider
- .create
- FrameCache
- test_grounding_tools.py
- LLMToolLoop
- instrument.py
- make_vision_service
- test_fundamentals.py
- PlaywrightProvider
- VoiceConfig
- Provenance
- test_agent_policy.py
- ClipboardService
- LiveTraceUI
- VisionProvider
- bootstrapper.py
- FakeLLMProvider
- asyncio
- test_yahoo_calendar_provider.py
- application/tools.py
- LLMProvider
- MemoryProvider
- calibration.py
- ProcessService
- asyncio
- test_prediction_evaluator.py
- PathGuard
- KeyboardService
- WindowInfo
- make_market_data
- YOLOProvider
- OpenCVProvider
- BrowserProvider
- parse_target
- LifecycleManager
- _RecordingMouse
- StageTimings
- RecoveryOutcome
- TestRegistration
- PredictionRecord
- BrowserService
- agent_loop.py
- ContextBuilder
- asyncio
- TestFinalResponse
- FakeOCRProvider
- make_service
- ClipboardController
- parse_llm_response
- PyAutoGuiMouse
- TaskManager
- ScreenService
- test_probability.py
- PyAutoGuiKeyboard
- HookRecorder
- window/tools.py
- HUDConfig
- _CountingExecutor
- VoiceState
- VoicePipeline
- commands
- InMemoryPredictionStore
- test_agent_execution.py
- ServiceContainer
- RenderContext
- automation/engine.py
- BacktestResult
- tool
- Path
- process/tools.py
- PredictionStore
- ExecutionBatch
- _settings
- MarketRegime
- ToolCommandService
- emit_trace
- Renderer
- GlowCache
- test_interface_contracts.py
- test_orchestration.py
- test_agent_observation.py
- .test_the_registered_engine_is_preferred
- FakeKeyboard
- _one
- TerminalService
- vision/tools.py
- FakeMouse
- VisionError
- agents/core.py
- screen/tools.py
- FakeHUDProcess
- _FakeMouse
- test_cli_agent.py
- TestToolsCommand
- HUDSnapshot
- test_input.py
- hud/__init__.py
- verification/tools.py
- LogisticRegression
- reasoner.py
- ContextConfig
- asyncio
- ScreenController
- MouseController
- TestSerialization
- workflow_believer_run.py
- AgentError
- .from_events
- _service
- text_match_score
- main
- test_indicators.py
- Agent
- WindowService
- TestCallIdentifiers
- import_all.py
- TTLCache
- test_yahoo_news_provider.py
- ToolRegistry
- TestEveryRegisteredToolHasAUsableSchema
- _make_analysis
- _settings
- AgentLoopResult
- ToolDiscovery
- test_trading_tools.py
- SpeechToText
- .to_dict
- .test_is_open_reports_state_without_touching_the_backend
- ToolCall
- PipeReader
- Box
- ExecutionStatus
- SapiTTS
- _RecordingMouse
- _started
- OpenAICompatibleProvider
- OpenCVTemplateProvider
- AetherOS
- rich_tools
- Layer
- get_logger
- FakeSCT
- AgentCore
- VisionService
- voice/service.py
- cli/main.py
- LLMProviderManager
- ._format_trading_report
- TestEveryToolModuleImports
- HUDProcess
- MSSScreen
- ToolError
- test_yahoo_fundamentals_provider.py
- renderer.py
- AgentStatus
- TraceEvent
- RecordingTTS
- ErrorContext
- MarketStructureService
- Application
- spatial.py
- enums.py
- qcolor
- TestSerializationAndLogging
- WatchlistScanService
- LLMConfig
- TechnicalAnalysisService
- TestRegisteredToolSurface
- .generate
- test_ui.py
- PyAutoGuiClipboard
- TestPromptCursor
- .from_dict
- features.py
- scan.py
- make_fake_detector
- parametrize
- ._ask
- WindowBounds
- TestProviderCompatibility
- test_agent_e2e.py
- AnomalyService
- _win32_clipboard
- TraceCollector
- .record
- .copy_files
- .copy_image
- automation/tools.py
- .save
- .test_speech_moves_the_mouse_through_the_agent
- main
- .download
- PulseLayer
- TickLayer
- .shutdown
- .hud
- TestMultipleIterations
- TestInvalidArguments
- TestToolFailure
- TestMSSSave
- TestFailureHandling
- .evaluate
- ._nearest
- .grab
- ._format_scan
- coord.py
- run_workflow_from_file.py
- ._live_context
- .speak
- bootstrapper
- executor
- .trace
- .voice
- .has_text
- .drag_relative
- .pid
- .key
- .__init__

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 242 edges
2. `Direction` - 222 edges
3. `Image` - 183 edges
4. `Instrument` - 166 edges
5. `AgentState` - 138 edges
6. `tool()` - 134 edges
7. `get_logger()` - 114 edges
8. `define()` - 106 edges
9. `EventBus` - 103 edges
10. `AgentPlanner` - 102 edges

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

## Communities (287 total, 31 thin omitted)

### Community 0 - "ToolExecutionCoordinator"
Cohesion: 0.11
Nodes (12): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, A name the registry has never heard of is refused before delegation., Once a run has ended, nothing executes and nothing is written. (+4 more)

### Community 1 - "Image"
Cohesion: 0.04
Nodes (24): ColorSpace, Image, ndarray, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV…, Universal image model for AetherOS. Every vision module should consume and… (+16 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (50): Executes registered AetherOS tools., The registry this executor validates and runs tools from., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes() (+42 more)

### Community 4 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 5 - "agents/__init__.py"
Cohesion: 0.10
Nodes (15): Agent layer. Four pieces so far. :mod:`~aetheros.agents.state` is the explicit,…, ActionType, Enum, str, Planner actions and results. The value types the planner returns. They exist so…, What the planner decided. ``str``-valued so a serialized action reads as…, Goal, Represents the user's objective. (+7 more)

### Community 6 - "ContextBuilder"
Cohesion: 0.05
Nodes (30): _clamp(), ContextBuilder, _describe_call(), _describe_result(), Any, Observation, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts. (+22 more)

### Community 7 - "TextBlock"
Cohesion: 0.03
Nodes (41): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+33 more)

### Community 8 - "Scene"
Cohesion: 0.05
Nodes (18): Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:…, The interpolated style for this frame., Smoothed audio level, 0..1., Slowly decaying peak, used for the outer bloom., The particles this frame should draw. Intensity and quality both trim from the…, Amplitude history ordered so index 0 is the oldest bin. (+10 more)

### Community 9 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.07
Nodes (39): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, RecoveryRunner, Build a workflow from a plain dict, as ``run_workflow`` receives it., Calls, engine() (+31 more)

### Community 11 - "AgentState"
Cohesion: 0.05
Nodes (12): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,…, asyncio, parametrize, TestCompletion, TestErrors (+4 more)

### Community 12 - "MarketData"
Cohesion: 0.02
Nodes (86): AnomalyAnalysis, Any, datetime, Statistical-anomaly value object. An :class:`AnomalyAnalysis` is the…, Deterministic last-bar statistical-outlier read for one instrument., Whether this read rests on data solid enough to lean on. Mock or unusable data,…, _utcnow(), Assertion (+78 more)

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (59): Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, Outcome of one desktop action, as the model sees it. Distinct from… (+51 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.04
Nodes (36): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+28 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.09
Nodes (18): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not., One well-formed call for a known tool is planned, not executed., A provider that supports parallel calls gets one action per call. (+10 more)

### Community 16 - "voice_error.py"
Cohesion: 0.07
Nodes (30): AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed., Base exception for all voice-subsystem errors. Examples: - Microphone… (+22 more)

### Community 17 - "HUDService"
Cohesion: 0.06
Nodes (24): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+16 more)

### Community 18 - "test_agent_planner.py"
Cohesion: 0.08
Nodes (32): builder(), context(), _FailingProvider, move_mouse(), planner(), provider(), Any, asyncio (+24 more)

### Community 19 - "test_tool_schema.py"
Cohesion: 0.06
Nodes (31): NotAnImportableType, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse(), optionals(), Any (+23 more)

### Community 20 - "Message"
Cohesion: 0.08
Nodes (39): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), main(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the… (+31 more)

### Community 21 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 22 - "PlannedAction"
Cohesion: 0.05
Nodes (22): PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because… (+14 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (68): Event, Base class for all events in AetherOS. Every event inherits from this class., Returns the event class name., Decorator used to register an event handler. Example:…, subscribe(), LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM. (+60 more)

### Community 24 - "EventBus"
Cohesion: 0.07
Nodes (20): EventHandler, Any, Consume one trace event. Sync, on the publish path, never raises. Kept…, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard. (+12 more)

### Community 25 - "trading/tools.py"
Cohesion: 0.09
Nodes (48): _analysis(), analyze_fundamentals(), analyze_instrument(), analyze_macro_context(), analyze_market_structure(), analyze_news_sentiment(), analyze_relative_strength(), _anomaly() (+40 more)

### Community 26 - "ToolExecutionResult"
Cohesion: 0.07
Nodes (21): AgentExecutionResult, _failure(), A failure in the engine's own currency, for a call the engine never saw.…, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Run one validated call and record the round it produced. Accepts either shape a…, Record a call that was turned away, without the engine being asked. The refusal… (+13 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.09
Nodes (6): Bootstrapper, Whether Playwright can be imported. find_spec rather than a try/import:…, Coordinates application startup and shutdown. The bootstrapper is responsible…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Shutdown subsystems in reverse order.

### Community 28 - "DesktopError"
Cohesion: 0.09
Nodes (23): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, PsutilProcess, Any, Path, psutil process backend. Two safety rules are enforced here, in the backend,…, Fetch a psutil handle, translating its errors into DesktopError. psutil's… (+15 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.13
Nodes (4): Any, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.08
Nodes (10): CommandHandler, CommandRegistry, Execute a parsed command., Registry for AetherOS CLI commands., Render one tool as ``name(arg: type, arg: type = default)``. Names, types, and…, A readable type name for a resolved annotation, or "" when there is no usable…, Render a parameter's default value for display., Show LLM provider status and model information. (+2 more)

### Community 31 - "PredictionOutcome"
Cohesion: 0.10
Nodes (14): PredictionOutcome, Any, The auditable result of checking one prediction against later market data., A resolved, directional outcome that was actually graded hit/miss., PredictionError, An auditable prediction record could not be built, stored, or read back., _ensure_utc(), PredictionEvaluator (+6 more)

### Community 32 - "._touch"
Cohesion: 0.11
Nodes (13): ErrorRecord, BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Finish the run unsuccessfully, recording the unrecoverable error., Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would… (+5 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.05
Nodes (29): PolicyConfig, Any, Policy configuration: the rules the engine evaluates against. Deliberately…, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyDecision, PolicyEvaluation, Any (+21 more)

### Community 34 - "VoiceService"
Cohesion: 0.06
Nodes (24): AudioCapture, Microphone capture with energy-based silence detection. PortAudio delivers…, Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Any, A flat snapshot for the CLI., Bring the voice subsystem up. (+16 more)

### Community 35 - "asyncio"
Cohesion: 0.09
Nodes (17): asyncio, _raising_start(), `publisher.publish()` is how code fires an event without holding a bus., Dropping the reference is not enough: the HUD registers bound methods, so a…, A headless or server install must not try to open a window., Nothing should grab the microphone or install a global hotkey hook unless it…, The common case: `aether` on a machine with both flags unset., The gate is the caller's, not HUDService's — the service stays usable from a… (+9 more)

### Community 36 - "safe_preview"
Cohesion: 0.10
Nodes (15): Any, Log-safe projections for trace payloads. The trace persists to disk and renders…, Redact forbidden keys without shortening the surviving values. For the…, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, redact_keys(), safe_metadata() (+7 more)

### Community 37 - "LLMEngine"
Cohesion: 0.11
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 38 - "ProcessController"
Cohesion: 0.07
Nodes (18): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+10 more)

### Community 39 - "TradingAnalysis"
Cohesion: 0.05
Nodes (34): Any, Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, CriticCheck, CriticReport, Any, datetime (+26 more)

### Community 40 - "Direction"
Cohesion: 0.16
Nodes (89): CheckStatus, CriticVerdict, Direction, Outcome of one critic check. SKIPPED is first-class: a check the current build…, The critic's go/no-go decision on a proposed signal. INSUFFICIENT_EVIDENCE is…, Directional bias of a signal or piece of evidence., _analysis(), _anomaly() (+81 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (18): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+10 more)

### Community 42 - "ApplicationService"
Cohesion: 0.10
Nodes (24): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+16 more)

### Community 43 - "agents/state.py"
Cohesion: 0.08
Nodes (18): Record the outcome, tolerating a run that ended underneath it. The only way…, new_state_id(), Any, Enum, Agent execution state. One :class:`AgentState` is the complete, explicit record…, Fail on fields we do not recognise instead of dropping them. Ignoring an…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly. (+10 more)

### Community 44 - "test_news.py"
Cohesion: 0.04
Nodes (63): NewsAnalysis, NewsItem, Any, datetime, News & sentiment value objects (spec sections 5, 9, 26 item #9). The…, Aggregate news sentiment for an instrument, with its full audit trail., Content-addressed id: same headline from the same source -> same id.…, A single sourced headline as a provider returned it (no interpretation). (+55 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "asyncio"
Cohesion: 0.09
Nodes (22): An assistant turn, optionally carrying the calls the model asked for.…, _call(), asyncio, Tests for the agent context layer. The properties under test are the ones the…, A plain back-and-forth reaches the provider unchanged., Tool rounds keep the shape the provider layer already accepts., A tool message whose assistant turn was trimmed fails the request. The provider…, The digest must stay safe to log; the history carries the values. (+14 more)

### Community 47 - "Instrument"
Cohesion: 0.05
Nodes (81): Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, EventCalendar, EventImpact, EventType, MarketEvent, Any, datetime (+73 more)

### Community 48 - "PlanResult"
Cohesion: 0.08
Nodes (16): PlanResult, What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Faithful, and therefore not safe for the log sinks., Log-safe: what was decided, not what was said., Any, Exception (+8 more)

### Community 49 - "CLIUI"
Cohesion: 0.11
Nodes (9): Panel, CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen. (+1 more)

### Community 50 - "Win32Window"
Cohesion: 0.11
Nodes (17): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+9 more)

### Community 51 - "wire"
Cohesion: 0.09
Nodes (20): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., ultralytics and its weights are optional, so the agent has to be told the… (+12 more)

### Community 52 - "test_unified_interaction.py"
Cohesion: 0.11
Nodes (25): InteractionGateway, The one entry a front end submits a turn through. Both the terminal and voice…, Submit a goal to the shared agent, tagged with its front end., new_session_id(), A fresh per-session id for a front end that owns one gateway., _boom(), _build_agent(), _CountingExecutor (+17 more)

### Community 53 - "get_settings"
Cohesion: 0.11
Nodes (23): get_settings(), Singleton Settings object., Attempts to make, resolved against configuration and clamped., Safety — the gates every destructive desktop action passes through. Two…, PathVerdict, Path validation for the filesystem and application tools. A model that can…, The outcome of validating one path against one intended access. Returned rather…, Capability (+15 more)

### Community 54 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

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
Cohesion: 0.14
Nodes (14): _block(), executor(), asyncio, fixture, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received…, Register the services the grounding tools resolve, with fake edges. Mirrors… (+6 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.10
Nodes (18): LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text. (+10 more)

### Community 61 - "instrument.py"
Cohesion: 0.03
Nodes (82): datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, _utcnow(), VolumeAnalysis, Supported candle timeframes., StructureSignalType, Timeframe, TrendState (+74 more)

### Community 62 - "make_vision_service"
Cohesion: 0.21
Nodes (15): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+7 more)

### Community 63 - "test_fundamentals.py"
Cohesion: 0.24
Nodes (22): FakeFundamentalsProvider, asyncio, Deterministic fundamental-analysis tests (spec sections 5, 9, 21, 28). Two…, A controllable, clearly-synthetic snapshot stamped a non-mock tier., Hands back exactly the snapshot the test built; non-mock so it can be reliable., _service(), _snapshot(), test_mock_provider_is_deterministic() (+14 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 65 - "VoiceConfig"
Cohesion: 0.05
Nodes (27): ABC, WakeCallback, Abstract activation source for the voice pipeline. An activator decides *when*…, Activator name, e.g. "push-to-talk"., Whether the activator is currently armed., Arm the activator. `on_activate` may be invoked from a foreign thread, so…, Disarm the activator and release any OS hooks., VoiceActivator (+19 more)

### Community 66 - "Provenance"
Cohesion: 0.04
Nodes (50): FundamentalAnalysis, FundamentalFactor, FundamentalSnapshot, Any, datetime, Fundamental-analysis value objects (spec sections 5, 9, 26). The fundamentals…, Names of the metrics that were actually reported (non-None)., One deterministic signed read the scorer derived from a single metric.… (+42 more)

### Community 67 - "test_agent_policy.py"
Cohesion: 0.15
Nodes (21): _call(), _coordinator(), _CountingExecutor, executor(), move_mouse(), Any, asyncio, fixture (+13 more)

### Community 68 - "ClipboardService"
Cohesion: 0.09
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "bootstrapper.py"
Cohesion: 0.07
Nodes (39): Register the deterministic Trading Intelligence core. Self-contained: it…, MockFundamentalsProvider, A reproducible, clearly-labelled synthetic fundamentals source., AnalysisService, Deterministic end-to-end analysis for one instrument., BacktestService, Largest peak-to-trough drop on the additive equity curve (>= 0)., Per-trade mean/std ratio. Not annualised; None when undefined. (+31 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.05
Nodes (25): Whether the far end has gone away., make_unclosable_ocr(), Raises from ``close()``. Shutdown must survive a provider that cannot release…, UnclosableOCRProvider, asyncio, parametrize, Path, skipif (+17 more)

### Community 74 - "test_yahoo_calendar_provider.py"
Cohesion: 0.17
Nodes (25): AsyncClient, datetime, Extract unix-timestamp dates from a calendarEvents field. Yahoo carries a date…, Real scheduled corporate events from Yahoo's public quoteSummary endpoint., YahooCalendarProvider, _calendar_payload(), _ok_handler(), _provider() (+17 more)

### Community 75 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 76 - "LLMProvider"
Cohesion: 0.13
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "calibration.py"
Cohesion: 0.11
Nodes (23): datetime, Aggregate prediction-performance value object (spec sections 6, 9, 28, 29).…, _utcnow(), accuracy(), brier_score(), CalibrationReport, _clip01(), expected_calibration_error() (+15 more)

### Community 79 - "ProcessService"
Cohesion: 0.12
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.10
Nodes (9): asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing (+1 more)

### Community 81 - "test_prediction_evaluator.py"
Cohesion: 0.12
Nodes (49): PredictionOutcomeStatus, The state of a past prediction checked against what actually happened.…, _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes. (+41 more)

### Community 82 - "PathGuard"
Cohesion: 0.13
Nodes (18): PathLike, PathAccess, PathGuard, Enum, Path, str, Validates filesystem paths before any tool acts on them. Reads its rules from…, Normalise a caller-supplied path without requiring it to exist. ``expanduser``… (+10 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowInfo"
Cohesion: 0.10
Nodes (14): Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Poll until a matching window appears, or the timeout expires. Polling rather…, Poll until a matching window holds focus, or the timeout expires. Distinct from…, Poll ``probe`` until it returns a window, bounded by ``timeout``. The bound is…, Synchronous selector matching, for use inside poll probes. (+6 more)

### Community 85 - "make_market_data"
Cohesion: 0.05
Nodes (79): MarketPosture, The broad-market risk posture, derived from a market benchmark's own regime.…, The directional bias implied by the posture -- never a probability., Map a benchmark's regime to a broad-market risk posture. A trending-up market…, Resolve a user/tool string to a Timeframe, raising ValueError if unknown., MarketDataError, A market-data operation could not be completed., downtrend_data() (+71 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (15): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Make torch.cuda.is_available() report a chosen value. (+7 more)

### Community 87 - "OpenCVProvider"
Cohesion: 0.10
Nodes (11): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, parametrize, A fixed COLOR_BGR2GRAY would weight red and blue the wrong way round for RGB… (+3 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.05
Nodes (18): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page title., Return the current page URL. (+10 more)

### Community 89 - "parse_target"
Cohesion: 0.12
Nodes (14): _clean(), _find_element_type(), _find_ordinal(), _find_relation(), parse_target(), Parse a natural-language target into a :class:`GroundingTarget`. Deterministic,…, Return the canonical element type mentioned, longest phrase first., Parse ``query`` into a structured :class:`GroundingTarget`. The residual text… (+6 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 92 - "StageTimings"
Cohesion: 0.12
Nodes (11): Opt-in per-stage timing for the vision pipeline. Vision is the one subsystem…, Accumulated per-stage timings for one vision request. A plain name ->…, Times named stages when profiling is enabled, and is a no-op otherwise.…, Time the wrapped block. Used around an ``await`` -- ``with…, StageTimings, VisionProfiler, Tests for the opt-in vision profiler. The contract these pin, from §11 of the…, TestDisabledProfilerIsANoop (+3 more)

### Community 93 - "RecoveryOutcome"
Cohesion: 0.14
Nodes (8): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design…, RecoveryOutcome, RecoveryStrategy

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "PredictionRecord"
Cohesion: 0.08
Nodes (37): PredictionRecord, Any, datetime, A prediction resting on mock data can never be treated as reliable., Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, Content-addressed id for one prediction (spec section 8). Keyed on the full…, The auditable section-8 contract for one produced trading report. (+29 more)

### Community 96 - "BrowserService"
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "agent_loop.py"
Cohesion: 0.15
Nodes (17): The LLM ↔ tool execution loop. One run is a bounded conversation: the model is…, Record of one tool the loop attempted during a run., ToolInvocation, MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is… (+9 more)

### Community 98 - "ContextBuilder"
Cohesion: 0.16
Nodes (13): Any, ContextBuilder, A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools. (+5 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 101 - "FakeOCRProvider"
Cohesion: 0.07
Nodes (22): Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), bgr_image(), fake_ocr(), FakeOCRProvider, FakeScreen, isolated_container(), Any (+14 more)

### Community 102 - "make_service"
Cohesion: 0.13
Nodes (15): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+7 more)

### Community 103 - "ClipboardController"
Cohesion: 0.12
Nodes (9): ClipboardController, ABC, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"…, Copy text to the clipboard., Returns clipboard text. (+1 more)

### Community 104 - "parse_llm_response"
Cohesion: 0.12
Nodes (11): parse_llm_response(), ParsedResponse, Normalised view of one provider response., Normalise a provider tool-call response. Never raises. Accepts the shape…, parametrize, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn. (+3 more)

### Community 105 - "PyAutoGuiMouse"
Cohesion: 0.11
Nodes (3): PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 106 - "TaskManager"
Cohesion: 0.06
Nodes (37): Any, TaskContext, InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError (+29 more)

### Community 107 - "ScreenService"
Cohesion: 0.19
Nodes (10): Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, ScreenService, make_fake_screen(), asyncio, A capture failure must surface, not be turned into an empty frame that OCR… (+2 more)

### Community 108 - "test_probability.py"
Cohesion: 0.25
Nodes (19): _learnable_closes(), asyncio, ndarray, _random_walk_closes(), ProbabilityService: deterministic, calibrated, look-ahead-safe probability.…, A bar's feature vector must not change when future bars are appended., Build a valid OHLCV series from a list/array of closes., A smooth multi-cycle series: recent momentum genuinely predicts the next few… (+11 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 110 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "HUDConfig"
Cohesion: 0.07
Nodes (21): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+13 more)

### Community 113 - "_CountingExecutor"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, _CountingExecutor, Defaults, and the invariant the class docstring states., The real engine, counting how often it was asked. A subclass rather than a…, TestConstruction

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 115 - "VoicePipeline"
Cohesion: 0.10
Nodes (15): Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE., Run one turn under a timeout, mapping failures onto ERROR., Outcome of one voice interaction. (+7 more)

### Community 116 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 117 - "InMemoryPredictionStore"
Cohesion: 0.29
Nodes (19): InMemoryPredictionStore, Process-local reference store. Deterministic, dependency-free, non-durable.…, _FakeEvaluator, asyncio, The prediction track-record service: the on-demand composition of the audit…, A minimal, hand-built recorded prediction with a fixed content id., A RESOLVED, optionally-graded outcome for the fake evaluator to hand back., Returns a pre-baked outcome per record id; raises for flagged ids. (+11 more)

### Community 118 - "test_agent_execution.py"
Cohesion: 0.10
Nodes (27): add_async(), coordinator(), executor(), explodes(), journal(), _journalled(), move_mouse(), Any (+19 more)

### Community 119 - "ServiceContainer"
Cohesion: 0.07
Nodes (18): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, AgentReasoner, LLMLoopReasoner (+10 more)

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "automation/engine.py"
Cohesion: 0.06
Nodes (42): _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Run a step's read-back, polling when it declared a timeout. Returns ``None``… (+34 more)

### Community 122 - "BacktestResult"
Cohesion: 0.11
Nodes (12): SignalFn, BacktestResult, Any, datetime, Backtest value objects. A :class:`BacktestResult` is the deterministic product…, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome (+4 more)

### Community 123 - "tool"
Cohesion: 0.15
Nodes (29): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+21 more)

### Community 125 - "process/tools.py"
Cohesion: 0.21
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 126 - "PredictionStore"
Cohesion: 0.07
Nodes (23): datetime, Prediction-outcome value object (spec sections 6, 15, 16, 29). A…, _utcnow(), PredictionPerformance, Any, An auditable aggregate of many resolved predictions' outcomes., Whether any calibrated-probability predictions were available to grade., PredictionPerformanceService (+15 more)

### Community 127 - "ExecutionBatch"
Cohesion: 0.07
Nodes (14): ExecutionBatch, Any, Faithful, and therefore not safe for the log sinks. Holds the argument values…, Log-safe: names, outcomes and timings, never values. ``error`` is included…, Every outcome from one round of tool calls, in the order they ran. Exists for…, Everything that did not succeed, refusals included., The calls this layer turned away before the engine was asked., True for an empty batch: nothing was asked, so nothing went wrong. (+6 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "MarketRegime"
Cohesion: 0.15
Nodes (22): MarketRegime, The prevailing *character* of the market, classified deterministically from…, The directional bias implied by the regime -- never a probability., datetime, Market-regime value object. A ``RegimeAnalysis`` is the deterministic read of…, _utcnow(), _FakeBus, asyncio (+14 more)

### Community 130 - "ToolCommandService"
Cohesion: 0.11
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "emit_trace"
Cohesion: 0.06
Nodes (37): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), TraceSpan (+29 more)

### Community 132 - "Renderer"
Cohesion: 0.15
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 133 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "test_orchestration.py"
Cohesion: 0.18
Nodes (29): The final desk-level recommendation on a composed trading report. A…, ReportRecommendation, _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_report_fuses_anomaly_as_advisory_but_stays_no_trade(), test_report_fuses_calendar_as_advisory_but_stays_no_trade(), test_report_fuses_fundamentals_as_advisory_but_stays_no_trade() (+21 more)

### Community 136 - "test_agent_observation.py"
Cohesion: 0.05
Nodes (50): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``…, Observe browser state. The seam the task asks for: there is no browser-state… (+42 more)

### Community 137 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 138 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 139 - "_one"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 140 - "TerminalService"
Cohesion: 0.14
Nodes (15): Process, _clip(), CommandResult, _decode(), Path, Command execution. Three decisions in here are load-bearing. **A non-zero exit…, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment… (+7 more)

### Community 141 - "vision/tools.py"
Cohesion: 0.16
Nodes (30): get_frame_cache(), Process-wide frame cache, sized from the shared settings object. Built once…, click_grounded_target(), _engine(), ground_target(), Any, Grounding tools: the agent-facing surface of the grounding layer. These are the…, type_into_grounded_target() (+22 more)

### Community 143 - "VisionError"
Cohesion: 0.11
Nodes (13): Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary)., Grab a region and drop the alpha channel. mss hands back BGRA; slicing to three… (+5 more)

### Community 144 - "agents/core.py"
Cohesion: 0.05
Nodes (44): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Agent context assembly. One :class:`AgentContext` is everything the model needs…, The agent core loop: the driver that turns a goal into a finished run. This is…, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, Agent policy layer. The gate that sits before tool execution. It answers one…, Recovery — bounded self-healing between step attempts. A retry that changes…, get_llm_tools() (+36 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "FakeHUDProcess"
Cohesion: 0.10
Nodes (8): FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first., The state of every snapshot sent, in order., Stands in for HUDProcess without launching anything. Records what the service…

### Community 148 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 149 - "TestToolsCommand"
Cohesion: 0.13
Nodes (4): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., The list is read live from the registry, so a tool registered after the command…, TestToolsCommand

### Community 150 - "HUDSnapshot"
Cohesion: 0.07
Nodes (22): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+14 more)

### Community 151 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 152 - "hud/__init__.py"
Cohesion: 0.13
Nodes (18): The AetherOS heads-up display. Importing this package deliberately does not…, _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Cross-fade toward the target style., One orbiting mote. Motion is a closed-form function of time rather than an… (+10 more)

### Community 153 - "verification/tools.py"
Cohesion: 0.18
Nodes (13): _parse_condition(), parse_mode(), parse_region(), Any, Parse a caller-supplied comparison mode. Shared by the ``verify_action`` tool…, Parse a ``[left, top, width, height]`` screen region., Build a request from a plain dict, as a workflow step carries it. Unknown keys…, list_verification_methods() (+5 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.23
Nodes (7): LogisticRegression, ndarray, Deterministic logistic regression in pure numpy. A small, fully reproducible…, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "reasoner.py"
Cohesion: 0.10
Nodes (15): EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, HookRecorder, Any, The voice reasoner — the seam between a spoken turn and the LLM tool loop.…, EchoReasoner is what the pipeline tests run against, so its contract has to…, Stands in for the pipeline's HUD-facing progress callbacks. (+7 more)

### Community 156 - "ContextConfig"
Cohesion: 0.25
Nodes (6): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, ``tool_categories`` narrows the menu to the relevant tools for a run. Left…, Limits are clamped, not trusted., TestConfiguration, TestToolCategoryScoping

### Community 157 - "asyncio"
Cohesion: 0.10
Nodes (20): EnvelopeResult, _ocr_with(), Any, asyncio, Exception, ndarray, Unit tests for the concrete vision providers. The OpenCV and template providers…, Stands in for a built PaddleOCR pipeline. Records the frame it was handed so a… (+12 more)

### Community 158 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 159 - "MouseController"
Cohesion: 0.08
Nodes (11): MouseController, ABC, Drag to an absolute position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y), Move the mouse to an absolute screen position. Named ``x``/``y`` rather than… (+3 more)

### Community 160 - "TestSerialization"
Cohesion: 0.14
Nodes (10): Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, call(), failed_result(), ok_result(), _populated_state(), fixture, Tests for the agent execution state. The state layer has no interesting…, state() (+2 more)

### Community 161 - "workflow_believer_run.py"
Cohesion: 0.38
Nodes (6): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows.

### Community 162 - "AgentError"
Cohesion: 0.08
Nodes (15): ObservationLog, Any, Observation, An append-only, ordered collection of :class:`Observation`., Append one observation, rejecting anything that is not one. The type guard is…, Every observation from one source, oldest first., The most recent observations, newest last. ``latest(1)`` is the freshest single…, Accept a member or its name; reject anything else. An unknown source is… (+7 more)

### Community 163 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.14
Nodes (9): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, Score a detection ``label`` against a desired element ``target_type``., text_match_score(), _tokens(), type_match_score(), Unit tests for the deterministic match scoring. The scale is graded on purpose…, TestTextMatchScore (+1 more)

### Community 170 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 171 - "WindowService"
Cohesion: 0.17
Nodes (10): Human-readable condition, used when the caller did not supply one., Any, Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``., A full snapshot, which carries the bounds along with everything else., High-level window service. Backed by a :class:`WindowController`; holds no…, Full snapshot in one call. Uses the backend's ``describe`` when it has one --… (+2 more)

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - "test_yahoo_news_provider.py"
Cohesion: 0.40
Nodes (18): _news_item(), _ok_handler(), _provider(), asyncio, YahooNewsProvider: the first real news adapter. These tests are fully…, _search_payload(), test_duplicate_story_is_deduped(), test_empty_news_list_is_honest_no_news_not_an_error() (+10 more)

### Community 176 - "ToolRegistry"
Cohesion: 0.08
Nodes (37): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, Any, asyncio, Tests for the agent core loop. ``AgentCore`` is the driver that turns a goal…, The real engine, counting how often it was actually asked to run a tool.… (+29 more)

### Community 177 - "TestEveryRegisteredToolHasAUsableSchema"
Cohesion: 0.17
Nodes (6): fixture, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations…, A parameter with no default that is missing from ``required`` lets the model…, An open schema lets a model invent an argument, which arrives as an unexpected…, TestEveryRegisteredToolHasAUsableSchema

### Community 178 - "_make_analysis"
Cohesion: 0.25
Nodes (22): _levels(), _make_analysis(), _prov(), asyncio, parametrize, RiskService: deterministic risk geometry from a TradingAnalysis. Every number…, Construct a TradingAnalysis directly for precise risk-math assertions., _stable() (+14 more)

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 181 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 182 - "test_trading_tools.py"
Cohesion: 0.11
Nodes (32): executor(), asyncio, fixture, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_macro_context_tool_is_labelled_mock(), test_analyze_market_structure_tool() (+24 more)

### Community 183 - "SpeechToText"
Cohesion: 0.05
Nodes (29): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+21 more)

### Community 185 - ".test_is_open_reports_state_without_touching_the_backend"
Cohesion: 0.24
Nodes (11): _build(), _CountingExecutor, _fake_browser(), Any, asyncio, The real executor, recording every tool it was actually asked to run. A name…, Bind the ``BrowserService`` the tools resolve to a recording provider. Every…, Copy production tool definitions into an isolated registry. (+3 more)

### Community 186 - "ToolCall"
Cohesion: 0.21
Nodes (7): _as_tool_call(), Record the request, before anything is checked or run. Ordered first on…, Normalise what the caller handed over into a :class:`ToolCall`. A ``tool_call``…, Record a call the model asked for. Accepts the parse layer's :class:`ToolCall`…, A tool call the model requested, with usable arguments., ToolCall, TestToolCalls

### Community 187 - "PipeReader"
Cohesion: 0.09
Nodes (11): IO, decode(), PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived. (+3 more)

### Community 188 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 189 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 190 - "SapiTTS"
Cohesion: 0.13
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 192 - "_started"
Cohesion: 0.17
Nodes (10): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., One round, several calls: all answered, in order, one at a time., _started(), TestLogSafety (+2 more)

### Community 193 - "OpenAICompatibleProvider"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 194 - "OpenCVTemplateProvider"
Cohesion: 0.07
Nodes (17): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, Scales that would make the template larger than the image are dropped rather…, TestTemplateProvider, asyncio (+9 more)

### Community 205 - "rich_tools"
Cohesion: 0.12
Nodes (19): boom(), check_playing(), click_element(), ground_target(), move_mouse(), open_browser(), fixture, Click an element, reporting success but changing nothing (test double). The… (+11 more)

### Community 206 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 207 - "get_logger"
Cohesion: 0.09
Nodes (17): __init__(), Application, Main AetherOS application. Responsible for starting and shutting down the…, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+9 more)

### Community 208 - "FakeSCT"
Cohesion: 0.17
Nodes (10): fake_sct(), FakeSCT, mss_screen(), fixture, Tests for the screen capture layer. Screen capture is where the vision…, ``np.asarray`` over an mss ScreenShot aliases a buffer mss reuses, so the next…, Stands in for an ``mss.mss()`` session. Returns BGRA, the way mss does, so the…, A real MSSScreen backed by a fake session instead of a display. (+2 more)

### Community 209 - "AgentCore"
Cohesion: 0.09
Nodes (19): AgentCore, _planned_to_call(), ContextBuilder, Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Assemble a core from a provider and, optionally, its collaborators. The…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors… (+11 more)

### Community 210 - "VisionService"
Cohesion: 0.05
Nodes (27): Build the YOLO detector when its package and weights are both present. Returns…, High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a… (+19 more)

### Community 211 - "voice/service.py"
Cohesion: 0.08
Nodes (26): Future, ABC, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Stop playback immediately. Safe to call when nothing is playing., Whether audio is currently playing. (+18 more)

### Community 212 - "cli/main.py"
Cohesion: 0.14
Nodes (10): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…, CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->… (+2 more)

### Community 214 - "._format_trading_report"
Cohesion: 0.13
Nodes (8): A number for display, or ``-`` when it is missing/non-numeric., A 0-1 fraction as a percentage, or ``-`` when missing., One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.…, Run the deterministic trading pipeline for one instrument and render the…, Surface the recorded prediction-audit trail and its track record for a human --…, Render the aggregate track record + the recorded audit trail as honest plain…

### Community 215 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 216 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 217 - "MSSScreen"
Cohesion: 0.14
Nodes (9): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., parametrize, mss raises on construction without a display, so the DI container would…, TestMSSBackendInitialisation (+1 more)

### Community 218 - "ToolError"
Cohesion: 0.15
Nodes (9): Exception, ToolError, Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools. (+1 more)

### Community 219 - "test_yahoo_fundamentals_provider.py"
Cohesion: 0.39
Nodes (14): _ok_handler(), _provider(), asyncio, YahooFundamentalsProvider: the first real fundamentals adapter. These tests are…, Build a Yahoo /v10/finance/quoteSummary-shaped JSON payload., _summary_payload(), test_empty_modules_is_an_honest_empty_snapshot_not_an_error(), test_empty_result_becomes_fundamentals_error() (+6 more)

### Community 220 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 221 - "AgentStatus"
Cohesion: 0.14
Nodes (7): AgentRunResult, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, Run ``goal`` on the shared agent, labelling the turn with ``source``.…, AgentStatus, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…

### Community 222 - "TraceEvent"
Cohesion: 0.05
Nodes (52): IntEnum, _default_stage(), Enum, str, The trace event vocabulary. One concrete :class:`TraceEvent` class (not a class…, One observed moment in a run, safe to log and to persist. Only observable, log-…, Every stage of the live execution pipeline. ``str``-valued so a serialized…, How the stage an event reports is doing. Kept small and orthogonal to… (+44 more)

### Community 223 - "RecordingTTS"
Cohesion: 0.14
Nodes (5): AmplitudeCallback, Records what would have been spoken. The test double for speech output: it…, RecordingTTS, _FailingTTS, RecordingTTS whose ``speak`` raises, to exercise TTS error handling.

### Community 224 - "ErrorContext"
Cohesion: 0.05
Nodes (49): Factories that turn what a subsystem produced into an :class:`Observation`.…, BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,… (+41 more)

### Community 225 - "MarketStructureService"
Cohesion: 0.24
Nodes (11): MarketStructureService, Swing/level/trend detection over a candle series., MarketStructureService: swings, levels, trend and structural signals., test_downtrend_detected(), test_insufficient_bars_raises(), test_levels_ranked_by_proximity(), test_pattern_flags_consistent(), test_signals_carry_reference_price() (+3 more)

### Community 226 - "Application"
Cohesion: 0.17
Nodes (8): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal()

### Community 227 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 228 - "enums.py"
Cohesion: 0.03
Nodes (87): BaseSettings, Settings, Enumerations shared across the Trading Intelligence domain. Every enum inherits…, The Prediction Contract value object (spec sections 8, 19, 28). A…, CalibrationMetrics, ProbabilityEstimate, Any, datetime (+79 more)

### Community 229 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 230 - "TestSerializationAndLogging"
Cohesion: 0.20
Nodes (4): IterationInfo, Where the run is in its budget. Carried explicitly because the model behaves…, One faithful view for auditing, one redacted view for the sinks., TestSerializationAndLogging

### Community 231 - "WatchlistScanService"
Cohesion: 0.19
Nodes (6): Exception, Strongest actionable setups first; errored rows last. Sort ascending on a tuple…, Deterministic multi-instrument ranking over the analysis layer., Trim, drop blanks, de-duplicate (order-preserving), and cap., WatchlistScanService, test_mock_feed_is_scanned_but_never_actionable()

### Community 232 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 233 - "TechnicalAnalysisService"
Cohesion: 0.24
Nodes (11): Computes latest-value technical readings from a candle series., TechnicalAnalysisService, TechnicalAnalysisService: snapshot computation and honesty about gaps., test_determinism(), test_downtrend_fast_sma_below_slow(), test_insufficient_bars_raises(), test_missing_indicators_are_none_not_guessed(), test_mock_tier_propagates() (+3 more)

### Community 234 - "TestRegisteredToolSurface"
Cohesion: 0.17
Nodes (7): ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, Asserts against the process-wide registry, which the @tool decorator populates…, TestRegisteredToolSurface

### Community 235 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 236 - "test_ui.py"
Cohesion: 0.11
Nodes (13): cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, ``errors="replace"`` is the second half of the fix. Without it a single…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, The regression itself: this raised UnicodeEncodeError from _show_logo. (+5 more)

### Community 237 - "PyAutoGuiClipboard"
Cohesion: 0.22
Nodes (5): PyAutoGuiClipboard, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 238 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 239 - ".from_dict"
Cohesion: 0.11
Nodes (11): _as_float(), Any, Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., parametrize, Every bound is enforced in a constructor, so an unbounded workflow cannot exist…, "Never create infinite retries" is not satisfied by a large number either: 500…, Unknown keys are rejected rather than ignored. A step that says ``{"method":… (+3 more)

### Community 240 - "features.py"
Cohesion: 0.24
Nodes (8): _feature_columns(), FeatureMatrix, _momentum(), ndarray, Causal feature construction for probability estimation. Turns an OHLCV series…, close[t]/close[t-period] - 1, NaN for the first ``period`` positions., Stack the causal feature columns into an (n, n_features) matrix., Look-ahead-safe features + forward labels for a single series.

### Community 241 - "scan.py"
Cohesion: 0.22
Nodes (8): Any, datetime, Watchlist-scan value objects. A :class:`ScanResult` is the deterministic…, One symbol's compact directional read within a watchlist scan., A ranked watchlist scan over several instruments., ScanEntry, ScanResult, _utcnow()

### Community 242 - "make_fake_detector"
Cohesion: 0.14
Nodes (5): make_fake_detector(), Positional wiring is rejected: ``VisionService(ocr, cv)`` and…, TestDetectObjects, TestServiceInitialisation, TestShutdown

### Community 243 - "parametrize"
Cohesion: 0.27
Nodes (3): parametrize, TestRegistration, TestSchema

### Community 244 - "._ask"
Cohesion: 0.33
Nodes (3): Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal.

### Community 245 - "WindowBounds"
Cohesion: 0.22
Nodes (4): A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 246 - "TestProviderCompatibility"
Cohesion: 0.33
Nodes (4): The payload has to be accepted by the engine that already exists., The invariant the provider enforces, asserted over the whole payload., Reads are lock-free because state hands back immutable snapshots., TestProviderCompatibility

### Community 248 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 249 - "AnomalyService"
Cohesion: 0.39
Nodes (4): AnomalyService, ndarray, z-score of the last element vs the prior ``used`` elements. Returns ``(z,…, Deterministic last-bar statistical-outlier read over candles.

### Community 250 - "_win32_clipboard"
Cohesion: 0.29
Nodes (4): Any, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard()

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 252 - ".record"
Cohesion: 0.12
Nodes (15): LevelCallback, _normalize_level(), Any, ndarray, Captured microphone audio., Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is… (+7 more)

### Community 253 - ".copy_files"
Cohesion: 0.40
Nodes (3): Path, Copy one or more files/folders to the clipboard., Returns copied file paths. Returns: Empty list if clipboard contains no files.

### Community 254 - ".copy_image"
Cohesion: 0.40
Nodes (3): Any, Copy an image to the clipboard., Returns an image from the clipboard. Returns: None if clipboard doesn't contain…

### Community 255 - "automation/tools.py"
Cohesion: 0.19
Nodes (14): describe_strategies(), Strategy name to description. Read by the ``run_workflow`` tool description and…, _build(), list_recovery_strategies(), Any, The automation tools — multi-step desktop work, exposed to the model. Three…, Turn the model's JSON into a validated :class:`Workflow`. Parse errors are re-…, Execute a workflow and return its full execution record. :param name: Label for… (+6 more)

### Community 256 - ".save"
Cohesion: 0.25
Nodes (5): ndarray, Path, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region., Save a captured frame to disk.

### Community 257 - ".test_speech_moves_the_mouse_through_the_agent"
Cohesion: 0.16
Nodes (10): _agent_reasoner(), _BlockingReasoner, _CountingExecutor, _fake_mouse(), Any, A reasoner that parks until released, to exercise cancellation., Bind the ``MouseService`` the tool resolves to a recording controller.…, Wrap a real ``AgentCore`` in the production ``AgentReasoner`` adapter. (+2 more)

### Community 258 - "main"
Cohesion: 0.43
Nodes (6): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms.

### Community 259 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 265 - "TestMultipleIterations"
Cohesion: 0.29
Nodes (3): The context tracks where the run is in its budget., Determinism: no clock, no registry order, no set iteration., TestMultipleIterations

### Community 268 - "TestMSSSave"
Cohesion: 0.47
Nodes (3): Path, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame…, TestMSSSave

### Community 269 - "TestFailureHandling"
Cohesion: 0.33
Nodes (3): A vision tool invoked before bootstrap has run. The agent should get a readable…, The duration is what makes a slow-then-failed tool distinguishable from one…, TestFailureHandling

### Community 270 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 271 - "._nearest"
Cohesion: 0.40
Nodes (3): ndarray, Indices of the k nearest rows of ``x`` to ``latest`` in a standardised feature…, Up-rate and mean forward return of the analogues at ``idxs``.

### Community 272 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 278 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

### Community 279 - "executor"
Cohesion: 0.67
Nodes (3): executor(), fixture, An executor over the process-wide registry, which is where @tool registers.

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2824 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `agents/__init__.py`, `ContextBuilder`, `WindowController`, `AutomationEngine`, `TerminalService`, `VerificationResult`, `PaddleOCRProvider`, `agents/core.py`, `voice_error.py`, `Bootstrapper`, `CommandRegistry`, `MouseController`, `ScreenController`, `PolicyEngine`, `VoiceService`, `LLMEngine`, `ProcessController`, `Agent`, `agents/state.py`, `ApplicationService`, `test_unified_interaction.py`, `get_settings`, `SpeechToText`, `instrument.py`, `SapiTTS`, `VoiceConfig`, `Provenance`, `ClipboardService`, `AgentCore`, `voice/service.py`, `cli/main.py`, `KeyboardService`, `YOLOProvider`, `BrowserProvider`, `HUDProcess`, `LifecycleManager`, `StageTimings`, `TraceEvent`, `ErrorContext`, `agent_loop.py`, `Application`, `enums.py`, `ClipboardController`, `TaskManager`, `HUDConfig`, `_CountingExecutor`, `VoiceState`, `ServiceContainer`, `automation/engine.py`, `process/tools.py`, `PredictionStore`, `automation/tools.py`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `.test_speech_moves_the_mouse_through_the_agent`, `ToolCommandService`, `define`, `answer`, `agents/__init__.py`, `ContextBuilder`, `TestMultipleIterations`, `AutomationEngine`, `TestToolFailure`, `AgentPlanner`, `agents/core.py`, `test_agent_planner.py`, `test_cli_agent.py`, `ContextConfig`, `asyncio`, `test_unified_interaction.py`, `.test_is_open_reports_state_without_touching_the_backend`, `ExecutionStatus`, `_started`, `test_agent_policy.py`, `FakeLLMProvider`, `rich_tools`, `get_logger`, `AgentCore`, `ContextBuilder`, `TestFinalResponse`, `TestSerializationAndLogging`, `_CountingExecutor`, `TestProviderCompatibility`, `test_agent_execution.py`, `test_agent_e2e.py`, `automation/engine.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `get_settings` to `MarketRegime`, `main`, `test_backtest.py`, `test_orchestration.py`, `AutomationEngine`, `VerificationResult`, `vision/tools.py`, `agents/core.py`, `Bootstrapper`, `PolicyEngine`, `Direction`, `test_news.py`, `Instrument`, `_make_analysis`, `instrument.py`, `test_fundamentals.py`, `bootstrapper.py`, `get_logger`, `test_prediction_evaluator.py`, `VisionService`, `PathGuard`, `make_market_data`, `StageTimings`, `PredictionRecord`, `ErrorContext`, `enums.py`, `WatchlistScanService`, `LLMConfig`, `TestRegisteredToolSurface`, `test_probability.py`, `InMemoryPredictionStore`, `automation/engine.py`, `process/tools.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 159 inferred relationships involving `Direction` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Direction` has 159 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 88 inferred relationships involving `Instrument` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Instrument` has 88 INFERRED edges - model-reasoned connections that need verification._