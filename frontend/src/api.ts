/**
 * api.ts — thin fetch wrapper for the StockSense FastAPI backend.
 * All calls go through Vite's /api proxy → http://localhost:8000
 */

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
  const res = await fetch(path, options)
  if (!res.ok) throw new Error(`${options?.method ?? 'GET'} ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

// ─── API functions ─────────────────────────────────────────────────────────

export const api = {
  health: () => apiFetch<HealthResponse>('/api/health'),

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
    demand: 5,                            // overridden by forecast when available
    lead: params?.lead_time_days ?? 7,
    safety: 20,                           // overridden by forecast when available
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
