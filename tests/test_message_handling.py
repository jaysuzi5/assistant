"""Tests for H7 message history race condition fix.

Tests message format conversion, validation, and integration with state machine.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from src.sidekick import Sidekick
from src.validation import validate_run_superstep_input


class TestMessagePreperation:
    """Tests for _prepare_messages method."""

    @pytest.fixture
    def sidekick(self):
        """Create a Sidekick instance for testing."""
        sk = Sidekick()
        return sk

    def test_simple_message_conversion(self, sidekick):
        """Test converting single user message to BaseMessage."""
        messages = sidekick._prepare_messages("Hello world", [])

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello world"

    def test_history_with_single_user_message(self, sidekick):
        """Test single message in history."""
        history = [{"role": "user", "content": "First question"}]
        messages = sidekick._prepare_messages("Follow-up", history)

        assert len(messages) == 2
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "First question"
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "Follow-up"

    def test_history_with_multiple_turns(self, sidekick):
        """Test converting multi-turn conversation history."""
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"}
        ]
        messages = sidekick._prepare_messages("Follow-up", history)

        assert len(messages) == 3
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "First question"
        assert isinstance(messages[1], AIMessage)
        assert messages[1].content == "First answer"
        assert isinstance(messages[2], HumanMessage)
        assert messages[2].content == "Follow-up"

    def test_history_with_system_message(self, sidekick):
        """Test history containing system messages."""
        history = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Question"}
        ]
        messages = sidekick._prepare_messages("Follow-up", history)

        assert len(messages) == 3
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert isinstance(messages[2], HumanMessage)

    def test_gradio_message_format_with_metadata(self, sidekick):
        """Test handling Gradio chat messages with extra fields."""
        history = [
            {
                "role": "user",
                "content": "First question",
                "metadata": None,
                "options": None
            },
            {
                "role": "assistant",
                "content": "Answer",
                "metadata": None,
                "options": None
            }
        ]
        messages = sidekick._prepare_messages("Next question", history)

        assert len(messages) == 3
        assert all(hasattr(m, 'content') for m in messages)
        assert messages[0].content == "First question"
        assert messages[1].content == "Answer"
        assert messages[2].content == "Next question"

    def test_empty_history(self, sidekick):
        """Test with empty history."""
        messages = sidekick._prepare_messages("Question", [])

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Question"

    def test_message_order_preservation(self, sidekick):
        """Test that message order is maintained through conversion."""
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"}
        ]
        messages = sidekick._prepare_messages("Q3", history)

        assert len(messages) == 5
        assert messages[0].content == "Q1"
        assert messages[1].content == "A1"
        assert messages[2].content == "Q2"
        assert messages[3].content == "A2"
        assert messages[4].content == "Q3"

    def test_skips_empty_messages_in_history(self, sidekick):
        """Test that empty messages in history are skipped."""
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "   "},  # Empty after strip
            {"role": "user", "content": "Follow-up"}
        ]
        messages = sidekick._prepare_messages("Next", history)

        # Should have: user Q, assistant (skipped), user follow-up, user next
        assert len(messages) == 3
        assert messages[0].content == "Question"
        assert messages[1].content == "Follow-up"
        assert messages[2].content == "Next"

    def test_handles_case_insensitive_roles(self, sidekick):
        """Test that role names are case-insensitive."""
        history = [
            {"role": "USER", "content": "Question"},
            {"role": "ASSISTANT", "content": "Answer"}
        ]
        messages = sidekick._prepare_messages("Follow-up", history)

        assert len(messages) == 3
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], HumanMessage)


class TestValidationLayer:
    """Tests for input validation."""

    def test_valid_simple_input(self):
        """Test validation passes for simple input."""
        result = validate_run_superstep_input("Hello", None, [])

        assert result.message == "Hello"
        assert result.history == []

    def test_valid_input_with_history(self):
        """Test validation passes with history."""
        history = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"}
        ]
        result = validate_run_superstep_input("Follow-up", None, history)

        assert result.message == "Follow-up"
        assert len(result.history) == 2

    def test_valid_input_with_success_criteria(self):
        """Test validation passes with success criteria."""
        result = validate_run_superstep_input("Task", "Complete it", [])

        assert result.message == "Task"
        assert result.success_criteria == "Complete it"

    def test_invalid_role_rejected(self):
        """Test validation rejects invalid role."""
        with pytest.raises(ValueError) as exc_info:
            validate_run_superstep_input(
                "task",
                None,
                [{"role": "invalid_role", "content": "message"}]
            )
        assert "role" in str(exc_info.value).lower()

    def test_empty_content_rejected(self):
        """Test validation rejects empty message content."""
        with pytest.raises(ValueError) as exc_info:
            validate_run_superstep_input(
                "task",
                None,
                [{"role": "user", "content": "   "}]  # Empty after strip
            )
        assert "content" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_gradio_format_accepted(self):
        """Test validation accepts Gradio message format."""
        history = [
            {
                "role": "user",
                "content": "Question",
                "metadata": None,
                "options": None
            }
        ]
        result = validate_run_superstep_input("Follow-up", None, history)

        assert len(result.history) == 1
        assert result.history[0]["role"] == "user"
        assert result.history[0]["content"] == "Question"

    def test_whitespace_trimmed(self):
        """Test that whitespace is trimmed from content."""
        history = [{"role": "user", "content": "  question  "}]
        result = validate_run_superstep_input("  follow-up  ", None, history)

        assert result.message == "follow-up"
        assert result.history[0]["content"] == "question"

    def test_empty_message_rejected(self):
        """Test validation rejects empty message."""
        with pytest.raises(ValueError):
            validate_run_superstep_input("", None, [])

    def test_very_long_message_rejected(self):
        """Test validation rejects messages over limit."""
        long_message = "a" * 100001
        with pytest.raises(ValueError):
            validate_run_superstep_input(long_message, None, [])


class TestIntegration:
    """Integration tests for message handling."""

    @pytest.fixture
    def sidekick(self):
        """Create a Sidekick instance."""
        sk = Sidekick()
        return sk

    def test_prepared_messages_are_base_message_list(self, sidekick):
        """Test that prepared messages are proper BaseMessage objects."""
        history = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"}
        ]
        messages = sidekick._prepare_messages("Follow-up", history)

        # All should be BaseMessage subclasses
        assert all(isinstance(m, BaseMessage) for m in messages)
        assert isinstance(messages, list)

    def test_complex_conversation_flow(self, sidekick):
        """Test complex conversation with multiple turns."""
        history = [
            {"role": "user", "content": "First query"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second query"},
            {"role": "assistant", "content": "Second response"},
            {"role": "user", "content": "Third query"}
        ]
        messages = sidekick._prepare_messages("Follow-up to third", history)

        # Should have all 6 messages
        assert len(messages) == 6

        # Verify types alternate correctly
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], HumanMessage)
        assert isinstance(messages[3], AIMessage)
        assert isinstance(messages[4], HumanMessage)
        assert isinstance(messages[5], HumanMessage)

    def test_validation_then_preparation_workflow(self, sidekick):
        """Test full workflow: validation then message preparation."""
        history_input = [
            {
                "role": "user",
                "content": "Previous question",
                "metadata": None  # Gradio format
            },
            {
                "role": "assistant",
                "content": "Previous answer",
                "metadata": None
            }
        ]

        # Step 1: Validate
        validated = validate_run_superstep_input(
            "New question",
            "Complete the task",
            history_input
        )

        # Step 2: Prepare messages
        messages = sidekick._prepare_messages(validated.message, validated.history)

        # Verify result
        assert len(messages) == 3
        assert all(isinstance(m, BaseMessage) for m in messages)
        assert messages[0].content == "Previous question"
        assert messages[1].content == "Previous answer"
        assert messages[2].content == "New question"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture
    def sidekick(self):
        """Create a Sidekick instance."""
        sk = Sidekick()
        return sk

    def test_unicode_content(self, sidekick):
        """Test handling of Unicode characters."""
        history = [{"role": "user", "content": "Hello 你好 مرحبا"}]
        messages = sidekick._prepare_messages("Follow-up", history)

        assert messages[0].content == "Hello 你好 مرحبا"

    def test_very_long_conversation(self, sidekick):
        """Test handling of very long conversation history."""
        history = [
            {"role": "user", "content": f"Q{i}"}
            for i in range(100)
        ]
        messages = sidekick._prepare_messages("New question", history)

        assert len(messages) == 101  # 100 from history + 1 new

    def test_messages_with_special_characters(self, sidekick):
        """Test handling of special characters."""
        special_content = "Hello!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        messages = sidekick._prepare_messages(special_content, [])

        assert messages[0].content == special_content

    def test_messages_with_newlines(self, sidekick):
        """Test handling of messages with newlines."""
        multi_line = "Line 1\nLine 2\nLine 3"
        messages = sidekick._prepare_messages(multi_line, [])

        assert messages[0].content == multi_line

    def test_messages_with_quotes(self, sidekick):
        """Test handling of messages with quotes."""
        quoted = 'He said "Hello" and she replied \'Hi\''
        messages = sidekick._prepare_messages(quoted, [])

        assert messages[0].content == quoted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
