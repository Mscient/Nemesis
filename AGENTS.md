# Hackathon Starter – Agent Rules (all AI tools)

> Same rules as CLAUDE.md. This file is picked up by Codex, Aider, Cursor, and similar tools.

## Run Commands
```bash
make dev          # start everything (hot reload)
make test         # backend pytest
make lint         # ruff + eslint
make seed         # demo data
```

## Core Constraints
- **No host installs** – Docker only. Use `docker compose run --rm <service> <cmd>`.
- **Plan before acting** – write checklist, then code.
- **Minimal dependencies** – justify every new package.
- **Mock AI** – `USE_MOCK_AI=true` skips Anthropic calls.

## Architecture
```
browser → localhost:5173 (Vite dev server)
              ↓ proxy /api/*
       localhost:8000 (FastAPI uvicorn)
              ↓
        SQLite /data/db.sqlite3
              ↓ (optional)
       Anthropic Claude API
```

## File Map
| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, CORS, routers |
| `backend/app/routes/` | One file per feature |
| `backend/app/schemas/` | Pydantic request/response models |
| `backend/app/services/ai_service.py` | Streaming AI calls |
| `frontend/src/lib/api-client.ts` | Typed HTTP wrapper |
| `frontend/src/components/ai/ChatBox.tsx` | Chat UI |
