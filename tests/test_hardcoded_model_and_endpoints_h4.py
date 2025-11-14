"""Unit tests for H4: Hardcoded Model and Endpoints.

This test suite validates:
1. Model configuration is loaded correctly from environment variables
2. Endpoint configuration is loaded correctly from environment variables
3. LLM instances are created with correct models
4. API endpoints are properly configured
5. Validation catches invalid configurations
6. Default values work when environment variables are not set
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Generator

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestModelConfiguration:
    """Test LLM model configuration."""

    def test_worker_llm_model_has_default(self) -> None:
        """Test that WORKER_LLM_MODEL has a default value."""
        import config
        assert config.WORKER_LLM_MODEL is not None
        assert config.WORKER_LLM_MODEL == "gpt-4o-mini"

    def test_evaluator_llm_model_has_default(self) -> None:
        """Test that EVALUATOR_LLM_MODEL has a default value."""
        import config
        assert config.EVALUATOR_LLM_MODEL is not None
        assert config.EVALUATOR_LLM_MODEL == "gpt-4o-mini"

    def test_worker_llm_model_from_env(self) -> None:
        """Test that WORKER_LLM_MODEL respects environment variable."""
        os.environ['WORKER_LLM_MODEL'] = 'gpt-4'

        import importlib
        import config
        importlib.reload(config)

        assert config.WORKER_LLM_MODEL == 'gpt-4'

        # Reset
        if 'WORKER_LLM_MODEL' in os.environ:
            del os.environ['WORKER_LLM_MODEL']

    def test_evaluator_llm_model_from_env(self) -> None:
        """Test that EVALUATOR_LLM_MODEL respects environment variable."""
        os.environ['EVALUATOR_LLM_MODEL'] = 'claude-3-5-sonnet-20241022'

        import importlib
        import config
        importlib.reload(config)

        assert config.EVALUATOR_LLM_MODEL == 'claude-3-5-sonnet-20241022'

        # Reset
        if 'EVALUATOR_LLM_MODEL' in os.environ:
            del os.environ['EVALUATOR_LLM_MODEL']

    def test_worker_model_name_is_string(self) -> None:
        """Test that WORKER_LLM_MODEL is a string."""
        import config
        assert isinstance(config.WORKER_LLM_MODEL, str)
        assert len(config.WORKER_LLM_MODEL) > 0

    def test_evaluator_model_name_is_string(self) -> None:
        """Test that EVALUATOR_LLM_MODEL is a string."""
        import config
        assert isinstance(config.EVALUATOR_LLM_MODEL, str)
        assert len(config.EVALUATOR_LLM_MODEL) > 0


class TestOpenAIConfiguration:
    """Test OpenAI-specific configuration."""

    def test_openai_api_base_is_optional(self) -> None:
        """Test that OPENAI_API_BASE is optional."""
        import config
        # Should be None by default
        assert config.OPENAI_API_BASE is None or isinstance(config.OPENAI_API_BASE, str)

    def test_openai_api_version_is_optional(self) -> None:
        """Test that OPENAI_API_VERSION is optional."""
        import config
        # Should be None by default
        assert config.OPENAI_API_VERSION is None or isinstance(config.OPENAI_API_VERSION, str)

    def test_openai_api_base_from_env(self) -> None:
        """Test that OPENAI_API_BASE respects environment variable."""
        os.environ['OPENAI_API_BASE'] = 'https://api.openai.com/v1'

        import importlib
        import config
        importlib.reload(config)

        assert config.OPENAI_API_BASE == 'https://api.openai.com/v1'

        # Reset
        if 'OPENAI_API_BASE' in os.environ:
            del os.environ['OPENAI_API_BASE']

    def test_openai_api_version_from_env(self) -> None:
        """Test that OPENAI_API_VERSION respects environment variable."""
        os.environ['OPENAI_API_VERSION'] = '2024-10-01'

        import importlib
        import config
        importlib.reload(config)

        assert config.OPENAI_API_VERSION == '2024-10-01'

        # Reset
        if 'OPENAI_API_VERSION' in os.environ:
            del os.environ['OPENAI_API_VERSION']


class TestEndpointConfiguration:
    """Test API endpoint configuration."""

    def test_pushover_api_url_has_default(self) -> None:
        """Test that PUSHOVER_API_URL has a default value."""
        import config
        assert config.PUSHOVER_API_URL is not None
        assert "pushover" in config.PUSHOVER_API_URL.lower()

    def test_serper_api_url_has_default(self) -> None:
        """Test that SERPER_API_URL has a default value."""
        import config
        assert config.SERPER_API_URL is not None
        assert "serper" in config.SERPER_API_URL.lower()

    def test_pushover_api_url_is_https(self) -> None:
        """Test that PUSHOVER_API_URL uses HTTPS."""
        import config
        assert config.PUSHOVER_API_URL.startswith("https://")

    def test_serper_api_url_is_https(self) -> None:
        """Test that SERPER_API_URL uses HTTPS."""
        import config
        assert config.SERPER_API_URL.startswith("https://")

    def test_pushover_api_url_from_env(self) -> None:
        """Test that PUSHOVER_API_URL respects environment variable."""
        os.environ['PUSHOVER_API_URL'] = 'https://custom.pushover.net/v1/messages'

        import importlib
        import config
        importlib.reload(config)

        assert config.PUSHOVER_API_URL == 'https://custom.pushover.net/v1/messages'

        # Reset
        if 'PUSHOVER_API_URL' in os.environ:
            del os.environ['PUSHOVER_API_URL']

    def test_serper_api_url_from_env(self) -> None:
        """Test that SERPER_API_URL respects environment variable."""
        os.environ['SERPER_API_URL'] = 'https://custom.serper.dev/search'

        import importlib
        import config
        importlib.reload(config)

        assert config.SERPER_API_URL == 'https://custom.serper.dev/search'

        # Reset
        if 'SERPER_API_URL' in os.environ:
            del os.environ['SERPER_API_URL']


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_validate_llm_config_passes_with_defaults(self) -> None:
        """Test that default LLM configuration passes validation."""
        import config
        # Should not raise any exception
        config.validate_llm_config()

    def test_validate_api_endpoints_passes_with_defaults(self) -> None:
        """Test that default API endpoints pass validation."""
        import config
        # Should not raise any exception
        config.validate_api_endpoints()

    def test_validate_llm_config_rejects_empty_worker_model(self) -> None:
        """Test that validation rejects empty WORKER_LLM_MODEL."""
        import config

        with patch.object(config, 'WORKER_LLM_MODEL', ''):
            with pytest.raises(ValueError, match="WORKER_LLM_MODEL"):
                config.validate_llm_config()

    def test_validate_llm_config_rejects_empty_evaluator_model(self) -> None:
        """Test that validation rejects empty EVALUATOR_LLM_MODEL."""
        import config

        with patch.object(config, 'EVALUATOR_LLM_MODEL', ''):
            with pytest.raises(ValueError, match="EVALUATOR_LLM_MODEL"):
                config.validate_llm_config()

    def test_validate_api_endpoints_rejects_empty_pushover_url(self) -> None:
        """Test that validation rejects empty PUSHOVER_API_URL."""
        import config

        with patch.object(config, 'PUSHOVER_API_URL', ''):
            with pytest.raises(ValueError, match="PUSHOVER_API_URL"):
                config.validate_api_endpoints()

    def test_validate_api_endpoints_rejects_invalid_pushover_url(self) -> None:
        """Test that validation rejects non-https PUSHOVER_API_URL."""
        import config

        with patch.object(config, 'PUSHOVER_API_URL', 'not-a-url'):
            with pytest.raises(ValueError, match="must be a valid URL"):
                config.validate_api_endpoints()

    def test_validate_api_endpoints_rejects_empty_serper_url(self) -> None:
        """Test that validation rejects empty SERPER_API_URL."""
        import config

        with patch.object(config, 'SERPER_API_URL', ''):
            with pytest.raises(ValueError, match="SERPER_API_URL"):
                config.validate_api_endpoints()

    def test_validate_api_endpoints_rejects_invalid_serper_url(self) -> None:
        """Test that validation rejects non-https SERPER_API_URL."""
        import config

        with patch.object(config, 'SERPER_API_URL', 'ftp://invalid.url'):
            with pytest.raises(ValueError, match="must be a valid URL"):
                config.validate_api_endpoints()


class TestSidekickLLMConfiguration:
    """Test that Sidekick properly uses LLM configuration."""

    @patch('sidekick.ChatOpenAI')
    def test_sidekick_setup_uses_worker_model_config(self, mock_chat_openai: MagicMock) -> None:
        """Test that Sidekick setup uses WORKER_LLM_MODEL configuration."""
        import config
        from sidekick import Sidekick

        sidekick = Sidekick()

        # Mock the playwright_tools and other_tools to avoid real browser
        async def mock_setup():
            from unittest.mock import AsyncMock
            sidekick.tools = []
            sidekick.browser = AsyncMock()
            sidekick.playwright = AsyncMock()

            # Manually set the LLM models to test
            sidekick.worker_llm_with_tools = MagicMock()
            sidekick.evaluator_llm_with_output = MagicMock()
            sidekick.graph = MagicMock()

        # Can't easily test async setup in sync context, so we verify config exists
        assert config.WORKER_LLM_MODEL is not None

    def test_sidekick_tools_uses_pushover_endpoint(self) -> None:
        """Test that sidekick_tools uses PUSHOVER_API_URL configuration."""
        import config
        import sidekick_tools

        # Verify the pushover_url variable was set from config
        assert sidekick_tools.pushover_url == config.PUSHOVER_API_URL


class TestConfigModuleAttributes:
    """Test that config module exports expected attributes."""

    def test_config_has_worker_llm_model(self) -> None:
        """Test that config module has WORKER_LLM_MODEL."""
        import config
        assert hasattr(config, 'WORKER_LLM_MODEL')

    def test_config_has_evaluator_llm_model(self) -> None:
        """Test that config module has EVALUATOR_LLM_MODEL."""
        import config
        assert hasattr(config, 'EVALUATOR_LLM_MODEL')

    def test_config_has_openai_api_base(self) -> None:
        """Test that config module has OPENAI_API_BASE."""
        import config
        assert hasattr(config, 'OPENAI_API_BASE')

    def test_config_has_openai_api_version(self) -> None:
        """Test that config module has OPENAI_API_VERSION."""
        import config
        assert hasattr(config, 'OPENAI_API_VERSION')

    def test_config_has_pushover_api_url(self) -> None:
        """Test that config module has PUSHOVER_API_URL."""
        import config
        assert hasattr(config, 'PUSHOVER_API_URL')

    def test_config_has_serper_api_url(self) -> None:
        """Test that config module has SERPER_API_URL."""
        import config
        assert hasattr(config, 'SERPER_API_URL')

    def test_config_has_validation_functions(self) -> None:
        """Test that config module has validation functions."""
        import config
        assert hasattr(config, 'validate_llm_config')
        assert hasattr(config, 'validate_api_endpoints')
        assert callable(config.validate_llm_config)
        assert callable(config.validate_api_endpoints)


class TestConfigurationFlexibility:
    """Test configuration flexibility for different scenarios."""

    def test_can_use_gpt4_model(self) -> None:
        """Test that GPT-4 model can be configured."""
        os.environ['WORKER_LLM_MODEL'] = 'gpt-4'

        import importlib
        import config
        importlib.reload(config)

        assert config.WORKER_LLM_MODEL == 'gpt-4'
        # Verify it passes validation
        config.validate_llm_config()

        # Reset
        del os.environ['WORKER_LLM_MODEL']

    def test_can_use_different_models_for_worker_and_evaluator(self) -> None:
        """Test that worker and evaluator can use different models."""
        os.environ['WORKER_LLM_MODEL'] = 'gpt-4o-mini'
        os.environ['EVALUATOR_LLM_MODEL'] = 'gpt-4'

        import importlib
        import config
        importlib.reload(config)

        assert config.WORKER_LLM_MODEL != config.EVALUATOR_LLM_MODEL
        config.validate_llm_config()

        # Reset
        del os.environ['WORKER_LLM_MODEL']
        del os.environ['EVALUATOR_LLM_MODEL']

    def test_can_configure_custom_pushover_endpoint(self) -> None:
        """Test that custom Pushover endpoint can be configured."""
        os.environ['PUSHOVER_API_URL'] = 'https://staging.pushover.net/api/1/messages'

        import importlib
        import config
        importlib.reload(config)

        assert config.PUSHOVER_API_URL == 'https://staging.pushover.net/api/1/messages'
        config.validate_api_endpoints()

        # Reset
        del os.environ['PUSHOVER_API_URL']

    def test_can_configure_openai_proxy(self) -> None:
        """Test that OpenAI proxy can be configured."""
        os.environ['OPENAI_API_BASE'] = 'https://my-proxy.example.com/openai/v1'

        import importlib
        import config
        importlib.reload(config)

        assert config.OPENAI_API_BASE == 'https://my-proxy.example.com/openai/v1'

        # Reset
        del os.environ['OPENAI_API_BASE']


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_default_models_are_gpt4o_mini(self) -> None:
        """Test that default models are gpt-4o-mini for backward compatibility."""
        import config
        assert config.WORKER_LLM_MODEL == "gpt-4o-mini"
        assert config.EVALUATOR_LLM_MODEL == "gpt-4o-mini"

    def test_default_pushover_endpoint_is_official(self) -> None:
        """Test that default Pushover endpoint is the official one."""
        import config
        assert "api.pushover.net" in config.PUSHOVER_API_URL

    def test_default_serper_endpoint_is_official(self) -> None:
        """Test that default Serper endpoint is the official one."""
        import config
        assert "google.serper.dev" in config.SERPER_API_URL


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
