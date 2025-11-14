"""Tool error handling and execution wrapper for Sidekick agent framework.

This module provides comprehensive error handling for tool execution, including:
- Exception catching and logging
- Formatted error messages for LLM consumption
- Per-tool error handling and recovery
- Execution timing and instrumentation
"""

import logging
from typing import Any, Dict, Optional
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Custom exception for tool execution failures.

    Attributes:
        tool_name: Name of the tool that failed
        original_error: The original exception that was raised
        tool_input: The input provided to the tool
        error_type: Type name of the original exception
        timestamp: When the error occurred
    """

    def __init__(
        self,
        tool_name: str,
        original_error: Exception,
        tool_input: Any = None,
        message: Optional[str] = None,
    ):
        """Initialize ToolExecutionError.

        Args:
            tool_name: Name of the tool that failed
            original_error: The exception that was raised during tool execution
            tool_input: Optional input that was provided to the tool
            message: Optional custom error message
        """
        self.tool_name = tool_name
        self.original_error = original_error
        self.tool_input = tool_input
        self.error_type = type(original_error).__name__
        self.timestamp = datetime.now()

        if message:
            self.message = message
        else:
            self.message = f"Tool '{tool_name}' failed: {self.error_type}"

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging or serialization.

        Returns:
            Dictionary with error details
        """
        return {
            "tool_name": self.tool_name,
            "error_type": self.error_type,
            "message": str(self.original_error),
            "timestamp": self.timestamp.isoformat(),
        }


def wrap_tool_with_error_handling(tool: BaseTool) -> BaseTool:
    """Wrap a tool with comprehensive error handling.

    This wrapper:
    1. Catches all exceptions during tool execution
    2. Logs errors with full context (tool name, inputs, error type)
    3. Returns a formatted error message the LLM can understand
    4. Records execution timing

    Note: The wrapping is done at a higher level when tools are added to the
    ErrorHandlingToolNode, which catches exceptions during tool.invoke().
    This function is preserved for future use if per-tool wrapping is needed.

    Args:
        tool: BaseTool instance (returned as-is for now)

    Returns:
        BaseTool with error handling (currently returned as-is)

    Example:
        >>> from langchain_community.tools import Tool
        >>> def my_func(x): return x * 2
        >>> tool = Tool(name="double", func=my_func, description="Double a number")
        >>> wrapped = wrap_tool_with_error_handling(tool)
        >>> # Tool is used within ErrorHandlingToolNode for safety
    """
    # For now, return the tool as-is since the error handling is done
    # at the node level in ErrorHandlingToolNode.__call__()
    # This maintains backward compatibility while deferring wrapping
    # to the node where it's more effective for LangChain tool types
    return tool


def format_tool_error_for_llm(
    tool_name: str,
    error_type: str,
    error_message: str,
) -> str:
    """Format a tool error message for LLM consumption.

    The LLM needs to understand that a tool failed and why, so it can:
    - Retry with different inputs
    - Use an alternative tool
    - Ask the user for clarification

    Args:
        tool_name: Name of the tool that failed
        error_type: Exception class name
        error_message: Human-readable error message

    Returns:
        Formatted error string

    Example:
        >>> msg = format_tool_error_for_llm("search", "RateLimitError", "Rate limit exceeded")
        >>> print(msg)
        Tool Execution Failed
        Tool: search
        Error Type: RateLimitError
        Message: Rate limit exceeded

        The tool failed and cannot be used for this request.
    """
    return (
        f"Tool Execution Failed\n"
        f"Tool: {tool_name}\n"
        f"Error Type: {error_type}\n"
        f"Message: {error_message}\n\n"
        f"The tool failed and cannot be used for this request."
    )


def create_tool_error_message(
    tool_name: str,
    error: Exception,
    tool_call_id: str,
) -> ToolMessage:
    """Create a ToolMessage representing a tool execution failure.

    This message type is recognized by LangGraph and properly integrated
    into the message history, allowing the worker to see tool failures.

    Args:
        tool_name: Name of the tool that failed
        error: The exception that was raised
        tool_call_id: ID of the tool call (from AIMessage.tool_calls)

    Returns:
        ToolMessage with error content

    Example:
        >>> error = ValueError("Invalid input")
        >>> msg = create_tool_error_message("search", error, "call_123")
        >>> print(msg.content)
        [TOOL ERROR] search failed with ValueError: Invalid input
    """
    error_type = type(error).__name__
    error_content = (
        f"[TOOL ERROR] {tool_name} failed with {error_type}: {str(error)[:500]}"
    )

    return ToolMessage(
        content=error_content,
        tool_call_id=tool_call_id,
        name=tool_name,
    )


class ToolErrorRegistry:
    """Registry for tracking tool errors and providing statistics.

    This helps with observability - we can see which tools fail most often
    and what types of errors are most common.
    """

    def __init__(self):
        """Initialize error registry."""
        self.errors: Dict[str, list] = {}
        self.error_counts: Dict[str, int] = {}

    def record_error(self, tool_name: str, error: Exception) -> None:
        """Record a tool execution error.

        Args:
            tool_name: Name of the tool
            error: The exception that occurred
        """
        error_type = type(error).__name__
        key = f"{tool_name}:{error_type}"

        if key not in self.errors:
            self.errors[key] = []
            self.error_counts[key] = 0

        self.errors[key].append(
            {
                "timestamp": datetime.now().isoformat(),
                "error_message": str(error)[:200],
            }
        )
        self.error_counts[key] += 1

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by tool and type.

        Returns:
            Dictionary mapping "tool:error_type" to count
        """
        return self.error_counts.copy()

    def get_errors_for_tool(self, tool_name: str) -> Dict[str, Any]:
        """Get all errors for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary of errors for that tool
        """
        result = {}
        for key, errors in self.errors.items():
            if key.startswith(tool_name):
                result[key] = errors
        return result
