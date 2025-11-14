# Sidekick Test Suite

This directory contains the automated test suite for the Sidekick AI Agent Framework.

## Overview

The test suite focuses on critical functionality and resource management, with initial emphasis on the C2 resource cleanup fix.

### Test Structure

```
tests/
├── conftest.py                      # Pytest configuration and shared fixtures
├── test_sidekick_cleanup.py         # Tests for resource cleanup (C2)
├── test_app.py                      # Tests for Gradio UI callbacks (future)
├── test_tools.py                    # Tests for tool integration (future)
└── README.md                        # This file
```

## Running Tests

### Install Test Dependencies

```bash
# Install test dependencies via UV
uv pip install -e ".[test]"

# Or use pip directly
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

### Run Specific Test Files

```bash
# Run cleanup tests only
pytest tests/test_sidekick_cleanup.py

# Run a specific test class
pytest tests/test_sidekick_cleanup.py::TestCleanupHappyPath

# Run a specific test
pytest tests/test_sidekick_cleanup.py::TestCleanupHappyPath::test_cleanup_closes_browser_and_playwright
```

### Run Tests by Marker

```bash
# Run only async tests
pytest -m asyncio

# Run only unit tests
pytest -m unit

# Run only cleanup-related tests
pytest -m cleanup

# Exclude slow tests
pytest -m "not slow"
```

## Test Coverage

### C2: Resource Cleanup Tests (`test_sidekick_cleanup.py`)

Comprehensive test suite with **50+ test cases** covering:

#### Happy Path Tests
- ✓ Proper browser and playwright closure
- ✓ Correct awaiting of async operations
- ✓ Correct cleanup order (browser first, then playwright)
- ✓ Success logging

#### Error Handling Tests
- ✓ Browser close exceptions
- ✓ Playwright stop exceptions
- ✓ Graceful error handling (cleanup continues after partial failure)
- ✓ Multiple simultaneous exceptions
- ✓ Exception logging with tracebacks

#### Edge Case Tests
- ✓ No resources allocated (cleanup with None)
- ✓ Browser without playwright
- ✓ Idempotent cleanup (can call multiple times)
- ✓ Already-closed resources
- ✓ Preserves sidekick instance ID

#### Logging Tests
- ✓ Logs include sidekick ID for tracing
- ✓ Debug-level messages for detailed tracing
- ✓ Error logging with full traceback

#### Async Behavior Tests
- ✓ Cleanup is actually async (not hidden sync)
- ✓ Returns proper coroutine
- ✓ Handles concurrent calls safely

#### Integration Tests
- ✓ Gradio callback with None
- ✓ Gradio callback logging
- ✓ Exception handling in callback

## Test Fixtures

### `conftest.py` Fixtures

#### `event_loop`
Creates a fresh event loop for each async test.

```python
@pytest.fixture
def event_loop():
    """Create and provide event loop for async tests."""
```

#### `mock_browser`
Creates a mocked browser object with async methods.

```python
@pytest.fixture
async def mock_browser():
    """Create a mock browser object."""
```

#### `mock_playwright`
Creates a mocked playwright object.

```python
@pytest.fixture
async def mock_playwright():
    """Create a mock playwright object."""
```

#### `sidekick_with_mocked_resources`
Creates a Sidekick instance with fully mocked browser/playwright resources. **Most commonly used.**

```python
@pytest.fixture
async def sidekick_with_mocked_resources():
    """Create a Sidekick instance with mocked browser/playwright resources."""
```

#### `sidekick_without_resources`
Creates a Sidekick instance without any resources (testing None case).

```python
@pytest.fixture
async def sidekick_without_resources():
    """Create a Sidekick instance with no resources allocated."""
```

## Test Patterns

### Testing Async Code

All async tests use `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_cleanup_closes_browser(self, sidekick_with_mocked_resources):
    sidekick = sidekick_with_mocked_resources
    await sidekick.cleanup()
    sidekick.browser.close.assert_called_once()
```

### Mocking Async Functions

Use `AsyncMock` from `unittest.mock`:

```python
from unittest.mock import AsyncMock

sidekick.browser.close = AsyncMock()
sidekick.playwright.stop = AsyncMock(side_effect=ValueError("Error"))
```

### Capturing Logs

Use pytest's `caplog`:

```python
with caplog.at_level(logging.ERROR):
    await sidekick.cleanup()

assert "Failed to close browser" in caplog.text
```

### Testing Execution Order

Use nonlocal variables to track call order:

```python
call_order = []

async def mock_close():
    call_order.append("browser_close")

sidekick.browser.close = AsyncMock(side_effect=mock_close)
await sidekick.cleanup()

assert call_order == ["browser_close", "playwright_stop"]
```

## Key Test Classes

### `TestCleanupHappyPath`
Tests normal cleanup scenarios where everything works correctly.

### `TestCleanupErrorHandling`
Tests exception handling during cleanup - ensures errors are caught, logged, and don't prevent other cleanup operations.

### `TestCleanupEdgeCases`
Tests unusual scenarios like None resources, already-closed browsers, idempotent calls.

### `TestCleanupLogging`
Verifies logging behavior for debugging and monitoring.

### `TestCleanupIntegration`
Tests integration with Gradio callbacks and broader system behavior.

### `TestAsyncBehavior`
Verifies proper async/await semantics and no hidden synchronous operations.

## Common Issues

### Issue: "Event loop already running"
**Cause:** Mixing async fixtures with sync test functions
**Solution:** Make test function async with `async def` and `@pytest.mark.asyncio`

### Issue: "RuntimeError: asyncio.run() cannot be called from a running event loop"
**Cause:** Trying to call `asyncio.run()` within an already-running loop
**Solution:** Use `await` directly in async tests, only use `asyncio.run()` for sync test setup

### Issue: Tests are slow
**Cause:** Actually launching browsers instead of mocking
**Solution:** Use `sidekick_with_mocked_resources` fixture which avoids real browser launches

### Issue: Mock not being called
**Cause:** Forgot to import or assign the mock
**Solution:** Verify mock is in `sidekick.cleanup()` method's scope

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention: `test_<functionality>_<expected_behavior>`
2. Add docstrings explaining what is being tested
3. Use appropriate fixtures from `conftest.py`
4. Group related tests in test classes
5. Add pytest markers (`@pytest.mark.asyncio`, etc.)
6. Consider edge cases and error conditions

Example:

```python
@pytest.mark.asyncio
async def test_new_feature_works_correctly(self, sidekick_with_mocked_resources):
    """Test that new feature works as expected.

    This test verifies that:
    1. Feature is called
    2. Feature returns expected value
    3. Side effects occur correctly
    """
    sidekick = sidekick_with_mocked_resources

    result = await sidekick.new_feature()

    assert result == expected_value
    sidekick.some_method.assert_called_once()
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```bash
# In CI/CD (e.g., GitHub Actions):
pip install -e ".[test]"
pytest --cov=src --cov-report=term-missing

# Or with coverage badge generation:
pytest --cov=src --cov-report=xml
```

## Coverage Goals

- **Phase 1 (Current):** 80%+ coverage of cleanup functionality
- **Phase 2:** 80%+ overall test coverage
- **Phase 3:** 90%+ test coverage with integration tests

## Future Test Files

- `test_app.py` - Tests for Gradio UI and callbacks
- `test_tools.py` - Tests for tool integration and execution
- `test_sidekick_worker.py` - Tests for worker node
- `test_sidekick_evaluator.py` - Tests for evaluator node
- `test_sidekick_tools.py` - Tests for tool registration and binding

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## Contributing to Tests

When submitting changes to the codebase:

1. Update or add tests for modified/new functionality
2. Run `pytest --cov` to verify coverage
3. Fix any failing tests before submitting PR
4. Add docstrings to new test functions/classes

Thank you for maintaining high test quality!
