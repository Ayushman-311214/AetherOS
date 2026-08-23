from ...config.config_loader import get_settings
from .container import ServiceContainer
from ...core.logging import get_logger

container=ServiceContainer()
container.register_singleton(
    "settings",
    get_settings,
    
)

container.register_singleton(
    "logger",
    lambda: get_logger("core"),
)