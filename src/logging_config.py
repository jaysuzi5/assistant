"""Centralized logging configuration for Sidekick.

This module provides a unified logging setup with:
- Console output with colored formatting
- File output with automatic rotation
- Structured logging for machine readability
- Environment-based configuration
- Per-module logger management

Key components:
- setup_logging(): Configure all loggers
- get_logger(): Get module-specific logger
- LogLevel: Enum for log level configuration
"""

import logging
import logging.handlers
import sys
import os
from typing import Optional
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    """Log level configuration enum."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color codes for console output.

    Provides visual distinction between log levels for terminal output.
    """

    # ANSI color codes
    COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color codes.

        Args:
            record: The log record to format

        Returns:
            Formatted log message with color codes
        """
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Formatter for structured logging output.

    Provides machine-readable format suitable for log aggregation services.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured data.

        Args:
            record: The log record to format

        Returns:
            Structured log message with additional context
        """
        # Base message
        message = record.getMessage()

        # Add timestamp
        timestamp = self.formatTime(record)

        # Build structured output
        structured = (
            f"[{timestamp}] {record.levelname:8} {record.name:25} "
            f"{record.funcName}:{record.lineno} - {message}"
        )

        # Add exception info if present
        if record.exc_info:
            structured += f"\n{self.formatException(record.exc_info)}"

        return structured


class LoggingConfig:
    """Centralized logging configuration manager.

    Handles setup and management of all loggers in the Sidekick framework.

    Attributes:
        log_dir: Directory for log files
        log_level: Current logging level
        max_bytes: Maximum size before log rotation (10MB default)
        backup_count: Number of backup files to keep (5 default)
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_level: LogLevel = LogLevel.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ) -> None:
        """Initialize logging configuration.

        Args:
            log_dir: Directory for log files (defaults to ./logs)
            log_level: Initial logging level (defaults to INFO)
            max_bytes: Max file size before rotation (defaults to 10MB)
            backup_count: Number of backup log files to keep (defaults to 5)
        """
        # Determine log directory
        if log_dir is None:
            log_dir = os.environ.get(
                "SIDEKICK_LOG_DIR",
                str(Path(__file__).parent.parent / "logs")
            )

        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Track configured loggers to avoid duplicate handlers
        self._configured_loggers: set = set()

    def setup_logging(self) -> None:
        """Configure root logger and common module loggers.

        Sets up both console and file handlers with appropriate formatters.
        Should be called once at application startup.
        """
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level.value)

        # Remove any existing handlers
        root_logger.handlers.clear()

        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level.value)
        console_formatter = ColoredFormatter(
            fmt="%(levelname)s | %(name)s | %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        log_file = self.log_dir / "sidekick.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
        )
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        file_formatter = StructuredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Configure specific module loggers
        self._configure_module_loggers()

    def _configure_module_loggers(self) -> None:
        """Configure loggers for specific modules.

        Sets appropriate log levels for different components.
        """
        # Sidekick modules - DEBUG level for development, INFO for production
        sidekick_modules = [
            "sidekick",
            "sidekick_tools",
            "validation",
            "tool_error_handler",
            "llm_invocation",
            "app",
        ]

        for module in sidekick_modules:
            logger = logging.getLogger(module)
            logger.setLevel(logging.DEBUG)

        # External library loggers - only WARNING and above
        external_modules = [
            "langchain",
            "langchain_core",
            "langchain_community",
            "langgraph",
            "gradio",
            "urllib3",
            "httpx",
            "asyncio",
        ]

        for module in external_modules:
            logger = logging.getLogger(module)
            logger.setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for a module.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)

        # Ensure logger is configured
        if name not in self._configured_loggers:
            logger.setLevel(logging.DEBUG)
            self._configured_loggers.add(name)

        return logger

    def set_log_level(self, level: LogLevel) -> None:
        """Change the logging level at runtime.

        Args:
            level: New log level
        """
        self.log_level = level
        root_logger = logging.getLogger()
        root_logger.setLevel(level.value)

        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(level.value)

    def get_log_file_path(self) -> Path:
        """Get the path to the main log file.

        Returns:
            Path to sidekick.log
        """
        return self.log_dir / "sidekick.log"

    def get_backup_log_files(self) -> list:
        """Get list of backup log files.

        Returns:
            List of paths to backup log files (rotated logs)
        """
        backup_files = []
        for i in range(1, self.backup_count + 1):
            backup_file = self.log_dir / f"sidekick.log.{i}"
            if backup_file.exists():
                backup_files.append(backup_file)
        return backup_files

    def clear_logs(self) -> None:
        """Clear all log files (for testing).

        WARNING: This deletes all log files. Use with caution.
        """
        log_file = self.get_log_file_path()
        if log_file.exists():
            log_file.unlink()

        for backup_file in self.get_backup_log_files():
            backup_file.unlink()


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def setup_logging(
    log_dir: Optional[str] = None,
    log_level: LogLevel = LogLevel.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> LoggingConfig:
    """Initialize the logging framework.

    This function should be called once at application startup, before
    creating any loggers. It returns a LoggingConfig instance that can
    be used to manage logging at runtime.

    Args:
        log_dir: Directory for log files (defaults to ./logs)
        log_level: Initial logging level (defaults to INFO)
        max_bytes: Max file size before rotation (defaults to 10MB)
        backup_count: Number of backup log files to keep (defaults to 5)

    Returns:
        LoggingConfig instance for runtime management

    Example:
        >>> logging_config = setup_logging(log_level=LogLevel.DEBUG)
        >>> logger = logging_config.get_logger(__name__)
        >>> logger.info("Application started")
    """
    global _logging_config

    _logging_config = LoggingConfig(
        log_dir=log_dir,
        log_level=log_level,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    _logging_config.setup_logging()

    return _logging_config


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module.

    This is a convenience function that returns a logger with the
    appropriate name and configuration. It should be called in each
    module as: logger = get_logger(__name__)

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello world")
    """
    if _logging_config is None:
        # Fallback if setup_logging() hasn't been called
        setup_logging()

    return _logging_config.get_logger(name)


def get_logging_config() -> Optional[LoggingConfig]:
    """Get the global logging configuration instance.

    Returns:
        LoggingConfig instance if initialized, None otherwise
    """
    return _logging_config
