---
name: hackathon-mode
description: Speed over perfection. Bias toward shipping. Cut scope aggressively.
---

# Hackathon Mode

## Principles
- **Done > perfect.** A working prototype beats elegant unfinished code.
- **Cut scope aggressively.** If a feature is not in the demo script, skip it.
- **Mock everything expensive.** Use `USE_MOCK_AI=true`, hardcoded data, and fake endpoints to unblock UI work.
- **One happy path.** Only handle the error case if the demo breaks without it.
- **No premature abstractions.** Duplicate code is fine for 12 hours.

## Permitted shortcuts
- Inline SQL instead of a service layer for one-off queries.
- Hardcoded user ID instead of real auth (add a `TODO: replace with JWT`).
- `console.log` debugging left in.
- No pagination on lists (limit 100 rows).
- SQLite instead of Postgres.

## Forbidden shortcuts
- Committing secrets.
- Skipping the health check endpoint (judges will hit it).
- Breaking hot reload (never delete the volume mount).
