"""Application logging setup shared by runtime and offline pipelines."""

import os
import sys

from loguru import logger


def setup_logging():
    """Configure process logging according to environment settings."""
    # Remove default handler
    logger.remove()

    # In PROD, we use JSON format for CloudWatch
    log_format = (
        "{message}"
        if os.getenv("LOG_FORMAT_JSON") == "true"
        else "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=log_format,
        serialize=(os.getenv("LOG_FORMAT_JSON") == "true"),
        level="INFO",
    )


# Initialize once
setup_logging()


def get_logger(name: str):
    """Return a logger with the repository's configured context."""
    return logger.bind(name=name)


def log_separator(log_instance, char: str = "=", length: int = 60):
    """Emit a visually distinct section marker for long-running jobs."""
    log_instance.info(char * length)
