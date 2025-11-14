"""Pytest configuration and shared fixtures for Sidekick tests."""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def event_loop():
    """Create and provide event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def mock_browser():
    """Create a mock browser object."""
    browser = AsyncMock()
    browser.close = AsyncMock()
    browser.is_closed = MagicMock(return_value=False)
    return browser


@pytest.fixture
async def mock_playwright():
    """Create a mock playwright object."""
    playwright = AsyncMock()
    playwright.stop = AsyncMock()
    return playwright


@pytest.fixture
async def sidekick_with_mocked_resources():
    """Create a Sidekick instance with mocked browser/playwright resources.

    This fixture creates a Sidekick without actually launching a browser,
    which is much faster for unit testing.
    """
    from sidekick import Sidekick

    sidekick = Sidekick()

    # Mock the resources instead of actually creating them
    sidekick.browser = AsyncMock()
    sidekick.browser.close = AsyncMock()
    sidekick.playwright = AsyncMock()
    sidekick.playwright.stop = AsyncMock()
    sidekick.tools = []
    sidekick.worker_llm_with_tools = MagicMock()
    sidekick.evaluator_llm_with_output = MagicMock()
    sidekick.graph = MagicMock()

    yield sidekick

    # Cleanup: ensure mock cleanup is called
    # (in real tests, this should be tested separately)


@pytest.fixture
async def sidekick_without_resources():
    """Create a Sidekick instance with no resources allocated.

    Useful for testing cleanup when no resources were created.
    """
    from sidekick import Sidekick

    sidekick = Sidekick()
    # Don't set browser or playwright - test handles None case
    sidekick.tools = []
    sidekick.worker_llm_with_tools = MagicMock()
    sidekick.evaluator_llm_with_output = MagicMock()
    sidekick.graph = MagicMock()

    yield sidekick
