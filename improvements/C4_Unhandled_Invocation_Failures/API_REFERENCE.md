# LLM Invocation API Reference

Complete API documentation for the `llm_invocation` module providing error handling and retry logic for LLM API calls.

## Module: `src/llm_invocation.py`

### Classes

#### `LLMInvocationError(Exception)`

Custom exception raised when LLM invocation fails after all retry attempts.

**Attributes:**
- `message` (str): Description of the failure
- `original_error` (Optional[Exception]): The underlying exception that caused the failure
- `attempt` (int): Which attempt this occurred on (1-indexed)
- `max_attempts` (int): Total number of attempts made

**Constructor:**
```python
LLMInvocationError(
    message: str,
    original_error: Optional[Exception] = None,
    attempt: int = 1,
    max_attempts: int = 3
)
```

**Example:**
```python
try:
    result = invoke_with_retry_sync(llm_call, max_retries=3)
except LLMInvocationError as e:
    print(f"Failed on attempt {e.attempt}/{e.max_attempts}")
    print(f"Original error: {type(e.original_error).__name__}")
    print(f"Full message: {str(e)}")
```

### Functions

#### `is_retryable_error(error: Exception) -> bool`

Determine if an error should be retried.

**Parameters:**
- `error` (Exception): The exception to classify

**Returns:**
- `bool`: `True` if the error is retryable, `False` otherwise

**Retryable Errors:**
- `openai.RateLimitError` - API quota exceeded (429)
- `openai.APIConnectionError` - Network or connectivity issues
- `openai.APIError` - Server-side errors

**Example:**
```python
from openai import RateLimitError
try:
    response = llm.invoke(messages)
except RateLimitError as e:
    if is_retryable_error(e):
        print("Will retry this request")
    else:
        print("Won't retry")
```

#### `is_fatal_error(error: Exception) -> bool`

Determine if an error is fatal and should not be retried.

**Parameters:**
- `error` (Exception): The exception to classify

**Returns:**
- `bool`: `True` if the error is fatal, `False` otherwise

**Fatal Errors (Don't Retry):**
- `openai.AuthenticationError` - Invalid API credentials (401)
- `ValueError` - Invalid parameters
- `TypeError` - Type mismatch
- Other built-in exceptions

**Example:**
```python
try:
    response = llm.invoke(messages)
except Exception as e:
    if is_fatal_error(e):
        print("Fatal error - will not retry")
        logger.error(f"Fatal error: {e}")
    else:
        print("Transient error - will retry")
```

#### `async def invoke_with_retry(invocation_func, max_retries=3, initial_delay=1.0, max_delay=60.0, operation_name="LLM invocation") -> T`

Asynchronously invoke a function with exponential backoff retry logic.

**Parameters:**
- `invocation_func` (Callable[[], Awaitable[T]]): Async function to invoke
- `max_retries` (int, optional): Maximum number of retries. Default: 3
  - Total attempts = max_retries + 1 (initial attempt plus retries)
- `initial_delay` (float, optional): Initial delay in seconds. Default: 1.0
  - Delay sequence: 1.0, 2.0, 4.0, 8.0, ... (exponential)
- `max_delay` (float, optional): Maximum delay cap in seconds. Default: 60.0
  - Prevents backoff from growing unbounded
- `operation_name` (str, optional): Name for logging. Default: "LLM invocation"

**Returns:**
- `T`: Result from successful invocation_func

**Raises:**
- `LLMInvocationError`: If all retries exhausted or fatal error occurs

**Example:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

async def call_llm():
    response = await llm.ainvoke(messages)
    return response

try:
    result = await invoke_with_retry(
        call_llm,
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        operation_name="GPT-4 invocation"
    )
    print(f"Success: {result.content}")
except LLMInvocationError as e:
    print(f"Failed after {e.attempt}/{e.max_attempts} attempts")
    logger.error(f"LLM invocation failed: {e}")
```

#### `def invoke_with_retry_sync(invocation_func, max_retries=3, initial_delay=1.0, max_delay=60.0, operation_name="LLM invocation") -> T`

Synchronously invoke a function with exponential backoff retry logic.

**Parameters:**
- `invocation_func` (Callable[[], T]): Sync function to invoke
- `max_retries` (int, optional): Maximum number of retries. Default: 3
- `initial_delay` (float, optional): Initial delay in seconds. Default: 1.0
- `max_delay` (float, optional): Maximum delay cap in seconds. Default: 60.0
- `operation_name` (str, optional): Name for logging. Default: "LLM invocation"

**Returns:**
- `T`: Result from successful invocation_func

**Raises:**
- `LLMInvocationError`: If all retries exhausted or fatal error occurs

**Example:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def call_llm_sync():
    response = llm.invoke(messages)  # Synchronous call
    return response

try:
    result = invoke_with_retry_sync(
        call_llm_sync,
        max_retries=3,
        initial_delay=1.0,
        operation_name="Worker LLM invocation"
    )
    print(f"Success: {result.content}")
except LLMInvocationError as e:
    logger.error(f"Worker LLM failed: {e}", exc_info=True)
    # Handle gracefully - return error message instead of crashing
    return {"error": str(e)}
```

## Integration Examples

### Example 1: Worker Node with Error Handling

```python
from llm_invocation import invoke_with_retry_sync, LLMInvocationError
from langchain_core.messages import HumanMessage

def worker(self, state: State) -> Dict[str, Any]:
    """Worker node with robust error handling."""

    # Build messages
    messages = self._build_messages(state)

    # Invoke LLM with retry logic
    try:
        response = invoke_with_retry_sync(
            lambda: self.worker_llm_with_tools.invoke(messages),
            max_retries=3,
            initial_delay=1.0,
            operation_name="Worker LLM invocation"
        )
        return {"messages": [response]}
    except LLMInvocationError as e:
        logger.error(f"Worker LLM failed: {e}", exc_info=True)
        # Graceful fallback
        error_message = HumanMessage(
            content=f"I encountered a temporary error: {type(e.original_error).__name__}. "
                    f"Please try again."
        )
        return {"messages": [error_message]}
```

### Example 2: Evaluator Node with Failsafe

```python
from llm_invocation import invoke_with_retry_sync, LLMInvocationError
from pydantic import BaseModel

class EvaluatorOutput(BaseModel):
    feedback: str
    success_criteria_met: bool
    user_input_needed: bool

def evaluator(self, state: State) -> State:
    """Evaluator with automatic failsafe on error."""

    messages = self._build_evaluation_messages(state)

    try:
        result = invoke_with_retry_sync(
            lambda: self.evaluator_llm_with_output.invoke(messages),
            max_retries=3,
            initial_delay=1.0,
            operation_name="Evaluator LLM invocation"
        )
        return {
            "feedback_on_work": result.feedback,
            "success_criteria_met": result.success_criteria_met,
            "user_input_needed": result.user_input_needed,
        }
    except LLMInvocationError as e:
        logger.error(f"Evaluator failed: {e}", exc_info=True)
        # Failsafe: Request user input instead of crashing
        return {
            "feedback_on_work": f"Evaluation error: {type(e.original_error).__name__}",
            "success_criteria_met": False,
            "user_input_needed": True,  # Escalate to user
        }
```

### Example 3: Custom Retry Strategy

```python
from llm_invocation import invoke_with_retry_sync, LLMInvocationError

def aggressive_retry():
    """Custom retry strategy for critical operations."""
    try:
        result = invoke_with_retry_sync(
            lambda: llm.invoke(messages),
            max_retries=5,        # More retries
            initial_delay=0.5,    # Faster start
            max_delay=30.0,       # Quick backoff
            operation_name="Critical LLM call"
        )
        return result
    except LLMInvocationError as e:
        if e.attempt >= 5:
            # All retries exhausted - escalate
            logger.critical(f"Critical operation failed: {e}")
            raise
        return None

def gentle_retry():
    """Custom retry strategy for background operations."""
    try:
        result = invoke_with_retry_sync(
            lambda: llm.invoke(messages),
            max_retries=1,        # Minimal retries
            initial_delay=5.0,    # Longer delays
            max_delay=60.0,       # Longer backoff
            operation_name="Background LLM call"
        )
        return result
    except LLMInvocationError as e:
        # Log and continue - non-critical
        logger.warning(f"Background operation failed (acceptable): {e}")
        return None
```

## Behavior Reference

### Retry Flow Diagram

```
┌─ Invoke Function
│
├─ Success? ──→ Return Result
│
└─ Exception?
   │
   ├─ Fatal Error (AuthenticationError, ValueError)?
   │  └─ Raise LLMInvocationError (FAIL FAST)
   │
   ├─ Non-Retryable (Unknown)?
   │  └─ Raise LLMInvocationError (FAIL FAST)
   │
   └─ Retryable (RateLimitError, APIConnectionError, APIError)?
      │
      ├─ Attempt >= max_retries?
      │  └─ Raise LLMInvocationError (ALL RETRIES EXHAUSTED)
      │
      └─ Attempt < max_retries?
         ├─ Calculate Backoff: min(delay * 2^attempt + jitter, max_delay)
         ├─ Log Warning & Wait
         ├─ Increment Attempt
         └─ Go to Invoke Function
```

### Delay Sequence Example

With default parameters (initial_delay=1.0, max_delay=60.0):

```
Attempt 1: Invoke immediately
Attempt 2: Wait 1.0s + jitter (0-0.1s)
Attempt 3: Wait 2.0s + jitter (0-0.2s)
Attempt 4: Wait 4.0s + jitter (0-0.4s)
Attempt 5: Wait 8.0s + jitter (0-0.8s)
Attempt 6: Wait 16.0s + jitter (0-1.6s)
Attempt 7: Wait 32.0s + jitter (0-3.2s)
Attempt 8: Wait 60.0s + jitter (0-6.0s) [capped at max_delay]
```

**Total wait time for 7 retries:** ~1+2+4+8+16+32+60 = ~123 seconds (with jitter)

## Error Messages

### Successful Retry

```
DEBUG: Worker LLM invocation: Attempt 1/3
WARNING: Worker LLM invocation: Retryable error on attempt 1/3: APIConnectionError: Connection timeout
INFO: Worker LLM invocation: Retrying in 1.05s (attempt 1/3)
DEBUG: Worker LLM invocation: Attempt 2/3
INFO: Worker LLM invocation: Succeeded on attempt 2
```

### All Retries Exhausted

```
DEBUG: Worker LLM invocation: Attempt 1/3
WARNING: Worker LLM invocation: Retryable error on attempt 1/3: RateLimitError: Rate limit exceeded
INFO: Worker LLM invocation: Retrying in 1.08s (attempt 1/3)
DEBUG: Worker LLM invocation: Attempt 2/3
WARNING: Worker LLM invocation: Retryable error on attempt 2/3: RateLimitError: Rate limit exceeded
INFO: Worker LLM invocation: Retrying in 2.12s (attempt 2/3)
DEBUG: Worker LLM invocation: Attempt 3/3
WARNING: Worker LLM invocation: Retryable error on attempt 3/3: RateLimitError: Rate limit exceeded
ERROR: Worker LLM invocation: All 3 retries exhausted
ERROR: Worker LLM invocation failed: LLM invocation failed after 3 attempts (attempt 3/3): RateLimitError: Rate limit exceeded
```

### Fatal Error

```
DEBUG: Worker LLM invocation: Attempt 1/3
ERROR: Worker LLM invocation: Fatal error on attempt 1: AuthenticationError: Invalid API key
ERROR: Worker LLM invocation failed: LLM invocation failed with fatal error (attempt 1/3): AuthenticationError: Invalid API key
```

## Best Practices

1. **Always catch `LLMInvocationError`**
   ```python
   try:
       result = invoke_with_retry_sync(llm_call)
   except LLMInvocationError as e:
       logger.error(f"LLM failed: {e}", exc_info=True)
       # Handle gracefully
   ```

2. **Use meaningful operation_name for logging**
   ```python
   result = invoke_with_retry_sync(
       llm_call,
       operation_name="GPT-4 response generation for user query"
   )
   ```

3. **Adjust retry count based on criticality**
   ```python
   # Critical operation - more retries
   invoke_with_retry_sync(critical_llm_call, max_retries=5)

   # Non-critical operation - fewer retries
   invoke_with_retry_sync(background_llm_call, max_retries=1)
   ```

4. **Return graceful fallbacks instead of raising**
   ```python
   try:
       response = invoke_with_retry_sync(llm_call)
   except LLMInvocationError as e:
       # Return error message to user, not exception
       return f"I encountered an error. Please try again."
   ```

5. **Log original errors with full context**
   ```python
   except LLMInvocationError as e:
       logger.error(
           f"LLM call failed after {e.attempt} attempts: {e.original_error}",
           exc_info=True  # Include full traceback
       )
   ```

## Performance Considerations

### Timeout Implications

- Default max_retries=3 with backoff can take up to ~7 seconds for complete failure
- Adjust `max_retries` and delays based on timeout constraints
- Consider `max_delay` to prevent excessive waiting

### Resource Usage

- Exponential backoff prevents resource exhaustion from rapid retries
- Jitter prevents thundering herd when multiple instances retry simultaneously
- No additional memory overhead beyond exception objects

### Logging Overhead

- Each retry attempt generates log entries (DEBUG, WARNING, or ERROR)
- Suitable for production with standard logging configuration
- Consider log aggregation for large-scale deployments

## Troubleshooting

### Issue: "Fatal error - all retries exhausted"

**Cause:** All retry attempts used without success

**Solutions:**
1. Increase `max_retries`: `invoke_with_retry_sync(..., max_retries=5)`
2. Check if error is actually transient
3. Verify API key and endpoint configuration
4. Check network connectivity

### Issue: "AuthenticationError: Invalid API key"

**Cause:** API credentials are invalid or expired

**Solutions:**
1. Verify `OPENAI_API_KEY` environment variable
2. Check API key in OpenAI dashboard
3. Rotate API key if compromised
4. Note: This error will NOT retry (fatal)

### Issue: "RateLimitError" after all retries

**Cause:** API quota exceeded

**Solutions:**
1. Upgrade API plan
2. Implement request queuing
3. Increase `initial_delay` to space out requests
4. Check concurrent request volume

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-14 | Initial implementation |

## Related Issues

- **Issue C4:** Unhandled LLM Invocation Failures
- **Implementation:** `improvements/C4_Unhandled_Invocation_Failures/IMPLEMENTATION.md`
- **Tests:** `tests/test_llm_invocation_c4.py`
