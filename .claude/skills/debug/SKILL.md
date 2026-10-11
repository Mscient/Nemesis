---
name: debug
description: Systematic debugging steps for this Docker-based stack.
---

# Debug Skill

## Container isn't starting
```bash
make logs                      # read the error
make shell-backend             # get a shell, run manually
docker compose ps              # check health
```

## Backend 500 errors
1. Check `make logs` for the Python traceback.
2. Open http://localhost:8000/docs – try the endpoint there.
3. Add a `breakpoint()` and `make shell-backend` to run interactively.

## Frontend API errors
1. Open DevTools → Network tab.
2. Check that Vite proxy is forwarding `/api/*` → `http://backend:8000`.
3. Verify `VITE_API_URL` in `frontend/.env`.
4. Try `curl http://localhost:8000/api/health` to confirm backend is alive.

## Streaming broken
- Confirm `Content-Type: text/event-stream` is returned.
- Disable any response buffering: `X-Accel-Buffering: no`.
- Never wrap SSE routes with a middleware that buffers responses.

## Hot reload not working
- Vite: ensure `watch: { usePolling: true }` in `vite.config.ts` (needed on Docker/Windows).
- FastAPI: ensure `--reload` flag and volume mount is `./backend:/app`.

## SQLite locked
- Only one container should write to the DB at a time.
- If you see "database is locked", restart with `make down && make dev`.
