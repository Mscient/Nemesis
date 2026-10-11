/**
 * API type definitions.
 * These are hand-written to match the backend OpenAPI schema.
 * Run `make types` to regenerate automatically once the backend is running.
 */

export interface HealthResponse {
  status: string;
  version: string;
}

// ── Items ─────────────────────────────────────────────────────────────────────

export interface Item {
  id: number;
  title: string;
  description: string;
  created_at: string; // ISO8601
}

export interface ItemCreate {
  title: string;
  description?: string;
}

export interface ItemUpdate {
  title?: string;
  description?: string;
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

export interface ChatChunk {
  chunk?: string;
  error?: string;
}
