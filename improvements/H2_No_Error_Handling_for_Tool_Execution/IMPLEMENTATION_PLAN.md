# H2: No Error Handling for Tool Execution - Implementation Plan

**Severity:** HIGH PRIORITY (Phase 2 Implementation)
**Status:** In Progress
**Estimated Effort:** 2 hours
**Created:** 2025-11-14

## Problem Statement

When tools fail during execution in the Sidekick agent framework, the LangGraph `ToolNode` silently swallows errors. This prevents the LLM worker from knowing that tool execution failed, causing the agent to:

1. Loop indefinitely on failing tool calls
2. Provide incorrect responses based on missing tool results
3. Exit without clear error feedback to the user
4. Make debugging production issues nearly impossible

## Root Cause Analysis

### Current Architecture

The state machine flow uses LangGraph's prebuilt `ToolNode`:

```python
# src/sidekick.py:307
graph_builder.add_node("tools", ToolNode(tools=self.tools))
```

The `ToolNode` automatically executes tools but provides **no error handling, logging, or fallback mechanisms**.

### Comparison with Existing Error Handling

The codebase **does** have comprehensive error handling for:

- **Worker Node** (`src/sidekick.py:129-148`): LLM invocation with retry logic and error messages
- **Evaluator Node** (`src/sidekick.py:238-264`): LLM invocation with retry logic and fail-safe states

However, **tool execution has zero error handling**.

### Tool Failure Scenarios

Tools can fail in multiple ways:

| Tool Category | Failure Scenarios |
|---|---|
| **Playwright Browser Tools** | Navigation timeouts, element not found, popup blocking, permission denied |
| **File Management Tools** | File not found, permission denied, disk full, invalid paths |
| **Web Search** | API rate limits, malformed queries, network timeouts |
| **Wikipedia** | Page not found, connection timeouts, malformed queries |
| **Push Notifications** | Network failures, invalid credentials, API timeouts |
| **Python REPL** | Execution errors, infinite loops, syntax errors, resource exhaustion |

## Solution Design

### 1. Tool Error Wrapper

Create a wrapper function to catch and log tool execution errors:

```python
# src/tool_error_handler.py

def wrap_tool_with_error_handling(tool: BaseTool) -> BaseTool:
    """Wrap a tool with error handling, logging, and formatted error responses.

    Returns:
        BaseTool: Wrapped tool that safely handles exceptions
    """
    # Implementation details in code section below
```

### 2. Custom Tool Execution Node

Replace `ToolNode` with a custom implementation that:
- Iterates over tool calls
- Wraps each execution in try/except
- Logs all successes and failures
- Returns structured error messages to the worker

### 3. Error Message Format for LLM

Define how tool failures are communicated back to the worker:

```
Tool Execution Result:
Tool Name: [tool_name]
Status: FAILED
Error Type: [exception_type]
Error Message: [human_readable_message]
```

### 4. Logging Strategy

Log at three levels:

- **INFO**: Tool name, inputs (truncated for size)
- **SUCCESS**: Tool completed with result size
- **ERROR**: Full traceback, inputs, outputs for debugging

## Implementation Steps

### Phase 1: Error Wrapper Implementation

**File:** `src/tool_error_handler.py` (NEW)

1. Create `ToolExecutionError` custom exception class
2. Create `wrap_tool_with_error_handling()` function
3. Create `execute_tool_safely()` async helper
4. Add comprehensive logging

### Phase 2: Custom Tool Node

**File:** `src/sidekick.py` (MODIFIED)

1. Create `ErrorHandlingToolNode` class (replaces `ToolNode`)
2. Implement tool call iteration and error handling
3. Format error responses for LLM consumption
4. Add timing and instrumentation

### Phase 3: Integration

**File:** `src/sidekick.py` (MODIFIED)

1. Update `build_graph()` to use `ErrorHandlingToolNode`
2. Update tool binding to wrap tools (optional - if done in Phase 1)
3. Update logging configuration

### Phase 4: Testing

**Files:** `tests/test_tool_error_handling.py` (NEW)

1. Unit tests for error wrapper
2. Integration tests for each tool type
3. Tests for error message formatting
4. Tests for logging output

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Wrap individual tools | Protects each tool independently; enables per-tool configuration |
| Log at INFO/ERROR | Provides observability without verbosity for normal operation |
| Return formatted errors to LLM | LLM can understand failures and retry with different approach |
| Don't crash on tool failure | Agent continues despite tool failures; user gets feedback |
| Include tool inputs in logs | Helps debug malformed tool calls |

## Expected Outcomes

### Before Implementation

```
Worker: "search for latest news about AI"
  ↓
Tools: Search fails (API rate limited) → Error silently swallowed
  ↓
Worker: Receives no result, loops or halts
  ↓
User: No error feedback, confused why task failed
```

### After Implementation

```
Worker: "search for latest news about AI"
  ↓
Tools: Search fails (API rate limited) → Error caught & logged
  ↓
Worker: Receives structured error message
  ↓
Worker: Understands failure and adjusts strategy (retries, uses different tool, asks user)
  ↓
User: Gets clear feedback about what failed and why
```

## Validation Criteria

- ✅ All existing tests pass
- ✅ New unit tests cover error wrapper (>90% coverage)
- ✅ New integration tests verify tool failure handling
- ✅ Tool failures are logged with sufficient detail for debugging
- ✅ Worker receives error messages it can parse and respond to
- ✅ No silent failures; all errors logged to stderr/stdout
- ✅ Documentation includes examples of each failure scenario

## Files to Modify/Create

| File | Action | Reason |
|------|--------|--------|
| `src/tool_error_handler.py` | CREATE | Tool wrapper and error handling utilities |
| `src/sidekick.py` | MODIFY | Add `ErrorHandlingToolNode` and update `build_graph()` |
| `tests/test_tool_error_handling.py` | CREATE | Comprehensive error handling tests |

## Timeline

- **2025-11-14 14:00**: Start implementation
- **2025-11-14 15:00**: Complete error wrapper and custom tool node
- **2025-11-14 15:30**: Complete tests and validation
- **2025-11-14 16:00**: Publish to working branch

## References

- **Issue Location:** `/Volumes/Storage/Projects/assistant/improvements/20251114_142300_code_review_and_improvement_plan.md` (lines 152-164)
- **Code Review Details:** "H2: No Error Handling for Tool Execution"
- **Related Code:**
  - Tool execution: `src/sidekick.py:307`
  - Tool definitions: `src/sidekick_tools.py`
  - Error handling reference: `src/sidekick.py:129-148` (worker error handling)
