"""
Factory for creating AI adapter instances.

Reads the AI_ADAPTER configuration and returns the appropriate adapter.
Uses a singleton pattern so the same adapter instance is reused across
the application lifetime.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from app.config import get_settings

if TYPE_CHECKING:
    from .adapter import AIAdapter

logger = logging.getLogger(__name__)

_adapter_instance: AIAdapter | None = None
_adapter_lock = threading.Lock()


def get_adapter() -> AIAdapter:
    """Return the singleton AI adapter based on configuration.

    The adapter type is determined by the AI_ADAPTER setting:
    - "openrouter" -> OpenRouterAdapter (HTTP calls to OpenRouter API)
    - "cli" -> CLIAdapter (spawns local CLI subprocess)
    - "mock" -> MockAIAdapter (fixture responses for testing)

    If the configured adapter cannot be instantiated, falls back to
    MockAIAdapter with a warning.

    Returns:
        A ready-to-use AIAdapter instance.
    """
    global _adapter_instance

    if _adapter_instance is not None:
        return _adapter_instance

    with _adapter_lock:
        # Double-check after acquiring lock
        if _adapter_instance is not None:
            return _adapter_instance

        settings = get_settings()
        adapter_name = settings.AI_ADAPTER

        logger.info("Initialising AI adapter: %s", adapter_name)

        try:
            if adapter_name == "openrouter":
                from .openrouter_adapter import OpenRouterAdapter

                _adapter_instance = OpenRouterAdapter()
                logger.info(
                    "OpenRouter adapter initialised (model=%s)",
                    settings.OPENROUTER_MODEL,
                )

            elif adapter_name == "cli":
                from .cli_adapter import CLIAdapter

                _adapter_instance = CLIAdapter()
                logger.info(
                    "CLI adapter initialised (tool=%s)",
                    settings.AI_CLI_TOOL,
                )

            elif adapter_name == "mock":
                from .mock_adapter import MockAIAdapter

                _adapter_instance = MockAIAdapter()
                logger.info("Mock AI adapter initialised")

            else:
                logger.warning(
                    "Unknown AI_ADAPTER value '%s'; falling back to mock adapter",
                    adapter_name,
                )
                from .mock_adapter import MockAIAdapter

                _adapter_instance = MockAIAdapter()

        except Exception:
            logger.exception(
                "Failed to initialise '%s' adapter; falling back to mock adapter",
                adapter_name,
            )
            from .mock_adapter import MockAIAdapter

            _adapter_instance = MockAIAdapter()

    return _adapter_instance


def reset_adapter() -> None:
    """Reset the singleton adapter instance.

    Useful in tests to force re-initialisation with different settings.
    """
    global _adapter_instance
    with _adapter_lock:
        _adapter_instance = None
        logger.debug("AI adapter singleton reset")
