#!/usr/bin/env sh
# generate-types.sh – wrapper called by `make types`.
# Proxies to the frontend container script.
docker compose run --rm frontend sh /app/scripts/generate-types.sh
