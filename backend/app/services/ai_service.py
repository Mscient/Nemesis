"""Anthropic Claude streaming service."""

import logging
from collections.abc import AsyncGenerator

import anthropic

from app.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = "app/prompts/system.md"


def _load_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are a helpful assistant."


async def anthropic_stream(
    message: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Yield text chunks from Anthropic Claude via streaming."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = _load_system_prompt()

    logger.info("Calling Anthropic API with message length=%d", len(message))

    with client.messages.stream(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        for text_chunk in stream.text_stream:
            yield text_chunk
