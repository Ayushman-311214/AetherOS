# Graph Report - AetherOS  (2026-10-01)

## Corpus Check
- 427 files · ~342,169 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 8490 nodes · 22339 edges · 268 communities (232 shown, 23 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2825 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8ddd675e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- mock_fundamentals_provider.py
- Image
- answer
- define
- bootstrapper.py
- ContextBuilder
- Any
- TextBlock
- Scene
- WindowController
- AutomationEngine
- AgentState
- enums.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- AgentCore
- TradingAnalysis
- trading/tools.py
- get_llm_tools
- Message
- OpenCVProvider
- PlannedAction
- Event
- EventBus
- SourceTier
- VoiceConfig
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- FakeHUDProcess
- Any
- PolicyEngine
- VoiceService
- test_wiring.py
- make_vision_service
- asyncio
- desktop_error.py
- .create
- Direction
- HUDWindow
- ApplicationService
- Instrument
- CLIRuntime
- FileController
- MouseController
- test_calendar.py
- test_performance.py
- CLIUI
- Win32Window
- wire
- VisionError
- policy.py
- test_cli_agent.py
- indicators/core.py
- _RecordingProvider
- PredictionOutcome
- FrameCache
- test_grounding_tools.py
- LLMToolLoop
- TraceEvent
- ._bootstrap_desktop
- grounding/engine.py
- PlaywrightProvider
- TaskManager
- resolve_level
- Any
- ClipboardService
- LiveTraceUI
- VisionProvider
- VoiceActivator
- FakeLLMProvider
- asyncio
- browser/tools.py
- test_track_record_command.py
- LLMProvider
- MemoryProvider
- performance_service.py
- ProcessService
- tool
- PredictionOutcomeStatus
- PlanResult
- KeyboardService
- WindowService
- policy/__init__.py
- YOLOProvider
- HUDConfig
- BrowserProvider
- PortfolioRiskService
- LifecycleManager
- BacktestService
- SpeechToText
- RecoveryRunner
- TestRegistration
- InMemoryPredictionStore
- BrowserService
- parse_llm_response
- LLMEngine
- asyncio
- workflow.py
- MarketEvent
- strategy.py
- ClipboardController
- _state
- StageTimings
- test_fundamentals.py
- ScreenController
- PredictionRecord
- PyAutoGuiKeyboard
- parse_target
- window/tools.py
- get_logger
- _CountingExecutor
- VoiceState
- vision/main.py
- test_regime.py
- HookRecorder
- test_agent_execution.py
- process/tools.py
- .from_events
- vision/tools.py
- MarketData
- FakeProvider
- FakeKeyboard
- test_agent_planner.py
- ExecutionStatus
- ToolCall
- _settings
- test_ui.py
- ToolCommandService
- commands
- TestRegisteredToolSurface
- FakeMouse
- test_interface_contracts.py
- test_orchestration.py
- AgentError
- test_agent.py
- ScreenService
- TestWellFormedCalls
- test_yahoo_calendar_provider.py
- test_analyze_command.py
- CalendarProvider
- .test_is_open_reports_state_without_touching_the_backend
- tools/__init__.py
- SapiTTS
- TimeframeAlignment
- _FakeMouse
- Agent
- test_backtest.py
- .parse
- cli/main.py
- safe_preview
- RenderContext
- LogisticRegression
- PlannerConfig
- TradingReport
- PredictionError
- FakeOCRProvider
- PyAutoGuiMouse
- DivergenceService
- HUDService
- Renderer
- ._run
- _service
- text_match_score
- events/__init__.py
- .test_the_registered_engine_is_preferred
- test_input.py
- AnomalyService
- interaction.py
- import_all.py
- TTLCache
- test_yahoo_news_provider.py
- ToolRegistry
- test_yahoo_fundamentals_provider.py
- PredictionEvaluator
- _settings
- PyAutoGuiClipboard
- screen/tools.py
- test_trading_tools.py
- tool_calls.py
- Box
- voice_error.py
- ._fmt_num
- TestToolsCommand
- RecordingTTS
- make_market_data
- tasks/__init__.py
- _RecordingMouse
- ToolExecutionCoordinator
- OpenAICompatibleProvider
- OpenCVTemplateProvider
- AetherOS
- test_monitoring.py
- observability/__init__.py
- TradingError
- NullTTS
- test_evidence.py
- AgentRunResult
- _one
- Workflow
- scan.py
- test_manager.py
- TechnicalAnalysisService
- test_calibration_history.py
- MSSScreen
- TestToolFailure
- _build
- Application
- ._fmt_pct
- observability/pipeline.py
- ToolDiscovery
- vision/controller.py
- ParsedResponse
- test_anomaly.py
- spatial.py
- RegimeAnalysis
- test_breakout.py
- market_structure_service.py
- _rescale_blocks
- TestPromptCursor
- test_historical_analogue.py
- test_macro.py
- test_tool_calls.py
- TaskContext
- _candidate
- ._format_trading_report
- TestRawArguments
- EventImpact
- _started
- CalendarError
- LLMProviderManager
- main
- .grab
- TestFinalResponse
- _RecordingMouse
- MalformedToolCall
- ._ask
- TraceCollector
- .hud
- .shutdown
- LLMConfig
- Application
- ._format_scan
- ServiceContainer
- .direction
- .direction
- .generate
- _FakeMouseController
- .test_a_finished_run_executes_nothing
- run_workflow_from_file.py
- ._nearest
- .trace
- .voice

## God Nodes (most connected - your core abstractions)
1. `Direction` - 284 edges
2. `ToolRegistry` - 242 edges
3. `Image` - 183 edges
4. `Instrument` - 175 edges
5. `tool()` - 143 edges
6. `AgentState` - 138 edges
7. `get_logger()` - 117 edges
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

## Communities (268 total, 23 thin omitted)

### Community 0 - "mock_fundamentals_provider.py"
Cohesion: 0.05
Nodes (31): FundamentalFactor, FundamentalSnapshot, Any, datetime, Names of the metrics that were actually reported (non-None)., One deterministic signed read the scorer derived from a single metric.…, Content-addressed id: same instrument + source + reporting period -> same id.…, Raw sourced company financials (no interpretation). Missing metric = None. (+23 more)

### Community 1 - "Image"
Cohesion: 0.04
Nodes (25): ColorSpace, Image, ndarray, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV…, Universal image model for AetherOS. Every vision module should consume and… (+17 more)

### Community 2 - "answer"
Cohesion: 0.07
Nodes (47): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+39 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (50): Executes registered AetherOS tools., The registry this executor validates and runs tools from., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes() (+42 more)

### Community 4 - "bootstrapper.py"
Cohesion: 0.04
Nodes (80): Register the deterministic Trading Intelligence core. Self-contained: it…, get_settings(), Singleton Settings object., Map ATR-as-fraction-of-price to a volatility band (deterministic)., MockFundamentalsProvider, A reproducible, clearly-labelled synthetic fundamentals source., MockNewsProvider, A reproducible, clearly-labelled synthetic news source. (+72 more)

### Community 5 - "ContextBuilder"
Cohesion: 0.06
Nodes (41): ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call(), asyncio, ContextBuilder (+33 more)

### Community 6 - "Any"
Cohesion: 0.07
Nodes (22): _clamp(), _describe_call(), _describe_result(), IterationInfo, Any, Observation, Where the run is in its budget. Carried explicitly because the model behaves…, The tool name inside a generated schema, or ``""`` if it is malformed. Tolerant… (+14 more)

### Community 7 - "TextBlock"
Cohesion: 0.07
Nodes (15): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, sample_blocks() (+7 more)

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
Nodes (33): File a failure in the run's error ledger. Field by field rather than by handing…, AgentState, Finish the run successfully. Running out of iterations is a completion, not a…, Stop the run on request. Distinct from failure: nothing went wrong., A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,… (+25 more)

### Community 12 - "enums.py"
Cohesion: 0.03
Nodes (141): BaseSettings, Settings, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, _utcnow(), VolumeAnalysis, AnomalyAnalysis, Any (+133 more)

### Community 13 - "VerificationResult"
Cohesion: 0.05
Nodes (43): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, _parse_condition(), Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, What was checked, what was expected, and what was actually observed. The four… (+35 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (33): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+25 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.08
Nodes (22): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider… (+14 more)

### Community 16 - "AgentCore"
Cohesion: 0.17
Nodes (11): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, Assemble a core from a provider and, optionally, its collaborators. The…, _fake_mouse(), _is_ordered_subsequence(), Any, asyncio (+3 more)

### Community 17 - "TradingAnalysis"
Cohesion: 0.05
Nodes (35): Any, Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, CriticCheck, CriticReport, Any, datetime (+27 more)

### Community 18 - "trading/tools.py"
Cohesion: 0.07
Nodes (66): _analysis(), analyze_fundamentals(), analyze_instrument(), analyze_macro_context(), analyze_market_structure(), analyze_multi_timeframe(), analyze_news_sentiment(), analyze_relative_strength() (+58 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "Message"
Cohesion: 0.06
Nodes (53): QApplication, Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, build_application(), _initial_config(), Any, Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Wait briefly for the parent's opening config message. Without this the window… (+45 more)

### Community 21 - "OpenCVProvider"
Cohesion: 0.06
Nodes (31): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, EnvelopeResult, _ocr_with() (+23 more)

### Community 22 - "PlannedAction"
Cohesion: 0.06
Nodes (19): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim. (+11 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (60): The single trace subscriber (PHASES 2, 6, 8, 9). ``TraceRecorder`` is the one…, Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name., LLMThinkingFinished, LLMThinkingStarted (+52 more)

### Community 24 - "EventBus"
Cohesion: 0.08
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "SourceTier"
Cohesion: 0.05
Nodes (60): Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, NewsAnalysis, NewsItem, Any, Aggregate news sentiment for an instrument, with its full audit trail., Content-addressed id: same headline from the same source -> same id.…, A single sourced headline as a provider returned it (no interpretation). (+52 more)

### Community 26 - "VoiceConfig"
Cohesion: 0.05
Nodes (46): Future, ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Synthesize and play `text`, returning when playback ends. Must not block the… (+38 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.08
Nodes (7): Bootstrapper, Whether Playwright can be imported. find_spec rather than a try/import:…, Coordinates application startup and shutdown. The bootstrapper is responsible…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…

### Community 28 - "DesktopError"
Cohesion: 0.10
Nodes (22): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, PsutilProcess, Any, Path, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Refuse to act on a process that must not be stopped. Returns the psutil handle… (+14 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.09
Nodes (10): CommandHandler, CommandRegistry, Register a CLI command., Execute a parsed command., Registry for AetherOS CLI commands., Render one tool as ``name(arg: type, arg: type = default)``. Names, types, and…, A readable type name for a resolved annotation, or "" when there is no usable…, Render a parameter's default value for display. (+2 more)

### Community 31 - "FakeHUDProcess"
Cohesion: 0.08
Nodes (13): process(), Fixtures for the HUD tests. The process double lives in…, A HUD child process that never launches anything., FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code. (+5 more)

### Community 32 - "Any"
Cohesion: 0.12
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.06
Nodes (36): PolicyConfig, Any, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyEngine, Decides whether one requested tool call may run. Runs nothing. Stateful in…, Latch the stop. Every subsequent :meth:`evaluate` denies until it is cleared --…, Release the stop. Deliberately explicit: nothing clears it on the engine's… (+28 more)

### Community 34 - "VoiceService"
Cohesion: 0.07
Nodes (19): Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,…, Stop and start again., Run one microphone-driven turn., Run one turn from typed text. Works with no microphone at all, which makes it… (+11 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.07
Nodes (29): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+21 more)

### Community 36 - "make_vision_service"
Cohesion: 0.05
Nodes (37): Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), isolated_container(), make_fake_detector(), make_fake_ocr(), make_unclosable_ocr(), make_vision_service(), fixture (+29 more)

### Community 37 - "asyncio"
Cohesion: 0.07
Nodes (26): bus(), fake_process(), make_service(), fixture, A bus isolated from the process-wide publisher., The double's class, for tests that need a differently configured one., Build an unstarted service over a fake process., A started service, stopped again on teardown. `start()` creates the pump task,… (+18 more)

### Community 38 - "desktop_error.py"
Cohesion: 0.05
Nodes (30): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+22 more)

### Community 39 - ".create"
Cohesion: 0.07
Nodes (20): Any, Build an event, defaulting the stage label from the type., A JSONL-ready row: enums as their wire strings, timestamp as ISO-8601., Path, Append trace events to a per-run JSONL file. Files are opened lazily on the…, Append one event to its run's file. Never raises., Flush and close every open file. Safe to call more than once., Reduce a run id to a filename-safe token. ``state_id`` values are already tame,… (+12 more)

### Community 40 - "Direction"
Cohesion: 0.12
Nodes (114): CheckStatus, CriticVerdict, Direction, MarketRegime, Outcome of one critic check. SKIPPED is first-class: a check the current build…, The critic's go/no-go decision on a proposed signal. INSUFFICIENT_EVIDENCE is…, Directional bias of a signal or piece of evidence., The prevailing *character* of the market, classified deterministically from… (+106 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.11
Nodes (22): ApplicationService, Any, Path, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``…, Whether an application is running, by executable name. (+14 more)

### Community 43 - "Instrument"
Cohesion: 0.07
Nodes (41): Supported candle timeframes., Resolve a user/tool string to a Timeframe, raising ValueError if unknown., Timeframe, Instrument, Any, A tradable instrument (equity, crypto pair, index, ...)., InsufficientDataError, MarketDataError (+33 more)

### Community 44 - "CLIRuntime"
Cohesion: 0.20
Nodes (5): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 47 - "test_calendar.py"
Cohesion: 0.18
Nodes (28): MockCalendarProvider, A reproducible, clearly-labelled synthetic event-calendar source., _event(), FakeCalendarProvider, asyncio, Deterministic event / economic-calendar tests (spec sections 5, 9, 21, 28). Two…, A controllable, clearly-synthetic event stamped a non-mock tier., Hands back exactly the events built by the test; non-mock so it can be reliable. (+20 more)

### Community 48 - "test_performance.py"
Cohesion: 0.22
Nodes (23): _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes., _resolved(), _service() (+15 more)

### Community 49 - "CLIUI"
Cohesion: 0.08
Nodes (15): Panel, CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen. (+7 more)

### Community 50 - "Win32Window"
Cohesion: 0.09
Nodes (20): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+12 more)

### Community 51 - "wire"
Cohesion: 0.07
Nodes (27): executor(), asyncio, fixture, Path, Tests for the vision tools and their registry integration. These exercise the…, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in… (+19 more)

### Community 52 - "VisionError"
Cohesion: 0.03
Nodes (53): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError (+45 more)

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

### Community 57 - "PredictionOutcome"
Cohesion: 0.05
Nodes (42): MonitoringReport, Any, datetime, Monitoring-sweep value object. A :class:`MonitoringReport` is the result of one…, One bounded monitoring sweep: resolved outcomes + their aggregate., _utcnow(), PredictionOutcome, Any (+34 more)

### Community 58 - "FrameCache"
Cohesion: 0.12
Nodes (15): FrameCache, Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.…, Drop the cached frame so the next op captures fresh., Return a frame, reusing the cached one when it is fresh enough. Returns…, _Clock, _make_capture(), asyncio, Tests for the short-lived screen-frame cache. The clock is injected so time… (+7 more)

### Community 59 - "test_grounding_tools.py"
Cohesion: 0.09
Nodes (17): _block(), executor(), asyncio, fixture, parametrize, Tests for the grounding tools through the registry and executor. These run the…, Records moves and clicks instead of driving a real pointer., Records what it was asked to type, so a test can prove the keyboard received… (+9 more)

### Community 60 - "LLMToolLoop"
Cohesion: 0.08
Nodes (22): AgentLoopResult, LLMToolLoop, _planned_action_to_tool_call(), Any, ContextBuilder, Outcome of a full loop run., Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls. (+14 more)

### Community 61 - "TraceEvent"
Cohesion: 0.12
Nodes (24): InteractionGateway, Submit a goal to the shared agent, tagged with its front end., One observed moment in a run, safe to log and to persist. Only observable, log-…, TraceEvent, _boom(), _build_agent(), _CountingExecutor, _mouse_position() (+16 more)

### Community 62 - "._bootstrap_desktop"
Cohesion: 0.13
Nodes (15): Process, _clip(), CommandResult, _decode(), Path, Command execution. Three decisions in here are load-bearing. **A non-zero exit…, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment… (+7 more)

### Community 63 - "grounding/engine.py"
Cohesion: 0.10
Nodes (15): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+7 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 66 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 67 - "Any"
Cohesion: 0.07
Nodes (18): ErrorRecord, Any, BaseException, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Finish the run unsuccessfully, recording the unrecoverable error., Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly. (+10 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "LiveTraceUI"
Cohesion: 0.12
Nodes (12): LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing., _NonTerminalConsole, The live terminal dashboard (PHASE 7). The dashboard is pure presentation and… (+4 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "VoiceActivator"
Cohesion: 0.06
Nodes (18): ABC, WakeCallback, Abstract activation source for the voice pipeline. An activator decides *when*…, Activator name, e.g. "push-to-talk"., Whether the activator is currently armed., Arm the activator. `on_activate` may be invoked from a foreign thread, so…, Disarm the activator and release any OS hooks., VoiceActivator (+10 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (15): FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per…, Build a provider response requesting the given ``(name, arguments)`` calls.… (+7 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 74 - "browser/tools.py"
Cohesion: 0.12
Nodes (26): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+18 more)

### Community 75 - "test_track_record_command.py"
Cohesion: 0.10
Nodes (21): BollingerReading, MACDReading, Any, datetime, Technical-analysis value objects. TechnicalSnapshot holds the *latest* scalar…, Latest values of the computed indicators for one timeframe., TechnicalSnapshot, _utcnow() (+13 more)

### Community 76 - "LLMProvider"
Cohesion: 0.13
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "performance_service.py"
Cohesion: 0.05
Nodes (46): CalibrationAudit, Any, datetime, Calibration-audit value object. A :class:`CalibrationAudit` is the honest first…, Realised-calibration measurement over the accumulated prediction history., _utcnow(), PredictionPerformance, Any (+38 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "tool"
Cohesion: 0.09
Nodes (31): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+23 more)

### Community 81 - "PredictionOutcomeStatus"
Cohesion: 0.26
Nodes (26): PredictionOutcomeStatus, The state of a past prediction checked against what actually happened.…, _Bus, _evaluator(), _market_data(), asyncio, datetime, The deterministic prediction-outcome evaluator (spec sections 6, 16, 29). These… (+18 more)

### Community 82 - "PlanResult"
Cohesion: 0.07
Nodes (18): PlanResult, No next step exists. ``error_type`` names the kind of wall hit., What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only… (+10 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (23): Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt…, ``"normal"``, ``"minimized"`` or ``"maximized"``. (+15 more)

### Community 85 - "policy/__init__.py"
Cohesion: 0.10
Nodes (15): Policy configuration: the rules the engine evaluates against. Deliberately…, PolicyDecision, PolicyEvaluation, Any, Enum, str, Policy decisions: the vocabulary the agent policy layer answers in. Three…, What the policy decided about one requested tool call. ``str``-valued so a… (+7 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.05
Nodes (22): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., Any (+14 more)

### Community 87 - "HUDConfig"
Cohesion: 0.03
Nodes (47): IO, Popen, main(), Standalone entry point. Exists so the HUD can be developed and visually…, _as_bool(), _as_float(), _as_int(), _as_text() (+39 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.04
Nodes (25): BrowserProvider, ABC, Any, Path, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element. (+17 more)

### Community 89 - "PortfolioRiskService"
Cohesion: 0.12
Nodes (22): PortfolioCandidate, PortfolioPosition, PortfolioRiskPlan, Any, datetime, Portfolio-risk value objects. Where…, One candidate trade feeding the allocator: its directional risk geometry., A candidate after allocation: its size, risk and notional (or why not). (+14 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "BacktestService"
Cohesion: 0.11
Nodes (13): SignalFn, BacktestResult, Any, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome, BacktestCompleted, A deterministic walk-forward backtest of a signal was completed. (+5 more)

### Community 92 - "SpeechToText"
Cohesion: 0.05
Nodes (29): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+21 more)

### Community 93 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 94 - "TestRegistration"
Cohesion: 0.13
Nodes (8): parametrize, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry…, Resolved annotations are what make ``path`` advertise "string" instead of…, TestRegistration, TestSchema

### Community 95 - "InMemoryPredictionStore"
Cohesion: 0.11
Nodes (31): InMemoryPredictionStore, PredictionStore, ABC, The prediction audit store -- interface plus an in-memory reference impl.…, Append-and-read persistence port for auditable predictions (section 8).…, Persist ``record`` and return its id. Idempotent on the id., Return the recorded prediction with this id, or ``None`` if unknown., Return recorded predictions newest-first. Optionally filtered to one… (+23 more)

### Community 96 - "BrowserService"
Cohesion: 0.08
Nodes (6): BrowserService, The visible text of the whole page. Reuses the provider's existing element-text…, Whether ``query`` appears in the visible text of the current page. A…, Release the browser if one is still open. Called from…, Whether a browser is currently launched. Reads the service's own ``_launched``…, High-level browser service. Responsible for coordinating browser operations.…

### Community 97 - "parse_llm_response"
Cohesion: 0.19
Nodes (6): parse_llm_response(), Normalise a provider tool-call response. Never raises. Accepts the shape…, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn., TestContent

### Community 98 - "LLMEngine"
Cohesion: 0.12
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 99 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 100 - "workflow.py"
Cohesion: 0.07
Nodes (30): _append_recovery_detail(), _backoff_seconds(), Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran…, Delay before the next attempt: exponential, and capped. Exponential because the…, Fold recovery outcomes into the error the step will report if it still fails.… (+22 more)

### Community 101 - "MarketEvent"
Cohesion: 0.08
Nodes (15): EventCalendar, MarketEvent, Any, datetime, Signed days from ``reference`` to the event (negative = already past)., Scheduled events for an instrument within a horizon, with its audit trail., The soonest scheduled event in the horizon, if any., Content-addressed id for one event. Keyed on the scheduled *date* (not the… (+7 more)

### Community 102 - "strategy.py"
Cohesion: 0.07
Nodes (31): Verification — reading state back after a desktop action. The public surface is…, Enum, str, The result contract every desktop tool returns. Before this module every…, Outcome of one desktop action, as the model sees it. Distinct from…, Whether the caller may proceed as if the action happened. False when the…, The JSON shape the model receives. ``verified`` is lifted to the top level…, Outcome of the verification pass for a single action. ``str`` mixin so the… (+23 more)

### Community 103 - "ClipboardController"
Cohesion: 0.07
Nodes (16): ClipboardController, ABC, Any, Path, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"… (+8 more)

### Community 104 - "_state"
Cohesion: 0.14
Nodes (13): Any, Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., ``tool_categories`` narrows the menu to the relevant tools for a run. Left…, A state that has not run yet still produces a usable payload. (+5 more)

### Community 105 - "StageTimings"
Cohesion: 0.12
Nodes (10): Accumulated per-stage timings for one vision request. A plain name ->…, Times named stages when profiling is enabled, and is a no-op otherwise.…, Time the wrapped block. Used around an ``await`` -- ``with…, StageTimings, VisionProfiler, Tests for the opt-in vision profiler. The contract these pin, from §11 of the…, TestDisabledProfilerIsANoop, TestEnabledProfilerRecords (+2 more)

### Community 106 - "test_fundamentals.py"
Cohesion: 0.24
Nodes (22): FakeFundamentalsProvider, asyncio, Deterministic fundamental-analysis tests (spec sections 5, 9, 21, 28). Two…, A controllable, clearly-synthetic snapshot stamped a non-mock tier., Hands back exactly the snapshot the test built; non-mock so it can be reliable., _service(), _snapshot(), test_mock_provider_is_deterministic() (+14 more)

### Community 107 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 108 - "PredictionRecord"
Cohesion: 0.07
Nodes (38): PredictionRecord, Any, datetime, The Prediction Contract value object (spec sections 8, 19, 28). A…, A prediction resting on mock data can never be treated as reliable., Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, Content-addressed id for one prediction (spec section 8). Keyed on the full… (+30 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.11
Nodes (9): Any, PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or… (+1 more)

### Community 110 - "parse_target"
Cohesion: 0.12
Nodes (14): _clean(), _find_element_type(), _find_ordinal(), _find_relation(), parse_target(), Parse a natural-language target into a :class:`GroundingTarget`. Deterministic,…, Return the canonical element type mentioned, longest phrase first., Parse ``query`` into a structured :class:`GroundingTarget`. The residual text… (+6 more)

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "get_logger"
Cohesion: 0.04
Nodes (51): Level 1+2: import every tool module, report registration. The module list is…, ContextBuilder, Agent context assembly. One :class:`AgentContext` is everything the model needs…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, The agent core loop: the driver that turns a goal into a finished run. This is…, Agent-level tool execution. One responsibility: *a planned tool call becomes a…, The one entry a front end submits a turn through. Both the terminal and voice…, Agent layer. Four pieces so far. :mod:`~aetheros.agents.state` is the explicit,… (+43 more)

### Community 113 - "_CountingExecutor"
Cohesion: 0.15
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, _CountingExecutor, Defaults, and the invariant the class docstring states., The real engine, counting how often it was asked. A subclass rather than a…, TestConstruction

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (12): Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state., Move to `target`. Returns True when the state actually changed. Illegal… (+4 more)

### Community 115 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 116 - "test_regime.py"
Cohesion: 0.23
Nodes (16): _FakeBus, asyncio, Market-regime detection: deterministic trending / ranging / volatile reads.…, Records published events; duck-typed stand-in for the EventBus., _service(), test_clean_downtrend_is_trending_down(), test_clean_uptrend_is_trending_up(), test_detect_emits_event_when_bus_wired() (+8 more)

### Community 117 - "HookRecorder"
Cohesion: 0.17
Nodes (11): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The HUD is a child process that can die at any moment. Losing it must cost the… (+3 more)

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
Cohesion: 0.15
Nodes (31): get_frame_cache(), Short-lived screen-frame cache. A desktop agent frequently runs several vision…, Process-wide frame cache, sized from the shared settings object. Built once…, click_grounded_target(), _engine(), ground_target(), Any, Grounding tools: the agent-facing surface of the grounding layer. These are the… (+23 more)

### Community 122 - "MarketData"
Cohesion: 0.03
Nodes (40): BreakoutAnalysis, Any, Deterministic channel-breakout read for one instrument., Whether this read rests on data solid enough to lean on. Mock or unusable data,…, DivergenceAnalysis, Any, Deterministic price-vs-oscillator regular-divergence read., Whether this read rests on data solid enough to lean on. Mock or unusable data,… (+32 more)

### Community 123 - "FakeProvider"
Cohesion: 0.30
Nodes (15): FakeProvider, A controllable, clearly-synthetic provider for service tests. Unlike the mock…, asyncio, MarketDataService: caching, validation, freshness and honest error typing. This…, _service(), test_fresh_series_is_ok(), test_invalid_symbol_raises(), test_non_positive_limit_raises() (+7 more)

### Community 124 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 125 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 126 - "ExecutionStatus"
Cohesion: 0.22
Nodes (6): ExecutionStatus, Enum, str, How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 127 - "ToolCall"
Cohesion: 0.04
Nodes (40): A stable identity for *what this call did*, for loop detection. Two calls share…, AgentExecutionResult, _as_tool_call(), ExecutionBatch, _failure(), Any, A failure in the engine's own currency, for a call the engine never saw.…, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool… (+32 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "test_ui.py"
Cohesion: 0.19
Nodes (10): _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal(), cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must… (+2 more)

### Community 130 - "ToolCommandService"
Cohesion: 0.10
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 132 - "TestRegisteredToolSurface"
Cohesion: 0.08
Nodes (13): fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations… (+5 more)

### Community 134 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 135 - "test_orchestration.py"
Cohesion: 0.16
Nodes (35): The final desk-level recommendation on a composed trading report. A…, ReportRecommendation, _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_report_fuses_anomaly_as_advisory_but_stays_no_trade(), test_report_fuses_breakout_as_advisory_but_stays_no_trade(), test_report_fuses_calendar_as_advisory_but_stays_no_trade() (+27 more)

### Community 136 - "AgentError"
Cohesion: 0.04
Nodes (67): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``… (+59 more)

### Community 137 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 138 - "ScreenService"
Cohesion: 0.12
Nodes (15): ndarray, Path, Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region. (+7 more)

### Community 139 - "TestWellFormedCalls"
Cohesion: 0.15
Nodes (5): SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The OpenAI wire format sends arguments as a JSON *string*., A provider that passes the wire shape through verbatim keeps the name and…, TestWellFormedCalls

### Community 140 - "test_yahoo_calendar_provider.py"
Cohesion: 0.32
Nodes (20): _calendar_payload(), _ok_handler(), _provider(), asyncio, YahooCalendarProvider: the first real event-calendar adapter. These tests are…, A unix timestamp ``days_from_now`` days from now (negative = past)., Build a Yahoo /v10/finance/quoteSummary calendarEvents-shaped payload., test_empty_calendar_is_a_clear_calendar_not_an_error() (+12 more)

### Community 141 - "test_analyze_command.py"
Cohesion: 0.17
Nodes (21): asyncio, The ``analyze`` CLI command: the deterministic trading pipeline surfaced to a…, test_analyze_backtest_flag_includes_backtest(), test_analyze_carries_uncertainty_reminder(), test_analyze_flags_advisory_layers_as_unreliable(), test_analyze_never_fabricates_probability(), test_analyze_not_connected_without_service(), test_analyze_renders_critic_verdict_and_checks() (+13 more)

### Community 142 - "CalendarProvider"
Cohesion: 0.16
Nodes (8): CalendarProvider, ABC, Interface every event/economic-calendar source implements., AsyncClient, datetime, Extract unix-timestamp dates from a calendarEvents field. Yahoo carries a date…, Real scheduled corporate events from Yahoo's public quoteSummary endpoint., YahooCalendarProvider

### Community 143 - ".test_is_open_reports_state_without_touching_the_backend"
Cohesion: 0.24
Nodes (11): _build(), _CountingExecutor, _fake_browser(), Any, asyncio, The real executor, recording every tool it was actually asked to run. A name…, Bind the ``BrowserService`` the tools resolve to a recording provider. Every…, Copy production tool definitions into an isolated registry. (+3 more)

### Community 144 - "tools/__init__.py"
Cohesion: 0.06
Nodes (39): Parameter, Exception, ToolError, is_unconstrained(), public_parameters(), Any, Signature, Annotation resolution shared by the schema generator and the validator. Every… (+31 more)

### Community 145 - "SapiTTS"
Cohesion: 0.14
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 146 - "TimeframeAlignment"
Cohesion: 0.23
Nodes (9): How a base-timeframe directional read sits against the higher timeframe. A…, TimeframeAlignment, _analyse(), _mtf(), asyncio, test_classify_covers_every_alignment(), test_higher_trend_confirms_base_and_is_reliable(), test_is_deterministic() (+1 more)

### Community 148 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 149 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 150 - ".parse"
Cohesion: 0.33
Nodes (11): Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``. Raises ValueError for an empty…, asyncio, Mock market-data provider: reproducibility and honesty. The mock exists so the…, test_candle_count_matches_limit(), test_candles_are_deterministic_per_symbol(), test_different_symbols_differ(), test_ohlc_are_internally_consistent(), test_quote_is_mock() (+3 more)

### Community 151 - "cli/main.py"
Cohesion: 0.13
Nodes (19): CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command., _ask(), _build(), _CountingExecutor (+11 more)

### Community 152 - "safe_preview"
Cohesion: 0.09
Nodes (15): Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, Emit the terminal tool event for a delegated call (PHASE 5). ``describe()`` is…, Any, A truncated, single-block preview of model/tool text. Not a secret filter --…, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary… (+7 more)

### Community 153 - "RenderContext"
Cohesion: 0.06
Nodes (45): QFont, QLinearGradient, QPointF, Layer, ABC, Whether this layer should draw at all this frame., One element of the overlay, drawn back to front. Layers are stateless with…, CoreLayer (+37 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.23
Nodes (7): LogisticRegression, ndarray, Deterministic logistic regression in pure numpy. A small, fully reproducible…, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 156 - "TradingReport"
Cohesion: 0.08
Nodes (13): EvidenceReason, Explanation, Any, datetime, Signal-explanation value object. An :class:`Explanation` answers the spec's…, One line of the consolidated ledger (a compact view of an Evidence item)., A deterministic, read-only explanation of a report's recommendation., _utcnow() (+5 more)

### Community 157 - "PredictionError"
Cohesion: 0.18
Nodes (16): PredictionError, An auditable prediction record could not be built, stored, or read back., FilePredictionStore, Path, A durable, append-only JSON Lines implementation of the same port. Each…, Populate the in-memory index from the file (once). Caller holds lock., asyncio, FilePredictionStore: the durable JSON Lines prediction-audit store. These pin… (+8 more)

### Community 158 - "FakeOCRProvider"
Cohesion: 0.06
Nodes (16): fake_ocr(), FakeDetectionProvider, FakeOCRProvider, FakeScreen, Any, Exception, ndarray, Path (+8 more)

### Community 159 - "PyAutoGuiMouse"
Cohesion: 0.07
Nodes (9): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., Return the current desktop subsystem status., status(), PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController., Return whether the process backend is available. (+1 more)

### Community 160 - "DivergenceService"
Cohesion: 0.18
Nodes (16): DivergenceService, ndarray, Indices that are a strict local min (low) / max (high) over +/-window. Returns…, Classify regular divergence over the two most recent pivots. For lows…, Deterministic price-vs-RSI regular-divergence read over candles., DivergenceService: deterministic price-vs-RSI regular-divergence detection. Two…, _service(), test_clean_series_reads_determinate_direction() (+8 more)

### Community 161 - "HUDService"
Cohesion: 0.05
Nodes (25): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+17 more)

### Community 162 - "Renderer"
Cohesion: 0.09
Nodes (12): QPixmap, GlowCache, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour., Exception, QPainter, Draw one frame. Returns how long it took, in seconds. (+4 more)

### Community 163 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.14
Nodes (9): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, Score a detection ``label`` against a desired element ``target_type``., text_match_score(), _tokens(), type_match_score(), Unit tests for the deterministic match scoring. The scale is graded on purpose…, TestTextMatchScore (+1 more)

### Community 166 - "events/__init__.py"
Cohesion: 0.14
Nodes (16): get_event_bus(), publish(), Set the global EventBus instance. This should be called once during application…, Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been…, Publish an event using the global EventBus., set_event_bus(), clear_subscribers(), get_subscribers() (+8 more)

### Community 167 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 170 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 171 - "AnomalyService"
Cohesion: 0.25
Nodes (5): AnomalyService, ndarray, z-score of the last element vs the prior ``used`` elements. Returns ``(z,…, Directional lean of the detected anomaly. A return outlier leans with the sign…, Deterministic last-bar statistical-outlier read over candles.

### Community 172 - "interaction.py"
Cohesion: 0.21
Nodes (10): Run ``goal`` on the shared agent, labelling the turn with ``source``.…, current_interaction(), interaction_scope(), InteractionContext, new_request_id(), The interaction context that tags a run with where it came from. A single…, Where the in-flight turn came from and how to correlate it. Immutable: a turn's…, The context of the turn running in this task, or None outside a scope. (+2 more)

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 175 - "test_yahoo_news_provider.py"
Cohesion: 0.20
Nodes (23): AsyncClient, datetime, Convert Yahoo's ``providerPublishTime`` (unix seconds) to UTC., Real recent headlines from Yahoo's public search endpoint., YahooNewsProvider, _news_item(), _ok_handler(), _provider() (+15 more)

### Community 176 - "ToolRegistry"
Cohesion: 0.05
Nodes (60): AgentStatus, Enum, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…, Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, boom(), _build() (+52 more)

### Community 177 - "test_yahoo_fundamentals_provider.py"
Cohesion: 0.39
Nodes (14): _ok_handler(), _provider(), asyncio, YahooFundamentalsProvider: the first real fundamentals adapter. These tests are…, Build a Yahoo /v10/finance/quoteSummary-shaped JSON payload., _summary_payload(), test_empty_modules_is_an_honest_empty_snapshot_not_an_error(), test_empty_result_becomes_fundamentals_error() (+6 more)

### Community 178 - "PredictionEvaluator"
Cohesion: 0.19
Nodes (8): _ensure_utc(), PredictionEvaluator, datetime, Fetch the freshest candles for the prediction's instrument, then resolve. A…, Index of the last candle whose open time is at or before the prediction. This…, Treat a naive timestamp as UTC so comparisons never raise or mislead., Deterministic scorer of a past prediction against later market data., Score ``record`` against ``data`` (candles observed after the prediction).…

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "PyAutoGuiClipboard"
Cohesion: 0.13
Nodes (11): Any, Path, PyAutoGuiClipboard, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Return the current clipboard state. The state is inspected once and reused so…, Return the ``win32clipboard`` module. Imported lazily so this module stays… (+3 more)

### Community 181 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 182 - "test_trading_tools.py"
Cohesion: 0.09
Nodes (40): executor(), asyncio, fixture, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_macro_context_tool_is_labelled_mock(), test_analyze_market_structure_tool() (+32 more)

### Community 183 - "tool_calls.py"
Cohesion: 0.29
Nodes (11): _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object., Best-effort text form of a malformed payload, for the error report. (+3 more)

### Community 184 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 185 - "voice_error.py"
Cohesion: 0.06
Nodes (38): LevelCallback, AudioDeviceError, MicrophoneUnavailableError, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed., Base exception for all voice-subsystem errors. Examples: - Microphone… (+30 more)

### Community 186 - "._fmt_num"
Cohesion: 0.20
Nodes (5): Risk-budget a basket of trades for a human -- no LLM involved (spec section 5,…, Render a portfolio-risk plan dict as honest, plain terminal text., A number for display, or ``-`` when it is missing/non-numeric., Explain WHY an instrument's recommendation came out the way it did -- no LLM…, Render an explanation dict as honest, plain terminal text.

### Community 187 - "TestToolsCommand"
Cohesion: 0.13
Nodes (4): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., The list is read live from the registry, so a tool registered after the command…, TestToolsCommand

### Community 188 - "RecordingTTS"
Cohesion: 0.05
Nodes (32): Captured microphone audio., Recording, EchoReasoner, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, Records what would have been spoken. The test double for speech output: it…, RecordingTTS, HookRecorder (+24 more)

### Community 189 - "make_market_data"
Cohesion: 0.21
Nodes (19): downtrend_data(), flat_data(), make_market_data(), datetime, fixture, Shared builders for trading tests. These construct MarketData with *controlled*…, Build a MarketData from a close series with plausible OHLC/volume., uptrend_data() (+11 more)

### Community 190 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 192 - "ToolExecutionCoordinator"
Cohesion: 0.11
Nodes (10): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, One round, several calls: all answered, in order, one at a time., What counts as a validated call, and what is a programming error. These raise… (+2 more)

### Community 193 - "OpenAICompatibleProvider"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 194 - "OpenCVTemplateProvider"
Cohesion: 0.06
Nodes (24): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms., Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider (+16 more)

### Community 205 - "test_monitoring.py"
Cohesion: 0.31
Nodes (12): _Bus, _outcome(), asyncio, The monitoring service: one bounded "Observe Result -> Evaluate" sweep. These…, _record(), _service_with(), test_empty_history_is_a_valid_quiet_sweep(), test_report_to_dict_shape_is_complete() (+4 more)

### Community 206 - "observability/__init__.py"
Cohesion: 0.09
Nodes (28): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), TraceSpan (+20 more)

### Community 207 - "TradingError"
Cohesion: 0.17
Nodes (12): BacktestError, CriticError, IndicatorError, ProbabilityError, A calibrated probability estimate could not be produced honestly., Base class for every Trading Intelligence error., A technical indicator could not be computed., A risk assessment could not be computed from the given inputs. (+4 more)

### Community 208 - "NullTTS"
Cohesion: 0.17
Nodes (3): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…

### Community 209 - "test_evidence.py"
Cohesion: 0.31
Nodes (9): _build(), EvidenceService: turning deterministic reads into sourced, weighted claims. The…, test_every_item_is_weighted_and_typed(), test_evidence_inherits_provenance_and_quality(), test_evidence_is_deterministic(), test_mock_evidence_is_not_reliable(), test_primary_calculated_evidence_is_reliable(), test_uptrend_yields_bullish_leaning_evidence() (+1 more)

### Community 210 - "AgentRunResult"
Cohesion: 0.22
Nodes (3): AgentRunResult, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…

### Community 211 - "_one"
Cohesion: 0.27
Nodes (5): _one(), Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature., A tool message must carry a name, so a nameless call cannot be answered inside…, TestMalformedCalls

### Community 212 - "Workflow"
Cohesion: 0.07
Nodes (25): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows., _as_float(), _clamp_seconds() (+17 more)

### Community 213 - "scan.py"
Cohesion: 0.22
Nodes (8): Any, datetime, Watchlist-scan value objects. A :class:`ScanResult` is the deterministic…, One symbol's compact directional read within a watchlist scan., A ranked watchlist scan over several instruments., ScanEntry, ScanResult, _utcnow()

### Community 214 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 215 - "TechnicalAnalysisService"
Cohesion: 0.14
Nodes (21): Computes latest-value technical readings from a candle series., TechnicalAnalysisService, make_invalid_market_data(), A series with a structurally impossible candle (high below low)., _analysis_service(), asyncio, AnalysisService: the deterministic end-to-end orchestrator. Fusion is a…, test_mock_analysis_is_deterministic() (+13 more)

### Community 216 - "test_calibration_history.py"
Cohesion: 0.47
Nodes (10): _audit_over(), _outcome(), asyncio, CalibrationHistoryService: the honest first rung of learning from history. It…, test_empty_history_cannot_measure(), test_is_deterministic(), test_mock_and_unreliable_outcomes_are_excluded(), test_overconfident_history_is_flagged_with_a_correction() (+2 more)

### Community 217 - "MSSScreen"
Cohesion: 0.07
Nodes (24): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., Return whether screen capture is available., Return the current screen subsystem status., fake_sct() (+16 more)

### Community 219 - "_build"
Cohesion: 0.28
Nodes (9): _build(), list_recovery_strategies(), Any, Turn the model's JSON into a validated :class:`Workflow`. Parse errors are re-…, Execute a workflow and return its full execution record. :param name: Label for…, Validate a workflow specification. Executes nothing., Report the recovery strategies and their current availability., run_workflow() (+1 more)

### Community 220 - "Application"
Cohesion: 0.22
Nodes (5): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application.

### Community 221 - "._fmt_pct"
Cohesion: 0.20
Nodes (5): Run one monitoring sweep for a human -- resolve the recorded predictions…, Render a monitoring-sweep dict as honest, plain terminal text., Surface the recorded prediction-audit trail and its track record for a human --…, Render the aggregate track record + the recorded audit trail as honest plain…, A 0-1 fraction as a percentage, or ``-`` when missing.

### Community 222 - "observability/pipeline.py"
Cohesion: 0.10
Nodes (26): _accumulate_status(), _apply_event(), _detail(), ExecutionPipeline, PipelineStage, PipelineStatus, _presentation_for(), Any (+18 more)

### Community 223 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 224 - "vision/controller.py"
Cohesion: 0.07
Nodes (35): VisionProvider, Vision system for AetherOS. Provides OCR, object detection, template matching,…, Vision domain models., Any, Represents a template match result., TemplateMatch, BaseVisionProvider, DetectionProvider (+27 more)

### Community 225 - "ParsedResponse"
Cohesion: 0.22
Nodes (5): ParsedResponse, Normalised view of one provider response., parametrize, A provider that returned plain text still yields a usable answer., TestDegenerateInput

### Community 226 - "test_anomaly.py"
Cohesion: 0.36
Nodes (9): AnomalyService: deterministic last-bar statistical-outlier detection. These…, _service(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_quiet_tape_is_no_anomaly_and_reliable(), test_return_crash_down_is_anomalous(), test_return_spike_up_is_anomalous_and_reliable(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 227 - "spatial.py"
Cohesion: 0.36
Nodes (10): _Box, center(), distance(), _h_overlap(), Protocol, Pure geometry helpers for spatial grounding. These operate on anything exposing…, Euclidean distance between the two boxes' centres., Whether ``candidate`` stands in ``relation`` to ``anchor``. "below"/"above"… (+2 more)

### Community 228 - "RegimeAnalysis"
Cohesion: 0.06
Nodes (22): Any, Deterministic market-regime classification for one instrument., Directional bias implied by the regime (SIDEWAYS for a range)., Whether this regime read rests on data solid enough to lean on. Mock or…, RegimeAnalysis, AnalysisCompleted, MarketDataUpdated, MarketRegimeDetected (+14 more)

### Community 229 - "test_breakout.py"
Cohesion: 0.36
Nodes (9): BreakoutService: deterministic channel-breakout detection. The channel/volume…, _service(), test_falling_series_breaks_down(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_range_bound_series_has_no_breakout(), test_rising_series_breaks_out_up(), test_thin_data_is_unknown_not_fabricated() (+1 more)

### Community 230 - "market_structure_service.py"
Cohesion: 0.08
Nodes (40): Enum, str, Qualitative risk level for a trade plan. Never a probability. UNKNOWN is first-…, Bump one level toward HIGH; UNKNOWN becomes MEDIUM, HIGH is capped., RiskBand, StructureSignalType, TrendState, Level (+32 more)

### Community 231 - "_rescale_blocks"
Cohesion: 0.42
Nodes (3): Map box coordinates from a downscaled frame back to the original image. Pure…, _rescale_blocks(), TestRescaleBlocks

### Community 232 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 233 - "test_historical_analogue.py"
Cohesion: 0.39
Nodes (8): HistoricalAnalogueService: deterministic nearest-analogue forward-outcome read.…, _service(), test_falling_tape_leans_down(), test_horizon_override_is_respected(), test_is_deterministic(), test_mock_data_is_never_reliable(), test_rising_tape_leans_up_and_reliable(), test_thin_history_is_unknown_not_fabricated()

### Community 234 - "test_macro.py"
Cohesion: 0.47
Nodes (8): asyncio, MacroContextService: deterministic broad-market risk-posture read. These tests…, _service(), test_is_deterministic(), test_mock_benchmark_is_never_reliable(), test_thin_benchmark_is_unknown_not_fabricated(), test_trending_down_benchmark_is_risk_off(), test_trending_up_benchmark_is_risk_on_and_reliable()

### Community 235 - "test_tool_calls.py"
Cohesion: 0.25
Nodes (3): Parsing of provider tool-call responses. Everything the model emits is…, A tool message whose tool_call_id matches nothing in the assistant turn is a…, TestCallIdentifiers

### Community 237 - "_candidate"
Cohesion: 0.29
Nodes (4): _candidate(), Unit tests for the grounding data models. The models carry the public contract,…, TestCandidateGeometry, TestResult

### Community 238 - "._format_trading_report"
Cohesion: 0.25
Nodes (4): One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.…, Run the deterministic trading pipeline for one instrument and render the…

### Community 239 - "TestRawArguments"
Cohesion: 0.29
Nodes (3): The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, TestRawArguments

### Community 240 - "EventImpact"
Cohesion: 0.40
Nodes (6): EventImpact, EventType, Enum, str, Category of a scheduled market event. Inherits ``str`` for JSON output., How disruptive an event is expected to be. A label, never a probability.

### Community 241 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 245 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 246 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 249 - "MalformedToolCall"
Cohesion: 0.50
Nodes (3): MalformedToolCall, A tool call that could not be turned into something executable. Surfaced rather…, Whether this call can be answered with a ``role: "tool"`` message. The OpenAI…

### Community 250 - "._ask"
Cohesion: 0.33
Nodes (3): Send a message to the LLM, letting it call AetherOS tools., Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal.

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 254 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 257 - "ServiceContainer"
Cohesion: 0.08
Nodes (16): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, AgentReasoner, Any (+8 more)

### Community 260 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 266 - "._nearest"
Cohesion: 0.40
Nodes (3): ndarray, Indices of the k nearest rows of ``x`` to ``latest`` in a standardised feature…, Up-rate and mean forward return of the analogues at ``idxs``.

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2922 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `ServiceContainer`, `WindowController`, `enums.py`, `VerificationResult`, `PaddleOCRProvider`, `AgentCore`, `tools/__init__.py`, `Agent`, `Event`, `cli/main.py`, `VoiceConfig`, `Bootstrapper`, `CommandRegistry`, `PolicyEngine`, `desktop_error.py`, `CLIRuntime`, `MouseController`, `policy.py`, `PredictionOutcome`, `LLMToolLoop`, `._bootstrap_desktop`, `Any`, `VoiceActivator`, `test_track_record_command.py`, `performance_service.py`, `ProcessService`, `NullTTS`, `KeyboardService`, `policy/__init__.py`, `YOLOProvider`, `HUDConfig`, `BrowserProvider`, `LifecycleManager`, `Application`, `RecoveryRunner`, `SpeechToText`, `InMemoryPredictionStore`, `vision/controller.py`, `strategy.py`, `ClipboardController`, `market_structure_service.py`, `StageTimings`, `ScreenController`, `_CountingExecutor`, `VoiceState`, `Application`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `ToolCommandService`, `define`, `answer`, `ContextBuilder`, `AutomationEngine`, `AgentPlanner`, `AgentCore`, `tools/__init__.py`, `.test_is_open_reports_state_without_touching_the_backend`, `get_llm_tools`, `cli/main.py`, `PlannerConfig`, `Any`, `PolicyEngine`, `test_cli_agent.py`, `RecordingTTS`, `TraceEvent`, `ToolExecutionCoordinator`, `FakeLLMProvider`, `TestToolFailure`, `RecoveryRunner`, `_state`, `get_logger`, `_CountingExecutor`, `test_agent_execution.py`, `TestFinalResponse`, `test_agent_planner.py`, `ExecutionStatus`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `bootstrapper.py` to `TestRegisteredToolSurface`, `test_orchestration.py`, `AutomationEngine`, `enums.py`, `VerificationResult`, `AgentCore`, `tools/__init__.py`, `TimeframeAlignment`, `test_backtest.py`, `SourceTier`, `Bootstrapper`, `DivergenceService`, `PolicyEngine`, `Direction`, `test_calendar.py`, `test_performance.py`, `policy.py`, `indicators/core.py`, `make_market_data`, `OpenCVTemplateProvider`, `test_monitoring.py`, `PredictionOutcomeStatus`, `Workflow`, `policy/__init__.py`, `TechnicalAnalysisService`, `test_calibration_history.py`, `PortfolioRiskService`, `InMemoryPredictionStore`, `test_anomaly.py`, `workflow.py`, `test_breakout.py`, `strategy.py`, `market_structure_service.py`, `test_historical_analogue.py`, `test_fundamentals.py`, `test_macro.py`, `PredictionRecord`, `get_logger`, `test_regime.py`, `vision/tools.py`, `FakeProvider`, `LLMConfig`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 201 inferred relationships involving `Direction` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Direction` has 201 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `Instrument` (e.g. with `TradingAnalysis` and `AnomalyAnalysis`) actually correct?**
  _`Instrument` has 93 INFERRED edges - model-reasoned connections that need verification._