---
name: backend
description: FastAPI layering, endpoint patterns, and service conventions for this hackathon project.
---

# Backend Skill

## Layering
```
routes/      ← HTTP: validate input, call service, return response
services/    ← business logic, AI calls, DB queries
models/      ← SQLAlchemy ORM models (DB tables)
schemas/     ← Pydantic models (request/response shapes)
core/        ← cross-cutting: logging, error handlers, auth
```

## Adding an Endpoint (copy `items.py` as reference)
1. `app/routes/my_feature.py` – define `router = APIRouter(prefix="/api/my-feature")`
2. `app/schemas/my_feature.py` – Pydantic `BaseModel` for request and response
3. `app/models/my_feature.py` – SQLAlchemy `Base` subclass if you need persistence
4. Register in `app/main.py`: `app.include_router(my_feature.router)`

## Dependency Injection
```python
# Get DB session
async def endpoint(db: Session = Depends(get_db)):
    ...

# Get settings
async def endpoint(settings: Settings = Depends(get_settings)):
    ...
```

## Streaming (SSE)
Use `StreamingResponse` with `media_type="text/event-stream"`.
See `app/routes/chat.py` for the full pattern including error handling and mock fallback.

## AI Service
- Real: `app/services/ai_service.py` – uses Anthropic SDK with streaming.
- Mock: `app/services/mock_ai.py` – yields fake chunks, activated by `USE_MOCK_AI=true`.
- Always wrap Anthropic calls in try/except; fall back to mock on failure.

## Error Handling
- Raise `HTTPException` for known errors.
- Unhandled exceptions are caught by the global handler in `app/core/errors.py`.
- Log with `app/core/logging.py` structured logger (no `print()`).

## Database
- Session: `get_db()` generator in `app/db.py`.
- Migrations: Not used (hackathon). `Base.metadata.create_all()` runs on startup.
- SQLite file lives at `DATABASE_URL` (mounted Docker volume).
