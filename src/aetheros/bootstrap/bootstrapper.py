from __future__ import annotations

from ..vision.providers.base import BaseVisionProvider
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

            await self._bootstrap_desktop()
            await self._bootstrap_tools()
            await self._bootstrap_vision()
            await self._bootstrap_browser()
            await self._bootstrap_memory()
            await self._bootstrap_llm()

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

        from ..core.container.container import ServiceContainer

        self._container = ServiceContainer()

        self._logger.info(
            "DI container initialized."
        )

    async def _bootstrap_events(self) -> None:
        self._logger.debug(
            "Initializing event bus..."
        )

        # EventBus will be connected here.
        #
        # Example:
        #
        # self._event_bus = EventBus()

        self._logger.info(
            "Event system initialized."
        )


    async def _bootstrap_desktop(self) -> None:
        self._logger.debug("Initializing desktop services...")

    
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

        print("\n========== TOOL BOOTSTRAP ==========")
    
        print(
        "[DEBUG TOOLS] Importing keyboard tools..."
    )
        from ..desktop.keyboard.controller import KeyboardService
        from ..desktop.keyboard.pyautogui_backend import PyAutoGuiKeyboard
    
        keyboard_controller = PyAutoGuiKeyboard()

        print(f"[DEBUG BOOTSTRAP DESKTOP] Keyboard Controller : {keyboard_controller}")

        print(
        "[DEBUG TOOLS] Total:",
        tool_registry.count,
    )
        container.register_singleton(
            PyAutoGuiKeyboard,
            lambda: keyboard_controller,
        )


        container.register_singleton(
            KeyboardService,
            lambda: KeyboardService(
                container.resolve(PyAutoGuiKeyboard)
            ),
        )
        
# ---------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------
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
        
        print(f"[DEBUG BOOTSTRAP DESKTOP] Registery after keyboard : ",container.registered_services())

        self._logger.debug(
            "Desktop services initialized."
        )


    async def _bootstrap_vision(self) -> None:
        self._logger.debug(
            "Initializing vision services..."
        )

        from ..vision.controller import VisionService
        from ..vision.providers.opencv_provider import OpenCVProvider
        from ..vision.providers.paddleocr_provider import PaddleOCRProvider

        # ---------------------------------------------------------
        # OpenCV provider
        # ---------------------------------------------------------

        opencv = OpenCVProvider()

        self._container.register_singleton(
            OpenCVProvider,
            lambda: opencv,
        )

        # ---------------------------------------------------------
        # PaddleOCR provider
        # ---------------------------------------------------------

        ocr = PaddleOCRProvider()

        self._container.register_singleton(
            PaddleOCRProvider,
            lambda: ocr,
        )

        # ---------------------------------------------------------
        # Vision service
        # ---------------------------------------------------------

        self._container.register_singleton(
            VisionService,
            lambda: VisionService(
                ocr=self._container.resolve(PaddleOCRProvider),
                cv=self._container.resolve(OpenCVProvider),
            ),
        )

        self._logger.info(
            "Vision services initialized."
        )

        print(
            "[DEBUG BOOTSTRAP VISION] Registry:",
            self._container.registered_services(),
        )
        
    

    async def _bootstrap_tools(self) -> None:
        print("\n========== TOOL BOOTSTRAP START ==========")

        self._logger.info(
            "Initializing tool system..."
        )

        print("[DEBUG BOOTSTRAP] Importing registry...")

        from ..tools.registry import tool_registry

        print(
            "[DEBUG BOOTSTRAP] Registry imported:",
            tool_registry
        )

    

        print("[DEBUG BOOTSTRAP] Importing mouse tools...")

        import src.aetheros.desktop.mouse.tools
        import src.aetheros.desktop.keyboard.tools
        import src.aetheros.desktop.clipboard.tools
        print("[DEBUG BOOTSTRAP] Desktop tools import finished")
        import src.aetheros.vision.tools
        print("[DEBUG BOOTSTRAP] Vision tools import finished")


        print(
            "[DEBUG BOOTSTRAP] Tool count:",
            tool_registry.count
        )

        print("========== TOOL BOOTSTRAP END ==========\n")

    
        
    async def _bootstrap_browser(self) -> None:
        self._logger.debug(
            "Initializing browser services..."
        )

    async def _bootstrap_memory(self) -> None:
        self._logger.debug(
            "Initializing memory services..."
        )

    async def _bootstrap_llm(self) -> None:
        self._logger.info(
            "Initializing LLM providers..."
        )

        from ..core.container import container

        from ..llm.config import LLMConfig
        from ..llm.manager import LLMProviderManager
        from ..llm.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )

        # ----------------------------------------------------------
        # Configuration
        # ----------------------------------------------------------

        config = LLMConfig.from_env()

        self._logger.debug(
            "LLM model: %s",
            config.model,
        )

        self._logger.debug(
            "LLM base URL: %s",
            config.base_url,
        )

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
        # Container
        # ----------------------------------------------------------

        container.register_singleton(
            LLMProviderManager,
            lambda: manager,
        )

        container.register_singleton(
            "llm_provider",
            lambda: provider,
        )

        # ----------------------------------------------------------
        # Health
        # ----------------------------------------------------------

        healthy = await provider.health_check()

        if healthy:
            self._logger.info(
                "LLM provider '%s' is healthy.",
                provider.name,
            )
        else:
            self._logger.warning(
                "LLM provider '%s' failed health check.",
                provider.name,
            )
            
            
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

    async def _shutdown_vision(self) -> None:
        self._logger.debug(
            "Stopping vision services..."
        )

    async def _shutdown_desktop(self) -> None:
        self._logger.debug(
            "Stopping desktop services..."
        )

    async def _shutdown_events(self) -> None:
        self._logger.debug(
            "Stopping event bus..."
        )

        self._event_bus = None

    async def _shutdown_container(self) -> None:
        self._logger.debug(
            "Destroying DI container..."
        )

        self._container = None

    async def _shutdown_logging(self) -> None:
        self._logger.debug(
            "Stopping logging..."
        )