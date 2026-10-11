FROM python:3.12-slim

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install production dependencies only
COPY backend/pyproject.toml ./pyproject.toml
RUN uv venv /opt/venv && uv pip install \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic-settings>=2.4.0" \
    "sqlalchemy>=2.0.0" \
    "anthropic>=0.34.0" \
    "python-dotenv>=1.0.0" \
    "httpx>=0.27.0"

# Create directory for SQLite
RUN mkdir -p /data

# Copy backend source code into /app
COPY backend /app

EXPOSE 8000

# Start uvicorn with dynamic $PORT support (defaults to 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
