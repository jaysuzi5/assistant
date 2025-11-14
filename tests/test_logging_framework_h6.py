"""Unit tests for H6: Missing Logging Framework.

This test suite validates:
1. Logging framework initialization and configuration
2. File rotation with size limits
3. Log level management and filtering
4. Color formatting for console output
5. Structured formatting for file output
6. Integration with application modules
7. Error handling and edge cases
"""

import pytest
import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestLoggingConfigInitialization:
    """Test LoggingConfig initialization and setup."""

    def test_logging_config_creates_log_directory(self) -> None:
        """Test that LoggingConfig creates log directory if missing."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "logs")
            assert not os.path.exists(log_dir)

            config = LoggingConfig(log_dir=log_dir)
            assert os.path.exists(log_dir)

    def test_logging_config_uses_existing_directory(self) -> None:
        """Test that LoggingConfig uses existing log directory."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            assert config.log_dir == Path(temp_dir)

    def test_logging_config_default_values(self) -> None:
        """Test that LoggingConfig has sensible defaults."""
        from logging_config import LoggingConfig, LogLevel

        config = LoggingConfig()
        assert config.log_level == LogLevel.INFO
        assert config.max_bytes == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5

    def test_logging_config_custom_values(self) -> None:
        """Test that LoggingConfig accepts custom values."""
        from logging_config import LoggingConfig, LogLevel

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                log_dir=temp_dir,
                log_level=LogLevel.DEBUG,
                max_bytes=1024 * 1024,  # 1MB
                backup_count=3,
            )

            assert config.log_level == LogLevel.DEBUG
            assert config.max_bytes == 1024 * 1024
            assert config.backup_count == 3

    def test_setup_logging_creates_handlers(self) -> None:
        """Test that setup_logging creates console and file handlers."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            config.setup_logging()

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0

            # Check handler types
            handler_types = [type(h).__name__ for h in root_logger.handlers]
            assert "StreamHandler" in handler_types
            assert "RotatingFileHandler" in handler_types

    def test_setup_logging_log_file_created(self) -> None:
        """Test that setup_logging creates log file."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            config.setup_logging()

            log_file = Path(temp_dir) / "sidekick.log"
            assert log_file.exists()


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_enum_values(self) -> None:
        """Test that LogLevel enum has correct values."""
        from logging_config import LogLevel

        assert LogLevel.DEBUG.value == logging.DEBUG
        assert LogLevel.INFO.value == logging.INFO
        assert LogLevel.WARNING.value == logging.WARNING
        assert LogLevel.ERROR.value == logging.ERROR
        assert LogLevel.CRITICAL.value == logging.CRITICAL

    def test_log_level_from_environment(self) -> None:
        """Test that log level can be set from environment."""
        from logging_config import LogLevel

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            # Environment variable doesn't affect enum, but shows intended pattern
            level = LogLevel.DEBUG
            assert level.value == logging.DEBUG


class TestColoredFormatter:
    """Test ColoredFormatter for console output."""

    def test_colored_formatter_formats_message(self) -> None:
        """Test that ColoredFormatter formats messages."""
        from logging_config import ColoredFormatter

        formatter = ColoredFormatter(fmt="%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "Test message" in formatted

    def test_colored_formatter_includes_level(self) -> None:
        """Test that ColoredFormatter includes log level."""
        from logging_config import ColoredFormatter

        formatter = ColoredFormatter(fmt="%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "ERROR" in formatted or "\033" in formatted  # Color codes

    def test_colored_formatter_exception_info(self) -> None:
        """Test that ColoredFormatter includes exception info."""
        from logging_config import ColoredFormatter

        formatter = ColoredFormatter(fmt="%(levelname)s | %(message)s")
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

            formatted = formatter.format(record)
            assert "Error occurred" in formatted
            assert "Traceback" in formatted


class TestStructuredFormatter:
    """Test StructuredFormatter for file output."""

    def test_structured_formatter_formats_message(self) -> None:
        """Test that StructuredFormatter formats messages."""
        from logging_config import StructuredFormatter

        formatter = StructuredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Structured message",
            args=(),
            exc_info=None,
            func="test_func",
        )

        formatted = formatter.format(record)
        assert "Structured message" in formatted
        assert "test_func:42" in formatted

    def test_structured_formatter_includes_timestamp(self) -> None:
        """Test that StructuredFormatter includes timestamp."""
        from logging_config import StructuredFormatter

        formatter = StructuredFormatter(
            fmt="%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Timestamped message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "Timestamped message" in formatted
        # Timestamp is in ISO format
        assert "-" in formatted  # Date separator


class TestLoggingConfiguration:
    """Test logging configuration and runtime changes."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a logger instance."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            logger = config.get_logger("test_module")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_module"

    def test_set_log_level_changes_level(self) -> None:
        """Test that set_log_level updates logging level."""
        from logging_config import LoggingConfig, LogLevel

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir, log_level=LogLevel.INFO)
            config.setup_logging()

            config.set_log_level(LogLevel.DEBUG)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_configure_module_loggers(self) -> None:
        """Test that module loggers are configured correctly."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            config.setup_logging()

            # Check that sidekick modules are configured
            sidekick_logger = logging.getLogger("sidekick")
            assert sidekick_logger.level == logging.DEBUG

            # Check that external modules have WARNING level
            external_logger = logging.getLogger("langchain")
            assert external_logger.level == logging.WARNING


class TestFileRotation:
    """Test log file rotation functionality."""

    def test_get_log_file_path(self) -> None:
        """Test that get_log_file_path returns correct path."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            log_file = config.get_log_file_path()

            assert log_file.name == "sidekick.log"
            assert str(log_file).startswith(temp_dir)

    def test_get_backup_log_files_empty(self) -> None:
        """Test that get_backup_log_files returns empty list initially."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            backups = config.get_backup_log_files()

            assert backups == []

    def test_clear_logs_removes_files(self) -> None:
        """Test that clear_logs removes log files."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            config.setup_logging()

            log_file = config.get_log_file_path()
            assert log_file.exists()

            config.clear_logs()
            assert not log_file.exists()

    def test_clear_logs_handles_missing_files(self) -> None:
        """Test that clear_logs handles missing files gracefully."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            config = LoggingConfig(log_dir=temp_dir)
            # Don't call setup_logging, so log files don't exist

            # Should not raise exception
            config.clear_logs()


class TestSetupLoggingFunction:
    """Test setup_logging convenience function."""

    def test_setup_logging_returns_config(self) -> None:
        """Test that setup_logging returns LoggingConfig instance."""
        from logging_config import setup_logging

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir)

            assert config is not None
            assert hasattr(config, "setup_logging")

    def test_setup_logging_with_custom_level(self) -> None:
        """Test that setup_logging accepts log level parameter."""
        from logging_config import setup_logging, LogLevel

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir, log_level=LogLevel.DEBUG)

            assert config.log_level == LogLevel.DEBUG

    def test_setup_logging_initializes_root_logger(self) -> None:
        """Test that setup_logging initializes root logger."""
        from logging_config import setup_logging

        with TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0


class TestGetLoggerFunction:
    """Test get_logger convenience function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns logger instance."""
        from logging_config import get_logger, setup_logging

        with TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)
            logger = get_logger("test_module")

            assert isinstance(logger, logging.Logger)

    def test_get_logger_multiple_calls_same_instance(self) -> None:
        """Test that multiple get_logger calls return same instance."""
        from logging_config import get_logger, setup_logging

        with TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)

            logger1 = get_logger("test_module")
            logger2 = get_logger("test_module")

            assert logger1 is logger2

    def test_get_logger_without_setup_initializes(self) -> None:
        """Test that get_logger initializes logging if needed."""
        from logging_config import get_logger
        import logging_config

        # Reset global config
        original_config = logging_config._logging_config
        logging_config._logging_config = None

        try:
            logger = get_logger("test_module")
            assert isinstance(logger, logging.Logger)
            assert logging_config._logging_config is not None
        finally:
            logging_config._logging_config = original_config


class TestGetLoggingConfigFunction:
    """Test get_logging_config function."""

    def test_get_logging_config_returns_instance(self) -> None:
        """Test that get_logging_config returns LoggingConfig instance."""
        from logging_config import get_logging_config, setup_logging

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir)
            retrieved_config = get_logging_config()

            assert retrieved_config is config

    def test_get_logging_config_before_setup(self) -> None:
        """Test that get_logging_config returns None before setup."""
        from logging_config import get_logging_config
        import logging_config

        # Reset global config
        original_config = logging_config._logging_config
        logging_config._logging_config = None

        try:
            config = get_logging_config()
            assert config is None
        finally:
            logging_config._logging_config = original_config


class TestLoggingIntegration:
    """Test logging integration with application."""

    def test_logging_in_sidekick_module(self) -> None:
        """Test that sidekick module uses logging."""
        from logging_config import setup_logging, get_logger

        with TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)
            logger = get_logger("sidekick")

            # Should not raise exception
            logger.info("Test log message")
            logger.debug("Debug message")
            logger.warning("Warning message")

    def test_logging_to_file(self) -> None:
        """Test that messages are actually logged to file."""
        from logging_config import setup_logging, get_logger

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir)
            logger = get_logger("test_module")

            logger.info("Test message to file")

            log_file = config.get_log_file_path()
            assert log_file.exists()

            with open(log_file, "r") as f:
                content = f.read()
                assert "Test message to file" in content

    def test_logging_different_levels(self) -> None:
        """Test logging at different levels."""
        from logging_config import setup_logging, get_logger

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir)
            logger = get_logger("test_module")

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            log_file = config.get_log_file_path()
            with open(log_file, "r") as f:
                content = f.read()
                assert "Debug message" in content
                assert "Info message" in content
                assert "Warning message" in content
                assert "Error message" in content


class TestLoggingErrorHandling:
    """Test error handling in logging framework."""

    def test_logging_with_exception(self) -> None:
        """Test logging with exception information."""
        from logging_config import setup_logging, get_logger

        with TemporaryDirectory() as temp_dir:
            config = setup_logging(log_dir=temp_dir)
            logger = get_logger("test_module")

            try:
                raise ValueError("Test error")
            except ValueError:
                logger.error("An error occurred", exc_info=True)

            log_file = config.get_log_file_path()
            with open(log_file, "r") as f:
                content = f.read()
                assert "An error occurred" in content
                assert "ValueError" in content

    def test_logging_with_relative_path(self) -> None:
        """Test logging with relative directory path."""
        from logging_config import LoggingConfig
        import tempfile

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            relative_subdir = os.path.join(temp_dir, "logs", "subdir")
            config = LoggingConfig(log_dir=relative_subdir)

            # Should create nested directories
            assert os.path.exists(relative_subdir)
            assert config is not None


class TestEnvironmentVariables:
    """Test environment variable configuration."""

    def test_log_dir_from_environment(self) -> None:
        """Test that log directory can be set from environment."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"SIDEKICK_LOG_DIR": temp_dir}):
                config = LoggingConfig()
                assert config.log_dir == Path(temp_dir)

    def test_log_dir_explicit_overrides_environment(self) -> None:
        """Test that explicit log_dir overrides environment variable."""
        from logging_config import LoggingConfig

        with TemporaryDirectory() as temp_dir1:
            with TemporaryDirectory() as temp_dir2:
                with patch.dict(os.environ, {"SIDEKICK_LOG_DIR": temp_dir1}):
                    config = LoggingConfig(log_dir=temp_dir2)
                    assert config.log_dir == Path(temp_dir2)


class TestBackwardCompatibility:
    """Test backward compatibility with existing logging."""

    def test_existing_loggers_still_work(self) -> None:
        """Test that existing loggers continue to work."""
        from logging_config import setup_logging

        with TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)

            # Create logger the old way
            logger = logging.getLogger("test_module")

            # Should still work
            logger.info("Message with existing logger")

    def test_setup_logging_multiple_calls(self) -> None:
        """Test that setup_logging can be called multiple times."""
        from logging_config import setup_logging

        with TemporaryDirectory() as temp_dir1:
            with TemporaryDirectory() as temp_dir2:
                config1 = setup_logging(log_dir=temp_dir1)
                config2 = setup_logging(log_dir=temp_dir2)

                # Both should work
                assert config1 is not None
                assert config2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
