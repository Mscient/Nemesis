# Architecture

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  localhost:5173                                         │
│  React + Vite + Tailwind + shadcn/ui                    │
└───────────────────────┬─────────────────────────────────┘
                        │  HTTP / SSE (proxy /api/*)
┌───────────────────────▼─────────────────────────────────┐
│  Backend                                                │
│  localhost:8000                                         │
│  FastAPI + Uvicorn (--reload)                           │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐ │
│  │  Routes    │  │  Services   │  │  Models/Schemas   │ │
│  │  health    │  │  ai_service │  │  SQLAlchemy ORM   │ │
│  │  chat      │  │  mock_ai    │  │  Pydantic v2      │ │
│  │  items     │  └──────┬──────┘  └──────────────────┘ │
│  └────────────┘         │                               │
└───────────────────────┬─┼───────────────────────────────┘
                        │ │
            ┌───────────┘ └──────────────┐
            ▼                            ▼
┌───────────────────┐        ┌───────────────────────────┐
│  SQLite           │        │  Anthropic Claude API      │
│  /data/db.sqlite3 │        │  (streaming, optional)     │
│  Docker volume    │        └───────────────────────────┘
└───────────────────┘
```

## Container Map

| Container | Image base | Port | Hot reload |
|-----------|-----------|------|-----------|
| `hackathon_backend` | python:3.12-slim | 8000 | uvicorn --reload |
| `hackathon_frontend` | node:20-alpine | 5173 | Vite HMR + polling |

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Database | SQLite | Zero-config, perfect for 12h hackathon |
| AI streaming | Server-Sent Events | Simpler than WebSockets, works with `fetch` |
| Package manager | uv (backend), pnpm (frontend) | Fast installs in Docker |
| Host deps | None | Docker Compose only – teammate zero setup |
| Auth | None (TODO) | Skipped for speed; add JWT in `core/auth.py` |
