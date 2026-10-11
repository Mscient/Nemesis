/**
 * api.ts — thin fetch wrapper for the StockSense FastAPI backend.
 * All calls go through Vite's /api proxy → http://localhost:8000
 */

// ─── Auth Shapes ─────────────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user?: User | null
}

export const authStorage = {
  getToken: (): string | null => localStorage.getItem('stocksense_token'),
  setToken: (token: string | null) => {
    if (token) localStorage.setItem('stocksense_token', token)
    else localStorage.removeItem('stocksense_token')
  },
  getUser: (): User | null => {
    const raw = localStorage.getItem('stocksense_user')
    try {
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },
  setUser: (user: User | null) => {
    if (user) localStorage.setItem('stocksense_user', JSON.stringify(user))
    else localStorage.removeItem('stocksense_user')
  },
  clear: () => {
    localStorage.removeItem('stocksense_token')
    localStorage.removeItem('stocksense_user')
  },
}

// ─── Backend shape (matches Pydantic schemas) ──────────────────────────────

export interface SkuSummary {
  sku: string
  name: string | null
  status: 'OK' | 'REORDER' | 'AT_RISK'
  inventory_position: number
  reorder_point: number | null
  on_hand: number
  on_order: number
  is_synthetic: boolean
}

export interface SkuParams {
  lead_time_days: number
  lead_time_std_days: number
  unit_cost: number
  order_cost: number
  holding_cost_per_unit_per_year: number
  stockout_penalty_per_unit: number
  moq: number
  pack_size: number
  max_storage: number | null
  service_level: number
  on_hand: number
  on_order: number
}

export interface SkuDetail {
  sku: string
  name: string | null
  status: 'OK' | 'REORDER' | 'AT_RISK'
  params: SkuParams
  is_synthetic: boolean
}

export interface ForecastResponse {
  sku: string
  horizon_days: number
  model_used: string
  avg_daily_demand: number
  sigma_daily: number
  predictions: number[]
  confidence: string
  warnings: string[]
}

export interface RecommendationResponse {
  sku: string
  action: 'ORDER_NOW' | 'HOLD' | 'AT_RISK'
  order_quantity: number
  inventory_position: number
  reorder_point: number
  safety_stock: number
  warnings: string[]
  confidence: string
}

export interface HealthResponse {
  status: string
  timestamp: string
}

// ─── Helpers ───────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = authStorage.getToken()
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(path, { ...options, headers })
  if (!res.ok) {
    if (res.status === 401 && path !== '/api/auth/login' && path !== '/api/auth/register') {
      authStorage.clear()
    }
    const errBody = await res.json().catch(() => null)
    const msg =
      errBody?.detail ||
      errBody?.error?.message ||
      `${options?.method ?? 'GET'} ${path} → ${res.status}`
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

// ─── API functions ─────────────────────────────────────────────────────────

export const api = {
  health: () => apiFetch<HealthResponse>('/api/health'),

  /** Auth endpoints */
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await apiFetch<AuthResponse>('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    authStorage.setToken(res.access_token)
    if (res.user) authStorage.setUser(res.user)
    return res
  },

  register: async (email: string, password: string, fullName?: string): Promise<AuthResponse> => {
    const res = await apiFetch<AuthResponse>('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    })
    authStorage.setToken(res.access_token)
    if (res.user) authStorage.setUser(res.user)
    return res
  },

  me: async (): Promise<User> => {
    const user = await apiFetch<User>('/api/auth/me')
    authStorage.setUser(user)
    return user
  },

  logout: () => {
    authStorage.clear()
  },

  /** List all SKUs with status */
  listSkus: () => apiFetch<SkuSummary[]>('/api/skus'),

  /** Get a single SKU's full detail */
  getSku: (sku: string) => apiFetch<SkuDetail>(`/api/skus/${encodeURIComponent(sku)}`),

  /** Demand forecast for a SKU */
  getForecast: (sku: string, horizon = 14) =>
    apiFetch<ForecastResponse>(`/api/skus/${encodeURIComponent(sku)}/forecast?horizon=${horizon}`),

  /** Compute reorder recommendation */
  getRecommendation: (sku: string) =>
    apiFetch<RecommendationResponse>(`/api/skus/${encodeURIComponent(sku)}/recommendation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }),
}

// ─── Mapping: backend shapes → frontend Product ─────────────────────────────

export interface Product {
  name: string
  sku: string
  category: string
  supplier: string
  stock: number
  demand: number
  lead: number
  safety: number
  price: number
  incoming: number
}

/** Derive a rough category from the SKU prefix */
function categoryFromSku(sku: string): string {
  const prefix = sku.split('-')[0].toUpperCase()
  const map: Record<string, string> = {
    GRC: 'Grocery',
    KIT: 'Kitchen',
    PKG: 'Packaging',
    HOM: 'Home',
  }
  return map[prefix] ?? 'General'
}

/** Convert backend SkuSummary + optional detail into the Product shape */
export function toProduct(summary: SkuSummary, detail?: SkuDetail): Product {
  const params = detail?.params
  return {
    name: summary.name ?? summary.sku,
    sku: summary.sku,
    category: categoryFromSku(summary.sku),
    supplier: 'Unknown Supplier',
    stock: Math.round(summary.on_hand),
    demand: 5, // overridden by forecast when available
    lead: params?.lead_time_days ?? 7,
    safety: 20, // overridden by forecast when available
    price: params?.unit_cost ?? 10,
    incoming: Math.round(summary.on_order),
  }
}

/** Richer conversion that uses forecast avg_daily_demand + sigma for safety stock */
export function toProductFromForecast(
  summary: SkuSummary,
  detail: SkuDetail,
  forecast: ForecastResponse,
): Product {
  const params = detail.params
  const demand = forecast.avg_daily_demand
  // Safety stock ≈ z * sigma * sqrt(lead_time)  (z=1.65 for ~95% SL)
  const safety = Math.ceil(1.65 * forecast.sigma_daily * Math.sqrt(params.lead_time_days))
  return {
    name: summary.name ?? summary.sku,
    sku: summary.sku,
    category: categoryFromSku(summary.sku),
    supplier: 'Unknown Supplier',
    stock: Math.round(summary.on_hand),
    demand,
    lead: params.lead_time_days,
    safety,
    price: params.unit_cost,
    incoming: Math.round(summary.on_order),
  }
}
