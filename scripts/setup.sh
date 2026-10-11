#!/usr/bin/env sh
# setup.sh – One-time project bootstrap.
# Only Docker and Git need to be installed on the host.

set -e

echo "🚀 Hackathon Starter setup"

# Check Docker
if ! command -v docker &> /dev/null; then
  echo "❌ Docker not found. Install Docker Desktop and try again."
  exit 1
fi

# Copy envs
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ Copied .env.example → .env (add your ANTHROPIC_API_KEY)"
fi

if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env
  echo "✅ Copied frontend/.env.example → frontend/.env"
fi

echo ""
echo "All set! Run: make dev"
