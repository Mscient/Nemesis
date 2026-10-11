FROM python:3.12-slim

# ── Install uv (fast Python package manager) ──────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# ── Install dependencies (cached layer) ───────────────────────────────────────
COPY pyproject.toml ./

# Install all deps into /opt/venv (outside /app so host bind mount cannot shadow it)
RUN uv venv /opt/venv && uv pip install \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    sqlalchemy \
    anthropic \
    python-dotenv \
    httpx \
    pytest \
    pytest-asyncio \
    ruff

RUN mkdir -p /data

# ── Copy source (overridden by bind mount in dev) ─────────────────────────────
COPY . .

EXPOSE 8000

# Hot-reload with uvicorn; --reload watches all .py files under /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
