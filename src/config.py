"""Configuration module for Sidekick with timeout settings.

This module provides centralized configuration for timeouts and other
settings used throughout the Sidekick application.
"""

import os
from typing import Optional

# ============================================================================
# TIMEOUT CONFIGURATION (in seconds)
# ============================================================================

# Default timeout for external API calls (requests library)
# Used for: push notifications, web search, Wikipedia, etc.
DEFAULT_REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "10.0"))

# Pushover-specific timeout (may differ from default)
# Pushover notifications should complete quickly; 5 seconds is reasonable
PUSHOVER_REQUEST_TIMEOUT: float = float(
    os.getenv("PUSHOVER_REQUEST_TIMEOUT", "5.0")
)

# Web search (Serper API) timeout
# Searches can take longer due to remote indexing; 15 seconds is reasonable
SERPER_REQUEST_TIMEOUT: float = float(
    os.getenv("SERPER_REQUEST_TIMEOUT", "15.0")
)

# Wikipedia API timeout
# Wikipedia is typically fast; 10 seconds is reasonable
WIKIPEDIA_REQUEST_TIMEOUT: float = float(
    os.getenv("WIKIPEDIA_REQUEST_TIMEOUT", "10.0")
)

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Worker LLM model name
# Examples: "gpt-4o-mini", "gpt-4", "claude-3-5-sonnet-20241022", etc.
WORKER_LLM_MODEL: str = os.getenv("WORKER_LLM_MODEL", "gpt-4o-mini")

# Evaluator LLM model name
# Can be the same as WORKER_LLM_MODEL or a different model
# Examples: "gpt-4o-mini", "gpt-4", "claude-3-5-sonnet-20241022", etc.
EVALUATOR_LLM_MODEL: str = os.getenv("EVALUATOR_LLM_MODEL", "gpt-4o-mini")

# OpenAI API base URL (for using proxies or alternative endpoints)
# Default: OpenAI's official API endpoint
OPENAI_API_BASE: Optional[str] = os.getenv("OPENAI_API_BASE", None)

# OpenAI API version (for Azure OpenAI or other implementations)
OPENAI_API_VERSION: Optional[str] = os.getenv("OPENAI_API_VERSION", None)

# ============================================================================
# API ENDPOINTS CONFIGURATION
# ============================================================================

# Pushover API endpoint for push notifications
# Default: Official Pushover service
PUSHOVER_API_URL: str = os.getenv(
    "PUSHOVER_API_URL",
    "https://api.pushover.net/1/messages.json"
)

# Google Serper API endpoint for web search
# Default: Official Serper service
SERPER_API_URL: str = os.getenv(
    "SERPER_API_URL",
    "https://google.serper.dev/search"
)

# ============================================================================
# VALIDATION
# ============================================================================

def validate_timeout_config() -> None:
    """Validate that all timeout values are positive.

    Raises:
        ValueError: If any timeout is not positive.
    """
    timeouts = {
        "DEFAULT_REQUEST_TIMEOUT": DEFAULT_REQUEST_TIMEOUT,
        "PUSHOVER_REQUEST_TIMEOUT": PUSHOVER_REQUEST_TIMEOUT,
        "SERPER_REQUEST_TIMEOUT": SERPER_REQUEST_TIMEOUT,
        "WIKIPEDIA_REQUEST_TIMEOUT": WIKIPEDIA_REQUEST_TIMEOUT,
    }

    for name, value in timeouts.items():
        if value <= 0:
            raise ValueError(
                f"{name} must be positive, got {value}"
            )


def validate_llm_config() -> None:
    """Validate that LLM configuration values are not empty.

    Raises:
        ValueError: If any required LLM config is empty.
    """
    if not WORKER_LLM_MODEL or not WORKER_LLM_MODEL.strip():
        raise ValueError("WORKER_LLM_MODEL must not be empty")

    if not EVALUATOR_LLM_MODEL or not EVALUATOR_LLM_MODEL.strip():
        raise ValueError("EVALUATOR_LLM_MODEL must not be empty")


def validate_api_endpoints() -> None:
    """Validate that API endpoints are valid URLs.

    Raises:
        ValueError: If any endpoint is not a valid URL.
    """
    endpoints = {
        "PUSHOVER_API_URL": PUSHOVER_API_URL,
        "SERPER_API_URL": SERPER_API_URL,
    }

    for name, url in endpoints.items():
        if not url or not url.strip():
            raise ValueError(f"{name} must not be empty")
        if not url.startswith(("http://", "https://")):
            raise ValueError(
                f"{name} must be a valid URL (http:// or https://), got: {url}"
            )


# Validate on module load
validate_timeout_config()
validate_llm_config()
validate_api_endpoints()
