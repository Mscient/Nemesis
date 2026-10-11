#!/usr/bin/env sh
# generate-types.sh – Generates TypeScript types from the running backend's OpenAPI schema.
# Usage: make types  (runs inside the frontend container)

set -e

BACKEND_URL="${VITE_API_URL:-http://backend:8000}"
OUT="src/types/api.ts"

echo "Fetching OpenAPI schema from $BACKEND_URL/openapi.json …"
curl -sf "$BACKEND_URL/openapi.json" -o /tmp/openapi.json

echo "Generating TypeScript types → $OUT"
pnpm dlx openapi-typescript /tmp/openapi.json -o "$OUT"

echo "✅ Types written to $OUT"
