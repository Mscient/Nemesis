"""Chat endpoint – streams AI responses as Server-Sent Events."""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    body: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """
    POST /api/chat
    Accepts a message, returns an SSE stream of AI chunks.

    Frontend reads:
        data: {"chunk": "..."}\n\n
        data: [DONE]\n\n
    """
    use_mock = settings.use_mock_ai or not settings.anthropic_api_key.startswith("sk-ant-api")

    if use_mock:
        from app.services.mock_ai import mock_stream

        generator = mock_stream(body.message)
    else:
        from app.services.ai_service import anthropic_stream

        try:
            generator = anthropic_stream(body.message, settings)
        except Exception as exc:
            logger.error("Anthropic call failed, falling back to mock: %s", exc)
            from app.services.mock_ai import mock_stream

            generator = mock_stream(body.message)

    return StreamingResponse(
        _sse_wrapper(generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


async def _sse_wrapper(generator):
    """Wrap an async generator of text chunks into SSE format."""
    try:
        async for chunk in generator:
            payload = json.dumps({"chunk": chunk})
            yield f"data: {payload}\n\n"
    except Exception as exc:
        logger.error("Streaming error: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"
