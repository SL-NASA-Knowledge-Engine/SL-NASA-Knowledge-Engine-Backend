# core/logging_config.py
import logging
from enum import StrEnum
from uvicorn.logging import DefaultFormatter


class LogLevels(StrEnum):
    info = "INFO"
    warn = "WARNING"
    error = "ERROR"
    debug = "DEBUG"


def configure_logging(log_level: str = LogLevels.error):
    log_level = str(log_level).upper()
    valid_levels = [level.value for level in LogLevels]

    if log_level not in valid_levels:
        log_level = LogLevels.error

    handler = logging.StreamHandler()
    formatter = DefaultFormatter(fmt="%(levelprefix)s %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []
    root_logger.addHandler(handler)
