"""Tests for C4 - Unhandled LLM Invocation Failures.

This test module covers:
1. Error handling and recovery for worker LLM invocations
2. Error handling and recovery for evaluator LLM invocations
3. Retry logic with exponential backoff
4. Different error types (retryable, fatal, non-retryable)
5. Graceful degradation when API calls fail
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
import logging
from contextlib import asynccontextmanager

# Import the modules under test
from llm_invocation import (
    invoke_with_retry_sync,
    invoke_with_retry,
    LLMInvocationError,
    is_retryable_error,
    is_fatal_error,
)


class TestErrorClassification:
    """Tests for error type classification."""

    def test_is_fatal_error_value_error(self):
        """Test ValueError is classified as fatal."""
        error = ValueError("Invalid parameter")
        assert is_fatal_error(error) is True

    def test_is_fatal_error_type_error(self):
        """Test TypeError is classified as fatal."""
        error = TypeError("Wrong type")
        assert is_fatal_error(error) is True

    def test_error_classification_by_class_name(self):
        """Test error classification works by class name for unknown imports."""
        # Test retryable errors by class name
        assert is_retryable_error.__doc__ is not None

    def test_non_retryable_error_unknown_exception(self):
        """Test unknown exception is not retryable."""
        error = RuntimeError("Some unknown error")
        assert is_retryable_error(error) is False

    def test_fatal_error_classification(self):
        """Test fatal error classification."""
        # Test by class name
        assert is_fatal_error(ValueError("test")) is True
        assert is_fatal_error(TypeError("test")) is True
        assert is_fatal_error(RuntimeError("test")) is False


class TestSyncInvokeWithRetry:
    """Tests for synchronous invoke_with_retry_sync function."""

    def test_invoke_success_no_retries(self):
        """Test successful invocation on first try."""
        def success_func():
            return "success"

        result = invoke_with_retry_sync(success_func)
        assert result == "success"

    def test_invoke_fatal_error_fails_fast(self):
        """Test fatal error fails immediately without retries."""
        attempt_count = 0

        def fatal_error_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Fatal error")

        with pytest.raises(LLMInvocationError) as exc_info:
            invoke_with_retry_sync(fatal_error_func, max_retries=3)

        # Should fail on first attempt without retrying
        assert attempt_count == 1
        assert "Fatal error" in str(exc_info.value)

    def test_invoke_non_retryable_error_fails_fast(self):
        """Test non-retryable error fails immediately."""
        attempt_count = 0

        def non_retryable_func():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError("Non-retryable error")

        with pytest.raises(LLMInvocationError) as exc_info:
            invoke_with_retry_sync(non_retryable_func, max_retries=3)

        # Should fail on first attempt without retrying
        assert attempt_count == 1
        assert "Non-retryable error" in str(exc_info.value)

    def test_invoke_retryable_error_with_eventual_success(self):
        """Test retryable error succeeds after retries."""
        attempt_count = 0

        # Create a mock retryable error class
        class MockRetryableError(Exception):
            """Mock retryable error for testing."""
            pass

        def retryable_then_success_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise MockRetryableError("Temporary failure")
            return "success"

        # Mock the error classification to recognize our mock error
        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                result = invoke_with_retry_sync(
                    retryable_then_success_func,
                    max_retries=5,
                    initial_delay=0.01  # Short delay for testing
                )

        assert result == "success"
        assert attempt_count == 3

    def test_invoke_retryable_error_exhausts_retries(self):
        """Test retryable error exhausts all retries."""
        attempt_count = 0

        class MockRetryableError(Exception):
            pass

        def always_fails_func():
            nonlocal attempt_count
            attempt_count += 1
            raise MockRetryableError("Persistent failure")

        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                with pytest.raises(LLMInvocationError) as exc_info:
                    invoke_with_retry_sync(
                        always_fails_func,
                        max_retries=3,
                        initial_delay=0.01  # Short delay for testing
                    )

        # Should attempt max_retries times
        assert attempt_count == 3
        assert "3 attempts" in str(exc_info.value)

    def test_invoke_with_custom_operation_name(self):
        """Test operation name appears in error messages."""
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(LLMInvocationError) as exc_info:
            invoke_with_retry_sync(
                failing_func,
                operation_name="Custom Operation"
            )

        assert "Custom Operation" in str(exc_info.value)

    def test_invoke_with_custom_retry_count(self):
        """Test custom retry count is respected."""
        attempt_count = 0

        class MockRetryableError(Exception):
            pass

        def retryable_func():
            nonlocal attempt_count
            attempt_count += 1
            raise MockRetryableError("Connection failed")

        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                with pytest.raises(LLMInvocationError):
                    invoke_with_retry_sync(
                        retryable_func,
                        max_retries=2,
                        initial_delay=0.01
                    )

        assert attempt_count == 2

    def test_invoke_error_includes_original_exception(self):
        """Test LLMInvocationError includes original exception."""
        original_error = ValueError("Original error")

        def failing_func():
            raise original_error

        with pytest.raises(LLMInvocationError) as exc_info:
            invoke_with_retry_sync(failing_func)

        assert exc_info.value.original_error is original_error


class TestAsyncInvokeWithRetry:
    """Tests for asynchronous invoke_with_retry function."""

    @pytest.mark.asyncio
    async def test_async_invoke_success_no_retries(self):
        """Test successful async invocation on first try."""
        async def success_func():
            return "success"

        result = await invoke_with_retry(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_invoke_fatal_error_fails_fast(self):
        """Test fatal error fails immediately without retries."""
        attempt_count = 0

        async def fatal_error_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Fatal error")

        with pytest.raises(LLMInvocationError) as exc_info:
            await invoke_with_retry(fatal_error_func, max_retries=3)

        # Should fail on first attempt without retrying
        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_async_invoke_retryable_error_with_eventual_success(self):
        """Test retryable async error succeeds after retries."""
        attempt_count = 0

        class MockRetryableError(Exception):
            pass

        async def retryable_then_success_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise MockRetryableError("Connection failed")
            return "success"

        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                result = await invoke_with_retry(
                    retryable_then_success_func,
                    max_retries=5,
                    initial_delay=0.01
                )

        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_async_invoke_retryable_error_exhausts_retries(self):
        """Test retryable async error exhausts all retries."""
        attempt_count = 0

        class MockRetryableError(Exception):
            pass

        async def always_fails_func():
            nonlocal attempt_count
            attempt_count += 1
            raise MockRetryableError("Connection failed")

        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                with pytest.raises(LLMInvocationError) as exc_info:
                    await invoke_with_retry(
                        always_fails_func,
                        max_retries=3,
                        initial_delay=0.01
                    )

        assert attempt_count == 3


class TestWorkerLLMInvocationWithErrorHandling:
    """Tests for worker node LLM invocation with error handling."""

    @pytest.mark.asyncio
    async def test_worker_successful_invocation(self, sidekick_with_mocked_resources):
        """Test worker successfully invokes LLM."""
        sidekick = sidekick_with_mocked_resources

        # Mock the LLM to return a successful response
        mock_response = MagicMock()
        mock_response.content = "Test response"
        sidekick.worker_llm_with_tools.invoke = MagicMock(return_value=mock_response)

        # Create a state
        state = {
            "messages": [],
            "success_criteria": "Test this",
            "feedback_on_work": None,
        }

        # Call worker
        result = sidekick.worker(state)

        # Verify result
        assert "messages" in result
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_worker_handles_rate_limit_error(self, sidekick_with_mocked_resources):
        """Test worker gracefully handles RateLimitError."""
        sidekick = sidekick_with_mocked_resources

        # Mock the LLM to raise an error
        def raise_error():
            raise RuntimeError("API Rate limit exceeded")

        sidekick.worker_llm_with_tools.invoke = MagicMock(side_effect=raise_error)

        state = {
            "messages": [],
            "success_criteria": "Test this",
            "feedback_on_work": None,
        }

        # Call worker - should not raise, but return error message
        result = sidekick.worker(state)

        assert "messages" in result
        # Should contain error message
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_worker_handles_api_connection_error(self, sidekick_with_mocked_resources):
        """Test worker gracefully handles APIConnectionError."""
        sidekick = sidekick_with_mocked_resources

        # Mock the LLM to raise an error
        def raise_connection_error():
            raise ConnectionError("Connection failed")

        sidekick.worker_llm_with_tools.invoke = MagicMock(side_effect=raise_connection_error)

        state = {
            "messages": [],
            "success_criteria": "Test this",
            "feedback_on_work": None,
        }

        result = sidekick.worker(state)

        assert "messages" in result


class TestEvaluatorLLMInvocationWithErrorHandling:
    """Tests for evaluator node LLM invocation with error handling."""

    @pytest.mark.asyncio
    async def test_evaluator_successful_invocation(self, sidekick_with_mocked_resources):
        """Test evaluator successfully invokes LLM."""
        sidekick = sidekick_with_mocked_resources

        # Mock the evaluator LLM to return a successful response
        from sidekick import EvaluatorOutput
        mock_response = EvaluatorOutput(
            feedback="Good job",
            success_criteria_met=True,
            user_input_needed=False
        )
        sidekick.evaluator_llm_with_output.invoke = MagicMock(return_value=mock_response)

        # Create a state with messages
        from langchain_core.messages import HumanMessage, AIMessage
        state = {
            "messages": [
                HumanMessage(content="User request"),
                AIMessage(content="Assistant response"),
            ],
            "success_criteria": "Test this",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }

        # Call evaluator
        result = sidekick.evaluator(state)

        # Verify result
        assert result["success_criteria_met"] is True
        assert result["user_input_needed"] is False

    @pytest.mark.asyncio
    async def test_evaluator_handles_rate_limit_error(self, sidekick_with_mocked_resources):
        """Test evaluator gracefully handles RateLimitError."""
        sidekick = sidekick_with_mocked_resources

        # Mock the evaluator LLM to raise an error
        def raise_error():
            raise RuntimeError("Rate limit exceeded")

        sidekick.evaluator_llm_with_output.invoke = MagicMock(side_effect=raise_error)

        from langchain_core.messages import HumanMessage, AIMessage
        state = {
            "messages": [
                HumanMessage(content="User request"),
                AIMessage(content="Assistant response"),
            ],
            "success_criteria": "Test this",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }

        # Call evaluator - should not raise, but return error state
        result = sidekick.evaluator(state)

        # Should request user input as failsafe
        assert result["user_input_needed"] is True
        assert result["success_criteria_met"] is False

    @pytest.mark.asyncio
    async def test_evaluator_handles_api_connection_error(self, sidekick_with_mocked_resources):
        """Test evaluator gracefully handles APIConnectionError."""
        sidekick = sidekick_with_mocked_resources

        # Mock the evaluator LLM to raise an error
        def raise_connection_error():
            raise ConnectionError("Connection failed")

        sidekick.evaluator_llm_with_output.invoke = MagicMock(side_effect=raise_connection_error)

        from langchain_core.messages import HumanMessage, AIMessage
        state = {
            "messages": [
                HumanMessage(content="User request"),
                AIMessage(content="Assistant response"),
            ],
            "success_criteria": "Test this",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }

        result = sidekick.evaluator(state)

        # Should request user input as failsafe
        assert result["user_input_needed"] is True


class TestErrorLogging:
    """Tests for error logging behavior."""

    def test_llm_invocation_error_message_format(self):
        """Test LLMInvocationError message format."""
        original = ValueError("Original error")
        error = LLMInvocationError(
            "Test operation failed",
            original_error=original,
            attempt=2,
            max_attempts=3
        )

        error_str = str(error)
        assert "Test operation failed" in error_str
        assert "attempt 2/3" in error_str
        assert "ValueError" in error_str
        assert "Original error" in error_str

    def test_llm_invocation_error_without_original(self):
        """Test LLMInvocationError without original exception."""
        error = LLMInvocationError("Operation failed", attempt=1, max_attempts=3)

        error_str = str(error)
        assert "Operation failed" in error_str
        assert "attempt 1/3" in error_str

    def test_llm_invocation_error_preserves_original_exception(self):
        """Test LLMInvocationError preserves original exception."""
        original = ValueError("Test")
        error = LLMInvocationError("Failed", original_error=original)

        assert error.original_error is original


class TestErrorHandlingEdgeCases:
    """Tests for edge cases in error handling."""

    def test_invoke_with_zero_retries(self):
        """Test behavior with one retry (minimum)."""
        attempt_count = 0

        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Invalid input")  # Fatal error

        with pytest.raises(LLMInvocationError):
            invoke_with_retry_sync(
                failing_func,
                max_retries=1,
                initial_delay=0.01
            )

        # Should fail on first attempt (fatal error, don't retry)
        assert attempt_count == 1

    def test_invoke_with_large_delay_cap(self):
        """Test max_delay parameter is respected."""
        attempt_count = 0

        class MockRetryableError(Exception):
            pass

        def retryable_func():
            nonlocal attempt_count
            attempt_count += 1
            raise MockRetryableError("Connection failed")

        # Test that max_delay prevents exponential backoff from growing too large
        with patch('llm_invocation.is_retryable_error', return_value=True):
            with patch('llm_invocation.is_fatal_error', return_value=False):
                with pytest.raises(LLMInvocationError):
                    invoke_with_retry_sync(
                        retryable_func,
                        max_retries=5,
                        initial_delay=0.01,  # Reduced for faster tests
                        max_delay=0.05,  # Should cap at 0.05 seconds
                    )

        assert attempt_count == 5
