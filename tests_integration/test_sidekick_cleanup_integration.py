"""Integration tests for cleanup with Gradio callback.

This module contains integration tests that test the interaction between
the Sidekick cleanup functionality and the Gradio application layer.
These tests require the app module and test real callbacks, not just
the cleanup logic in isolation.
"""

import pytest
import logging
from unittest.mock import AsyncMock


class TestCleanupIntegration:
    """Integration tests for cleanup with Gradio callback."""

    @pytest.mark.skip(reason="Requires Gradio app setup and resources initialization")
    def test_free_resources_callback_with_none(self, caplog):
        """Test free_resources callback handles None gracefully."""
        from app import free_resources

        with caplog.at_level(logging.DEBUG):
            free_resources(None)

        log_text = caplog.text
        assert "No Sidekick instance to cleanup" in log_text

    @pytest.mark.skip(reason="Requires Gradio app setup and resources initialization")
    def test_free_resources_callback_logs_invocation(self, caplog):
        """Test free_resources callback logs when cleanup is called."""
        from app import free_resources
        from sidekick import Sidekick

        sidekick = Sidekick()
        sidekick.browser = AsyncMock()
        sidekick.playwright = AsyncMock()

        with caplog.at_level(logging.INFO):
            free_resources(sidekick)

        log_text = caplog.text
        assert "free_resources called" in log_text

    @pytest.mark.skip(reason="Requires Gradio app setup and resources initialization")
    @pytest.mark.asyncio
    async def test_cleanup_exception_handling(self, sidekick_with_mocked_resources, caplog):
        """Test that cleanup exceptions are caught and logged, not raised."""
        sidekick = sidekick_with_mocked_resources
        sidekick.browser.close = AsyncMock(side_effect=Exception("Unexpected error"))

        with caplog.at_level(logging.ERROR):
            # Should not raise
            await sidekick.cleanup()

        log_text = caplog.text
        assert "Failed to close browser" in log_text
        assert "Unexpected error" in log_text
