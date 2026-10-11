"""Mock AI streamer – returns a fake response without calling Anthropic.

Activated when USE_MOCK_AI=true or when the real API key is missing.
Streams character-by-character to simulate the real streaming experience.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

_CANNED_RESPONSE = (
    "Thanks for your message! I'm the mock AI assistant running in offline mode. "
    "Set USE_MOCK_AI=false in your .env and add a real ANTHROPIC_API_KEY to enable "
    "Claude. For now, I can confirm that streaming is working correctly — each chunk "
    "arrives one word at a time, just like the real API. 🚀"
)


async def mock_stream(message: str) -> AsyncGenerator[str, None]:
    """Yield fake response tokens with a small delay to simulate streaming."""
    logger.info("Mock AI responding to: %s", message[:50])
    words = _CANNED_RESPONSE.split()
    for i, word in enumerate(words):
        chunk = word if i == 0 else f" {word}"
        yield chunk
        await asyncio.sleep(0.04)  # ~25 words/sec – fast but visible
