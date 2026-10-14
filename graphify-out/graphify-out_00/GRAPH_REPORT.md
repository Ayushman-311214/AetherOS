# Graph Report - AetherOS  (2026-09-02)

## Corpus Check
- 275 files · ~299,672 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6828 nodes · 12379 edges · 305 communities (255 shown, 34 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 1031 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9a453c7f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- VerificationResult
- make_loop
- define
- Image
- AutomationEngine
- Scene
- asyncio
- ErrorContext
- PaddleOCRProvider
- policy.py
- TerminalService
- HUDService
- Any
- ContextBuilder
- TextBlock
- test_tool_schema.py
- AgentState
- NullSTT
- VoiceConfig
- asyncio
- .build
- RecoveryRunner
- VisionError
- VoiceService
- .record
- VoicePipeline
- FakeHUDProcess
- bootstrapper.py
- WakeWordActivator
- asyncio
- HUDWindow
- Bootstrapper
- Message
- FileController
- Step
- Win32Window
- get_settings
- FakeSCT
- OpenCVProvider
- asyncio
- MouseService
- wire
- ._reject_if_terminal
- PlaywrightProvider
- ApplicationService
- AgentPlanner
- test_wiring.py
- PlannedAction
- BrowserProvider
- HUDConfig
- OpenCVTemplateProvider
- VisionVerifier
- YOLOProvider
- 05_RUNTIME_FLOW_11.md
- Event
- HUDProcess
- WindowController
- ProcessService
- tool
- ToolRegistry
- _one
- PipeReader
- 05_RUNTIME_FLOW_05.md
- VisionProvider
- Detection
- claude.md
- FakeLLMProvider
- MemoryProvider
- LLMToolLoop
- asyncio
- RenderContext
- WindowService
- parse_llm_response
- Any
- browser/tools.py
- make_vision_service
- 02_ARCHITECTURE_01.md
- 04_PROJECT_STRUCTURE_09.md
- test_tools.py
- CommandRegistry
- get_logger
- LifecycleManager
- AgentError
- 05_RUNTIME_FLOW_07.md
- BrowserService
- MouseController
- LLMEngine
- HookRecorder
- AetherOS Project
- PyAutoGuiKeyboard
- ClipboardController
- ProcessController
- ScreenController
- FasterWhisperSTT
- SapiTTS
- ToolExecutionResult
- PsutilProcess
- ScreenService
- window/tools.py
- AetherOS HUD State Gallery (7-panel montage)
- 05_RUNTIME_FLOW_10.md
- BaseError
- LLMProvider
- context.py
- PyAutoGuiMouse
- 02_ARCHITECTURE_02.md
- 05_RUNTIME_FLOW_03.md
- PyAutoGuiClipboard
- process/tools.py
- 05_RUNTIME_FLOW_04.md
- ToolCall
- ToolCommandService
- CLIUI
- Layer
- tool_calls.py
- qcolor
- GlowCache
- screen/tools.py
- Renderer
- voice_error.py
- TestNonUnicodeTerminal
- strategy.py
- renderer.py
- ToolDiscovery
- test_interface_contracts.py
- Application
- DesktopError
- OpenAICompatibleProvider
- ._run
- vision/tools.py
- agents/__init__.py
- application/tools.py
- 05_RUNTIME_FLOW_09.md
- 04_PROJECT_STRUCTURE_05.md
- TestRegisteredToolSurface
- 04_PROJECT_STRUCTURE_06.md
- FakeScreen
- 05_RUNTIME_FLOW_06.md
- cli/main.py
- TestEveryToolModuleImports
- AetherOS Text-Only HUD Overlay
- ._bootstrap_llm
- Any
- LLMProviderManager
- AetherOS Voice HUD (zoomed capture)
- CLIRuntime
- _win32_clipboard
- .save
- 02_ARCHITECTURE_03.md
- main
- .download
- .generate
- WindowBounds
- Mouse Automation Layering Diagram
- 05_RUNTIME_FLOW_08.md
- TestFailureHandling
- main
- test_ui.py
- MSSScreen
- TestDetectScreenObjects
- .evaluate
- .copy_files
- .copy_image
- .open_file
- .grab
- dashboard.md
- PulseLayer
- discover Module Import Discovery Script
- ._live_context
- ._bootstrap_hud
- agent_loop.py
- testing.md
- bootstrapper
- import_all.py
- .hud
- 03_TECH_STACK.md
- 04_PROJECT_STRUCTURE_08.md
- 04_PROJECT_STRUCTURE_10.md
- .title
- .wait
- .click
- agents.md
- trading.md
- 05_RUNTIME_FLOW_02.md
- 01_VISION.md
- core.md
- AetherOS
- VSCode Python Configuration
- 02_ARCHITECTURE_04.md
- 04_PROJECT_STRUCTURE_03.md
- 04_PROJECT_STRUCTURE_01.md
- 04_PROJECT_STRUCTURE_07.md
- 05_RUNTIME_FLOW_12.md
- api.md
- browser.md
- logging.md
- memory.md
- 05_RUNTIME_FLOW_01.md
- automation.md
- database.md
- vision.md
- desktop.md
- llm.md
- planner.md
- reasoning.md
- 00_INTRODUCTION.md
- _started
- PHASE_06_MEMORY.md
- PHASE_02_LLM.md
- PHASE_03_TOOLS.md
- PHASE_04_DESKTOP.md
- PHASE_05_VISION.md
- vision/conftest.py
- AetherOS Vision Engine
- 04_PROJECT_STRUCTURE_04.md
- KeyboardController
- 04_PROJECT_STRUCTURE_02.md
- FakeKeyboard
- FakeMouse
- 5. Core components and their responsibilities
- vision/main.py
- AetherOS Architecture Audit & Development Plan
- AetherOS Development Plan & Architecture Analysis
- ✅ Implemented (Foundation Layer)
- PlannerConfig
- DemoScript
- test_input.py
- NullTTS
- Folder Structure
- Folder
- Directory
- Purpose
- AetherOS — Codebase Guide
- 11. Known gaps and gotchas
- 4. Main execution flow
- 5.6 Action layer — `desktop/`
- Directory
- Critical Findings
- 10. Visual sequence diagrams
- 5.4 Reasoning layer (`llm/`)
- Architectural Inconsistencies
- ._await_exit
- Critical Path to MVP
- 7. Data flow through the application
- Directory
- 3. Application entry points
- 5.3 Tool layer (`tools/`)
- 5.5 User interface layer (`cli/`)
- 6. Dependency relationships
- ❌ Missing Critical Components (Trading Focus)
- TestCallIdentifiers
- 2. High-level folder structure
- 8. Important interfaces and implementations
- 9. Visual architecture diagrams
- Architecture Alignment Plan
- Development Priority Matrix
- Architecture State by Module
- Conclusion
- Testing Strategy
- PHASE_01_FOUNDATION.md
- Technology Stack Decisions
- Architectural Principles (From claude.md)
- Dependency Flow Analysis
- Tool Registration Flow (Working)
- Testing Strategy
- Dependency Analysis
- Technology Stack Decisions
- Immediate Action Plan (Next 2 Weeks)
- .speak
- .start
- Path
- 10. state_manager/
- 12. retry/
- 13. interfaces/
- 5. workflow/
- 6. reasoning/
- 7. event_bus/
- 9. task_queue/
- Summary
- Browser Engine
- Memory Engine
- Trading Engine
- Execution Engine
- Verification Engine
- Learning Engine
- Summary
- .close
- .has_text
- .is_pressed

## God Nodes (most connected - your core abstractions)
1. `Image` - 171 edges
2. `AgentState` - 109 edges
3. `ToolRegistry` - 108 edges
4. `ContextBuilder` - 107 edges
5. `tool()` - 103 edges
6. `define()` - 92 edges
7. `AgentPlanner` - 91 edges
8. `get_logger()` - 81 edges
9. `DesktopError` - 76 edges
10. `AgentContext` - 75 edges

## Surprising Connections (you probably didn't know these)
- `PyAutoGuiMouse Backend` --semantically_similar_to--> `pyautogui Desktop Automation`  [INFERRED] [semantically similar]
  .audit/coord.py → pyproject.toml
- `VSCode pytest Configuration` --semantically_similar_to--> `pytest Testing Framework`  [INFERRED] [semantically similar]
  .vscode/settings.json → pyproject.toml
- `main()` --calls--> `PyAutoGuiMouse`  [INFERRED]
  .audit/coord.py → src/aetheros/desktop/mouse/pyautogui_backend.py
- `main()` --uses--> `Bootstrapper`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/bootstrap/bootstrapper.py
- `main()` --uses--> `ToolExecutor`  [INFERRED]
  .audit/ocr_time.py → src/aetheros/tools/executor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Mouse Automation Layer Stack: Interface, Backend, Service, Tool Definition** — src_aetheros_vision_test_mouseinterface, src_aetheros_vision_test_pyautoguibackend, src_aetheros_vision_test_mouseservice, src_aetheros_vision_test_mouse_tool_definition [EXTRACTED 1.00]
- **HUD Overlay Visual Language (wordmark, dark ground, text-only mode)** — hud_textonly_aetheros_wordmark, hud_textonly_dark_transparent_overlay_design, hud_textonly_text_only_render_mode, hud_textonly_hud_overlay_screenshot [INFERRED 0.75]
- **Desktop Automation Technology Stack** — pyproject_pyautogui, pyproject_pynput, pyproject_keyboard, pyproject_mouse, audit_coord_main [INFERRED 0.85]
- **End-to-End Demo Trace: spoken command to tool call to spoken result** — hud_states_command_move_mouse_300px, hud_states_transcribing_state, hud_states_move_relative_tool, hud_states_executing_state, hud_states_speaking_state [INFERRED 0.85]
- **HUD Orb Visual Composition Layers** — hud_states_orb_core, hud_states_orbital_ring_system, hud_states_audio_tick_ring, hud_states_particle_field, hud_states_state_label_typography, hud_states_transcript_caption_line [INFERRED 0.85]
- **Voice Command HUD Feedback Loop (state, transcript, command, automation intent)** — hud_textonly_transcribing_state_indicator, hud_textonly_transcript_readout, hud_textonly_voice_command_move_mouse, hud_textonly_desktop_automation_intent [INFERRED 0.85]
- **Voice Capture Visual Feedback Loop (orb, state label, transcript, particles)** — hud_zoom_central_orb_visualizer, hud_zoom_transcribing_state, hud_zoom_live_transcript_display, hud_zoom_radial_particle_field [INFERRED 0.85]
- **LLM Provider Ecosystem** — pyproject_openai, pyproject_ollama, pyproject_httpx [INFERRED 0.85]
- **Vision and OCR Technology Stack** — pyproject_opencv, pyproject_paddleocr, audit_ocr_time_main [INFERRED 0.85]
- **Voice Command Lifecycle States (IDLE to SPEAKING with ERROR branch)** — hud_states_idle_state, hud_states_listening_state, hud_states_transcribing_state, hud_states_thinking_state, hud_states_executing_state, hud_states_speaking_state, hud_states_error_state [INFERRED 0.95]

## Communities (305 total, 34 thin omitted)

### Community 0 - "VerificationResult"
Cohesion: 0.05
Nodes (44): Run a step's read-back, polling when it declared a timeout. Returns ``None``…, Any, True when read-back actively disagreed with the expectation. This is the only…, Declare that this action cannot be verified, and say why. The ``detail`` is not…, The action executed. ``verification`` still decides ``success``. There is no…, The action did not execute. ``success`` is false regardless of anything else in…, What was checked, what was expected, and what was actually observed. The four…, True only for a real, passing check. UNSUPPORTED and SKIPPED are both false… (+36 more)

### Community 1 - "make_loop"
Cohesion: 0.07
Nodes (53): AgentLoopConfig, Bounds and behaviour for a single loop run., answer(), tool_calls(), make_loop(), Any, fixture, Build a ``(provider, loop)`` pair driven by a scripted response list. Schemas… (+45 more)

### Community 2 - "define"
Cohesion: 0.06
Nodes (49): Executes registered AetherOS tools., ToolExecutor, define(), Factory for ToolDefinition objects (the factory-as-fixture pattern)., add(), add_async(), explodes(), asyncio (+41 more)

### Community 3 - "Image"
Cohesion: 0.04
Nodes (27): ColorSpace, Image, ndarray, Path, Return this image with RGB channel order. Idempotent: an image already in RGB,…, Return this image with BGR channel order — the pipeline default. Idempotent,…, Return a single-channel copy., Drop the alpha channel, keeping the channel order. PaddleOCR and most OpenCV… (+19 more)

### Community 4 - "AutomationEngine"
Cohesion: 0.07
Nodes (41): AutomationEngine, Executes workflows step by step, verifying as it goes. Stateless between runs:…, An ordered list of steps and the policy for running them., Build a workflow from a plain dict, as ``run_workflow`` receives it., The same workflow, validated instead of executed., What became of one step. ``RECOVERED`` is kept distinct from ``SUCCEEDED`` on…, StepStatus, Workflow (+33 more)

### Community 5 - "Scene"
Cohesion: 0.04
Nodes (38): _blend(), _build_particles(), _mix(), _mix_colour(), Particle, Pulse, An expanding ring emitted from the core., The animation state of the overlay. Holds everything that changes over time:… (+30 more)

### Community 6 - "asyncio"
Cohesion: 0.19
Nodes (9): _call(), asyncio, Invoke a tool the way the executor does -- by name, out of the registry. Going…, This tool is described to the model as "press and hold", but it called…, The ``release_modifiers`` recovery strategy calls this tool by name, so an…, The backend and interface both had mouse_down; MouseService dropped it, so no…, The pair matters more than either one: a horizontal_scroll wired to scroll()…, TestKeyboardTools (+1 more)

### Community 7 - "ErrorContext"
Cohesion: 0.08
Nodes (28): ErrorContext, Additional information about an error., LLMError, Exception, Base exception for all LLM-related errors. Examples: - Provider connection…, VisionProvider, Vision system for AetherOS. Provides OCR, object detection, template matching,…, Vision domain models. (+20 more)

### Community 8 - "PaddleOCRProvider"
Cohesion: 0.06
Nodes (30): PaddleOCRProvider, Any, ndarray, _quiet_model_source_check(), The installed PaddleOCR version, or ``"unavailable"``. Read from the package…, Whether PaddleOCR *and* its paddle runtime are importable. Uses find_spec so…, Recognise text in an image. Returns an empty list for an image with no readable…, Release the OCR model. (+22 more)

### Community 9 - "policy.py"
Cohesion: 0.07
Nodes (38): PathLike, Safety — the gates every destructive desktop action passes through. Two…, PathAccess, PathGuard, PathVerdict, Enum, Path, str (+30 more)

### Community 10 - "TerminalService"
Cohesion: 0.14
Nodes (14): Process, _clip(), CommandResult, _decode(), Path, Runs commands and reports honestly on how they went., Extend the current environment rather than replacing it. A replaced environment…, Await completion, or kill the command and raise on timeout. (+6 more)

### Community 11 - "HUDService"
Cohesion: 0.06
Nodes (24): _clip(), HUDService, Any, Whether there is a live overlay on screen., A flat snapshot for the CLI., Show the overlay. Returns whether it came up. Reports failure rather than…, Close the overlay and release everything behind it. Ordering matters: stop…, Close the overlay and open a new one. (+16 more)

### Community 12 - "Any"
Cohesion: 0.09
Nodes (13): Any, The request payload, in the order the provider expects. Exactly one system…, Schemas in the shape ``LLMEngine.tool_call(tools=...)`` accepts., Faithful, and therefore not safe for the log sinks. Holds the goal, the…, Counts and tool names only -- the view the sinks may keep., The tool name inside a generated schema, or ``""`` if it is malformed. Tolerant…, Shorthand for ``build(state).messages()``., The replayable transcript window, plus what it cost to bound it. Two rules… (+5 more)

### Community 13 - "ContextBuilder"
Cohesion: 0.07
Nodes (40): ContextBuilder, ContextConfig, The limits that keep one iteration's prompt a predictable size. Defaults are…, Turns an :class:`AgentState` into an :class:`AgentContext`. Collaborators are…, A builder over the same collaborators with different limits., An assistant turn, optionally carrying the calls the model asked for.…, builder(), _call() (+32 more)

### Community 14 - "TextBlock"
Cohesion: 0.06
Nodes (21): Any, Check whether a point lies inside the text block., Check if text contains query., Represents detected text from OCR., Convert to serializable dictionary., TextBlock, Recognise text, returning one block per detected region. Returns an empty list…, ocr_provider() (+13 more)

### Community 15 - "test_tool_schema.py"
Cohesion: 0.06
Nodes (33): NotAnImportableType, get_llm_tools(), Return schemas for all enabled AetherOS tools. Both collaborators are…, anything(), containers(), every_scalar(), mixed_defaults(), move_mouse() (+25 more)

### Community 16 - "AgentState"
Cohesion: 0.06
Nodes (12): AgentState, A faithful, round-trippable snapshot of the whole run. Contains the goal, the…, The mutable record of one agent run. Not a dataclass, deliberately. The…, asyncio, parametrize, TestCompletion, TestErrors, TestInitialState (+4 more)

### Community 17 - "NullSTT"
Cohesion: 0.11
Nodes (5): NullSTT, ndarray, Speech recognition that never recognizes anything. Used when the user has…, Returns queued phrases in order. This is the test double that lets the whole…, ScriptedSTT

### Community 18 - "VoiceConfig"
Cohesion: 0.04
Nodes (63): Future, ABC, ndarray, Result of a speech-recognition request., Abstract base class for all speech-recognition providers. Implementations must…, Provider name, e.g. "faster-whisper"., Sample rate, in Hz, the provider expects audio in., Load models and acquire resources. (+55 more)

### Community 19 - "asyncio"
Cohesion: 0.06
Nodes (22): Whether the far end has gone away., asyncio, parametrize, Path, skipif, The service must be wired with the *registered* provider instances.…, Registration overwrites rather than raising, so a re-entered bootstrap must not…, Vision must come up on a machine with no display. Only the capture-based tools… (+14 more)

### Community 20 - ".build"
Cohesion: 0.08
Nodes (22): Assemble the context for ``state``'s current iteration. Synchronous and side-…, EchoReasoner, Any, Exception, Returns a canned reply, optionally reporting a tool call. The test double for…, Produce a spoken reply to `text`., add(), HookRecorder (+14 more)

### Community 21 - "RecoveryRunner"
Cohesion: 0.11
Nodes (11): Any, Tools that must exist for this strategy to do anything at all. Optional actions…, What one strategy achieved. ``applied`` is false for both "the tools are…, Applies recovery strategies by name. Never raises for a recovery-level problem.…, Which of ``names`` are not recovery strategies. Used by the dry-run path so a…, Which strategies can currently do anything, given the registered tools., Apply each named strategy in order, once., A named, context-free repair applied between attempts. Context-free is a design… (+3 more)

### Community 22 - "VisionError"
Cohesion: 0.05
Nodes (29): Exception, Base exception for all vision-related errors. Examples: - Screen capture failed…, VisionError, ndarray, Path, Write a captured BGR frame to disk. cv2.imwrite expects BGR, which is exactly…, Capture a specific monitor (1 = primary)., Grab a region and drop the alpha channel. mss hands back BGRA; slicing to three… (+21 more)

### Community 23 - "VoiceService"
Cohesion: 0.06
Nodes (23): Protocol, Anything that can turn an utterance into a spoken reply. The pipeline depends…, VoiceReasoner, Any, A flat snapshot for the CLI., Bring the voice subsystem up., Take the voice subsystem down and release every resource. Ordering matters:…, Owns the voice subsystem's lifecycle. Assembles capture, recognition,… (+15 more)

### Community 24 - ".record"
Cohesion: 0.14
Nodes (13): LevelCallback, _normalize_level(), Any, ndarray, Captured microphone audio., Record one utterance. Capture ends on whichever comes first: sustained silence…, Play `samples`, returning when playback finishes. Cancellation stops the device…, Import sounddevice lazily. Keeps PortAudio out of the process until voice is… (+5 more)

### Community 25 - "VoicePipeline"
Cohesion: 0.04
Nodes (50): LLMThinkingFinished, LLMThinkingStarted, A reasoning request was sent to the LLM., The LLM produced a response., Speech synthesis playback began., The voice state machine moved between states. This is the single event the HUD…, Speech synthesis playback ended., A recoverable voice-subsystem failure. Named for the HUD's benefit; the… (+42 more)

### Community 26 - "FakeHUDProcess"
Cohesion: 0.11
Nodes (8): FakeHUDProcess, Any, Shared HUD test doubles. Nothing here touches Qt, a display, or a subprocess:…, Backwards-compatible location for the HUD test double. The double itself moved…, Die the way a Qt failure does: gone, with a non-zero code., Every snapshot payload sent, oldest first., The state of every snapshot sent, in order., Stands in for HUDProcess without launching anything. Records what the service…

### Community 27 - "bootstrapper.py"
Cohesion: 0.11
Nodes (13): KeyboardService, Release every modifier key. Worth exposing on its own: a workflow that fails…, Press and release a key., Press and release several keys, one after another. Not a shortcut -- use…, High-level keyboard service. This service delegates all keyboard operations to…, Hold a key down until ``key_up`` releases it., clear_input(), clear_modifiers() (+5 more)

### Community 28 - "WakeWordActivator"
Cohesion: 0.12
Nodes (5): NullActivator, WakeCallback, An activator that never fires. This is what "always-listening is off" looks…, Placeholder for always-listening wake-word detection. The abstraction exists so…, WakeWordActivator

### Community 29 - "asyncio"
Cohesion: 0.05
Nodes (35): A tool finished, successfully or otherwise., ToolExecutionFinished, bus(), fake_process(), make_service(), process(), fixture, Fixtures for the HUD tests. The process double lives in… (+27 more)

### Community 30 - "HUDWindow"
Cohesion: 0.07
Nodes (18): QMouseEvent, QPaintEvent, QWidget, HUDWindow, QPainter, Size the window and place it on the configured anchor., Make the window ignore the mouse, if configured to. Qt's own…, Show the overlay and begin animating. (+10 more)

### Community 31 - "Bootstrapper"
Cohesion: 0.09
Nodes (6): Bootstrapper, Coordinates application startup and shutdown. The bootstrapper is responsible…, Shutdown subsystems in reverse order., Build the YOLO detector when its package and weights are both present. Returns…, Whether Playwright can be imported. find_spec rather than a try/import:…, Park the overlay at IDLE when nothing will publish voice events.

### Community 32 - "Message"
Cohesion: 0.05
Nodes (43): Message, One turn of the conversation, in the shape the providers expect. Frozen: a…, _initial_config(), Any, Wait briefly for the parent's opening config message. Without this the window…, Where the render process sends messages. Routes to the parent when there is…, _Reporter, Build a snapshot for one state, with plausible sample content. Used by `hud… (+35 more)

### Community 33 - "FileController"
Cohesion: 0.08
Nodes (19): FileController, ABC, Any, Path, Copy a file or directory., Move a file or directory., Rename a file or directory., Delete a file or directory. (+11 more)

### Community 34 - "Step"
Cohesion: 0.11
Nodes (16): _as_float(), _clamp_seconds(), _parse_condition(), Any, Build a step from a plain dict, as the ``run_workflow`` tool receives it.…, Round-trippable description, used in logs and dry-run output., Coerce a duration to a non-negative float no larger than ``ceiling``., One tool call, with the conditions around it. Fields ------ name Label used in… (+8 more)

### Community 35 - "Win32Window"
Cohesion: 0.10
Nodes (18): Any, Coerce whatever the caller passed into a window handle. Accepts a…, Resolve to a handle and confirm the window still exists. Checked on every…, Owning process name, or empty when it cannot be read. Empty rather than an…, Build a snapshot of one window., Every visible top-level window that has a title, in Z-order. Filtered rather…, The topmost window whose title matches. Case-insensitive, and a substring match…, The foreground window, or ``None`` when nothing is focused. ``None`` is a real… (+10 more)

### Community 36 - "get_settings"
Cohesion: 0.08
Nodes (19): BaseSettings, get_settings(), Singleton Settings object., Settings, _append_recovery_detail(), _backoff_seconds(), Run a workflow, or validate it when ``workflow.dry_run`` is set., Check a workflow without executing any of it. Catches everything that can be… (+11 more)

### Community 37 - "FakeSCT"
Cohesion: 0.15
Nodes (11): fake_sct(), FakeSCT, mss_screen(), fixture, parametrize, Tests for the screen capture layer. Screen capture is where the vision…, ``np.asarray`` over an mss ScreenShot aliases a buffer mss reuses, so the next…, Stands in for an ``mss.mss()`` session. Returns BGRA, the way mss does, so the… (+3 more)

### Community 38 - "OpenCVProvider"
Cohesion: 0.11
Nodes (9): OpenCVProvider, ndarray, VisionProvider, OpenCV implementation of VisionProvider. Responsible for image processing…, Wrap transformed pixels, carrying provenance and colour space over., Convert to single-channel. Delegates to :meth:`Image.gray`, which picks the…, A fixed COLOR_BGR2GRAY would weight red and blue the wrong way round for RGB…, TestOpenCVOperations (+1 more)

### Community 39 - "asyncio"
Cohesion: 0.10
Nodes (21): EnvelopeResult, _ocr_with(), Any, asyncio, Exception, parametrize, Unit tests for the concrete vision providers. The OpenCV and template providers…, Stands in for a built PaddleOCR pipeline. Records the frame it was handed so a… (+13 more)

### Community 40 - "MouseService"
Cohesion: 0.09
Nodes (17): MouseService, Press a button and leave it held. Exposed separately from click() because a…, Release a held button., High-level mouse service. This class delegates all operations to the configured…, click(), double_click(), drag_relative(), drag_to() (+9 more)

### Community 41 - "wire"
Cohesion: 0.12
Nodes (15): asyncio, Path, The regression this guards: the tool used to pass the raw ndarray from…, A frame tagged RGB here would be channel-swapped on its way to the OCR model,…, Tool results are JSON-encoded for the model; a stray dataclass or ndarray in…, Reading a saved image is the path that works on a headless machine, so it must…, "Not on screen" is an answer the agent can act on, not an error., A missing optional backend must not cost the caller the OCR result it would… (+7 more)

### Community 42 - "._reject_if_terminal"
Cohesion: 0.10
Nodes (12): ErrorRecord, BaseException, Stop the run on request. Distinct from failure: nothing went wrong., Something that went wrong during the run. ``recoverable`` is the important…, A finished run is immutable. This is what makes the record auditable: a state…, PENDING -> RUNNING. Idempotence is not offered on purpose: a second start would…, Open the transcript with the system prompt and the goal., Append several turns atomically. One lock acquisition, not one per message: an… (+4 more)

### Community 43 - "PlaywrightProvider"
Cohesion: 0.07
Nodes (6): Page, PlaywrightProvider, Any, Path, Playwright implementation of BrowserProvider., The installed Playwright version. Read from package metadata rather than hard-…

### Community 44 - "ApplicationService"
Cohesion: 0.10
Nodes (25): ApplicationService, Any, Path, Application service. An application is not a process, and conflating the two is…, Start an application, optionally waiting until it has a window. The window wait…, Open a shell URI such as ``ms-settings:``. Restricted to the two prefix sets…, Open a URL in the default browser., Poll for a window of this executable that was not open before. Returns ``None``… (+17 more)

### Community 45 - "AgentPlanner"
Cohesion: 0.06
Nodes (42): AgentContext, One iteration's worth of assembled context. Frozen: a snapshot that can be…, AgentPlanner, Decides the next action for one iteration of an agent run. Holds the provider…, _answer(), builder(), _calls(), context() (+34 more)

### Community 46 - "test_wiring.py"
Cohesion: 0.07
Nodes (27): boot(), _clean_env(), _injecting_init(), asyncio, fixture, _raising_start(), Bootstrap wiring for the two optional subsystems. The HUD and the voice…, `publisher.publish()` is how code fires an event without holding a bus. (+19 more)

### Community 47 - "PlannedAction"
Cohesion: 0.03
Nodes (39): PlannedAction, PlanResult, Any, Faithful, and therefore not safe for the log sinks. Holds ``raw_arguments``,…, Log-safe: names and reasons, never argument values., One decision, described rather than performed. Frozen because an action that…, The model answered. ``content`` is the answer, verbatim., A validated request to run ``tool_name``. The arguments are copied. The planner… (+31 more)

### Community 48 - "BrowserProvider"
Cohesion: 0.06
Nodes (15): BrowserProvider, ABC, Fill an input element., Press a keyboard key on an element., Hover over an element., Return the text content of an element., Return the current page URL., Return the current page HTML. (+7 more)

### Community 49 - "HUDConfig"
Cohesion: 0.07
Nodes (26): QApplication, build_application(), main(), Run the overlay until told to stop. Blocks; returns an exit code. This is the…, Run driven by a parent process over stdio. This is how HUDService starts the…, Standalone entry point. Exists so the HUD can be developed and visually…, Create the QApplication with high-DPI behaviour set correctly. The rounding…, run_hud() (+18 more)

### Community 50 - "OpenCVTemplateProvider"
Cohesion: 0.08
Nodes (15): Wrap a raw array. ``color_space`` is inferred when omitted: single channel…, OpenCVTemplateProvider, Template matching using OpenCV., Find template at multiple scales. Useful when template size might vary., Find template in image using OpenCV. Args: image: Source image to search in…, Scales that would make the template larger than the image are dropped rather…, TestTemplateProvider, asyncio (+7 more)

### Community 51 - "VisionVerifier"
Cohesion: 0.24
Nodes (5): Drive OCR through the tool registry, the way an agent would., Runs the verification stages and collects their results., VisionVerifier, The canonical verification image containing :data:`REFERENCE_LINES`., reference_image()

### Community 52 - "YOLOProvider"
Cohesion: 0.11
Nodes (9): Any, Path, Ultralytics YOLO implementation. Supports object detection using YOLOv8/YOLOv11…, Whether detection can run without a download., YOLOProvider, Weights are never fetched implicitly: a silent download would put an internet…, The inverse: make one package look installed even when it is not. Lets the…, _show_package() (+1 more)

### Community 53 - "05_RUNTIME_FLOW_11.md"
Cohesion: 0.04
Nodes (47): 05_RUNTIME_FLOW.md, Browser Events, Cancellation Runtime, Complete Runtime Architecture, Complete Runtime Flow, CPU Scheduling, Deadlock Prevention, Delayed Tasks (+39 more)

### Community 54 - "Event"
Cohesion: 0.07
Nodes (33): EventHandler, EventBus, Central event bus for AetherOS. Features: - Sync + Async handlers - Multiple…, Register an event handler., Publish an event. Every subscriber receives the event., Event, Any, Base class for all events in AetherOS. Every event inherits from this class. (+25 more)

### Community 55 - "HUDProcess"
Cohesion: 0.09
Nodes (14): Popen, HUDProcess, Record that the child has reported MSG_READY., Launch the overlay. Returns whether it started. Failure is reported rather than…, Shut the overlay down and release every handle. Escalates: ask, then terminate,…, The overlay, running as a separate process. Separate rather than a thread for…, Kill the overlay and anything it started. Not just process.terminate(): on…, Close both channels and join the reader thread. (+6 more)

### Community 56 - "WindowController"
Cohesion: 0.10
Nodes (13): ABC, Any, Returns (width, height)., Check whether a window still exists., Returns True if the window is active., Returns the window title., Returns all open windows., Find a window by title. (+5 more)

### Community 57 - "ProcessService"
Cohesion: 0.14
Nodes (7): ProcessService, Any, Path, Wait until a process exits, bounded by ``timeout``. Polls rather than calling…, Wait until at least one process with this name is running. Used after launching…, High-level process operations., Resolve a name to exactly one process, or explain why it could not. Refuses to…

### Community 58 - "tool"
Cohesion: 0.10
Nodes (20): ClipboardService, Any, Path, High-level clipboard service. Delegates clipboard operations to the configured…, clear_clipboard(), copy_files(), copy_image(), copy_text() (+12 more)

### Community 59 - "ToolRegistry"
Cohesion: 0.09
Nodes (16): Central registry for every tool in AetherOS. Responsibilities ----------------…, ToolRegistry, Any, A snapshot that can be edited after assembly is not a snapshot., Three tools, registered out of alphabetical order on purpose., Only enabled tools, from the injected registry, in a stable order., Schemas are resolved per build, so a late registration is visible., Not a second schema format: byte-identical to ToolSchemaGenerator. (+8 more)

### Community 60 - "_one"
Cohesion: 0.09
Nodes (14): _one(), Parsing of provider tool-call responses. Everything the model emits is…, SDK responses arrive as objects with attributes, not dicts., A no-argument tool is commonly called with "" or " "., The assistant turn replayed to the provider must match what the model actually…, default=str covers most oddities; the result must be valid JSON either way,…, Parse a response expected to hold exactly one call, and return it., Valid JSON, but not an object: it cannot be splatted into a signature. (+6 more)

### Community 61 - "PipeReader"
Cohesion: 0.10
Nodes (9): IO, PipeReader, PipeWriter, Any, Receives messages from a text stream. Owns exactly one thread, because a pipe…, Stop reading, and release the stream if it is safe to. Deliberately does *not*…, Inject a message locally, as if it had arrived., Sends messages down a text stream. Satisfies the sending half of MessageQueue… (+1 more)

### Community 62 - "05_RUNTIME_FLOW_05.md"
Cohesion: 0.05
Nodes (42): 05_RUNTIME_FLOW.md, Complete Memory Runtime, Complete Memory Runtime Flow, Dependency Rules, During Execution, Episodic Memory, Execution Begins, Execution Completed (+34 more)

### Community 63 - "VisionProvider"
Cohesion: 0.11
Nodes (11): ABC, Any, Path, Apply preprocessing before OCR or detection., Generate an image caption., Generate image embedding., Returns True if the provider is ready., Extract text from an image. (+3 more)

### Community 64 - "Detection"
Cohesion: 0.07
Nodes (10): Detection, Any, Convert to a serializable dictionary., Check whether a point lies inside the detection., Check if two detections overlap., Represents a detected object., Calculate Intersection over Union (IoU)., FakeDetectionProvider (+2 more)

### Community 65 - "claude.md"
Cohesion: 0.05
Nodes (41): 10. LLM Architecture, 11. Tool Architecture, 12. Desktop Automation, 13. Vision, 14. TradingView / Browser Automation, 15. Memory, 16. Event-Driven Architecture, 17. Model Selection (+33 more)

### Community 66 - "FakeLLMProvider"
Cohesion: 0.09
Nodes (17): fake_hud_process(), FakeLLMProvider, _final_response(), _make_tool_definition(), Any, fixture, Shared pytest configuration and fixtures for the AetherOS test suite., Scripted LLMProvider for tests. ``responses`` is consumed one entry per… (+9 more)

### Community 67 - "MemoryProvider"
Cohesion: 0.09
Nodes (13): MemoryProvider, ABC, Any, Update an existing item., Remove all stored items., Check if a key exists., Number of stored items., Initialize memory provider. (+5 more)

### Community 68 - "LLMToolLoop"
Cohesion: 0.13
Nodes (13): LLMToolLoop, Any, Main LLM ↔ ToolExecutor loop., Run the loop and return the model's final answer text., Run the loop and return the full record of what happened., Await an optional progress hook without letting it break the run. A hook…, Rebuild the assistant turn that requested these tool calls., Turn an execution outcome into text the model can read. (+5 more)

### Community 69 - "asyncio"
Cohesion: 0.12
Nodes (8): asyncio, parametrize, The type boundary that used to fail inside a provider with ``AttributeError:…, A single-channel result tagged BGR would make a later rgb() call try to reorder…, TestFindTemplate, TestFindText, TestImageProcessing, TestReadText

### Community 70 - "RenderContext"
Cohesion: 0.13
Nodes (16): QFont, Whether this layer should draw at all this frame., _font(), RGB, The state name, below the core, with flanking rules., One elided, centred line of secondary text., Choose the single most relevant line for this moment., Build a font, scaled and optionally letterspaced. (+8 more)

### Community 71 - "WindowService"
Cohesion: 0.08
Nodes (24): Human-readable condition, used when the caller did not supply one., Any, Every window matching the given selectors, frontmost first. Selectors combine…, Every visible titled top-level window, frontmost first., The frontmost window matching ``title``, or ``None``., The focused window, or ``None`` when nothing has focus., Focus a window. Raises if focus did not actually land on it., Ask a window to close. A request, not a guarantee -- the application may prompt… (+16 more)

### Community 72 - "parse_llm_response"
Cohesion: 0.12
Nodes (11): parse_llm_response(), ParsedResponse, Normalised view of one provider response., Normalise a provider tool-call response. Never raises. Accepts the shape…, parametrize, Dropping it silently would leave the model repeating the same broken call until…, Models often narrate before calling a tool., The wire format sets content to null on a pure tool-call turn. (+3 more)

### Community 73 - "Any"
Cohesion: 0.10
Nodes (13): Any, Fail on fields we do not recognise instead of dropping them. Ignoring an…, Rebuild a run from a snapshot, rejecting anything we cannot restore. Private…, The redacted view, safe for the log sinks. Counts and tool *names* only — no…, The provider-facing shape, matching ``LLMToolLoop`` exactly., The transcript in provider wire format, ready to send., ISO-8601 timestamp in UTC. UTC, not local time: a DST transition in a local-…, _reject_unknown() (+5 more)

### Community 74 - "browser/tools.py"
Cohesion: 0.14
Nodes (22): _browser(), browser_back(), browser_forward(), browser_reload(), browser_screenshot(), click_element(), close_browser(), current_url() (+14 more)

### Community 75 - "make_vision_service"
Cohesion: 0.13
Nodes (9): make_fake_detector(), make_fake_ocr(), make_vision_service(), Factory for services with a specific provider mix (factory-as-fixture)., No readable text is an outcome, not a failure., Positional wiring is rejected: ``VisionService(ocr, cv)`` and…, TestDetectObjects, TestServiceInitialisation (+1 more)

### Community 76 - "02_ARCHITECTURE_01.md"
Cohesion: 0.05
Nodes (41): 02_ARCHITECTURE.md, 10. Design Patterns, 11. Project Boundaries, 12. Scalability Strategy, 1. Architecture Philosophy, 2. System Overview, 3. Architectural Goals, 4. Layered Architecture (+33 more)

### Community 77 - "04_PROJECT_STRUCTURE_09.md"
Cohesion: 0.05
Nodes (41): 04_PROJECT_STRUCTURE.md, 10. storage/, 11. downloads/, 12. uploads/, 13. javascript/, 14. dom/, 15. network/, 16. screenshots/ (+33 more)

### Community 78 - "test_tools.py"
Cohesion: 0.11
Nodes (12): executor(), fixture, parametrize, Tests for the vision tools and their registry integration. These exercise the…, The category is how an agent asks for "the vision tools" rather than naming…, The description is the only thing the model sees when choosing a tool., Every vision tool awaits a service. A definition marked sync would be pushed…, Re-importing the tool module must not register a second copy — the registry… (+4 more)

### Community 79 - "CommandRegistry"
Cohesion: 0.09
Nodes (8): CommandHandler, CommandRegistry, Registry for AetherOS CLI commands., Show LLM provider status and model information., Send a message to the LLM, letting it call AetherOS tools., Render an agent-loop result for the terminal., Register a CLI command., Execute a parsed command.

### Community 80 - "get_logger"
Cohesion: 0.12
Nodes (15): __init__(), Application, Main AetherOS application. Responsible for starting and shutting down the…, configure_handlers(), Configure every AetherOS log sink. Parameters ---------- console: Attach a…, disable_console_logging(), enable_console_logging(), get_logger() (+7 more)

### Community 81 - "LifecycleManager"
Cohesion: 0.10
Nodes (10): LifecycleComponent, LifecycleManager, Protocol, Every service that participates in the application lifecycle should implement…, Execute health checks for all components., Returns True if every component is healthy., Coordinates startup and shutdown of all services., Register a lifecycle component. (+2 more)

### Community 82 - "AgentError"
Cohesion: 0.09
Nodes (16): _clamp(), Coerce a configured limit into range, or refuse it. Clamping rather than…, ActionType, Enum, str, Planner actions and results. The value types the planner returns. They exist so…, What the planner decided. ``str``-valued so a serialized action reads as…, AgentStatus (+8 more)

### Community 83 - "05_RUNTIME_FLOW_07.md"
Cohesion: 0.05
Nodes (41): 05_RUNTIME_FLOW.md, Audio Runtime, Clipboard Runtime, Complete Desktop Runtime, Complete Desktop Runtime Flow, Coordinate System, Desktop Components, Desktop Event System (+33 more)

### Community 84 - "BrowserService"
Cohesion: 0.09
Nodes (3): BrowserService, Release the browser if one is still open. Called from…, High-level browser service. Responsible for coordinating browser operations.…

### Community 85 - "MouseController"
Cohesion: 0.09
Nodes (10): MouseController, ABC, Drag to an absolute position., Drag relative to the current position., Press and hold a mouse button., Release a mouse button., Get the current mouse position. Returns: (x, y), Move the mouse to an absolute screen position. Named ``x``/``y`` rather than… (+2 more)

### Community 86 - "LLMEngine"
Cohesion: 0.07
Nodes (21): Any, Register a singleton service. Instance is created lazily., Register a factory. Every resolve() creates a new instance., Simple Dependency Injection (DI) container. Supports: - Singleton services -…, Whether a singleton has actually been built yet. Shutdown code needs this:…, ServiceContainer, LLMEngine, Any (+13 more)

### Community 87 - "HookRecorder"
Cohesion: 0.22
Nodes (5): explodes(), HookRecorder, Any, The tool-progress hooks on the agent loop. These exist for a presentation…, Stands in for the voice pipeline's progress callbacks.

### Community 88 - "AetherOS Project"
Cohesion: 0.10
Nodes (21): AetherOS Project, black Code Formatter, hatchling Build Backend, httpx HTTP Client, keyboard Library, loguru Logging Library, mouse Library, mypy Type Checker (+13 more)

### Community 89 - "PyAutoGuiKeyboard"
Cohesion: 0.12
Nodes (8): PyAutoGuiKeyboard, PyAutoGUI implementation of the KeyboardController interface., Report whether a key is physically held right now. PyAutoGUI itself cannot…, MonkeyPatch, Asserts on the pyautogui functions the backend calls. Every function under test…, This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is…, Both sides deliberately: an interrupted hotkey may have left either the left or…, TestPyAutoGuiKeyboardBackend

### Community 90 - "ClipboardController"
Cohesion: 0.12
Nodes (9): ClipboardController, ABC, Returns True if clipboard contains an image., Returns True if clipboard contains files., Returns True if clipboard is empty., Returns the clipboard content type. Examples: "text" "image" "files" "empty"…, Copy text to the clipboard., Returns clipboard text. (+1 more)

### Community 91 - "ProcessController"
Cohesion: 0.11
Nodes (10): ProcessController, ABC, Force kill a process., Restart a process. Returns: New PID., Returns True if process exists., Returns True if process is running., Wait for a process to exit., Open a URL in the default browser. (+2 more)

### Community 92 - "ScreenController"
Cohesion: 0.11
Nodes (12): ABC, Any, ndarray, Path, Abstract interface for raw screen-capture backends (MSS, DXGI, ...). Capture…, Capture the primary monitor as a BGR array., Capture a rectangular region as a BGR array., Write a BGR array to disk, preserving its colours. (+4 more)

### Community 93 - "FasterWhisperSTT"
Cohesion: 0.12
Nodes (11): FasterWhisperSTT, _prepare_audio(), ndarray, Local speech recognition via faster-whisper (CTranslate2). Runs entirely…, Transcribe mono float32 PCM., Run inference. Executed on a worker thread., Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants., Linear resampling. Adequate here because capture is configured at 16 kHz… (+3 more)

### Community 94 - "SapiTTS"
Cohesion: 0.13
Nodes (9): AmplitudeCallback, Any, Execute `function` on the owned COM thread., Synthesize `text` into a temporary WAV file., Offline speech synthesis via the Windows Speech API. Uses pywin32, which…, Translate an edge-tts percentage offset into SAPI's -10..10 scale., Create the COM voice object on its dedicated thread., _sapi_rate() (+1 more)

### Community 95 - "ToolExecutionResult"
Cohesion: 0.18
Nodes (11): Adapt a :class:`ToolExecutionResult` without re-implementing it. ``content`` is…, _render(), Outcome of a single tool execution. Carries failures as data rather than as…, ToolExecutionResult, call(), failed_result(), ok_result(), fixture (+3 more)

### Community 96 - "PsutilProcess"
Cohesion: 0.16
Nodes (12): PsutilProcess, Any, Fetch a psutil handle, translating its errors into DesktopError. psutil's…, Read one process into a plain dict. Fields that require privileges are filled…, Open a URL in the default browser. Returns ``0`` for the same reason as…, Every process the current user can see. ``process_iter`` with an explicit…, Every process whose name matches, case-insensitively. Matched with and without…, Whether a process exists *and* has not become a zombie. Distinct from… (+4 more)

### Community 97 - "ScreenService"
Cohesion: 0.19
Nodes (10): Returns the primary screen size as (width, height)., Returns information about connected monitors., Release the backend's screen handle., High-level screen service. Responsible for screen capture operations. The…, ScreenService, make_fake_screen(), asyncio, A capture failure must surface, not be turned into an empty frame that OCR… (+2 more)

### Community 98 - "window/tools.py"
Cohesion: 0.25
Nodes (19): close_window(), focus_window(), get_active_window(), get_window_bounds(), get_window_state(), list_windows(), maximize_window(), minimize_window() (+11 more)

### Community 99 - "AetherOS HUD State Gallery (7-panel montage)"
Cohesion: 0.17
Nodes (19): Radial Tick Ring (audio level meter), Demo Command: "move the mouse 300 pixels to the right", HUD ERROR State, HUD EXECUTING State, AetherOS HUD State Gallery (7-panel montage), HUD IDLE State, HUD LISTENING State, move_relative Tool Invocation (+11 more)

### Community 100 - "05_RUNTIME_FLOW_10.md"
Cohesion: 0.05
Nodes (40): 05_RUNTIME_FLOW.md, Alternative Strategy Selection, Browser Recovery, Checkpoint System, Circuit Breaker, Complete Recovery Runtime Flow, Complete Self-Healing Architecture, Critical Errors (+32 more)

### Community 101 - "BaseError"
Cohesion: 0.13
Nodes (12): BaseError, Any, Exception, Base exception for the entire AetherOS project. Every custom exception should…, Convert the exception into a structured dictionary. Useful for logging, APIs,…, HUDError, HUDProcessError, HUDUnavailableError (+4 more)

### Community 102 - "LLMProvider"
Cohesion: 0.12
Nodes (9): LLMProvider, ABC, Return all available models., Change the active model., Provider name. Example: OpenAI Ollama OpenRouter, Initialize provider resources., Release provider resources., Returns True if provider is healthy. (+1 more)

### Community 103 - "context.py"
Cohesion: 0.06
Nodes (39): Level 1+2: import every tool module, report registration. The module list is…, Parameter, Agent context assembly. One :class:`AgentContext` is everything the model needs…, Agent planner. One responsibility: ``GOAL -> the next action``. The planner…, Exception, ToolError, Recovery — bounded self-healing between step attempts. A retry that changes…, One move within a recovery strategy. Either a tool call, or a pause, or both —… (+31 more)

### Community 104 - "PyAutoGuiMouse"
Cohesion: 0.11
Nodes (3): PyAutoGuiMouse, Report whether a mouse button is physically held right now. PyAutoGUI cannot…, PyAutoGUI implementation of MouseController.

### Community 105 - "02_ARCHITECTURE_02.md"
Cohesion: 0.05
Nodes (39): 02_ARCHITECTURE.md, 10. State Manager, 11. Coordinator, 12. Execution Lifecycle, 13. Folder Structure, 1. Core Philosophy, 2. Core Components, 3. Orchestrator (+31 more)

### Community 106 - "05_RUNTIME_FLOW_03.md"
Cohesion: 0.05
Nodes (39): 05_RUNTIME_FLOW.md, Alternative Strategies, Atomic Execution, Browser, Cancellation, Complete Execution Pipeline, Complete Execution Sequence, Dependency Graph (+31 more)

### Community 107 - "PyAutoGuiClipboard"
Cohesion: 0.22
Nodes (5): PyAutoGuiClipboard, Whether the clipboard holds no data of any format. Counting formats rather than…, Describe what the clipboard holds. Files are checked before images and images…, Clipboard backend. Text transfer is implemented using pyperclip. Image and file…, Whether any of ``formats`` is currently on the clipboard.…

### Community 108 - "process/tools.py"
Cohesion: 0.29
Nodes (16): execute_command(), execute_shell(), get_process_info(), kill_process(), list_processes(), process_exists(), _processes(), Any (+8 more)

### Community 109 - "05_RUNTIME_FLOW_04.md"
Cohesion: 0.05
Nodes (39): 05_RUNTIME_FLOW.md, Argument Validation, Complete Routing Flow, Complete Tool Calling Architecture, Controller Resolution, Dependency Rules, Dynamic Tool Discovery, Engine Dispatcher (+31 more)

### Community 110 - "ToolCall"
Cohesion: 0.47
Nodes (3): Record a call the model asked for. Accepts the parse layer's :class:`ToolCall`…, A tool call the model requested, with usable arguments., ToolCall

### Community 111 - "ToolCommandService"
Cohesion: 0.13
Nodes (6): Any, Bridge between the AetherOS CLI and Tool Framework., Return registered tool names., Execute a registered AetherOS tool. Raises ToolError on failure; the CLI…, ToolCommandService, main()

### Community 112 - "CLIUI"
Cohesion: 0.14
Nodes (5): CLIUI, Render a model response., Render a secondary line beneath a response., Clear the terminal and display the AetherOS CLI startup screen., Terminal user interface for AetherOS CLI.

### Community 113 - "Layer"
Cohesion: 0.29
Nodes (7): Layer, ABC, One element of the overlay, drawn back to front. Layers are stateless with…, One arc group in the ring system., Concentric rotating arc groups. The dominant structural element: thin technical…, RingLayer, RingSpec

### Community 114 - "tool_calls.py"
Cohesion: 0.20
Nodes (14): MalformedToolCall, _parse_arguments(), _parse_entry(), Any, Safe parsing of a provider's tool-calling response. Everything a model emits is…, Return ``(arguments, error)``; exactly one is meaningful., The argument string to replay in the assistant message., Read ``key`` from a mapping or an attribute of an object. (+6 more)

### Community 115 - "qcolor"
Cohesion: 0.16
Nodes (10): QLinearGradient, QPointF, A barely-there radial wash behind everything. Gives the luminous elements…, VignetteLayer, _bin_weight(), Stable 0.35..1.0 weight for one bin., qcolor(), A directional fade across a ring, used to make arcs look lit from one side… (+2 more)

### Community 116 - "GlowCache"
Cohesion: 0.17
Nodes (7): QPixmap, GlowCache, RGB, Blit an additive glow. Additive compositing is what makes overlapping energy…, Pre-rendered radial glows. Radial gradients are by far the most expensive part…, Set the device pixel ratio. Cached pixmaps are rendered at physical resolution,…, A soft circular glow of the given radius and colour.

### Community 117 - "screen/tools.py"
Cohesion: 0.45
Nodes (10): capture_region(), capture_screen(), _describe(), list_monitors(), Any, Summarise a captured frame. A capture is a multi-megabyte pixel array. Tool…, save_region_screenshot(), save_screenshot() (+2 more)

### Community 118 - "Renderer"
Cohesion: 0.14
Nodes (7): Exception, QPainter, Draw one frame. Returns how long it took, in seconds., Draws the scene, back to front. Owns the layer stack and the glow cache. Each…, Read and clear the most recent layer failure., Drop cached pixmaps, e.g. after a resize or theme change., Renderer

### Community 119 - "voice_error.py"
Cohesion: 0.07
Nodes (30): AudioDeviceError, MicrophoneUnavailableError, Exception, The requested audio device is missing or cannot be opened., Microphone capture could not be started. AetherOS must remain usable without a…, Transcription failed, or the STT model could not be loaded., Speech synthesis or audio playback failed., Base exception for all voice-subsystem errors. Examples: - Microphone… (+22 more)

### Community 120 - "TestNonUnicodeTerminal"
Cohesion: 0.14
Nodes (10): cp1252_stdout(), fixture, MonkeyPatch, ``errors="replace"`` is the second half of the fix. Without it a single…, Replace stdout with a real cp1252 text stream. A ``TextIOWrapper`` over…, The regression itself: this raised UnicodeEncodeError from _show_logo., Asserts the mechanism, not just the absence of a crash — so that a future…, StringIO has no ``reconfigure``, which is how pytest's own capture and most… (+2 more)

### Community 121 - "strategy.py"
Cohesion: 0.09
Nodes (28): Verification — reading state back after a desktop action. The public surface is…, Enum, str, The result contract every desktop tool returns. Before this module every…, Outcome of one desktop action, as the model sees it. Distinct from…, Whether the caller may proceed as if the action happened. False when the…, The JSON shape the model receives. ``verified`` is lifted to the top level…, Outcome of the verification pass for a single action. ``str`` mixin so the… (+20 more)

### Community 122 - "renderer.py"
Cohesion: 0.18
Nodes (8): CoreLayer, The glowing central core. Drawn as stacked additive blooms under a hot inner…, ParticleLayer, An orbiting particle field. Positions are a closed-form function of the scene…, A ring of fine radial graduations. Pure technical texture — the detail that…, TickLayer, A radial waveform around the core. Bars read the scene's amplitude history,…, WaveformLayer

### Community 123 - "ToolDiscovery"
Cohesion: 0.20
Nodes (5): Clears imported module history. Useful for testing., Automatically discovers and imports tool modules. Importing a module executes…, Discover tools from multiple packages. Returns: List of imported module names., Import a package and every module beneath it. Returns the modules imported by…, ToolDiscovery

### Community 124 - "test_interface_contracts.py"
Cohesion: 0.19
Nodes (10): _incomplete_implementations(), _is_interface_module(), _package_modules(), parametrize, Every concrete backend must actually satisfy its interface.…, Guard the guard: an import or filtering bug that examined no classes would make…, Six modules used absolute imports (``from core.logging import ...``) that…, Classes that inherit an AetherOS ABC but left abstract methods unimplemented. (+2 more)

### Community 125 - "Application"
Cohesion: 0.21
Nodes (6): main(), Application, Restart the application., Main AetherOS application. Responsible for managing the application's…, Returns whether the application is running., Start the application.

### Community 126 - "DesktopError"
Cohesion: 0.06
Nodes (42): DesktopError, Exception, Base exception for all desktop automation errors. Examples: - Mouse movement…, Any, The automation engine — ACTION → EXECUTE → VERIFY → RETURN, in a loop. Every…, Trim a tool's return value to something a result can carry., _summarise_value(), Automation — multi-step desktop work with verification, retries and rollback.… (+34 more)

### Community 127 - "OpenAICompatibleProvider"
Cohesion: 0.18
Nodes (3): OpenAICompatibleProvider, Any, Provider implementation for OpenAI-compatible APIs. The same implementation can…

### Community 128 - "._run"
Cohesion: 0.22
Nodes (7): Any, Execute a registered tool, reporting failure as a value. Never raises for a…, Single execution path shared by execute() and execute_safe()., The execution budget for one tool, in seconds. A tool's own declared timeout…, Call the tool function, handling both sync and async tools., Record that a tool ran, without recording what it was given. Tool arguments are…, Execute a registered tool, raising on failure. Raises ------ ToolError Unknown…

### Community 129 - "vision/tools.py"
Cohesion: 0.40
Nodes (12): analyze_screen(), _blocks(), _capture(), detect_screen_objects(), find_text(), Any, OCR a saved image. Kept separate from read_screen_text so text recognition can…, Capture the screen as a vision Image. ScreenService returns a raw BGR… (+4 more)

### Community 130 - "agents/__init__.py"
Cohesion: 0.06
Nodes (20): _describe_call(), _describe_result(), IterationInfo, Where the run is in its budget. Carried explicitly because the model behaves…, The single system message: instructions, goal, budget, digests. Everything that…, One digest line for a call: names, never values. The model already has the…, One digest line for a result: outcome, and why if it failed., Shorten ``text`` to ``limit`` characters, saying so explicitly. (+12 more)

### Community 131 - "application/tools.py"
Cohesion: 0.39
Nodes (11): close_application(), get_application_info(), is_application_running(), launch_application(), launch_url(), Any, Application tools. These are the tools a model reaches for first -- "open…, restart_application() (+3 more)

### Community 132 - "05_RUNTIME_FLOW_09.md"
Cohesion: 0.05
Nodes (39): 05_RUNTIME_FLOW.md, Complete LLM Runtime, Complete LLM Runtime Flow, Context Compression, Cost Optimizer, Dependency Rules, Fallback Runtime, Future Enhancements (+31 more)

### Community 133 - "04_PROJECT_STRUCTURE_05.md"
Cohesion: 0.05
Nodes (38): 04_PROJECT_STRUCTURE.md, 10. accessibility/, 11. automation/, 12. verification/, 13. tools/, 14. wrappers/, 15. utils/, 1. mouse/ (+30 more)

### Community 134 - "TestRegisteredToolSurface"
Cohesion: 0.08
Nodes (13): fixture, ToolRegistry.register raises on a collision, so a duplicate name across two…, A category vanishing is the visible symptom of a module that stopped importing., The CLI prints "No tools registered." from an empty registry, and that message…, Every vision tool was unreachable in practice: a full-screen PaddleOCR pass…, The other half of the same rule. A declared budget is an admission that the…, The schema is the only thing the model sees. A tool whose schema is wrong is…, Every tool module uses ``from __future__ import annotations``, so annotations… (+5 more)

### Community 135 - "04_PROJECT_STRUCTURE_06.md"
Cohesion: 0.05
Nodes (38): 04_PROJECT_STRUCTURE.md, 10. parsing/, 11. models/, 12. cache/, 13. pipelines/, 14. datasets/, 15. benchmarking/, 16. utils/ (+30 more)

### Community 136 - "FakeScreen"
Cohesion: 0.21
Nodes (5): FakeScreen, Any, ndarray, Path, A screen controller backed by a fixed array instead of a display. Lets the…

### Community 137 - "05_RUNTIME_FLOW_06.md"
Cohesion: 0.05
Nodes (38): 05_RUNTIME_FLOW.md, Browser Vision, Capture Manager, Capture Output, Change Detection, Complete Vision Runtime, Complete Vision Runtime Flow, Continuous Observation (+30 more)

### Community 138 - "cli/main.py"
Cohesion: 0.38
Nodes (5): CommandParser, ParsedCommand, Parses user input into a command name and arguments. Examples: "help" ->…, Parse a command string. Empty input returns None., Represents a parsed CLI command.

### Community 139 - "TestEveryToolModuleImports"
Cohesion: 0.33
Nodes (4): parametrize, Guard the guard: a discovery bug that found nothing would make every other test…, A tool module that cannot be imported registers nothing, and bootstrap swallows…, TestEveryToolModuleImports

### Community 140 - "AetherOS Text-Only HUD Overlay"
Cohesion: 0.33
Nodes (9): AETHEROS Wordmark Header, Dark Non-Intrusive Overlay Design, Desktop Mouse Automation Intent, AetherOS Text-Only HUD Overlay, Text-Only HUD Render Mode, TRANSCRIBING State Indicator, Live Transcript Readout, Voice Command: move the mouse 300 pixels (+1 more)

### Community 141 - "._bootstrap_llm"
Cohesion: 0.33
Nodes (3): LLMConfig, Configuration for an OpenAI-compatible LLM provider. Values can be provided…, main()

### Community 142 - "Any"
Cohesion: 0.22
Nodes (5): Any, Returns process information. Example: name pid cpu_percent memory_usage…, Returns all running processes., Find a process by PID., Find processes by executable name.

### Community 144 - "AetherOS Voice HUD (zoomed capture)"
Cohesion: 0.39
Nodes (8): AetherOS Voice HUD (zoomed capture), AETHEROS Letter-Spaced Wordmark, Central Glowing Orb Visualizer, Live Transcript Text Display, Radial Particle and Arc Field, TRANSCRIBING HUD State, Transparent Circular Desktop Overlay, Voice Command: "move the mouse 300 pixels"

### Community 145 - "CLIRuntime"
Cohesion: 0.32
Nodes (3): CLIRuntime, Read one prompt line without blocking the event loop. `console.input()` blocks…, Interactive AetherOS CLI runtime.

### Community 146 - "_win32_clipboard"
Cohesion: 0.29
Nodes (4): Any, Remove everything from the clipboard. ``EmptyClipboard`` rather than copying an…, Return the ``win32clipboard`` module. Imported lazily so this module stays…, _win32_clipboard()

### Community 147 - ".save"
Cohesion: 0.25
Nodes (5): ndarray, Path, Capture the primary screen. Returns: BGR image array of shape (height, width,…, Capture a screen region., Save a captured frame to disk.

### Community 148 - "02_ARCHITECTURE_03.md"
Cohesion: 0.05
Nodes (37): 02_ARCHITECTURE.md, 10. Memory Agent, 11. Research Agent, 12. Coding Agent, 13. Trading Agent, 14. Voice Agent, 15. Learning Agent, 16. Agent Communication (+29 more)

### Community 149 - "main"
Cohesion: 0.33
Nodes (6): Bootstrapper System Initialization, main(), How long does OCR actually take, cold then warm? The executor allows 30s., read_screen_text OCR Tool, ToolExecutor Tool Execution Engine, tool_registry Central Tool Registry

### Community 150 - ".download"
Cohesion: 0.29
Nodes (4): Path, Capture a screenshot of the current page., Capture a screenshot of a specific element., Click a download element and save the resulting file.

### Community 151 - ".generate"
Cohesion: 0.29
Nodes (4): Any, Execute a tool-calling request. Returns: Provider-specific tool call response., Generate a complete response., Stream tokens incrementally.

### Community 152 - "WindowBounds"
Cohesion: 0.20
Nodes (5): Window identity and geometry. A title is not an identity. Two Explorer windows…, A window's screen rectangle. Stored as origin plus extent rather than as two…, Midpoint, for aiming a click at a window without knowing its layout., WindowBounds, Win32 window backend. Uses pywin32 directly rather than pygetwindow (which…

### Community 153 - "Mouse Automation Layering Diagram"
Cohesion: 0.57
Nodes (7): Dependency Inversion for Automation Backends, Layered Desktop Automation Stack (Interface -> Backend -> Service -> Tool -> Agent), Mouse Automation Layering Diagram, Mouse Tool Definition (LLM/Agent Tool Exposure), MouseInterface (Abstract Mouse Contract), MouseService (High-Level Mouse API), PyAutoGUIBackend (Mouse Backend Implementation)

### Community 154 - "05_RUNTIME_FLOW_08.md"
Cohesion: 0.05
Nodes (37): 05_RUNTIME_FLOW.md, Authentication Runtime, Browser Components, Browser Context, Browser Events, Browser Launch Pipeline, Browser Lifecycle, Browser Manager (+29 more)

### Community 155 - "TestFailureHandling"
Cohesion: 0.29
Nodes (3): A vision tool invoked before bootstrap has run. The agent should get a readable…, The duration is what makes a slow-then-failed tool distinguishable from one…, TestFailureHandling

### Community 156 - "main"
Cohesion: 0.33
Nodes (5): main(), pyautogui Library, PyAutoGuiMouse Backend, Is move_relative's round trip exact? §6 'incorrect coordinate handling'., pyautogui Desktop Automation

### Community 157 - "test_ui.py"
Cohesion: 0.33
Nodes (3): _ensure_unicode_output(), Make stdout/stderr able to carry the UI's box-drawing characters. On Windows a…, The terminal UI must not be able to abort the application. Bootstrap succeeding…

### Community 158 - "MSSScreen"
Cohesion: 0.13
Nodes (11): MSSScreen, Returns primary monitor size as (width, height)., MSS implementation of the ScreenController interface. Provides high-performance…, Returns monitor metadata. Index 0 of ``mss.monitors`` is the virtual bounding…, Release MSS resources., Path, mss raises on construction without a display, so the DI container would…, cv2.imwrite expects BGR, which is what capture() returns. Passing the frame… (+3 more)

### Community 159 - "TestDetectScreenObjects"
Cohesion: 0.33
Nodes (3): ultralytics and its weights are optional, so the agent has to be told the…, execute() is the raising variant; execute_safe() is the one the agent loop uses., TestDetectScreenObjects

### Community 160 - ".evaluate"
Cohesion: 0.40
Nodes (3): Any, Execute JavaScript in the current page., Return currently available browser pages.

### Community 161 - ".copy_files"
Cohesion: 0.40
Nodes (3): Path, Copy one or more files/folders to the clipboard., Returns copied file paths. Returns: Empty list if clipboard contains no files.

### Community 162 - ".copy_image"
Cohesion: 0.40
Nodes (3): Any, Copy an image to the clipboard., Returns an image from the clipboard. Returns: None if clipboard doesn't contain…

### Community 163 - ".open_file"
Cohesion: 0.40
Nodes (3): Path, Start a new process. Returns: Process ID (PID), Open a file with its default application. Returns: Process ID if available.

### Community 164 - ".grab"
Cohesion: 0.40
Nodes (3): Any, Exception, ndarray

### Community 165 - "dashboard.md"
Cohesion: 0.05
Nodes (37): AetherOS Dashboard Architecture, Agent Monitor, Analytics, Analytics Dashboard, API Layer, Architecture, Authentication, Dashboard API (+29 more)

### Community 167 - "discover Module Import Discovery Script"
Cohesion: 0.67
Nodes (3): discover Module Import Discovery Script, tool_registry Tool Registration, AetherOS Main Package

### Community 172 - "agent_loop.py"
Cohesion: 0.29
Nodes (5): AgentLoopResult, The LLM ↔ tool execution loop. One run is a bounded conversation: the model is…, Record of one tool the loop attempted during a run., Outcome of a full loop run., ToolInvocation

### Community 173 - "testing.md"
Cohesion: 0.05
Nodes (37): AetherOS Testing Architecture, Agent Testing, API Testing, Architecture, Browser Testing, CI Integration, Coverage, Design Philosophy (+29 more)

### Community 174 - "bootstrapper"
Cohesion: 0.67
Nodes (3): bootstrapper(), fixture, A bootstrapper over the isolated container, with detection opted out.…

### Community 177 - "03_TECH_STACK.md"
Cohesion: 0.05
Nodes (35): 10. Databases, 11. API Layer, 12. Authentication, 13. Logging, 14. Configuration, 15. Testing, 16. Deployment, 17. Monitoring (+27 more)

### Community 178 - "04_PROJECT_STRUCTURE_08.md"
Cohesion: 0.05
Nodes (36): 04_PROJECT_STRUCTURE.md, 10. ranking/, 11. compression/, 12. summarization/, 13. indexing/, 14. persistence/, 15. forgetting/, 16. synchronization/ (+28 more)

### Community 179 - "04_PROJECT_STRUCTURE_10.md"
Cohesion: 0.05
Nodes (36): 04_PROJECT_STRUCTURE.md, 🎉 04_PROJECT_STRUCTURE.md Complete, 10. websocket/, 11. scheduler/, 12. plugins/, 13. integrations/, 14. monitoring/, 15. logging/ (+28 more)

### Community 183 - "agents.md"
Cohesion: 0.05
Nodes (36): AetherOS Multi-Agent Architecture, Agent Communication, Agent Hierarchy, Agent Lifecycle, Agent State, AGENTS.md, Analytics, Architecture Overview (+28 more)

### Community 184 - "trading.md"
Cohesion: 0.05
Nodes (36): AetherOS Trading Intelligence Architecture, Alerts, Analysis Engine, Analytics, Architecture, Backtesting Engine, Broker Layer, Chart Engine (+28 more)

### Community 185 - "05_RUNTIME_FLOW_02.md"
Cohesion: 0.06
Nodes (35): 05_RUNTIME_FLOW.md, Agent Communication, Agent Lifecycle, Agent Philosophy, Agent Priority, Agent Security Rules, Agent States, Browser Agent (+27 more)

### Community 186 - "01_VISION.md"
Cohesion: 0.06
Nodes (33): 1. Goal-Oriented Intelligence, 2. Observe Before Acting, 3. Think Before Executing, 4. Verify Every Action, 5. Learn Continuously, 6. Modular by Design, AetherOS Vision, Autonomous Execution Cycle (+25 more)

### Community 187 - "core.md"
Cohesion: 0.06
Nodes (34): AetherOS Core Architecture, Async Utilities, Cache, Concurrency, Configuration System, Constants, Core Design Rules, CORE.md (+26 more)

### Community 199 - "02_ARCHITECTURE_04.md"
Cohesion: 0.06
Nodes (33): 02_ARCHITECTURE.md, 10. Verification Engine, 11. Execution Engine, 12. Learning Engine, 13. Engine Communication, 14. Folder Structure, 1. Engine Philosophy, 2. Engine Architecture (+25 more)

### Community 200 - "04_PROJECT_STRUCTURE_03.md"
Cohesion: 0.06
Nodes (33): 04_PROJECT_STRUCTURE.md, Agent Communication, Agent Context, Agent Design Standards, Agent Layer Philosophy, base_agent.py, Browser Agent, CEO Agent (+25 more)

### Community 201 - "04_PROJECT_STRUCTURE_01.md"
Cohesion: 0.06
Nodes (32): 04_PROJECT_STRUCTURE.md, assets/, configs/, data/, Development Workflow, docker-compose.yml, Dockerfile, docs/ (+24 more)

### Community 202 - "04_PROJECT_STRUCTURE_07.md"
Cohesion: 0.06
Nodes (32): 04_PROJECT_STRUCTURE.md, 10. memory/, 11. cache/, 12. tokenization/, 13. models/, 14. benchmarking/, 15. utils/, 1. providers/ (+24 more)

### Community 203 - "05_RUNTIME_FLOW_12.md"
Cohesion: 0.06
Nodes (32): 05_RUNTIME_FLOW.md, Agent Collaboration, Complete Runtime Overview, End-to-End Runtime Guarantees, Example User Request, Final Summary, Full Component Interaction, Future Runtime Vision (+24 more)

### Community 204 - "api.md"
Cohesion: 0.06
Nodes (32): AetherOS Unified API Architecture, Analytics, API Documentation, API Execution Flow, API Gateway, API.md, API Schemas, Architecture (+24 more)

### Community 205 - "browser.md"
Cohesion: 0.06
Nodes (32): Accessibility Layer, AetherOS Browser Automation Architecture, Architecture, Authentication, Automation Layer, Browser Contexts, Browser Execution Flow, BROWSER.md (+24 more)

### Community 206 - "logging.md"
Cohesion: 0.06
Nodes (31): AetherOS Logging & Observability Architecture, Alerts, Analytics, Architecture, Audit Logs, Dashboard Integration, Design Philosophy, Design Principles (+23 more)

### Community 207 - "memory.md"
Cohesion: 0.06
Nodes (31): AetherOS Memory Architecture, Analytics, Architecture, Cache, Design Philosophy, Design Principles, Directory Structure, Document Memory (+23 more)

### Community 208 - "05_RUNTIME_FLOW_01.md"
Cohesion: 0.06
Nodes (30): 05_RUNTIME_FLOW.md, Complete Runtime Layers, Dependency Rules, Engine Selection, Execution Layer, Executor Agent, High-Level Runtime, Layer 1 — User Interaction (+22 more)

### Community 209 - "automation.md"
Cohesion: 0.06
Nodes (30): AetherOS Automation Engine Architecture, Analytics, Architecture, Automation API, Automation Engine, Automation Execution Flow, AUTOMATION.md, Design Philosophy (+22 more)

### Community 210 - "database.md"
Cohesion: 0.06
Nodes (30): AetherOS Database Architecture, Analytics, Architecture, Backup System, Cache Layer, Connection Manager, Core Tables, Database API (+22 more)

### Community 211 - "vision.md"
Cohesion: 0.06
Nodes (30): AetherOS Vision Intelligence Architecture, Analytics, Architecture, Coordinate Mapper, Design Philosophy, Design Principles, Directory Structure, Embedding Engine (+22 more)

### Community 212 - "desktop.md"
Cohesion: 0.07
Nodes (29): AetherOS Desktop Automation Architecture, Application Manager, Architecture, Audio Manager, Automation Layer, Clipboard, Design Philosophy, Design Principles (+21 more)

### Community 213 - "llm.md"
Cohesion: 0.07
Nodes (29): AetherOS Large Language Model (LLM) Architecture, Analytics, Architecture, Cache, Context Builder, Conversation Manager, Design Philosophy, Design Principles (+21 more)

### Community 214 - "planner.md"
Cohesion: 0.07
Nodes (29): AetherOS Planning & Task Orchestration Architecture, Agent Selector, Analytics, Architecture, Dependency Engine, Design Philosophy, Design Principles, Directory Structure (+21 more)

### Community 215 - "reasoning.md"
Cohesion: 0.07
Nodes (29): AetherOS Reasoning Engine Architecture, Analytics, Architecture, Cache, Confidence Engine, Constraint Solver, Context Analyzer, Decision Engine (+21 more)

### Community 216 - "00_INTRODUCTION.md"
Cohesion: 0.07
Nodes (28): 1. Introduction, 1. Observe Before Acting, 2. Reason Like a Human, 3. Modular Architecture, 4. Tool-Based Intelligence, 5. Multi-Agent Collaboration, 6. Continuous Learning, AetherOS (+20 more)

### Community 217 - "_started"
Cohesion: 0.13
Nodes (10): _FailingProvider, asyncio, BaseException, A provider that raises instead of answering. Not a :class:`FakeLLMProvider`…, A running, seeded state on its first iteration., A provider that cannot answer becomes a described failure, not a raise., A finished run has no next action, and costs no tokens to say so., _started() (+2 more)

### Community 218 - "PHASE_06_MEMORY.md"
Cohesion: 0.08
Nodes (25): Estimated Timeline, Final Deliverable, Folder Status After Phase 6, Milestone 10 — Mobile Companion (Future), Milestone 11 — Continuous Learning, Milestone 12 — Enterprise Features, Milestone 13 — Production Benchmark, Milestone 14 — Documentation (+17 more)

### Community 219 - "PHASE_02_LLM.md"
Cohesion: 0.08
Nodes (24): Deliverable, Estimated Timeline, Folder Status After Phase 2, Milestone 10 — Change Detection, Milestone 11 — Window Recognition, Milestone 12 — Visual Search API, Milestone 13 — Coordinate Mapper, Milestone 14 — Vision Benchmark (+16 more)

### Community 220 - "PHASE_03_TOOLS.md"
Cohesion: 0.08
Nodes (24): Deliverable, Estimated Timeline, Folder Status After Phase 3, Milestone 10 — Learning Engine, Milestone 11 — Memory Cache, Milestone 12 — Storage Layer, Milestone 13 — Memory API, Milestone 14 — Memory Benchmark (+16 more)

### Community 221 - "PHASE_04_DESKTOP.md"
Cohesion: 0.08
Nodes (24): Deliverable, Estimated Timeline, Folder Status After Phase 4, Milestone 10 — Window Management, Milestone 11 — Verification Engine, Milestone 12 — Hybrid Automation Layer, Milestone 13 — Browser API, Milestone 14 — Automation Benchmark (+16 more)

### Community 222 - "PHASE_05_VISION.md"
Cohesion: 0.08
Nodes (24): Deliverable, Estimated Timeline, Folder Status After Phase 5, Milestone 10 — Task Graph Engine, Milestone 11 — Decision Engine, Milestone 12 — Prompt Library, Milestone 13 — Workflow Engine, Milestone 14 — Agent Benchmark (+16 more)

### Community 223 - "vision/conftest.py"
Cohesion: 0.12
Nodes (17): bgr_image(), fake_ocr(), FakeOCRProvider, isolated_container(), make_unclosable_ocr(), fixture, Fixtures for the vision test suite. The fakes here implement the real provider…, A small BGR image whose channels are all different. Uniform grey would hide a… (+9 more)

### Community 224 - "AetherOS Vision Engine"
Cohesion: 0.10
Nodes (20): AetherOS Vision Engine, Architecture, Bootstrap and DI, Capabilities, Colour space, Dependencies, Domain models, Errors (+12 more)

### Community 225 - "04_PROJECT_STRUCTURE_04.md"
Cohesion: 0.11
Nodes (17): 04_PROJECT_STRUCTURE.md, base_engine.py, Complete Engine Flow, context.py, Dependency Rules, Directory Structure, Engine Communication, Engine Development Standards (+9 more)

### Community 226 - "KeyboardController"
Cohesion: 0.12
Nodes (8): KeyboardController, ABC, Returns True if the key is currently pressed., Release all modifier keys. Useful after automation failures., Press and release a key., Press multiple keys sequentially., Abstract interface for keyboard automation. Every keyboard implementation must…, Execute a keyboard shortcut. Example: Ctrl+C Ctrl+Shift+Esc Alt+Tab

### Community 227 - "04_PROJECT_STRUCTURE_02.md"
Cohesion: 0.12
Nodes (16): 04_PROJECT_STRUCTURE.md, 11. execution/, 14. exceptions/, 15. models/, 16. utils/, 4. scheduler/, 8. message_bus/, constants.py (+8 more)

### Community 228 - "FakeKeyboard"
Cohesion: 0.14
Nodes (4): FakeKeyboard, The original defect: this called ``controller.release()``, which exists on no…, Records calls instead of typing. Implements exactly the abstract methods, so…, TestKeyboardServiceMapsOntoTheInterface

### Community 230 - "5. Core components and their responsibilities"
Cohesion: 0.12
Nodes (16): 5.1 Startup layer, 5.2 Foundation layer (`core/`), 5.7 Action layer — `vision/`, 5.8 Action layer — `browser/`, 5.9 Written but not wired, 5. Core components and their responsibilities, Abstract interfaces, `Application` (+8 more)

### Community 231 - "vision/main.py"
Cohesion: 0.18
Nodes (12): Check, main(), Vision engine verification entry point. Run with:: python -m…, Run every verification stage., start(), expected_words(), Deterministic images for verifying the vision pipeline. The OCR path cannot be…, Render lines of text onto a white background. Returns a BGR :class:`Image`.… (+4 more)

### Community 232 - "AetherOS Architecture Audit & Development Plan"
Cohesion: 0.15
Nodes (12): AetherOS Architecture Audit & Development Plan, Code Quality Assessment, Executive Summary, Implementation Roadmap, MVP Complete When:, Repository Health: **Foundation Solid, Core Mission Missing**, Risk Mitigation, Strengths (+4 more)

### Community 233 - "AetherOS Development Plan & Architecture Analysis"
Cohesion: 0.15
Nodes (12): AetherOS Development Plan & Architecture Analysis, Conclusion, Critical Gaps vs. Architecture Documents, Current State: **Early Foundation (Phase 1 - Partially Complete)**, Executive Summary, High Risk Areas, Key Architectural Principles to Maintain, Mitigation Strategies (+4 more)

### Community 234 - "✅ Implemented (Foundation Layer)"
Cohesion: 0.15
Nodes (13): 10. Browser Automation (Stub), 11. CLI Runtime, 12. Bootstrap System, 1. Configuration System, 2. Logging System, 3. Error Framework, 4. Dependency Injection Container, 5. Event Bus (+5 more)

### Community 235 - "PlannerConfig"
Cohesion: 0.22
Nodes (5): PlannerConfig, The limit actually applied, once parallelism is accounted for., What the planner is willing to accept from one response. All three defaults are…, The one bounded number is clamped rather than trusted., TestPlannerConfig

### Community 236 - "DemoScript"
Cohesion: 0.18
Nodes (8): DemoScript, Total length of one pass, in seconds., Which step is current at `elapsed` seconds., The snapshot that should be showing at `elapsed` seconds., Every state the script visits, in order., A speech-like level, without any audio. Three unrelated periods multiplied…, A time-driven state walkthrough. Deliberately free of Qt, asyncio and threads:…, synthetic_amplitude()

### Community 237 - "test_input.py"
Cohesion: 0.19
Nodes (10): Register the global hotkey. Never raises: a hotkey that cannot be registered is…, keyboard(), mouse(), Any, fixture, Regression tests for the mouse and keyboard services, backends and tools. Every…, Put a fake-backed service in the container, then put things back. Only an…, Guard the guard. If a fake grew a ``release`` or ``tap`` method, every… (+2 more)

### Community 238 - "NullTTS"
Cohesion: 0.17
Nodes (3): NullTTS, AmplitudeCallback, Speech synthesis that produces no sound. Selected when the user disables spoken…

### Community 239 - "Folder Structure"
Cohesion: 0.18
Nodes (11): 1. orchestrator/, context.py, controller.py, dispatcher.py, executor.py, Folder Structure, lifecycle.py, manager.py (+3 more)

### Community 240 - "Folder"
Cohesion: 0.18
Nodes (11): 2. planner/, dependency.py, estimator.py, Folder, goal_parser.py, optimizer.py, planner.py, Purpose (+3 more)

### Community 241 - "Directory"
Cohesion: 0.18
Nodes (11): capture.py, charts.py, detection.py, Directory, matcher.py, ocr.py, preprocessing.py, Purpose (+3 more)

### Community 242 - "Purpose"
Cohesion: 0.22
Nodes (9): 3. coordinator/, coordinator.py, load_balancer.py, locks.py, monitor.py, priority.py, Purpose, registry.py (+1 more)

### Community 243 - "AetherOS — Codebase Guide"
Cohesion: 0.22
Nodes (8): 12. Glossary, 1.1 What AetherOS is meant to be, 1.2 What AetherOS is *right now*, 1.3 The three design rules that explain most of the code, 1. Project purpose, AetherOS — Codebase Guide, Table of contents, Where to go next

### Community 244 - "11. Known gaps and gotchas"
Cohesion: 0.22
Nodes (9): 11.1 The `aether` console script does not work, 11.2 Two module identities, 11.3 `core/application.py` is dead code, 11.4 Whole subsystems are written but unwired, 11.5 The trading core does not exist, 11.6 Desktop subsystems still to come, 11.7 Naming differences from the original spec, 11.8 Small things (+1 more)

### Community 245 - "4. Main execution flow"
Cohesion: 0.22
Nodes (9): 4.1 The three phases, 4.2 Phase 1 — Startup, step by step, 4.3 Phase 2 — One turn of the conversation, 4.4 The `ask` command — the heart of the system, 4.5 Phase 3 — Shutdown, 4. Main execution flow, Step 10 in detail — how the LLM gets wired, Why step 5 is defensive (+1 more)

### Community 246 - "5.6 Action layer — `desktop/`"
Cohesion: 0.22
Nodes (9): 5.6 Action layer — `desktop/`, `ApplicationService`, `AutomationEngine`, `MouseService` / `KeyboardService` / `ClipboardService` / `ScreenService`, `ProcessService`, `SafetyPolicy` and `PathGuard`, `TerminalService`, `Verifier` (verification system) (+1 more)

### Community 247 - "Directory"
Cohesion: 0.25
Nodes (8): Desktop Engine, Directory, display.py, filesystem.py, keyboard.py, mouse.py, process.py, window.py

### Community 248 - "Critical Findings"
Cohesion: 0.25
Nodes (8): 1. Mission-Architecture Mismatch (SEVERITY: CRITICAL), 2. Agent System Not Implemented (SEVERITY: CRITICAL), 3. LLM Infrastructure Disconnected (SEVERITY: HIGH), 4. Event Bus Inactive (SEVERITY: MEDIUM), 5. Memory System Missing (SEVERITY: HIGH), 6. Vision System Incomplete (SEVERITY: MEDIUM), 7. Container Confusion (SEVERITY: LOW), Critical Findings

### Community 249 - "10. Visual sequence diagrams"
Cohesion: 0.25
Nodes (8): 10.1 Startup — `python main.py`, 10.2 A simple command — `tools`, 10.3 The main flow — one `ask` turn with two tool calls, 10.4 When a tool fails — the model recovers, 10.5 A dangerous tool — the confirmation gate, 10.6 A workflow — `AutomationEngine`, 10.7 Shutdown, 10. Visual sequence diagrams

### Community 250 - "5.4 Reasoning layer (`llm/`)"
Cohesion: 0.25
Nodes (8): 5.4 Reasoning layer (`llm/`), `get_llm_tools`, `LLMConfig`, `LLMEngine`, `LLMProviderManager`, `LLMToolLoop`, `OpenAICompatibleProvider`, `parse_llm_response`

### Community 251 - "Architectural Inconsistencies"
Cohesion: 0.25
Nodes (8): 1. **Mission vs Implementation Gap**, 2. **Agent Architecture Not Implemented**, 3. **LLM Integration Incomplete**, 4. **Tool System vs Agent System Disconnect**, 5. **Event Bus Not Utilized**, 6. **Vision System Incomplete**, 7. **Memory System Missing**, Architectural Inconsistencies

### Community 252 - "._await_exit"
Cohesion: 0.29
Nodes (4): Ask a process to exit, then report whether it actually did. The report is read…, Stop a process immediately, then confirm it is gone., Ask a process to exit, and force it only if asking did not work. The escalation…, Poll until the process is gone, returning whether it went. Returns a bool…

### Community 253 - "Critical Path to MVP"
Cohesion: 0.29
Nodes (7): Critical Path to MVP, Phase 0: Fix Foundation (1 week), Phase 1: Agent Foundation (2 weeks), Phase 2: Trading Core (3 weeks), Phase 3: Probability & Risk (2 weeks), Phase 4: Validation & Memory (2 weeks), Phase 5: Backtesting (2 weeks)

### Community 254 - "7. Data flow through the application"
Cohesion: 0.29
Nodes (7): 7.1 Configuration flowing in (startup, once), 7.2 Capability flowing in (startup, once), 7.3 One `ask` turn, value by value, 7.4 What crosses each boundary, 7.5 The failure path, 7.6 Where data comes to rest, 7. Data flow through the application

### Community 255 - "Directory"
Cohesion: 0.33
Nodes (6): Directory, LLM Engine, parser.py, providers/, router.py, tools.py

### Community 256 - "3. Application entry points"
Cohesion: 0.33
Nodes (6): 3.1 `main.py` — the real entry point ✅, 3.2 `aether` console script — declared but broken ❌, 3.3 `pytest` — the test entry point ✅, 3.4 Standalone scripts — developer scratch space, 3.5 Entry points at a glance, 3. Application entry points

### Community 257 - "5.3 Tool layer (`tools/`)"
Cohesion: 0.33
Nodes (6): 5.3 Tool layer (`tools/`), `ToolDiscovery`, `ToolExecutor`, `ToolRegistry` and the `@tool` decorator, `ToolSchemaGenerator`, `ToolValidator`

### Community 258 - "5.5 User interface layer (`cli/`)"
Cohesion: 0.33
Nodes (6): 5.5 User interface layer (`cli/`), `CLIRuntime`, `CLIUI`, `CommandParser`, `CommandRegistry`, `ToolCommandService`

### Community 259 - "6. Dependency relationships"
Cohesion: 0.33
Nodes (6): 6.1 The layering rule, 6.2 Who depends on `core/`, 6.3 The inversion in one picture, 6.4 The container breaks the remaining cycles, 6.5 External dependencies, and which module owns each, 6. Dependency relationships

### Community 260 - "❌ Missing Critical Components (Trading Focus)"
Cohesion: 0.33
Nodes (6): 1. Agent System (CRITICAL), 2. Trading System (CRITICAL), 3. Memory System (CRITICAL), 4. Data Providers (CRITICAL for Trading), ❌ Missing Critical Components (Trading Focus), Repository Structure Analysis

### Community 262 - "2. High-level folder structure"
Cohesion: 0.40
Nodes (5): 2.1 The repository root, 2.2 Inside `src/aetheros/` — the packages that matter, 2.3 The one-sentence version, 2.4 Folder map as a diagram, 2. High-level folder structure

### Community 263 - "8. Important interfaces and implementations"
Cohesion: 0.40
Nodes (5): 8.1 The pattern, 8.2 The full table, 8.3 Why `LLMProvider` matters most, 8.4 Value objects you will meet everywhere, 8. Important interfaces and implementations

### Community 264 - "9. Visual architecture diagrams"
Cohesion: 0.40
Nodes (5): 9.1 The whole system, layered, 9.2 The tool system on its own, 9.3 The desktop layer's repeated shape, 9.4 The safety gate, 9. Visual architecture diagrams

### Community 265 - "Architecture Alignment Plan"
Cohesion: 0.40
Nodes (5): Architecture Alignment Plan, Step 1: Activate Core Infrastructure (Week 3), Step 2: Build Agent Pipeline (Week 3-5), Step 3: Add Intelligence Layer (Week 5-7), Step 4: Validation & Safety (Week 7-8)

### Community 266 - "Development Priority Matrix"
Cohesion: 0.40
Nodes (5): Development Priority Matrix, **P0 - CRITICAL (Must have for trading intelligence)**, **P1 - HIGH (Required for intelligent trading)**, **P2 - MEDIUM (Enhanced capabilities)**, **P3 - LOW (Nice to have)**

### Community 267 - "Architecture State by Module"
Cohesion: 0.50
Nodes (4): Architecture State by Module, ✅ COMPLETE & WORKING, ❌ MISSING (CRITICAL FOR MISSION), ⚠️ PARTIAL / DISCONNECTED

### Community 268 - "Conclusion"
Cohesion: 0.50
Nodes (4): Conclusion, Current State, Next Immediate Steps, Recommendation

### Community 269 - "Testing Strategy"
Cohesion: 0.50
Nodes (4): Integration Tests Required, Testing Strategy, Unit Tests Required, Validation Tests Required

### Community 270 - "PHASE_01_FOUNDATION.md"
Cohesion: 0.50
Nodes (3): Phase 1 — Foundation & Core Infrastructure (Weeks 1–6), Phase Overview, ROADMAP.md

### Community 271 - "Technology Stack Decisions"
Cohesion: 0.67
Nodes (3): Additions Required, Confirmed, Technology Stack Decisions

### Community 272 - "Architectural Principles (From claude.md)"
Cohesion: 0.67
Nodes (3): Architectural Principles (From claude.md), Followed ✅, Violated ❌

### Community 273 - "Dependency Flow Analysis"
Cohesion: 0.67
Nodes (3): Broken/Missing Flows, Current Working Flow, Dependency Flow Analysis

### Community 274 - "Tool Registration Flow (Working)"
Cohesion: 0.67
Nodes (3): Current State (Correct), Missing: Agent → Tool Execution, Tool Registration Flow (Working)

### Community 275 - "Testing Strategy"
Cohesion: 0.67
Nodes (3): Test Examples, Testing Strategy, Unit Tests (Required)

### Community 276 - "Dependency Analysis"
Cohesion: 0.67
Nodes (3): Broken/Missing Dependencies, Dependency Analysis, Working Dependencies

### Community 277 - "Technology Stack Decisions"
Cohesion: 0.67
Nodes (3): Confirmed Choices, Required Additions, Technology Stack Decisions

### Community 278 - "Immediate Action Plan (Next 2 Weeks)"
Cohesion: 0.67
Nodes (3): Immediate Action Plan (Next 2 Weeks), Week 1: Market Data + Trading Foundation, Week 2: Technical Analysis + Agent Foundation

## Ambiguous Edges - Review These
- `HUD THINKING State` → `HUD TRANSCRIBING State`  [AMBIGUOUS]
  hud_states.png · relation: semantically_similar_to

## Knowledge Gaps
- **1904 isolated node(s):** `AetherOS`, `1. Project Mission`, `2. Core Philosophy`, `3. Probability Is Not a Guarantee`, `4. Primary Architecture` (+1899 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3767 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `HUD THINKING State` and `HUD TRANSCRIBING State`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `get_logger()` connect `get_logger` to `VerificationResult`, `ErrorContext`, `PaddleOCRProvider`, `policy.py`, `cli/main.py`, `TerminalService`, `ContextBuilder`, `CLIRuntime`, `VoiceConfig`, `NullSTT`, `RecoveryRunner`, `VoicePipeline`, `bootstrapper.py`, `WakeWordActivator`, `Bootstrapper`, `ApplicationService`, `agent_loop.py`, `HUDConfig`, `YOLOProvider`, `Event`, `HUDProcess`, `WindowController`, `ProcessService`, `tool`, `Any`, `CommandRegistry`, `LifecycleManager`, `AgentError`, `BrowserService`, `MouseController`, `LLMEngine`, `ClipboardController`, `ProcessController`, `ScreenController`, `FasterWhisperSTT`, `SapiTTS`, `KeyboardController`, `context.py`, `NullTTS`, `voice_error.py`, `strategy.py`, `DesktopError`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `HUDConfig` connect `HUDConfig` to `Message`, `Scene`, `HUDService`, `test_wiring.py`, `Event`, `HUDProcess`, `bootstrapper.py`, `asyncio`, `HUDWindow`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `HUDService` connect `HUDService` to `Message`, `._bootstrap_hud`, `DemoScript`, `test_wiring.py`, `HUDConfig`, `Event`, `HUDProcess`, `bootstrapper.py`, `asyncio`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Image` (e.g. with `VisionService` and `reference_image()`) actually correct?**
  _`Image` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `AgentState` (e.g. with `ContextBuilder` and `_started()`) actually correct?**
  _`AgentState` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ToolRegistry` (e.g. with `ToolExecutor` and `builder()`) actually correct?**
  _`ToolRegistry` has 27 INFERRED edges - model-reasoned connections that need verification._