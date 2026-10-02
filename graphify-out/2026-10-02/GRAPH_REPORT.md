# Graph Report - AetherOS  (2026-10-02)

## Corpus Check
- 434 files · ~348,214 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 8616 nodes · 22641 edges · 254 communities (217 shown, 24 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2845 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ddd675e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ToolCall
- Image
- answer
- define
- bootstrapper.py
- ContextBuilder
- ContextBuilder
- AgentState
- Scene
- WindowController
- AutomationEngine
- asyncio
- test_multi_timeframe.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- .test_the_full_pipeline_emits_every_stage_in_order
- voice/service.py
- trading/tools.py
- get_llm_tools
- Message
- safe_preview
- PlannedAction
- Event
- EventBus
- test_news.py
- TextToSpeech
- Bootstrapper
- PsutilProcess
- _RecordingProvider
- CommandRegistry
- FakeHUDProcess
- test_agent_planner.py
- PolicyEngine
- VoiceService
- asyncio
- make_vision_service
- test_voice_agent_e2e.py
- ProcessController
- VisionError
- test_critic.py
- HUDWindow
- ApplicationService
- test_yahoo_provider.py
- CLIRuntime
- FileController
- MouseController
- agents/state.py
- test_performance.py
- CLIUI
- Win32Window
- wire
- VisionService
- policy.py
- test_cli_agent.py
- indicators/core.py
- _RecordingProvider
- observability/pipeline.py
- FrameCache
- test_grounding_tools.py
- LLMToolLoop
- TraceEvent
- TerminalService
- Detection
- PlaywrightProvider
- TaskManager
- resolve_level
- DesktopError
- ClipboardService
- LiveTraceUI
- VisionProvider
- MarketStructureService
- FakeLLMProvider
- asyncio
- tool
- test_ceo.py
- LLMProvider
- MemoryProvider
- ProbabilityService
- ProcessService
- MouseService
- test_prediction_evaluator.py
- HUDSnapshot
- KeyboardService
- WindowService
- PipeReader
- YOLOProvider
- HUDProcess
- BrowserProvider
- PortfolioRiskService
- LifecycleManager
- events/__init__.py
- FasterWhisperSTT
- RecoveryRunner
- TestRegistration
- InMemoryPredictionStore
- BrowserService
- parse_llm_response
- VoiceConfig
- asyncio
- PlanResult
- Instrument
- ScreenController
- ClipboardController
- FileOutcomeStore
- test_browser_tools_e2e.py
- FakeProvider
- ScreenService
- PredictionRecord
- PyAutoGuiKeyboard
- FakeKeyboard
- window/tools.py
- setup_logging
- _CountingExecutor
- VoiceState
- VoicePipeline
- MarketRegime
- HookRecorder
- test_agent_execution.py
- process/tools.py
- .from_events
- vision/tools.py
- MarketData
- make_market_data
- FakeMouse
- .create
- ExecutionStatus
- AgentExecutionResult
- _settings
- ServiceContainer
- ToolCommandService
- commands
- TestRegisteredToolSurface
- Layer
- test_interface_contracts.py
- test_orchestration.py
- AgentError
- _prov
- ceo_agent_service.py
- TestWellFormedCalls
- test_yahoo_calendar_provider.py
- test_analyze_command.py
- SapiTTS
- test_ceo_agent.py
- executor.py
- EventCalendarService
- Any
- _FakeMouse
- Agent
- test_backtest.py
- GlowCache
- cli/main.py
- DivergenceService
- RenderContext
- LogisticRegression
- PlannerConfig
- renderer.py
- FilePredictionStore
- TextBlock
- PyAutoGuiMouse
- RejectedToolCall
- HUDService
- Renderer
- test_yahoo_fundamentals_provider.py
- _service
- text_match_score
- application/tools.py
- .test_the_registered_engine_is_preferred
- test_input.py
- hud/config.py
- CalibrationHistoryService
- import_all.py
- TTLCache
- test_yahoo_news_provider.py
- ToolRegistry
- test_fundamentals.py
- PredictionOutcome
- _settings
- PyAutoGuiClipboard
- screen/tools.py
- test_trading_tools.py
- tool_calls.py
- Box
- FakeScreen
- qcolor
- TestToolsCommand
- AgentCore
- test_portfolio.py
- ._fmt_num
- _RecordingMouse
- ToolExecutionCoordinator
- OpenAICompatibleProvider
- OpenCVTemplateProvider
- AetherOS
- PredictionOutcomeStatus
- ._fmt_pct
- LLMProviderManager
- ._format_trading_report
- calibration_audit.py
- main
- _one
- Step
- ._run
- Application
- enums.py
- test_calibration_history.py
- MSSScreen
- _Def
- TestUnknownTool
- .grab
- AgentRunResult
- agents/core.py
- ._brief_command
- ErrorContext
- ParsedResponse
- .is_available
- PulseLayer
- TickLayer
- scan.py
- Provenance
- bootstrapper
- spatial.py
- .test_a_finished_run_executes_nothing
- run_workflow_from_file.py
- TestCallIdentifiers
- Any
- executor
- _stable_id
- TestFinalResponse
- .hud
- _started
- .trace
- .voice
- main
- .move_to
- _RecordingMouse
- TestToolFailure
- TraceCollector
- TestEveryToolModuleImports
- LLMEngine
- Direction

## God Nodes (most connected - your core abstractions)
1. `Direction` - 284 edges
2. `ToolRegistry` - 242 edges
3. `Image` - 183 edges
4. `Instrument` - 177 edges
5. `tool()` - 146 edges
6. `AgentState` - 138 edges
7. `get_logger()` - 119 edges
8. `Provenance` - 108 edges
9. `define()` - 106 edges
10. `EventBus` - 105 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/run_workflow_from_file.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --calls--> `run_workflow()`  [INFERRED]
  .audit/run_workflow_from_file.py → src/aetheros/desktop/automation/tools.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (254 total, 24 thin omitted)

### Community 0 - "ToolCall"
Cohesion: 0.08
Nodes (22): _as_tool_call(), _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, Record a call that was turned away, without the engine being asked. The refusal…, Report a refusal that could not be written down. Reached only when the run is…, Write the outcome into the run, then describe it. The record is built before it… (+14 more)

### Community 1 - "Image"
Cohesion: 0.03
Nodes (50): Image, ndarray, Universal image model for AetherOS. Every vision module should consume and…, Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing… (+42 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (50): Executes registered AetherOS tools., The registry this executor validates and runs tools from., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes() (+42 more)

### Community 4 - "bootstrapper.py"
Cohesion: 0.03
Nodes (85): Register the deterministic Trading Intelligence core. Self-contained: it…, get_settings(), Singleton Settings object., Map ATR-as-fraction-of-price to a volatility band (deterministic)., MockNewsProvider, A reproducible, clearly-labelled synthetic news source., AnalysisService, Deterministic end-to-end analysis for one instrument. (+77 more)

### Community 5 - "ContextBuilder"
Cohesion: 0.05
Nodes (53): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call(), Any, asyncio, ContextBuilder (+45 more)

### Community 6 - "ContextBuilder"
Cohesion: 0.05
Nodes (42): _clamp(), ContextBuilder, _describe_call(), _describe_result(), IterationInfo, Any, Observation, Agent context assembly. One :class:`AgentContext` is everything the model needs… (+34 more)

### Community 7 - "AgentState"
Cohesion: 0.04
Nodes (21): AgentState, ErrorRecord, BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Finish the run unsuccessfully, recording the unrecoverable error., Stop the run on request. Distinct from failure: nothing went wrong., A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, Something that went wrong during the run. ``recoverable`` is the important… (+13 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (38): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+30 more)

### Community 9 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.05
Nodes (53): AutomationEngine, _backoff_seconds(), Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran…, Delay before the next attempt: exponential, and capped. Exponential because the…, Executes workflows step by step, verifying as it goes. Stateless between runs:… (+45 more)

### Community 11 - "asyncio"
Cohesion: 0.08
Nodes (13): call(), failed_result(), ok_result(), asyncio, fixture, Tests for the agent execution state. The state layer has no interesting…, state(), TestCompletion (+5 more)

### Community 12 - "test_multi_timeframe.py"
Cohesion: 0.54
Nodes (7): _analyse(), _mtf(), asyncio, MultiTimeframeService: deterministic base-vs-higher-timeframe confirmation. Two…, test_higher_trend_confirms_base_and_is_reliable(), test_is_deterministic(), test_mock_data_is_never_reliable()

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (50): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, Outcome of one desktop action, as the model sees it. Distinct from…, Whether the caller may proceed as if the action happened. False when the…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in… (+42 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (34): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+26 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.08
Nodes (22): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider… (+14 more)

### Community 16 - ".test_the_full_pipeline_emits_every_stage_in_order"
Cohesion: 0.20
Nodes (10): _fake_mouse(), _FakeMouseController, _is_ordered_subsequence(), Any, asyncio, End-to-end: the live trace of "What is my mouse position?" (PHASE 14). This is…, The one seam below MouseService -- returns a fixed cursor position. Duck-typed…, Bind the ``MouseService`` the tool resolves to a fixed-position backend. (+2 more)

### Community 17 - "voice/service.py"
Cohesion: 0.03
Nodes (42): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+34 more)

### Community 18 - "trading/tools.py"
Cohesion: 0.07
Nodes (71): _analysis(), analyze_fundamentals(), analyze_instrument(), analyze_macro_context(), analyze_market_structure(), analyze_multi_timeframe(), analyze_news_sentiment(), analyze_relative_strength() (+63 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.05
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "Message"
Cohesion: 0.05
Nodes (48): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, The provider-facing shape, matching ``LLMToolLoop`` exactly., build_application(), _initial_config(), main(), Any (+40 more)

### Community 21 - "safe_preview"
Cohesion: 0.12
Nodes (12): Emit the terminal tool event for a delegated call (PHASE 5). ``describe()`` is…, Any, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, safe_metadata(), safe_preview(), truncate_value() (+4 more)

### Community 22 - "PlannedAction"
Cohesion: 0.05
Nodes (20): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim. (+12 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (71): Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM. (+63 more)

### Community 24 - "EventBus"
Cohesion: 0.08
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "test_news.py"
Cohesion: 0.06
Nodes (47): NewsItem, Any, Content-addressed id: same headline from the same source -> same id.…, A single sourced headline as a provider returned it (no interpretation)., _stable_id(), NewsError, A news/sentiment analysis could not be produced from the given inputs., NewsSentimentAnalyzed (+39 more)

### Community 26 - "TextToSpeech"
Cohesion: 0.04
Nodes (53): Future, LevelCallback, AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded. (+45 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.09
Nodes (6): Bootstrapper, Whether Playwright can be imported. find_spec rather than a try/import:…, Coordinates application startup and shutdown. The bootstrapper is responsible…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Shutdown subsystems in reverse order.

### Community 28 - "PsutilProcess"
Cohesion: 0.09
Nodes (21): PsutilProcess, Any, Path, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle…, Read one process into a plain dict. Fields that require privileges are filled…, Start a program and return its pid. ``env``, when given, *extends* the current…, Open a file with its registered application. Returns ``0``, which means "no pid… (+13 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.06
Nodes (17): CommandHandler, CommandRegistry, Scan a watchlist and rank it by directional signal for a human -- no LLM…, Register a CLI command., Render a watchlist-scan dict as an honest, ranked plain-text table., Execute a parsed command., Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as… (+9 more)

### Community 31 - "FakeHUDProcess"
Cohesion: 0.07
Nodes (21): bus(), fake_process(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything., The double's class, for tests that need a differently configured one. (+13 more)

### Community 32 - "test_agent_planner.py"
Cohesion: 0.08
Nodes (32): builder(), context(), _FailingProvider, move_mouse(), planner(), provider(), Any, asyncio (+24 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.04
Nodes (51): PolicyConfig, Any, Policy configuration: the rules the engine evaluates against. Deliberately…, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyDecision, PolicyEvaluation, Any (+43 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "asyncio"
Cohesion: 0.09
Nodes (17): asyncio, _raising_start(), `publisher.publish()` is how code fires an event without holding a bus., Dropping the reference is not enough: the HUD registers bound methods, so a…, A headless or server install must not try to open a window., Nothing should grab the microphone or install a global hotkey hook unless it…, The common case: `aether` on a machine with both flags unset., The gate is the caller's, not HUDService's — the service stays usable from a… (+9 more)

### Community 36 - "make_vision_service"
Cohesion: 0.05
Nodes (37): Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), isolated_container(), make_fake_detector(), make_fake_ocr(), make_unclosable_ocr(), make_vision_service(), fixture (+29 more)

### Community 37 - "test_voice_agent_e2e.py"
Cohesion: 0.06
Nodes (29): Captured microphone audio., Recording, _flag(), _integer(), _number(), Build a configuration from AETHEROS_* environment variables., _text(), EchoReasoner (+21 more)

### Community 38 - "ProcessController"
Cohesion: 0.07
Nodes (18): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+10 more)

### Community 39 - "VisionError"
Cohesion: 0.07
Nodes (20): ColorSpace, Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary). (+12 more)

### Community 40 - "test_critic.py"
Cohesion: 0.17
Nodes (88): CheckStatus, CriticVerdict, Outcome of one critic check. SKIPPED is first-class: a check the current build…, The critic's go/no-go decision on a proposed signal. INSUFFICIENT_EVIDENCE is…, _analysis(), _evidence(), asyncio, CriticService: deterministic go/no-go validation of a proposed signal. The… (+80 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.11
Nodes (22): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+14 more)

### Community 43 - "test_yahoo_provider.py"
Cohesion: 0.12
Nodes (28): Resolve a user/tool string to a Timeframe, raising ValueError if unknown., InsufficientDataError, MarketDataError, ProviderError, A market-data operation could not be completed., A data provider failed, timed out, or returned an unusable response., Not enough history to compute the requested analysis honestly., AsyncClient (+20 more)

### Community 44 - "CLIRuntime"
Cohesion: 0.20
Nodes (5): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MouseController"
Cohesion: 0.08
Nodes (11): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+3 more)

### Community 47 - "agents/state.py"
Cohesion: 0.11
Nodes (14): new_state_id(), Any, Agent execution state. One :class:`AgentState` is the complete, explicit record…, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The transcript in provider wire format, ready to send., ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-… (+6 more)

### Community 48 - "test_performance.py"
Cohesion: 0.22
Nodes (23): _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes., _resolved(), _service() (+15 more)

### Community 49 - "CLIUI"
Cohesion: 0.05
Nodes (25): CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI. (+17 more)

### Community 50 - "Win32Window"
Cohesion: 0.07
Nodes (23): A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window. (+15 more)

### Community 51 - "wire"
Cohesion: 0.07
Nodes (27): executor(), asyncio, fixture, Path, Tests for the vision tools and their registry integration. These exercise the…, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in… (+19 more)

### Community 52 - "VisionService"
Cohesion: 0.04
Nodes (45): High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService (+37 more)

### Community 53 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 54 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 55 - "indicators/core.py"
Cohesion: 0.05
Nodes (61): adx(), _as_float_array(), atr(), bollinger(), ema(), last_finite(), macd(), _nan_prefix() (+53 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - "observability/pipeline.py"
Cohesion: 0.10
Nodes (26): _accumulate_status(), _apply_event(), _detail(), ExecutionPipeline, PipelineStage, PipelineStatus, _presentation_for(), Any (+18 more)

### Community 58 - "FrameCache"
Cohesion: 0.12
Nodes (15): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, _Clock, _make_capture(), asyncio, Tests for the short-lived screen-frame cache. The clock is injected so time… (+7 more)

### Community 59 - "test_grounding_tools.py"
Cohesion: 0.09
Nodes (17): _block(), executor(), asyncio, fixture, parametrize, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received… (+9 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.08
Nodes (24): AgentLoopResult, LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Outcome of a full loop run., Main LLM ↔ tool-coordination loop., Run the loop against AgentState and the agent-layer coordinator. The existing… (+16 more)

### Community 61 - "TraceEvent"
Cohesion: 0.10
Nodes (27): InteractionGateway, The one entry a front end submits a turn through. Both the terminal and voice…, Submit a goal to the shared agent, tagged with its front end., One observed moment in a run, safe to log and to persist. Only observable, log-…, TraceEvent, new_session_id(), A fresh per-session id for a front end that owns one gateway., _boom() (+19 more)

### Community 62 - "TerminalService"
Cohesion: 0.14
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 63 - "Detection"
Cohesion: 0.04
Nodes (41): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+33 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 65 - "TaskManager"
Cohesion: 0.06
Nodes (37): Any, TaskContext, InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError (+29 more)

### Community 66 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 67 - "DesktopError"
Cohesion: 0.04
Nodes (69): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Application service. An application is not a process, and conflating the two is…, is_uri(), Application name resolution. The model asks for "notepad", or "calculator", or…, Whether a target is a shell URI (``ms-settings:``, ``mailto:``) rather than a…, Any (+61 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "LiveTraceUI"
Cohesion: 0.11
Nodes (13): Panel, LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole (+5 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "MarketStructureService"
Cohesion: 0.11
Nodes (21): MarketStructureService, ndarray, Swing/level/trend detection over a candle series., _build(), EvidenceService: turning deterministic reads into sourced, weighted claims. The…, test_every_item_is_weighted_and_typed(), test_evidence_inherits_provenance_and_quality(), test_evidence_is_deterministic() (+13 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "tool"
Cohesion: 0.15
Nodes (29): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+21 more)

### Community 75 - "test_ceo.py"
Cohesion: 0.08
Nodes (28): CEOBrief, Any, datetime, Trading-CEO brief value object. A :class:`CEOBrief` is the natural-language…, A grounded natural-language narration of a deterministic trading report., _utcnow(), Narrate via the LLM when wired; otherwise a deterministic fallback. Any LLM…, Interpret a free-text request, then brief the instrument it names. The LLM… (+20 more)

### Community 76 - "LLMProvider"
Cohesion: 0.08
Nodes (13): LLMProvider, ABC, Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources. (+5 more)

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "ProbabilityService"
Cohesion: 0.04
Nodes (46): MonitoringReport, Any, datetime, Monitoring-sweep value object. A :class:`MonitoringReport` is the result of one…, One bounded monitoring sweep: resolved outcomes + their aggregate., _utcnow(), PredictionPerformance, Any (+38 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 81 - "test_prediction_evaluator.py"
Cohesion: 0.28
Nodes (24): _Bus, _evaluator(), _market_data(), asyncio, datetime, The deterministic prediction-outcome evaluator (spec sections 6, 16, 29). These…, A minimal event bus that records what the evaluator publishes., _record() (+16 more)

### Community 82 - "HUDSnapshot"
Cohesion: 0.08
Nodes (21): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+13 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 85 - "PipeReader"
Cohesion: 0.08
Nodes (13): IO, decode(), encode(), PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Frame one message as a single line of JSON. Newline-delimited JSON rather than… (+5 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (17): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Make torch.cuda.is_available() report a chosen value. (+9 more)

### Community 87 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.04
Nodes (25): BrowserProvider, ABC, Any, Path, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element. (+17 more)

### Community 89 - "PortfolioRiskService"
Cohesion: 0.15
Nodes (13): PortfolioCandidate, PortfolioPosition, PortfolioRiskPlan, Any, datetime, Portfolio-risk value objects. Where…, One candidate trade feeding the allocator: its directional risk geometry., A candidate after allocation: its size, risk and notional (or why not). (+5 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "events/__init__.py"
Cohesion: 0.14
Nodes (16): get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application…, Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., set_event_bus(), clear_subscribers(), get_subscribers() (+8 more)

### Community 92 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 93 - "RecoveryRunner"
Cohesion: 0.10
Nodes (13): _append_recovery_detail(), Fold recovery outcomes into the error the step will report if it still fails.…, Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools. (+5 more)

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "InMemoryPredictionStore"
Cohesion: 0.29
Nodes (19): InMemoryPredictionStore, Process-local reference store. Deterministic, dependency-free, non-durable.…, _FakeEvaluator, asyncio, The prediction track-record service: the on-demand composition of the audit…, A minimal, hand-built recorded prediction with a fixed content id., A RESOLVED, optionally-graded outcome for the fake evaluator to hand back., Returns a pre-baked outcome per record id; raises for flagged ids. (+11 more)

### Community 96 - "BrowserService"
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "parse_llm_response"
Cohesion: 0.19
Nodes (6): parse_llm_response(), Normalise a provider tool-call response. Never raises. Accepts the shape…, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn., TestContent

### Community 98 - "VoiceConfig"
Cohesion: 0.05
Nodes (34): AudioCapture, AudioPlayer, Microphone capture with energy-based silence detection. PortAudio delivers…, Non-blocking playback of mono float32 PCM. Amplitude is measured inside the…, Abort playback immediately., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always…, Configuration for the AetherOS voice subsystem. Values may be supplied directly… (+26 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "PlanResult"
Cohesion: 0.09
Nodes (13): PlanResult, What one planning round produced. The question the planner answers is singular…, Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only…, Emit LLM_RESPONSE_RECEIVED from observable response data only. Reads…, Emit PLANNER_DECISION from the log-safe ``describe`` projection. (+5 more)

### Community 101 - "Instrument"
Cohesion: 0.03
Nodes (122): Supported candle timeframes., Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, Timeframe, EventImpact, EventType, MarketEvent, Any (+114 more)

### Community 102 - "ScreenController"
Cohesion: 0.12
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - "FileOutcomeStore"
Cohesion: 0.22
Nodes (13): FileOutcomeStore, Path, Durable JSON Lines outcome store (append-per-write, last-line-wins on load).…, _outcome(), asyncio, The outcome store: in-memory + durable JSON Lines accumulation of resolved…, test_file_store_last_line_wins_on_reload(), test_file_store_newest_first_filter_and_limit() (+5 more)

### Community 105 - "test_browser_tools_e2e.py"
Cohesion: 0.23
Nodes (12): _build(), _CountingExecutor, _fake_browser(), Any, asyncio, End-to-end validation of the browser tools through the Agent Core. This mirrors…, The real executor, recording every tool it was actually asked to run. A name…, Bind the ``BrowserService`` the tools resolve to a recording provider. Every… (+4 more)

### Community 106 - "FakeProvider"
Cohesion: 0.30
Nodes (15): FakeProvider, A controllable, clearly-synthetic provider for service tests. Unlike the mock…, asyncio, MarketDataService: caching, validation, freshness and honest error typing. This…, _service(), test_fresh_series_is_ok(), test_invalid_symbol_raises(), test_non_positive_limit_raises() (+7 more)

### Community 107 - "ScreenService"
Cohesion: 0.12
Nodes (15): ndarray, Path, Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region. (+7 more)

### Community 108 - "PredictionRecord"
Cohesion: 0.05
Nodes (50): PredictionRecord, Any, datetime, The Prediction Contract value object (spec sections 8, 19, 28). A…, A prediction resting on mock data can never be treated as reliable., Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, Content-addressed id for one prediction (spec section 8). Keyed on the full… (+42 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.11
Nodes (9): Any, PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or… (+1 more)

### Community 110 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "setup_logging"
Cohesion: 0.23
Nodes (9): __init__(), configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), Configure AetherOS logging. Idempotent unless ``force`` is set. This is the…, Re-configure logging with a stderr console sink attached., Re-configure logging with file sinks only. (+1 more)

### Community 113 - "_CountingExecutor"
Cohesion: 0.16
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, _CountingExecutor, Defaults, and the invariant the class docstring states., The real engine, counting how often it was asked. A subclass rather than a…, TestConstruction

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (13): Queue a state event. The state machine is synchronous, so publishing is…, Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state. (+5 more)

### Community 115 - "VoicePipeline"
Cohesion: 0.11
Nodes (15): Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE., Run one turn under a timeout, mapping failures onto ERROR., Outcome of one voice interaction. (+7 more)

### Community 116 - "MarketRegime"
Cohesion: 0.18
Nodes (19): MarketRegime, The prevailing *character* of the market, classified deterministically from…, The directional bias implied by the regime -- never a probability., _FakeBus, asyncio, Market-regime detection: deterministic trending / ranging / volatile reads.…, Records published events; duck-typed stand-in for the EventBus., _service() (+11 more)

### Community 117 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 118 - "test_agent_execution.py"
Cohesion: 0.10
Nodes (27): add_async(), coordinator(), executor(), explodes(), journal(), _journalled(), move_mouse(), Any (+19 more)

### Community 119 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 120 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 121 - "vision/tools.py"
Cohesion: 0.07
Nodes (42): get_frame_cache(), Short-lived screen-frame cache. A desktop agent frequently runs several vision…, Process-wide frame cache, sized from the shared settings object. Built once…, click_grounded_target(), _engine(), ground_target(), Any, Grounding tools: the agent-facing surface of the grounding layer. These are the… (+34 more)

### Community 122 - "MarketData"
Cohesion: 0.04
Nodes (53): SignalFn, BacktestResult, Any, datetime, Backtest value objects. A :class:`BacktestResult` is the deterministic product…, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome (+45 more)

### Community 123 - "make_market_data"
Cohesion: 0.09
Nodes (48): make_market_data(), datetime, Build a MarketData from a close series with plausible OHLC/volume., AnomalyService: deterministic last-bar statistical-outlier detection. These…, _service(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_quiet_tape_is_no_anomaly_and_reliable() (+40 more)

### Community 125 - ".create"
Cohesion: 0.07
Nodes (20): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,… (+12 more)

### Community 126 - "ExecutionStatus"
Cohesion: 0.25
Nodes (5): ExecutionStatus, str, How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 127 - "AgentExecutionResult"
Cohesion: 0.06
Nodes (19): AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values… (+11 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "ServiceContainer"
Cohesion: 0.08
Nodes (14): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance. (+6 more)

### Community 130 - "ToolCommandService"
Cohesion: 0.11
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 132 - "TestRegisteredToolSurface"
Cohesion: 0.08
Nodes (13): fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations… (+5 more)

### Community 133 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "test_orchestration.py"
Cohesion: 0.09
Nodes (44): The final desk-level recommendation on a composed trading report. A…, ReportRecommendation, EvidenceReason, Explanation, Any, datetime, Signal-explanation value object. An :class:`Explanation` answers the spec's…, One line of the consolidated ledger (a compact view of an Evidence item). (+36 more)

### Community 136 - "AgentError"
Cohesion: 0.04
Nodes (64): Record one :class:`Observation` per delegated tool result. A refused call…, browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller… (+56 more)

### Community 137 - "_prov"
Cohesion: 0.15
Nodes (20): _anomaly(), _backtest(), _breakout(), _calendar(), _divergence(), _fundamentals(), _historical(), _macro() (+12 more)

### Community 138 - "ceo_agent_service.py"
Cohesion: 0.12
Nodes (17): CEOInvestigation, CEOStep, Any, datetime, CEO-investigation value object. A :class:`CEOInvestigation` is the record of…, One tool call the CEO made during an investigation., The record of an agentic, tool-calling CEO investigation., _utcnow() (+9 more)

### Community 139 - "TestWellFormedCalls"
Cohesion: 0.15
Nodes (5): SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The OpenAI wire format sends arguments as a JSON *string*., A provider that passes the wire shape through verbatim keeps the name and…, TestWellFormedCalls

### Community 140 - "test_yahoo_calendar_provider.py"
Cohesion: 0.32
Nodes (20): _calendar_payload(), _ok_handler(), _provider(), asyncio, YahooCalendarProvider: the first real event-calendar adapter. These tests are…, A unix timestamp ``days_from_now`` days from now (negative = past)., Build a Yahoo /v10/finance/quoteSummary calendarEvents-shaped payload., test_empty_calendar_is_a_clear_calendar_not_an_error() (+12 more)

### Community 141 - "test_analyze_command.py"
Cohesion: 0.13
Nodes (28): asyncio, The ``analyze`` CLI command: the deterministic trading pipeline surfaced to a…, test_analyze_backtest_flag_includes_backtest(), test_analyze_carries_uncertainty_reminder(), test_analyze_flags_advisory_layers_as_unreliable(), test_analyze_never_fabricates_probability(), test_analyze_not_connected_without_service(), test_analyze_renders_critic_verdict_and_checks() (+20 more)

### Community 142 - "SapiTTS"
Cohesion: 0.14
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 143 - "test_ceo_agent.py"
Cohesion: 0.20
Nodes (16): _FakeExecutor, Any, asyncio, CEOAgentService: the Trading CEO as a bounded, fenced tool-calling loop. A…, Returns canned results per tool name; records what was executed., Yields a fixed sequence of raw replies, one per generate() call., _Result, _ScriptedLLM (+8 more)

### Community 144 - "executor.py"
Cohesion: 0.05
Nodes (43): Level 1+2: import every tool module, report registration. The module list is…, Parameter, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Agent planner. One responsibility: ``GOAL -> the next action``. The planner…, Exception, ToolError, is_unconstrained(), public_parameters() (+35 more)

### Community 145 - "EventCalendarService"
Cohesion: 0.20
Nodes (6): CalendarError, An event/economic-calendar lookup could not be produced from the inputs., MarketEventsDetected, A deterministic event-calendar lookup was produced for an instrument., EventCalendarService, Deterministic scheduled-event lookup for one instrument and horizon.

### Community 146 - "Any"
Cohesion: 0.05
Nodes (23): AnalysisCompleted, BacktestCompleted, FundamentalsAnalyzed, MarketDataUpdated, MarketRegimeDetected, PredictionCreated, PredictionResolved, ProbabilityEstimated (+15 more)

### Community 148 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 149 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 150 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 151 - "cli/main.py"
Cohesion: 0.13
Nodes (19): CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command., _ask(), _build(), _CountingExecutor (+11 more)

### Community 152 - "DivergenceService"
Cohesion: 0.15
Nodes (17): DivergenceService, ndarray, Indices that are a strict local min (low) / max (high) over +/-window. Returns…, Classify regular divergence over the two most recent pivots. For lows…, Pick the stronger of a detected bullish/bearish divergence. If both fired, the…, Deterministic price-vs-RSI regular-divergence read over candles., DivergenceService: deterministic price-vs-RSI regular-divergence detection. Two…, _service() (+9 more)

### Community 153 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.27
Nodes (6): LogisticRegression, ndarray, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "PlannerConfig"
Cohesion: 0.15
Nodes (6): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, parametrize, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 156 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 157 - "FilePredictionStore"
Cohesion: 0.19
Nodes (14): FilePredictionStore, Path, A durable, append-only JSON Lines implementation of the same port. Each…, Populate the in-memory index from the file (once). Caller holds lock., asyncio, FilePredictionStore: the durable JSON Lines prediction-audit store. These pin…, Build a minimal, valid PredictionRecord with a chosen id., _record() (+6 more)

### Community 158 - "TextBlock"
Cohesion: 0.04
Nodes (24): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, Map box coordinates from a downscaled frame back to the original image. Pure… (+16 more)

### Community 159 - "PyAutoGuiMouse"
Cohesion: 0.08
Nodes (7): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., Return the current desktop subsystem status., status(), PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 160 - "RejectedToolCall"
Cohesion: 0.19
Nodes (6): A call the planner refused to pass on, and why. Carries enough to answer the…, Whether a ``tool`` message can carry this rejection back. A provider rejects a…, RejectedToolCall, Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read.

### Community 161 - "HUDService"
Cohesion: 0.06
Nodes (23): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+15 more)

### Community 162 - "Renderer"
Cohesion: 0.15
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 163 - "test_yahoo_fundamentals_provider.py"
Cohesion: 0.39
Nodes (14): _ok_handler(), _provider(), asyncio, YahooFundamentalsProvider: the first real fundamentals adapter. These tests are…, Build a Yahoo /v10/finance/quoteSummary-shaped JSON payload., _summary_payload(), test_empty_modules_is_an_honest_empty_snapshot_not_an_error(), test_empty_result_becomes_fundamentals_error() (+6 more)

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.14
Nodes (9): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, Score a detection ``label`` against a desired element ``target_type``., text_match_score(), _tokens(), type_match_score(), Unit tests for the deterministic match scoring. The scale is graded on purpose…, TestTextMatchScore (+1 more)

### Community 166 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 167 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 170 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 171 - "hud/config.py"
Cohesion: 0.29
Nodes (8): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), Any, Coerce and clamp every field. Runs on every construction path — defaults,…, Every field's declared default. Derived from the dataclass rather than written…

### Community 172 - "CalibrationHistoryService"
Cohesion: 0.17
Nodes (8): CalibrationAudit, Any, Realised-calibration measurement over the accumulated prediction history., CalibrationHistoryService, ndarray, A resolved, non-mock, reliable outcome carrying a calibrated P(up)., Fit a secondary Platt map p_corrected = sigmoid(a*p + b) on history. Returns…, Measures realised calibration over the accumulated outcome history.

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - "test_yahoo_news_provider.py"
Cohesion: 0.40
Nodes (18): _news_item(), _ok_handler(), _provider(), asyncio, YahooNewsProvider: the first real news adapter. These tests are fully…, _search_payload(), test_duplicate_story_is_deduped(), test_empty_news_list_is_honest_no_news_not_an_error() (+10 more)

### Community 176 - "ToolRegistry"
Cohesion: 0.05
Nodes (61): Assemble a core from a provider and, optionally, its collaborators. The…, AgentStatus, Enum, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…, Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, boom() (+53 more)

### Community 177 - "test_fundamentals.py"
Cohesion: 0.12
Nodes (31): FundamentalSnapshot, Any, Names of the metrics that were actually reported (non-None)., Content-addressed id: same instrument + source + reporting period -> same id.…, Raw sourced company financials (no interpretation). Missing metric = None., _stable_id(), MockFundamentalsProvider, A reproducible, clearly-labelled synthetic fundamentals source. (+23 more)

### Community 178 - "PredictionOutcome"
Cohesion: 0.08
Nodes (13): PredictionOutcome, Any, datetime, Rebuild an outcome from its :meth:`to_dict` form (durable read-back). The…, The auditable result of checking one prediction against later market data., A resolved, directional outcome that was actually graded hit/miss., _utcnow(), InMemoryOutcomeStore (+5 more)

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "PyAutoGuiClipboard"
Cohesion: 0.12
Nodes (11): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Return the current clipboard state. The state is inspected once and reused so…, Return the ``win32clipboard`` module. Imported lazily so this module stays… (+3 more)

### Community 181 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 182 - "test_trading_tools.py"
Cohesion: 0.09
Nodes (41): asyncio, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_macro_context_tool_is_labelled_mock(), test_analyze_market_structure_tool(), test_analyze_multi_timeframe_tool_is_labelled_mock(), test_analyze_news_sentiment_tool_is_labelled_mock() (+33 more)

### Community 183 - "tool_calls.py"
Cohesion: 0.29
Nodes (11): _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object., Best-effort text form of a malformed payload, for the error report. (+3 more)

### Community 184 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 185 - "FakeScreen"
Cohesion: 0.21
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 186 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 187 - "TestToolsCommand"
Cohesion: 0.17
Nodes (3): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., TestToolsCommand

### Community 188 - "AgentCore"
Cohesion: 0.12
Nodes (11): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, A stable identity for *what this call did*, for loop detection. Two calls share…, _agent_reasoner(), _CountingExecutor, Any (+3 more)

### Community 189 - "test_portfolio.py"
Cohesion: 0.44
Nodes (9): _cand(), PortfolioRiskService: deterministic risk-budgeted allocation across a basket.…, _svc(), test_candidate_without_a_stop_is_excluded_with_a_reason(), test_empty_basket_is_a_valid_empty_plan(), test_equal_risk_slices_and_budget_respected(), test_exposure_cap_scales_the_book_down(), test_is_deterministic() (+1 more)

### Community 190 - "._fmt_num"
Cohesion: 0.20
Nodes (5): Risk-budget a basket of trades for a human -- no LLM involved (spec section 5,…, Render a portfolio-risk plan dict as honest, plain terminal text., A number for display, or ``-`` when it is missing/non-numeric., Explain WHY an instrument's recommendation came out the way it did -- no LLM…, Render an explanation dict as honest, plain terminal text.

### Community 191 - "_RecordingMouse"
Cohesion: 0.11
Nodes (4): _fake_mouse(), Bind the ``MouseService`` the tool resolves to a recording controller.…, A ``MouseController`` sitting where PyAutoGUI would. Records every absolute…, _RecordingMouse

### Community 192 - "ToolExecutionCoordinator"
Cohesion: 0.12
Nodes (10): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, The agent-layer coordinator used by legacy loop calls., Argument names may be logged. Argument values may not. ``type_text`` and…, What counts as a validated call, and what is a programming error. These raise… (+2 more)

### Community 193 - "OpenAICompatibleProvider"
Cohesion: 0.14
Nodes (6): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…, main()

### Community 194 - "OpenCVTemplateProvider"
Cohesion: 0.07
Nodes (17): Build the YOLO detector when its package and weights are both present. Returns…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, A real VisionService with a fake OCR backend. The OpenCV and template providers…, vision_service(), asyncio (+9 more)

### Community 205 - "PredictionOutcomeStatus"
Cohesion: 0.29
Nodes (14): PredictionOutcomeStatus, The state of a past prediction checked against what actually happened.…, _Bus, _outcome(), asyncio, The monitoring service: one bounded "Observe Result -> Evaluate" sweep. These…, _record(), _service_with() (+6 more)

### Community 206 - "._fmt_pct"
Cohesion: 0.20
Nodes (5): Run one monitoring sweep for a human -- resolve the recorded predictions…, Render a monitoring-sweep dict as honest, plain terminal text., Surface the recorded prediction-audit trail and its track record for a human --…, Render the aggregate track record + the recorded audit trail as honest plain…, A 0-1 fraction as a percentage, or ``-`` when missing.

### Community 208 - "._format_trading_report"
Cohesion: 0.25
Nodes (4): One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.…, Run the deterministic trading pipeline for one instrument and render the…

### Community 209 - "calibration_audit.py"
Cohesion: 0.67
Nodes (3): datetime, Calibration-audit value object. A :class:`CalibrationAudit` is the honest first…, _utcnow()

### Community 210 - "main"
Cohesion: 0.43
Nodes (6): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms.

### Community 211 - "_one"
Cohesion: 0.15
Nodes (9): _one(), Parsing of provider tool-call responses. Everything the model emits is…, The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature., A tool message must carry a name, so a nameless call cannot be answered inside…, TestMalformedCalls (+1 more)

### Community 212 - "Step"
Cohesion: 0.08
Nodes (21): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows., _clamp_seconds(), Any (+13 more)

### Community 213 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 215 - "enums.py"
Cohesion: 0.03
Nodes (112): BaseSettings, Settings, get_logger(), Returns a module-specific logger. Example: logger = get_logger("vision"), Command execution. Three decisions in here are load-bearing. **A non-zero exit…, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, _utcnow() (+104 more)

### Community 216 - "test_calibration_history.py"
Cohesion: 0.47
Nodes (10): _audit_over(), _outcome(), asyncio, CalibrationHistoryService: the honest first rung of learning from history. It…, test_empty_history_cannot_measure(), test_is_deterministic(), test_mock_and_unreliable_outcomes_are_excluded(), test_overconfident_history_is_flagged_with_a_correction() (+2 more)

### Community 217 - "MSSScreen"
Cohesion: 0.08
Nodes (22): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., fake_sct(), FakeSCT, mss_screen() (+14 more)

### Community 220 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 221 - "AgentRunResult"
Cohesion: 0.10
Nodes (14): AgentRunResult, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, Run ``goal`` on the shared agent, labelling the turn with ``source``.…, current_interaction(), interaction_scope(), InteractionContext (+6 more)

### Community 222 - "agents/core.py"
Cohesion: 0.08
Nodes (33): The agent core loop: the driver that turns a goal into a finished run. This is…, Enum, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits… (+25 more)

### Community 224 - "ErrorContext"
Cohesion: 0.05
Nodes (46): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError (+38 more)

### Community 225 - "ParsedResponse"
Cohesion: 0.22
Nodes (5): ParsedResponse, Normalised view of one provider response., parametrize, A provider that returned plain text still yields a usable answer., TestDegenerateInput

### Community 229 - "scan.py"
Cohesion: 0.18
Nodes (9): Any, datetime, Watchlist-scan value objects. A :class:`ScanResult` is the deterministic…, One symbol's compact directional read within a watchlist scan., A ranked watchlist scan over several instruments., ScanEntry, ScanResult, _utcnow() (+1 more)

### Community 230 - "Provenance"
Cohesion: 0.02
Nodes (142): Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, AnomalyAnalysis, Any, datetime, Statistical-anomaly value object. An :class:`AnomalyAnalysis` is the…, Deterministic last-bar statistical-outlier read for one instrument. (+134 more)

### Community 231 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

### Community 232 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 239 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 241 - "_started"
Cohesion: 0.17
Nodes (10): _call(), asyncio, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., The engine's verdict is captured, not re-derived. The planner checks arguments…, One round, several calls: all answered, in order, one at a time., _started(), TestInvalidArguments (+2 more)

### Community 248 - "_RecordingMouse"
Cohesion: 0.11
Nodes (3): A ``MouseController`` sitting where PyAutoGUI would. Reports a fixed position…, _RecordingMouse, The list is read live from the registry, so a tool registered after the command…

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 252 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 256 - "LLMEngine"
Cohesion: 0.11
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 258 - "Direction"
Cohesion: 0.12
Nodes (33): Direction, How a base-timeframe directional read sits against the higher timeframe. A…, Directional bias of a signal or piece of evidence., TimeframeAlignment, Directional bias implied by the posture (SIDEWAYS for neutral)., The read's headline direction is the higher-timeframe trend (context)., Directional bias implied by the regime (SIDEWAYS for a range)., Fold the checks into a verdict. Insufficient-evidence gates come first: without… (+25 more)

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2958 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `enums.py` to `LLMEngine`, `ServiceContainer`, `define`, `ContextBuilder`, `WindowController`, `ceo_agent_service.py`, `VerificationResult`, `PaddleOCRProvider`, `executor.py`, `voice/service.py`, `Agent`, `Message`, `cli/main.py`, `TextToSpeech`, `Bootstrapper`, `CommandRegistry`, `PolicyEngine`, `ProcessController`, `CLIRuntime`, `MouseController`, `agents/state.py`, `policy.py`, `AgentCore`, `TraceEvent`, `TerminalService`, `DesktopError`, `LLMProvider`, `ProcessService`, `KeyboardService`, `Application`, `HUDProcess`, `BrowserProvider`, `YOLOProvider`, `LifecycleManager`, `FasterWhisperSTT`, `RecoveryRunner`, `agents/core.py`, `ErrorContext`, `VoiceConfig`, `ScreenController`, `ClipboardController`, `Provenance`, `setup_logging`, `_CountingExecutor`, `VoiceState`, `vision/tools.py`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `bootstrapper.py` to `ServiceContainer`, `Direction`, `TestRegisteredToolSurface`, `test_orchestration.py`, `AutomationEngine`, `test_multi_timeframe.py`, `VerificationResult`, `test_ceo_agent.py`, `executor.py`, `test_backtest.py`, `DivergenceService`, `test_news.py`, `Bootstrapper`, `PolicyEngine`, `test_critic.py`, `test_performance.py`, `test_fundamentals.py`, `policy.py`, `indicators/core.py`, `test_portfolio.py`, `OpenAICompatibleProvider`, `OpenCVTemplateProvider`, `DesktopError`, `test_ceo.py`, `PredictionOutcomeStatus`, `test_prediction_evaluator.py`, `main`, `Step`, `enums.py`, `test_calibration_history.py`, `InMemoryPredictionStore`, `Instrument`, `FakeProvider`, `PredictionRecord`, `setup_logging`, `MarketRegime`, `vision/tools.py`, `MarketData`, `make_market_data`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `Image` connect `Image` to `ErrorContext`, `OpenCVTemplateProvider`, `MSSScreen`, `make_vision_service`, `VisionError`, `VerificationResult`, `PaddleOCRProvider`, `main`, `wire`, `VisionService`, `YOLOProvider`, `vision/tools.py`, `FrameCache`, `TextBlock`, `Detection`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 201 inferred relationships involving `Direction` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Direction` has 201 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `Instrument` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Instrument` has 93 INFERRED edges - model-reasoned connections that need verification._