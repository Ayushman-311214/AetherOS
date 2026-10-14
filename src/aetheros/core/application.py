from __future__ import annotations

from .logging import get_logger


class Application:
    """
    Main AetherOS application.

    Responsible for starting and shutting down
    the AetherOS runtime.
    """

    def __init__(self) -> None:
        self.logger = get_logger("aetheros")

    def startup(self) -> None:
        self.logger.info("Starting AetherOS...")

        # Future initialization:
        #
        # self._load_config()
        # self._setup_container()
        # self._setup_event_bus()
        # self._setup_tools()
        # self._setup_desktop()
        # self._setup_vision()
        # self._setup_browser()
        # self._setup_llm()

        self.logger.info("AetherOS started successfully.")

    def shutdown(self) -> None:
        self.logger.info("Shutting down AetherOS...")

        # Future cleanup:
        #
        # close browser
        # stop services
        # cleanup resources

        self.logger.info("AetherOS stopped.")

    def run(self) -> None:
        try:
            self.startup()

            self.logger.info(
                "AetherOS is running. Press Ctrl+C to stop."
            )

            while True:
                pass

        except KeyboardInterrupt:
            self.logger.info("Shutdown requested.")

        finally:
            self.shutdown()