"""Tests for Sidekick resource cleanup (C2 Issue).

This module tests the async cleanup behavior to ensure:
1. Browser is properly closed
2. Playwright is properly stopped
3. Exceptions during cleanup are handled gracefully
4. Edge cases are handled (None resources, already closed, etc.)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import logging
from contextlib import asynccontextmanager


class TestCleanupHappyPath:
    """Tests for normal cleanup scenarios."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_browser_and_playwright(self, sidekick_with_mocked_resources):
        """Test cleanup properly closes both browser and playwright."""
        sidekick = sidekick_with_mocked_resources

        # Verify mocks are set up
        assert sidekick.browser is not None
        assert sidekick.playwright is not None
        assert sidekick.browser.close is not None
        assert sidekick.playwright.stop is not None

        # Run cleanup
        await sidekick.cleanup()

        # Verify both were called
        sidekick.browser.close.assert_called_once()
        sidekick.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_awaits_browser_close(self, sidekick_with_mocked_resources):
        """Test cleanup properly awaits browser.close()."""
        sidekick = sidekick_with_mocked_resources

        # Create a flag to verify await actually happened
        close_called = False

        async def mock_close():
            nonlocal close_called
            close_called = True

        sidekick.browser.close = AsyncMock(side_effect=mock_close)

        # Run cleanup
        await sidekick.cleanup()

        # Verify close was awaited (not just scheduled)
        assert close_called
        sidekick.browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_awaits_playwright_stop(self, sidekick_with_mocked_resources):
        """Test cleanup properly awaits playwright.stop()."""
        sidekick = sidekick_with_mocked_resources

        # Create a flag to verify await actually happened
        stop_called = False

        async def mock_stop():
            nonlocal stop_called
            stop_called = True

        sidekick.playwright.stop = AsyncMock(side_effect=mock_stop)

        # Run cleanup
        await sidekick.cleanup()

        # Verify stop was awaited (not just scheduled)
        assert stop_called
        sidekick.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_order(self, sidekick_with_mocked_resources):
        """Test cleanup closes browser before stopping playwright.

        Browser should close first, then playwright, to avoid race conditions.
        """
        sidekick = sidekick_with_mocked_resources

        call_order = []

        async def mock_close():
            call_order.append("browser_close")

        async def mock_stop():
            call_order.append("playwright_stop")

        sidekick.browser.close = AsyncMock(side_effect=mock_close)
        sidekick.playwright.stop = AsyncMock(side_effect=mock_stop)

        # Run cleanup
        await sidekick.cleanup()

        # Verify order: browser first, then playwright
        assert call_order == ["browser_close", "playwright_stop"]

    @pytest.mark.asyncio
    async def test_cleanup_logs_success(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup logs success messages."""
        sidekick = sidekick_with_mocked_resources

        with caplog.at_level(logging.INFO):
            await sidekick.cleanup()

        # Verify success logs are present
        log_text = caplog.text
        assert "Starting resource cleanup" in log_text
        assert "Browser closed successfully" in log_text
        assert "Playwright stopped successfully" in log_text
        assert "Cleanup completed" in log_text


class TestCleanupErrorHandling:
    """Tests for error handling during cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_handles_browser_close_exception(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup handles exceptions from browser.close() gracefully."""
        sidekick = sidekick_with_mocked_resources

        # Make browser.close() raise an exception
        sidekick.browser.close = AsyncMock(side_effect=RuntimeError("Browser crash"))

        with caplog.at_level(logging.ERROR):
            # Should not raise, but log the error
            await sidekick.cleanup()

        # Verify error was logged
        log_text = caplog.text
        assert "Failed to close browser" in log_text
        assert "RuntimeError" in log_text
        assert "Browser crash" in log_text

    @pytest.mark.asyncio
    async def test_cleanup_handles_playwright_stop_exception(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup handles exceptions from playwright.stop() gracefully."""
        sidekick = sidekick_with_mocked_resources

        # Make playwright.stop() raise an exception
        sidekick.playwright.stop = AsyncMock(side_effect=TimeoutError("Timeout stopping"))

        with caplog.at_level(logging.ERROR):
            # Should not raise, but log the error
            await sidekick.cleanup()

        # Verify error was logged
        log_text = caplog.text
        assert "Failed to stop playwright" in log_text
        assert "TimeoutError" in log_text
        assert "Timeout stopping" in log_text

    @pytest.mark.asyncio
    async def test_cleanup_continues_after_browser_error(self, sidekick_with_mocked_resources):
        """Test cleanup continues to playwright even if browser.close() fails."""
        sidekick = sidekick_with_mocked_resources

        # Make browser.close() fail
        sidekick.browser.close = AsyncMock(side_effect=RuntimeError("Browser error"))

        # Run cleanup - should still call playwright.stop()
        await sidekick.cleanup()

        # Verify playwright was still called despite browser error
        sidekick.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_multiple_exceptions(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup handles exceptions from both browser and playwright."""
        sidekick = sidekick_with_mocked_resources

        # Make both fail
        sidekick.browser.close = AsyncMock(side_effect=RuntimeError("Browser error"))
        sidekick.playwright.stop = AsyncMock(side_effect=RuntimeError("Playwright error"))

        with caplog.at_level(logging.ERROR):
            # Should not raise despite both failing
            await sidekick.cleanup()

        log_text = caplog.text
        # Both errors should be logged
        assert "Failed to close browser" in log_text
        assert "Failed to stop playwright" in log_text


class TestCleanupEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    @pytest.mark.asyncio
    async def test_cleanup_with_no_browser(self, sidekick_without_resources, caplog):
        """Test cleanup handles case where browser was never created."""
        sidekick = sidekick_without_resources

        with caplog.at_level(logging.DEBUG):
            # Should not raise
            await sidekick.cleanup()

        # Should exit early with debug log
        log_text = caplog.text
        assert "No browser to cleanup" in log_text

    @pytest.mark.asyncio
    async def test_cleanup_with_browser_but_no_playwright(self, sidekick_with_mocked_resources):
        """Test cleanup handles case where playwright is not set."""
        sidekick = sidekick_with_mocked_resources
        sidekick.playwright = None

        # Should not raise and should still close browser
        await sidekick.cleanup()

        sidekick.browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self, sidekick_with_mocked_resources):
        """Test cleanup can be called multiple times safely.

        This ensures cleanup is idempotent and can be called multiple times
        without causing issues (e.g., if called twice by accident).
        """
        sidekick = sidekick_with_mocked_resources

        # Call cleanup twice
        await sidekick.cleanup()
        await sidekick.cleanup()

        # Both resources should have been called twice (once per cleanup)
        assert sidekick.browser.close.call_count == 2
        assert sidekick.playwright.stop.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_preserves_sidekick_id(self, sidekick_with_mocked_resources):
        """Test cleanup doesn't modify sidekick instance ID during cleanup."""
        sidekick = sidekick_with_mocked_resources
        original_id = sidekick.sidekick_id

        await sidekick.cleanup()

        assert sidekick.sidekick_id == original_id

    @pytest.mark.asyncio
    async def test_cleanup_returns_none(self, sidekick_with_mocked_resources):
        """Test cleanup returns None as specified in return type."""
        sidekick = sidekick_with_mocked_resources

        result = await sidekick.cleanup()

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_with_already_closed_browser(self, sidekick_with_mocked_resources):
        """Test cleanup handles browser that's already closed."""
        sidekick = sidekick_with_mocked_resources

        # Simulate browser already being closed
        sidekick.browser.close = AsyncMock()
        sidekick.browser.is_closed = MagicMock(return_value=True)

        # Should handle gracefully without error
        await sidekick.cleanup()

        # close() should still be called (Playwright handles the idempotency)
        sidekick.browser.close.assert_called_once()


class TestCleanupLogging:
    """Tests for logging behavior during cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_logs_sidekick_id(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup logs include sidekick ID for tracing."""
        sidekick = sidekick_with_mocked_resources

        with caplog.at_level(logging.DEBUG):
            await sidekick.cleanup()

        log_text = caplog.text
        # All log messages should include the sidekick ID
        sidekick_id = sidekick.sidekick_id
        assert sidekick_id in log_text

    @pytest.mark.asyncio
    async def test_cleanup_logs_debug_messages(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup logs debug-level messages for detailed tracing."""
        sidekick = sidekick_with_mocked_resources

        with caplog.at_level(logging.DEBUG):
            await sidekick.cleanup()

        log_text = caplog.text
        # Should have debug messages for each step
        assert "Closing browser" in log_text
        assert "Stopping playwright" in log_text

    @pytest.mark.asyncio
    async def test_cleanup_logs_exceptions_with_traceback(self, sidekick_with_mocked_resources, caplog):
        """Test cleanup logs exceptions with full traceback for debugging."""
        sidekick = sidekick_with_mocked_resources
        sidekick.browser.close = AsyncMock(side_effect=ValueError("Test error"))

        with caplog.at_level(logging.ERROR):
            await sidekick.cleanup()

        # exc_info=True should include traceback
        # (pytest caplog captures this in exc_text)
        assert "ValueError" in caplog.text


class TestAsyncBehavior:
    """Tests to verify proper async/await behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_is_actually_async(self):
        """Test cleanup is truly async, not a hidden sync function."""
        import inspect
        from sidekick import Sidekick

        assert inspect.iscoroutinefunction(Sidekick.cleanup), \
            "cleanup() must be an async function"

    @pytest.mark.asyncio
    async def test_cleanup_returns_coroutine(self, sidekick_with_mocked_resources):
        """Test cleanup returns a coroutine that can be awaited."""
        sidekick = sidekick_with_mocked_resources

        # Call cleanup without await - should return a coroutine
        cleanup_coro = sidekick.cleanup()

        # Verify it's a coroutine
        import inspect
        assert inspect.iscoroutine(cleanup_coro)

        # Now await it
        await cleanup_coro

    @pytest.mark.asyncio
    async def test_cleanup_concurrent_calls(self, sidekick_with_mocked_resources):
        """Test behavior when cleanup is called concurrently.

        Note: This is an edge case that shouldn't happen in practice,
        but we test it to ensure no deadlocks or race conditions.
        """
        import asyncio
        sidekick = sidekick_with_mocked_resources

        # Call cleanup twice concurrently
        await asyncio.gather(
            sidekick.cleanup(),
            sidekick.cleanup()
        )

        # Both should have executed (even if redundant)
        assert sidekick.browser.close.call_count == 2
        assert sidekick.playwright.stop.call_count == 2
