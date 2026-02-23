"""
Structured Logging for pyrite

Provides consistent logging across all modules with:
- Configurable log levels
- Structured output (JSON optional)
- Module-specific loggers
"""

import logging
import sys
from typing import Literal

# Log level type
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Default format
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module logger names
LOGGER_NAMES = {
    "root": "pyrite",
    "storage": "pyrite.storage",
    "index": "pyrite.storage.index",
    "database": "pyrite.storage.database",
    "migrations": "pyrite.storage.migrations",
    "repository": "pyrite.storage.repository",
    "services": "pyrite.services",
    "api": "pyrite.server.api",
    "cli": "pyrite.cli",
    "mcp": "pyrite.mcp",
}


def get_logger(name: str = "root") -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Logger name (use keys from LOGGER_NAMES or full dotted name)

    Returns:
        Configured logger instance
    """
    logger_name = LOGGER_NAMES.get(name, name)
    return logging.getLogger(logger_name)


def configure_logging(
    level: LogLevel = "INFO",
    format_string: str | None = None,
    date_format: str | None = None,
    stream: object = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (default: timestamp [level] name: message)
        date_format: Custom date format (default: YYYY-MM-DD HH:MM:SS)
        stream: Output stream (default: stderr)
    """
    root_logger = logging.getLogger("pyrite")

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set level
    root_logger.setLevel(getattr(logging, level))

    # Create handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(getattr(logging, level))

    # Create formatter
    formatter = logging.Formatter(
        fmt=format_string or DEFAULT_FORMAT,
        datefmt=date_format or DEFAULT_DATE_FORMAT,
    )
    handler.setFormatter(formatter)

    # Add handler
    root_logger.addHandler(handler)

    # Don't propagate to root logger
    root_logger.propagate = False


def configure_quiet() -> None:
    """Configure logging to suppress all but errors."""
    configure_logging(level="ERROR")


def configure_verbose() -> None:
    """Configure logging for verbose output."""
    configure_logging(level="DEBUG")


# Pre-configured loggers for common use
logger = get_logger("root")
storage_logger = get_logger("storage")
index_logger = get_logger("index")
db_logger = get_logger("database")
migration_logger = get_logger("migrations")
api_logger = get_logger("api")
cli_logger = get_logger("cli")


# Initialize with default config
configure_logging()
