"""AI enabled/disabled check and status."""
import os
from stocksense_ai.schemas import AIStatus


def is_enabled() -> bool:
    return os.getenv("AI_ENABLED", "false").lower() == "true"


def status() -> AIStatus:
    return AIStatus(
        enabled=is_enabled(),
        provider=os.getenv("LLM_PROVIDER", "mock"),
        model=os.getenv("LLM_MODEL", "mock-model"),
    )
