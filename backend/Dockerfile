FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required by asyncpg / psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy local packages first (build context is the repo root)
COPY core /core
COPY ai /ai

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e /core -e /ai

# Copy backend source
COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
