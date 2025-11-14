"""Unit tests for H5: Missing Input Validation.

This test suite validates:
1. Pydantic model creation and validation
2. Input validation for all user-facing methods
3. Error handling for invalid inputs
4. Edge cases and boundary conditions
5. Integration with sidekick.py
"""

import pytest
import sys
import os
from pydantic import ValidationError

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestHistoryItemValidation:
    """Test HistoryItemInput validation."""

    def test_valid_user_message(self) -> None:
        """Test valid user history item."""
        from validation import HistoryItemInput

        item = HistoryItemInput(role="user", content="Hello")
        assert item.role == "user"
        assert item.content == "Hello"

    def test_valid_assistant_message(self) -> None:
        """Test valid assistant history item."""
        from validation import HistoryItemInput

        item = HistoryItemInput(role="assistant", content="Response")
        assert item.role == "assistant"
        assert item.content == "Response"

    def test_valid_system_message(self) -> None:
        """Test valid system history item."""
        from validation import HistoryItemInput

        item = HistoryItemInput(role="system", content="Context")
        assert item.role == "system"
        assert item.content == "Context"

    def test_role_case_insensitive(self) -> None:
        """Test that role is case-insensitive."""
        from validation import HistoryItemInput

        item = HistoryItemInput(role="USER", content="Message")
        assert item.role == "user"

    def test_content_whitespace_stripped(self) -> None:
        """Test that content whitespace is stripped."""
        from validation import HistoryItemInput

        item = HistoryItemInput(role="user", content="  Hello  ")
        assert item.content == "Hello"

    def test_invalid_role(self) -> None:
        """Test that invalid role raises error."""
        from validation import HistoryItemInput

        with pytest.raises(ValidationError) as exc_info:
            HistoryItemInput(role="invalid", content="Message")

        assert "role must be" in str(exc_info.value)

    def test_empty_content_rejected(self) -> None:
        """Test that empty content is rejected."""
        from validation import HistoryItemInput

        with pytest.raises(ValidationError) as exc_info:
            HistoryItemInput(role="user", content="")

        assert "content must not be empty" in str(exc_info.value)

    def test_whitespace_only_content_rejected(self) -> None:
        """Test that whitespace-only content is rejected."""
        from validation import HistoryItemInput

        with pytest.raises(ValidationError) as exc_info:
            HistoryItemInput(role="user", content="   ")

        assert "content must not be empty" in str(exc_info.value)

    def test_non_string_content_rejected(self) -> None:
        """Test that non-string content is rejected."""
        from validation import HistoryItemInput

        with pytest.raises(ValidationError) as exc_info:
            HistoryItemInput(role="user", content=123)

        # Pydantic v2 rejects non-string types before custom validator runs
        error_str = str(exc_info.value)
        assert "content" in error_str and ("string" in error_str or "String" in error_str)

    def test_content_max_length(self) -> None:
        """Test content length validation."""
        from validation import HistoryItemInput

        # Valid: max length
        item = HistoryItemInput(role="user", content="x" * 100000)
        assert len(item.content) == 100000

        # Invalid: over max length
        with pytest.raises(ValidationError) as exc_info:
            HistoryItemInput(role="user", content="x" * 100001)

        assert "exceeds maximum length" in str(exc_info.value)


class TestRunSuperstepInputValidation:
    """Test RunSuperstepInput validation."""

    def test_valid_minimal_input(self) -> None:
        """Test valid input with only required message."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Hello")
        assert input_data.message == "Hello"
        assert input_data.success_criteria is None
        assert input_data.history == []

    def test_valid_full_input(self) -> None:
        """Test valid input with all parameters."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Find a recipe",
            success_criteria="Recipe found",
            history=[
                {"role": "user", "content": "What's for dinner?"},
                {"role": "assistant", "content": "Let me search for recipes"}
            ]
        )
        assert input_data.message == "Find a recipe"
        assert input_data.success_criteria == "Recipe found"
        assert len(input_data.history) == 2

    def test_empty_message_rejected(self) -> None:
        """Test that empty message is rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="")

        assert "message must not be empty" in str(exc_info.value)

    def test_whitespace_only_message_rejected(self) -> None:
        """Test that whitespace-only message is rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="   ")

        assert "message must not be empty" in str(exc_info.value)

    def test_non_string_message_rejected(self) -> None:
        """Test that non-string message is rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message=123)

        # Pydantic v2 rejects non-string types before custom validator runs
        error_str = str(exc_info.value)
        assert "message" in error_str and ("string" in error_str or "String" in error_str)

    def test_message_max_length(self) -> None:
        """Test message length validation."""
        from validation import RunSuperstepInput

        # Valid: max length
        input_data = RunSuperstepInput(message="x" * 100000)
        assert len(input_data.message) == 100000

        # Invalid: over max length
        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="x" * 100001)

        assert "exceeds maximum length" in str(exc_info.value)

    def test_success_criteria_optional(self) -> None:
        """Test that success_criteria can be None."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Task",
            success_criteria=None
        )
        assert input_data.success_criteria is None

    def test_empty_success_criteria_rejected(self) -> None:
        """Test that empty success_criteria is rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="Task", success_criteria="")

        assert "success_criteria must not be empty" in str(exc_info.value)

    def test_success_criteria_max_length(self) -> None:
        """Test success_criteria length validation."""
        from validation import RunSuperstepInput

        # Valid: max length
        input_data = RunSuperstepInput(
            message="Task",
            success_criteria="x" * 10000
        )
        assert len(input_data.success_criteria) == 10000

        # Invalid: over max length
        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(
                message="Task",
                success_criteria="x" * 10001
            )

        assert "exceeds maximum length" in str(exc_info.value)

    def test_history_default_empty_list(self) -> None:
        """Test that history defaults to empty list."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Task")
        assert input_data.history == []
        assert isinstance(input_data.history, list)

    def test_valid_history(self) -> None:
        """Test valid history validation."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Task",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"}
            ]
        )
        assert len(input_data.history) == 2
        assert input_data.history[0]["role"] == "user"
        assert input_data.history[1]["role"] == "assistant"

    def test_history_with_system_messages(self) -> None:
        """Test history with system messages."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Task",
            history=[
                {"role": "system", "content": "Context"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"}
            ]
        )
        assert len(input_data.history) == 3
        assert input_data.history[0]["role"] == "system"

    def test_history_not_list_rejected(self) -> None:
        """Test that non-list history is rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="Task", history="not a list")

        # Pydantic v2 rejects non-list types before custom validator runs
        error_str = str(exc_info.value)
        assert "history" in error_str and ("list" in error_str or "List" in error_str)

    def test_history_max_length(self) -> None:
        """Test history length validation."""
        from validation import RunSuperstepInput

        # Valid: max length
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1000)
        ]
        input_data = RunSuperstepInput(message="Task", history=history)
        assert len(input_data.history) == 1000

        # Invalid: over max length
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1001)
        ]
        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(message="Task", history=history)

        assert "exceeds maximum length" in str(exc_info.value)

    def test_history_item_invalid_rejected(self) -> None:
        """Test that invalid history items are rejected."""
        from validation import RunSuperstepInput

        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(
                message="Task",
                history=[
                    {"role": "user", "content": "Hello"},
                    {"role": "invalid", "content": "Bad"}
                ]
            )

        assert "history[1]" in str(exc_info.value)

    def test_alternating_roles_valid(self) -> None:
        """Test that alternating user/assistant roles are valid."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Task",
            history=[
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"},
                {"role": "user", "content": "Q2"},
                {"role": "assistant", "content": "A2"}
            ]
        )
        assert len(input_data.history) == 4

    def test_alternating_roles_invalid(self) -> None:
        """Test that non-alternating roles are rejected."""
        from validation import RunSuperstepInput

        # Two users in a row
        with pytest.raises(ValidationError) as exc_info:
            RunSuperstepInput(
                message="Task",
                history=[
                    {"role": "user", "content": "Q1"},
                    {"role": "user", "content": "Q2"}
                ]
            )

        assert "should alternate" in str(exc_info.value)

    def test_alternating_roles_with_system(self) -> None:
        """Test alternation validation ignores system messages."""
        from validation import RunSuperstepInput

        # System messages should not break alternation check
        input_data = RunSuperstepInput(
            message="Task",
            history=[
                {"role": "system", "content": "Context"},
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"}
            ]
        )
        assert len(input_data.history) == 3


class TestValidateFunctionConvenience:
    """Test the convenience validation function."""

    def test_validate_run_superstep_input_function(self) -> None:
        """Test validate_run_superstep_input convenience function."""
        from validation import validate_run_superstep_input

        result = validate_run_superstep_input(
            message="Hello",
            success_criteria="OK",
            history=[]
        )
        assert result.message == "Hello"
        assert result.success_criteria == "OK"
        assert result.history == []

    def test_validate_function_with_defaults(self) -> None:
        """Test validate function with default parameters."""
        from validation import validate_run_superstep_input

        result = validate_run_superstep_input(message="Hello")
        assert result.message == "Hello"
        assert result.success_criteria is None
        assert result.history == []

    def test_validate_function_validation_error(self) -> None:
        """Test that validation errors are raised."""
        from validation import validate_run_superstep_input

        with pytest.raises(ValidationError):
            validate_run_superstep_input(message="")


class TestSidekickIntegration:
    """Test integration with sidekick.py."""

    def test_sidekick_imports_validation(self) -> None:
        """Test that sidekick imports validation module."""
        import sidekick

        # Verify the module imported validation
        assert hasattr(sidekick, 'validate_run_superstep_input')

    def test_sidekick_run_superstep_has_validation(self) -> None:
        """Test that run_superstep method has validation."""
        import sidekick
        import inspect

        # Check method signature includes validation
        source = inspect.getsource(sidekick.Sidekick.run_superstep)
        assert "validate_run_superstep_input" in source
        assert "ValidationError" in source


class TestValidationModuleAttributes:
    """Test that validation module exports all expected items."""

    def test_validation_module_has_pydantic_models(self) -> None:
        """Test that validation module exports Pydantic models."""
        import validation

        assert hasattr(validation, 'HistoryItemInput')
        assert hasattr(validation, 'RunSuperstepInput')
        assert hasattr(validation, 'SetupInput')
        assert hasattr(validation, 'WorkerInput')

    def test_validation_module_has_convenience_function(self) -> None:
        """Test that validation module exports convenience function."""
        import validation

        assert hasattr(validation, 'validate_run_superstep_input')
        assert callable(validation.validate_run_superstep_input)

    def test_pydantic_models_are_basemodel(self) -> None:
        """Test that models are Pydantic BaseModel."""
        from pydantic import BaseModel
        from validation import HistoryItemInput, RunSuperstepInput

        assert issubclass(HistoryItemInput, BaseModel)
        assert issubclass(RunSuperstepInput, BaseModel)


class TestErrorMessages:
    """Test that validation error messages are clear."""

    def test_error_message_on_empty_message(self) -> None:
        """Test error message for empty message."""
        from validation import RunSuperstepInput

        try:
            RunSuperstepInput(message="")
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "message" in error_msg.lower()
            assert "empty" in error_msg.lower()

    def test_error_message_on_invalid_role(self) -> None:
        """Test error message for invalid role."""
        from validation import HistoryItemInput

        try:
            HistoryItemInput(role="bad", content="Text")
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "role" in error_msg.lower()

    def test_error_message_on_non_alternating_roles(self) -> None:
        """Test error message for non-alternating roles."""
        from validation import RunSuperstepInput

        try:
            RunSuperstepInput(
                message="Task",
                history=[
                    {"role": "user", "content": "Q1"},
                    {"role": "user", "content": "Q2"}
                ]
            )
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "alternate" in error_msg.lower()


class TestBackwardCompatibility:
    """Test backward compatibility of validation."""

    def test_valid_inputs_still_work(self) -> None:
        """Test that previously valid inputs still work."""
        from validation import RunSuperstepInput

        # This should work as it's valid
        input_data = RunSuperstepInput(
            message="Find me a recipe",
            success_criteria="Recipe provided",
            history=[]
        )
        assert input_data.message == "Find me a recipe"

    def test_omitted_history_becomes_empty_list(self) -> None:
        """Test that omitted history defaults to empty list."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Task")
        assert input_data.history == []
        assert isinstance(input_data.history, list)

    def test_default_history_is_empty_list(self) -> None:
        """Test that default history is empty list."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Task")
        assert input_data.history == []


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_character_message(self) -> None:
        """Test valid single character message."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="A")
        assert input_data.message == "A"

    def test_message_with_special_characters(self) -> None:
        """Test message with special characters."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(
            message="Hello! @#$%^&*()_+-=[]{}|;:',.<>?/`~"
        )
        assert "@#$" in input_data.message

    def test_unicode_message(self) -> None:
        """Test message with unicode characters."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="你好 مرحبا שלום")
        assert "你好" in input_data.message

    def test_very_long_valid_message(self) -> None:
        """Test very long but valid message."""
        from validation import RunSuperstepInput

        long_msg = "A" * 50000
        input_data = RunSuperstepInput(message=long_msg)
        assert len(input_data.message) == 50000

    def test_message_with_newlines(self) -> None:
        """Test message with newlines."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Line 1\nLine 2\nLine 3")
        assert "\n" in input_data.message

    def test_message_with_tabs(self) -> None:
        """Test message with tabs."""
        from validation import RunSuperstepInput

        input_data = RunSuperstepInput(message="Col1\tCol2\tCol3")
        assert "\t" in input_data.message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
