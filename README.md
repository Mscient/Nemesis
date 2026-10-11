# 🚀 Hackathon Starter

> Clone → `make dev` → build in 12 hours.

## Quick Start

```bash
git clone <repo-url> my-hack
cd my-hack
cp .env.example .env          # add your ANTHROPIC_API_KEY
make dev                       # builds images + starts with hot reload
```

| Service   | URL |
|-----------|-----|
| Frontend  | http://localhost:5173 |
| Backend   | http://localhost:8000 |
| API Docs  | http://localhost:8000/docs |

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 18 · Vite · TypeScript · Tailwind CSS · shadcn/ui |
| Backend   | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy · SQLite |
| AI        | Anthropic Claude (streaming SSE) |
| Tooling   | Docker Compose · uv · pnpm · ruff · ESLint |

## Requirements

**Only Docker (with Compose v2) and Git are needed on the host.**
Node, Python, pnpm, and uv all run inside containers.

## Make Targets

| Command | Description |
|---------|-------------|
| `make dev` | Start both services with hot reload |
| `make build` | Rebuild images |
| `make down` | Stop containers |
| `make test` | Run backend tests |
| `make lint` | ruff + eslint |
| `make seed` | Load demo data |
| `make shell-backend` | Shell into backend container |
| `make shell-frontend` | Shell into frontend container |
| `make types` | Regenerate TS types from OpenAPI |

## Mock AI

Set `USE_MOCK_AI=true` in `.env` to skip real Anthropic calls.
The mock streamer returns a fake response character-by-character so you
can develop the UI without burning API credits.

## Project Structure

```
hackathon-starter/
├── backend/          FastAPI + SQLite + Anthropic SDK
├── frontend/         React + Vite + shadcn/ui
├── docs/             Problem statement, user stories, architecture
├── scripts/          Host-level helper scripts
└── .claude/skills/   AI-agent skill files
```

## Adding a Feature

1. `backend/app/routes/my_feature.py` – copy `items.py`
2. Register router in `backend/app/main.py`
3. `make types` – regenerate TS types
4. Build the UI in `frontend/src/pages/`

## Demo Script

See [`docs/demo-script.md`](docs/demo-script.md) for the 2-minute pitch flow.

---

Built for speed. Ship it. 🏆
