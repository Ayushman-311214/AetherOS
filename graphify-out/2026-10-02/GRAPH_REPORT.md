# Graph Report - AetherOS  (2026-10-02)

## Corpus Check
- 477 files · ~369,526 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 9247 nodes · 23709 edges · 270 communities (241 shown, 16 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 2403 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a356bfc6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- memory/domain/__init__.py
- Image
- answer
- define
- bootstrapper.py
- ContextBuilder
- ContextBuilder
- services/manager.py
- Scene
- WindowController
- AutomationEngine
- AgentState
- MultiTimeframeService
- VerificationResult
- TextBlock
- AgentPlanner
- .from_provider
- VoiceConfig
- trading/tools.py
- get_llm_tools
- Message
- Memory
- PlannedAction
- Event
- TraceRecorder
- test_news.py
- .record
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- FakeHUDProcess
- asyncio
- PolicyEngine
- VoiceService
- test_wiring.py
- asyncio
- test_voice_agent_e2e.py
- ProcessController
- ErrorContext
- test_critic.py
- HUDWindow
- ApplicationService
- test_yahoo_provider.py
- cli/main.py
- FileController
- MouseController
- AgentError
- test_performance.py
- CLIUI
- Win32Window
- wire
- VisionService
- policy.py
- test_cli_agent.py
- indicators/core.py
- _RecordingProvider
- TraceEvent
- FrameCache
- test_grounding_tools.py
- ToolCall
- EventBus
- TerminalService
- grounding/engine.py
- PlaywrightProvider
- TaskManager
- resolve_level
- automation/engine.py
- ClipboardService
- LiveTraceUI
- VisionProvider
- trading/domain/enums.py
- FakeLLMProvider
- asyncio
- tool
- test_ceo.py
- LLMProvider
- MemoryProvider
- calibration.py
- ProcessService
- MouseService
- test_prediction_evaluator.py
- MemoryRepository
- KeyboardService
- WindowService
- HUDConfig
- YOLOProvider
- VectorIndex
- BrowserProvider
- PortfolioRiskService
- LifecycleManager
- events/events.py
- SpeechToText
- RecoveryRunner
- TestRegistration
- InMemoryPredictionStore
- BrowserService
- parse_llm_response
- KnowledgeGraph
- asyncio
- SQLiteMemoryProvider
- SourceTier
- asyncio
- ClipboardController
- _state
- VisionError
- FakeProvider
- ScreenService
- PredictionRecord
- PyAutoGuiKeyboard
- FakeKeyboard
- window/tools.py
- setup_logging
- ExecutionConfig
- VoiceState
- event_calendar.py
- test_regime.py
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
- agents/state.py
- _settings
- Application
- ToolCommandService
- commands
- TestRegisteredToolSurface
- test_calendar.py
- test_interface_contracts.py
- test_orchestration.py
- test_agent_observation.py
- vision/main.py
- ceo_agent_service.py
- TestWellFormedCalls
- test_yahoo_calendar_provider.py
- test_analyze_command.py
- SapiTTS
- test_ceo_agent.py
- executor.py
- yahoo_calendar_provider.py
- MemoryScorer
- _FakeMouse
- Agent
- test_backtest.py
- test_agent_policy.py
- test_agent_e2e.py
- DivergenceService
- RenderContext
- LogisticRegression
- make_vision_service
- StageTimings
- FilePredictionStore
- Detection
- PyAutoGuiMouse
- SQLiteDatabase
- HUDService
- Renderer
- test_yahoo_fundamentals_provider.py
- _service
- text_match_score
- application/tools.py
- ServiceContainer
- test_input.py
- .from_dict
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
- test_prediction_store.py
- verification/tools.py
- TestToolsCommand
- rich_tools
- Procedure
- WorkingMemory
- _RecordingMouse
- ToolExecutionCoordinator
- OpenAICompatibleProvider
- test_vision_engine.py
- AetherOS
- test_monitoring.py
- .parse
- AnomalyService
- ._format_trading_report
- calibration_audit.py
- test_explanation.py
- _one
- automation/tools.py
- ._run
- Application
- get_logger
- test_calibration_history.py
- MSSScreen
- test_ui.py
- ProbabilityService
- memory/tools.py
- agents/core.py
- emit_trace
- test_prediction.py
- vision/controller.py
- ParsedResponse
- NullTTS
- test_evidence.py
- test_analysis_service.py
- test_monitoring_scheduler.py
- Instrument
- ToolDiscovery
- spatial.py
- .test_a_finished_run_executes_nothing
- NullActivator
- TestCallIdentifiers
- test_anomaly.py
- test_breakout.py
- parametrize
- MemoryConsolidator
- MemoryLifecycle
- _started
- TestPromptCursor
- test_historical_analogue.py
- main
- test_macro.py
- CEOBrief
- _RecordingMouse
- PlattScaler
- trading/conftest.py
- TraceCollector
- TestEveryToolModuleImports
- workflow_believer_run.py
- .download
- test_divergence.py
- LLMEngine
- TestServiceInitialisation
- test_risk.py
- ._ask
- .evaluate
- prediction.py
- ._bootstrap_browser
- .speak
- .start
- AgentLoopResult
- .registry
- .test_registry_fixture_is_isolated
- .test_the_hooks_reach_the_loop

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 242 edges
2. `Image` - 183 edges
3. `Instrument` - 177 edges
4. `tool()` - 159 edges
5. `AgentState` - 138 edges
6. `Direction` - 124 edges
7. `get_logger()` - 122 edges
8. `Provenance` - 108 edges
9. `define()` - 106 edges
10. `EventBus` - 105 edges

## Surprising Connections (you probably didn't know these)
- `test_from_dict_rejects_unknown_field()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_from_dict_requires_source()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_memory_rejects_blank_content()` --calls--> `Memory`  [INFERRED]
  tests/memory/test_memory_storage.py → src/aetheros/memory/domain/memory.py
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (270 total, 16 thin omitted)

### Community 0 - "memory/domain/__init__.py"
Cohesion: 0.05
Nodes (56): int, MemoryImportance, OutcomeStatus, Result of an episode / action / recovery attempt (spec Phase 9/11)., Where a memory originated -- its provenance channel (spec Rule 8)., How much a memory matters, as an ordered scale (spec Phase 13/21).…, Importance mapped onto [0, 1] for scoring., SourceType (+48 more)

### Community 1 - "Image"
Cohesion: 0.03
Nodes (27): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+19 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (48): Executes registered AetherOS tools., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes(), asyncio (+40 more)

### Community 4 - "bootstrapper.py"
Cohesion: 0.03
Nodes (81): Register the deterministic Trading Intelligence core. Self-contained: it…, get_settings(), Singleton Settings object., Resolve a user/tool string to a Timeframe, raising ValueError if unknown., MonitoringReport, Any, One bounded monitoring sweep: resolved outcomes + their aggregate., AnalysisService (+73 more)

### Community 5 - "ContextBuilder"
Cohesion: 0.06
Nodes (38): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call(), asyncio, ContextBuilder (+30 more)

### Community 6 - "ContextBuilder"
Cohesion: 0.05
Nodes (42): _clamp(), ContextBuilder, _describe_call(), _describe_result(), IterationInfo, Any, Observation, Agent context assembly. One :class:`AgentContext` is everything the model needs… (+34 more)

### Community 7 - "services/manager.py"
Cohesion: 0.06
Nodes (51): datetime, Internal time helpers shared across memory modules (tz-aware UTC)., utcnow(), utcnow_iso(), Resolved memory configuration (spec Phase 23). A single immutable snapshot of…, confidence_band(), MemoryScope, MemoryStatus (+43 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (38): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+30 more)

### Community 9 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (36): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, Build a workflow from a plain dict, as ``run_workflow`` receives it., Calls, engine(), _failing_state(), _matching_state(), asyncio (+28 more)

### Community 11 - "AgentState"
Cohesion: 0.04
Nodes (25): AgentState, AgentStatus, Enum, str, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,… (+17 more)

### Community 12 - "MultiTimeframeService"
Cohesion: 0.17
Nodes (13): How a base-timeframe directional read sits against the higher timeframe. A…, TimeframeAlignment, MultiTimeframeService, Deterministic base-vs-higher-timeframe confirmation read., The higher timeframe used when a caller names none., _analyse(), _mtf(), asyncio (+5 more)

### Community 13 - "VerificationResult"
Cohesion: 0.04
Nodes (54): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Verification — reading state back after a desktop action. The public surface is…, Any, Enum, str, The result contract every desktop tool returns. Before this module every…, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not… (+46 more)

### Community 14 - "TextBlock"
Cohesion: 0.03
Nodes (50): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, PaddleOCRProvider (+42 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.04
Nodes (58): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, PlannerConfig, The limit actually applied, once parallelism is accounted for., Decides the next action for one iteration of an agent run. Holds the provider…, What the planner is willing to accept from one response. All three defaults are…, _answer() (+50 more)

### Community 16 - ".from_provider"
Cohesion: 0.24
Nodes (8): Assemble a core from a provider and, optionally, its collaborators. The…, _fake_mouse(), _is_ordered_subsequence(), Any, asyncio, Bind the ``MouseService`` the tool resolves to a fixed-position backend., True if every item of ``expected`` occurs in ``actual`` in order., TestMousePositionPipelineE2E

### Community 17 - "VoiceConfig"
Cohesion: 0.04
Nodes (65): Future, AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Base exception for all voice-subsystem errors. Examples: - Microphone…, The wake-word engine failed to initialize or detect. (+57 more)

### Community 18 - "trading/tools.py"
Cohesion: 0.05
Nodes (82): MonitoringScheduler, A cancellable, opt-in loop that repeats the bounded monitoring sweep., Start the loop if enabled and not already running. Returns started?., Cancel the loop and await its clean exit (idempotent)., Run a single sweep immediately (bypasses the schedule)., _analysis(), analyze_fundamentals(), analyze_instrument() (+74 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "Message"
Cohesion: 0.06
Nodes (53): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window… (+45 more)

### Community 21 - "Memory"
Cohesion: 0.05
Nodes (27): Memory, One stored memory -- the universal record (spec Phase 2/3). Mutable on purpose:…, MemoryManager, Any, Create and persist a memory from primitive fields (spec Phase 4)., Persist a pre-built Memory, honouring the retention policy., Hybrid, explainable retrieval (spec Phase 7)., Convenience alias for a plain semantic+lexical search. (+19 more)

### Community 22 - "PlannedAction"
Cohesion: 0.03
Nodes (40): _as_tool_call(), Normalise what the caller handed over into a :class:`ToolCall`. A ``tool_call``…, PlannedAction, PlanResult, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that… (+32 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (59): Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM. (+51 more)

### Community 24 - "TraceRecorder"
Cohesion: 0.12
Nodes (14): Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent., TraceRecorder (+6 more)

### Community 25 - "test_news.py"
Cohesion: 0.05
Nodes (58): Map a 0..1 score to a band. This is a label, not a calibrated probability., NewsItem, Any, Content-addressed id: same headline from the same source -> same id.…, A single sourced headline as a provider returned it (no interpretation)., A news item paired with the deterministic sentiment read it was given., ScoredNewsItem, _stable_id() (+50 more)

### Community 26 - ".record"
Cohesion: 0.18
Nodes (11): LevelCallback, _normalize_level(), Any, ndarray, Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is…, Root-mean-square amplitude of a PCM block. (+3 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.07
Nodes (9): Bootstrapper, Coordinates application startup and shutdown. The bootstrapper is responsible…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Shutdown subsystems in reverse order., The running HUD service, or None when the overlay is not up., Build the YOLO detector when its package and weights are both present. Returns…, The running voice service, or None when voice is not up. (+1 more)

### Community 28 - "DesktopError"
Cohesion: 0.09
Nodes (22): DesktopError, Base exception for all desktop automation errors. Examples: - Mouse movement…, PsutilProcess, Any, Path, psutil process backend. Two safety rules are enforced here, in the backend,…, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle… (+14 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.05
Nodes (25): CommandHandler, CommandRegistry, Scan a watchlist and rank it by directional signal for a human -- no LLM…, Register a CLI command., Render a watchlist-scan dict as an honest, ranked plain-text table., Risk-budget a basket of trades for a human -- no LLM involved (spec section 5,…, Execute a parsed command., Render a portfolio-risk plan dict as honest, plain terminal text. (+17 more)

### Community 31 - "FakeHUDProcess"
Cohesion: 0.08
Nodes (13): process(), Fixtures for the HUD tests. The process double lives in…, A HUD child process that never launches anything., FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code. (+5 more)

### Community 32 - "asyncio"
Cohesion: 0.07
Nodes (26): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, EnvelopeResult, _ocr_with(), Any (+18 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.05
Nodes (31): PolicyConfig, Any, Policy configuration: the rules the engine evaluates against. Deliberately…, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyDecision, PolicyEvaluation, Any (+23 more)

### Community 34 - "VoiceService"
Cohesion: 0.06
Nodes (22): Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,… (+14 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 36 - "asyncio"
Cohesion: 0.08
Nodes (12): make_fake_detector(), asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestDetectObjects, TestFindTemplate (+4 more)

### Community 37 - "test_voice_agent_e2e.py"
Cohesion: 0.07
Nodes (22): Captured microphone audio., Recording, Records what would have been spoken. The test double for speech output: it…, RecordingTTS, _agent_reasoner(), _BlockingReasoner, _CountingExecutor, _FailingTTS (+14 more)

### Community 38 - "ProcessController"
Cohesion: 0.07
Nodes (18): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+10 more)

### Community 39 - "ErrorContext"
Cohesion: 0.06
Nodes (37): Exception, BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,… (+29 more)

### Community 40 - "test_critic.py"
Cohesion: 0.11
Nodes (106): _analysis(), _anomaly(), _backtest(), _breakout(), _calendar(), _divergence(), _evidence(), _fundamentals() (+98 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.12
Nodes (21): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+13 more)

### Community 43 - "test_yahoo_provider.py"
Cohesion: 0.36
Nodes (17): _chart_payload(), _ok_handler(), _provider(), asyncio, YahooMarketDataProvider: the first real market-data adapter. These tests are…, Build a Yahoo /v8/finance/chart-shaped JSON payload., test_all_null_bars_become_insufficient_data(), test_drops_null_trailing_bar() (+9 more)

### Community 44 - "cli/main.py"
Cohesion: 0.14
Nodes (10): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…, CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->… (+2 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 47 - "AgentError"
Cohesion: 0.05
Nodes (30): Accept a member or its name; reject anything else. An unknown source is…, ErrorRecord, new_state_id(), Any, BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Finish the run unsuccessfully, recording the unrecoverable error. (+22 more)

### Community 48 - "test_performance.py"
Cohesion: 0.22
Nodes (23): _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes., _resolved(), _service() (+15 more)

### Community 49 - "CLIUI"
Cohesion: 0.08
Nodes (14): CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI. (+6 more)

### Community 50 - "Win32Window"
Cohesion: 0.07
Nodes (24): A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Any, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an… (+16 more)

### Community 51 - "wire"
Cohesion: 0.07
Nodes (27): executor(), asyncio, fixture, Path, Tests for the vision tools and their registry integration. These exercise the…, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in… (+19 more)

### Community 52 - "VisionService"
Cohesion: 0.06
Nodes (26): High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService (+18 more)

### Community 53 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 54 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 55 - "indicators/core.py"
Cohesion: 0.05
Nodes (62): adx(), _as_float_array(), atr(), bollinger(), ema(), last_finite(), macd(), _nan_prefix() (+54 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - "TraceEvent"
Cohesion: 0.07
Nodes (44): Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, TraceSpan, _default_stage(), Enum, str, The trace event vocabulary. One concrete :class:`TraceEvent` class (not a class…, One observed moment in a run, safe to log and to persist. Only observable, log-… (+36 more)

### Community 58 - "FrameCache"
Cohesion: 0.12
Nodes (15): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, _Clock, _make_capture(), asyncio, Tests for the short-lived screen-frame cache. The clock is injected so time… (+7 more)

### Community 59 - "test_grounding_tools.py"
Cohesion: 0.14
Nodes (14): _block(), executor(), asyncio, fixture, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received…, Register the services the grounding tools resolve, with fake edges. Mirrors… (+6 more)

### Community 60 - "ToolCall"
Cohesion: 0.08
Nodes (24): Record the request, before anything is checked or run. Ordered first on…, Record a call the model asked for. Accepts the parse layer's :class:`ToolCall`…, LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls. (+16 more)

### Community 61 - "EventBus"
Cohesion: 0.08
Nodes (32): EventHandler, InteractionGateway, Submit a goal to the shared agent, tagged with its front end., EventBus, Central event bus for AetherOS. Features: - Sync + Async handlers - Multiple…, Register an event handler., Publish an event. Every subscriber receives the event., Set the global EventBus instance. This should be called once during application… (+24 more)

### Community 62 - "TerminalService"
Cohesion: 0.14
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 63 - "grounding/engine.py"
Cohesion: 0.05
Nodes (33): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+25 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 65 - "TaskManager"
Cohesion: 0.06
Nodes (37): Any, TaskContext, InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError (+29 more)

### Community 66 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 67 - "automation/engine.py"
Cohesion: 0.07
Nodes (35): _append_recovery_detail(), _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran… (+27 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "LiveTraceUI"
Cohesion: 0.11
Nodes (13): Panel, LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole (+5 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "trading/domain/enums.py"
Cohesion: 0.03
Nodes (86): Any, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, _utcnow(), VolumeAnalysis, Assertion, Confidence, DataQualityStatus (+78 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "tool"
Cohesion: 0.16
Nodes (28): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+20 more)

### Community 75 - "test_ceo.py"
Cohesion: 0.20
Nodes (15): _FakeLLM, Any, asyncio, TradingCEOService: the LLM narration layer over the deterministic core. These…, A deterministic, offline stand-in for an LLMProvider. It records the messages…, _service(), test_brief_embeds_the_report_and_narrates_via_llm(), test_empty_llm_response_degrades_to_the_deterministic_summary() (+7 more)

### Community 76 - "LLMProvider"
Cohesion: 0.07
Nodes (15): LLMProvider, ABC, Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources. (+7 more)

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "calibration.py"
Cohesion: 0.24
Nodes (14): accuracy(), brier_score(), _clip01(), expected_calibration_error(), log_loss(), ndarray, Probability calibration (Platt scaling) and honest calibration metrics. A raw…, Binary cross-entropy; lower is better. (+6 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 81 - "test_prediction_evaluator.py"
Cohesion: 0.28
Nodes (24): _Bus, _evaluator(), _market_data(), asyncio, datetime, The deterministic prediction-outcome evaluator (spec sections 6, 16, 29). These…, A minimal event bus that records what the evaluator publishes., _record() (+16 more)

### Community 82 - "MemoryRepository"
Cohesion: 0.06
Nodes (34): Memory persistence layer (spec Phase 2): SQLite database + repository., MemoryRepository, Any, Count of live memories by type -- an observability signal (Phase 22)., Bump access_count/last_accessed_at and append an access audit row., Return the structurally-matching candidate pool for a query. This is…, Every memory -- used by decay and consolidation sweeps., Wipe every memory table (user 'clear all' / tests). (+26 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 85 - "HUDConfig"
Cohesion: 0.03
Nodes (47): IO, Popen, main(), Standalone entry point. Exists so the HUD can be developed and visually…, _as_bool(), _as_float(), _as_int(), _as_text() (+39 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (16): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Tests for the vision providers' performance-oriented internals. These pin the… (+8 more)

### Community 87 - "VectorIndex"
Cohesion: 0.06
Nodes (21): EmbeddingProvider, ABC, ndarray, Embedding provider abstraction (spec Phase 5). The vector layer must not be…, Turns text into a fixed-dimension, L2-normalised vector., Stable identifier recorded alongside each stored vector., Length of every vector this provider emits., Embed one string. Returns a float32 array of length ``dimension``. (+13 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.05
Nodes (18): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page title., Return the current page URL. (+10 more)

### Community 89 - "PortfolioRiskService"
Cohesion: 0.12
Nodes (22): PortfolioCandidate, PortfolioPosition, PortfolioRiskPlan, Any, datetime, Portfolio-risk value objects. Where…, One candidate trade feeding the allocator: its directional risk geometry., A candidate after allocation: its size, risk and notional (or why not). (+14 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "events/events.py"
Cohesion: 0.21
Nodes (11): get_event_bus(), publish(), Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., clear_subscribers(), get_subscribers(), Any, Decorator used to register an event handler. Example:… (+3 more)

### Community 92 - "SpeechToText"
Cohesion: 0.05
Nodes (27): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+19 more)

### Community 93 - "RecoveryRunner"
Cohesion: 0.10
Nodes (14): Any, Recovery — bounded self-healing between step attempts. A retry that changes…, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once. (+6 more)

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "InMemoryPredictionStore"
Cohesion: 0.22
Nodes (19): InMemoryPredictionStore, Process-local reference store. Deterministic, dependency-free, non-durable.…, _FakeEvaluator, asyncio, The prediction track-record service: the on-demand composition of the audit…, A minimal, hand-built recorded prediction with a fixed content id., A RESOLVED, optionally-graded outcome for the fake evaluator to hand back., Returns a pre-baked outcome per record id; raises for flagged ids. (+11 more)

### Community 96 - "BrowserService"
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "parse_llm_response"
Cohesion: 0.19
Nodes (6): parse_llm_response(), Normalise a provider tool-call response. Never raises. Accepts the shape…, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn., TestContent

### Community 98 - "KnowledgeGraph"
Cohesion: 0.07
Nodes (20): DiGraph, Entity, Any, datetime, Semantic-memory value objects: entities and the relationships between them.…, A node in the knowledge graph (spec Phase 6)., Canonical lookup key: type + normalised name (graph dedup)., A typed edge between two entities (spec Phase 6). ``valid_from`` / ``valid_to``… (+12 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "SQLiteMemoryProvider"
Cohesion: 0.06
Nodes (19): MemoryConfig, Path, Immutable, fully-resolved memory settings., A minimal config for tests / embedded use. Everything enabled, pointed at…, build_embedding_provider(), Select an embedding provider from configuration (spec Phase 5/23). Only the…, AetherOS Memory subsystem (CLAUDE.md section 15; implementation spec Phases…, Any (+11 more)

### Community 101 - "SourceTier"
Cohesion: 0.03
Nodes (63): Supported candle timeframes., Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, Timeframe, FundamentalSnapshot, Any, Names of the metrics that were actually reported (non-None)., Raw sourced company financials (no interpretation). Missing metric = None. (+55 more)

### Community 102 - "asyncio"
Cohesion: 0.07
Nodes (26): bus(), fake_process(), make_service(), fixture, A bus isolated from the process-wide publisher., The double's class, for tests that need a differently configured one., Build an unstarted service over a fake process., A started service, stopped again on teardown. `start()` creates the pump task,… (+18 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - "_state"
Cohesion: 0.11
Nodes (16): Any, One faithful view for auditing, one redacted view for the sinks., A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools. (+8 more)

### Community 105 - "VisionError"
Cohesion: 0.10
Nodes (12): Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the… (+4 more)

### Community 106 - "FakeProvider"
Cohesion: 0.30
Nodes (15): FakeProvider, A controllable, clearly-synthetic provider for service tests. Unlike the mock…, asyncio, MarketDataService: caching, validation, freshness and honest error typing. This…, _service(), test_fresh_series_is_ok(), test_invalid_symbol_raises(), test_non_positive_limit_raises() (+7 more)

### Community 107 - "ScreenService"
Cohesion: 0.06
Nodes (28): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms., ndarray, Path (+20 more)

### Community 108 - "PredictionRecord"
Cohesion: 0.10
Nodes (10): PredictionRecord, Any, A prediction resting on mock data can never be treated as reliable., Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, The auditable section-8 contract for one produced trading report., Persist ``record`` and return its id. Idempotent on the id., Return the recorded prediction with this id, or ``None`` if unknown., Return recorded predictions newest-first. Optionally filtered to one… (+2 more)

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

### Community 113 - "ExecutionConfig"
Cohesion: 0.15
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 114 - "VoiceState"
Cohesion: 0.10
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 115 - "event_calendar.py"
Cohesion: 0.08
Nodes (21): EventType, MarketEvent, Any, datetime, Enum, str, Event / economic-calendar value objects (spec sections 5, 9, 26). The calendar…, Signed days from ``reference`` to the event (negative = already past). (+13 more)

### Community 116 - "test_regime.py"
Cohesion: 0.23
Nodes (16): _FakeBus, asyncio, Market-regime detection: deterministic trending / ranging / volatile reads.…, Records published events; duck-typed stand-in for the EventBus., _service(), test_clean_downtrend_is_trending_down(), test_clean_uptrend_is_trending_up(), test_detect_emits_event_when_bus_wired() (+8 more)

### Community 117 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 118 - "test_agent_execution.py"
Cohesion: 0.09
Nodes (29): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+21 more)

### Community 119 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 120 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 121 - "vision/tools.py"
Cohesion: 0.14
Nodes (33): get_frame_cache(), Short-lived screen-frame cache. A desktop agent frequently runs several vision…, Process-wide frame cache, sized from the shared settings object. Built once…, Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), click_grounded_target(), _engine(), ground_target() (+25 more)

### Community 122 - "MarketData"
Cohesion: 0.04
Nodes (29): SignalFn, Any, One walk-forward prediction scored against its realised forward return., TradeOutcome, Map a benchmark's regime to a broad-market risk posture. A trending-up market…, MarketData, ndarray, Serialise for a tool result. By default the full candle series is *not*… (+21 more)

### Community 123 - "make_market_data"
Cohesion: 0.34
Nodes (13): make_market_data(), Build a MarketData from a close series with plausible OHLC/volume., RelativeStrengthService: deterministic instrument-vs-benchmark strength. These…, _service(), test_clear_laggard_is_down(), test_clear_outperformer_is_up_and_reliable(), test_is_deterministic(), test_lookback_override_is_respected() (+5 more)

### Community 125 - ".create"
Cohesion: 0.07
Nodes (20): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,… (+12 more)

### Community 126 - "ExecutionStatus"
Cohesion: 0.25
Nodes (5): ExecutionStatus, str, How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 127 - "agents/state.py"
Cohesion: 0.04
Nodes (41): AgentExecutionResult, ExecutionBatch, _failure(), Any, A failure in the engine's own currency, for a call the engine never saw.…, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., Turned away by this layer, without the engine being asked. (+33 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "Application"
Cohesion: 0.22
Nodes (5): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application.

### Community 130 - "ToolCommandService"
Cohesion: 0.11
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 132 - "TestRegisteredToolSurface"
Cohesion: 0.08
Nodes (13): fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations… (+5 more)

### Community 133 - "test_calendar.py"
Cohesion: 0.19
Nodes (30): EventImpact, How disruptive an event is expected to be. A label, never a probability., MockCalendarProvider, A reproducible, clearly-labelled synthetic event-calendar source., _event(), FakeCalendarProvider, asyncio, Deterministic event / economic-calendar tests (spec sections 5, 9, 21, 28). Two… (+22 more)

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "test_orchestration.py"
Cohesion: 0.16
Nodes (33): _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_report_fuses_anomaly_as_advisory_but_stays_no_trade(), test_report_fuses_breakout_as_advisory_but_stays_no_trade(), test_report_fuses_calendar_as_advisory_but_stays_no_trade(), test_report_fuses_divergence_as_advisory_but_stays_no_trade(), test_report_fuses_fundamentals_as_advisory_but_stays_no_trade() (+25 more)

### Community 136 - "test_agent_observation.py"
Cohesion: 0.04
Nodes (57): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``…, Observe browser state. The seam the task asks for: there is no browser-state… (+49 more)

### Community 137 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

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
Cohesion: 0.06
Nodes (28): Speech synthesis or audio playback failed., TextToSpeechError, decode_mp3(), decode_wav(), _frame_to_mono(), _load_av(), Any, ndarray (+20 more)

### Community 143 - "test_ceo_agent.py"
Cohesion: 0.16
Nodes (18): _Def, _FakeExecutor, _FakeRegistry, Any, asyncio, CEOAgentService: the Trading CEO as a bounded, fenced tool-calling loop. A…, Returns canned results per tool name; records what was executed., Yields a fixed sequence of raw replies, one per generate() call. (+10 more)

### Community 144 - "executor.py"
Cohesion: 0.05
Nodes (40): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Agent planner. One responsibility: ``GOAL -> the next action``. The planner…, Exception, ToolError, is_unconstrained(), public_parameters(), Any (+32 more)

### Community 145 - "yahoo_calendar_provider.py"
Cohesion: 0.17
Nodes (8): CalendarError, An event/economic-calendar lookup could not be produced from the inputs., AsyncClient, datetime, Yahoo Finance event-calendar provider. The first *real* event-calendar source…, Extract unix-timestamp dates from a calendarEvents field. Yahoo carries a date…, Real scheduled corporate events from Yahoo's public quoteSummary endpoint., YahooCalendarProvider

### Community 146 - "MemoryScorer"
Cohesion: 0.10
Nodes (15): MemoryResult, Any, Per-memory, per-signal justification for a retrieval (Rule 6, Phase 7). Each…, A retrieved memory paired with its ranking explanation., RetrievalExplanation, MemoryRetriever, Memories referencing the query's entities (and their graph neighbours)., Memories joined to a candidate by a typed memory_link (e.g. recovery). (+7 more)

### Community 148 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 149 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 150 - "test_agent_policy.py"
Cohesion: 0.15
Nodes (21): _call(), _coordinator(), _CountingExecutor, executor(), move_mouse(), Any, asyncio, fixture (+13 more)

### Community 151 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 152 - "DivergenceService"
Cohesion: 0.18
Nodes (11): DivergenceService, ndarray, Indices that are a strict local min (low) / max (high) over +/-window. Returns…, Classify regular divergence over the two most recent pivots. For lows…, Pick the stronger of a detected bullish/bearish divergence. If both fired, the…, Deterministic price-vs-RSI regular-divergence read over candles., test_fewer_than_two_pivots_is_none(), test_no_divergence_when_price_and_oscillator_agree() (+3 more)

### Community 153 - "RenderContext"
Cohesion: 0.06
Nodes (45): QFont, QLinearGradient, QPointF, Layer, ABC, Whether this layer should draw at all this frame., One element of the overlay, drawn back to front. Layers are stateless with…, CoreLayer (+37 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.23
Nodes (7): LogisticRegression, ndarray, Deterministic logistic regression in pure numpy. A small, fully reproducible…, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "make_vision_service"
Cohesion: 0.21
Nodes (15): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+7 more)

### Community 156 - "StageTimings"
Cohesion: 0.12
Nodes (10): Accumulated per-stage timings for one vision request. A plain name ->…, Times named stages when profiling is enabled, and is a no-op otherwise.…, Time the wrapped block. Used around an ``await`` -- ``with…, StageTimings, VisionProfiler, Tests for the opt-in vision profiler. The contract these pin, from §11 of the…, TestDisabledProfilerIsANoop, TestEnabledProfilerRecords (+2 more)

### Community 157 - "FilePredictionStore"
Cohesion: 0.19
Nodes (14): FilePredictionStore, Path, A durable, append-only JSON Lines implementation of the same port. Each…, Populate the in-memory index from the file (once). Caller holds lock., asyncio, FilePredictionStore: the durable JSON Lines prediction-audit store. These pin…, Build a minimal, valid PredictionRecord with a chosen id., _record() (+6 more)

### Community 158 - "Detection"
Cohesion: 0.07
Nodes (11): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., test_vision_observation_averages_confidence_and_serialises_readings() (+3 more)

### Community 159 - "PyAutoGuiMouse"
Cohesion: 0.07
Nodes (9): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., Return the current desktop subsystem status., status(), PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController., Return whether the process backend is available. (+1 more)

### Community 160 - "SQLiteDatabase"
Cohesion: 0.17
Nodes (10): Connection, MemoryStorageError, A persistence operation (SQLite read/write/migration) failed., Any, Path, Row, Run several (sql, params) statements in one committed transaction., Owns the SQLite connection and keeps the schema migrated. (+2 more)

### Community 161 - "HUDService"
Cohesion: 0.05
Nodes (25): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+17 more)

### Community 162 - "Renderer"
Cohesion: 0.09
Nodes (12): QPixmap, GlowCache, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour., Exception, QPainter, Draw one frame. Returns how long it took, in seconds. (+4 more)

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

### Community 167 - "ServiceContainer"
Cohesion: 0.05
Nodes (33): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, EchoReasoner, Any (+25 more)

### Community 170 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 171 - ".from_dict"
Cohesion: 0.12
Nodes (12): MemoryLink, new_id(), _parse_dt(), Any, datetime, Record that this memory was retrieved (feeds recency/frequency)., Whether the memory has passed its TTL. PERMANENT memories never expire…, Timezone-aware current UTC instant (the whole layer is tz-aware). (+4 more)

### Community 172 - "CalibrationHistoryService"
Cohesion: 0.20
Nodes (8): CalibrationAudit, Realised-calibration measurement over the accumulated prediction history., CalibrationHistoryService, ndarray, Fit a recalibration map on history and validate it out-of-sample. Time-orders…, A resolved, non-mock, reliable outcome carrying a calibrated P(up)., Fit a secondary Platt map p_corrected = sigmoid(a*p + b) on history. Returns…, Measures realised calibration over the accumulated outcome history.

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - "test_yahoo_news_provider.py"
Cohesion: 0.40
Nodes (18): _news_item(), _ok_handler(), _provider(), asyncio, YahooNewsProvider: the first real news adapter. These tests are fully…, _search_payload(), test_duplicate_story_is_deduped(), test_empty_news_list_is_honest_no_news_not_an_error() (+10 more)

### Community 176 - "ToolRegistry"
Cohesion: 0.06
Nodes (49): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, Any, asyncio, Tests for the agent core loop. ``AgentCore`` is the driver that turns a goal…, The real engine, counting how often it was actually asked to run a tool.… (+41 more)

### Community 177 - "test_fundamentals.py"
Cohesion: 0.24
Nodes (22): FakeFundamentalsProvider, asyncio, Deterministic fundamental-analysis tests (spec sections 5, 9, 21, 28). Two…, A controllable, clearly-synthetic snapshot stamped a non-mock tier., Hands back exactly the snapshot the test built; non-mock so it can be reliable., _service(), _snapshot(), test_mock_provider_is_deterministic() (+14 more)

### Community 178 - "PredictionOutcome"
Cohesion: 0.06
Nodes (31): PredictionOutcome, Any, Rebuild an outcome from its :meth:`to_dict` form (durable read-back). The…, The auditable result of checking one prediction against later market data., A resolved, directional outcome that was actually graded hit/miss., FileOutcomeStore, InMemoryOutcomeStore, Path (+23 more)

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
Cohesion: 0.08
Nodes (45): executor(), asyncio, fixture, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_macro_context_tool_is_labelled_mock(), test_analyze_market_structure_tool() (+37 more)

### Community 183 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 184 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 185 - "test_prediction_store.py"
Cohesion: 0.24
Nodes (17): _Bus, _orchestrator(), asyncio, The prediction audit store: interface, in-memory reference impl, and the…, A minimal event bus that records what the orchestrator publishes., _report(), test_announced_prediction_matches_the_recorded_one(), test_orchestrator_records_prediction_when_store_wired() (+9 more)

### Community 186 - "verification/tools.py"
Cohesion: 0.15
Nodes (17): _parse_condition(), MatchMode, parse_mode(), parse_region(), Any, Enum, str, Parse a caller-supplied comparison mode. Shared by the ``verify_action`` tool… (+9 more)

### Community 187 - "TestToolsCommand"
Cohesion: 0.17
Nodes (3): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., TestToolsCommand

### Community 188 - "rich_tools"
Cohesion: 0.12
Nodes (19): boom(), check_playing(), click_element(), ground_target(), move_mouse(), open_browser(), fixture, Click an element, reporting success but changing nothing (test double). The… (+11 more)

### Community 189 - "Procedure"
Cohesion: 0.16
Nodes (9): Procedure, ProcedureStep, Any, datetime, Procedural-memory records: learned, reusable procedures (spec Phase 10). A…, One step in a procedure (spec Phase 10)., A learned, reusable procedure (spec Phase 10)., Confidence from evidence, not assertion (spec Phase 10/13). A Wilson-style… (+1 more)

### Community 190 - "WorkingMemory"
Cohesion: 0.15
Nodes (6): Any, A compact textual summary of the working set (for context assembly)., One entry in the working set., Bounded live context for one session (spec Phase 8)., WorkingItem, WorkingMemory

### Community 191 - "_RecordingMouse"
Cohesion: 0.11
Nodes (4): _fake_mouse(), Bind the ``MouseService`` the tool resolves to a recording controller.…, A ``MouseController`` sitting where PyAutoGUI would. Records every absolute…, _RecordingMouse

### Community 192 - "ToolExecutionCoordinator"
Cohesion: 0.10
Nodes (11): ContextBuilder, Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, One round, several calls: all answered, in order, one at a time. (+3 more)

### Community 193 - "OpenAICompatibleProvider"
Cohesion: 0.14
Nodes (6): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…, main()

### Community 194 - "test_vision_engine.py"
Cohesion: 0.13
Nodes (9): asyncio, skipif, Tests for the Vision Engine. Run with: pytest tests/vision/, test_opencv_provider_metadata(), test_paddleocr_provider_metadata(), test_yolo_provider_metadata(), TestTemplateMatching, TestTextBlock (+1 more)

### Community 205 - "test_monitoring.py"
Cohesion: 0.24
Nodes (13): _Bus, _FakeEvaluator, _outcome(), asyncio, The monitoring service: one bounded "Observe Result -> Evaluate" sweep. These…, _record(), _service_with(), test_empty_history_is_a_valid_quiet_sweep() (+5 more)

### Community 206 - ".parse"
Cohesion: 0.30
Nodes (13): Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``. Raises ValueError for an empty…, MockMarketDataProvider, A reproducible, clearly-labelled synthetic data source., asyncio, Mock market-data provider: reproducibility and honesty. The mock exists so the…, test_candle_count_matches_limit(), test_candles_are_deterministic_per_symbol(), test_different_symbols_differ() (+5 more)

### Community 207 - "AnomalyService"
Cohesion: 0.25
Nodes (5): AnomalyService, ndarray, z-score of the last element vs the prior ``used`` elements. Returns ``(z,…, Directional lean of the detected anomaly. A return outlier leans with the sign…, Deterministic last-bar statistical-outlier read over candles.

### Community 208 - "._format_trading_report"
Cohesion: 0.14
Nodes (7): Run one monitoring sweep for a human -- resolve the recorded predictions…, Render a monitoring-sweep dict as honest, plain terminal text., A 0-1 fraction as a percentage, or ``-`` when missing., One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.…, Run the deterministic trading pipeline for one instrument and render the…

### Community 209 - "calibration_audit.py"
Cohesion: 0.18
Nodes (7): CalibrationCorrection, Any, datetime, Calibration-audit value object. A :class:`CalibrationAudit` is the honest first…, A holdout-validated recalibration map ``p' = sigmoid(a*p + b)``. Derived from…, Correct a probability -- but only when trusted; otherwise unchanged., _utcnow()

### Community 210 - "test_explanation.py"
Cohesion: 0.21
Nodes (11): ExplanationService, Deterministic, read-only explanation of a composed trading report., Every evidence item the report carries, de-duplicated by content id. Order-…, _explain(), asyncio, ExplanationService: deterministic, read-only "why" over a trading report. These…, _service(), test_is_deterministic() (+3 more)

### Community 211 - "_one"
Cohesion: 0.15
Nodes (9): _one(), Parsing of provider tool-call responses. Everything the model emits is…, The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature., A tool message must carry a name, so a nameless call cannot be answered inside…, TestMalformedCalls (+1 more)

### Community 212 - "automation/tools.py"
Cohesion: 0.06
Nodes (32): main(), Run a workflow defined in a JSON file THROUGH the run_workflow tool. This…, describe_strategies(), Strategy name to description. Read by the ``run_workflow`` tool description and…, _build(), list_recovery_strategies(), Any, The automation tools — multi-step desktop work, exposed to the model. Three… (+24 more)

### Community 213 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 215 - "get_logger"
Cohesion: 0.02
Nodes (121): BaseSettings, Settings, get_logger(), Returns a module-specific logger. Example: logger = get_logger("vision"), Application service. An application is not a process, and conflating the two is…, is_uri(), Application name resolution. The model asks for "notepad", or "calculator", or…, Whether a target is a shell URI (``ms-settings:``, ``mailto:``) rather than a… (+113 more)

### Community 216 - "test_calibration_history.py"
Cohesion: 0.37
Nodes (14): _audit_over(), _derive_over(), _outcome(), asyncio, CalibrationHistoryService: the honest first rung of learning from history. It…, test_correction_is_validated_out_of_sample(), test_empty_history_cannot_measure(), test_is_deterministic() (+6 more)

### Community 217 - "MSSScreen"
Cohesion: 0.04
Nodes (46): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+38 more)

### Community 218 - "test_ui.py"
Cohesion: 0.19
Nodes (10): _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal(), cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must… (+2 more)

### Community 219 - "ProbabilityService"
Cohesion: 0.19
Nodes (6): CalibrationMetrics, Any, Out-of-sample calibration/accuracy measures over one evaluation slice., ProbabilityService, A non-committal 0.5 estimate when no model can honestly be fit., Deterministic, calibrated, look-ahead-safe probability estimator.

### Community 220 - "memory/tools.py"
Cohesion: 0.46
Nodes (12): _disabled(), find_related_memory(), forget_memory(), get_memory(), list_memories(), _manager(), memory_status(), Any (+4 more)

### Community 221 - "agents/core.py"
Cohesion: 0.06
Nodes (30): AgentCore, AgentRunResult, _planned_to_call(), The agent core loop: the driver that turns a goal into a finished run. This is…, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Run one goal to a terminal state and report the outcome. Creates and seeds a… (+22 more)

### Community 222 - "emit_trace"
Cohesion: 0.08
Nodes (22): emit_trace(), Any, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), Any, Redact forbidden keys without shortening the surviving values. For the…, Bound the size of an arbitrary value destined for a payload. Scalars pass… (+14 more)

### Community 223 - "test_prediction.py"
Cohesion: 0.41
Nodes (10): Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, _orchestrator(), asyncio, PredictionRecord: the auditable section-8 prediction contract. These tests pin…, test_record_captures_section_8_contract(), test_record_id_is_deterministic_for_the_same_report(), test_record_never_fabricates_probability_on_mock(), test_record_preserves_mock_no_trade_verbatim() (+2 more)

### Community 224 - "vision/controller.py"
Cohesion: 0.06
Nodes (45): VisionProvider, Vision system for AetherOS. Provides OCR, object detection, template matching,…, Vision domain models., Any, Represents a template match result., TemplateMatch, BaseVisionProvider, DetectionProvider (+37 more)

### Community 225 - "ParsedResponse"
Cohesion: 0.22
Nodes (5): ParsedResponse, Normalised view of one provider response., parametrize, A provider that returned plain text still yields a usable answer., TestDegenerateInput

### Community 226 - "NullTTS"
Cohesion: 0.17
Nodes (3): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…

### Community 227 - "test_evidence.py"
Cohesion: 0.31
Nodes (9): _build(), EvidenceService: turning deterministic reads into sourced, weighted claims. The…, test_every_item_is_weighted_and_typed(), test_evidence_inherits_provenance_and_quality(), test_evidence_is_deterministic(), test_mock_evidence_is_not_reliable(), test_primary_calculated_evidence_is_reliable(), test_uptrend_yields_bullish_leaning_evidence() (+1 more)

### Community 228 - "test_analysis_service.py"
Cohesion: 0.36
Nodes (10): make_invalid_market_data(), A series with a structurally impossible candle (high below low)., _analysis_service(), asyncio, AnalysisService: the deterministic end-to-end orchestrator. Fusion is a…, test_mock_analysis_is_deterministic(), test_mock_analysis_is_labelled_and_not_actionable(), test_publishes_analysis_completed() (+2 more)

### Community 229 - "test_monitoring_scheduler.py"
Cohesion: 0.40
Nodes (8): _FakeMonitoring, asyncio, MonitoringScheduler: the bounded, opt-in autonomous loop (spec section 29). A…, _settings(), test_a_failing_sweep_does_not_kill_the_loop(), test_disabled_scheduler_does_not_start(), test_enabled_scheduler_sweeps_then_stops_cleanly(), test_run_once_now_bypasses_the_schedule()

### Community 230 - "Instrument"
Cohesion: 0.02
Nodes (163): Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, AnomalyAnalysis, Any, datetime, Statistical-anomaly value object. An :class:`AnomalyAnalysis` is the…, Deterministic last-bar statistical-outlier read for one instrument. (+155 more)

### Community 231 - "ToolDiscovery"
Cohesion: 0.22
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 232 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 234 - "NullActivator"
Cohesion: 0.20
Nodes (3): NullActivator, WakeCallback, An activator that never fires. This is what "always-listening is off" looks…

### Community 236 - "test_anomaly.py"
Cohesion: 0.36
Nodes (9): AnomalyService: deterministic last-bar statistical-outlier detection. These…, _service(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_quiet_tape_is_no_anomaly_and_reliable(), test_return_crash_down_is_anomalous(), test_return_spike_up_is_anomalous_and_reliable(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 237 - "test_breakout.py"
Cohesion: 0.36
Nodes (9): BreakoutService: deterministic channel-breakout detection. The channel/volume…, _service(), test_falling_series_breaks_down(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_range_bound_series_has_no_breakout(), test_rising_series_breaks_out_up(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 238 - "parametrize"
Cohesion: 0.27
Nodes (3): parametrize, TestRegistration, TestSchema

### Community 239 - "MemoryConsolidator"
Cohesion: 0.36
Nodes (4): MemoryConsolidator, ndarray, Deduplicate and merge redundant memories (spec Phase 12)., Merge near-duplicates within one type; return how many were merged.

### Community 240 - "MemoryLifecycle"
Cohesion: 0.31
Nodes (5): MemoryLifecycle, datetime, Decide and apply lifecycle status transitions., The status a memory *should* have, without mutating it., Re-evaluate every memory's status and persist any transitions. Returns a count…

### Community 241 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 242 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 243 - "test_historical_analogue.py"
Cohesion: 0.39
Nodes (8): HistoricalAnalogueService: deterministic nearest-analogue forward-outcome read.…, _service(), test_falling_tape_leans_down(), test_horizon_override_is_respected(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_rising_tape_leans_up_and_reliable(), test_thin_history_is_unknown_not_fabricated()

### Community 245 - "test_macro.py"
Cohesion: 0.47
Nodes (8): asyncio, MacroContextService: deterministic broad-market risk-posture read. These tests…, _service(), test_is_deterministic(), test_mock_benchmark_is_never_reliable(), test_thin_benchmark_is_unknown_not_fabricated(), test_trending_down_benchmark_is_risk_off(), test_trending_up_benchmark_is_risk_on_and_reliable()

### Community 246 - "CEOBrief"
Cohesion: 0.29
Nodes (6): CEOBrief, Any, datetime, Trading-CEO brief value object. A :class:`CEOBrief` is the natural-language…, A grounded natural-language narration of a deterministic trading report., _utcnow()

### Community 248 - "_RecordingMouse"
Cohesion: 0.11
Nodes (3): A ``MouseController`` sitting where PyAutoGUI would. Reports a fixed position…, _RecordingMouse, The list is read live from the registry, so a tool registered after the command…

### Community 249 - "PlattScaler"
Cohesion: 0.29
Nodes (3): PlattScaler, Deterministic 1-D logistic calibrator: p_cal = sigmoid(a * score + b)., _sigmoid()

### Community 250 - "trading/conftest.py"
Cohesion: 0.32
Nodes (7): downtrend_data(), flat_data(), _provenance(), datetime, fixture, Shared builders for trading tests. These construct MarketData with *controlled*…, uptrend_data()

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 252 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 253 - "workflow_believer_run.py"
Cohesion: 0.38
Nodes (6): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows.

### Community 254 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 255 - "test_divergence.py"
Cohesion: 0.48
Nodes (6): DivergenceService: deterministic price-vs-RSI regular-divergence detection. Two…, _service(), test_clean_series_reads_determinate_direction(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_thin_data_is_unknown_not_fabricated()

### Community 256 - "LLMEngine"
Cohesion: 0.11
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 258 - "test_risk.py"
Cohesion: 0.25
Nodes (22): _levels(), _make_analysis(), _prov(), asyncio, parametrize, RiskService: deterministic risk geometry from a TradingAnalysis. Every number…, Construct a TradingAnalysis directly for precise risk-math assertions., _stable() (+14 more)

### Community 259 - "._ask"
Cohesion: 0.33
Nodes (3): Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal.

### Community 260 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 261 - "prediction.py"
Cohesion: 0.50
Nodes (4): datetime, The Prediction Contract value object (spec sections 8, 19, 28). A…, Content-addressed id for one prediction (spec section 8). Keyed on the full…, _stable_id()

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3184 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `LLMEngine`, `Application`, `bootstrapper.py`, `ContextBuilder`, `services/manager.py`, `WindowController`, `ceo_agent_service.py`, `VerificationResult`, `TextBlock`, `AgentPlanner`, `executor.py`, `VoiceConfig`, `Agent`, `Bootstrapper`, `StageTimings`, `CommandRegistry`, `PolicyEngine`, `ProcessController`, `cli/main.py`, `MouseController`, `AgentError`, `policy.py`, `TraceEvent`, `TerminalService`, `ToolExecutionCoordinator`, `automation/engine.py`, `trading/domain/enums.py`, `ProcessService`, `MouseService`, `KeyboardService`, `automation/tools.py`, `HUDConfig`, `Application`, `YOLOProvider`, `BrowserProvider`, `MSSScreen`, `LifecycleManager`, `SpeechToText`, `agents/core.py`, `RecoveryRunner`, `vision/controller.py`, `NullTTS`, `SourceTier`, `Instrument`, `ClipboardController`, `NullActivator`, `setup_logging`, `VoiceState`, `agents/state.py`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `bootstrapper.py` to `test_risk.py`, `TestRegisteredToolSurface`, `test_calendar.py`, `test_orchestration.py`, `AutomationEngine`, `MultiTimeframeService`, `VerificationResult`, `test_ceo_agent.py`, `.from_provider`, `executor.py`, `test_backtest.py`, `test_news.py`, `Bootstrapper`, `PolicyEngine`, `test_critic.py`, `test_performance.py`, `test_fundamentals.py`, `policy.py`, `indicators/core.py`, `test_prediction_store.py`, `OpenAICompatibleProvider`, `automation/engine.py`, `test_ceo.py`, `test_monitoring.py`, `test_prediction_evaluator.py`, `test_explanation.py`, `automation/tools.py`, `get_logger`, `test_calibration_history.py`, `PortfolioRiskService`, `test_prediction.py`, `InMemoryPredictionStore`, `SQLiteMemoryProvider`, `test_analysis_service.py`, `test_monitoring_scheduler.py`, `FakeProvider`, `ScreenService`, `test_anomaly.py`, `test_breakout.py`, `setup_logging`, `test_historical_analogue.py`, `test_regime.py`, `test_macro.py`, `vision/tools.py`, `make_market_data`, `test_divergence.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `ToolCommandService`, `define`, `bootstrapper.py`, `ContextBuilder`, `ContextBuilder`, `answer`, `AutomationEngine`, `.registry`, `AgentPlanner`, `executor.py`, `.from_provider`, `get_llm_tools`, `test_agent_policy.py`, `test_agent_e2e.py`, `PolicyEngine`, `test_voice_agent_e2e.py`, `test_cli_agent.py`, `rich_tools`, `EventBus`, `ToolExecutionCoordinator`, `automation/engine.py`, `FakeLLMProvider`, `RecoveryRunner`, `agents/core.py`, `_state`, `ExecutionConfig`, `test_agent_execution.py`, `ExecutionStatus`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `Instrument` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Instrument` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._