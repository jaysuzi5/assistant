"""Input validation module for Sidekick using Pydantic.

This module provides comprehensive input validation for all user-facing
API methods using Pydantic BaseModel. It ensures that all inputs are
well-formed before processing, catching errors early and providing
clear error messages to users.

Key components:
- RunSuperstepInput: Validates message, success_criteria, and history
- HistoryItemInput: Validates individual history items
- Custom validators for specific constraints
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Optional, Any
import re


class HistoryItemInput(BaseModel):
    """Validates a single history item.

    History items represent conversation turns with a role and content.

    Attributes:
        role: Either "user", "assistant", or "system"
        content: The message content (non-empty string)

    Raises:
        ValueError: If role is invalid or content is empty
    """

    role: str = Field(
        ...,
        description="Role of the speaker (user, assistant, or system)"
    )
    content: str = Field(
        ...,
        description="Message content (must be non-empty)"
    )

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate that role is one of the allowed values."""
        v = v.strip().lower()
        if v not in ('user', 'assistant', 'system'):
            raise ValueError(
                f"role must be 'user', 'assistant', or 'system', got '{v}'"
            )
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate that content is a non-empty string."""
        if not isinstance(v, str):
            raise ValueError(f"content must be a string, got {type(v).__name__}")

        # Strip leading/trailing whitespace
        v = v.strip()

        if not v:
            raise ValueError("content must not be empty")

        # Content should be reasonably long (at least 1 char after strip)
        if len(v) > 100000:
            raise ValueError(
                f"content exceeds maximum length of 100,000 characters "
                f"(got {len(v)})"
            )

        return v

    class Config:
        """Pydantic configuration for HistoryItemInput."""
        str_strip_whitespace = False  # We handle whitespace manually


class RunSuperstepInput(BaseModel):
    """Validates input for Sidekick.run_superstep() method.

    Attributes:
        message: The user's task request (non-empty string)
        success_criteria: Task completion criteria (optional, defaults to generic)
        history: Previous conversation turns (list of role/content dicts)

    Raises:
        ValueError: If any validation constraint is violated
    """

    message: str = Field(
        ...,
        description="User's task request message (non-empty)"
    )
    success_criteria: Optional[str] = Field(
        default=None,
        description="Task completion criteria (optional)"
    )
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation history"
    )

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate that message is a non-empty string."""
        if not isinstance(v, str):
            raise ValueError(
                f"message must be a string, got {type(v).__name__}"
            )

        # Strip and validate
        v = v.strip()

        if not v:
            raise ValueError("message must not be empty")

        if len(v) > 100000:
            raise ValueError(
                f"message exceeds maximum length of 100,000 characters "
                f"(got {len(v)})"
            )

        return v

    @field_validator('success_criteria')
    @classmethod
    def validate_success_criteria(cls, v: Optional[str]) -> Optional[str]:
        """Validate that success_criteria is either None or a non-empty string.

        Empty strings are treated as None (will use default criteria).
        """
        if v is None:
            return v

        if not isinstance(v, str):
            raise ValueError(
                f"success_criteria must be a string or None, got {type(v).__name__}"
            )

        # Strip and validate
        v = v.strip()

        # Treat empty strings as None (will use default)
        if not v:
            return None

        if len(v) > 10000:
            raise ValueError(
                f"success_criteria exceeds maximum length of 10,000 characters "
                f"(got {len(v)})"
            )

        return v

    @field_validator('history')
    @classmethod
    def validate_history(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate that history is a list of valid history items."""
        if not isinstance(v, list):
            raise ValueError(
                f"history must be a list, got {type(v).__name__}"
            )

        if len(v) > 1000:
            raise ValueError(
                f"history exceeds maximum length of 1000 items (got {len(v)})"
            )

        # Validate each history item
        validated_items = []
        for i, item in enumerate(v):
            if not isinstance(item, dict):
                raise ValueError(
                    f"history[{i}] must be a dict, got {type(item).__name__}"
                )

            try:
                validated_item = HistoryItemInput(**item)
                validated_items.append({
                    "role": validated_item.role,
                    "content": validated_item.content
                })
            except ValueError as e:
                raise ValueError(f"history[{i}]: {str(e)}")

        return validated_items

    @model_validator(mode='after')
    def validate_alternating_roles(self) -> 'RunSuperstepInput':
        """Validate that history alternates between user and assistant.

        This check helps catch malformed histories that might confuse the LLM.
        The pattern should be: user, assistant, [user, assistant, ...], user

        Note: We allow system messages at the start for context injection.
        """
        if not self.history:
            return self

        # Filter out system messages for role alternation check
        non_system = [h for h in self.history if h['role'] != 'system']

        if not non_system:
            # Only system messages, which is fine
            return self

        # Check that non-system messages alternate between user and assistant
        expected_role = 'user'
        for i, item in enumerate(non_system):
            if item['role'] != expected_role:
                raise ValueError(
                    f"history: messages should alternate between user and "
                    f"assistant. Expected '{expected_role}' at position {i}, "
                    f"got '{item['role']}'"
                )
            # Toggle expected role
            expected_role = 'assistant' if expected_role == 'user' else 'user'

        return self


class SetupInput(BaseModel):
    """Validates input for Sidekick.setup() method.

    The setup() method doesn't take parameters, but this model serves as
    documentation of what setup() does and validates.

    Note: setup() doesn't require input validation in the traditional sense,
    but we document it here for completeness.
    """

    pass


class WorkerInput(BaseModel):
    """Validates input for the worker node (internal use).

    The worker is invoked internally with LangGraph state, which has
    its own validation through State TypedDict.

    Attributes:
        state: The current graph state containing messages, criteria, etc.

    Note: Worker input is validated through State definition, not this model.
    """

    pass


def validate_run_superstep_input(
    message: str,
    success_criteria: Optional[str] = None,
    history: List[Dict[str, str]] = None
) -> RunSuperstepInput:
    """Validate and return RunSuperstepInput.

    This is a convenience function that validates all inputs for run_superstep()
    and returns a validated model instance.

    Args:
        message: User's task request
        success_criteria: Task completion criteria (optional)
        history: Previous conversation history (optional)

    Returns:
        RunSuperstepInput: Validated input model

    Raises:
        ValueError: If any validation fails (from Pydantic)

    Example:
        >>> validated = validate_run_superstep_input(
        ...     message="Find me a recipe",
        ...     success_criteria="Recipe found and formatted",
        ...     history=[]
        ... )
        >>> print(validated.message)
        'Find me a recipe'
    """
    if history is None:
        history = []

    return RunSuperstepInput(
        message=message,
        success_criteria=success_criteria,
        history=history
    )
