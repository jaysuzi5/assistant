# H2: Technical Reference - Tool Error Handling

## Module: `src/tool_error_handler.py`

### Classes and Functions

#### `ToolExecutionError(Exception)`

**Purpose**: Custom exception for structured error information about tool failures.

**Attributes**:
```python
tool_name: str              # Name of the tool that failed
original_error: Exception   # The original exception
tool_input: Any            # Input provided to the tool
error_type: str            # Type name of the exception (e.g., "ValueError")
timestamp: datetime        # When the error occurred
message: str              # Human-readable error message
```

**Methods**:
```python
def __init__(
    self,
    tool_name: str,
    original_error: Exception,
    tool_input: Any = None,
    message: Optional[str] = None,
) -> None:
    """Initialize ToolExecutionError."""

def to_dict(self) -> Dict[str, Any]:
    """Convert error to dictionary for serialization."""
```

**Example**:
```python
try:
    tool.invoke({"query": "test"})
except Exception as e:
    error = ToolExecutionError(
        tool_name="search",
        original_error=e,
        tool_input={"query": "test"}
    )
    print(error.error_type)  # "ValueError", "TimeoutError", etc.
```

---

#### `wrap_tool_with_error_handling(tool: BaseTool) -> BaseTool`

**Purpose**: Wrapper function for future per-tool error handling (currently returns tool as-is).

**Note**: The primary error handling is done in `ErrorHandlingToolNode.__call__()`, which is more effective for LangChain tool types.

**Parameters**:
- `tool`: BaseTool instance to wrap

**Returns**: BaseTool (same tool, with error handling performed at node level)

**Design Decision**: Error handling deferred to node level for better integration with LangChain's tool execution mechanism.

---

#### `format_tool_error_for_llm(tool_name: str, error_type: str, error_message: str) -> str`

**Purpose**: Format tool execution error in a way the LLM can understand and respond to.

**Parameters**:
- `tool_name`: Name of the tool
- `error_type`: Exception class name
- `error_message`: Human-readable error message

**Returns**: Formatted error string

**Format**:
```
Tool Execution Failed
Tool: [tool_name]
Error Type: [error_type]
Message: [error_message]

The tool failed and cannot be used for this request.
```

**Design**: The message is structured to be:
1. **Recognizable**: "Tool Execution Failed" is clearly a failure indicator
2. **Informative**: Includes tool name and error type for debugging
3. **Actionable**: Tells LLM it can't use this tool and should try alternatives
4. **Consistent**: Structured format makes it easy for LLM to parse

**Example**:
```python
error_msg = format_tool_error_for_llm(
    tool_name="search",
    error_type="RateLimitError",
    error_message="Too many requests"
)
# Output:
# Tool Execution Failed
# Tool: search
# Error Type: RateLimitError
# Message: Too many requests
#
# The tool failed and cannot be used for this request.
```

---

#### `create_tool_error_message(tool_name: str, error: Exception, tool_call_id: str) -> ToolMessage`

**Purpose**: Create a LangChain `ToolMessage` representing a tool execution failure.

**Parameters**:
- `tool_name`: Name of the tool that failed
- `error`: The exception that was raised
- `tool_call_id`: ID from the original AIMessage.tool_calls

**Returns**: `ToolMessage` with error content

**Important**: The `tool_call_id` must match the original tool call ID from the LLM to ensure proper message routing in LangGraph.

**Example**:
```python
error = ValueError("Invalid input")
tool_call_id = "call_xyz_123"
tool_msg = create_tool_error_message(
    tool_name="processor",
    error=error,
    tool_call_id=tool_call_id
)
# Result: ToolMessage(
#     content="[TOOL ERROR] processor failed with ValueError: Invalid input",
#     tool_call_id="call_xyz_123",
#     name="processor"
# )
```

---

#### `class ToolErrorRegistry`

**Purpose**: Track and provide statistics on tool execution errors.

**Methods**:
```python
def __init__(self) -> None:
    """Initialize error registry."""

def record_error(self, tool_name: str, error: Exception) -> None:
    """Record a tool execution error."""
    # Stores: {tool_name: [error_entries]}
    # Each entry: {timestamp, error_message}

def get_error_summary(self) -> Dict[str, int]:
    """Get summary of errors by tool and type."""
    # Returns: {"tool:error_type": count}

def get_errors_for_tool(self, tool_name: str) -> Dict[str, Any]:
    """Get all errors for a specific tool."""
    # Returns: {"tool:error_type": [error_entries]}
```

**Example**:
```python
registry = ToolErrorRegistry()

# Record errors
registry.record_error("search", ValueError("Bad query"))
registry.record_error("search", TimeoutError("Timeout"))
registry.record_error("api", ConnectionError("No connection"))

# Get summary
summary = registry.get_error_summary()
# {"search:ValueError": 1, "search:TimeoutError": 1, "api:ConnectionError": 1}

# Get specific tool errors
search_errors = registry.get_errors_for_tool("search")
# {"search:ValueError": [...], "search:TimeoutError": [...]}
```

---

## Class: `ErrorHandlingToolNode` (in `src/sidekick.py`)

### Purpose

Custom tool execution node that replaces LangGraph's prebuilt `ToolNode` to provide comprehensive error handling and logging.

### Initialization

```python
def __init__(self, tools: List[BaseTool]):
    """Initialize the error-handling tool node.

    Args:
        tools: List of tools available to the node
    """
    self.tools = {tool.name: tool for tool in tools}  # Lookup by name
    self.tool_error_registry = {}  # Track errors
```

### Main Method: `__call__`

```python
def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool calls from the last message with comprehensive error handling.

    Args:
        state: Graph state containing messages

    Returns:
        Updated state with tool results and error messages
    """
```

**Execution Flow**:

1. **Extract Tool Calls**
   - Get last message from state
   - Check for `tool_calls` attribute
   - Return empty if no tool calls found

2. **Process Each Tool Call**
   - For each tool call:
     - Extract name, args, id
     - Look up tool in registry
     - Execute tool with error handling
     - On success: Create ToolMessage with result
     - On failure: Log error, create ToolMessage with error message

3. **Return Results**
   - Return list of ToolMessages back to LangGraph

**Error Handling Details**:

```python
try:
    # Execute the tool
    tool_result = tool.invoke(tool_input)

    # Create success message
    result_message = ToolMessage(
        content=str(tool_result),
        tool_call_id=tool_call_id,
        name=tool_name,
    )
    results.append(result_message)

except Exception as e:
    # Log error with context
    logger.error(
        f"Tool execution failed: {tool_name}",
        extra={
            "tool_name": tool_name,
            "error_type": type(e).__name__,
            "error_message": str(e)[:200],
        },
        exc_info=True,
    )

    # Track in registry
    if tool_name not in self.tool_error_registry:
        self.tool_error_registry[tool_name] = []
    self.tool_error_registry[tool_name].append({
        "error_type": type(e).__name__,
        "error_message": str(e),
        "timestamp": datetime.now().isoformat(),
    })

    # Create error message for LLM
    formatted_error = format_tool_error_for_llm(
        tool_name,
        type(e).__name__,
        str(e)
    )
    error_result = ToolMessage(
        content=formatted_error,
        tool_call_id=tool_call_id,
        name=tool_name,
    )
    results.append(error_result)
```

### Error Registry Method

```python
def get_error_summary(self) -> Dict[str, List[Dict[str, Any]]]:
    """Get summary of all errors encountered.

    Returns:
        Dictionary mapping tool names to their errors
    """
    # Example return:
    # {
    #     "search": [
    #         {
    #             "error_type": "RateLimitError",
    #             "error_message": "Rate limit exceeded",
    #             "timestamp": "2025-11-14T15:30:00.123456"
    #         }
    #     ]
    # }
```

---

## Integration with LangGraph State Machine

### Before: Using LangGraph's ToolNode

```python
from langgraph.prebuilt import ToolNode

async def build_graph(self):
    graph_builder = StateGraph(State)

    # Using prebuilt ToolNode (no error handling)
    graph_builder.add_node("tools", ToolNode(tools=self.tools))

    # ... rest of graph setup ...
```

**Problems**:
- Exceptions silently swallowed
- No error logging
- LLM never knows tools failed

### After: Using ErrorHandlingToolNode

```python
from sidekick import ErrorHandlingToolNode

async def build_graph(self):
    graph_builder = StateGraph(State)

    # Using ErrorHandlingToolNode (comprehensive error handling)
    error_handling_tool_node = ErrorHandlingToolNode(tools=self.tools)
    graph_builder.add_node("tools", error_handling_tool_node)

    # ... rest of graph setup ...
```

**Benefits**:
- All exceptions caught and logged
- Detailed error context available
- LLM receives structured error messages
- Error registry for observability

---

## Logging Output

### Success Log Entry

```
INFO - Executing tool: search
INFO - Tool succeeded: search
  extra: {
    "tool_name": "search",
    "result_length": 1234
  }
```

### Failure Log Entry

```
ERROR - Tool execution failed: search
  extra: {
    "tool_name": "search",
    "error_type": "RateLimitError",
    "error_message": "Rate limit exceeded (429)"
  }
  exc_info: Full traceback
```

### Batch Processing Log Entry

```
INFO - Processing 3 tool call(s)
INFO - Tool execution batch completed
  extra: {
    "successful": 2,
    "total": 3
  }
```

---

## Message Flow Example

### Successful Tool Execution

```
Worker LLM:
  tool_calls = [{"id": "call_1", "name": "search", "args": {"q": "python"}}]

ErrorHandlingToolNode:
  1. Extract tool_call
  2. Look up "search" tool
  3. Execute: tool.invoke({"q": "python"})
  4. Result: "Python is a programming language..."
  5. Create: ToolMessage(content="Python is...", tool_call_id="call_1", name="search")
  6. Return: {"messages": [ToolMessage]}

Back to Worker LLM:
  Receives: ToolMessage with search results
  Continues: Processing results
```

### Failed Tool Execution

```
Worker LLM:
  tool_calls = [{"id": "call_2", "name": "api_call", "args": {"endpoint": "/data"}}]

ErrorHandlingToolNode:
  1. Extract tool_call
  2. Look up "api_call" tool
  3. Execute: tool.invoke({"endpoint": "/data"})
  4. Exception: TimeoutError("Connection timeout")
  5. Log: ERROR - Tool execution failed: api_call
  6. Track: registry["api_call"].append({error_type: "TimeoutError", ...})
  7. Format: "Tool Execution Failed\nTool: api_call\nError Type: TimeoutError\n..."
  8. Create: ToolMessage(content="Tool Execution Failed\n...", tool_call_id="call_2", name="api_call")
  9. Return: {"messages": [ToolMessage]}

Back to Worker LLM:
  Receives: ToolMessage with error message
  Understands: Tool failed due to timeout
  Decision: Try alternative approach or ask user
```

---

## Test Coverage Analysis

### Unit Test Classes

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestToolExecutionError` | 3 | Exception creation, serialization |
| `TestWrapToolWithErrorHandling` | 6 | Tool preservation, wrapping behavior |
| `TestFormatToolErrorForLLM` | 3 | Message formatting, guidance |
| `TestCreateToolErrorMessage` | 2 | ToolMessage creation, truncation |
| `TestToolErrorRegistry` | 5 | Error tracking, retrieval, statistics |
| `TestErrorHandlingToolNode` | 11 | Node initialization, execution, error handling |

### Integration Test Classes

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestErrorHandlingIntegration` | 2 | Multi-tool sequences, error tracking |

### Key Test Scenarios

1. **Tool Success**
   - ✓ Single tool executes successfully
   - ✓ Multiple tools execute successfully
   - ✓ Tool with various argument types

2. **Tool Failure**
   - ✓ Tool raises exception
   - ✓ Tool not found in registry
   - ✓ Invalid tool call format

3. **Error Handling**
   - ✓ Exception caught and logged
   - ✓ Error message formatted for LLM
   - ✓ Tool call ID preserved
   - ✓ Error tracked in registry

4. **Mixed Scenarios**
   - ✓ Batch with successes and failures
   - ✓ Sequential tool execution with errors
   - ✓ Error accumulation across calls

---

## Configuration & Customization

### Future Extensibility

While the current implementation provides comprehensive error handling, it's designed to support future enhancements:

#### Per-Tool Timeouts (Future)

```python
class ErrorHandlingToolNode:
    def __init__(
        self,
        tools: List[BaseTool],
        tool_config: Optional[Dict[str, Any]] = None
    ):
        self.tools = {tool.name: tool for tool in tools}
        self.tool_config = tool_config or {}
        # tool_config: {"tool_name": {"timeout": 5.0, ...}}
```

#### Automatic Retries (Future)

```python
def invoke_with_retry(self, tool, tool_input, max_retries=2):
    # Automatic retry for transient failures
    # Skip for permanent failures (value errors, not found)
    pass
```

#### Fallback Tools (Future)

```python
# tool_config = {
#     "search": {"fallback": "wikipedia_search"},
#     "api": {"fallback": None}  # No fallback
# }
```

---

## Performance Characteristics

### Memory

- **Per Tool**: ~100 bytes overhead (tool name + error list reference)
- **Per Error**: ~200 bytes (timestamp + error type + message)
- **Total**: Scales linearly with error count

### CPU

- **Success Case**: <1ms additional overhead (logging only)
- **Failure Case**: 5-10ms additional overhead (error formatting + tracking)
- **Impact**: Negligible for normal operations

### Logging I/O

- **Per Tool Success**: 1 log entry (~200 bytes)
- **Per Tool Failure**: 1-2 log entries (~500 bytes + traceback)
- **Impact**: Normal logging overhead

---

## Best Practices

### When Writing Tools

```python
# Good: Tools with clear, specific exceptions
@tool
def search(query: str) -> str:
    """Search the web."""
    try:
        result = api.search(query)
        return result
    except requests.Timeout:
        raise TimeoutError(f"Search timeout for query: {query}")
    except requests.HTTPError as e:
        raise ValueError(f"Search API error: {e.response.status_code}")

# Avoid: Tools that silently fail
@tool
def bad_search(query: str) -> str:
    """Search the web."""
    try:
        result = api.search(query)
        return result
    except Exception:
        return ""  # Silent failure - don't do this!
```

### When Using Tools

```python
# The ErrorHandlingToolNode will handle all exceptions
# You don't need to add extra try/except around tool usage
# Just trust the error handling system

node = ErrorHandlingToolNode(tools=[search, bad_search])
# Both tools are protected by error handling
```

### Monitoring Errors

```python
# After tools execution, check for errors
error_summary = node.get_error_summary()
if error_summary:
    logger.warning(f"Tools encountered errors: {error_summary}")
    # Can alert, send to monitoring system, etc.
```

---

## Debugging Guide

### Common Issues

#### "Tool Execution Failed" Message in Output

**Cause**: Tool raised an exception

**Debug Steps**:
1. Check logs for full exception traceback
2. Verify tool inputs are correct format
3. Check external service (API, database) is available
4. Review tool implementation for edge cases

#### Tool Not Found Error

**Cause**: Tool name doesn't match in LLM tool call

**Debug Steps**:
1. Check tool registration: `node.tools.keys()`
2. Verify LLM generated correct tool name
3. Check for typos in tool name or function definition

#### Agent Loops on Tool Failure

**Note**: This should NOT happen with error handling in place

**Debug Steps**:
1. Verify ErrorHandlingToolNode is being used
2. Check that error messages are reaching worker
3. Review worker LLM system prompt for tool failure handling

### Accessing Debug Information

```python
# Get all errors
errors = node.get_error_summary()

# Check specific tool
if "search" in errors:
    search_errors = errors["search"]
    for error_entry in search_errors:
        print(f"{error_entry['error_type']}: {error_entry['error_message']}")

# Check logs
# Look for "ERROR - Tool execution failed" entries
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-14 | Initial implementation with comprehensive error handling |

---

## References

- **Implementation Plan**: `IMPLEMENTATION_PLAN.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Test Suite**: `tests/test_tool_error_handling.py`
- **Main Code**: `src/tool_error_handler.py`, `src/sidekick.py`
