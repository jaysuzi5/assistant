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


# Validate on module load
validate_timeout_config()
