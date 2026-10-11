.PHONY: dev build down logs lint test seed shell-backend shell-frontend types

# ── Core ──────────────────────────────────────────────────────────────────────
dev:          ## Start both services with hot reload
	docker compose up --build

build:        ## Build images without starting
	docker compose build

down:         ## Stop and remove containers
	docker compose down

logs:         ## Tail all container logs
	docker compose logs -f

# ── Quality ───────────────────────────────────────────────────────────────────
lint:         ## Run ruff (backend) + eslint (frontend) via Docker
	docker compose run --rm backend uv run ruff check app tests
	docker compose run --rm frontend pnpm lint

test:         ## Run backend pytest suite
	docker compose run --rm backend uv run pytest -v

# ── Data ──────────────────────────────────────────────────────────────────────
seed:         ## Insert demo data into SQLite
	docker compose run --rm backend uv run python scripts/seed.py

# ── Shells ────────────────────────────────────────────────────────────────────
shell-backend:  ## Open a bash shell in the backend container
	docker compose run --rm backend bash

shell-frontend: ## Open a sh shell in the frontend container
	docker compose run --rm frontend sh

# ── Type generation ───────────────────────────────────────────────────────────
types:        ## Generate TS types from OpenAPI schema (backend must be running)
	docker compose run --rm frontend sh /app/scripts/generate-types.sh
