def __init__(self) -> None:
    setup_logging(console=False)

    self._logger = get_logger("bootstrapper")

    self._started = False

    self._container = None
    self._event_bus = None