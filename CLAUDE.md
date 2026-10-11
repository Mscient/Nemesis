# Hackathon Starter – Agent Rules

## Quick Run Commands
```bash
make dev          # start everything (hot reload)
make test         # run backend tests
make lint         # ruff + eslint
make seed         # load demo data
make shell-backend  # debug backend
make shell-frontend # debug frontend
```

## Stack Summary
| Layer     | Tech |
|-----------|------|
| Frontend  | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| Backend   | Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy |
| AI        | Anthropic Claude (SSE streaming) |
| DB        | SQLite (file at `/data/db.sqlite3`) |
| Tooling   | Docker Compose · uv · pnpm · ruff · eslint |

## Project-Wide Rules
1. **Plan first** – before any large change, write a short checklist in a code block, then act.
2. **Docker only** – never install Node, Python, or uv on the host. Run everything via `docker compose run`.
3. **Minimal deps** – don't add a package without stating why.
4. **Mock AI** – set `USE_MOCK_AI=true` in `.env` to avoid burning API credits during development.
5. **Hackathon mode** – prefer done over perfect. Bias toward shipping.

## Key Files
- `backend/app/main.py` – FastAPI entry point
- `backend/app/config.py` – all env config via pydantic-settings
- `backend/app/services/ai_service.py` – Anthropic streaming
- `backend/app/services/mock_ai.py` – fake streamer for offline dev
- `frontend/src/lib/api-client.ts` – typed fetch wrapper
- `frontend/src/components/ai/ChatBox.tsx` – streaming chat UI

## Adding a New Backend Endpoint
1. Create `backend/app/routes/my_feature.py` (copy `items.py` as reference)
2. Add schemas to `backend/app/schemas/`
3. Register router in `backend/app/main.py` with prefix `/api`
4. Run `make types` to regenerate TS types

## Environment Variables
Copy `.env.example` → `.env` and fill in `ANTHROPIC_API_KEY`.
