# Graph Report - AetherOS  (2026-09-29)

## Corpus Check
- 379 files · ~306,683 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 7747 nodes · 19580 edges · 245 communities (213 shown, 20 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 2378 edges (avg confidence: 0.91)
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
- MarketData
- AgentError
- agents/state.py
- PredictionRecord
- Scene
- make_service
- AutomationEngine
- AgentState
- policy.py
- VerificationResult
- PaddleOCRProvider
- AgentPlanner
- CriticService
- HUDService
- test_performance.py
- get_llm_tools
- hud/__init__.py
- VisionService
- PlannedAction
- Event
- EventBus
- PipeReader
- ToolExecutionCoordinator
- Bootstrapper
- DesktopError
- _RecordingProvider
- CommandRegistry
- test_prediction_store.py
- test_news.py
- PolicyEngine
- VoiceService
- test_wiring.py
- safe_metadata
- LLMEngine
- ProcessController
- Detection
- Direction
- HUDWindow
- ApplicationService
- safe_preview
- bootstrapper.py
- FileController
- get_logger
- SourceTier
- InMemoryPredictionStore
- CLIUI
- Win32Window
- wire
- AgentCore
- AgentExecutionResult
- MouseService
- indicators/core.py
- _RecordingProvider
- .create
- FrameCache
- test_grounding_tools.py
- LLMToolLoop
- Instrument
- ToolCall
- test_fundamentals.py
- PlaywrightProvider
- test_cli_agent.py
- vision/main.py
- WindowController
- ClipboardService
- observability/pipeline.py
- VisionProvider
- HUDProcess
- FakeLLMProvider
- asyncio
- PredictionOutcome
- application/tools.py
- LLMProvider
- MemoryProvider
- calibration.py
- ProcessService
- asyncio
- test_prediction_evaluator.py
- PathGuard
- KeyboardService
- WindowService
- make_market_data
- YOLOProvider
- _make_analysis
- BrowserProvider
- HookRecorder
- LifecycleManager
- _RecordingMouse
- parse_llm_response
- TestRegisteredToolSurface
- TestRegistration
- OpenAICompatibleProvider
- BrowserService
- HUDSnapshot
- test_indicators.py
- FakeKeyboard
- Any
- make_vision_service
- FakeHUDProcess
- ClipboardController
- PlannerConfig
- PyAutoGuiMouse
- TaskManager
- VoicePipeline
- test_probability.py
- PyAutoGuiKeyboard
- TextToSpeech
- window/tools.py
- HUDConfig
- ExecutionConfig
- VoiceState
- .test_move_flows_through_the_full_chain_with_arguments
- commands
- get_settings
- test_agent_execution.py
- ServiceContainer
- RenderContext
- workflow.py
- trading/tools.py
- ToolError
- PyAutoGuiClipboard
- process/tools.py
- PlanResult
- resolve_level
- _settings
- test_ui.py
- ToolCommandService
- asyncio
- Renderer
- GlowCache
- test_interface_contracts.py
- test_orchestration.py
- test_agent_observation.py
- .test_the_registered_engine_is_preferred
- ContextBuilder
- _one
- TerminalService
- vision/tools.py
- _state
- test_agent_policy.py
- agents/core.py
- screen/tools.py
- tool
- _FakeMouse
- FasterWhisperSTT
- test_agent.py
- VisionError
- enums.py
- Agent
- RegimeAnalysis
- LogisticRegression
- voice/service.py
- interaction.py
- OpenCVProvider
- ScreenService
- MouseController
- rich_tools
- Step
- test_backtest.py
- .from_events
- _service
- text_match_score
- main
- test_agent_planner.py
- TestToolsCommand
- _feature_columns
- ExecutionStatus
- import_all.py
- TTLCache
- TestServiceInitialisation
- ToolRegistry
- set_event_bus
- audio.py
- _settings
- make_fake_detector
- ._ask
- test_trading_tools.py
- CommandParser
- tasks/__init__.py
- ._format_trading_report
- .test_a_finished_run_executes_nothing
- tool_calls.py
- Box
- VoiceConfig
- Layer
- _RecordingMouse
- AgentStatus
- automation/tools.py
- test_vision_engine.py
- AetherOS
- renderer.py
- TextBlock
- test_manager.py
- LiveTraceUI
- qcolor
- TestPromptCursor
- parametrize
- CLIRuntime
- LLMProviderManager
- TestFinalResponse
- TestEveryToolModuleImports
- .describe
- MSSScreen
- TaskContext
- Application
- PredictionError
- LLMConfig
- TraceEvent
- .generate
- run_workflow_from_file.py
- .to_dict
- ._any_available
- ToolDiscovery
- _win32_clipboard
- .copy_files
- .copy_image
- Provenance
- PulseLayer
- .test_the_full_pipeline_emits_every_stage_in_order
- TickLayer
- TestCallIdentifiers
- outcome.py
- AgentLoopResult
- executor
- RecoveryRunner
- .copy_text
- .shutdown
- TraceCollector
- bootstrapper

## God Nodes (most connected - your core abstractions)
1. `ToolRegistry` - 242 edges
2. `Image` - 183 edges
3. `Direction` - 164 edges
4. `AgentState` - 138 edges
5. `tool()` - 128 edges
6. `Instrument` - 115 edges
7. `get_logger()` - 113 edges
8. `define()` - 106 edges
9. `EventBus` - 103 edges
10. `AgentPlanner` - 102 edges

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

## Communities (245 total, 20 thin omitted)

### Community 0 - "_started"
Cohesion: 0.16
Nodes (12): _call(), asyncio, Argument names may be logged. Argument values may not. ``type_text`` and…, A running, seeded state on its first iteration., A live tool with good arguments: run it, record it, report it., A name the registry has never heard of is refused before delegation., The engine's verdict is captured, not re-derived. The planner checks arguments…, _started() (+4 more)

### Community 1 - "Image"
Cohesion: 0.03
Nodes (28): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+20 more)

### Community 2 - "answer"
Cohesion: 0.08
Nodes (46): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+38 more)

### Community 3 - "define"
Cohesion: 0.06
Nodes (50): Executes registered AetherOS tools., The registry this executor validates and runs tools from., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes() (+42 more)

### Community 4 - "MarketData"
Cohesion: 0.05
Nodes (27): SignalFn, BacktestResult, Any, datetime, Backtest value objects. A :class:`BacktestResult` is the deterministic product…, One walk-forward prediction scored against its realised forward return., Deterministic, reproducible walk-forward evaluation of a signal., TradeOutcome (+19 more)

### Community 5 - "AgentError"
Cohesion: 0.05
Nodes (32): Accept a member or its name; reject anything else. An unknown source is…, ErrorRecord, Message, Any, BaseException, Finish the run successfully. Running out of iterations is a completion, not a…, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Finish the run unsuccessfully, recording the unrecoverable error. (+24 more)

### Community 6 - "agents/state.py"
Cohesion: 0.05
Nodes (45): _clamp(), _describe_call(), _describe_result(), IterationInfo, Any, Observation, Agent context assembly. One :class:`AgentContext` is everything the model needs…, Where the run is in its budget. Carried explicitly because the model behaves… (+37 more)

### Community 7 - "PredictionRecord"
Cohesion: 0.11
Nodes (20): PredictionRecord, Any, datetime, A prediction resting on mock data can never be treated as reliable., Flatten a composed :class:`TradingReport` into its section-8 contract. Reads…, Rebuild a record from its ``to_dict`` form (audit read-back). The inverse of…, Content-addressed id for one prediction (spec section 8). Keyed on the full…, The auditable section-8 contract for one produced trading report. (+12 more)

### Community 8 - "Scene"
Cohesion: 0.04
Nodes (38): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+30 more)

### Community 9 - "make_service"
Cohesion: 0.13
Nodes (15): bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in…, A bus isolated from the process-wide publisher., A HUD child process that never launches anything. (+7 more)

### Community 10 - "AutomationEngine"
Cohesion: 0.08
Nodes (39): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, An ordered list of steps and the policy for running them., Build a workflow from a plain dict, as ``run_workflow`` receives it., The same workflow, validated instead of executed., Workflow, Calls, engine() (+31 more)

### Community 11 - "AgentState"
Cohesion: 0.04
Nodes (27): Write the outcome into the run, then describe it. The record is built before it…, Record the outcome, tolerating a run that ended underneath it. The only way…, File a failure in the run's error ledger. Field by field rather than by handing…, AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, The mutable record of one agent run. Not a dataclass, deliberately. The…, A copy of the effort counters (``llm_calls``, ``tool_calls``, ``step_count``,… (+19 more)

### Community 12 - "policy.py"
Cohesion: 0.15
Nodes (17): Safety — the gates every destructive desktop action passes through. Two…, Capability, Decision, PolicyDecision, Enum, str, The risk policy that gates every desktop action. The rule this module exists to…, Evaluates desktop actions against configuration and caller intent. Stateless.… (+9 more)

### Community 13 - "VerificationResult"
Cohesion: 0.06
Nodes (37): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, What was checked, what was expected, and what was actually observed. The four…, True only for a real, passing check. UNSUPPORTED and SKIPPED are both false… (+29 more)

### Community 14 - "PaddleOCRProvider"
Cohesion: 0.05
Nodes (33): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+25 more)

### Community 15 - "AgentPlanner"
Cohesion: 0.09
Nodes (19): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, Enabled tool names, sorted, for a message the model has to read., _calls(), Argument names may be logged; argument values may not., One well-formed call for a known tool is planned, not executed. (+11 more)

### Community 16 - "CriticService"
Cohesion: 0.09
Nodes (18): CriticCheck, CriticReport, Any, datetime, Critic / validation value objects. A :class:`CriticReport` is the adversary's…, One named check the critic ran, its outcome and a human-readable reason., Deterministic go/no-go verdict on a proposed signal, with its reasoning., True only for an outright APPROVE -- never for REJECT/INSUFFICIENT. (+10 more)

### Community 17 - "HUDService"
Cohesion: 0.06
Nodes (23): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+15 more)

### Community 18 - "test_performance.py"
Cohesion: 0.22
Nodes (23): _Bus, _min_sample(), _pending(), asyncio, The deterministic prediction-performance aggregator (spec sections 6, 9, 28,…, A minimal event bus that records what the service publishes., _resolved(), _service() (+15 more)

### Community 19 - "get_llm_tools"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 20 - "hud/__init__.py"
Cohesion: 0.08
Nodes (28): _initial_config(), Any, Wait briefly for the parent's opening config message. Without this the window…, Where the render process sends messages. Routes to the parent when there is…, _Reporter, The AetherOS heads-up display. Importing this package deliberately does not…, decode(), encode() (+20 more)

### Community 21 - "VisionService"
Cohesion: 0.06
Nodes (24): High-level vision service. Coordinates OCR, computer vision, object detection…, Release provider resources. Each provider is closed independently: one backend…, Reject a missing image here rather than inside a provider. A None slipping…, Whether text recognition can actually run., A serialisable summary of what this service can do., Recognise text in an image. An empty list means "no readable text", which is a…, VisionService, ocr_provider() (+16 more)

### Community 22 - "PlannedAction"
Cohesion: 0.06
Nodes (17): PlannedAction, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner…, Another iteration is needed. Named with a trailing underscore because… (+9 more)

### Community 23 - "Event"
Cohesion: 0.04
Nodes (67): Event, Any, Base class for all events in AetherOS. Every event inherits from this class., Convert event into a serializable dictionary., Returns the event class name., get_event_bus(), publish(), Returns the configured EventBus. Raises: RuntimeError: If EventBus has not been… (+59 more)

### Community 24 - "EventBus"
Cohesion: 0.08
Nodes (19): EventHandler, Any, Drop the in-memory window (PHASE 10 `trace clear`)., A copy of the buffered events, newest last., A flat snapshot for `trace status`., Subscribe to trace events, filter, display and persist them. Everything is…, Subscribe to :class:`TraceEvent` and bring up the dashboard., Unsubscribe, stop the dashboard and flush the file. Idempotent. (+11 more)

### Community 25 - "PipeReader"
Cohesion: 0.10
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 26 - "ToolExecutionCoordinator"
Cohesion: 0.13
Nodes (9): Runs one planned tool call through the engine and records what happened. Holds…, The injected execution engine used for delegated tool calls., The policy gate consulted before delegation, or ``None`` when the coordinator…, Enabled tool names, sorted, for a message the model has to read. Enabled only…, ToolExecutionCoordinator, One round, several calls: all answered, in order, one at a time., What counts as a validated call, and what is a programming error. These raise…, TestCallShapes (+1 more)

### Community 27 - "Bootstrapper"
Cohesion: 0.07
Nodes (10): Bootstrapper, Whether Playwright can be imported. find_spec rather than a try/import:…, Whether PySide6 can be imported. find_spec rather than a try/import, for the…, Park the overlay at IDLE when nothing will publish voice events., Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., The running HUD service, or None when the overlay is not up., Build the YOLO detector when its package and weights are both present. Returns… (+2 more)

### Community 28 - "DesktopError"
Cohesion: 0.07
Nodes (26): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, _from_registry(), Application name resolution. The model asks for "notepad", or "calculator", or…, Look one executable up in App Paths, returning its full path. The value is the…, PsutilProcess, Any (+18 more)

### Community 29 - "_RecordingProvider"
Cohesion: 0.12
Nodes (5): Any, Exception, Path, A ``BrowserProvider`` that records calls instead of driving a browser. Every…, _RecordingProvider

### Community 30 - "CommandRegistry"
Cohesion: 0.09
Nodes (9): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Render one tool as ``name(arg: type, arg: type = default)``. Names, types, and…, A readable type name for a resolved annotation, or "" when there is no usable…, Render a parameter's default value for display., Show LLM provider status and model information., Inspect and control the live execution trace (PHASE 10). Subcommands: trace… (+1 more)

### Community 31 - "test_prediction_store.py"
Cohesion: 0.24
Nodes (17): _Bus, _orchestrator(), asyncio, The prediction audit store: interface, in-memory reference impl, and the…, A minimal event bus that records what the orchestrator publishes., _report(), test_announced_prediction_matches_the_recorded_one(), test_orchestrator_records_prediction_when_store_wired() (+9 more)

### Community 32 - "test_news.py"
Cohesion: 0.07
Nodes (46): NewsItem, Any, Content-addressed id: same headline from the same source -> same id.…, A single sourced headline as a provider returned it (no interpretation)., _stable_id(), Deterministic news & sentiment analysis (spec sections 5, 9, 26 item #9). This…, classify(), LexiconSentiment (+38 more)

### Community 33 - "PolicyEngine"
Cohesion: 0.05
Nodes (30): PolicyConfig, Any, Policy configuration: the rules the engine evaluates against. Deliberately…, Log-safe summary. Validators are reported by count, not identity -- they are…, The rule set one :class:`PolicyEngine` evaluates against. Frozen: a policy that…, PolicyDecision, PolicyEvaluation, Any (+22 more)

### Community 34 - "VoiceService"
Cohesion: 0.06
Nodes (22): AudioCapture, Microphone capture with energy-based silence detection. PortAudio delivers…, Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Any, A flat snapshot for the CLI., Bring the voice subsystem up. (+14 more)

### Community 35 - "test_wiring.py"
Cohesion: 0.08
Nodes (22): _injecting_init(), asyncio, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus., Dropping the reference is not enough: the HUD registers bound methods, so a…, A headless or server install must not try to open a window., Nothing should grab the microphone or install a global hotkey hook unless it… (+14 more)

### Community 36 - "safe_metadata"
Cohesion: 0.18
Nodes (8): Any, Bound the size of an arbitrary value destined for a payload. Scalars pass…, Strip forbidden keys and bound the rest. A defence in depth, not the primary…, safe_metadata(), truncate_value(), Log-safe projections for trace payloads (PHASES 3, 5, 11). The redaction rules…, TestSafeMetadata, TestTruncateValue

### Community 37 - "LLMEngine"
Cohesion: 0.11
Nodes (12): LLMEngine, Any, High-level LLM service. Responsible for generation and tool-calling…, Schemas for the tools this engine will offer the model., Ask the model for a response that may contain tool calls. ``tools`` defaults to…, add(), asyncio, test_legacy_loop_delegates_tool_execution_to_coordinator() (+4 more)

### Community 38 - "ProcessController"
Cohesion: 0.06
Nodes (20): ProcessController, ABC, Any, Path, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running. (+12 more)

### Community 39 - "Detection"
Cohesion: 0.04
Nodes (40): GroundingEngine, The grounding engine: natural-language target -> ranked visual match. The…, Score readable elements against the target by text and by type. OCR blocks are…, Every element as a neutral candidate, for ordinal/spatial selection. Used only…, Keep only candidates standing in the requested relation to the anchor. The…, Resolve a target phrase to an on-screen element using existing vision., Vision grounding: resolve a natural-language target into screen coordinates.…, GroundingCandidate (+32 more)

### Community 40 - "Direction"
Cohesion: 0.18
Nodes (72): CheckStatus, CriticVerdict, Direction, MarketRegime, str, Outcome of one critic check. SKIPPED is first-class: a check the current build…, The critic's go/no-go decision on a proposed signal. INSUFFICIENT_EVIDENCE is…, Directional bias of a signal or piece of evidence. (+64 more)

### Community 41 - "HUDWindow"
Cohesion: 0.07
Nodes (19): QMouseEvent, QPaintEvent, QWidget, Renderer, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own… (+11 more)

### Community 42 - "ApplicationService"
Cohesion: 0.11
Nodes (22): ApplicationService, Any, Path, Application service. An application is not a process, and conflating the two is…, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``… (+14 more)

### Community 43 - "safe_preview"
Cohesion: 0.13
Nodes (10): _planned_to_call(), Turn a planned tool call into the :class:`ToolCall` an assistant message needs…, Run one goal to a terminal state and report the outcome. Creates and seeds a…, The OBSERVE -> CONTEXT -> PLAN -> POLICY -> EXECUTE -> RECORD cycle. Mirrors…, Record one :class:`Observation` per delegated tool result. A refused call…, A stable identity for *what this call did*, for loop detection. Two calls share…, Emit the terminal tool event for a delegated call (PHASE 5). ``describe()`` is…, A truncated, single-block preview of model/tool text. Not a secret filter --… (+2 more)

### Community 44 - "bootstrapper.py"
Cohesion: 0.04
Nodes (41): Register the deterministic Trading Intelligence core. Self-contained: it…, CalibrationMetrics, ProbabilityEstimate, Any, datetime, Probability-estimate value objects (spec sections 3, 6, 8).…, Out-of-sample calibration/accuracy measures over one evaluation slice., A calibrated directional probability with its full audit trail. (+33 more)

### Community 45 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 46 - "get_logger"
Cohesion: 0.13
Nodes (14): __init__(), Application, Main AetherOS application. Responsible for starting and shutting down the…, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+6 more)

### Community 47 - "SourceTier"
Cohesion: 0.05
Nodes (61): Provenance tier for an observation. MOCK is a first-class tier so…, SourceTier, EventCalendar, EventImpact, EventType, MarketEvent, Any, datetime (+53 more)

### Community 48 - "InMemoryPredictionStore"
Cohesion: 0.29
Nodes (19): InMemoryPredictionStore, Process-local reference store. Deterministic, dependency-free, non-durable.…, _FakeEvaluator, asyncio, The prediction track-record service: the on-demand composition of the audit…, A minimal, hand-built recorded prediction with a fixed content id., A RESOLVED, optionally-graded outcome for the fake evaluator to hand back., Returns a pre-baked outcome per record id; raises for flagged ids. (+11 more)

### Community 49 - "CLIUI"
Cohesion: 0.09
Nodes (13): CLIUI, _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, Make the terminal caret visible. Best-effort and never raises. A no-op off a…, Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI., ``errors="replace"`` is the second half of the fix. Without it a single… (+5 more)

### Community 50 - "Win32Window"
Cohesion: 0.10
Nodes (18): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+10 more)

### Community 51 - "wire"
Cohesion: 0.08
Nodes (23): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., ultralytics and its weights are optional, so the agent has to be told the… (+15 more)

### Community 52 - "AgentCore"
Cohesion: 0.09
Nodes (28): AgentCore, ContextBuilder, Drives one goal to a terminal state, one iteration at a time. Holds no mutable…, InteractionGateway, The one entry a front end submits a turn through. Both the terminal and voice…, Submit a goal to the shared agent, tagged with its front end., new_session_id(), A fresh per-session id for a front end that owns one gateway. (+20 more)

### Community 53 - "AgentExecutionResult"
Cohesion: 0.06
Nodes (18): AgentExecutionResult, ExecutionBatch, Any, The outcome of one tool call, as the agent layer sees it. Frozen: what a tool…, Turned away by this layer, without the engine being asked., Sorted names, no values -- the log-safe half of the arguments. ``type_text``…, Faithful, and therefore not safe for the log sinks. Holds the argument values…, Log-safe: names, outcomes and timings, never values. ``error`` is included… (+10 more)

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
Nodes (18): LLMToolLoop, Any, ContextBuilder, Main LLM ↔ tool-coordination loop., The agent-layer coordinator used by legacy loop calls., Run the loop against AgentState and the agent-layer coordinator. The existing…, Run the loop and return the model's final answer text., Run the loop and return the full record of what happened. (+10 more)

### Community 61 - "Instrument"
Cohesion: 0.05
Nodes (65): AsyncClient, Supported candle timeframes., Timeframe, Instrument, Any, Instrument identity. A tradable thing AetherOS can analyse. Symbol…, A tradable instrument (equity, crypto pair, index, ...)., Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``. Raises ValueError for an empty… (+57 more)

### Community 62 - "ToolCall"
Cohesion: 0.07
Nodes (23): _as_tool_call(), _failure(), A failure in the engine's own currency, for a call the engine never saw.…, Run one validated call and record the round it produced. Accepts either shape a…, Run several calls in order, one at a time, answering all of them. The iteration…, ``exists`` before ``get``, because ``get`` raises ``KeyError``. An invented…, Record a call that was turned away, without the engine being asked. The refusal…, Report a refusal that could not be written down. Reached only when the run is… (+15 more)

### Community 63 - "test_fundamentals.py"
Cohesion: 0.10
Nodes (33): FundamentalSnapshot, Any, Names of the metrics that were actually reported (non-None)., Raw sourced company financials (no interpretation). Missing metric = None., FundamentalsProvider, ABC, Interface every fundamentals source implements., Return the latest reported financials for the instrument. Must raise a… (+25 more)

### Community 64 - "PlaywrightProvider"
Cohesion: 0.06
Nodes (8): BrowserContext, Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…, The browser context, or a diagnosable error. Reaching through ``self._context``…

### Community 65 - "test_cli_agent.py"
Cohesion: 0.14
Nodes (20): _ask(), _build(), _CountingExecutor, invoked(), mouse_position(), move_mouse(), Any, asyncio (+12 more)

### Community 66 - "vision/main.py"
Cohesion: 0.13
Nodes (17): Check, main(), Vision engine verification entry point. Run with:: python -m…, Drive OCR through the tool registry, the way an agent would., Run every verification stage., Runs the verification stages and collects their results., start(), VisionVerifier (+9 more)

### Community 67 - "WindowController"
Cohesion: 0.07
Nodes (19): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+11 more)

### Community 68 - "ClipboardService"
Cohesion: 0.10
Nodes (17): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+9 more)

### Community 69 - "observability/pipeline.py"
Cohesion: 0.10
Nodes (26): _accumulate_status(), _apply_event(), _detail(), ExecutionPipeline, PipelineStage, PipelineStatus, _presentation_for(), Any (+18 more)

### Community 70 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 71 - "HUDProcess"
Cohesion: 0.09
Nodes (14): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+6 more)

### Community 72 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 73 - "asyncio"
Cohesion: 0.06
Nodes (20): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+12 more)

### Community 74 - "PredictionOutcome"
Cohesion: 0.12
Nodes (12): PredictionOutcome, Any, The auditable result of checking one prediction against later market data., A resolved, directional outcome that was actually graded hit/miss., _ensure_utc(), PredictionEvaluator, datetime, Fetch the freshest candles for the prediction's instrument, then resolve. A… (+4 more)

### Community 75 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 76 - "LLMProvider"
Cohesion: 0.12
Nodes (8): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Returns True if provider is healthy., Abstract base class for all LLM providers. Every provider (OpenAI, Ollama,…

### Community 77 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 78 - "calibration.py"
Cohesion: 0.11
Nodes (23): datetime, Aggregate prediction-performance value object (spec sections 6, 9, 28, 29).…, _utcnow(), accuracy(), brier_score(), CalibrationReport, _clip01(), expected_calibration_error() (+15 more)

### Community 79 - "ProcessService"
Cohesion: 0.11
Nodes (11): ProcessService, Any, Path, Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching… (+3 more)

### Community 80 - "asyncio"
Cohesion: 0.10
Nodes (9): asyncio, parametrize, No readable text is an outcome, not a failure., The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing (+1 more)

### Community 81 - "test_prediction_evaluator.py"
Cohesion: 0.26
Nodes (26): PredictionOutcomeStatus, The state of a past prediction checked against what actually happened.…, _Bus, _evaluator(), _market_data(), asyncio, datetime, The deterministic prediction-outcome evaluator (spec sections 6, 16, 29). These… (+18 more)

### Community 82 - "PathGuard"
Cohesion: 0.11
Nodes (21): PathLike, PathAccess, PathGuard, PathVerdict, Enum, Path, str, Path validation for the filesystem and application tools. A model that can… (+13 more)

### Community 83 - "KeyboardService"
Cohesion: 0.06
Nodes (21): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab (+13 more)

### Community 84 - "WindowService"
Cohesion: 0.08
Nodes (22): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+14 more)

### Community 85 - "make_market_data"
Cohesion: 0.07
Nodes (62): DataQualityStatus, Computes latest-value technical readings from a candle series., TechnicalAnalysisService, downtrend_data(), FakeProvider, flat_data(), make_invalid_market_data(), make_market_data() (+54 more)

### Community 86 - "YOLOProvider"
Cohesion: 0.08
Nodes (16): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Decide which torch device detection runs on. Empty preference means auto: CUDA…, Whether detection can run without a download., YOLOProvider, _force_cuda(), Tests for the vision providers' performance-oriented internals. These pin the… (+8 more)

### Community 87 - "_make_analysis"
Cohesion: 0.16
Nodes (27): Qualitative risk level for a trade plan. Never a probability. UNKNOWN is first-…, Map ATR-as-fraction-of-price to a volatility band (deterministic)., Bump one level toward HIGH; UNKNOWN becomes MEDIUM, HIGH is capped., RiskBand, _stronger(), _levels(), _make_analysis(), _prov() (+19 more)

### Community 88 - "BrowserProvider"
Cohesion: 0.04
Nodes (25): BrowserProvider, ABC, Any, Path, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element. (+17 more)

### Community 89 - "HookRecorder"
Cohesion: 0.16
Nodes (12): add(), explodes(), HookRecorder, Any, asyncio, The tool-progress hooks on the agent loop. These exist for a presentation…, `run` is the entry point the reasoner used to call; the hooks must not be…, The repeat guard refuses to run the call at all, so a display that showed… (+4 more)

### Community 90 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 91 - "_RecordingMouse"
Cohesion: 0.11
Nodes (3): A ``MouseController`` sitting where PyAutoGUI would. Reports a fixed position…, _RecordingMouse, The list is read live from the registry, so a tool registered after the command…

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

### Community 97 - "HUDSnapshot"
Cohesion: 0.09
Nodes (20): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., Build a snapshot for one state, with plausible sample content. Used by `hud…, A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:… (+12 more)

### Community 99 - "FakeKeyboard"
Cohesion: 0.05
Nodes (25): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, _call(), FakeKeyboard, FakeMouse, keyboard(), mouse(), Any, asyncio (+17 more)

### Community 100 - "Any"
Cohesion: 0.12
Nodes (15): _FailingProvider, Any, asyncio, BaseException, ContextBuilder, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise. (+7 more)

### Community 101 - "make_vision_service"
Cohesion: 0.21
Nodes (15): make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., _block(), _det(), _engine(), asyncio, Unit tests for the grounding engine. The engine ties parsing, scoring, spatial… (+7 more)

### Community 102 - "FakeHUDProcess"
Cohesion: 0.08
Nodes (12): ready_message(), stats_message(), FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first. (+4 more)

### Community 103 - "ClipboardController"
Cohesion: 0.12
Nodes (9): ClipboardController, ABC, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"…, Returns clipboard text., Abstract interface for clipboard operations. Every clipboard implementation… (+1 more)

### Community 104 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 105 - "PyAutoGuiMouse"
Cohesion: 0.10
Nodes (5): main(), Is move_relative's round trip exact? §6 'incorrect coordinate handling'., PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 107 - "VoicePipeline"
Cohesion: 0.11
Nodes (17): Speech synthesis playback ended., SpeechFinished, Any, Run one microphone-driven turn, start to finish., Run one turn from typed text, skipping capture and recognition. This is how the…, Speak `text` without reasoning about it., Stop capturing but let the rest of the turn proceed. This is what a second…, Abandon the current turn and return to IDLE. (+9 more)

### Community 108 - "test_probability.py"
Cohesion: 0.25
Nodes (19): _learnable_closes(), asyncio, ndarray, _random_walk_closes(), ProbabilityService: deterministic, calibrated, look-ahead-safe probability.…, A bar's feature vector must not change when future bars are appended., Build a valid OHLCV series from a list/array of closes., A smooth multi-cycle series: recent momentum genuinely predicts the next few… (+11 more)

### Community 109 - "PyAutoGuiKeyboard"
Cohesion: 0.11
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 110 - "TextToSpeech"
Cohesion: 0.05
Nodes (26): ABC, AmplitudeCallback, Abstract base class for all speech-synthesis providers. Implementations must be…, Provider name, e.g. "edge-tts"., Acquire synthesis resources., Release synthesis and playback resources., Synthesize and play `text`, returning when playback ends. Must not block the…, Stop playback immediately. Safe to call when nothing is playing. (+18 more)

### Community 111 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 112 - "HUDConfig"
Cohesion: 0.07
Nodes (27): QApplication, build_application(), main(), Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Run driven by a parent process over stdio. This is how HUDService starts the…, Standalone entry point. Exists so the HUD can be developed and visually…, Create the QApplication with high-DPI behaviour set correctly. The rounding…, run_hud() (+19 more)

### Community 113 - "ExecutionConfig"
Cohesion: 0.14
Nodes (6): ExecutionConfig, What the coordinator records, and how loudly. Both defaults are the strict…, Defaults, and the invariant the class docstring states., A tool that ran and raised is data, not an exception., TestConstruction, TestToolFailure

### Community 114 - "VoiceState"
Cohesion: 0.09
Nodes (13): Queue a state event. The state machine is synchronous, so publishing is…, Enum, str, Lifecycle state of a single voice interaction. A typical conversational turn:…, Guards voice-state transitions and notifies listeners. The state machine is…, Whether a turn is currently in flight., Whether a new voice turn may begin., Whether moving to `target` is legal from the current state. (+5 more)

### Community 115 - ".test_move_flows_through_the_full_chain_with_arguments"
Cohesion: 0.17
Nodes (13): _ask(), _build(), _CountingExecutor, _fake_mouse(), Any, asyncio, Bind the ``MouseService`` the tools resolve to a recording controller. The real…, Copy one *production* tool definition into an isolated registry. (+5 more)

### Community 116 - "commands"
Cohesion: 0.16
Nodes (16): capture_screen(), click(), commands(), move_mouse(), move_mouse_relative(), optional_arg(), Any, fixture (+8 more)

### Community 117 - "get_settings"
Cohesion: 0.06
Nodes (43): get_settings(), Singleton Settings object., _backoff_seconds(), Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Delay before the next attempt: exponential, and capped. Exponential because the…, Trim a tool's return value to something a result can carry., _summarise_value() (+35 more)

### Community 118 - "test_agent_execution.py"
Cohesion: 0.09
Nodes (29): add_async(), coordinator(), _CountingExecutor, executor(), explodes(), journal(), _journalled(), move_mouse() (+21 more)

### Community 119 - "ServiceContainer"
Cohesion: 0.13
Nodes (10): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, boot(), _clean_env() (+2 more)

### Community 120 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 121 - "workflow.py"
Cohesion: 0.09
Nodes (24): Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be…, Precondition → wait → (execute → verify → retry) → wait., Undo the steps that succeeded, most recent first. Only steps that actually ran…, Automation — multi-step desktop work with verification, retries and rollback.…, ExecutionResult, ExecutionStatus, new_execution_id() (+16 more)

### Community 122 - "trading/tools.py"
Cohesion: 0.13
Nodes (34): _analysis(), analyze_fundamentals(), analyze_instrument(), analyze_market_structure(), analyze_news_sentiment(), assess_risk(), _backtest(), backtest_signal() (+26 more)

### Community 123 - "ToolError"
Cohesion: 0.15
Nodes (9): Exception, ToolError, Any, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools. (+1 more)

### Community 124 - "PyAutoGuiClipboard"
Cohesion: 0.22
Nodes (4): Any, Path, PyAutoGuiClipboard, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…

### Community 125 - "process/tools.py"
Cohesion: 0.21
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 126 - "PlanResult"
Cohesion: 0.08
Nodes (15): PlanResult, No next step exists. ``error_type`` names the kind of wall hit., What one planning round produced. The question the planner answers is singular…, The next action. Never absent -- see :meth:`__post_init__`., Whether the caller should plan again. True for ``continue`` and for tool calls…, Any, Exception, Ask the model what to do next, and describe the answer as an action. The only… (+7 more)

### Community 127 - "resolve_level"
Cohesion: 0.11
Nodes (13): IntEnum, level_for_event(), The minimum level at which an event of this type/status is shown. A…, Ordered verbosity. Higher shows strictly more. ``IntEnum`` so ``event_level <=…, Coerce a config value into a :class:`TraceLevel`, defaulting to NORMAL.…, resolve_level(), TraceLevel, Consume one trace event. Sync, on the publish path, never raises. Kept… (+5 more)

### Community 128 - "_settings"
Cohesion: 0.14
Nodes (11): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the Vision performance settings. These pin the…, The defaults must reproduce the pre-optimisation behaviour exactly., _settings(), TestDefaultsPreserveHistoricalBehaviour (+3 more)

### Community 129 - "test_ui.py"
Cohesion: 0.24
Nodes (7): cp1252_stdout(), fixture, MonkeyPatch, The terminal UI must not be able to abort the application. Bootstrap succeeding…, Exiting AetherOS -- cleanly, by exception, or by Ctrl+C during startup -- must…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, TestTerminalRestoredOnExit

### Community 130 - "ToolCommandService"
Cohesion: 0.11
Nodes (10): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, commands(), fixture, main() (+2 more)

### Community 131 - "asyncio"
Cohesion: 0.26
Nodes (6): Any, asyncio, Best-effort emission and the timed span context (PHASES 2, 5, 12). The contract…, TestEmitTraceIsBestEffort, TestEmitTracePublishes, TestTraceContext

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
Cohesion: 0.24
Nodes (21): The final desk-level recommendation on a composed trading report. A…, ReportRecommendation, _orchestrator(), asyncio, OrchestrationService: the deterministic end-to-end trading-desk pipeline. These…, test_report_fuses_calendar_as_advisory_but_stays_no_trade(), test_report_fuses_fundamentals_as_advisory_but_stays_no_trade(), test_report_fuses_news_as_advisory_but_stays_no_trade() (+13 more)

### Community 136 - "test_agent_observation.py"
Cohesion: 0.04
Nodes (64): browser_observation(), _mean_confidence(), _outcome_description(), Any, Observation, Factories that turn what a subsystem produced into an :class:`Observation`.…, Observe that a screenshot exists on disk. Reuses ``ScreenService``: the caller…, Observe what the vision layer read off an image. Consumes ``VisionService``… (+56 more)

### Community 137 - ".test_the_registered_engine_is_preferred"
Cohesion: 0.17
Nodes (12): add(), make_reasoner(), asyncio, fixture, Bootstrap registers an LLMEngine whose tool_provider is bound to the live…, A tool is registered so the loop takes its tool-calling path; with an empty…, The spoken prompt is the reasoner's only real contribution; the loop's own…, This is the entire producer side of the HUD's EXECUTING state. Before the loop… (+4 more)

### Community 138 - "ContextBuilder"
Cohesion: 0.06
Nodes (43): ContextBuilder, ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call() (+35 more)

### Community 139 - "_one"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 140 - "TerminalService"
Cohesion: 0.13
Nodes (15): Process, _clip(), CommandResult, _decode(), Path, Command execution. Three decisions in here are load-bearing. **A non-zero exit…, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment… (+7 more)

### Community 141 - "vision/tools.py"
Cohesion: 0.07
Nodes (42): get_frame_cache(), Short-lived screen-frame cache. A desktop agent frequently runs several vision…, Process-wide frame cache, sized from the shared settings object. Built once…, click_grounded_target(), _engine(), ground_target(), Any, Grounding tools: the agent-facing surface of the grounding layer. These are the… (+34 more)

### Community 142 - "_state"
Cohesion: 0.14
Nodes (13): Any, Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator., No second registry: an isolated one must not see the singleton's tools., ``tool_categories`` narrows the menu to the relevant tools for a run. Left…, A state that has not run yet still produces a usable payload. (+5 more)

### Community 143 - "test_agent_policy.py"
Cohesion: 0.15
Nodes (21): _call(), _coordinator(), _CountingExecutor, executor(), move_mouse(), Any, asyncio, fixture (+13 more)

### Community 144 - "agents/core.py"
Cohesion: 0.06
Nodes (38): Level 1+2: import every tool module, report registration. The module list is…, Parameter, The agent core loop: the driver that turns a goal into a finished run. This is…, is_unconstrained(), public_parameters(), Any, Signature, Annotation resolution shared by the schema generator and the validator. Every… (+30 more)

### Community 145 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 146 - "tool"
Cohesion: 0.15
Nodes (29): _browser(), browser_back(), browser_find_text(), browser_forward(), browser_is_open(), browser_press_key(), browser_reload(), browser_screenshot() (+21 more)

### Community 148 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 149 - "test_agent.py"
Cohesion: 0.15
Nodes (13): agent_parts(), CancellingLoop, CompletingLoop, ContextBuilder, FailingLoop, asyncio, fixture, RecordingPlanner (+5 more)

### Community 150 - "VisionError"
Cohesion: 0.05
Nodes (55): BaseError, ErrorContext, Any, Exception, Additional information about an error., Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError (+47 more)

### Community 151 - "enums.py"
Cohesion: 0.03
Nodes (98): BaseSettings, Settings, Enumerations shared across the Trading Intelligence domain. Every enum inherits…, datetime, Market-data value objects: Candle, Quote, MarketData. MarketData is the…, _utcnow(), The Prediction Contract value object (spec sections 8, 19, 28). A…, datetime (+90 more)

### Community 152 - "Agent"
Cohesion: 0.12
Nodes (8): Agent, Any, ContextBuilder, Exception, Build the bounded model projection for ``state``., High-level orchestrator for one task and one runtime state., Execute ``goal`` and return the state owned by this run., The singleton exists for parity with schema_generator/tool_executor.

### Community 153 - "RegimeAnalysis"
Cohesion: 0.14
Nodes (10): Any, datetime, Market-regime value object. A ``RegimeAnalysis`` is the deterministic read of…, Deterministic market-regime classification for one instrument., Directional bias implied by the regime (SIDEWAYS for a range)., Whether this regime read rests on data solid enough to lean on. Mock or…, RegimeAnalysis, _utcnow() (+2 more)

### Community 154 - "LogisticRegression"
Cohesion: 0.23
Nodes (7): LogisticRegression, ndarray, Deterministic logistic regression in pure numpy. A small, fully reproducible…, P(y=1) for each row of X., A deterministic L2-regularised logistic classifier (batch gradient descent)., Raw logits (w·x + b) -- the natural input to Platt calibration., _sigmoid()

### Community 155 - "voice/service.py"
Cohesion: 0.04
Nodes (38): ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources., Release model and resources. (+30 more)

### Community 156 - "interaction.py"
Cohesion: 0.32
Nodes (7): interaction_scope(), InteractionContext, new_request_id(), The interaction context that tags a run with where it came from. A single…, Where the in-flight turn came from and how to correlate it. Immutable: a turn's…, A fresh per-turn correlation id., Tag everything emitted inside the block with one interaction context. Wrap the…

### Community 157 - "OpenCVProvider"
Cohesion: 0.04
Nodes (39): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., OpenCVTemplateProvider, Template matching using OpenCV. (+31 more)

### Community 158 - "ScreenService"
Cohesion: 0.04
Nodes (41): _bench(), _cuda(), _have(), main(), Vision performance benchmark — REAL numbers only. Measures the stages that can…, Time ``fn`` ``iterations`` times and print avg/min/max in ms., ABC, Any (+33 more)

### Community 159 - "MouseController"
Cohesion: 0.07
Nodes (12): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Returns True if the button is currently held down. Declared here because…, Get the current mouse position. Returns: (x, y) (+4 more)

### Community 160 - "rich_tools"
Cohesion: 0.12
Nodes (19): boom(), check_playing(), click_element(), ground_target(), move_mouse(), open_browser(), fixture, Click an element, reporting success but changing nothing (test double). The… (+11 more)

### Community 161 - "Step"
Cohesion: 0.07
Nodes (23): brave_windows(), build_workflow(), main(), Phase 5 runner for Task 4: execute ONE real automation workflow against the…, The one real workflow, built with the actual Step/Workflow API, using the…, Ground truth from the real desktop: titles of visible Brave windows., _as_float(), _clamp_seconds() (+15 more)

### Community 162 - "test_backtest.py"
Cohesion: 0.30
Nodes (18): _always_down(), _always_up(), asyncio, BacktestService: deterministic, look-ahead-safe walk-forward evaluation. Every…, The signal must only ever see bars up to the bar it predicts from., Build a valid OHLCV series from a list of closes for exact math., _series(), _stable() (+10 more)

### Community 163 - ".from_events"
Cohesion: 0.21
Nodes (8): Fold the recorder's event window into the pipeline for one run. The target run…, _ev(), The execution-pipeline projection. These tests hold the *observational* fold to…, _single_tool_run(), TestFold, TestIterations, TestSafety, TestStatus

### Community 164 - "_service"
Cohesion: 0.25
Nodes (5): asyncio, Unit tests for :class:`BrowserService`. The service owns no browser of its own:…, _service(), TestBrowserServiceDelegation, TestBrowserServiceLifecycle

### Community 165 - "text_match_score"
Cohesion: 0.10
Nodes (19): Deterministic match scoring for grounding candidates. Kept separate from the…, Score how well ``candidate`` text satisfies the ``target`` label. * exact…, Score a detection ``label`` against a desired element ``target_type``., text_match_score(), _tokens(), type_match_score(), _Box, center() (+11 more)

### Community 167 - "test_agent_planner.py"
Cohesion: 0.16
Nodes (17): builder(), context(), move_mouse(), planner(), provider(), fixture, Tests for the agent planner. The planner's contract is narrow: goal in, one…, An isolated registry holding two live tools and one disabled one. (+9 more)

### Community 170 - "TestToolsCommand"
Cohesion: 0.17
Nodes (3): *args / **kwargs are not part of a tool's callable surface and must not appear…, Only ``name(args)`` -- never the tool's docstring/description., TestToolsCommand

### Community 171 - "_feature_columns"
Cohesion: 0.27
Nodes (9): build_features(), _feature_columns(), FeatureMatrix, _momentum(), ndarray, Causal feature construction for probability estimation. Turns an OHLCV series…, close[t]/close[t-period] - 1, NaN for the first ``period`` positions., Stack the causal feature columns into an (n, n_features) matrix. (+1 more)

### Community 172 - "ExecutionStatus"
Cohesion: 0.18
Nodes (7): ExecutionStatus, Enum, str, ``ok``, ``failed`` if the engine was asked, ``refused`` if it was not., How one attempt ended. ``str``-valued so a serialized result reads as…, Registered but switched off is refused too, and named differently., TestDisabledTool

### Community 174 - "TTLCache"
Cohesion: 0.14
Nodes (7): _Entry, A tiny time-to-live cache. Used by the market-data service so repeated…, A single-process, thread-unsafe TTL cache keyed by string. Kept intentionally…, Return a fresh value or None (expired entries are evicted)., Age in seconds of a live entry, ignoring freshness; None if absent., TTLCache, V

### Community 176 - "ToolRegistry"
Cohesion: 0.06
Nodes (49): Assemble a core from a provider and, optionally, its collaborators. The…, Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, _build(), _CountingExecutor, Any, asyncio, Tests for the agent core loop. ``AgentCore`` is the driver that turns a goal… (+41 more)

### Community 177 - "set_event_bus"
Cohesion: 0.33
Nodes (5): Set the global EventBus instance. This should be called once during application…, set_event_bus(), fixture, Install a fresh bus as the global publisher target, restored afterwards.…, wired()

### Community 178 - "audio.py"
Cohesion: 0.04
Nodes (53): Future, LevelCallback, AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded. (+45 more)

### Community 179 - "_settings"
Cohesion: 0.22
Nodes (9): _clear_env(), fixture, MonkeyPatch, parametrize, Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.…, _settings(), TestDefault, TestInvalidValuesFailAtConfigLoad (+1 more)

### Community 180 - "make_fake_detector"
Cohesion: 0.14
Nodes (11): Drop the process-wide cache (used by tests and at shutdown)., reset_frame_cache(), isolated_container(), make_fake_detector(), make_unclosable_ocr(), fixture, Clear the process-wide frame cache around every vision test. ``_capture()``…, Yield the process-wide container with its registrations saved and restored.… (+3 more)

### Community 181 - "._ask"
Cohesion: 0.33
Nodes (3): Render an ``AgentRunResult`` for the terminal. Deliberately the same shape as…, Render an agent-loop result for the terminal., Send a message to the LLM, letting it call AetherOS tools.

### Community 182 - "test_trading_tools.py"
Cohesion: 0.15
Nodes (23): asyncio, Trading tools exercised through the real ToolRegistry + ToolExecutor. These are…, test_analyze_fundamentals_tool_is_labelled_mock(), test_analyze_instrument_tool_is_labelled_mock(), test_analyze_market_structure_tool(), test_analyze_news_sentiment_tool_is_labelled_mock(), test_assess_risk_tool_is_labelled_mock(), test_assess_risk_tool_position_sizing() (+15 more)

### Community 183 - "CommandParser"
Cohesion: 0.27
Nodes (6): Execute a parsed command., CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 184 - "tasks/__init__.py"
Cohesion: 0.26
Nodes (10): InvalidTaskStateError, Exception, Raised when an invalid state transition is requested., Base exception for task subsystem., Raised when a task cannot be found., TaskError, TaskNotFoundError, Enum (+2 more)

### Community 185 - "._format_trading_report"
Cohesion: 0.13
Nodes (8): A number for display, or ``-`` when it is missing/non-numeric., A 0-1 fraction as a percentage, or ``-`` when missing., One honest line for an advisory layer (news / calendar / fundamentals). Absent…, A compact human summary of an advisory layer's own read., Render a section-27 trading report dict as honest, plain terminal text.…, Run the deterministic trading pipeline for one instrument and render the…, Surface the recorded prediction-audit trail and its track record for a human --…, Render the aggregate track record + the recorded audit trail as honest plain…

### Community 187 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 188 - "Box"
Cohesion: 0.26
Nodes (4): Box, Unit tests for the spatial-relation geometry. Plain rectangles, no perception:…, TestDistance, TestSatisfies

### Community 189 - "VoiceConfig"
Cohesion: 0.04
Nodes (54): Captured microphone audio., Recording, _flag(), _integer(), _number(), Build a configuration from AETHEROS_* environment variables., Minimum seconds between amplitude publishes., Resolve "auto" to CUDA when a usable GPU is present. A CPU fallback must always… (+46 more)

### Community 190 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, One arc group in the ring system., RingSpec

### Community 192 - "AgentStatus"
Cohesion: 0.14
Nodes (7): AgentRunResult, The per-run effort counters (llm_calls, tool_calls, step_count, retries,…, The outcome of one :meth:`AgentCore.run`. Pairs the terminal…, Run ``goal`` on the shared agent, labelling the turn with ``source``.…, AgentStatus, str, Lifecycle of one run. ``str`` subclass so the value serializes as itself and a…

### Community 193 - "automation/tools.py"
Cohesion: 0.19
Nodes (14): describe_strategies(), Strategy name to description. Read by the ``run_workflow`` tool description and…, _build(), list_recovery_strategies(), Any, The automation tools — multi-step desktop work, exposed to the model. Three…, Turn the model's JSON into a validated :class:`Workflow`. Parse errors are re-…, Execute a workflow and return its full execution record. :param name: Label for… (+6 more)

### Community 194 - "test_vision_engine.py"
Cohesion: 0.11
Nodes (10): asyncio, skipif, Tests for the Vision Engine. Run with: pytest tests/vision/, test_opencv_provider_metadata(), test_paddleocr_provider_metadata(), test_yolo_provider_metadata(), TestDetection, TestTemplateMatching (+2 more)

### Community 205 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 206 - "TextBlock"
Cohesion: 0.04
Nodes (26): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, Map box coordinates from a downscaled frame back to the original image. Pure… (+18 more)

### Community 207 - "test_manager.py"
Cohesion: 0.26
Nodes (10): create_manager(), FakeEventBus, Minimal event bus for isolated TaskManager tests., test_cancel_task(), test_complete_task(), test_create_task(), test_fail_task(), test_get_task() (+2 more)

### Community 208 - "LiveTraceUI"
Cohesion: 0.10
Nodes (14): Panel, Render a model response., LiveTraceUI, Any, Redraw the dashboard from the recorder's current window. Never raises., Leave the Live context, restoring the terminal. Safe to double-call., Render a run as a live, in-place vertical execution pipeline. Construction is…, Enter the Rich Live context. Returns whether a dashboard is showing. (+6 more)

### Community 209 - "qcolor"
Cohesion: 0.24
Nodes (8): QLinearGradient, QPointF, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side…, Convert a theme colour and 0..1 alpha into a QColor., sweep_gradient()

### Community 210 - "TestPromptCursor"
Cohesion: 0.25
Nodes (4): _FakeConsole, The live trace dashboard's persistent ``rich.live.Live`` hides the terminal…, A console that cannot honour the control code must not break input., TestPromptCursor

### Community 211 - "parametrize"
Cohesion: 0.27
Nodes (3): parametrize, TestRegistration, TestSchema

### Community 212 - "CLIRuntime"
Cohesion: 0.22
Nodes (5): CLIRuntime, Subscribe the terminal to the shared execution trace. Defensive: a runtime…, Render one lifecycle event as safe, user-facing terminal output. Synchronous on…, Interactive AetherOS CLI runtime., Read one prompt line without blocking the event loop. `console.input()` blocks…

### Community 214 - "TestFinalResponse"
Cohesion: 0.33
Nodes (3): _answer(), A response with prose and no tool calls ends the run., TestFinalResponse

### Community 215 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 216 - ".describe"
Cohesion: 0.14
Nodes (4): The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep.

### Community 217 - "MSSScreen"
Cohesion: 0.07
Nodes (25): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., fake_sct(), FakeSCT, mss_screen() (+17 more)

### Community 219 - "Application"
Cohesion: 0.17
Nodes (8): Application, Main AetherOS application. Responsible for managing the application's…, Restart the application., Returns whether the application is running., Start the application., _main(), Last-resort guarantee that the terminal cursor is visible on exit. The live…, _restore_terminal()

### Community 220 - "PredictionError"
Cohesion: 0.10
Nodes (12): PredictionPerformance, Any, An auditable aggregate of many resolved predictions' outcomes., Whether any calibrated-probability predictions were available to grade., PredictionError, An auditable prediction record could not be built, stored, or read back., Aggregate ``outcomes`` into an auditable :class:`PredictionPerformance`. A…, _round() (+4 more)

### Community 221 - "LLMConfig"
Cohesion: 0.39
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 222 - "TraceEvent"
Cohesion: 0.10
Nodes (28): emit_trace(), Any, Best-effort emission of trace events. The one rule this module exists to…, Mutable handle a :func:`trace_context` body uses to enrich the closing event.…, Bracket a stage with a started event and a timed completed/failed event. Emits…, Publish one trace event, swallowing every failure. Never raises: a missing bus,…, trace_context(), TraceSpan (+20 more)

### Community 223 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 227 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 228 - "_win32_clipboard"
Cohesion: 0.33
Nodes (4): Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Whether the clipboard holds no data of any format. Counting formats rather than…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard()

### Community 229 - ".copy_files"
Cohesion: 0.40
Nodes (3): Path, Copy one or more files/folders to the clipboard., Returns copied file paths. Returns: Empty list if clipboard contains no files.

### Community 230 - ".copy_image"
Cohesion: 0.40
Nodes (3): Any, Copy an image to the clipboard., Returns an image from the clipboard. Returns: None if clipboard doesn't contain…

### Community 231 - "Provenance"
Cohesion: 0.03
Nodes (104): Any, datetime, Aggregate analysis value objects. VolumeAnalysis is a small structured read of…, Deterministic, evidence-grounded situation report for one instrument., Whether this analysis rests on data solid enough to act on. Mock or unusable…, TradingAnalysis, _utcnow(), VolumeAnalysis (+96 more)

### Community 233 - ".test_the_full_pipeline_emits_every_stage_in_order"
Cohesion: 0.21
Nodes (9): _fake_mouse(), _FakeMouseController, _is_ordered_subsequence(), Any, asyncio, The one seam below MouseService -- returns a fixed cursor position. Duck-typed…, Bind the ``MouseService`` the tool resolves to a fixed-position backend., True if every item of ``expected`` occurs in ``actual`` in order. (+1 more)

### Community 236 - "outcome.py"
Cohesion: 0.67
Nodes (3): datetime, Prediction-outcome value object (spec sections 6, 15, 16, 29). A…, _utcnow()

### Community 238 - "executor"
Cohesion: 0.67
Nodes (3): executor(), fixture, An executor over the process-wide registry, which is where @tool registers.

### Community 239 - "RecoveryRunner"
Cohesion: 0.09
Nodes (16): _append_recovery_detail(), Fold recovery outcomes into the error the step will report if it still fails.…, Any, Recovery — bounded self-healing between step attempts. A retry that changes…, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a… (+8 more)

### Community 251 - "TraceCollector"
Cohesion: 0.19
Nodes (9): collector(), event_bus(), Any, fixture, Fixtures for the live-execution-trace tests. The trace layer publishes through…, A fresh bus wired as the global publisher, torn down afterwards. ``emit_trace``…, A recording subscriber -- the honest witness for what was emitted. Sync…, A :class:`TraceCollector` already subscribed to the bus.… (+1 more)

### Community 252 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out. These…

## Knowledge Gaps
- **1 isolated node(s):** `AetherOS`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2743 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_logger()` connect `get_logger` to `AgentError`, `agents/state.py`, `ContextBuilder`, `TerminalService`, `policy.py`, `VerificationResult`, `vision/tools.py`, `agents/core.py`, `PaddleOCRProvider`, `FasterWhisperSTT`, `VisionError`, `enums.py`, `Agent`, `Bootstrapper`, `voice/service.py`, `CommandRegistry`, `MouseController`, `ScreenService`, `PolicyEngine`, `VoiceService`, `LLMEngine`, `ProcessController`, `ApplicationService`, `audio.py`, `AgentCore`, `VoiceConfig`, `automation/tools.py`, `WindowController`, `ClipboardService`, `HUDProcess`, `LLMProvider`, `ProcessService`, `KeyboardService`, `YOLOProvider`, `BrowserProvider`, `LifecycleManager`, `Application`, `TraceEvent`, `ClipboardController`, `Provenance`, `TextToSpeech`, `RecoveryRunner`, `HUDConfig`, `ExecutionConfig`, `VoiceState`, `get_settings`, `process/tools.py`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `ToolCommandService`, `define`, `answer`, `agents/state.py`, `ContextBuilder`, `AutomationEngine`, `_state`, `AgentPlanner`, `agents/core.py`, `test_agent_policy.py`, `get_llm_tools`, `ToolExecutionCoordinator`, `rich_tools`, `test_agent_planner.py`, `ExecutionStatus`, `AgentCore`, `VoiceConfig`, `test_cli_agent.py`, `FakeLLMProvider`, `LLMProvider`, `TestFinalResponse`, `Any`, `PlannerConfig`, `.test_the_full_pipeline_emits_every_stage_in_order`, `RecoveryRunner`, `ExecutionConfig`, `.test_move_flows_through_the_full_chain_with_arguments`, `get_settings`, `test_agent_execution.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `EventBus` connect `EventBus` to `asyncio`, `MarketData`, `test_orchestration.py`, `make_service`, `CriticService`, `Event`, `enums.py`, `RegimeAnalysis`, `voice/service.py`, `test_news.py`, `VoiceService`, `test_wiring.py`, `test_backtest.py`, `Direction`, `bootstrapper.py`, `get_logger`, `SourceTier`, `set_event_bus`, `AgentCore`, `test_fundamentals.py`, `PredictionOutcome`, `make_market_data`, `_make_analysis`, `TraceEvent`, `Provenance`, `test_probability.py`, `HUDConfig`, `TraceCollector`, `resolve_level`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Image` (e.g. with `main()` and `VisionService`) actually correct?**
  _`Image` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 118 inferred relationships involving `Direction` (e.g. with `TradingAnalysis` and `TradeOutcome`) actually correct?**
  _`Direction` has 118 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AgentState` (e.g. with `Agent` and `ContextBuilder`) actually correct?**
  _`AgentState` has 18 INFERRED edges - model-reasoned connections that need verification._