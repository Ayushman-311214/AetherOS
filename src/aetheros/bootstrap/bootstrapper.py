from __future__ import annotations

import importlib.util
import os

from ..tools.discovery import tool_discovery
from ..core.container import container

from ..core.logging.logging import(
    get_logger,
    setup_logging,
)
from ..tools.registry import tool_registry

class Bootstrapper:
    """
    Coordinates application startup and shutdown.

    The bootstrapper is responsible for initialization order.
    Actual implementation logic belongs to the individual
    subsystems/services.
    """

    def __init__(self) -> None:
        self._logger = get_logger("bootstrapper")

        self.tool_registry=tool_registry
        self._started = False
        # Runtime references
        self._container = None
        self._event_bus = None

        # Both are optional subsystems, gated on AETHEROS_HUD_ENABLED and
        # AETHEROS_VOICE_ENABLED. They stay None when disabled or when startup
        # degraded, and shutdown reads them to decide what to tear down.
        self._hud = None
        self._voice = None

        # The live execution-trace recorder. Observer-only: it subscribes to the
        # event bus, so it must be brought up after _bootstrap_events and torn
        # down before the bus is cleared. None until started.
        self._trace = None

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def container(self):
        return self._container

    @property
    def event_bus(self):
        return self._event_bus

    @property
    def hud(self):
        """
        The running HUD service, or None when the overlay is not up.
        """
        return self._hud

    @property
    def voice(self):
        """
        The running voice service, or None when voice is not up.
        """
        return self._voice

    @property
    def trace(self):
        """
        The live execution-trace recorder, or None when tracing is off.
        """
        return self._trace

    # ==========================================================
    # Startup
    # ==========================================================

    async def start(self) -> None:
        """
        Bootstrap AetherOS.
        """

        if self._started:
            self._logger.warning(
                "Bootstrapper already started."
            )
            return

        self._logger.info(
            "Bootstrapping AetherOS..."
        )

        try:
            # --------------------------------------------------
            # Configuration
            # --------------------------------------------------

            await self._bootstrap_config()

            # --------------------------------------------------
            # Logging
            # --------------------------------------------------

            await self._bootstrap_logging()

            # --------------------------------------------------
            # Dependency Injection
            # --------------------------------------------------

            await self._bootstrap_container()

            # --------------------------------------------------
            # Event System
            # --------------------------------------------------

            await self._bootstrap_events()

            # --------------------------------------------------
            # Live execution trace
            # --------------------------------------------------

            # Right after the bus, before any producer: the recorder subscribes
            # to TraceEvent here so it is already listening when the first
            # component (the LLM provider, the agent core) emits.
            await self._bootstrap_trace()

            # --------------------------------------------------
            # Future subsystems
            # --------------------------------------------------

            # Services before tools. Every @tool function resolves its service
            # from the container at call time, but importing the tool modules is
            # also what registers them — and vision tools depend on both
            # ScreenService and VisionService existing, so both subsystems are
            # bootstrapped first.
            await self._bootstrap_desktop()
            await self._bootstrap_vision()
            await self._bootstrap_browser()
            await self._bootstrap_trading()
            await self._bootstrap_tools()
            await self._bootstrap_memory()
            await self._bootstrap_llm()
            self._bootstrap_agents()

            # HUD before voice: the overlay subscribes to the voice events on
            # the bus, and VoiceServiceStarted is the event that takes it from
            # OFFLINE to IDLE. Starting voice first would publish that event
            # into a bus with no subscriber and leave the overlay dark.
            await self._bootstrap_hud()

            # Voice last of the subsystems: its reasoner resolves the
            # tool-enabled LLMEngine registered by _bootstrap_llm, and a spoken
            # turn can call any tool registered by _bootstrap_tools.
            await self._bootstrap_voice()

            # --------------------------------------------------
            # Lifecycle
            # --------------------------------------------------

            await self._bootstrap_lifecycle()

            # --------------------------------------------------
            # Health
            # --------------------------------------------------

            await self._bootstrap_health()

            self._started = True

            self._logger.info(
                "Bootstrap completed successfully."
            )

        except Exception:
            self._logger.exception(
                "AetherOS bootstrap failed."
            )

            await self.shutdown()

            raise

    # ==========================================================
    # Shutdown
    # ==========================================================

    async def shutdown(self) -> None:
        """
        Shutdown subsystems in reverse order.
        """

        if not self._started and self._container is None:
            return

        self._logger.info(
            "Shutting down AetherOS..."
        )

        await self._shutdown_health()
        await self._shutdown_lifecycle()
        # Reverse of startup: voice stops before the HUD so the overlay is
        # still subscribed when VoiceServiceStopped is published and can show
        # OFFLINE rather than freezing on its last state.
        await self._shutdown_voice()
        await self._shutdown_hud()
        await self._shutdown_llm()
        await self._shutdown_memory()
        await self._shutdown_browser()
        await self._shutdown_vision()
        await self._shutdown_desktop()
        # Trace before events: the recorder holds a subscription on the bus, so
        # it must unsubscribe (and flush its JSONL file) before the bus is
        # cleared out from under it.
        await self._shutdown_trace()
        await self._shutdown_events()
        await self._shutdown_container()
        await self._shutdown_logging()

        self._started = False

        self._logger.info(
            "Shutdown complete."
        )

    # ==========================================================
    # Bootstrap Modules
    # ==========================================================

    async def _bootstrap_config(self) -> None:
        self._logger.debug(
            "Loading configuration..."
        )

        # Configuration implementation will be connected here.

    async def _bootstrap_logging(self) -> None:
        self._logger.debug(
            "Initializing logging..."
        )

        self._logger.info(
            "File logging initialized."
        )

        # Logging is already available because the bootstrapper
        # itself uses get_logger().

    async def _bootstrap_container(self) -> None:
        self._logger.debug(
            "Building DI container..."
        )

        # The process-wide `container` singleton is the one every @ function
        # resolves its service from (see desktop/*/tools.py). Replacing
        # self._container with a fresh ServiceContainer here would split
        # registration across two containers: MouseService, ClipboardService and
        # VisionService would land on the private one while the tools looked for
        # them on the global one, and the first LLM-issued move_mouse would fail
        # with "Service 'MouseService' is not registered".
        self._container = container

        self._logger.info(
            "DI container initialized.",
        )

    async def _bootstrap_events(self) -> None:
        self._logger.debug(
            "Initializing event bus..."
        )

        from ..runtime.events.event_bus import EventBus
        from ..runtime.events.publisher import set_event_bus

        # One bus per application, created here because it has to exist before
        # any producer or consumer is built: the HUD subscribes during its own
        # startup and the voice pipeline publishes from its first turn.
        self._event_bus = EventBus()

        # Registered under both keys deliberately. `EventBus` is what a typed
        # constructor asks for; the string is what a @tool or a CLI command can
        # name without importing the runtime package.
        self._container.register_singleton(
            EventBus,
            lambda: self._event_bus,
        )

        self._container.register_singleton(
            "event_bus",
            lambda: self._event_bus,
        )

        # The module-level publish() helper resolves through this, so anything
        # that fires an event without holding a bus reference works too.
        set_event_bus(self._event_bus)

        self._logger.info(
            "Event system initialized."
        )

    async def _bootstrap_trace(self) -> None:
        self._logger.debug(
            "Initializing live execution trace..."
        )

        from ..config.config_loader import get_settings
        from ..core.observability import (
            LiveTraceUI,
            TraceFileWriter,
            TraceRecorder,
            resolve_level,
        )

        settings = get_settings()
        level = resolve_level(settings.TRACE_LEVEL)

        # The dashboard degrades to a no-op off a TTY (tests, piped output), so
        # constructing it unconditionally is safe; it simply never draws there.
        ui = LiveTraceUI()

        # Persistence is opt-out via TRACE_PERSIST. The writer opens its per-run
        # JSONL lazily on the first kept event, so an idle run leaves no file.
        writer = None
        if settings.TRACE_PERSIST:
            writer = TraceFileWriter(settings.LOG_DIR / "traces")

        recorder = TraceRecorder(
            event_bus=self._event_bus,
            level=level,
            ui=ui,
            writer=writer,
        )

        # Registered so the CLI `trace ...` commands can resolve the live
        # recorder and mutate it (set_level, clear, status).
        self._container.register_singleton(
            TraceRecorder,
            lambda: recorder,
        )
        self._container.register_singleton(
            "trace_recorder",
            lambda: recorder,
        )

        self._trace = recorder

        await recorder.start()

        self._logger.bind(
            level=recorder.level.name.lower(),
            persist=settings.TRACE_PERSIST,
        ).info("Live execution trace initialized.")

    async def _bootstrap_desktop(self) -> None:
        self._logger.debug("Initializing desktop services...")

        # ------------------------------------------------------
        # Mouse
        # ------------------------------------------------------

        from ..desktop.mouse.controller import MouseService
        from ..desktop.mouse.pyautogui_backend import PyAutoGuiMouse

        mouse_controller = PyAutoGuiMouse()

        self._container.register_singleton(
            PyAutoGuiMouse,
            lambda: mouse_controller,
        )

        self._container.register_singleton(
            MouseService,
            lambda: MouseService(
                container.resolve(PyAutoGuiMouse)
            ),
        )

        # ------------------------------------------------------
        # Keyboard
        # ------------------------------------------------------

        from ..desktop.keyboard.controller import KeyboardService
        from ..desktop.keyboard.pyautogui_backend import PyAutoGuiKeyboard

        keyboard_controller = PyAutoGuiKeyboard()

        self._container.register_singleton(
            PyAutoGuiKeyboard,
            lambda: keyboard_controller,
        )

        self._container.register_singleton(
            KeyboardService,
            lambda: KeyboardService(
                container.resolve(PyAutoGuiKeyboard)
            ),
        )

        # ------------------------------------------------------
        # Clipboard
        # ------------------------------------------------------

        from ..desktop.clipboard.controller import ClipboardService
        from ..desktop.clipboard.pyautogui_backend import PyAutoGuiClipboard

        clipboard_controller = PyAutoGuiClipboard()

        self._container.register_singleton(
            PyAutoGuiClipboard,
            lambda: clipboard_controller,
        )

        self._container.register_singleton(
            ClipboardService,
            lambda: ClipboardService(
                container.resolve(PyAutoGuiClipboard)
            ),
        )

        # ------------------------------------------------------
        # Screen capture
        # ------------------------------------------------------

        from ..core.errors.vision_error import VisionError
        from ..desktop.screen.controller import ScreenService
        from ..desktop.screen.mss_backend import MSSScreen

        # MSS needs an attached display and raises on construction without one.
        # A headless machine must still be able to start AetherOS and run the
        # trading-analysis core, so capture is registered only when it works and
        # the capture-based tools fail individually if it does not.
        try:
            screen_controller = MSSScreen()

        except VisionError as exc:
            self._logger.bind(
                error=exc.message,
            ).warning(
                "Screen capture unavailable; screen and vision capture "
                "tools will not work."
            )

        else:
            self._container.register_singleton(
                MSSScreen,
                lambda: screen_controller,
            )

            self._container.register_singleton(
                ScreenService,
                lambda: ScreenService(
                    container.resolve(MSSScreen)
                ),
            )

        # ------------------------------------------------------
        # Windows
        # ------------------------------------------------------

        from ..desktop.window.controller import WindowService
        from ..desktop.window.win32_backend import Win32Window

        # Construction never touches the API, so this is safe off Windows: the
        # backend raises per call when pywin32 is missing, which keeps the failure
        # attached to the tool that needed it rather than to startup.
        window_controller = Win32Window()

        self._container.register_singleton(
            Win32Window,
            lambda: window_controller,
        )

        self._container.register_singleton(
            WindowService,
            lambda: WindowService(
                container.resolve(Win32Window)
            ),
        )

        # ------------------------------------------------------
        # Processes and commands
        # ------------------------------------------------------

        from ..desktop.process.controller import ProcessService
        from ..desktop.process.psutil_backend import PsutilProcess
        from ..desktop.process.terminal import TerminalService

        process_controller = PsutilProcess()

        self._container.register_singleton(
            PsutilProcess,
            lambda: process_controller,
        )

        self._container.register_singleton(
            ProcessService,
            lambda: ProcessService(
                container.resolve(PsutilProcess)
            ),
        )

        # No backend: command execution goes straight to asyncio subprocesses,
        # because a command can run for a minute and wrapping a blocking call
        # would stall the event loop for all of it.
        self._container.register_singleton(
            TerminalService,
            lambda: TerminalService(),
        )

        # ------------------------------------------------------
        # Applications
        # ------------------------------------------------------

        from ..desktop.application.controller import ApplicationService

        # Composed from the two services above rather than from a backend of its
        # own: an application is processes plus windows, and it needs both to
        # answer "did it actually open".
        self._container.register_singleton(
            ApplicationService,
            lambda: ApplicationService(
                container.resolve(ProcessService),
                container.resolve(WindowService),
            ),
        )

        self._logger.info(
            "Desktop services initialized."
        )

    async def _bootstrap_vision(self) -> None:
        self._logger.debug(
            "Initializing vision services..."
        )

        from ..config.config_loader import get_settings
        from ..vision.controller import VisionService
        from ..vision.providers.opencv_provider import OpenCVProvider
        from ..vision.providers.paddleocr_provider import PaddleOCRProvider
        from ..vision.providers.template_provider import (
            OpenCVTemplateProvider,
        )

        # ---------------------------------------------------------
        # OpenCV provider
        # ---------------------------------------------------------

        opencv = OpenCVProvider()

        self._container.register_singleton(
            OpenCVProvider,
            lambda: opencv,
        )

        # ---------------------------------------------------------
        # Template matching
        # ---------------------------------------------------------

        template = OpenCVTemplateProvider()

        self._container.register_singleton(
            OpenCVTemplateProvider,
            lambda: template,
        )

        # ---------------------------------------------------------
        # PaddleOCR provider
        # ---------------------------------------------------------

        # Constructing this is cheap: the provider defers importing paddle and
        # building its models until the first read_text() call, so startup
        # neither blocks on a model download nor fails on a machine without
        # PaddleOCR installed.
        _settings = get_settings()
        ocr = PaddleOCRProvider(
            language=_settings.OCR_LANGUAGE,
            processing_width=_settings.VISION_WIDTH,
        )

        self._container.register_singleton(
            PaddleOCRProvider,
            lambda: ocr,
        )

        if not ocr.available:
            self._logger.warning(
                "PaddleOCR is not installed; text recognition is unavailable."
            )

        # ---------------------------------------------------------
        # Object detection (optional)
        # ---------------------------------------------------------

        detector = self._build_detector()

        # ---------------------------------------------------------
        # Vision service
        # ---------------------------------------------------------

        self._container.register_singleton(
            VisionService,
            lambda: VisionService(
                ocr=self._container.resolve(PaddleOCRProvider),
                cv=self._container.resolve(OpenCVProvider),
                detector=detector,
                template=self._container.resolve(OpenCVTemplateProvider),
            ),
        )

        self._logger.bind(
            ocr=ocr.available,
            detection=detector is not None,
        ).info("Vision services initialized.")

    def _build_detector(self):
        """
        Build the YOLO detector when its package and weights are both present.

        Returns None otherwise. Registering it unconditionally would make
        ultralytics a hard dependency and let it download weights during
        startup — a network call in what must be an offline-safe path.

        Device, inference size and confidence come from the single Settings
        object (§5/§13), never from scattered os.getenv. The weights path may be
        overridden by AETHEROS_YOLO_WEIGHTS for backward compatibility; when it
        is unset the configured VISION_MODEL is used.
        """

        from ..config.config_loader import get_settings
        from ..vision.providers.yolo_provider import YOLOProvider

        settings = get_settings()

        weights = os.environ.get("AETHEROS_YOLO_WEIGHTS") or settings.VISION_MODEL

        detector = YOLOProvider(
            model=weights,
            device=settings.VISION_DETECTION_DEVICE,
            imgsz=settings.VISION_DETECTION_IMGSZ,
            confidence=settings.VISION_DETECTION_CONFIDENCE,
        )

        if not detector.available:
            self._logger.bind(
                weights=weights,
            ).warning(
                "YOLO weights or ultralytics unavailable; "
                "object detection disabled."
            )
            return None

        self._container.register_singleton(
            YOLOProvider,
            lambda: detector,
        )

        return detector

    async def _bootstrap_tools(self) -> None:
        self._logger.info(
            "Initializing tool system..."
        )

        # Relative imports keep every tool in the same package tree as this
        # module. An absolute `import src.aetheros...` would build a second copy
        # of the package whenever the app is loaded as `aetheros.*`, giving the
        # tools their own tool_registry and container that nothing else can see.
        from ..desktop.mouse import tools as mouse_tools  # noqa: F401
        from ..desktop.keyboard import tools as keyboard_tools  # noqa: F401
        from ..desktop.clipboard import tools as clipboard_tools  # noqa: F401
        from ..desktop.screen import tools as screen_tools  # noqa: F401
        from ..desktop.window import tools as window_tools  # noqa: F401
        from ..desktop.process import tools as process_tools  # noqa: F401
        from ..desktop.application import tools as application_tools  # noqa: F401
        from ..vision import tools as vision_tools  # noqa: F401
        from ..vision.grounding import tools as grounding_tools  # noqa: F401

        # verify_action and the workflow tools. Registered after the action tools
        # on purpose: the automation tools build their descriptions from the live
        # verification and recovery tables, and list_recovery_strategies reports
        # which strategies are usable by checking whether their tools exist. Doing
        # this before mouse/keyboard registration would report every strategy
        # unavailable and quietly mislead the model.
        from ..desktop.verification import tools as verification_tools  # noqa: F401
        from ..desktop.automation import tools as automation_tools  # noqa: F401

        # Importing this costs nothing when Playwright is absent: the tools
        # reference BrowserService only through the container, and
        # browser/controller.py imports the provider *interface*, not Playwright.
        # Registering them unconditionally is what lets an agent be told the
        # capability exists and get BROWSER_UNAVAILABLE rather than silence.
        from ..browser import tools as browser_tools  # noqa: F401

        # Trading Intelligence tools. Registered only when the subsystem is
        # enabled; importing the module is what registers the @tool functions,
        # and they resolve their services from the container at call time (the
        # services were registered by _bootstrap_trading, which runs first).
        if self._trading_enabled():
            from ..trading import tools as trading_tools  # noqa: F401

        # Memory tools. Registered only when the subsystem is enabled; importing
        # the module is what registers the @tool functions. They resolve the
        # MemoryManager from the container at *call* time, so it is fine that
        # _bootstrap_memory runs just after this -- no tool fires during startup.
        from ..config.config_loader import get_settings

        if get_settings().ENABLE_MEMORY:
            from ..memory import tools as memory_tools  # noqa: F401

        self._logger.bind(
            tool_count=tool_registry.count,
            categories=tool_registry.categories(),
        ).info("Tool system initialized.")

    async def _bootstrap_browser(self) -> None:
        self._logger.debug(
            "Initializing browser services..."
        )

        from ..browser.controller import BrowserService

        # Playwright is an optional dependency (`pip install aetheros[browser]`),
        # and importing the provider module is what pulls it in. A machine
        # without it must still start: the browser tools then fail individually
        # with BROWSER_UNAVAILABLE, which is a diagnosable answer, where an
        # unguarded import would take the whole application down at startup.
        if not self._browser_available():
            self._logger.warning(
                "Playwright is not installed; browser automation is "
                "unavailable. Install with: pip install aetheros[browser]"
            )
            return

        from ..browser.providers.playwright_provider import PlaywrightProvider

        # Lazy, like vision: constructing a provider is cheap, but launching a
        # browser is not, and startup must not spawn a Chromium process for a
        # session that may never navigate anywhere.
        self._container.register_singleton(
            PlaywrightProvider,
            lambda: PlaywrightProvider(),
        )

        self._container.register_singleton(
            BrowserService,
            lambda: BrowserService(
                self._container.resolve(PlaywrightProvider)
            ),
        )

        self._logger.info(
            "Browser services initialized."
        )

    def _trading_enabled(self) -> bool:
        from ..config.config_loader import get_settings

        return bool(get_settings().ENABLE_TRADING)

    async def _bootstrap_trading(self) -> None:
        """
        Register the deterministic Trading Intelligence core.

        Self-contained: it depends on numpy and the config only -- never on
        Vision, Desktop, the browser or an LLM. With no provider credentials
        configured it uses the clearly-labelled MOCK provider, whose
        SourceTier.MOCK propagates into every result so synthetic numbers can
        never be mistaken for real market data (spec sections 9, 53, 61).
        """
        self._logger.debug("Initializing trading intelligence...")

        from ..config.config_loader import get_settings

        settings = get_settings()
        if not settings.ENABLE_TRADING:
            self._logger.info(
                "Trading intelligence disabled (ENABLE_TRADING=false)."
            )
            return

        from ..runtime.events.event_bus import EventBus
        from ..trading.providers.base import MarketDataProvider
        from ..trading.providers.calendar_base import CalendarProvider
        from ..trading.providers.fundamentals_base import FundamentalsProvider
        from ..trading.providers.mock_calendar_provider import MockCalendarProvider
        from ..trading.providers.mock_fundamentals_provider import (
            MockFundamentalsProvider,
        )
        from ..trading.providers.mock_news_provider import MockNewsProvider
        from ..trading.providers.mock_provider import MockMarketDataProvider
        from ..trading.providers.news_base import NewsProvider
        from ..trading.services.analysis_service import AnalysisService
        from ..trading.services.backtest_service import BacktestService
        from ..trading.services.breakout_service import BreakoutService
        from ..trading.services.calendar_service import EventCalendarService
        from ..trading.services.divergence_service import DivergenceService
        from ..trading.services.critic_service import CriticService
        from ..trading.services.evidence_service import EvidenceService
        from ..trading.services.explanation_service import ExplanationService
        from ..trading.services.fundamental_service import (
            FundamentalAnalysisService,
        )
        from ..trading.services.market_data_service import MarketDataService
        from ..trading.services.market_structure_service import (
            MarketStructureService,
        )
        from ..trading.services.news_service import NewsSentimentService
        from ..trading.services.orchestration_service import OrchestrationService
        from ..trading.services.portfolio_service import PortfolioRiskService
        from ..trading.services.prediction_evaluator import PredictionEvaluator
        from ..trading.services.performance_service import (
            PredictionPerformanceService,
        )
        from ..trading.services.prediction_store import (
            FilePredictionStore,
            InMemoryPredictionStore,
            PredictionStore,
        )
        from ..trading.services.anomaly_service import AnomalyService
        from ..trading.services.historical_analogue_service import (
            HistoricalAnalogueService,
        )
        from ..trading.services.macro_service import MacroContextService
        from ..trading.services.multi_timeframe_service import MultiTimeframeService
        from ..trading.services.probability_service import ProbabilityService
        from ..trading.services.calibration_history_service import (
            CalibrationHistoryService,
        )
        from ..trading.services.ceo_service import TradingCEOService
        from ..trading.services.ceo_agent_service import CEOAgentService
        from ..core.interfaces.llm_provider import LLMProvider
        from ..trading.services.monitoring_service import MonitoringService
        from ..trading.services.monitoring_scheduler import MonitoringScheduler
        from ..trading.services.outcome_store import (
            FileOutcomeStore,
            InMemoryOutcomeStore,
            OutcomeStore,
        )
        from ..trading.services.scan_service import WatchlistScanService
        from ..trading.services.regime_service import RegimeService
        from ..trading.services.relative_strength_service import (
            RelativeStrengthService,
        )
        from ..trading.services.risk_service import RiskService
        from ..trading.services.track_record_service import (
            PredictionTrackRecordService,
        )
        from ..trading.services.technical_analysis_service import (
            TechnicalAnalysisService,
        )

        # ------------------------------------------------------
        # Provider
        # ------------------------------------------------------

        provider_name = settings.MARKET_DATA_PROVIDER.strip().lower()
        if provider_name == "mock":
            provider: MarketDataProvider = MockMarketDataProvider()
        elif provider_name in ("yahoo", "yfinance"):
            from ..trading.providers.yahoo_provider import YahooMarketDataProvider

            provider = YahooMarketDataProvider(timeout=settings.TRADING_HTTP_TIMEOUT)
            self._logger.info(
                "Using the Yahoo market-data provider (SourceTier.SECONDARY -- "
                "real, aggregated, possibly-delayed data)."
            )
        else:
            # Only mock + yahoo ship today. Rather than fail startup, fall back
            # loudly so the system still runs, and never pretends an unavailable
            # real feed is present.
            self._logger.warning(
                "Market-data provider '%s' is not available; falling back to "
                "the MOCK provider. Results will be synthetic.",
                provider_name,
            )
            provider = MockMarketDataProvider()

        self._container.register_singleton(
            MarketDataProvider,
            lambda: provider,
        )

        # ------------------------------------------------------
        # News provider (deterministic-first; standalone from the
        # market-data pipeline this increment)
        # ------------------------------------------------------

        news_provider_name = settings.NEWS_PROVIDER.strip().lower()
        if news_provider_name == "mock":
            news_provider: NewsProvider = MockNewsProvider()
        elif news_provider_name in ("yahoo", "yfinance"):
            from ..trading.providers.yahoo_news_provider import YahooNewsProvider

            news_provider = YahooNewsProvider(timeout=settings.TRADING_HTTP_TIMEOUT)
            self._logger.info(
                "Using the Yahoo news provider (SourceTier.SECONDARY -- real "
                "recent headlines from Yahoo search; sentiment is a derived read)."
            )
        else:
            # Fall back loudly rather than pretend an unavailable real news feed
            # is present.
            self._logger.warning(
                "News provider '%s' is not available; falling back to the MOCK "
                "news provider. Sentiment will be synthetic.",
                news_provider_name,
            )
            news_provider = MockNewsProvider()

        self._container.register_singleton(
            NewsProvider,
            lambda: news_provider,
        )

        # ------------------------------------------------------
        # Calendar provider (deterministic-first; standalone from the
        # market-data + orchestration pipeline this increment)
        # ------------------------------------------------------

        calendar_provider_name = settings.CALENDAR_PROVIDER.strip().lower()
        if calendar_provider_name == "mock":
            calendar_provider: CalendarProvider = MockCalendarProvider()
        elif calendar_provider_name in ("yahoo", "yfinance"):
            from ..trading.providers.yahoo_calendar_provider import (
                YahooCalendarProvider,
            )

            calendar_provider = YahooCalendarProvider(
                timeout=settings.TRADING_HTTP_TIMEOUT
            )
            self._logger.info(
                "Using the Yahoo calendar provider (SourceTier.SECONDARY -- real "
                "scheduled earnings/dividend dates from Yahoo quoteSummary)."
            )
        else:
            # Fall back loudly rather than pretend an unavailable real economic
            # calendar is present.
            self._logger.warning(
                "Calendar provider '%s' is not available; falling back to the "
                "MOCK calendar provider. Events will be synthetic.",
                calendar_provider_name,
            )
            calendar_provider = MockCalendarProvider()

        self._container.register_singleton(
            CalendarProvider,
            lambda: calendar_provider,
        )

        # ------------------------------------------------------
        # Fundamentals provider (deterministic-first; standalone from the
        # market-data + orchestration pipeline this increment)
        # ------------------------------------------------------

        fundamentals_provider_name = settings.FUNDAMENTALS_PROVIDER.strip().lower()
        if fundamentals_provider_name == "mock":
            fundamentals_provider: FundamentalsProvider = MockFundamentalsProvider()
        elif fundamentals_provider_name in ("yahoo", "yfinance"):
            from ..trading.providers.yahoo_fundamentals_provider import (
                YahooFundamentalsProvider,
            )

            fundamentals_provider = YahooFundamentalsProvider(
                timeout=settings.TRADING_HTTP_TIMEOUT
            )
            self._logger.info(
                "Using the Yahoo fundamentals provider (SourceTier.SECONDARY -- "
                "real, aggregated, possibly-delayed financials)."
            )
        else:
            # Only mock + yahoo ship today. Fall back loudly rather than
            # pretend an unavailable real financials feed is present.
            self._logger.warning(
                "Fundamentals provider '%s' is not available; falling back to "
                "the MOCK fundamentals provider. Financials will be synthetic.",
                fundamentals_provider_name,
            )
            fundamentals_provider = MockFundamentalsProvider()

        self._container.register_singleton(
            FundamentalsProvider,
            lambda: fundamentals_provider,
        )

        # ------------------------------------------------------
        # Services (all resolve the shared EventBus for their events)
        # ------------------------------------------------------

        self._container.register_singleton(
            MarketDataService,
            lambda: MarketDataService(
                self._container.resolve(MarketDataProvider),
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        self._container.register_singleton(
            TechnicalAnalysisService,
            lambda: TechnicalAnalysisService(),
        )

        self._container.register_singleton(
            MarketStructureService,
            lambda: MarketStructureService(),
        )

        self._container.register_singleton(
            EvidenceService,
            lambda: EvidenceService(),
        )

        self._container.register_singleton(
            AnalysisService,
            lambda: AnalysisService(
                self._container.resolve(MarketDataService),
                self._container.resolve(TechnicalAnalysisService),
                self._container.resolve(MarketStructureService),
                self._container.resolve(EvidenceService),
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        self._container.register_singleton(
            RiskService,
            lambda: RiskService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        self._container.register_singleton(
            BacktestService,
            lambda: BacktestService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        self._container.register_singleton(
            CriticService,
            lambda: CriticService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic, calibrated probability estimator (spec sections 6, 7).
        # It is look-ahead-safe and gates its own reliability; the orchestrator
        # resolves it below and surfaces a probability only when it passes.
        self._container.register_singleton(
            ProbabilityService,
            lambda: ProbabilityService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic news-sentiment analysis (spec sections 5, 9, 26 item #9).
        # It depends on the NewsProvider ABC through the container and is fused
        # into the orchestrator's report below as soft, advisory context -- it
        # never lifts a recommendation above the critic's verdict.
        self._container.register_singleton(
            NewsSentimentService,
            lambda: NewsSentimentService(
                self._container.resolve(NewsProvider),
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic event/economic-calendar lookup (spec sections 5, 9, 26).
        # Registered before the orchestrator so it can be resolved as a
        # dependency below; it depends on the CalendarProvider ABC through the
        # container and emits MarketEventsDetected. It is fused into the
        # orchestrator and the critic's event_risk check (a reliable high-impact
        # event lets the critic veto), while a MOCK calendar only WARNs.
        self._container.register_singleton(
            EventCalendarService,
            lambda: EventCalendarService(
                self._container.resolve(CalendarProvider),
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic fundamental analysis (spec sections 5, 9, 26 item #9).
        # It depends on the FundamentalsProvider ABC through the container and
        # emits FundamentalsAnalyzed. Registered before the orchestrator so it can
        # be resolved as a dependency below and fused into the report + the
        # critic's advisory `fundamentals` check as soft, longer-horizon context
        # (it never lifts a recommendation above the critic's verdict).
        self._container.register_singleton(
            FundamentalAnalysisService,
            lambda: FundamentalAnalysisService(
                self._container.resolve(FundamentalsProvider),
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic market-regime detection (spec sections 5, 8, 26 item #2).
        # It reads trending/ranging/volatile from ADX + ATR over the candle
        # series (no LLM, no extra I/O) and emits MarketRegimeDetected. Registered
        # before the orchestrator so it can be resolved as a dependency below and
        # fused into the report + the critic's advisory `market_regime` check as
        # situational context -- it is never a price prediction and never lifts a
        # recommendation above the critic's verdict.
        self._container.register_singleton(
            RegimeService,
            lambda: RegimeService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic relative-strength / sector-strength read (spec sections
        # 2, 5, 27). It compares an instrument's return to a benchmark's over a
        # lookback window and produces a MARKET_CONTEXT evidence item -- the
        # "positive sector strength" line the example reports cite. It holds no
        # I/O of its own (the caller fetches both candle series and hands them
        # in). It backs both the analyze_relative_strength tool and, since it was
        # fused into the orchestrator, the report's relative-strength section +
        # the critic's advisory `relative_strength` check.
        self._container.register_singleton(
            RelativeStrengthService,
            lambda: RelativeStrengthService(get_settings()),
        )

        # Deterministic statistical-anomaly read (spec sections 5, 9, 27). It
        # z-scores the last bar's return, volume and overnight gap against a
        # trailing baseline and, on a genuine outlier, emits an ANOMALY evidence
        # item with a directional lean. It holds no I/O of its own (the caller
        # hands in the candles). It backs both the detect_anomalies tool and,
        # since it was fused into the orchestrator, the report's anomaly section +
        # the critic's advisory `anomaly` check.
        self._container.register_singleton(
            AnomalyService,
            lambda: AnomalyService(get_settings()),
        )

        # Deterministic historical-analogue read (spec sections 1, 7, 15, 27). It
        # reuses the look-ahead-safe causal feature matrix from the quant layer to
        # find the K past bars most like the latest one and reports how those
        # analogues resolved over a forward horizon (up-rate + mean forward
        # return), emitting a HISTORICAL evidence item. It holds no I/O of its own
        # (the caller hands in the candles). It backs both the
        # find_historical_analogues tool and, since it was fused into the
        # orchestrator, the report's historical_analogue section + the critic's
        # advisory `historical_analogue` check.
        self._container.register_singleton(
            HistoricalAnalogueService,
            lambda: HistoricalAnalogueService(get_settings()),
        )

        # Deterministic broad-market macro-context read (spec sections 2, 5, 27).
        # It composes RegimeService on a market benchmark's candles and maps the
        # benchmark regime to a RISK_ON / RISK_OFF / NEUTRAL posture, emitting a
        # MACRO evidence item -- the context a single-name signal sits inside. It
        # reuses the regime maths rather than duplicating it and holds no I/O of
        # its own (the caller fetches the benchmark candles and hands them in). It
        # backs both the analyze_macro_context tool and, since it was fused into
        # the orchestrator, the report's macro section + the critic's advisory
        # `macro_context` check.
        self._container.register_singleton(
            MacroContextService,
            lambda: MacroContextService(
                self._container.resolve(RegimeService),
                get_settings(),
            ),
        )

        # Deterministic watchlist scan/ranking (spec sections 1, 26). It composes
        # the analysis layer across several instruments and orders them so the
        # strongest actionable setups surface first -- the multi-instrument
        # counterpart to single-name analysis. It computes no signal of its own
        # (reuse, not duplication) and inherits the per-row honesty of the
        # analysis it ranks. Standalone: it is not part of the single-instrument
        # orchestrated report.
        self._container.register_singleton(
            WatchlistScanService,
            lambda: WatchlistScanService(
                self._container.resolve(AnalysisService),
                get_settings(),
            ),
        )

        # Deterministic multi-timeframe confirmation (spec section 5). Pure over
        # two TradingAnalysis objects (the tool runs both analyses and hands them
        # in), it classifies whether the higher-timeframe trend confirms/conflicts
        # with the base read. It computes no signal of its own (reuse of the
        # analysis layer). It backs both the analyze_multi_timeframe tool and,
        # since it was fused into the orchestrator, the report's multi_timeframe
        # section + the critic's advisory `multi_timeframe` check.
        self._container.register_singleton(
            MultiTimeframeService,
            lambda: MultiTimeframeService(get_settings()),
        )

        # Deterministic momentum-divergence detection (spec section 5). It reuses
        # the RSI from indicators/core to find regular price-vs-oscillator
        # divergence (lower price low / higher RSI low = bullish, and the mirror
        # for bearish). It holds no I/O of its own (the caller hands in the
        # candles). It backs both the detect_divergence tool and, since it was
        # fused into the orchestrator, the report's divergence section + the
        # critic's advisory `divergence` check.
        self._container.register_singleton(
            DivergenceService,
            lambda: DivergenceService(get_settings()),
        )

        # Deterministic channel-breakout detection (spec section 5, price action).
        # It flags the latest close pushing beyond the prior-N-bar channel
        # (highest high / lowest low) with above-average-volume confirmation,
        # emitting a MARKET_STRUCTURE evidence item. It holds no I/O of its own
        # (the caller hands in the candles). It backs both the detect_breakout
        # tool and, since it was fused into the orchestrator, the report's
        # breakout section + the critic's advisory `breakout` check.
        self._container.register_singleton(
            BreakoutService,
            lambda: BreakoutService(get_settings()),
        )

        # Deterministic portfolio-risk allocation (spec section 5 -- Risk Agent
        # position sizing / exposure / drawdown risk at the basket level). Pure
        # over a list of candidate trade geometries + account equity: it budgets a
        # total risk across the book and caps gross exposure, scaling down to fit.
        # It computes no signal (reuse of the per-trade RiskService upstream) and
        # is standalone -- not part of the single-instrument orchestrated report.
        self._container.register_singleton(
            PortfolioRiskService,
            lambda: PortfolioRiskService(get_settings()),
        )

        # Deterministic prediction-outcome resolution (spec sections 6, 16, 29).
        # The scoring half of the autonomous loop's "Observe Result -> Evaluate"
        # step: given a stored PredictionRecord and the candles that unfolded
        # after it, it grades the call (RESOLVED / PENDING / UNRESOLVABLE) and
        # emits PredictionResolved only for a genuinely resolved outcome. It is
        # stateless -- no persistence, no loop -- and holds no forecasting logic;
        # it reads the realised move off the candles and computes nothing more.
        self._container.register_singleton(
            PredictionEvaluator,
            lambda: PredictionEvaluator(
                get_settings(),
                market_data=self._container.resolve(MarketDataService),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic prediction-performance aggregation (spec sections 6, 9,
        # 29). Given a batch of already-resolved outcomes it reports directional
        # accuracy, coverage and -- reusing the shared quant calibration code --
        # Brier/ECE, gating reliability on TRADING_PERF_MIN_SAMPLE and on the
        # sample being free of MOCK data. Like the evaluator it is stateless: it
        # aggregates outcomes the caller holds and neither fetches nor stores.
        # The durable prediction store and the live loop that would feed it over
        # time remain deferred (spec sections 15, 16, 29).
        self._container.register_singleton(
            PredictionPerformanceService,
            lambda: PredictionPerformanceService(
                get_settings(),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Audit trail of every produced prediction (spec sections 8, 19, 28). The
        # orchestrator captures each report's section-8 contract into this store
        # and announces it with PredictionCreated. Two backends sit behind the one
        # PredictionStore port, selected by PREDICTION_STORE_BACKEND: the default
        # in-process InMemoryPredictionStore (a within-session trail), or a durable
        # FilePredictionStore that persists every prediction to a JSON Lines file
        # so the history survives restarts. Because both honour the same interface,
        # the orchestrator is untouched by the choice (spec sections 15, 23). The
        # richer learning/calibration-from-history Memory layer remains deferred.
        def _build_prediction_store() -> PredictionStore:
            from pathlib import Path

            settings = get_settings()
            backend = settings.PREDICTION_STORE_BACKEND.strip().lower()
            if backend in ("file", "jsonl", "durable"):
                raw = Path(settings.TRADING_PREDICTION_STORE_PATH)
                path = raw if raw.is_absolute() else settings.DATA_DIR / raw
                self._logger.info(
                    "Prediction store: durable file backend at %s", path
                )
                return FilePredictionStore(path)
            self._logger.info("Prediction store: in-memory backend (non-durable)")
            return InMemoryPredictionStore()

        self._container.register_singleton(
            PredictionStore,
            _build_prediction_store,
        )

        # The orchestrator composes the whole deterministic desk pipeline
        # (analysis -> risk -> optional backtest -> news -> calendar ->
        # fundamentals -> regime -> relative strength -> anomaly -> historical
        # analogue -> macro -> multi-timeframe -> divergence -> breakout ->
        # critic -> report). It holds no analytical logic of its own -- it depends
        # on the services above through the container, exactly as spec section 5
        # requires.
        self._container.register_singleton(
            OrchestrationService,
            lambda: OrchestrationService(
                self._container.resolve(MarketDataService),
                self._container.resolve(AnalysisService),
                self._container.resolve(RiskService),
                self._container.resolve(BacktestService),
                self._container.resolve(CriticService),
                get_settings(),
                probability=self._container.resolve(ProbabilityService),
                news=self._container.resolve(NewsSentimentService),
                calendar=self._container.resolve(EventCalendarService),
                fundamentals=self._container.resolve(FundamentalAnalysisService),
                regime=self._container.resolve(RegimeService),
                relative_strength=self._container.resolve(RelativeStrengthService),
                anomaly=self._container.resolve(AnomalyService),
                historical_analogue=self._container.resolve(HistoricalAnalogueService),
                macro=self._container.resolve(MacroContextService),
                multi_timeframe=self._container.resolve(MultiTimeframeService),
                divergence=self._container.resolve(DivergenceService),
                breakout=self._container.resolve(BreakoutService),
                prediction_store=self._container.resolve(PredictionStore),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # Deterministic, read-only signal explanation (spec section 1 -- "explain
        # why a signal was generated"). Pure synthesis over a finished report: it
        # consolidates every evidence item the report gathered into one ledger,
        # grouped into reasons supporting vs opposing the fused call. It computes
        # no new signal; the tool runs the orchestrator, then this service
        # explains the report it produced.
        self._container.register_singleton(
            ExplanationService,
            lambda: ExplanationService(get_settings()),
        )

        # The Trading CEO narration layer (spec sections 4, 5, 10): it runs the
        # deterministic report and has an LLMProvider narrate it. The LLM only
        # explains -- the deterministic core decides -- and it is optional: when no
        # provider is wired the brief falls back to a deterministic summary, so the
        # core still works without an LLM (sections 1, 10). The provider is passed
        # only if one is registered, keeping the trading core decoupled from any
        # concrete provider.
        def _build_ceo() -> TradingCEOService:
            llm = (
                self._container.resolve(LLMProvider)
                if self._container.has(LLMProvider)
                else None
            )
            return TradingCEOService(
                self._container.resolve(OrchestrationService),
                get_settings(),
                llm=llm,
            )

        self._container.register_singleton(TradingCEOService, _build_ceo)

        # The agentic Trading CEO (spec sections 4, 5, 29): a bounded, fenced
        # tool-calling loop where the LLM chooses and sequences the deterministic
        # trading tools itself. Only trading-category tools are exposed, the loop
        # is capped at MAX_TOOL_CALLS, every number still comes from a tool result,
        # and with no LLM it returns an honest "needs an LLM" result. It runs the
        # tools through a ToolExecutor over the shared registry.
        def _build_ceo_agent() -> CEOAgentService:
            from ..tools import tool_registry
            from ..tools.executor import ToolExecutor

            llm = (
                self._container.resolve(LLMProvider)
                if self._container.has(LLMProvider)
                else None
            )
            return CEOAgentService(
                ToolExecutor(tool_registry),
                get_settings(),
                llm=llm,
            )

        self._container.register_singleton(CEOAgentService, _build_ceo_agent)

        # On-demand track-record query (spec sections 6, 16, 28, 29). Composes the
        # audit store, the per-prediction evaluator and the performance aggregator
        # into one read-only question: "of the predictions we recorded, how have
        # they actually done?" It stores nothing and learns nothing -- every call
        # recomputes outcomes fresh. This is the synchronous query, NOT the
        # autonomous scheduled monitoring loop (which, with the durable outcome
        # store it needs, remains deferred to the Memory layer, spec sections 15,
        # 29).
        self._container.register_singleton(
            PredictionTrackRecordService,
            lambda: PredictionTrackRecordService(
                self._container.resolve(PredictionStore),
                self._container.resolve(PredictionEvaluator),
                self._container.resolve(PredictionPerformanceService),
            ),
        )

        # Durable accumulation of resolved outcomes (spec sections 15, 29). Two
        # backends behind the one OutcomeStore port, selected by
        # OUTCOME_STORE_BACKEND: the default in-process store, or a JSON Lines
        # file so a monitoring sweep's outcomes survive restarts and accumulate.
        # It is the storage foundation of the learning layer; it does not itself
        # learn or recalibrate (that stays deferred).
        def _build_outcome_store() -> OutcomeStore:
            from pathlib import Path

            settings = get_settings()
            backend = settings.OUTCOME_STORE_BACKEND.strip().lower()
            if backend in ("file", "jsonl", "durable"):
                raw = Path(settings.TRADING_OUTCOME_STORE_PATH)
                path = raw if raw.is_absolute() else settings.DATA_DIR / raw
                self._logger.info("Outcome store: durable file backend at %s", path)
                return FileOutcomeStore(path)
            self._logger.info("Outcome store: in-memory backend (non-durable)")
            return InMemoryOutcomeStore()

        self._container.register_singleton(OutcomeStore, _build_outcome_store)

        # The honest first rung of "learn from history" (spec sections 6, 29): it
        # reads the accumulated resolved outcomes and measures how well the live
        # model's past calibrated probabilities matched reality, proposing (only
        # on a large enough, non-mock sample) a recalibration correction. It is
        # pure measurement -- it never modifies the live probability pipeline;
        # applying any proposed correction is a separate, explicitly-gated step.
        self._container.register_singleton(
            CalibrationHistoryService,
            lambda: CalibrationHistoryService(
                get_settings(),
                outcome_store=self._container.resolve(OutcomeStore),
            ),
        )

        # One bounded "Observe Result -> Evaluate" monitoring sweep (spec sections
        # 16, 29). It composes the track-record resolver and the performance
        # aggregator into a single repeatable pass that resolves outstanding
        # predictions, summarises them, persists each outcome to the OutcomeStore
        # (so sweeps accumulate), and announces a MonitoringSweepCompleted event.
        # It is NOT a running background loop -- the continuously-scheduled runner
        # remains deferred to the Memory/state layer.
        self._container.register_singleton(
            MonitoringService,
            lambda: MonitoringService(
                self._container.resolve(PredictionTrackRecordService),
                self._container.resolve(PredictionPerformanceService),
                outcome_store=self._container.resolve(OutcomeStore),
                event_bus=self._container.resolve(EventBus),
            ),
        )

        # The bounded, opt-in autonomous monitoring loop (spec section 29). It is
        # registered but NOT started here: it only runs when TRADING_MONITOR_ENABLED
        # is set, and starting/stopping it is an explicit lifecycle call -- so the
        # default build (and the tests) never spin up a background task.
        self._container.register_singleton(
            MonitoringScheduler,
            lambda: MonitoringScheduler(
                self._container.resolve(MonitoringService),
                get_settings(),
            ),
        )

        self._logger.bind(
            provider=provider.name,
            source_tier=provider.tier.value,
        ).info("Trading intelligence initialized.")



    def _bootstrap_agents(self) -> None:
        self._logger.debug(
            "Initializing agent system..."
        )

        # ╔══════════════════════════════════════════╗
        # ║              Task Agent                  ║
        # ╚══════════════════════════════════════════╝

        from ..agents.tasks.manager import TaskManager
        from ..agents.agent import Agent
        from ..agents.context import ContextBuilder
        from ..agents.execution import ToolExecutionCoordinator
        from ..agents.planner import AgentPlanner, PlannerConfig
        from ..config.config_loader import get_settings

        max_tool_calls = get_settings().MAX_TOOL_CALLS

        task_manager = TaskManager(
            event_bus=self._event_bus,
        )
        self._container.register_singleton(
            TaskManager,
            lambda: task_manager,
        )

        def build_agent() -> Agent:
            provider = self._container.resolve("llm_provider")
            return Agent(
                task_manager=task_manager,
                planner=AgentPlanner(
                    provider,
                    registry=tool_registry,
                    config=PlannerConfig(max_tool_calls=max_tool_calls),
                ),
                context_builder=ContextBuilder(registry=tool_registry),
                llm_loop=self._container.resolve("llm_tool_loop"),
                execution_coordinator=self._container.resolve(
                    ToolExecutionCoordinator
                ),
            )

        self._container.register_singleton(Agent, build_agent)



        self._logger.info(
            "Agent system initialized."
        )



    @staticmethod
    def _browser_available() -> bool:
        """
        Whether Playwright can be imported.

        find_spec rather than a try/import: importing playwright costs a
        noticeable fraction of a second, and startup should not pay it on a
        machine that will never open a browser.
        """

        return importlib.util.find_spec("playwright") is not None

    async def _bootstrap_memory(self) -> None:
        self._logger.debug(
            "Initializing memory services..."
        )

        from ..config.config_loader import get_settings

        settings = get_settings()
        if not settings.ENABLE_MEMORY:
            self._logger.info(
                "Memory disabled (ENABLE_MEMORY=false); memory services and "
                "tools will not be registered."
            )
            return

        from ..core.interfaces.memory_provider import MemoryProvider
        from ..memory.config import MemoryConfig
        from ..memory.services.manager import MemoryManager
        from ..memory.services.provider import SQLiteMemoryProvider
        from ..runtime.events.event_bus import EventBus

        config = MemoryConfig.from_settings(settings)

        # One manager, shared by both the rich API and the ABC port. It owns the
        # SQLite connection and brings the schema up to date on initialize().
        manager = MemoryManager(
            config,
            event_bus=self._container.resolve(EventBus),
        )
        await manager.initialize()

        self._container.register_singleton(MemoryManager, lambda: manager)
        self._container.register_singleton("memory_manager", lambda: manager)

        # Register the key/value ABC port over the *same* manager so
        # interface-typed consumers resolve a working provider (CLAUDE.md §10).
        provider = SQLiteMemoryProvider(config, manager=manager)
        self._container.register_singleton(MemoryProvider, lambda: provider)

        self._logger.bind(
            db=str(config.database_path),
        ).info("Memory services initialized.")

    def _build_agent_memory(self):
        """
        Resolve the agent-memory port for AgentCore (spec Phase 20K).

        Returns ``(AgentMemory, recall_max_chars)``. When memory is enabled and
        its manager was registered by _bootstrap_memory (which runs first), wire
        the real ManagerAgentMemory; otherwise return a NullAgentMemory so the
        agent loop runs identically with memory off. This is the one place the
        ENABLE_MEMORY decision reaches the agent.
        """
        from ..agents.memory_port import NullAgentMemory
        from ..config.config_loader import get_settings
        from ..memory.services.manager import MemoryManager

        settings = get_settings()
        if not settings.ENABLE_MEMORY or not self._container.has(MemoryManager):
            return NullAgentMemory(), settings.MEMORY_AGENT_RECALL_MAX_CHARS

        from ..memory.config import MemoryConfig
        from ..memory.integration import build_agent_memory

        config = MemoryConfig.from_settings(settings)
        manager = self._container.resolve(MemoryManager)
        self._logger.info("Agent memory integration enabled (recall + recording).")
        return build_agent_memory(manager, config), config.agent_recall_max_chars

    async def _bootstrap_llm(self) -> None:
        self._logger.info(
            "Initializing LLM providers..."
        )

        from ..llm.agent_loop import AgentLoopConfig, LLMToolLoop
        from ..llm.config import LLMConfig
        from ..llm.engine import LLMEngine
        from ..llm.manager import LLMProviderManager
        from ..llm.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )
        from ..llm.tool_schema import get_llm_tools
        from ..agents.core import AgentCore
        from ..agents.execution import ToolExecutionCoordinator
        from ..agents.planner import PlannerConfig
        from ..agents.policy import PolicyConfig, PolicyEngine
        from ..config.config_loader import get_settings
        from ..tools.executor import ToolExecutor

        # ----------------------------------------------------------
        # Configuration
        # ----------------------------------------------------------

        config = LLMConfig.from_env()

        # The one place the tool-call budget is read from configuration. It is
        # threaded into every consumer below (planner cap, agent-loop iteration
        # budget) so none of them hardcodes its own limit. Logged once here --
        # not per iteration -- so the active value is visible at startup.
        settings = get_settings()
        max_tool_calls = settings.MAX_TOOL_CALLS
        self._logger.info("Max tool calls: {}", max_tool_calls)

        # bind(), not %-style args: loguru formats with str.format, so
        # logger.debug("model: %s", x) silently drops x. The api_key is never
        # bound here, and LLMConfig sets repr=False on it so it cannot reach a
        # sink through a traceback either.
        self._logger.bind(
            model=config.model,
            base_url=config.base_url,
        ).debug("LLM configuration loaded.")

        # ----------------------------------------------------------
        # Provider
        # ----------------------------------------------------------

        provider = OpenAICompatibleProvider(
            config,
            provider_name="openai-compatible",
        )

        await provider.initialize()

        # ----------------------------------------------------------
        # Manager
        # ----------------------------------------------------------

        manager = LLMProviderManager()

        manager.register(
            provider
        )

        manager.set_active(
            provider.name
        )

        # ----------------------------------------------------------
        # Engine and tool loop
        # ----------------------------------------------------------

        # get_llm_tools is passed as a callable rather than a materialised list
        # so the schemas are built per run, from whatever is registered then.
        engine = LLMEngine(
            provider,
            tool_provider=lambda: get_llm_tools(tool_registry),
        )

        executor = ToolExecutor(tool_registry)
        coordinator = ToolExecutionCoordinator(
            executor,
            registry=tool_registry,
        )
        tool_loop = LLMToolLoop(
            engine,
            executor,
            coordinator=coordinator,
            config=AgentLoopConfig(max_iterations=max_tool_calls),
        )

        # The agent core drives `ask`: it owns orchestration and gates every
        # call through a PolicyEngine before the shared ToolExecutor runs it.
        # from_provider builds its own planner and a policy-gated coordinator
        # over the *same* registry and executor, so no LLM or tool-execution
        # logic is duplicated. A default (permissive) policy preserves today's
        # behaviour -- every enabled tool is allowed -- while establishing the
        # gate the safety layer needs.
        # Memory integration (spec Phase 20): resolve the agent-memory port once,
        # here, so the agent loop never branches on whether memory exists. When
        # memory is disabled this returns a NullAgentMemory, keeping the single
        # ENABLE_MEMORY decision in the bootstrapper rather than in the loop.
        agent_memory, recall_max_chars = self._build_agent_memory()

        agent_core = AgentCore.from_provider(
            provider,
            registry=tool_registry,
            executor=executor,
            policy=PolicyEngine(PolicyConfig()),
            planner_config=PlannerConfig(max_tool_calls=max_tool_calls),
            max_iterations=max_tool_calls,
            memory=agent_memory,
            recall_max_chars=recall_max_chars,
        )

        # ----------------------------------------------------------
        # Container
        # ----------------------------------------------------------

        self._container.register_singleton(
            LLMProviderManager,
            lambda: manager,
        )

        self._container.register_singleton(
            "llm_provider",
            lambda: provider,
        )

        # Also register the active provider under the LLMProvider interface, so
        # interface-typed consumers (the Trading CEO narration layer) resolve the
        # real provider without coupling to a concrete class. The CEO degrades to
        # a deterministic summary if this provider is unhealthy, so wiring it here
        # is safe even when no API key is configured.
        from ..core.interfaces.llm_provider import LLMProvider as _LLMProvider

        self._container.register_singleton(
            _LLMProvider,
            lambda: provider,
        )

        self._container.register_singleton(
            LLMEngine,
            lambda: engine,
        )

        self._container.register_singleton(
            "llm_tool_loop",
            lambda: tool_loop,
        )

        self._container.register_singleton(
            "agent_core",
            lambda: agent_core,
        )

        # The single entry both front ends submit a turn through. It tags the
        # run with its origin (terminal / voice) and calls the *same* agent, so
        # a request enters the agent exactly once and every trace event of the
        # run is source-labelled for both UIs to observe.
        from ..agents.gateway import InteractionGateway

        interaction_gateway = InteractionGateway(agent_core)

        self._container.register_singleton(
            "interaction_gateway",
            lambda: interaction_gateway,
        )

        self._container.register_singleton(
            ToolExecutor,
            lambda: executor,
        )

        self._container.register_singleton(
            ToolExecutionCoordinator,
            lambda: coordinator,
        )

        # ----------------------------------------------------------
        # Health
        # ----------------------------------------------------------

        healthy = await provider.health_check()

        bound = self._logger.bind(
            provider=provider.name,
            model=provider.model,
        )

        if healthy:
            bound.info("LLM provider is healthy.")
        else:
            # Not fatal: the CLI still starts, and the failure surfaces on the
            # first request rather than blocking startup entirely.
            bound.warning("LLM provider failed its health check.")

    async def _bootstrap_hud(self) -> None:
        self._logger.debug(
            "Initializing HUD..."
        )

        from ..hud.config import HUDConfig
        from ..hud.service import HUDService
        config = HUDConfig.from_env()

        # HUDService.start() does not consult config.enabled — the gate is
        # deliberately the caller's, so the service stays usable from a test or
        # a demo without an environment variable. This is that caller.
        if not config.enabled:
            self._logger.debug(
                "HUD is disabled; set AETHEROS_HUD_ENABLED=true to enable it."
            )
            return

        # Importing the package does not import Qt (see hud/__init__), so
        # construction here is cheap and safe on a headless machine. Qt only
        # loads inside the child process the service spawns.
        if not self._qt_available():
            # Checked here rather than left to the child, because the child's
            # stderr goes to DEVNULL: a missing PySide6 would otherwise surface
            # only as exit code 1 with no explanation, and HUDService.start()
            # would still have returned True.
            self._logger.warning(
                "PySide6 is not installed; the HUD overlay is unavailable. "
                "Install with: pip install aetheros[hud]"
            )
            return

        hud = HUDService(
            config=config,
            event_bus=self._event_bus,
        )

        self._container.register_singleton(
            HUDService,
            lambda: hud,
        )

        self._container.register_singleton(
            "hud_service",
            lambda: hud,
        )

        self._hud = hud

        started = await hud.start()

        if not started:
            # Not fatal. The overlay is a display, and losing it must not stop
            # a session that can still do everything through the CLI.
            self._logger.bind(
                error=hud.failure,
            ).warning(
                "The HUD did not start; continuing without the overlay."
            )
            return

        self._logger.bind(
            theme=config.theme,
            position=config.position,
            fps=config.fps,
        ).info("HUD initialized.")

    async def _bootstrap_voice(self) -> None:
        self._logger.debug(
            "Initializing voice services..."
        )

        from ..voice.config import VoiceConfig
        from ..voice.service import VoiceService

        config = VoiceConfig.from_env()

        if not config.enabled:
            self._logger.debug(
                "Voice is disabled; set AETHEROS_VOICE_ENABLED=true "
                "to enable it."
            )

            # The overlay leaves OFFLINE on VoiceServiceStarted, so with voice
            # off it would otherwise sit dark forever. Show the resting state
            # instead: the HUD is still useful as a status surface.
            self._show_hud_idle()

            return

        voice = VoiceService(
            config=config,
            event_bus=self._event_bus,
            container=self._container,
        )

        self._container.register_singleton(
            VoiceService,
            lambda: voice,
        )

        self._container.register_singleton(
            "voice_service",
            lambda: voice,
        )

        self._voice = voice

        try:
            # start() degrades on its own for a missing microphone or an
            # unavailable TTS backend; it raises only when no reasoner can be
            # resolved, which means the LLM layer did not come up.
            await voice.start()

        except Exception:
            self._logger.exception(
                "Voice services failed to start; continuing without voice."
            )

            self._voice = None
            self._container.remove(VoiceService)
            self._container.remove("voice_service")

            self._show_hud_idle()

            return

        status = voice.status()

        self._logger.bind(
            stt=status["stt"],
            tts=status["tts"],
            activator=status["activator"],
            hotkey=status["hotkey"],
            can_listen=status["can_listen"],
        ).info("Voice services initialized.")

        if not voice.can_listen:
            self._logger.bind(
                reason=status["blocked"],
            ).warning(
                "Voice cannot listen; spoken input is unavailable."
            )

    @staticmethod
    def _qt_available() -> bool:
        """
        Whether PySide6 can be imported.

        find_spec rather than a try/import, for the same reason as
        _browser_available: importing Qt in the parent process is expensive and
        pointless — only the child ever needs it.
        """

        return importlib.util.find_spec("PySide6") is not None

    def _show_hud_idle(self) -> None:
        """
        Park the overlay at IDLE when nothing will publish voice events.
        """

        hud = self._hud

        if hud is None or not hud.is_running:
            return

        from ..hud.state import HUDState

        hud.show(HUDState.IDLE)

    async def _bootstrap_lifecycle(self) -> None:
        self._logger.debug(
            "Initializing lifecycle manager..."
        )

    async def _bootstrap_health(self) -> None:
        self._logger.debug(
            "Running health checks..."
        )

        self._logger.info(
            "Health checks passed."
        )

    # ==========================================================
    # Shutdown Modules
    # ==========================================================

    async def _shutdown_health(self) -> None:
        self._logger.debug(
            "Stopping health system..."
        )

    async def _shutdown_lifecycle(self) -> None:
        self._logger.debug(
            "Stopping lifecycle manager..."
        )

    async def _shutdown_voice(self) -> None:
        self._logger.debug(
            "Stopping voice services..."
        )

        voice = self._voice

        if voice is None:
            return

        self._voice = None

        try:
            # stop() cancels an in-flight turn, releases the microphone and the
            # hotkey hook, and publishes VoiceServiceStopped.
            await voice.stop()

        except Exception:
            # Shutdown continues regardless: a stuck audio device must not stop
            # the remaining subsystems from tearing down.
            self._logger.exception(
                "Voice services did not shut down cleanly."
            )

    async def _shutdown_hud(self) -> None:
        self._logger.debug(
            "Stopping HUD..."
        )

        hud = self._hud

        if hud is None:
            return

        self._hud = None

        try:
            # Asks the child to quit, then waits out a short grace period before
            # killing it. Left alone, the overlay would outlive the CLI and stay
            # on screen with nothing behind it.
            await hud.stop()

        except Exception:
            self._logger.exception(
                "The HUD did not shut down cleanly."
            )

    async def _shutdown_llm(self) -> None:
        self._logger.debug(
            "Stopping LLM providers..."
        )

    async def _shutdown_memory(self) -> None:
        self._logger.debug(
            "Stopping memory services..."
        )

        if self._container is None:
            return

        from ..memory.services.manager import MemoryManager

        # is_instantiated, not has: resolving would construct a manager (and open
        # a database) purely in order to close one that was never built.
        if not self._container.is_instantiated(MemoryManager):
            return

        try:
            await self._container.resolve(MemoryManager).shutdown()
        except Exception:
            self._logger.exception(
                "Memory services did not shut down cleanly."
            )

    async def _shutdown_browser(self) -> None:
        self._logger.debug(
            "Stopping browser services..."
        )

        if self._container is None:
            return

        from ..browser.controller import BrowserService

        # is_instantiated, not has: BrowserService is registered lazily, and
        # resolving it here would construct a provider purely in order to close
        # one that was never opened.
        if not self._container.is_instantiated(BrowserService):
            return

        await self._container.resolve(BrowserService).shutdown()

    async def _shutdown_vision(self) -> None:
        self._logger.debug(
            "Stopping vision services..."
        )

        if self._container is None:
            return

        from ..vision.controller import VisionService

        # is_instantiated, not has: VisionService is registered lazily, and
        # resolving it here would build an OCR model purely in order to close it.
        if not self._container.is_instantiated(VisionService):
            return

        try:
            await self._container.resolve(VisionService).shutdown()

        except Exception:
            # Shutdown continues regardless: an unreleased model must not stop
            # the remaining subsystems from tearing down.
            self._logger.exception(
                "Vision services did not shut down cleanly."
            )

    async def _shutdown_desktop(self) -> None:
        self._logger.debug(
            "Stopping desktop services..."
        )

        if self._container is None:
            return

        from ..desktop.screen.controller import ScreenService

        if not self._container.is_instantiated(ScreenService):
            return

        try:
            await self._container.resolve(ScreenService).shutdown()

        except Exception:
            self._logger.exception(
                "Screen capture did not shut down cleanly."
            )

    async def _shutdown_trace(self) -> None:
        self._logger.debug(
            "Stopping live execution trace..."
        )

        recorder = self._trace

        if recorder is None:
            return

        self._trace = None

        try:
            # stop() unsubscribes from the bus, stops the dashboard and flushes
            # and closes the JSONL file. Idempotent and best-effort.
            await recorder.stop()

        except Exception:
            # Shutdown continues regardless: the trace is an observer, and a
            # recorder that will not stop cleanly must not block teardown.
            self._logger.exception(
                "Live execution trace did not shut down cleanly."
            )

    async def _shutdown_events(self) -> None:
        self._logger.debug(
            "Stopping event bus..."
        )
        bus = self._event_bus

        if bus is not None:
            # Dropping the reference alone would not release the handlers: the
            # HUD registers bound methods on the bus, so a restart in the same
            # process would leave the previous overlay's callbacks subscribed
            # and publishing into a dead pipe.
            await bus.clear()

        self._event_bus = None

    async def _shutdown_container(self) -> None:
        self._logger.debug(
            "Destroying DI container..."
        )

        # The container is process-wide, so dropping only this reference would
        # leave every already-resolved singleton cached. resolve() checks its
        # instance cache before the factories, so a later start() in the same
        # process would hand out the stale instances — including a provider
        # whose HTTP client had been closed.
        if self._container is not None:
            self._container.clear()

        self._container = None

    async def _shutdown_logging(self) -> None:
        self._logger.debug(
            "Stopping logging..."
        )