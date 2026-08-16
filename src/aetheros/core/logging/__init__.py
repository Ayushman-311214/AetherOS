# """Central logging framework (core.logging), built on Loguru.

#     from core.logging import setup_logging, logger

#     setup_logging(app_name="myservice")
#     logger.info("hello")
# """

# from logger import logger, setup_logging

# __all__ = ["logger", "setup_logging"]


from .logger import get_logger

__all__ = ["get_logger"]