---
name: frontend
description: React + Vite + TypeScript + Tailwind + shadcn/ui conventions for this hackathon project.
---

# Frontend Skill

## Component Conventions

- **Pages** live in `src/pages/` and are route-level components (no logic, compose features).
- **Feature components** live in `src/components/` grouped by domain (`ai/`, `layout/`, `ui/`).
- **`src/components/ui/`** contains shadcn/ui primitives only – do not edit them directly.

## Styling
- Use Tailwind utility classes; no custom CSS files unless absolutely necessary.
- Prefer `cn()` from `src/lib/utils.ts` to merge class names conditionally.
- Dark mode is class-based (`dark:`). Toggle via `document.documentElement.classList`.

## Data Fetching
- All server state goes through **TanStack React Query**.
- Use `src/lib/api-client.ts` for all HTTP calls (never raw `fetch` in components).
- Mutation pattern:
  ```ts
  const { mutate } = useMutation({ mutationFn: api.createItem });
  ```

## Adding a New Page
1. Create `src/pages/MyPage.tsx`
2. Add route to `src/App.tsx` inside `<Routes>`
3. Add nav link to `src/components/layout/Navbar.tsx`

## Streaming (SSE)
- Use the existing `ChatBox.tsx` pattern: open a `fetch` stream, read chunks with `ReadableStream`, append to state.
- Never use WebSockets unless explicitly required.

## Type Safety
- All API types live in `src/types/api.ts` (generated from OpenAPI).
- Run `make types` after any backend schema change.
- Avoid `any`; use `unknown` and narrow.
