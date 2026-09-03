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
        self._container = container
        self._event_bus = None

        # Both are optional subsystems, gated on AETHEROS_HUD_ENABLED and
        # AETHEROS_VOICE_ENABLED. They stay None when disabled or when startup
        # degraded, and shutdown reads them to decide what to tear down.
        self._hud = None
        self._voice = None

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
            await self._bootstrap_tools()
            await self._bootstrap_memory()
            await self._bootstrap_llm()

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
        ocr = PaddleOCRProvider()

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
        """

        from ..vision.providers.yolo_provider import YOLOProvider

        weights = os.environ.get("AETHEROS_YOLO_WEIGHTS")

        if not weights:
            self._logger.debug(
                "AETHEROS_YOLO_WEIGHTS is not set; object detection disabled."
            )
            return None

        detector = YOLOProvider(model=weights)

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

    async def _bootstrap_llm(self) -> None:
        self._logger.info(
            "Initializing LLM providers..."
        )

        from ..llm.agent_loop import LLMToolLoop
        from ..llm.config import LLMConfig
        from ..llm.engine import LLMEngine
        from ..llm.manager import LLMProviderManager
        from ..llm.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )
        from ..llm.tool_schema import get_llm_tools
        from ..tools.executor import ToolExecutor

        # ----------------------------------------------------------
        # Configuration
        # ----------------------------------------------------------

        config = LLMConfig.from_env()

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

        tool_loop = LLMToolLoop(
            engine,
            ToolExecutor(tool_registry),
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

        self._container.register_singleton(
            LLMEngine,
            lambda: engine,
        )

        self._container.register_singleton(
            "llm_tool_loop",
            lambda: tool_loop,
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