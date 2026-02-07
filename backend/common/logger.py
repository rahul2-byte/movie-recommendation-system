"""
Logging configuration for the movie enrichment pipeline.

Provides structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from pythonjsonlogger import jsonlogger

from configs.settings import LOG_FORMAT_JSON

# Define LOG_DIR locally to remove dependency on backend.configs.settings
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)  # Ensure log directory exists

# Store created loggers to avoid duplicate handlers
_loggers = {}


def get_logger(
    name: str, log_file: Optional[str] = "enrichment.log", level: int = logging.INFO
) -> logging.Logger:
    """
    Get or create a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        log_file: Log file name, None for console only
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    # Return existing logger if already configured
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Clear any existing handlers
    logger.handlers.clear()

    # Define log format fields
    log_fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    if LOG_FORMAT_JSON:
        formatter = jsonlogger.JsonFormatter(log_fmt, datefmt=date_fmt)
    else:
        # Standard human-readable formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt=date_fmt,
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(log_path, mode="a")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def log_separator(logger: logging.Logger, char: str = "=", length: int = 60) -> None:
    """
    Log a visual separator line.

    Args:
        logger: Logger instance
        char: Character to use for separator
        length: Length of separator line
    """
    logger.info(char * length)

