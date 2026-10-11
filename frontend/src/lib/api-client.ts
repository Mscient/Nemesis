/**
 * Typed API client for the Hackathon backend.
 *
 * All requests go through /api (proxied to backend:8000 by Vite in dev).
 * Import and call these functions instead of using raw `fetch` in components.
 */

import type { ChatRequest, Item, ItemCreate, ItemUpdate } from "@/types/api";

const BASE = "/api";

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as { detail?: string }).detail ?? res.statusText);
  }

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;

  return res.json() as Promise<T>;
}

// ── Health ────────────────────────────────────────────────────────────────────

export const api = {
  health: {
    get: () => request<{ status: string; version: string }>("/health"),
  },

  // ── Items ───────────────────────────────────────────────────────────────────

  items: {
    list: () => request<Item[]>("/items"),
    get: (id: number) => request<Item>(`/items/${id}`),
    create: (body: ItemCreate) =>
      request<Item>("/items", { method: "POST", body: JSON.stringify(body) }),
    update: (id: number, body: ItemUpdate) =>
      request<Item>(`/items/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: (id: number) =>
      request<void>(`/items/${id}`, { method: "DELETE" }),
  },

  // ── Chat (SSE streaming) ─────────────────────────────────────────────────────

  chat: {
    /**
     * Opens an SSE stream for a chat message.
     * Returns a ReadableStreamDefaultReader<string>.
     *
     * Usage:
     *   const reader = await api.chat.stream({ message });
     *   while (true) {
     *     const { done, value } = await reader.read();
     *     if (done || value === '[DONE]') break;
     *     setContent(prev => prev + value);
     *   }
     */
    stream: async (body: ChatRequest): Promise<ReadableStreamDefaultReader<string>> => {
      const res = await fetch(`${BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Chat failed: ${res.statusText}`);
      }

      const reader = res.body
        .pipeThrough(new TextDecoderStream())
        .getReader();

      return reader;
    },
  },
};
