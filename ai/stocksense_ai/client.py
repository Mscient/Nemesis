"""
Provider-agnostic LLM client with timeout, retry/backoff, and token cap.

Supported providers (set via LLM_PROVIDER env var):
  - mock       : deterministic, no network; safe for tests and offline demo
  - openai     : OpenAI Chat Completions API
  - anthropic  : Anthropic Messages API

All functions return raw text.  JSON parsing and schema validation live
in the individual task modules (suggester, explainer, proposer).

Design rules:
  - Never raises to the caller — all exceptions are caught and re-raised as
    LLMError so callers can fall back gracefully.
  - Never logs the prompt content (data minimisation).
  - Enforces max_tokens to cap cost and latency.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from stocksense_ai.config import get_config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails after retries."""


# ─── Mock Provider ─────────────────────────────────────────────────────────────

_MOCK_ANOMALY_RESPONSE = json.dumps({
    "suggestions": []
})

_MOCK_EXPLAIN_RESPONSE = (
    "Based on the computed data, the recommended action is supported by the "
    "reorder point calculation using the specified service level and lead time."
)

_MOCK_ADJUST_RESPONSE = json.dumps({
    "proposals": [
        {
            "start_date": "2026-10-15",
            "end_date": "2026-10-22",
            "multiplier": 1.3,
            "rationale": "Expected demand increase based on event notes.",
            "confidence": 0.75,
        }
    ]
})


def _mock_complete(prompt: str) -> str:
    """Deterministic mock response keyed on prompt content."""
    p = prompt.lower()
    if "anomal" in p and "suggestions" in p:
        return _MOCK_ANOMALY_RESPONSE
    if "proposals" in p:
        return _MOCK_ADJUST_RESPONSE
    return _MOCK_EXPLAIN_RESPONSE


# ─── OpenAI Provider ──────────────────────────────────────────────────────────

async def _openai_complete(prompt: str, cfg: Any) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": cfg.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": cfg.max_tokens,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
        resp = client.post(url, headers=headers, json=body)
        resp = await resp if asyncio.iscoroutine(resp) else resp  # type: ignore[assignment]
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ─── Anthropic Provider ────────────────────────────────────────────────────────

async def _anthropic_complete(prompt: str, cfg: Any) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": cfg.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": cfg.model,
        "max_tokens": cfg.max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


# ─── Public interface ─────────────────────────────────────────────────────────

async def complete(prompt: str) -> tuple[str, float]:
    """
    Send *prompt* to the configured LLM and return (response_text, latency_ms).

    Raises LLMError if all retries are exhausted or provider is unknown.
    Never raises any other exception type.
    """
    cfg = get_config()
    t0 = time.monotonic()

    if cfg.provider == "mock":
        text = _mock_complete(prompt)
        latency_ms = (time.monotonic() - t0) * 1000
        return text, latency_ms

    for attempt in range(cfg.max_retries + 1):
        try:
            if cfg.provider == "openai":
                text = await _openai_complete(prompt, cfg)
            elif cfg.provider == "anthropic":
                text = await _anthropic_complete(prompt, cfg)
            else:
                raise LLMError(f"Unknown LLM_PROVIDER={cfg.provider!r}")

            latency_ms = (time.monotonic() - t0) * 1000
            return text, latency_ms

        except LLMError:
            raise
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning(
                "LLM call failed (attempt %d/%d): %s — retrying in %ds",
                attempt + 1, cfg.max_retries + 1, exc, wait,
            )
            if attempt < cfg.max_retries:
                await asyncio.sleep(wait)
            else:
                latency_ms = (time.monotonic() - t0) * 1000
                raise LLMError(f"LLM call failed after {cfg.max_retries + 1} attempts: {exc}") from exc

    # Should never reach here
    raise LLMError("Unreachable")
