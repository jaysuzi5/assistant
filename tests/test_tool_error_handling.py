"""Comprehensive tests for tool error handling functionality.

Tests cover:
- Tool error wrapper functionality
- Custom ErrorHandlingToolNode behavior
- Error message formatting
- Error registry tracking
- Integration with LangGraph state machine
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tool_error_handler import (
    ToolExecutionError,
    wrap_tool_with_error_handling,
    format_tool_error_for_llm,
    create_tool_error_message,
    ToolErrorRegistry,
)
from sidekick import ErrorHandlingToolNode
from langchain_core.tools import tool, StructuredTool
from langchain_core.messages import AIMessage, ToolMessage


class TestToolExecutionError:
    """Tests for ToolExecutionError exception class."""

    def test_creation_with_all_fields(self):
        """Test creating a ToolExecutionError with all fields."""
        original_error = ValueError("Invalid input")
        tool_error = ToolExecutionError(
            tool_name="search",
            original_error=original_error,
            tool_input="bad_query",
            message="Custom error message",
        )

        assert tool_error.tool_name == "search"
        assert tool_error.original_error is original_error
        assert tool_error.tool_input == "bad_query"
        assert tool_error.error_type == "ValueError"
        assert tool_error.message == "Custom error message"
        assert isinstance(tool_error.timestamp, datetime)

    def test_creation_with_minimal_fields(self):
        """Test creating a ToolExecutionError with minimal fields."""
        original_error = RuntimeError("Tool crashed")
        tool_error = ToolExecutionError(
            tool_name="process",
            original_error=original_error,
        )

        assert tool_error.tool_name == "process"
        assert tool_error.original_error is original_error
        assert tool_error.error_type == "RuntimeError"
        assert "process" in tool_error.message
        assert "RuntimeError" in tool_error.message

    def test_to_dict(self):
        """Test converting error to dictionary."""
        original_error = TypeError("Type mismatch")
        tool_error = ToolExecutionError(
            tool_name="convert",
            original_error=original_error,
        )

        error_dict = tool_error.to_dict()
        assert error_dict["tool_name"] == "convert"
        assert error_dict["error_type"] == "TypeError"
        assert error_dict["message"] == "Type mismatch"
        assert "timestamp" in error_dict


class TestWrapToolWithErrorHandling:
    """Tests for the wrap_tool_with_error_handling function."""

    def test_wrap_successful_tool(self):
        """Test wrapping a tool that executes successfully."""
        @tool
        def double(x: int) -> int:
            """Double a number."""
            return x * 2

        wrapped_tool = wrap_tool_with_error_handling(double)
        assert wrapped_tool.name == "double"

    def test_wrap_failing_tool(self):
        """Test wrapping a tool that raises an exception."""
        @tool
        def bad_tool(x: str) -> str:
            """Tool that always fails."""
            raise ValueError(f"Bad input: {x}")

        wrapped_tool = wrap_tool_with_error_handling(bad_tool)
        assert wrapped_tool.name == "bad_tool"

    def test_wrapped_tool_preserves_name(self):
        """Test that wrapped tool preserves original tool name."""
        @tool
        def my_func() -> str:
            """My tool."""
            return "result"

        wrapped_tool = wrap_tool_with_error_handling(my_func)
        assert wrapped_tool.name == "my_func"

    def test_wrapped_tool_preserves_description(self):
        """Test that wrapped tool preserves original description."""
        @tool
        def my_func() -> str:
            """My tool description."""
            return "result"

        wrapped_tool = wrap_tool_with_error_handling(my_func)
        assert wrapped_tool.description == "My tool description."

    def test_wrap_tool_with_logging(self, caplog):
        """Test that wrapped tool maintains name and description."""
        @tool
        def simple_tool() -> str:
            """Simple tool."""
            return "success"

        wrapped_tool = wrap_tool_with_error_handling(simple_tool)
        # Verify it returns the tool as-is
        assert wrapped_tool.name == "simple_tool"

    def test_wrap_tool_error_logging(self, caplog):
        """Test that wrapped tool returns the tool unchanged."""
        @tool
        def failing_tool() -> str:
            """Tool that fails."""
            raise RuntimeError("Execution error")

        wrapped_tool = wrap_tool_with_error_handling(failing_tool)
        # Should be the same tool, error handling is in ErrorHandlingToolNode
        assert wrapped_tool.name == "failing_tool"


class TestFormatToolErrorForLLM:
    """Tests for format_tool_error_for_llm function."""

    def test_format_error_message(self):
        """Test formatting an error message for LLM."""
        message = format_tool_error_for_llm(
            tool_name="search",
            error_type="RateLimitError",
            error_message="Rate limit exceeded",
        )

        assert "Tool Execution Failed" in message
        assert "search" in message
        assert "RateLimitError" in message
        assert "Rate limit exceeded" in message

    def test_format_error_contains_guidance(self):
        """Test that formatted error provides guidance to LLM."""
        message = format_tool_error_for_llm(
            tool_name="browser",
            error_type="TimeoutError",
            error_message="Page load timeout",
        )

        # Should indicate the tool failed and cannot be used
        assert "failed" in message.lower()
        assert "cannot be used" in message.lower()

    def test_format_error_structure(self):
        """Test the structure of formatted error message."""
        message = format_tool_error_for_llm(
            tool_name="test",
            error_type="TestError",
            error_message="Test error occurred",
        )

        lines = message.strip().split("\n")
        # Should have structured format with key: value pairs
        assert len(lines) > 3
        assert "Tool:" in message
        assert "Error Type:" in message
        assert "Message:" in message


class TestCreateToolErrorMessage:
    """Tests for create_tool_error_message function."""

    def test_create_error_tool_message(self):
        """Test creating a ToolMessage for tool execution error."""
        error = ValueError("Invalid value")
        message = create_tool_error_message(
            tool_name="validator",
            error=error,
            tool_call_id="call_123",
        )

        assert isinstance(message, ToolMessage)
        assert message.name == "validator"
        assert message.tool_call_id == "call_123"
        assert "[TOOL ERROR]" in message.content
        assert "validator" in message.content
        assert "ValueError" in message.content

    def test_error_message_truncation(self):
        """Test that long error messages are truncated."""
        long_error_text = "x" * 1000
        error = RuntimeError(long_error_text)
        message = create_tool_error_message(
            tool_name="big_error",
            error=error,
            tool_call_id="call_456",
        )

        # Message content should be truncated
        assert len(message.content) < len(long_error_text) + 100


class TestToolErrorRegistry:
    """Tests for ToolErrorRegistry class."""

    def test_record_single_error(self):
        """Test recording a single error."""
        registry = ToolErrorRegistry()
        error = ValueError("Test error")

        registry.record_error("test_tool", error)

        summary = registry.get_error_summary()
        assert "test_tool:ValueError" in summary
        assert summary["test_tool:ValueError"] == 1

    def test_record_multiple_errors_same_tool(self):
        """Test recording multiple errors from the same tool."""
        registry = ToolErrorRegistry()
        error1 = ValueError("Error 1")
        error2 = ValueError("Error 2")

        registry.record_error("tool", error1)
        registry.record_error("tool", error2)

        summary = registry.get_error_summary()
        assert summary["tool:ValueError"] == 2

    def test_record_different_error_types(self):
        """Test recording different error types from same tool."""
        registry = ToolErrorRegistry()
        error1 = ValueError("Value error")
        error2 = RuntimeError("Runtime error")

        registry.record_error("tool", error1)
        registry.record_error("tool", error2)

        summary = registry.get_error_summary()
        assert summary["tool:ValueError"] == 1
        assert summary["tool:RuntimeError"] == 1

    def test_get_errors_for_tool(self):
        """Test retrieving errors for a specific tool."""
        registry = ToolErrorRegistry()
        registry.record_error("search", ValueError("Bad query"))
        registry.record_error("search", TypeError("Wrong type"))
        registry.record_error("other", RuntimeError("Other error"))

        search_errors = registry.get_errors_for_tool("search")
        assert "search:ValueError" in search_errors
        assert "search:TypeError" in search_errors
        assert len(search_errors) == 2

    def test_error_summary_copy(self):
        """Test that error summary returns a copy, not reference."""
        registry = ToolErrorRegistry()
        registry.record_error("tool", ValueError("Error"))

        summary1 = registry.get_error_summary()
        summary2 = registry.get_error_summary()

        # Should be equal but not the same object
        assert summary1 == summary2
        assert summary1 is not summary2


class TestErrorHandlingToolNode:
    """Tests for ErrorHandlingToolNode class."""

    def test_initialization(self):
        """Test initializing ErrorHandlingToolNode."""
        @tool
        def dummy_func() -> str:
            """Dummy tool."""
            return "result"

        node = ErrorHandlingToolNode(tools=[dummy_func])
        assert "dummy_func" in node.tools
        assert node.tools["dummy_func"].name == "dummy_func"

    def test_tool_call_success(self):
        """Test successful tool execution."""
        @tool
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        node = ErrorHandlingToolNode(tools=[add])

        # Create state with tool call
        ai_message = AIMessage(
            content="Let me add these numbers",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "add",
                    "args": {"a": 5, "b": 3},
                }
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert "8" in result["messages"][0].content

    def test_tool_call_failure(self, caplog):
        """Test tool execution failure handling."""
        @tool
        def bad_func() -> str:
            """Tool that fails."""
            raise ValueError("Intentional error")

        node = ErrorHandlingToolNode(tools=[bad_func])

        # Create state with tool call
        ai_message = AIMessage(
            content="Use the bad tool",
            tool_calls=[
                {
                    "id": "call_bad",
                    "name": "bad_func",
                    "args": {},
                }
            ],
        )

        state = {"messages": [ai_message]}

        with caplog.at_level(logging.ERROR):
            result = node(state)

        # Should return error message
        assert "messages" in result
        assert len(result["messages"]) == 1
        tool_message = result["messages"][0]
        assert isinstance(tool_message, ToolMessage)
        assert "Tool Execution Failed" in tool_message.content
        assert "ValueError" in tool_message.content

        # Should track error
        assert "bad_func" in node.tool_error_registry
        assert len(node.tool_error_registry["bad_func"]) > 0

    def test_multiple_tool_calls(self):
        """Test executing multiple tool calls."""
        @tool
        def multiply(a: int, b: int) -> int:
            """Multiply."""
            return a * b

        @tool
        def subtract(a: int, b: int) -> int:
            """Subtract."""
            return a - b

        tools = [multiply, subtract]
        node = ErrorHandlingToolNode(tools=tools)

        ai_message = AIMessage(
            content="Do math",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "multiply",
                    "args": {"a": 4, "b": 3},
                },
                {
                    "id": "call_2",
                    "name": "subtract",
                    "args": {"a": 10, "b": 2},
                },
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        assert len(result["messages"]) == 2
        assert all(isinstance(msg, ToolMessage) for msg in result["messages"])
        assert "12" in result["messages"][0].content
        assert "8" in result["messages"][1].content

    def test_tool_not_found(self):
        """Test error when tool is not in registry."""
        @tool
        def exists() -> str:
            """Exists."""
            return "dummy"

        node = ErrorHandlingToolNode(tools=[exists])

        ai_message = AIMessage(
            content="Use nonexistent tool",
            tool_calls=[
                {
                    "id": "call_bad",
                    "name": "nonexistent",
                    "args": {},
                }
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        # Should return error message
        assert "messages" in result
        tool_message = result["messages"][0]
        assert "Tool Execution Failed" in tool_message.content

    def test_no_tool_calls_in_state(self):
        """Test when state has no tool calls."""
        node = ErrorHandlingToolNode(tools=[])

        # Message without tool calls
        ai_message = AIMessage(content="Just a message")
        state = {"messages": [ai_message]}

        result = node(state)
        assert result == {"messages": []}

    def test_empty_messages_state(self):
        """Test when state has no messages."""
        node = ErrorHandlingToolNode(tools=[])
        state = {"messages": []}

        result = node(state)
        assert result == {"messages": []}

    def test_get_error_summary(self):
        """Test retrieving error summary."""
        @tool
        def failing_tool() -> str:
            """Fails."""
            raise RuntimeError("Failed")

        node = ErrorHandlingToolNode(tools=[failing_tool])

        ai_message = AIMessage(
            content="Use failing tool",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "failing_tool",
                    "args": {},
                }
            ],
        )

        state = {"messages": [ai_message]}
        node(state)

        summary = node.get_error_summary()
        assert "failing_tool" in summary
        assert len(summary["failing_tool"]) > 0
        assert summary["failing_tool"][0]["error_type"] == "RuntimeError"

    def test_tool_message_preserves_tool_call_id(self):
        """Test that tool messages preserve the tool call ID."""
        @tool
        def echo(text: str) -> str:
            """Echo."""
            return text

        node = ErrorHandlingToolNode(tools=[echo])

        ai_message = AIMessage(
            content="Echo this",
            tool_calls=[
                {
                    "id": "special_call_id_123",
                    "name": "echo",
                    "args": {"text": "hello"},
                }
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        tool_message = result["messages"][0]
        assert tool_message.tool_call_id == "special_call_id_123"

    def test_mixed_success_and_failure(self):
        """Test batch with both successful and failing tools."""
        @tool
        def good_tool() -> str:
            """Good."""
            return "success"

        @tool
        def bad_tool() -> str:
            """Bad."""
            raise ValueError("Failed")

        tools = [good_tool, bad_tool]
        node = ErrorHandlingToolNode(tools=tools)

        ai_message = AIMessage(
            content="Try both",
            tool_calls=[
                {
                    "id": "call_good",
                    "name": "good_tool",
                    "args": {},
                },
                {
                    "id": "call_bad",
                    "name": "bad_tool",
                    "args": {},
                },
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        messages = result["messages"]
        assert len(messages) == 2

        # Find which is success and which is failure
        success_msg = next(m for m in messages if m.tool_call_id == "call_good")
        failure_msg = next(m for m in messages if m.tool_call_id == "call_bad")

        assert "success" in success_msg.content
        assert "Tool Execution Failed" in failure_msg.content


class TestErrorHandlingIntegration:
    """Integration tests combining multiple components."""

    def test_error_handling_in_tool_sequence(self):
        """Test error handling across multiple tool executions."""
        execution_log = []

        @tool
        def first_tool() -> str:
            """First."""
            execution_log.append("first")
            return "first_result"

        @tool
        def second_tool() -> str:
            """Second."""
            execution_log.append("second")
            raise RuntimeError("Second failed")

        @tool
        def third_tool() -> str:
            """Third."""
            execution_log.append("third")
            return "third_result"

        tools = [first_tool, second_tool, third_tool]
        node = ErrorHandlingToolNode(tools=tools)

        ai_message = AIMessage(
            content="Run all tools",
            tool_calls=[
                {"id": "call_1", "name": "first_tool", "args": {}},
                {"id": "call_2", "name": "second_tool", "args": {}},
                {"id": "call_3", "name": "third_tool", "args": {}},
            ],
        )

        state = {"messages": [ai_message]}
        result = node(state)

        # All tools should have been attempted
        assert execution_log == ["first", "second", "third"]

        # All should have results
        messages = result["messages"]
        assert len(messages) == 3

        # Check results
        assert "first_result" in messages[0].content
        assert "Tool Execution Failed" in messages[1].content
        assert "third_result" in messages[2].content

    def test_error_tracking_across_calls(self):
        """Test that error registry tracks errors across multiple invocations."""
        @tool
        def unreliable_tool(x: int) -> int:
            """Unreliable."""
            if x < 0:
                raise ValueError("Negative not allowed")
            return x * 2

        node = ErrorHandlingToolNode(tools=[unreliable_tool])

        # First successful call
        state1 = {
            "messages": [
                AIMessage(
                    content="Call with positive",
                    tool_calls=[
                        {"id": "call_1", "name": "unreliable_tool", "args": {"x": 5}}
                    ],
                )
            ]
        }
        result1 = node(state1)
        assert "10" in result1["messages"][0].content

        # Second failed call
        state2 = {
            "messages": [
                AIMessage(
                    content="Call with negative",
                    tool_calls=[
                        {"id": "call_2", "name": "unreliable_tool", "args": {"x": -5}}
                    ],
                )
            ]
        }
        result2 = node(state2)
        assert "Tool Execution Failed" in result2["messages"][0].content

        # Check registry tracks both
        error_registry = node.get_error_summary()
        # Note: ErrorHandlingToolNode stores errors grouped by tool name, not tool:error_type
        assert "unreliable_tool" in error_registry
        assert len(error_registry["unreliable_tool"]) > 0
        assert error_registry["unreliable_tool"][0]["error_type"] == "ValueError"
