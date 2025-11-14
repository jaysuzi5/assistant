"""LLM invocation utilities with error handling and retry logic.

This module provides robust error handling and retry mechanisms for LLM API calls.
It handles common OpenAI API errors and implements exponential backoff for retries.

Handled errors:
- RateLimitError: API quota exceeded (retry with backoff)
- APIConnectionError: Network issues (retry with backoff)
- APIError: Generic OpenAI API errors (retry with backoff)
- AuthenticationError: Invalid API credentials (fail fast, don't retry)
- ValidationError: Invalid parameters (fail fast, don't retry)

Retry strategy:
- Maximum 3 retries (configurable)
- Exponential backoff: 1s, 2s, 4s
- Jitter added to prevent thundering herd
"""

import logging
import asyncio
import random
from typing import Any, TypeVar, Callable, Awaitable, Optional
from functools import wraps
from langchain_core.exceptions import (
    LangChainException,
)

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")


class LLMInvocationError(Exception):
    """Raised when LLM invocation fails after all retries."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        attempt: int = 1,
        max_attempts: int = 3,
    ):
        """Initialize LLMInvocationError.

        Args:
            message: Description of the error
            original_error: The original exception that caused the error
            attempt: Which attempt this occurred on
            max_attempts: Total number of attempts made
        """
        self.original_error = original_error
        self.attempt = attempt
        self.max_attempts = max_attempts
        full_message = (
            f"{message} (attempt {attempt}/{max_attempts})"
        )
        if original_error:
            full_message += f": {type(original_error).__name__}: {original_error}"
        super().__init__(full_message)


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should be retried.

    Args:
        error: The exception that occurred

    Returns:
        True if the error is retryable, False otherwise
    """
    # Import here to avoid circular dependencies
    try:
        from openai import RateLimitError, APIConnectionError, APIError

        # Retryable errors
        if isinstance(error, (RateLimitError, APIConnectionError, APIError)):
            return True
    except ImportError:
        # If openai is not installed, try to identify by class name
        error_name = type(error).__name__
        if error_name in ("RateLimitError", "APIConnectionError", "APIError"):
            return True

    return False


def is_fatal_error(error: Exception) -> bool:
    """Determine if an error is fatal and should not be retried.

    Args:
        error: The exception that occurred

    Returns:
        True if the error is fatal, False otherwise
    """
    # Import here to avoid circular dependencies
    try:
        from openai import AuthenticationError

        # Fatal errors - don't retry
        if isinstance(error, AuthenticationError):
            return True
    except ImportError:
        # If openai is not installed, try to identify by class name
        error_name = type(error).__name__
        if error_name == "AuthenticationError":
            return True

    # Also check for validation errors
    if isinstance(error, (ValueError, TypeError)):
        return True

    return False


async def invoke_with_retry(
    invocation_func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    operation_name: str = "LLM invocation",
) -> T:
    """Invoke an async function with automatic retry and backoff.

    This function wraps an async callable and retries it with exponential backoff
    if it fails with a retryable error. Fatal errors are not retried.

    Args:
        invocation_func: Async function to invoke
        max_retries: Maximum number of retries (default 3)
        initial_delay: Initial delay between retries in seconds (default 1.0)
        max_delay: Maximum delay between retries in seconds (default 60.0)
        operation_name: Name of operation for logging (default "LLM invocation")

    Returns:
        Result of invocation_func if successful

    Raises:
        LLMInvocationError: If all retries are exhausted or a fatal error occurs
    """
    delay = initial_delay
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"{operation_name}: Attempt {attempt}/{max_retries}")
            result = await invocation_func()
            if attempt > 1:
                logger.info(f"{operation_name}: Succeeded on attempt {attempt}")
            return result
        except Exception as e:
            last_error = e

            # Check if error is fatal
            if is_fatal_error(e):
                logger.error(
                    f"{operation_name}: Fatal error on attempt {attempt}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed with fatal error",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Check if error is retryable
            if not is_retryable_error(e):
                logger.error(
                    f"{operation_name}: Non-retryable error on attempt {attempt}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed with non-retryable error",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Log retryable error
            logger.warning(
                f"{operation_name}: Retryable error on attempt {attempt}/{max_retries}: "
                f"{type(e).__name__}: {e}",
            )

            # Don't retry if this was the last attempt
            if attempt >= max_retries:
                logger.error(
                    f"{operation_name}: All {max_retries} retries exhausted",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed after {max_retries} attempts",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Calculate delay with jitter
            jitter = random.uniform(0, 0.1 * delay)
            wait_time = min(delay + jitter, max_delay)
            logger.info(
                f"{operation_name}: Retrying in {wait_time:.2f}s "
                f"(attempt {attempt}/{max_retries})"
            )

            # Wait before retrying
            await asyncio.sleep(wait_time)

            # Exponential backoff
            delay = min(delay * 2, max_delay)


def invoke_with_retry_sync(
    invocation_func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    operation_name: str = "LLM invocation",
) -> T:
    """Invoke a function with automatic retry and backoff (synchronous version).

    This function wraps a callable and retries it with exponential backoff
    if it fails with a retryable error. Fatal errors are not retried.

    Args:
        invocation_func: Function to invoke
        max_retries: Maximum number of retries (default 3)
        initial_delay: Initial delay between retries in seconds (default 1.0)
        max_delay: Maximum delay between retries in seconds (default 60.0)
        operation_name: Name of operation for logging (default "LLM invocation")

    Returns:
        Result of invocation_func if successful

    Raises:
        LLMInvocationError: If all retries are exhausted or a fatal error occurs
    """
    delay = initial_delay
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"{operation_name}: Attempt {attempt}/{max_retries}")
            result = invocation_func()
            if attempt > 1:
                logger.info(f"{operation_name}: Succeeded on attempt {attempt}")
            return result
        except Exception as e:
            last_error = e

            # Check if error is fatal
            if is_fatal_error(e):
                logger.error(
                    f"{operation_name}: Fatal error on attempt {attempt}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed with fatal error",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Check if error is retryable
            if not is_retryable_error(e):
                logger.error(
                    f"{operation_name}: Non-retryable error on attempt {attempt}: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed with non-retryable error",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Log retryable error
            logger.warning(
                f"{operation_name}: Retryable error on attempt {attempt}/{max_retries}: "
                f"{type(e).__name__}: {e}",
            )

            # Don't retry if this was the last attempt
            if attempt >= max_retries:
                logger.error(
                    f"{operation_name}: All {max_retries} retries exhausted",
                    exc_info=True,
                )
                raise LLMInvocationError(
                    f"{operation_name} failed after {max_retries} attempts",
                    original_error=e,
                    attempt=attempt,
                    max_attempts=max_retries,
                ) from e

            # Calculate delay with jitter
            jitter = random.uniform(0, 0.1 * delay)
            wait_time = min(delay + jitter, max_delay)
            logger.info(
                f"{operation_name}: Retrying in {wait_time:.2f}s "
                f"(attempt {attempt}/{max_retries})"
            )

            # Wait before retrying (using asyncio.run to avoid blocking the event loop)
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use asyncio.sleep directly
                # This function should be called from sync context
                import time
                time.sleep(wait_time)
            except RuntimeError:
                # Not in async context
                import time
                time.sleep(wait_time)

            # Exponential backoff
            delay = min(delay * 2, max_delay)
