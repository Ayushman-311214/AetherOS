# Graph Report - AetherOS  (2026-10-02)

## Corpus Check
- 482 files · ~373,300 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 9335 nodes · 23971 edges · 277 communities (244 shown, 20 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 2442 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a356bfc6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- services/manager.py
- Image
- define
- ToolExecutor
- bootstrapper.py
- asyncio
- Any
- MemoryConsolidator
- Scene
- WindowController
- AutomationEngine
- AgentState
- automation/engine.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- errors.py
- VoiceConfig
- trading/tools.py
- get_llm_tools
- Message
- agent_memory.py
- PlannedAction
- Event
- TraceRecorder
- test_news.py
- Any
- Bootstrapper
- PsutilProcess
- _RecordingProvider
- CommandRegistry
- FakeHUDProcess
- OpenCVProvider
- PolicyEngine
- VoiceService
- test_wiring.py
- make_vision_service
- test_voice_agent_e2e.py
- ProcessController
- VisionError
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
- HUDSnapshot
- PathGuard
- agents/core.py
- indicators/core.py
- _RecordingProvider
- TraceEvent
- FrameCache
- test_grounding_tools.py
- ToolCall
- test_unified_interaction.py
- TerminalService
- TextBlock
- PlaywrightProvider
- TaskManager
- resolve_level
- ._run_step
- ClipboardService
- LiveTraceUI
- VisionProvider
- explanation.py
- FakeLLMProvider
- asyncio
- DesktopError
- test_ceo.py
- LLMProvider
- MemoryProvider
- calibration_history_service.py
- ProcessService
- tool
- test_prediction_evaluator.py
- Memory
- KeyboardService
- WindowService
- HUDConfig
- YOLOProvider
- VectorIndex
- BrowserProvider
- PortfolioCandidate
- LifecycleManager
- events/__init__.py
- voice/service.py
- RecoveryRunner
- TestRegistration
- InMemoryPredictionStore
- BrowserService
- ObservationLog
- KnowledgeGraph
- asyncio
- MemoryManager
- Instrument
- asyncio
- ClipboardController
- ContextBuilder
- PlanResult
- FakeProvider
- ScreenService
- PredictionRecord
- PyAutoGuiKeyboard
- FakeKeyboard
- window/tools.py
- PipeReader
- ExecutionConfig
- VoiceStateMachine
- safety/policy.py
- test_regime.py
- HUDProcess
- test_agent_execution.py
- process/tools.py
- .from_events
- get_settings
- MarketData
- make_market_data
- FakeMouse
- TraceFileWriter
- execution.py
- AgentExecutionResult
- _settings
- bootstrap/application.py
- ToolCommandService
- commands
- ._touch
- test_calendar.py
- test_interface_contracts.py
- test_orchestration.py
- test_agent_observation.py
- vision/main.py
- ceo_agent_service.py
- ToolExecutionResult
- test_yahoo_calendar_provider.py
- test_analyze_command.py
- audio.py
- test_ceo_agent.py
- executor.py
- test_agent_context.py
- MemoryConfig
- _FakeMouse
- Agent
- test_backtest.py
- test_agent_memory_integration.py
- test_agent_e2e.py
- test_divergence.py
- RenderContext
- LogisticRegression
- ContextBuilder
- ScreenController
- FilePredictionStore
- emit_trace
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
- Any
- .create
- import_all.py
- TTLCache
- test_yahoo_news_provider.py
- ToolRegistry
- test_fundamentals.py
- PredictionOutcome
- _settings
- PyAutoGuiClipboard
- tools/__init__.py
- test_trading_tools.py
- test_memory_command.py
- Box
- test_prediction_store.py
- strategy.py
- TestToolsCommand
- SapiTTS
- Procedure
- WorkingMemory
- _RecordingMouse
- .execute
- OpenAICompatibleProvider
- test_vision_engine.py
- AetherOS
- test_monitoring.py
- .parse
- AnomalyService
- ._format_trading_report
- test_agent.py
- test_agent_planner.py
- parse_llm_response
- Workflow
- PlannerConfig
- Application
- get_logger
- test_calibration_history.py
- MSSScreen
- test_ui.py
- .test_the_registered_engine_is_preferred
- memory/tools.py
- interaction.py
- safe_preview
- tasks/__init__.py
- vision/controller.py
- Layer
- GlowCache
- trading/conftest.py
- AgentStatus
- test_monitoring_scheduler.py
- Direction
- RejectedToolCall
- spatial.py
- .assistant
- VoiceActivator
- renderer.py
- test_anomaly.py
- test_breakout.py
- test_manager.py
- qcolor
- utcnow
- ToolExecutionCoordinator
- TestPromptCursor
- test_historical_analogue.py
- main
- test_macro.py
- FakeScreen
- _RecordingMouse
- _build
- TestFinalResponse
- TraceCollector
- TestEveryToolModuleImports
- workflow_believer_run.py
- TaskContext
- .save
- LLMEngine
- main
- test_risk.py
- .test_payload_drives_a_real_tool_call_round_trip
- set_event_bus
- _stable_id
- TestMSSSave
- _Def
- .grab
- .is_available
- PulseLayer
- TickLayer
- Any
- bootstrapper
- .executor
- .policy
- .hud
- .trace
- .coordinator
- executor

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 244 edges
2. `Image` - 183 edges
3. `Instrument` - 177 edges
4. `tool()` - 159 edges
5. `AgentState` - 153 edges
6. `Direction` - 124 edges
7. `get_logger()` - 123 edges
8. `Provenance` - 108 edges
9. `define()` - 107 edges
10. `EventBus` - 105 edges

## Surprising Connections (you probably didn't know these)
- `test_from_dict_rejects_unknown_field()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_from_dict_requires_source()` --uses--> `AgentError`  [INFERRED]
  tests/agents/test_agent_observation.py → src/aetheros/core/errors/agent_error.py
- `test_classify_covers_every_alignment()` --uses--> `MultiTimeframeService`  [INFERRED]
  tests/trading/test_multi_timeframe.py → src/aetheros/trading/services/multi_timeframe_service.py
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py

## Import Cycles
- 4-file cycle: `src/aetheros/agents/context.py -> src/aetheros/llm/agent_loop.py -> src/aetheros/agents/planner/__init__.py -> src/aetheros/agents/planner/planner.py -> src/aetheros/agents/context.py`

## Communities (277 total, 20 thin omitted)

### Community 0 - "services/manager.py"
Cohesion: 0.06
Nodes (61): int, confidence_band(), MemoryImportance, MemoryScope, MemoryStatus, MemoryType, OutcomeStatus, PreferenceKind (+53 more)

### Community 1 - "Image"
Cohesion: 0.03
Nodes (44): ColorSpace, High-level vision service. Coordinates OCR, computer vision, object detection…, Recognise text and return only the blocks matching ``query``., Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a… (+36 more)

### Community 2 - "define"
Cohesion: 0.06
Nodes (62): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), define(), fixture, Factory for ToolDefinition objects (the factory-as-fixture pattern)., tool_calls(), make_loop() (+54 more)

### Community 3 - "ToolExecutor"
Cohesion: 0.04
Nodes (55): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…, Executes registered AetherOS tools. (+47 more)

### Community 4 - "bootstrapper.py"
Cohesion: 0.02
Nodes (101): Register the deterministic Trading Intelligence core. Self-contained: it…, Map ATR-as-fraction-of-price to a volatility band (deterministic)., MonitoringReport, Any, One bounded monitoring sweep: resolved outcomes + their aggregate., Level, Any, A support or resistance level clustered from swing points. (+93 more)

### Community 5 - "asyncio"
Cohesion: 0.14
Nodes (11): asyncio, A plain back-and-forth reaches the provider unchanged., Observations are not transcript turns, so the context has to carry them., A running, seeded state on its first iteration., The context tracks where the run is in its budget., Determinism: no clock, no registry order, no set iteration., The property that matters: a longer run is not a bigger prompt., _started() (+3 more)

### Community 6 - "Any"
Cohesion: 0.05
Nodes (24): _clamp(), _describe_result(), IterationInfo, Any, Observation, Where the run is in its budget. Carried explicitly because the model behaves…, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts. (+16 more)

### Community 7 - "MemoryConsolidator"
Cohesion: 0.10
Nodes (15): MemoryConsolidated, MemoryForgotten, MemoryRetrieved, MemoryStored, Any, Memory-domain events (spec Phase 16/22). Published on the shared EventBus so…, A memory was written (created or updated)., A retrieval returned a ranked set of memories. (+7 more)

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
Nodes (22): Record an episode (and failure/recovery) from a finished run., AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,…, call(), failed_result(), ok_result() (+14 more)

### Community 12 - "automation/engine.py"
Cohesion: 0.06
Nodes (43): Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Trim a tool's return value to something a result can carry., _summarise_value(), Automation — multi-step desktop work with verification, retries and rollback.…, describe_strategies(), Recovery — bounded self-healing between step attempts. A retry that changes…, Strategy name to description. Read by the ``run_workflow`` tool description and… (+35 more)

### Community 13 - "VerificationResult"
Cohesion: 0.05
Nodes (41): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, What was checked, what was expected, and what was actually observed. The four…, True only for a real, passing check. UNSUPPORTED and SKIPPED are both false… (+33 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.04
Nodes (39): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+31 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.10
Nodes (18): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _calls(), Argument names may be logged; argument values may not., One well-formed call for a known tool is planned, not executed., A provider that supports parallel calls gets one action per call. (+10 more)

### Community 16 - "errors.py"
Cohesion: 0.06
Nodes (30): Supported candle timeframes., Resolve a user/tool string to a Timeframe, raising ValueError if unknown., Timeframe, AnalysisError, BacktestError, CriticError, IndicatorError, InsufficientDataError (+22 more)

### Community 17 - "VoiceConfig"
Cohesion: 0.05
Nodes (30): ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Synthesize and play `text`, returning when playback ends. Must not block the…, Stop playback immediately. Safe to call when nothing is playing. (+22 more)

### Community 18 - "trading/tools.py"
Cohesion: 0.06
Nodes (77): _analysis(), analyze_fundamentals(), analyze_instrument(), analyze_macro_context(), analyze_market_structure(), analyze_multi_timeframe(), analyze_news_sentiment(), analyze_relative_strength() (+69 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "Message"
Cohesion: 0.08
Nodes (40): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, The provider-facing shape, matching ``LLMToolLoop`` exactly., build_application(), _initial_config(), main(), Any (+32 more)

### Community 21 - "agent_memory.py"
Cohesion: 0.07
Nodes (32): ActionRecord, Outcome, Any, datetime, One step taken within an episode (a tool call, an agent action)., The result of an episode or an action (spec Phase 9)., _utcnow(), build_agent_memory() (+24 more)

### Community 22 - "PlannedAction"
Cohesion: 0.06
Nodes (18): PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because… (+10 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (68): EventHandler, Register an event handler., Publish an event. Every subscriber receives the event., Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name. (+60 more)

### Community 24 - "TraceRecorder"
Cohesion: 0.12
Nodes (14): Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent., TraceRecorder (+6 more)

### Community 25 - "test_news.py"
Cohesion: 0.12
Nodes (33): Deterministic news & sentiment analysis (spec sections 5, 9, 26 item #9). This…, classify(), LexiconSentiment, The deterministic sentiment read for one piece of text., Classify ``text`` into a deterministic directional sentiment. Returns UNKNOWN…, _tokenize(), FakeNewsProvider, _item() (+25 more)

### Community 26 - "Any"
Cohesion: 0.13
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.08
Nodes (7): Bootstrapper, Whether Playwright can be imported. find_spec rather than a try/import:…, Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., The running voice service, or None when voice is not up.

### Community 28 - "PsutilProcess"
Cohesion: 0.10
Nodes (19): PsutilProcess, Any, Path, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle…, Read one process into a plain dict. Fields that require privileges are filled…, Start a program and return its pid. ``env``, when given, *extends* the current…, Open a file with its registered application. Returns ``0``, which means "no pid… (+11 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.04
Nodes (26): CommandHandler, CommandRegistry, Explain WHY an instrument's recommendation came out the way it did -- no LLM…, Render an explanation dict as honest, plain terminal text., Register a CLI command., Scan a watchlist and rank it by directional signal for a human -- no LLM…, Render a watchlist-scan dict as an honest, ranked plain-text table., Risk-budget a basket of trades for a human -- no LLM involved (spec section 5,… (+18 more)

### Community 31 - "FakeHUDProcess"
Cohesion: 0.10
Nodes (8): FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first., The state of every snapshot sent, in order., Stands in for HUDProcess without launching anything. Records what the service…

### Community 32 - "OpenCVProvider"
Cohesion: 0.05
Nodes (36): Build the YOLO detector when its package and weights are both present. Returns…, Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the… (+28 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.04
Nodes (51): PolicyConfig, Any, Policy configuration: the rules the engine evaluates against. Deliberately…, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyDecision, PolicyEvaluation, Any (+43 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 36 - "make_vision_service"
Cohesion: 0.06
Nodes (28): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+20 more)

### Community 37 - "test_voice_agent_e2e.py"
Cohesion: 0.05
Nodes (27): Captured microphone audio., Recording, EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, AmplitudeCallback, Records what would have been spoken. The test double for speech output: it…, RecordingTTS (+19 more)

### Community 38 - "ProcessController"
Cohesion: 0.07
Nodes (18): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+10 more)

### Community 39 - "VisionError"
Cohesion: 0.05
Nodes (45): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError (+37 more)

### Community 40 - "test_critic.py"
Cohesion: 0.11
Nodes (106): _analysis(), _anomaly(), _backtest(), _breakout(), _calendar(), _divergence(), _evidence(), _fundamentals() (+98 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.11
Nodes (23): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+15 more)

### Community 43 - "test_yahoo_provider.py"
Cohesion: 0.17
Nodes (26): ProviderError, A data provider failed, timed out, or returned an unusable response., asyncio, Returns crafted PRIMARY candles per symbol; raises for named symbols., _scan_service(), test_actionable_names_rank_ahead_and_errors_sink(), test_blank_and_duplicate_symbols_are_normalised(), test_scan_is_deterministic() (+18 more)

### Community 44 - "cli/main.py"
Cohesion: 0.13
Nodes (11): Execute a parsed command., CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…, CommandParser, ParsedCommand (+3 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 47 - "AgentError"
Cohesion: 0.06
Nodes (36): _describe_call(), Agent context assembly. One :class:`AgentContext` is everything the model needs…, One digest line for a call: names, never values. The model already has the…, Agent layer. Four pieces so far. :mod:`~aetheros.agents.state` is the explicit,…, ObservationLog: the ordered set of what the agent currently knows. A run…, ActionType, Enum, str (+28 more)

### Community 48 - "test_performance.py"
Cohesion: 0.22
Nodes (23): _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes., _resolved(), _service() (+15 more)

### Community 49 - "CLIUI"
Cohesion: 0.11
Nodes (9): Panel, CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen. (+1 more)

### Community 50 - "Win32Window"
Cohesion: 0.09
Nodes (20): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+12 more)

### Community 51 - "wire"
Cohesion: 0.07
Nodes (26): make_fake_detector(), executor(), asyncio, fixture, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in… (+18 more)

### Community 52 - "HUDSnapshot"
Cohesion: 0.09
Nodes (19): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+11 more)

### Community 53 - "PathGuard"
Cohesion: 0.11
Nodes (21): PathLike, PathAccess, PathGuard, PathVerdict, Enum, Path, str, Path validation for the filesystem and application tools. A model that can… (+13 more)

### Community 54 - "agents/core.py"
Cohesion: 0.04
Nodes (58): AgentCore, ContextBuilder, The agent core loop: the driver that turns a goal into a finished run. This is…, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Assemble a core from a provider and, optionally, its collaborators. The…, The one entry a front end submits a turn through. Both the terminal and voice…, AgentMemory, MemoryContext (+50 more)

### Community 55 - "indicators/core.py"
Cohesion: 0.05
Nodes (61): adx(), _as_float_array(), atr(), bollinger(), ema(), last_finite(), macd(), _nan_prefix() (+53 more)

### Community 56 - "_RecordingProvider"
Cohesion: 0.12
Nodes (3): Path, A ``BrowserProvider`` sitting where Playwright would. Records every call so…, _RecordingProvider

### Community 57 - "TraceEvent"
Cohesion: 0.08
Nodes (41): Best-effort emission of trace events. The one rule this module exists to…, _default_stage(), Enum, str, The trace event vocabulary. One concrete :class:`TraceEvent` class (not a class…, One observed moment in a run, safe to log and to persist. Only observable, log-…, Every stage of the live execution pipeline. ``str``-valued so a serialized…, How the stage an event reports is doing. Kept small and orthogonal to… (+33 more)

### Community 58 - "FrameCache"
Cohesion: 0.06
Nodes (28): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message… (+20 more)

### Community 59 - "test_grounding_tools.py"
Cohesion: 0.09
Nodes (17): _block(), executor(), asyncio, fixture, parametrize, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received… (+9 more)

### Community 60 - "ToolCall"
Cohesion: 0.07
Nodes (25): Record a call the model asked for. Accepts the parse layer's :class:`ToolCall`…, AgentLoopResult, LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Outcome of a full loop run., Main LLM ↔ tool-coordination loop. (+17 more)

### Community 61 - "test_unified_interaction.py"
Cohesion: 0.13
Nodes (22): InteractionGateway, Submit a goal to the shared agent, tagged with its front end., _boom(), _build_agent(), _CountingExecutor, _mouse_position(), Any, asyncio (+14 more)

### Community 62 - "TerminalService"
Cohesion: 0.14
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 63 - "TextBlock"
Cohesion: 0.03
Nodes (55): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+47 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 66 - "resolve_level"
Cohesion: 0.10
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 67 - "._run_step"
Cohesion: 0.10
Nodes (14): _append_recovery_detail(), _backoff_seconds(), Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran…, Delay before the next attempt: exponential, and capped. Exponential because the…, Fold recovery outcomes into the error the step will report if it still fails.… (+6 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "explanation.py"
Cohesion: 0.15
Nodes (9): EvidenceReason, Explanation, Any, datetime, Signal-explanation value object. An :class:`Explanation` answers the spec's…, One line of the consolidated ledger (a compact view of an Evidence item)., A deterministic, read-only explanation of a report's recommendation., _utcnow() (+1 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (16): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per…, Build a provider response requesting the given ``(name, arguments)`` calls.… (+8 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "DesktopError"
Cohesion: 0.09
Nodes (16): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Application service. An application is not a process, and conflating the two is…, Application name resolution. The model asks for "notepad", or "calculator", or…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard(), Process service. Sits between the tools and the psutil backend, and adds the… (+8 more)

### Community 75 - "test_ceo.py"
Cohesion: 0.08
Nodes (28): CEOBrief, Any, datetime, Trading-CEO brief value object. A :class:`CEOBrief` is the natural-language…, A grounded natural-language narration of a deterministic trading report., _utcnow(), Narrate via the LLM when wired; otherwise a deterministic fallback. Any LLM…, Interpret a free-text request, then brief the instrument it names. The LLM… (+20 more)

### Community 76 - "LLMProvider"
Cohesion: 0.07
Nodes (15): LLMProvider, ABC, Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources. (+7 more)

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "calibration_history_service.py"
Cohesion: 0.05
Nodes (42): CalibrationAudit, CalibrationCorrection, Any, datetime, Calibration-audit value object. A :class:`CalibrationAudit` is the honest first…, A holdout-validated recalibration map ``p' = sigmoid(a*p + b)``. Derived from…, Correct a probability -- but only when trusted; otherwise unchanged., Realised-calibration measurement over the accumulated prediction history. (+34 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "tool"
Cohesion: 0.07
Nodes (46): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+38 more)

### Community 81 - "test_prediction_evaluator.py"
Cohesion: 0.28
Nodes (24): _Bus, _evaluator(), _market_data(), asyncio, datetime, The deterministic prediction-outcome evaluator (spec sections 6, 16, 29). These…, A minimal event bus that records what the evaluator publishes., _record() (+16 more)

### Community 82 - "Memory"
Cohesion: 0.04
Nodes (45): Memory, datetime, One stored memory -- the universal record (spec Phase 2/3). Mutable on purpose:…, Record that this memory was retrieved (feeds recency/frequency)., Whether the memory has passed its TTL. PERMANENT memories never expire…, Timezone-aware current UTC instant (the whole layer is tz-aware)., utcnow(), MemoryPolicyEngine (+37 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 85 - "HUDConfig"
Cohesion: 0.07
Nodes (20): _as_bool(), _as_float(), _as_int(), _as_text(), _defaults(), HUDConfig, Any, Configuration for the JARVIS-style overlay. (+12 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (15): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Make torch.cuda.is_available() report a chosen value. (+7 more)

### Community 87 - "VectorIndex"
Cohesion: 0.06
Nodes (20): EmbeddingProvider, ABC, ndarray, Embedding provider abstraction (spec Phase 5). The vector layer must not be…, Turns text into a fixed-dimension, L2-normalised vector., Stable identifier recorded alongside each stored vector., Length of every vector this provider emits., Embed one string. Returns a float32 array of length ``dimension``. (+12 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.04
Nodes (25): BrowserProvider, ABC, Any, Path, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element. (+17 more)

### Community 89 - "PortfolioCandidate"
Cohesion: 0.12
Nodes (19): PortfolioCandidate, PortfolioPosition, PortfolioRiskPlan, Any, datetime, Portfolio-risk value objects. Where…, One candidate trade feeding the allocator: its directional risk geometry., A candidate after allocation: its size, risk and notional (or why not). (+11 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "events/__init__.py"
Cohesion: 0.21
Nodes (11): get_event_bus(), publish(), Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., clear_subscribers(), get_subscribers(), Any, Decorator used to register an event handler. Example:… (+3 more)

### Community 92 - "voice/service.py"
Cohesion: 0.05
Nodes (34): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+26 more)

### Community 93 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "InMemoryPredictionStore"
Cohesion: 0.22
Nodes (19): InMemoryPredictionStore, Process-local reference store. Deterministic, dependency-free, non-durable.…, _FakeEvaluator, asyncio, The prediction track-record service: the on-demand composition of the audit…, A minimal, hand-built recorded prediction with a fixed content id., A RESOLVED, optionally-graded outcome for the fake evaluator to hand back., Returns a pre-baked outcome per record id; raises for flagged ids. (+11 more)

### Community 96 - "BrowserService"
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "ObservationLog"
Cohesion: 0.08
Nodes (16): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, Recall relevant memory and inject it as advisory observations. Wrapped end-to-…, Record the finished run into memory, best-effort (spec Phase 20F-20I)., The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, ObservationLog (+8 more)

### Community 98 - "KnowledgeGraph"
Cohesion: 0.08
Nodes (19): DiGraph, Entity, Any, datetime, Semantic-memory value objects: entities and the relationships between them.…, A node in the knowledge graph (spec Phase 6)., Canonical lookup key: type + normalised name (graph dedup)., A typed edge between two entities (spec Phase 6). ``valid_from`` / ``valid_to``… (+11 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "MemoryManager"
Cohesion: 0.04
Nodes (25): Resolve the agent-memory port for AgentCore (spec Phase 20K). Returns…, Path, AetherOS Memory subsystem (CLAUDE.md section 15; implementation spec Phases…, MemoryManager, Any, Persist a pre-built Memory, honouring the retention policy., Edit a stored memory (spec Phase 4 -- MemoryUpdater). Supported fields:…, Create a typed memory-to-memory link (spec Phase 4 -- link). (+17 more)

### Community 101 - "Instrument"
Cohesion: 0.02
Nodes (111): Map a 0..1 score to a band. This is a label, not a calibrated probability., Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, EventCalendar, MarketEvent, Any, datetime, Event / economic-calendar value objects (spec sections 5, 9, 26). The calendar… (+103 more)

### Community 102 - "asyncio"
Cohesion: 0.07
Nodes (27): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+19 more)

### Community 103 - "ClipboardController"
Cohesion: 0.08
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - "ContextBuilder"
Cohesion: 0.17
Nodes (13): Any, ContextBuilder, A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools. (+5 more)

### Community 105 - "PlanResult"
Cohesion: 0.09
Nodes (13): PlanResult, What one planning round produced. The question the planner answers is singular…, Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only…, Emit LLM_RESPONSE_RECEIVED from observable response data only. Reads…, Emit PLANNER_DECISION from the log-safe ``describe`` projection. (+5 more)

### Community 106 - "FakeProvider"
Cohesion: 0.30
Nodes (15): FakeProvider, A controllable, clearly-synthetic provider for service tests. Unlike the mock…, asyncio, MarketDataService: caching, validation, freshness and honest error typing. This…, _service(), test_fresh_series_is_ok(), test_invalid_symbol_raises(), test_non_positive_limit_raises() (+7 more)

### Community 107 - "ScreenService"
Cohesion: 0.19
Nodes (10): Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, ScreenService, make_fake_screen(), asyncio, A capture failure must surface, not be turned into an empty frame that OCR… (+2 more)

### Community 108 - "PredictionRecord"
Cohesion: 0.11
Nodes (24): PredictionRecord, Any, A prediction resting on mock data can never be treated as reliable., Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, The auditable section-8 contract for one produced trading report., Persist ``record`` and return its id. Idempotent on the id., Return the recorded prediction with this id, or ``None`` if unknown. (+16 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.11
Nodes (9): Any, PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or… (+1 more)

### Community 110 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "PipeReader"
Cohesion: 0.09
Nodes (11): IO, decode(), PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived. (+3 more)

### Community 113 - "ExecutionConfig"
Cohesion: 0.21
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 114 - "VoiceStateMachine"
Cohesion: 0.09
Nodes (11): Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+3 more)

### Community 115 - "safety/policy.py"
Cohesion: 0.15
Nodes (17): Safety — the gates every destructive desktop action passes through. Two…, Capability, Decision, PolicyDecision, Enum, str, The risk policy that gates every desktop action. The rule this module exists to…, Evaluates desktop actions against configuration and caller intent. Stateless.… (+9 more)

### Community 116 - "test_regime.py"
Cohesion: 0.23
Nodes (16): _FakeBus, asyncio, Market-regime detection: deterministic trending / ranging / volatile reads.…, Records published events; duck-typed stand-in for the EventBus., _service(), test_clean_downtrend_is_trending_down(), test_clean_uptrend_is_trending_up(), test_detect_emits_event_when_bus_wired() (+8 more)

### Community 117 - "HUDProcess"
Cohesion: 0.09
Nodes (13): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+5 more)

### Community 118 - "test_agent_execution.py"
Cohesion: 0.08
Nodes (31): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+23 more)

### Community 119 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 120 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 121 - "get_settings"
Cohesion: 0.06
Nodes (47): get_settings(), Singleton Settings object., Attempts to make, resolved against configuration and clamped., get_frame_cache(), Short-lived screen-frame cache. A desktop agent frequently runs several vision…, Process-wide frame cache, sized from the shared settings object. Built once…, Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache() (+39 more)

### Community 122 - "MarketData"
Cohesion: 0.03
Nodes (41): SignalFn, BacktestResult, Any, datetime, Backtest value objects. A :class:`BacktestResult` is the deterministic product…, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome (+33 more)

### Community 123 - "make_market_data"
Cohesion: 0.30
Nodes (14): make_market_data(), datetime, Build a MarketData from a close series with plausible OHLC/volume., RelativeStrengthService: deterministic instrument-vs-benchmark strength. These…, _service(), test_clear_laggard_is_down(), test_clear_outperformer_is_up_and_reliable(), test_is_deterministic() (+6 more)

### Community 125 - "TraceFileWriter"
Cohesion: 0.12
Nodes (13): Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,…, _safe_name(), TraceFileWriter, Path (+5 more)

### Community 126 - "execution.py"
Cohesion: 0.20
Nodes (8): ExecutionStatus, Enum, str, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 127 - "AgentExecutionResult"
Cohesion: 0.06
Nodes (19): A stable identity for *what this call did*, for loop detection. Two calls share…, AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values… (+11 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "bootstrap/application.py"
Cohesion: 0.17
Nodes (8): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal()

### Community 130 - "ToolCommandService"
Cohesion: 0.11
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 132 - "._touch"
Cohesion: 0.11
Nodes (11): BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Finish the run unsuccessfully, recording the unrecoverable error., Stop the run on request. Distinct from failure: nothing went wrong., A finished run is immutable. This is what makes the record auditable: a state…, Open the transcript with the system prompt and the goal., Claim the next iteration, or refuse. Check-then-increment is exactly why the…, Add to the effort counters. Deltas only, never a negative. Guarded like every… (+3 more)

### Community 133 - "test_calendar.py"
Cohesion: 0.13
Nodes (37): EventImpact, EventType, Enum, str, Category of a scheduled market event. Inherits ``str`` for JSON output., How disruptive an event is expected to be. A label, never a probability., CalendarProvider, ABC (+29 more)

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "test_orchestration.py"
Cohesion: 0.16
Nodes (33): _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_report_fuses_anomaly_as_advisory_but_stays_no_trade(), test_report_fuses_breakout_as_advisory_but_stays_no_trade(), test_report_fuses_calendar_as_advisory_but_stays_no_trade(), test_report_fuses_divergence_as_advisory_but_stays_no_trade(), test_report_fuses_fundamentals_as_advisory_but_stays_no_trade() (+25 more)

### Community 136 - "test_agent_observation.py"
Cohesion: 0.05
Nodes (51): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``… (+43 more)

### Community 137 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 138 - "ceo_agent_service.py"
Cohesion: 0.12
Nodes (17): CEOInvestigation, CEOStep, Any, datetime, CEO-investigation value object. A :class:`CEOInvestigation` is the record of…, One tool call the CEO made during an investigation., The record of an agentic, tool-calling CEO investigation., _utcnow() (+9 more)

### Community 139 - "ToolExecutionResult"
Cohesion: 0.12
Nodes (12): Write the outcome into the run, then describe it. The record is built before it…, Record the outcome, tolerating a run that ended underneath it. The only way…, File a failure in the run's error ledger. Field by field rather than by handing…, Build the result. Pure -- no state, no clock beyond the elapsed span. The…, What came back from one tool call. A failed tool is data, not an exception: the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, Every result recorded against one call id., _render() (+4 more)

### Community 140 - "test_yahoo_calendar_provider.py"
Cohesion: 0.32
Nodes (20): _calendar_payload(), _ok_handler(), _provider(), asyncio, YahooCalendarProvider: the first real event-calendar adapter. These tests are…, A unix timestamp ``days_from_now`` days from now (negative = past)., Build a Yahoo /v10/finance/quoteSummary calendarEvents-shaped payload., test_empty_calendar_is_a_clear_calendar_not_an_error() (+12 more)

### Community 141 - "test_analyze_command.py"
Cohesion: 0.13
Nodes (28): asyncio, The ``analyze`` CLI command: the deterministic trading pipeline surfaced to a…, test_analyze_backtest_flag_includes_backtest(), test_analyze_carries_uncertainty_reminder(), test_analyze_flags_advisory_layers_as_unreliable(), test_analyze_never_fabricates_probability(), test_analyze_not_connected_without_service(), test_analyze_renders_critic_verdict_and_checks() (+20 more)

### Community 142 - "audio.py"
Cohesion: 0.05
Nodes (49): Future, LevelCallback, AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded. (+41 more)

### Community 143 - "test_ceo_agent.py"
Cohesion: 0.20
Nodes (16): _FakeExecutor, Any, asyncio, CEOAgentService: the Trading CEO as a bounded, fenced tool-calling loop. A…, Returns canned results per tool name; records what was executed., Yields a fixed sequence of raw replies, one per generate() call., _Result, _ScriptedLLM (+8 more)

### Community 144 - "executor.py"
Cohesion: 0.06
Nodes (35): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Exception, ToolError, is_unconstrained(), public_parameters(), Any, Signature (+27 more)

### Community 145 - "test_agent_context.py"
Cohesion: 0.11
Nodes (14): builder(), _call(), fixture, Tests for the agent context layer. The properties under test are the ones the…, One faithful view for auditing, one redacted view for the sinks., Tool rounds keep the shape the provider layer already accepts., A tool message whose assistant turn was trimmed fails the request. The provider…, The digest must stay safe to log; the history carries the values. (+6 more)

### Community 146 - "MemoryConfig"
Cohesion: 0.06
Nodes (29): MemoryConfig, Resolved memory configuration (spec Phase 23). A single immutable snapshot of…, Immutable, fully-resolved memory settings., MemoryQuery, MemoryResult, Any, Query, result and explanation value objects for retrieval (spec Phase 7). The…, A retrieval request (spec Phase 7 -- query understanding stage input). ``text``… (+21 more)

### Community 148 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 149 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 150 - "test_agent_memory_integration.py"
Cohesion: 0.17
Nodes (22): boom(), _build(), echo(), _FailingMemory, _memory_observation(), Any, asyncio, Phase 20 — Agent + Planner memory integration tests. Drive the real AgentCore… (+14 more)

### Community 151 - "test_agent_e2e.py"
Cohesion: 0.18
Nodes (14): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, End-to-end validation of the AetherOS agent through the CLI. These two runs…, Bind the ``MouseService`` the tools resolve to a recording controller. The real… (+6 more)

### Community 152 - "test_divergence.py"
Cohesion: 0.18
Nodes (14): ndarray, Indices that are a strict local min (low) / max (high) over +/-window. Returns…, Classify regular divergence over the two most recent pivots. For lows…, DivergenceService: deterministic price-vs-RSI regular-divergence detection. Two…, _service(), test_clean_series_reads_determinate_direction(), test_fewer_than_two_pivots_is_none(), test_is_deterministic() (+6 more)

### Community 153 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.27
Nodes (6): LogisticRegression, ndarray, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "ContextBuilder"
Cohesion: 0.17
Nodes (9): ContextBuilder, ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, A builder over the same collaborators with different limits., ``tool_categories`` narrows the menu to the relevant tools for a run. Left…, Limits are clamped, not trusted., TestConfiguration (+1 more)

### Community 156 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 157 - "FilePredictionStore"
Cohesion: 0.19
Nodes (14): FilePredictionStore, Path, A durable, append-only JSON Lines implementation of the same port. Each…, Populate the in-memory index from the file (once). Caller holds lock., asyncio, FilePredictionStore: the durable JSON Lines prediction-audit store. These pin…, Build a minimal, valid PredictionRecord with a chosen id., _record() (+6 more)

### Community 158 - "emit_trace"
Cohesion: 0.17
Nodes (13): emit_trace(), Any, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), TraceSpan, Any (+5 more)

### Community 159 - "PyAutoGuiMouse"
Cohesion: 0.07
Nodes (9): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., Return the current desktop subsystem status., status(), PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController., Return whether the process backend is available. (+1 more)

### Community 160 - "SQLiteDatabase"
Cohesion: 0.11
Nodes (16): Connection, MemoryStorageError, A persistence operation (SQLite read/write/migration) failed., Memory consolidator (spec Phase 12). Turns redundancy into stable knowledge:…, Any, Path, Row, SQLite connection management and migration runner (spec Phase 2). A thin,… (+8 more)

### Community 161 - "HUDService"
Cohesion: 0.06
Nodes (25): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+17 more)

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

### Community 167 - "ServiceContainer"
Cohesion: 0.08
Nodes (14): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, Any, Build a reasoner over the registered Agent Core. Raises: KeyError: no agent… (+6 more)

### Community 170 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 171 - "Any"
Cohesion: 0.29
Nodes (3): MemoryLink, Any, A typed, weighted edge between two memories (spec Phase 2 -- memory_links).…

### Community 172 - ".create"
Cohesion: 0.13
Nodes (7): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., The trace event vocabulary (PHASE 1). ``TraceEvent`` is the single class every…, TestTraceEventCreate, TestTraceEventToDict, TestTraceEventType

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - "test_yahoo_news_provider.py"
Cohesion: 0.40
Nodes (18): _news_item(), _ok_handler(), _provider(), asyncio, YahooNewsProvider: the first real news adapter. These tests are fully…, _search_payload(), test_duplicate_story_is_deduped(), test_empty_news_list_is_honest_no_news_not_an_error() (+10 more)

### Community 176 - "ToolRegistry"
Cohesion: 0.05
Nodes (68): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, boom(), _build(), check_playing(), click_element(), _CountingExecutor, ground_target() (+60 more)

### Community 177 - "test_fundamentals.py"
Cohesion: 0.24
Nodes (22): FakeFundamentalsProvider, asyncio, Deterministic fundamental-analysis tests (spec sections 5, 9, 21, 28). Two…, A controllable, clearly-synthetic snapshot stamped a non-mock tier., Hands back exactly the snapshot the test built; non-mock so it can be reliable., _service(), _snapshot(), test_mock_provider_is_deterministic() (+14 more)

### Community 178 - "PredictionOutcome"
Cohesion: 0.05
Nodes (34): PredictionOutcome, Any, Rebuild an outcome from its :meth:`to_dict` form (durable read-back). The…, The auditable result of checking one prediction against later market data., A resolved, directional outcome that was actually graded hit/miss., PredictionResolved, A past prediction was checked against the market that unfolded after it.…, FileOutcomeStore (+26 more)

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "PyAutoGuiClipboard"
Cohesion: 0.13
Nodes (9): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Return the current clipboard state. The state is inspected once and reused so…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file… (+1 more)

### Community 181 - "tools/__init__.py"
Cohesion: 0.14
Nodes (16): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+8 more)

### Community 182 - "test_trading_tools.py"
Cohesion: 0.08
Nodes (43): asyncio, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_macro_context_tool_is_labelled_mock(), test_analyze_market_structure_tool(), test_analyze_multi_timeframe_tool_is_labelled_mock(), test_analyze_news_sentiment_tool_is_labelled_mock() (+35 more)

### Community 183 - "test_memory_command.py"
Cohesion: 0.13
Nodes (17): A minimal config for tests / embedded use. Everything enabled, pointed at…, mem(), fixture, commands_with_memory(), asyncio, fixture, The ``memory`` CLI command (spec Phase 28). Drives the command handler directly…, test_memory_forget() (+9 more)

### Community 184 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 185 - "test_prediction_store.py"
Cohesion: 0.18
Nodes (11): _Bus, _FailingStore, _orchestrator(), The prediction audit store: interface, in-memory reference impl, and the…, A store whose backing fails on every write (durable-store outage sim)., A minimal event bus that records what the orchestrator publishes., test_announced_prediction_matches_the_recorded_one(), test_orchestrator_without_store_is_a_no_op() (+3 more)

### Community 186 - "strategy.py"
Cohesion: 0.12
Nodes (21): _parse_condition(), MatchMode, parse_mode(), parse_region(), PositionStrategy, Any, Enum, str (+13 more)

### Community 187 - "TestToolsCommand"
Cohesion: 0.13
Nodes (4): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., The list is read live from the registry, so a tool registered after the command…, TestToolsCommand

### Community 188 - "SapiTTS"
Cohesion: 0.14
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 189 - "Procedure"
Cohesion: 0.15
Nodes (8): Procedure, ProcedureStep, Any, datetime, One step in a procedure (spec Phase 10)., A learned, reusable procedure (spec Phase 10)., Confidence from evidence, not assertion (spec Phase 10/13). A Wilson-style…, _utcnow()

### Community 190 - "WorkingMemory"
Cohesion: 0.13
Nodes (7): Any, A compact textual summary of the working set (for context assembly)., Project the keep-worthy working items into long-term Memory records., One entry in the working set., Bounded live context for one session (spec Phase 8)., WorkingItem, WorkingMemory

### Community 191 - "_RecordingMouse"
Cohesion: 0.11
Nodes (4): _fake_mouse(), Bind the ``MouseService`` the tool resolves to a recording controller.…, A ``MouseController`` sitting where PyAutoGUI would. Records every absolute…, _RecordingMouse

### Community 192 - ".execute"
Cohesion: 0.10
Nodes (13): _as_tool_call(), _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, Record a call that was turned away, without the engine being asked. The refusal… (+5 more)

### Community 193 - "OpenAICompatibleProvider"
Cohesion: 0.14
Nodes (6): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…, main()

### Community 194 - "test_vision_engine.py"
Cohesion: 0.11
Nodes (10): asyncio, skipif, Tests for the Vision Engine. Run with: pytest tests/vision/, test_opencv_provider_metadata(), test_paddleocr_provider_metadata(), test_yolo_provider_metadata(), TestDetection, TestTemplateMatching (+2 more)

### Community 205 - "test_monitoring.py"
Cohesion: 0.24
Nodes (13): _Bus, _FakeEvaluator, _outcome(), asyncio, The monitoring service: one bounded "Observe Result -> Evaluate" sweep. These…, _record(), _service_with(), test_empty_history_is_a_valid_quiet_sweep() (+5 more)

### Community 206 - ".parse"
Cohesion: 0.33
Nodes (11): Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``. Raises ValueError for an empty…, asyncio, Mock market-data provider: reproducibility and honesty. The mock exists so the…, test_candle_count_matches_limit(), test_candles_are_deterministic_per_symbol(), test_different_symbols_differ(), test_ohlc_are_internally_consistent(), test_quote_is_mock() (+3 more)

### Community 207 - "AnomalyService"
Cohesion: 0.25
Nodes (5): AnomalyService, ndarray, z-score of the last element vs the prior ``used`` elements. Returns ``(z,…, Directional lean of the detected anomaly. A return outlier leans with the sign…, Deterministic last-bar statistical-outlier read over candles.

### Community 208 - "._format_trading_report"
Cohesion: 0.11
Nodes (10): Run one monitoring sweep for a human -- resolve the recorded predictions…, Render a monitoring-sweep dict as honest, plain terminal text., Surface the recorded prediction-audit trail and its track record for a human --…, Render the aggregate track record + the recorded audit trail as honest plain…, A 0-1 fraction as a percentage, or ``-`` when missing., One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.… (+2 more)

### Community 209 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 210 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 211 - "parse_llm_response"
Cohesion: 0.04
Nodes (41): MalformedToolCall, _parse_arguments(), _parse_entry(), parse_llm_response(), ParsedResponse, Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful. (+33 more)

### Community 212 - "Workflow"
Cohesion: 0.10
Nodes (14): _as_float(), Any, Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., An ordered list of steps and the policy for running them., The same workflow, validated instead of executed., Workflow, parametrize (+6 more)

### Community 213 - "PlannerConfig"
Cohesion: 0.15
Nodes (6): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, parametrize, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 215 - "get_logger"
Cohesion: 0.02
Nodes (108): BaseSettings, __init__(), Settings, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+100 more)

### Community 216 - "test_calibration_history.py"
Cohesion: 0.37
Nodes (14): _audit_over(), _derive_over(), _outcome(), asyncio, CalibrationHistoryService: the honest first rung of learning from history. It…, test_correction_is_validated_out_of_sample(), test_empty_history_cannot_measure(), test_is_deterministic() (+6 more)

### Community 217 - "MSSScreen"
Cohesion: 0.09
Nodes (19): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., fake_sct(), FakeSCT, mss_screen() (+11 more)

### Community 218 - "test_ui.py"
Cohesion: 0.11
Nodes (13): cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, ``errors="replace"`` is the second half of the fix. Without it a single…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, The regression itself: this raised UnicodeEncodeError from _show_logo. (+5 more)

### Community 219 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.18
Nodes (11): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, Running out of iterations used to be handled by catching IterationLimitExceeded… (+3 more)

### Community 220 - "memory/tools.py"
Cohesion: 0.46
Nodes (12): _disabled(), find_related_memory(), forget_memory(), get_memory(), list_memories(), _manager(), memory_status(), Any (+4 more)

### Community 221 - "interaction.py"
Cohesion: 0.21
Nodes (10): Run ``goal`` on the shared agent, labelling the turn with ``source``.…, current_interaction(), interaction_scope(), InteractionContext, new_request_id(), The interaction context that tags a run with where it came from. A single…, Where the in-flight turn came from and how to correlate it. Immutable: a turn's…, The context of the turn running in this task, or None outside a scope. (+2 more)

### Community 222 - "safe_preview"
Cohesion: 0.10
Nodes (15): Any, Log-safe projections for trace payloads. The trace persists to disk and renders…, Redact forbidden keys without shortening the surviving values. For the…, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, redact_keys(), safe_metadata() (+7 more)

### Community 223 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 224 - "vision/controller.py"
Cohesion: 0.05
Nodes (51): VisionProvider, Vision system for AetherOS. Provides OCR, object detection, template matching,…, Vision domain models., Any, Represents a template match result., TemplateMatch, BaseVisionProvider, DetectionProvider (+43 more)

### Community 225 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 226 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 227 - "trading/conftest.py"
Cohesion: 0.09
Nodes (34): downtrend_data(), flat_data(), make_invalid_market_data(), fixture, Shared builders for trading tests. These construct MarketData with *controlled*…, A series with a structurally impossible candle (high below low)., uptrend_data(), _analysis_service() (+26 more)

### Community 228 - "AgentStatus"
Cohesion: 0.14
Nodes (7): AgentRunResult, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, AgentStatus, Enum, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…

### Community 229 - "test_monitoring_scheduler.py"
Cohesion: 0.40
Nodes (8): _FakeMonitoring, asyncio, MonitoringScheduler: the bounded, opt-in autonomous loop (spec section 29). A…, _settings(), test_a_failing_sweep_does_not_kill_the_loop(), test_disabled_scheduler_does_not_start(), test_enabled_scheduler_sweeps_then_stops_cleanly(), test_run_once_now_bypasses_the_schedule()

### Community 230 - "Direction"
Cohesion: 0.02
Nodes (197): Any, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, _utcnow(), VolumeAnalysis (+189 more)

### Community 231 - "RejectedToolCall"
Cohesion: 0.18
Nodes (6): A call the planner refused to pass on, and why. Carries enough to answer the…, Whether a ``tool`` message can carry this rejection back. A provider rejects a…, RejectedToolCall, Sort requested calls into ones worth attempting and ones to answer. Malformed…, Check one call against the registry and the validator. Read-only throughout:…, Enabled tool names, sorted, for a message the model has to read.

### Community 232 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 233 - ".assistant"
Cohesion: 0.18
Nodes (5): An assistant turn, optionally carrying the calls the model asked for.…, A long run must not produce an unbounded prompt., `[-0:]` is the whole list, so zero has to be handled explicitly., Nothing in the window announced this id, so the provider would reject it., TestSizeLimits

### Community 234 - "VoiceActivator"
Cohesion: 0.06
Nodes (18): ABC, WakeCallback, Abstract activation source for the voice pipeline. An activator decides *when*…, Activator name, e.g. "push-to-talk"., Whether the activator is currently armed., Arm the activator. `on_activate` may be invoked from a foreign thread, so…, Disarm the activator and release any OS hooks., VoiceActivator (+10 more)

### Community 235 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 236 - "test_anomaly.py"
Cohesion: 0.36
Nodes (9): AnomalyService: deterministic last-bar statistical-outlier detection. These…, _service(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_quiet_tape_is_no_anomaly_and_reliable(), test_return_crash_down_is_anomalous(), test_return_spike_up_is_anomalous_and_reliable(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 237 - "test_breakout.py"
Cohesion: 0.36
Nodes (9): BreakoutService: deterministic channel-breakout detection. The channel/volume…, _service(), test_falling_series_breaks_down(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_range_bound_series_has_no_breakout(), test_rising_series_breaks_out_up(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 238 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 239 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 240 - "utcnow"
Cohesion: 0.15
Nodes (12): datetime, Internal time helpers shared across memory modules (tz-aware UTC)., utcnow(), utcnow_iso(), Knowledge-graph memory (spec Phase 6)., Knowledge-graph store over SQLite (spec Phase 6). Entities and relationships…, MemoryLifecycle, datetime (+4 more)

### Community 241 - "ToolExecutionCoordinator"
Cohesion: 0.11
Nodes (18): Runs one planned tool call through the engine and records what happened. Holds…, ToolExecutionCoordinator, _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation. (+10 more)

### Community 242 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 243 - "test_historical_analogue.py"
Cohesion: 0.39
Nodes (8): HistoricalAnalogueService: deterministic nearest-analogue forward-outcome read.…, _service(), test_falling_tape_leans_down(), test_horizon_override_is_respected(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_rising_tape_leans_up_and_reliable(), test_thin_history_is_unknown_not_fabricated()

### Community 245 - "test_macro.py"
Cohesion: 0.47
Nodes (8): asyncio, MacroContextService: deterministic broad-market risk-posture read. These tests…, _service(), test_is_deterministic(), test_mock_benchmark_is_never_reliable(), test_thin_benchmark_is_unknown_not_fabricated(), test_trending_down_benchmark_is_risk_off(), test_trending_up_benchmark_is_risk_on_and_reliable()

### Community 246 - "FakeScreen"
Cohesion: 0.22
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 249 - "_build"
Cohesion: 0.24
Nodes (9): main(), Run a workflow defined in a JSON file THROUGH the run_workflow tool. This…, _build(), Any, Turn the model's JSON into a validated :class:`Workflow`. Parse errors are re-…, Execute a workflow and return its full execution record. :param name: Label for…, Validate a workflow specification. Executes nothing., run_workflow() (+1 more)

### Community 250 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 252 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 253 - "workflow_believer_run.py"
Cohesion: 0.38
Nodes (6): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows.

### Community 255 - ".save"
Cohesion: 0.25
Nodes (5): ndarray, Path, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region., Save a captured frame to disk.

### Community 256 - "LLMEngine"
Cohesion: 0.11
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 257 - "main"
Cohesion: 0.43
Nodes (6): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms.

### Community 258 - "test_risk.py"
Cohesion: 0.26
Nodes (21): _make_analysis(), _prov(), asyncio, parametrize, RiskService: deterministic risk geometry from a TradingAnalysis. Every number…, Construct a TradingAnalysis directly for precise risk-math assertions., _stable(), _svc() (+13 more)

### Community 259 - ".test_payload_drives_a_real_tool_call_round_trip"
Cohesion: 0.29
Nodes (4): The payload has to be accepted by the engine that already exists., The invariant the provider enforces, asserted over the whole payload., Reads are lock-free because state hands back immutable snapshots., TestProviderCompatibility

### Community 260 - "set_event_bus"
Cohesion: 0.33
Nodes (5): Set the global EventBus instance. This should be called once during application…, set_event_bus(), fixture, Install a fresh bus as the global publisher target, restored afterwards.…, wired()

### Community 261 - "_stable_id"
Cohesion: 0.67
Nodes (3): datetime, Content-addressed id for one prediction (spec section 8). Keyed on the full…, _stable_id()

### Community 262 - "TestMSSSave"
Cohesion: 0.47
Nodes (3): Path, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame…, TestMSSSave

### Community 265 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 270 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3209 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `LLMEngine`, `bootstrap/application.py`, `services/manager.py`, `WindowController`, `ceo_agent_service.py`, `automation/engine.py`, `VerificationResult`, `PaddleOCRProvider`, `audio.py`, `executor.py`, `VoiceConfig`, `Agent`, `agent_memory.py`, `Bootstrapper`, `ContextBuilder`, `ScreenController`, `CommandRegistry`, `SQLiteDatabase`, `PolicyEngine`, `ProcessController`, `ServiceContainer`, `cli/main.py`, `MouseController`, `AgentError`, `agents/core.py`, `TraceEvent`, `strategy.py`, `TerminalService`, `ClipboardService`, `DesktopError`, `ProcessService`, `KeyboardService`, `PlannerConfig`, `Application`, `HUDConfig`, `BrowserProvider`, `YOLOProvider`, `LifecycleManager`, `voice/service.py`, `RecoveryRunner`, `vision/controller.py`, `Instrument`, `Direction`, `ClipboardController`, `VoiceActivator`, `ExecutionConfig`, `VoiceStateMachine`, `safety/policy.py`, `HUDProcess`, `get_settings`, `execution.py`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `ToolCommandService`, `ToolExecutor`, `.test_payload_drives_a_real_tool_call_round_trip`, `asyncio`, `define`, `AutomationEngine`, `automation/engine.py`, `AgentPlanner`, `executor.py`, `test_agent_context.py`, `get_llm_tools`, `test_agent_memory_integration.py`, `test_agent_e2e.py`, `Any`, `ContextBuilder`, `PolicyEngine`, `AgentError`, `tools/__init__.py`, `agents/core.py`, `test_unified_interaction.py`, `FakeLLMProvider`, `test_agent_planner.py`, `PlannerConfig`, `RecoveryRunner`, `ContextBuilder`, `.assistant`, `ExecutionConfig`, `ToolExecutionCoordinator`, `test_agent_execution.py`, `TestFinalResponse`, `execution.py`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `ToolExecutor` connect `ToolExecutor` to `LLMEngine`, `main`, `ToolCommandService`, `define`, `bootstrapper.py`, `Image`, `vision/main.py`, `ceo_agent_service.py`, `AutomationEngine`, `automation/engine.py`, `.executor`, `executor.py`, `VoiceConfig`, `executor`, `test_agent_memory_integration.py`, `test_agent_e2e.py`, `PolicyEngine`, `AgentError`, `ToolRegistry`, `wire`, `tools/__init__.py`, `agents/core.py`, `test_grounding_tools.py`, `test_unified_interaction.py`, `LLMProvider`, `.test_the_registered_engine_is_preferred`, `voice/service.py`, `RecoveryRunner`, `ExecutionConfig`, `main`, `test_agent_execution.py`, `execution.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 95 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 95 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `Instrument` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Instrument` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 21 INFERRED edges - model-reasoned connections that need verification._