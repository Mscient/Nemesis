"""
is_enabled() and status() — thin wrappers around AIConfig.
client.py re-exports these for backward compatibility.
"""
import os
from stocksense_ai.schemas import AIStatus
from stocksense_ai.config import get_config


def is_enabled() -> bool:
    return get_config().enabled


def status() -> AIStatus:
    cfg = get_config()
    return AIStatus(
        enabled=cfg.enabled,
        provider=cfg.provider,
        model=cfg.model,
    )
