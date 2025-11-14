# H3: Missing Timeout Configuration - Technical Details

**Date:** November 14, 2025
**Topic:** Implementation architecture and technical decisions

---

## Architecture & Design

### 1. Configuration Module Design

**File:** `src/config.py`

#### Module Structure

```python
┌─────────────────────────────────┐
│ src/config.py                   │
├─────────────────────────────────┤
│ 1. Imports (os, typing)         │
│ 2. Timeout Constants (4)        │
│ 3. Validation Function          │
│ 4. Module-level Validation Call │
└─────────────────────────────────┘
```

#### Timeout Constants

```python
# Configurable via environment variables with fallback defaults
DEFAULT_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))
PUSHOVER_REQUEST_TIMEOUT = float(os.getenv("PUSHOVER_REQUEST_TIMEOUT", "5.0"))
SERPER_REQUEST_TIMEOUT = float(os.getenv("SERPER_REQUEST_TIMEOUT", "15.0"))
WIKIPEDIA_REQUEST_TIMEOUT = float(os.getenv("WIKIPEDIA_REQUEST_TIMEOUT", "10.0"))
```

**Design Rationale:**

1. **Float values:** Allows fractional seconds (e.g., 5.5s for more precision)
2. **Environment override:** Follows 12-factor app methodology
3. **Default values:** Hardcoded defaults work out-of-the-box
4. **Separate per-service:** Different APIs have different characteristics

#### Validation Function

```python
def validate_timeout_config() -> None:
    """Validate that all timeout values are positive."""
    for name, value in timeouts.items():
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
```

**Benefits:**
- Catches configuration errors early (at module import time)
- Provides clear error messages
- Prevents silent bugs from invalid configuration

### 2. Push Function Enhancement

**File:** `src/sidekick_tools.py`

#### Before vs After

**BEFORE:**
```python
def push(text: str) -> str:
    requests.post(pushover_url, data={"token": ..., "user": ..., "message": text})
    return "success"
```

**Problems:**
- No timeout → indefinite hang on network issues
- No error handling → exceptions propagate unhandled
- No logging → difficult to debug failures

**AFTER:**
```python
def push(text: str) -> str:
    """Send a push notification to the user.

    Args:
        text: Message content to send

    Returns:
        "success" if notification sent, otherwise error message

    Raises:
        requests.exceptions.Timeout: If the request times out
        requests.exceptions.RequestException: If the request fails
    """
    try:
        requests.post(
            pushover_url,
            data={"token": pushover_token, "user": pushover_user, "message": text},
            timeout=PUSHOVER_REQUEST_TIMEOUT
        )
        return "success"
    except requests.exceptions.Timeout:
        logger.error(f"Push notification timeout after {PUSHOVER_REQUEST_TIMEOUT}s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Push notification failed: {e}")
        raise
```

**Improvements:**
1. ✅ Timeout parameter prevents indefinite hangs
2. ✅ Exception handling provides observability
3. ✅ Error logging aids debugging
4. ✅ Docstring documents behavior
5. ✅ Exceptions are re-raised for caller handling

#### Exception Hierarchy

```
requests.exceptions.RequestException (base)
├── requests.exceptions.Timeout (≤ 5 seconds timeout)
├── requests.exceptions.ConnectionError
├── requests.exceptions.HTTPError
└── ... (other subtypes)
```

**Handling Strategy:**
1. Catch `Timeout` first (most common, fastest services)
2. Catch `RequestException` for all other network errors
3. Log each separately for debugging
4. Re-raise both (caller decides recovery strategy)

### 3. Integration Points

#### How timeout config flows through system

```
┌──────────────────┐
│ src/config.py    │ ← Configuration module
└────────┬─────────┘
         │
         │ imports
         │
         v
┌────────────────────┐
│ sidekick_tools.py  │ ← Tools module
└────────┬───────────┘
         │
         │ uses PUSHOVER_REQUEST_TIMEOUT
         │
         v
┌────────────────────┐
│ push() function    │ ← Push notifications
└────────┬───────────┘
         │
         │ makes requests.post() call
         │
         v
┌────────────────────┐
│ External API       │ ← Pushover service
│ (Pushover)         │
└────────────────────┘
```

**Call Flow:**
```python
# 1. Configuration loaded
from config import PUSHOVER_REQUEST_TIMEOUT  # 5.0 seconds

# 2. Function invoked
sidekick_tools.push("Test message")

# 3. Network request with timeout
requests.post(url, data={...}, timeout=5.0)

# 4a. Success path
Response received within 5s → returns "success"

# 4b. Timeout path
No response within 5s → raises Timeout exception

# 4c. Other error path
Connection error, etc. → raises RequestException
```

### 4. Timeout Values & Rationale

#### Pushover (5.0 seconds)

**Why 5 seconds?**
- Pushover is a simple HTTP API
- Should respond immediately if online
- 5s is generous for production systems
- Allows for 1-2 retries within reasonable timeout

**When it might fail:**
- Pushover service is down
- Network connectivity is broken
- Extremely high latency (unlikely for push API)

#### Default (10.0 seconds)

**Why 10 seconds?**
- General-purpose timeout for most APIs
- Balances responsiveness with reliability
- Standard for many production systems
- Covers most typical network jitter

#### Serper/Web Search (15.0 seconds)

**Why 15 seconds?**
- Search requires remote indexing
- May query multiple sources
- Network hops to search infrastructure
- Higher latency acceptable for search operations

#### Wikipedia (10.0 seconds)

**Why 10 seconds?**
- Wikipedia API is typically fast
- Same as default (good baseline)
- Full encyclopedia available from single source
- Network distance might be farther than local APIs

### 5. Configuration Flexibility

#### Environment Variable Mapping

```
Environment Variable          →  Python Constant
─────────────────────────────────────────────────────
REQUEST_TIMEOUT               →  DEFAULT_REQUEST_TIMEOUT
PUSHOVER_REQUEST_TIMEOUT      →  PUSHOVER_REQUEST_TIMEOUT
SERPER_REQUEST_TIMEOUT        →  SERPER_REQUEST_TIMEOUT
WIKIPEDIA_REQUEST_TIMEOUT     →  WIKIPEDIA_REQUEST_TIMEOUT
```

#### Example Configurations

**Local Development (fast internet):**
```bash
REQUEST_TIMEOUT=5.0
PUSHOVER_REQUEST_TIMEOUT=3.0
SERPER_REQUEST_TIMEOUT=10.0
WIKIPEDIA_REQUEST_TIMEOUT=5.0
```

**Slow Network (3G/Mobile):**
```bash
REQUEST_TIMEOUT=20.0
PUSHOVER_REQUEST_TIMEOUT=10.0
SERPER_REQUEST_TIMEOUT=30.0
WIKIPEDIA_REQUEST_TIMEOUT=20.0
```

**Production (optimized):**
```bash
REQUEST_TIMEOUT=12.0
PUSHOVER_REQUEST_TIMEOUT=4.0
SERPER_REQUEST_TIMEOUT=18.0
WIKIPEDIA_REQUEST_TIMEOUT=12.0
```

### 6. Error Handling Flow

#### Timeout Error Path

```
requests.post(..., timeout=5.0)
    ↓
[Wait up to 5 seconds for response]
    ↓
[No response within 5 seconds]
    ↓
requests.exceptions.Timeout (raised)
    ↓
except requests.exceptions.Timeout:
    logger.error("Push notification timeout after 5.0s")
    raise  # Caller must handle
    ↓
Caller's error handling or application fails
```

#### Request Error Path

```
requests.post(..., timeout=5.0)
    ↓
[Connection failed, DNS error, etc.]
    ↓
requests.exceptions.RequestException (raised)
    ↓
except requests.exceptions.RequestException as e:
    logger.error(f"Push notification failed: {e}")
    raise  # Caller must handle
    ↓
Caller's error handling or application fails
```

#### Success Path

```
requests.post(..., timeout=5.0)
    ↓
[Response received within timeout]
    ↓
return "success"
    ↓
Caller receives "success" string
```

### 7. Testing Strategy

#### Unit Test Categories

**1. Configuration Tests**
```python
test_default_request_timeout_is_positive()
test_pushover_request_timeout_is_positive()
# ... etc (6 tests)
```

**2. Validation Tests**
```python
test_validate_timeout_config_passes_with_defaults()
test_validate_timeout_config_rejects_zero()
test_validate_timeout_config_rejects_negative()
```

**3. Function Behavior Tests**
```python
test_push_uses_pushover_timeout()  # Verify timeout parameter
test_push_sends_correct_data()     # Verify payload
test_push_returns_success()        # Verify return value
```

**4. Exception Handling Tests**
```python
test_push_handles_timeout_exception()
test_push_logs_timeout_error()
test_push_handles_request_exception()
test_push_logs_request_error()
```

**5. Environment Variable Tests**
```python
test_pushover_timeout_from_env()
test_default_timeout_from_env()
# ... etc (4 tests)
```

#### Mocking Strategy

**What to mock:**
- `requests.post()` - Don't make real HTTP calls
- `logger` - Verify logging calls
- Environment variables (via patching)

**What not to mock:**
- `config` module itself - Test real configuration loading
- Timeout constants - Test actual values

### 8. Backward Compatibility

**Non-breaking changes:**

1. **New module (config.py)**
   - No existing code depends on this
   - Safe to add

2. **Updated push function**
   - Same function signature
   - Same return type
   - Same exception behavior (exceptions still raised)
   - Existing code continues to work

3. **New timeout parameter**
   - Internal implementation detail
   - Not part of public API
   - Existing callers don't need changes

**Safe to deploy:**
- ✅ Existing code unchanged
- ✅ New features opt-in
- ✅ No breaking changes
- ✅ Can gradually migrate other functions

### 9. Performance Implications

#### Memory
- Config module: ~1KB (4 float variables + function)
- No runtime overhead
- Zero memory accumulation

#### CPU
- Timeout checking: OS-level (negligible cost)
- Validation: One-time at import (not in hot path)
- Logging: Minor cost (same as any error logging)

#### Network
- Timeouts prevent resource exhaustion
- Faster failure → faster retry capability
- Reduces hanging connections

**Overall:** Performance improvement (prevents hangs)

### 10. Monitoring & Observability

#### Log Messages

**Timeout:**
```
ERROR: Push notification timeout after 5.0s
```

**Request Error:**
```
ERROR: Push notification failed: ConnectionError(...)
```

#### Metrics to Track

```python
# In future iterations:
- timeout_count (per service)
- timeout_duration (actual time before timeout)
- retry_count
- success_rate
```

#### Debugging with Logs

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs will show:
# ERROR: Push notification timeout after 5.0s
# ^ Indicates API was slow or down
#
# ERROR: Push notification failed: ConnectionError(...)
# ^ Indicates network is broken
```

---

## Code Quality

### Type Hints

```python
# Configuration values
DEFAULT_REQUEST_TIMEOUT: float = ...

# Function signature
def push(text: str) -> str:

# Exception types documented
Raises:
    requests.exceptions.Timeout: If the request times out
    requests.exceptions.RequestException: If the request fails
```

### Docstring Quality

All functions have comprehensive docstrings with:
- Description of purpose
- Args section (parameter names + types + descriptions)
- Returns section (type + description)
- Raises section (exception types + when they occur)

### Error Handling Quality

```python
# Specific exception catching (not generic Exception)
except requests.exceptions.Timeout:
    ...
except requests.exceptions.RequestException:
    ...

# Each exception logged with context
logger.error(f"Push notification timeout after {PUSHOVER_REQUEST_TIMEOUT}s")

# Re-raise for caller to handle
raise
```

---

## Future Enhancement Points

### 1. Extend to Other Services

```python
# In future PR:
from config import WIKIPEDIA_REQUEST_TIMEOUT

# Update wikipedia_tool wrapper
requests.get(url, timeout=WIKIPEDIA_REQUEST_TIMEOUT)
```

### 2. Add Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def push(text: str) -> str:
    # ... existing implementation
```

### 3. Add Metrics Collection

```python
from prometheus_client import Counter, Histogram

timeout_counter = Counter('push_timeouts', 'Push notification timeouts')
request_timer = Histogram('push_duration', 'Push notification duration')

@request_timer.time()
def push(text: str) -> str:
    try:
        # ... existing implementation
    except requests.exceptions.Timeout:
        timeout_counter.inc()
        raise
```

### 4. Support Circuit Breaker Pattern

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def push(text: str) -> str:
    # ... existing implementation
```

---

## References

### Python Requests Documentation
- [Timeouts](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts)
- [Exception Handling](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts)

### Environment Variables
- [12 Factor App - Config](https://12factor.net/config)
- [Python os.getenv()](https://docs.python.org/3/library/os.html#os.getenv)

### Testing Patterns
- [unittest.mock.patch](https://docs.python.org/3/library/unittest.mock.html#patch)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)

---

**Document Generated:** 2025-11-14
**Status:** Technical documentation complete
