"""Unit tests for H3: Missing Timeout Configuration.

This test suite validates:
1. Timeout configuration values are loaded correctly
2. Timeout configuration values are positive
3. Push notification requests use the configured timeout
4. Timeout exceptions are properly handled and logged
5. Custom timeout values from environment variables are respected
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, ANY
from typing import Generator

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTimeoutConfigDefaults:
    """Test default timeout configuration values."""

    def test_default_request_timeout_is_positive(self) -> None:
        """Test that DEFAULT_REQUEST_TIMEOUT is a positive float."""
        import config
        assert config.DEFAULT_REQUEST_TIMEOUT > 0
        assert isinstance(config.DEFAULT_REQUEST_TIMEOUT, (int, float))

    def test_pushover_request_timeout_is_positive(self) -> None:
        """Test that PUSHOVER_REQUEST_TIMEOUT is a positive float."""
        import config
        assert config.PUSHOVER_REQUEST_TIMEOUT > 0
        assert isinstance(config.PUSHOVER_REQUEST_TIMEOUT, (int, float))

    def test_serper_request_timeout_is_positive(self) -> None:
        """Test that SERPER_REQUEST_TIMEOUT is a positive float."""
        import config
        assert config.SERPER_REQUEST_TIMEOUT > 0
        assert isinstance(config.SERPER_REQUEST_TIMEOUT, (int, float))

    def test_wikipedia_request_timeout_is_positive(self) -> None:
        """Test that WIKIPEDIA_REQUEST_TIMEOUT is a positive float."""
        import config
        assert config.WIKIPEDIA_REQUEST_TIMEOUT > 0
        assert isinstance(config.WIKIPEDIA_REQUEST_TIMEOUT, (int, float))

    def test_default_values_are_reasonable(self) -> None:
        """Test that default timeout values are in reasonable ranges."""
        import config

        # All timeouts should be between 1s and 60s
        assert 1 <= config.DEFAULT_REQUEST_TIMEOUT <= 60
        assert 1 <= config.PUSHOVER_REQUEST_TIMEOUT <= 60
        assert 1 <= config.SERPER_REQUEST_TIMEOUT <= 60
        assert 1 <= config.WIKIPEDIA_REQUEST_TIMEOUT <= 60


class TestTimeoutConfigValidation:
    """Test timeout configuration validation."""

    def test_validate_timeout_config_passes_with_defaults(self) -> None:
        """Test that default configuration passes validation."""
        import config
        # Should not raise any exception
        config.validate_timeout_config()

    def test_validate_timeout_config_rejects_zero(self) -> None:
        """Test that validation rejects zero timeout."""
        import config

        # Temporarily patch a timeout to 0
        with patch.object(config, 'DEFAULT_REQUEST_TIMEOUT', 0):
            with pytest.raises(ValueError, match="must be positive"):
                config.validate_timeout_config()

    def test_validate_timeout_config_rejects_negative(self) -> None:
        """Test that validation rejects negative timeout."""
        import config

        with patch.object(config, 'PUSHOVER_REQUEST_TIMEOUT', -5):
            with pytest.raises(ValueError, match="must be positive"):
                config.validate_timeout_config()


class TestPushNotificationWithTimeout:
    """Test push notification function with timeout configuration."""

    @patch('sidekick_tools.requests.post')
    def test_push_uses_pushover_timeout(self, mock_post: MagicMock) -> None:
        """Test that push() uses PUSHOVER_REQUEST_TIMEOUT."""
        import sidekick_tools
        import config

        mock_post.return_value = MagicMock(status_code=200)

        sidekick_tools.push("Test message")

        # Verify requests.post was called with the timeout parameter
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == config.PUSHOVER_REQUEST_TIMEOUT

    @patch('sidekick_tools.requests.post')
    def test_push_sends_correct_data(self, mock_post: MagicMock) -> None:
        """Test that push() sends correct notification data."""
        import sidekick_tools

        mock_post.return_value = MagicMock(status_code=200)

        test_message = "Test notification message"
        sidekick_tools.push(test_message)

        # Verify requests.post was called with correct data
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert 'data' in call_kwargs
        assert call_kwargs['data']['message'] == test_message

    @patch('sidekick_tools.requests.post')
    def test_push_returns_success(self, mock_post: MagicMock) -> None:
        """Test that push() returns 'success' on successful request."""
        import sidekick_tools

        mock_post.return_value = MagicMock(status_code=200)

        result = sidekick_tools.push("Test message")

        assert result == "success"

    @patch('sidekick_tools.requests.post')
    def test_push_handles_timeout_exception(self, mock_post: MagicMock) -> None:
        """Test that push() properly handles timeout exceptions."""
        import sidekick_tools
        import requests

        mock_post.side_effect = requests.exceptions.Timeout(
            "Connection timeout"
        )

        with pytest.raises(requests.exceptions.Timeout):
            sidekick_tools.push("Test message")

    @patch('sidekick_tools.requests.post')
    @patch('sidekick_tools.logger')
    def test_push_logs_timeout_error(
        self, mock_logger: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test that push() logs timeout errors."""
        import sidekick_tools
        import requests

        mock_post.side_effect = requests.exceptions.Timeout(
            "Connection timeout"
        )

        with pytest.raises(requests.exceptions.Timeout):
            sidekick_tools.push("Test message")

        # Verify error was logged
        mock_logger.error.assert_called()
        assert "timeout" in mock_logger.error.call_args[0][0].lower()

    @patch('sidekick_tools.requests.post')
    def test_push_handles_request_exception(
        self, mock_post: MagicMock
    ) -> None:
        """Test that push() properly handles general request exceptions."""
        import sidekick_tools
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Network error"
        )

        with pytest.raises(requests.exceptions.RequestException):
            sidekick_tools.push("Test message")

    @patch('sidekick_tools.requests.post')
    @patch('sidekick_tools.logger')
    def test_push_logs_request_error(
        self, mock_logger: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test that push() logs request errors."""
        import sidekick_tools
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Network error"
        )

        with pytest.raises(requests.exceptions.RequestException):
            sidekick_tools.push("Test message")

        # Verify error was logged
        mock_logger.error.assert_called()


class TestEnvironmentVariableOverrides:
    """Test that timeout values can be overridden via environment variables."""

    def test_pushover_timeout_from_env(self) -> None:
        """Test that PUSHOVER_REQUEST_TIMEOUT respects environment variable."""
        # Set environment variable before importing
        os.environ['PUSHOVER_REQUEST_TIMEOUT'] = '7.5'

        # Need to reload the module to pick up the new env var
        import importlib
        import config
        importlib.reload(config)

        assert config.PUSHOVER_REQUEST_TIMEOUT == 7.5

        # Reset to default
        if 'PUSHOVER_REQUEST_TIMEOUT' in os.environ:
            del os.environ['PUSHOVER_REQUEST_TIMEOUT']

    def test_default_timeout_from_env(self) -> None:
        """Test that DEFAULT_REQUEST_TIMEOUT respects environment variable."""
        os.environ['REQUEST_TIMEOUT'] = '20.0'

        import importlib
        import config
        importlib.reload(config)

        assert config.DEFAULT_REQUEST_TIMEOUT == 20.0

        # Reset
        if 'REQUEST_TIMEOUT' in os.environ:
            del os.environ['REQUEST_TIMEOUT']

    def test_serper_timeout_from_env(self) -> None:
        """Test that SERPER_REQUEST_TIMEOUT respects environment variable."""
        os.environ['SERPER_REQUEST_TIMEOUT'] = '25.0'

        import importlib
        import config
        importlib.reload(config)

        assert config.SERPER_REQUEST_TIMEOUT == 25.0

        # Reset
        if 'SERPER_REQUEST_TIMEOUT' in os.environ:
            del os.environ['SERPER_REQUEST_TIMEOUT']

    def test_wikipedia_timeout_from_env(self) -> None:
        """Test that WIKIPEDIA_REQUEST_TIMEOUT respects environment variable."""
        os.environ['WIKIPEDIA_REQUEST_TIMEOUT'] = '12.0'

        import importlib
        import config
        importlib.reload(config)

        assert config.WIKIPEDIA_REQUEST_TIMEOUT == 12.0

        # Reset
        if 'WIKIPEDIA_REQUEST_TIMEOUT' in os.environ:
            del os.environ['WIKIPEDIA_REQUEST_TIMEOUT']


class TestTimeoutConsistency:
    """Test timeout consistency across different values."""

    def test_all_timeouts_are_floats_or_ints(self) -> None:
        """Test that all timeout values are numeric."""
        import config

        timeouts = [
            config.DEFAULT_REQUEST_TIMEOUT,
            config.PUSHOVER_REQUEST_TIMEOUT,
            config.SERPER_REQUEST_TIMEOUT,
            config.WIKIPEDIA_REQUEST_TIMEOUT,
        ]

        for timeout in timeouts:
            assert isinstance(timeout, (int, float))
            assert timeout > 0

    def test_pushover_timeout_is_shorter_than_search_timeout(self) -> None:
        """Test that Pushover timeout is shorter than search timeout.

        This is reasonable because push notifications should be fast,
        while searches can take longer due to remote indexing.
        """
        import config

        assert (
            config.PUSHOVER_REQUEST_TIMEOUT
            < config.SERPER_REQUEST_TIMEOUT
        )


class TestPushFunctionDocumentation:
    """Test that push function has proper documentation."""

    def test_push_has_docstring(self) -> None:
        """Test that push() function has a docstring."""
        import sidekick_tools

        assert sidekick_tools.push.__doc__ is not None
        assert len(sidekick_tools.push.__doc__) > 0

    def test_push_docstring_mentions_timeout(self) -> None:
        """Test that push() docstring documents timeout behavior."""
        import sidekick_tools

        docstring = sidekick_tools.push.__doc__.lower()
        # Should document that exceptions can be raised
        assert 'timeout' in docstring or 'exception' in docstring or 'raise' in docstring

    def test_push_raises_documented(self) -> None:
        """Test that push() documents raised exceptions."""
        import sidekick_tools

        docstring = sidekick_tools.push.__doc__.lower()
        # Should document timeout and request exceptions
        assert 'raise' in docstring or 'exception' in docstring


class TestConfigModuleAttributes:
    """Test that config module exports expected attributes."""

    def test_config_module_has_default_timeout(self) -> None:
        """Test that config module exports DEFAULT_REQUEST_TIMEOUT."""
        import config
        assert hasattr(config, 'DEFAULT_REQUEST_TIMEOUT')

    def test_config_module_has_pushover_timeout(self) -> None:
        """Test that config module exports PUSHOVER_REQUEST_TIMEOUT."""
        import config
        assert hasattr(config, 'PUSHOVER_REQUEST_TIMEOUT')

    def test_config_module_has_serper_timeout(self) -> None:
        """Test that config module exports SERPER_REQUEST_TIMEOUT."""
        import config
        assert hasattr(config, 'SERPER_REQUEST_TIMEOUT')

    def test_config_module_has_wikipedia_timeout(self) -> None:
        """Test that config module exports WIKIPEDIA_REQUEST_TIMEOUT."""
        import config
        assert hasattr(config, 'WIKIPEDIA_REQUEST_TIMEOUT')

    def test_config_module_has_validation_function(self) -> None:
        """Test that config module exports validate_timeout_config."""
        import config
        assert hasattr(config, 'validate_timeout_config')
        assert callable(config.validate_timeout_config)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
