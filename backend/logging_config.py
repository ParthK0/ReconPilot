"""
backend/logging_config.py
=========================
Centralized structured logging configuration for ReconPilot.
Provides standard logger instances with uniform timestamp, log level,
and module context formatting across backend services.
"""

import os
import sys
import logging
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: Optional[str] = None):
    """Configures root logger with standard formatting."""
    log_level = getattr(logging, level.upper(), logging.INFO) if level else getattr(logging, LOG_LEVEL, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    root_logger = logging.getLogger()
    # Avoid duplicate handlers on re-configuration
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers[0].setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    root_logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance scoped to the specified component name."""
    return logging.getLogger(f"reconpilot.{name}")


# Initialize default configuration on module import
configure_logging()
