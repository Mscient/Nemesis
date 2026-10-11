# StockSense — Adaptive Inventory Replenishment Engine
## Project Specification for AI Coding Agents — v2 (FastAPI backend)

> **How to use this file.** This is the single source of truth for building StockSense. Read it fully before writing code. Sections 1–5 explain *what* and *why*; Sections 6–13 are the *build contract*; Section 14 splits the work into agent roles; Section 16 lists the rules you must not break.

---

## 1. Project Summary

**StockSense** is an explainable decision-support engine that tells a business **when to reorder a product and how much to order**.

It addresses five concrete problems:

| Problem | Consequence |
|---|---|
| Ordering too late | Stockouts, lost sales |
| Ordering too early | Storage cost, cash tied up |
| Unexpected demand increases | Shortages |
| Supplier delays | Disrupted supply |
| Unusual sales data (promotions, errors) | Inaccurate forecasts |

**Goal:** predict demand, calculate reorder points, minimise cost, and show *why* every recommendation was made.

**Positioning:** StockSense is **not** a replacement for an ERP such as SAP S/4HANA or Oracle NetSuite. Those systems already provide sophisticated inventory and supply planning. StockSense is a **focused, transparent decision-support layer**: it recommends replenishment, shows the calculations behind each recommendation, measures forecast accuracy, and shows how decisions change under demand or supplier disruption.

---

## 2. Core Concepts (domain glossary)

| Term | Meaning |
|---|---|
| **Demand forecasting** | Predicting how much of a product customers will need |
| **Safety stock (SS)** | Extra inventory held to protect against uncertain demand or late deliveries |
| **Lead time (L)** | Days between placing and receiving an order |
| **Reorder point (ROP)** | Inventory-position level at which a replenishment order should be placed |
| **Inventory position** | `on_hand + on_order − backordered` (use this, not on-hand alone, to compare against ROP) |
| **Supply planning** | Deciding how much additional supply is needed and when it should arrive |
| **MRP** | Material Requirements Planning — computes material requirements and replenishment timing (an ERP concept; StockSense borrows the idea, not the full system) |
| **Service level** | Target probability of *not* stocking out during a replenishment cycle (user-selected) |
| **z-factor** | Standard-normal quantile for the chosen service level |
| **Holdout data** | The most recent slice of history withheld from model fitting, used to measure forecast accuracy |

### How existing ERPs frame the problem (context only)

```
SAP S/4HANA : Inventory data → Forecasting → Reorder point → MRP → Replenishment proposal → Purchase order
NetSuite    : Sales history → Demand forecasting → Planning data → Supply planning → Recommendations → Orders
```

Both support much more than shown. These are the planning concepts that inspired StockSense, not a feature comparison of either product.

---

## 3. What Makes StockSense Different

| Feature | Purpose |
|---|---|
| **Smart replenishment** | Calculate reorder points and cost-aware order quantities |
| **Demand-anomaly detection** | Flag unusual sales and classify as *promotion*, *data error*, *stockout-censored*, or *unknown* |
| **Forecast evaluation** | Compare the proposed model against a simple baseline on holdout data |
| **Scenario simulation** | Simulate demand surges and supplier delays |
| **Cost & risk analysis** | Estimate holding, ordering and stockout cost, and stockout risk |

Every recommendation must display: the **user-selected service level, the z-factor, the formulas, all assumptions, and any AI-proposed adjustments** (clearly labelled as AI-proposed and user-approvable).

---

## 4. Intended Users

| User | Needs |
|---|---|
| **Inventory / replenishment planner** | Daily reorder recommendations they can trust and override |
| **Small-business owner / shop manager** | Plain-language "order X units now" guidance without ERP complexity |
| **Procurement / purchasing lead** | Lead-time risk view; what-if on supplier delays |
| **Operations / finance manager** | Cost trade-offs and stockout-risk numbers |
| **Hackathon judges / evaluators** | A clear end-to-end demo with visible math and measured accuracy |

---

## 5. System Architecture

### 5.1 Decision pipeline

```text
          Historical Sales Data
                   |
                   v
           Demand Forecasting
                   |
                   v
          Anomaly Detection          (rules first, optional AI suggestion second)
                   |
                   v
         Safety Stock Calculator
                   |
                   v
         Reorder Point Calculator
                   |
                   v
         Order Quantity Calculator
                   |
                   v
           Cost & Risk Analysis
                   |
                   v
          Scenario Simulation
                   |
                   v
          Inventory Dashboard
```

> Note: anomaly detection can run on raw history *before* the final forecast fit (to clean inputs) and again on forecast residuals. Implementation order in code: `clean → forecast → evaluate → size → simulate`. The diagram above is the conceptual flow.

### 5.2 Components

```text
┌──────────────────────────── React Frontend ────────────────────────────┐
│ Dashboard · SKU detail · Anomaly review · Scenario panel · Explain view │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST / JSON (snake_case)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend (Python only)                     │
│  Routers · Pydantic validation · orchestration · OpenAPI docs           │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ Analytics Core (stocksense_core) — deterministic, unit-tested       │ │
│ │ forecasting + evaluation · anomaly detection · safety stock · ROP · │ │
│ │ EOQ · cost & risk · Monte Carlo scenarios                           │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└──────────┬─────────────────────────────────────┬───────────────────────┘
           │                                     │ (optional, in-process)
 ┌─────────▼────────────┐              ┌─────────▼──────────────┐     ┌───────────────┐
 │ Database             │              │ AI module              │────▶│ LLM provider  │
 │ PostgreSQL via       │              │ (stocksense_ai)        │     │ API (external)│
 │ SQLAlchemy           │              │ suggests, explains —   │     └───────────────┘
 └──────────────────────┘              │ never calculates       │
                                       └────────────────────────┘
```

There is **no separate forecasting service**: forecasting and anomaly detection run in-process inside the FastAPI backend.

### 5.3 Technology stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript; Recharts | The only non-Python component |
| Backend | **FastAPI** + Pydantic v2 + pydantic-settings | Auto OpenAPI at `/docs`; plain `def` handlers for CPU-bound work, `async def` for AI calls |
| Analytics core | Python package `stocksense_core` (pandas, numpy, scipy, statsmodels) | No FastAPI/DB/LLM imports |
| Database | PostgreSQL via SQLAlchemy 2.x (SQLite allowed for local dev) | Pick one for the demo; do not support several |
| AI | Python package `stocksense_ai`; provider-agnostic LLM client with a mock provider | Optional; system must work with `AI_ENABLED=false` |
| Tests | pytest (core, ai, backend with `TestClient`), Vitest (frontend) | Core formula tests are mandatory |
| Packaging | Docker + docker-compose | `docker compose up` runs the whole app |

**Hard rule:** inventory calculations are done by **deterministic, unit-tested code in `stocksense_core`**, never by an AI model. Dependency direction: `frontend → backend → (core, ai)`; `core` and `ai` never import each other or the backend.

---

## 6. Decision Engine — Formulas (authoritative)

Let `μd` = average daily demand, `σd` = standard deviation of daily demand, `L` = lead time (days), `σL` = std-dev of lead time (days), `z` = z-factor for service level.

### 6.1 Safety stock

Constant lead time:

```
SS = z × σd × √L
```

Variable lead time:

```
SS = z × √( L × σd²  +  μd² × σL² )
```

Round **up** to a whole unit. Use the variable form when `σL > 0`.

### 6.2 Reorder point

```
ROP = (μd × L) + SS
```

Trigger an order when `inventory_position ≤ ROP`.

### 6.3 Economic order quantity

```
EOQ = √( 2 × D × S / H )
```

`D` = annual demand, `S` = fixed cost per order, `H` = holding cost per unit per year.
Then apply constraints in this order: **round up → enforce MOQ → round up to pack size → cap at max storage (if set)**.

### 6.4 Service-level → z lookup

| Service level | z |
|---|---|
| 90% | 1.282 |
| 95% | 1.645 |
| 97.5% | 1.960 |
| 99% | 2.326 |

For other values, compute the inverse normal CDF; do not interpolate this table.

### 6.5 Worked examples (use as unit-test fixtures)

**Example A — ROP from a given safety stock** (from the original discussion)

- `μd = 10/day`, `L = 5`, `SS = 20` → `ROP = (10×5) + 20 = 70` ✅

**Example B — computed safety stock**

- `μd = 10`, `σd = 4`, `L = 5`, service 95% (`z = 1.645`), `σL = 0`
- `SS = 1.645 × 4 × √5 = 14.71 → 15`
- `ROP = 50 + 15 = 65`

**Example C — EOQ**

- `D = 3,650/yr`, `S = 50`, `H = 2` → `EOQ = √(2×3650×50/2) = √182,500 = 427.2 → 428`

### 6.6 Edge cases the engine must handle

- `σd = 0` → `SS = 0`, flag "no demand variability observed"
- `L = 0` or negative → reject with validation error
- Fewer than 28 days of history → return a result with a **low-confidence warning**
- `H = 0` or `S = 0` → reject EOQ with a clear message
- Negative demand values → route to anomaly module, never into math silently

---

## 7. Forecasting & Evaluation

### 7.1 Models

| Role | Model | Purpose |
|---|---|---|
| **Baseline** | Naive (last value), seasonal-naive (same weekday last week), or 14-day moving average | The "must beat" reference |
| **Proposed** | Exponential smoothing / Holt-Winters with weekly seasonality (or regression with weekday + trend + promo flag) | The model StockSense uses |

### 7.2 Evaluation protocol

1. Sort history by date. Hold out the **last 20%** (minimum 14 days).
2. Fit both models on the training slice only.
3. Forecast the holdout window; compute metrics:

| Metric | Formula |
|---|---|
| MAE | `mean(|actual − forecast|)` |
| RMSE | `√mean((actual − forecast)²)` |
| WAPE | `Σ|actual − forecast| / Σ actual` |
| Bias | `mean(forecast − actual)` |

4. Report **both models side by side**. If the proposed model does *not* beat the baseline, **say so and use the baseline** — do not hide it.
5. Never claim improvement beyond what holdout metrics show.

---

## 8. Anomaly Detection

### 8.1 Detection (deterministic)

- Compute a rolling median (e.g., 14-day) and MAD, or IQR on residuals.
- Flag points with robust z-score `> 3.5` (configurable).
- Also flag: negative values, duplicate dates, impossible magnitudes, zero sales while inventory was zero.

### 8.2 Classification

| Class | Rule of thumb |
|---|---|
| `promotion` | Overlaps a known promotion window |
| `data_error` | Negative, duplicated, or physically impossible value |
| `stockout_censored` | Zero/low sales while on-hand was zero (true demand is unknown) |
| `unknown` | Flagged but matches none of the above |

### 8.3 Treatment

| Class | Default treatment |
|---|---|
| `promotion` | Keep but add promo flag (or exclude from baseline demand) |
| `data_error` | Exclude / correct |
| `stockout_censored` | Exclude or impute; do not treat as low demand |
| `unknown` | Keep, surface to user for review |

The AI assistant may **propose** a class with a confidence score and short rationale. The **user** confirms or overrides. Store `source: "rule" | "ai" | "user"` for every label.

---

## 9. Cost, Risk & Scenario Simulation

### 9.1 Cost model

```
Holding cost   = H_daily × average_inventory × days
Ordering cost  = S × number_of_orders
Stockout cost  = P × unmet_units          (P = penalty per unit; user-supplied)
Total cost     = Holding + Ordering + Stockout
```

### 9.2 Simulation engine

- Daily Monte Carlo simulation under the (ROP, Q) policy.
- Demand drawn from the forecast mean and residual spread; lead time drawn from the supplier distribution.
- **Seeded RNG** so results are reproducible (default 1,000 runs).
- Outputs: stockout probability, expected unmet units, average inventory, total cost with a spread (e.g., P10–P90).

### 9.3 Scenarios

| Scenario | Parameters |
|---|---|
| Demand surge | `+X%` for `N` days starting day `t` |
| Supplier delay | `+Y` days to lead time (or increased `σL`) |
| Combined | Both at once |

For each scenario show **before vs. after**: ROP, safety stock, stockout risk, total cost, and a recommended action. Present results as **estimates under stated assumptions**, never guarantees.

---

## 10. Data Contracts

> Agree on these **first**; everything else depends on them.

### 10.1 Input CSV — `sales.csv`

| Column | Type | Required |
|---|---|---|
| `date` | ISO date | ✅ |
| `sku` | string | ✅ |
| `units_sold` | number | ✅ |
| `on_hand` | number | optional (enables stockout-censoring) |
| `promo_flag` | 0/1 | optional |

### 10.2 SKU parameters (`snake_case` JSON everywhere)

```json
{
  "sku": "WATER-500",
  "name": "Water 500 ml",
  "lead_time_days": 5,
  "lead_time_std_days": 1.0,
  "unit_cost": 8.0,
  "order_cost": 50,
  "holding_cost_per_unit_per_year": 2.0,
  "stockout_penalty_per_unit": 6.0,
  "moq": 24,
  "pack_size": 12,
  "max_storage": null,
  "service_level": 0.95,
  "on_hand": 120,
  "on_order": 0
}
```

### 10.3 Recommendation response (the key payload)

```json
{
  "sku": "WATER-500",
  "as_of": "2026-10-11",
  "action": "ORDER_NOW",
  "order_quantity": 428,
  "inventory_position": 60,
  "reorder_point": 65,
  "safety_stock": 15,
  "forecast": { "model": "holt_winters", "avg_daily_demand": 10.0, "sigma_daily": 4.0 },
  "inputs": {
    "service_level": 0.95,
    "z_factor": 1.645,
    "lead_time_days": 5,
    "lead_time_std_days": 0
  },
  "formulas": {
    "safety_stock": "z × σd × √L = 1.645 × 4 × √5 = 14.71 → 15",
    "reorder_point": "(μd × L) + SS = (10 × 5) + 15 = 65",
    "order_quantity": "EOQ = √(2DS/H) = 427.2 → 428"
  },
  "assumptions": ["Demand ~ Normal", "Lead time fixed at 5 days"],
  "ai_adjustments": [],
  "warnings": [],
  "confidence": "medium"
}
```

### 10.4 Core database tables

`skus`, `sales_records(sku, date, units, on_hand, promo_flag)`, `anomalies(id, sku, date, value, class, source, status, rationale)`, `forecast_runs(id, sku, model, params, metrics_json, created_at)`, `scenarios(id, sku, params_json, results_json)`, `adjustments(id, sku, start_date, end_date, multiplier, source, status, rationale)`, `purchase_orders_open(sku, qty, eta)`, `ai_audit_log(id, task, model, prompt_version, latency_ms, validation_outcome, created_at)`.

---

## 11. API Contract (FastAPI)

Interactive docs at `/docs`; machine-readable schema at `/openapi.json` (the frontend generates its TypeScript types from it). Path parameters use FastAPI style `{sku}`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/ai/status` | AI enabled? provider / model |
| `POST` | `/api/datasets` | Upload `sales.csv` (structural validation + anomaly detection) |
| `GET` | `/api/skus` | List SKUs with status (OK / REORDER / AT_RISK) |
| `GET` | `/api/skus/{sku}` | SKU detail incl. parameters |
| `PUT` | `/api/skus/{sku}/params` | Update SKU parameters |
| `GET` | `/api/skus/{sku}/history` | Cleaned and raw sales history |
| `GET` | `/api/skus/{sku}/forecast?horizon=14` | Forecast + holdout evaluation summary |
| `GET` | `/api/skus/{sku}/evaluation` | Baseline vs proposed holdout comparison |
| `GET` | `/api/skus/{sku}/anomalies` | List flagged anomalies |
| `POST` | `/api/skus/{sku}/anomalies/suggest` | AI label suggestions (`source="ai"`) |
| `PATCH` | `/api/anomalies/{id}` | User confirms / reclassifies (`source="user"`) |
| `POST` | `/api/skus/{sku}/recommendation` | Compute ROP, SS, order quantity (returns 10.3) |
| `POST` | `/api/skus/{sku}/scenarios` | Run a what-if simulation |
| `POST` | `/api/skus/{sku}/explain` | AI plain-language explanation (template fallback if AI off) |
| `POST` | `/api/skus/{sku}/adjustments/propose` | AI proposes forecast adjustments |
| `GET` | `/api/skus/{sku}/adjustments` | List proposed / accepted / rejected adjustments |
| `PATCH` | `/api/adjustments/{id}` | User accepts or rejects an adjustment |

All errors use one envelope with a proper HTTP status:
`{ "error": { "code": "VALIDATION_ERROR", "message": "...", "field": "lead_time_days" } }`

### 11.1 FastAPI conventions

- Every request/response is a Pydantic v2 model; no untyped dicts at the API boundary.
- Settings via `pydantic-settings` (`DATABASE_URL`, `AI_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `MOCK_MODE`).
- `MOCK_MODE=true` returns the example payloads from `backend/mocks/` so the frontend can be built before the engine exists.
- Only approved adjustments (`status="accepted"`) are ever passed into the forecast.

---

## 12. AI Integration

| AI task | Allowed? | Guardrails |
|---|---|---|
| Suggest anomaly class (promo / error / unknown) | ✅ | Return JSON `{class, confidence, rationale}`; user approval required |
| Explain a recommendation in plain language | ✅ | Receives the **computed numbers**; may not change them |
| Propose a forecast adjustment (e.g., upcoming event) | ✅ | Shown as *AI-proposed*, off by default, user must accept |
| Compute ROP / SS / EOQ / costs | ❌ | Deterministic code only |
| Override user-selected service level | ❌ | Never |

Implementation notes:
- The system **must work fully with AI disabled** (`AI_ENABLED=false`).
- Validate AI JSON against a schema; on failure, fall back to `unknown`.
- Do not send data outside what is needed; never send secrets.
- Log every AI suggestion with `source: "ai"`.

---

## 13. Repository Layout

```text
stocksense/
├─ README.md                      # B
├─ docker-compose.yml, .env.example
├─ docs/                          # API.md (B) · AI.md (C) · CORE.md (D) · FRONTEND.md (A)
├─ frontend/                      # A — React + Vite + TS
├─ backend/                       # B — FastAPI
│  ├─ app/{main.py, config.py, deps.py}
│  ├─ app/routers/                # one router per resource
│  ├─ app/schemas/                # Pydantic API models
│  ├─ app/services/               # orchestration; ONLY place core and ai meet
│  ├─ app/db/                     # SQLAlchemy models, session, repositories
│  ├─ mocks/                      # contract example JSON (MOCK_MODE)
│  └─ tests/
├─ ai/                            # C — stocksense_ai (+ eval/, tests/)
├─ core/                          # D — stocksense_core (+ tests/)
│  └─ stocksense_core/{types, series, engine/, forecast/, anomaly/, cost/, simulation/}
├─ data/                          # D — synthetic generator + sample CSVs + ground truth
└─ demo/                          # C — demo script, pitch deck
```

---

## 14. Team Split & Ownership

Four people, four non-overlapping parts. The full per-person deliverable list, interface signatures, timeline and integration checklist are in **`TEAM_WORK_BREAKDOWN.md`**.

| Member | Part | Owns |
|---|---|---|
| **A** | Frontend | `frontend/` |
| **B** | Backend / API & data platform | `backend/`, `docker-compose.yml`, root `README.md` |
| **C** | LLM / AI layer (+ demo & pitch) | `ai/`, `demo/` |
| **D** | Analytics core (+ synthetic data) | `core/`, `data/` |

If you are an AI coding agent assigned to one member's part: edit **only** that part's directories, implement against the interface contracts in `TEAM_WORK_BREAKDOWN.md` §4, and never re-implement logic that belongs to another part.

### Recommended order of work (8-hour prototype)

```text
interface contracts + stubs (hour 1)  →  core math + data  →  backend integration
      →  forecasting / anomaly / AI modules  →  frontend on live API  →  scenario testing & demo
```

---

## 15. Acceptance Criteria

1. Upload CSV → see SKU list with status within one flow.
2. Each SKU shows ROP, SS, order quantity **with formulas and assumptions visible**.
3. Forecast page shows baseline vs proposed holdout metrics.
4. Anomalies are flagged, labelled, and user-reviewable.
5. Scenario panel shows before/after for a demand surge and a supplier delay.
6. All Section 6.5 examples pass as automated tests.
7. App runs with AI disabled.
8. One scripted demo works end to end on realistic (or realistically synthetic) data.

---

## 16. Rules You Must Not Break

1. **No AI-computed inventory math.** Deterministic code only.
2. **Show your work.** Every recommendation exposes service level, z, formulas, assumptions, and AI adjustments.
3. **Test the formulas** before building UI on top of them.
4. **Measure forecasts on held-out data.** Compare to a baseline; report honestly if the baseline wins.
5. **Do not claim guaranteed cost savings or guaranteed forecast improvement.** Simulation outputs are estimates under stated assumptions.
6. **Do not recreate an ERP.** Stay focused on the five differentiating features.
7. **Agree on API contracts early** and do not change them silently; update this file if they change.
8. **Label synthetic data** as synthetic everywhere it appears in the demo.
9. **User choices win.** Service level and approvals set by the user are never overridden by the system or AI.
10. **Keep one complete end-to-end demo working** at all times; prefer depth on the core path over breadth.

---

## 17. Out of Scope

Full ERP functionality, multi-echelon optimisation, automatic purchase-order submission to suppliers, user authentication/roles beyond a demo login, real-time integrations with SAP/NetSuite.

---

## 18. Final Verdict

StockSense is an **adaptive, explainable replenishment decision-support system** — not merely an inventory dashboard. Its strength is the combination of demand forecasting, uncertainty-aware safety stock, cost-based ordering, anomaly handling, and measurable disruption simulation. Success depends on implementing the core mathematics correctly, agreeing on API contracts early, using realistic data, and delivering one complete end-to-end demo.
