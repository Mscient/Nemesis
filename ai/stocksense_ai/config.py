"""
Configuration for stocksense_ai.
All settings are read from environment variables.
No secrets are logged or stored in this module.
"""
from __future__ import annotations
import os


class AIConfig:
    """Read-only config snapshot from environment."""

    def __init__(self) -> None:
        self.enabled: bool = os.getenv("AI_ENABLED", "false").lower() == "true"
        self.provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
        self.model: str = os.getenv("LLM_MODEL", "mock-model")
        self.api_key: str = os.getenv("LLM_API_KEY", "")
        self.timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "30"))
        self.max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
        self.max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Raise ValueError if a real provider is chosen but the key is missing."""
        if self.enabled and self.provider in ("anthropic", "openai") and not self.api_key:
            raise ValueError(
                f"AI_ENABLED=true and LLM_PROVIDER={self.provider} but LLM_API_KEY is empty."
            )


def get_config() -> AIConfig:
    """Return a fresh config snapshot (re-reads env on every call)."""
    return AIConfig()
