# StockSense — Team Work Breakdown (4 People, Zero Overlap)

> Companion to `STOCKSENSE_AGENT_SPEC.md` (v2, FastAPI). The spec says **what** the system does; this file says **who builds which piece**. If a task is not listed under your name, it is not yours.

---

## 1. Architecture Decision: Backend = FastAPI (completely)

| Before | Now |
|---|---|
| Node.js + Express API **plus** a separate Python forecasting service | **One FastAPI (Python) backend** that hosts everything server-side |
| Decision engine in TypeScript | Decision engine in Python (`core/`) |
| Two languages, two test stacks, cross-service contract | One backend language, one test stack (pytest), in-process calls |

**Why this is better for this project:** forecasting, anomaly detection and Monte Carlo simulation are all Python-native (pandas, numpy, statsmodels). Keeping them in-process removes a network hop, duplicated validation, and a whole class of integration bugs.

**Conventions that follow from it**
- Pydantic v2 for all request/response models; auto-generated OpenAPI at `/docs` and `/openapi.json`.
- **JSON field names are `snake_case` everywhere** (Python-native; no camelCase mapping layer).
- Route handlers are plain `def` (sync) so FastAPI runs the CPU-bound pandas/numpy work in its threadpool; AI calls are `async def`.
- Only the **frontend** is JavaScript/TypeScript (React). Everything else is Python.

---

## 2. The Four Parts

| Member | Part | Owns directory | Mission in one line |
|---|---|---|---|
| **A** | Frontend | `frontend/` | Everything the user sees and clicks; zero inventory math |
| **B** | Backend / API & Data Platform | `backend/`, `docker-compose.yml`, root `README.md` | FastAPI app, database, validation, orchestration, endpoints |
| **C** | LLM / AI Layer (+ demo & pitch) | `ai/`, `demo/` | Everything that talks to an LLM, safely; plus the demo script and pitch deck |
| **D** | Analytics Core (forecast, anomaly, decision math, simulation) + synthetic data | `core/`, `data/` | Every number the system produces |

(Member C also owns the demo script and pitch deck to balance load — the LLM layer is the lightest piece.)

---

## 3. Ownership Rules (what prevents overlap)

1. **Directory ownership is absolute.** You edit files only inside directories you own. Need a change elsewhere → ask the owner (message/issue); they make it.
2. **Dependency direction is one-way:**
   ```
   frontend ──HTTP──▶ backend ──imports──▶ core
                          └─────imports──▶ ai
   ```
   - `core/` imports **nothing** from `backend/`, `ai/`, FastAPI, or any database library.
   - `ai/` imports **nothing** from `backend/` or `core/`.
   - `backend/` is the only place where `core` and `ai` meet. **B writes all glue/mapping** between them.
   - `frontend/` never imports Python and never computes inventory math.
3. **The provider of an interface owns its signature.** Consumers don't edit it; they request changes. Changes are announced in the team chat and applied by the owner.
4. **One owner per file/doc:** see the matrix below.

### Ownership matrix

| Path / artifact | Owner |
|---|---|
| `frontend/**` (incl. its Dockerfile, tests, `frontend/README.md`) | **A** |
| `backend/app/**` (routers, schemas, services, db, config) | **B** |
| `backend/tests/**` (API + integration tests) | **B** |
| `backend/mocks/**` (contract example JSON) | **B** |
| `docker-compose.yml`, `backend/Dockerfile`, `.env.example`, root `README.md` | **B** |
| `docs/API.md` | **B** |
| `ai/stocksense_ai/**`, `ai/tests/**`, `ai/eval/**`, `docs/AI.md` | **C** |
| `demo/**` (demo script, pitch deck, demo checklist) | **C** |
| `core/stocksense_core/**`, `core/tests/**`, `docs/CORE.md` | **D** |
| `data/**` (synthetic generator, sample CSVs, ground-truth files) | **D** |
| `.gitignore` | **B** |

---

## 4. Interface Contracts (the seams between parts)

### 4.1 Frontend ⇄ Backend — REST (owner of contract: **B**)

All endpoints are defined and implemented by **B**; **A** consumes them. TypeScript types for A are generated from B's `/openapi.json`.

| Method | Endpoint | Handler logic calls | Consumed by screen (A) |
|---|---|---|---|
| GET | `/api/health` | — | App shell |
| GET | `/api/ai/status` | `ai.status()` | AI status banner |
| POST | `/api/datasets` | CSV parser (B) + `core.detect_anomalies` | Upload & Setup |
| GET | `/api/skus` | status derived from `core.compute_recommendation` | Dashboard |
| GET | `/api/skus/{sku}` | DB read | SKU Detail |
| PUT | `/api/skus/{sku}/params` | DB write | Setup / SKU Detail |
| GET | `/api/skus/{sku}/history` | DB read | SKU Detail chart |
| GET | `/api/skus/{sku}/forecast?horizon=14` | `core.run_forecast` | SKU Detail chart |
| GET | `/api/skus/{sku}/evaluation` | `core.run_forecast` (evaluation part) | Forecast Evaluation |
| GET | `/api/skus/{sku}/anomalies` | DB read | Anomaly Review |
| POST | `/api/skus/{sku}/anomalies/suggest` | `ai.suggest_anomaly_labels` | Anomaly Review |
| PATCH | `/api/anomalies/{id}` | DB write (`source="user"`) | Anomaly Review |
| POST | `/api/skus/{sku}/recommendation` | `core.compute_recommendation` | SKU Detail + Show-the-Math |
| POST | `/api/skus/{sku}/scenarios` | `core.run_scenario` | Scenario Panel |
| POST | `/api/skus/{sku}/explain` | `ai.explain_recommendation` | Explain panel |
| POST | `/api/skus/{sku}/adjustments/propose` | `ai.propose_forecast_adjustments` | Adjustments panel |
| GET | `/api/skus/{sku}/adjustments` | DB read | Adjustments panel |
| PATCH | `/api/adjustments/{id}` | DB write (accept / reject) | Adjustments panel |

Error envelope (all endpoints): `{ "error": { "code": "VALIDATION_ERROR", "message": "...", "field": "lead_time_days" } }`.

### 4.2 Backend ⇄ Core — Python functions (owner of contract: **D**, consumer: **B**)

```python
# stocksense_core/types.py  (frozen dataclasses — D owns)
SalesRecord(date, units_sold, on_hand | None, promo_flag | None)
SkuParams(sku, lead_time_days, lead_time_std_days, unit_cost, order_cost,
          holding_cost_per_unit_per_year, stockout_penalty_per_unit,
          moq, pack_size, max_storage | None, service_level, on_hand, on_order)
AnomalyFlag(date, value, expected_value, robust_z, flags[], cls, default_treatment, rationale)
Adjustment(start_date, end_date, multiplier, source)        # only user-approved ones are passed in

# stocksense_core/__init__.py  (public API)
service_level_to_z(p: float) -> float
detect_anomalies(records, promo_windows=(), threshold=3.5) -> list[AnomalyFlag]
clean_series(records, flags, user_decisions=None) -> CleanedSeries
run_forecast(cleaned, horizon_days=14, holdout_fraction=0.2, adjustments=()) -> ForecastResult
compute_recommendation(params, forecast) -> RecommendationResult
simulate(params, forecast, recommendation, n_runs=1000, seed=42, horizon_days=90) -> SimulationResult
run_scenario(params, forecast, scenario: ScenarioSpec) -> ScenarioComparison
```

`ForecastResult` includes predictions, `mu_d`, `sigma_d`, `model_used`, `evaluation` (baseline vs proposed metrics, chosen model, holdout window), `confidence`, `warnings`.
`RecommendationResult` includes `z_factor`, `safety_stock`, `reorder_point`, `inventory_position`, `action`, `order_quantity`, `formulas` (strings with substituted numbers), `assumptions`, `warnings`, `confidence`.

### 4.3 Backend ⇄ AI — Python functions (owner of contract: **C**, consumer: **B**)

```python
# stocksense_ai/__init__.py  (public API; all LLM failures are handled INSIDE — they never raise)
is_enabled() -> bool
status() -> AIStatus                                           # enabled, provider, model
async suggest_anomaly_labels(items: list[AnomalyContext]) -> AnomalySuggestionBatch
async explain_recommendation(req: ExplainRequest) -> ExplainResult            # has used_fallback: bool
async propose_forecast_adjustments(req: AdjustmentRequest) -> AdjustmentProposalBatch
```

C owns all of these schemas (`AnomalyContext`, `AnomalySuggestion`, `ExplainRequest`, `ExplainResult`, `AdjustmentRequest`, `AdjustmentProposal`, `AIAuditRecord`). **B** converts core results ⇄ these schemas in `backend/app/services/`.

### 4.4 Freeze point

By **end of hour 1** every owner has committed their interface as **stubs that return valid example data**: B (OpenAPI + mock mode), D (core stubs), C (AI stubs/mock provider), A (app shell). After the freeze, signature changes go through the owner and are announced.

---

## 5. MEMBER A — Frontend (React)

**Directory:** `frontend/` · **Stack:** React 18 + Vite + TypeScript, React Router, TanStack Query, Recharts, `openapi-typescript` for API types, Vitest + React Testing Library.

### A implements

| # | Deliverable | Details |
|---|---|---|
| A1 | App shell & routing | Layout, navigation, route map, global error boundary, env-based `API_BASE_URL` |
| A2 | Typed API client | Types generated from B's `/openapi.json`; fetch wrapper; TanStack Query hooks per endpoint; maps the error envelope to UI messages |
| A3 | Upload & Setup screen | CSV upload (progress, success/failure summary), SKU parameter form with field-level validation messages returned by the API |
| A4 | Dashboard | SKU table with status chips (OK / REORDER / AT RISK), search, filter, sort; KPI strip (SKUs to reorder, at risk, avg service level); "synthetic data" badge when flagged |
| A5 | SKU Detail | History chart, forecast chart with holdout region shaded, inventory position vs reorder-point visual, recommendation card (action, order quantity) |
| A6 | "Show the math" panel | Service-level selector (user-controlled), displays z-factor, substituted formulas, assumptions, warnings, confidence, AI adjustments (labelled "AI-proposed") — **displays values from the API only** |
| A7 | Forecast Evaluation page | Baseline vs proposed metrics table (MAE, RMSE, WAPE, bias), chart of both on the holdout window, clear banner when the baseline wins |
| A8 | Anomaly Review screen | Table of flagged points with class, treatment, `source` badge (rule / ai / user); confirm / reclassify controls; "Suggest labels with AI" button; chart highlighting points |
| A9 | Scenario Panel | Inputs: demand surge (% , days, start day) and supplier delay (+days); runs scenario; before-vs-after cards (ROP, safety stock, stockout risk, total cost P10–P90, recommended action); comparison chart |
| A10 | AI UI | AI status banner (enabled / disabled); "Explain this recommendation" panel (shows `used_fallback` indicator); AI-proposed adjustments list with accept / reject controls |
| A11 | UX states | Loading skeletons, empty states, error states, low-confidence warnings, disabled-AI state; responsive layout; basic accessibility (labels, keyboard focus, contrast) |
| A12 | Frontend quality | Vitest tests for key components (recommendation card, math panel, anomaly table, scenario form); `frontend/Dockerfile`; `frontend/README.md`; `docs/FRONTEND.md` notes |

### A does NOT
- Compute ROP, safety stock, EOQ, z-factors, costs, forecasts or statistics (display only).
- Call any LLM directly or hold API keys.
- Define API shapes (request changes from B).
- Write demo script or slides (C).

### A depends on / delivers to
- **Depends on B:** OpenAPI + mock mode (hour 1), real endpoints (hours 3–4).
- **Delivers:** the running UI used for the demo.
- **Early start:** use B's `MOCK_MODE=true` backend; no waiting on D or C.

### A is done when
All screens A3–A10 work against the live API with the sample dataset; loading/error/empty states exist; tests pass.

---

## 6. MEMBER B — Backend / API & Data Platform (FastAPI)

**Directory:** `backend/`, `docker-compose.yml`, `.env.example`, root `README.md`, `docs/API.md` · **Stack:** FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.x, PostgreSQL (SQLite allowed for local dev), pytest + `TestClient`, Docker.

### B implements

| # | Deliverable | Details |
|---|---|---|
| B1 | Project skeleton | `app/main.py`, `config.py` (pydantic-settings), `deps.py`, CORS for the frontend dev origin, logging, `/api/health` |
| B2 | **API contract + mock mode (hour 1, highest priority)** | Pydantic request/response schemas for every endpoint in §4.1 (`snake_case`); `backend/mocks/*.json` example payloads; `MOCK_MODE=true` returns them so A can start immediately |
| B3 | Database layer | SQLAlchemy models: `skus`, `sales_records`, `anomalies`, `forecast_runs`, `scenarios`, `adjustments`, `purchase_orders_open`, `ai_audit_log`; session handling; table creation/migration; repositories |
| B4 | CSV ingestion | `POST /api/datasets`: structural validation only (required columns, types, parseable dates, size limit, row-level error report); persists records; creates SKU rows with default params. Statistical anomalies are D's job — B just calls `core.detect_anomalies` after load and stores the flags |
| B5 | SKU & params endpoints | List (with derived status), detail, update params with validation (e.g., `lead_time_days > 0`, `holding_cost > 0`), history endpoint |
| B6 | Forecast & evaluation endpoints | Load records → `core.clean_series` → `core.run_forecast`; persist `forecast_runs`; return forecast + evaluation |
| B7 | Anomaly endpoints | List; `PATCH /api/anomalies/{id}` stores user decision with `source="user"`; re-clean/re-forecast uses user decisions |
| B8 | Recommendation endpoint | Build `SkuParams`, include user-approved adjustments, call `core.compute_recommendation`, return the full explainable payload |
| B9 | Scenario endpoint | Map request → `ScenarioSpec`, call `core.run_scenario`, persist to `scenarios`, return before/after |
| B10 | AI-facing endpoints | `/api/ai/status`, `/api/skus/{sku}/anomalies/suggest`, `/explain`, `/adjustments/propose`, `GET /adjustments`, `PATCH /api/adjustments/{id}`; **all glue/mapping** between core results and `ai` schemas lives here; stores AI suggestions with `source="ai"` and writes `ai_audit_log` |
| B11 | Error handling | Global exception handlers producing the standard error envelope; correct HTTP status codes; mapping of core validation errors to field-level errors |
| B12 | Packaging | `backend/Dockerfile`, `docker-compose.yml` (db + backend + frontend using A's Dockerfile), `.env.example` (documents `AI_ENABLED`, `LLM_*`, DB URL), `.gitignore` |
| B13 | Backend tests | Contract tests for every endpoint (response matches schema), ingestion tests (good/bad CSV), integration tests (upload → recommend → scenario) using `TestClient` |
| B14 | Docs | Root `README.md` (setup & run in ≤ 5 commands), `docs/API.md` (endpoint reference + curl examples) |

### B does NOT
- Implement any statistics, forecasting, safety-stock, ROP, EOQ, simulation or anomaly logic (calls `core`).
- Write prompts or call an LLM provider (calls `ai`).
- Build UI.

### B depends on / delivers to
- **Delivers early:** B2 (contract + mocks) to A at hour 1.
- **Depends on D:** `core` stubs at hour 1, real implementations by hour 3. **Depends on C:** `ai` stubs at hour 1, real by hour 3.
- **Integrates:** swaps mocks for real calls as D/C deliver.

### B is done when
Every endpoint in §4.1 returns correct data against real `core` and `ai` (with AI both enabled and disabled); tests pass; `docker compose up` brings up the whole app.

---

## 7. MEMBER C — LLM / AI Layer (+ Demo & Pitch)

**Directory:** `ai/`, `demo/`, `docs/AI.md` · **Stack:** Python package `stocksense_ai`, Pydantic v2, httpx/provider SDK, pytest.

### C implements

| # | Deliverable | Details |
|---|---|---|
| C1 | **Schemas + stubs (hour 1)** | All AI Pydantic models (`AnomalyContext`, `AnomalySuggestion`, `ExplainRequest`, `ExplainResult`, `AdjustmentRequest`, `AdjustmentProposal`, `AIAuditRecord`, `AIStatus`) and stubbed public functions returning valid example data |
| C2 | Config & switch | Env vars `AI_ENABLED`, `LLM_PROVIDER` (`anthropic` / `openai` / `mock`), `LLM_MODEL`, `LLM_API_KEY`, timeout, max tokens; `is_enabled()` and `status()` |
| C3 | LLM client wrapper | Provider-agnostic `complete(prompt, schema)` with timeout, retry/backoff, token cap; at least one real provider plus a deterministic **mock provider** for tests and offline demo |
| C4 | Prompt templates | Versioned templates in `ai/stocksense_ai/prompts/` for anomaly classification, explanation, and forecast adjustment; free-text fields are passed as *data*, never as instructions (prompt-injection safe) |
| C5 | Anomaly label suggester | `suggest_anomaly_labels`: batches items, requests JSON `{class, confidence, rationale}`, validates against schema; classes limited to `promotion / data_error / stockout_censored / unknown`; any invalid output → `unknown`, confidence 0 |
| C6 | Recommendation explainer | `explain_recommendation`: plain-language explanation for a chosen audience (`shop_owner` / `planner`) from the **already-computed** numbers; **number-consistency check** — every number in the output must appear in the input; otherwise use the template fallback |
| C7 | Forecast-adjustment proposer | `propose_forecast_adjustments`: from user-supplied event notes + forecast summary, returns bounded proposals (`start_date`, `end_date`, `multiplier` clamped to 0.5–2.0, rationale, confidence); status is always `proposed` |
| C8 | Guardrails & fallbacks | Data minimisation (only needed fields leave the system, no secrets), JSON-schema validation, output sanitising, deterministic template fallbacks so the system is fully usable with AI off; `used_fallback` flag; never raises to the caller |
| C9 | Audit records | `AIAuditRecord` per call (task, model, prompt version, latency, validation outcome) returned to B for storage |
| C10 | AI tests & evaluation | pytest with the mock provider (valid output, malformed output, timeout, injection attempt in a free-text field, disabled mode); `ai/eval/` script scoring label accuracy against D's `data/sample/anomaly_ground_truth.csv` (read-only) |
| C11 | Demo script | `demo/DEMO_SCRIPT.md`: 5–7 minute scripted flow (upload → anomalies → recommendation → math → evaluation → scenario → AI explain), with expected numbers from the sample data and a fallback plan if the network or LLM fails |
| C12 | Pitch deck & checklist | `demo/` slides (problem, solution, users, AI integration, differentiation, architecture, results) and a pre-demo checklist; `docs/AI.md` |

### C does NOT
- Compute or alter any inventory number (ROP, SS, EOQ, costs, forecasts).
- Import from `backend/` or `core/`; touch the database; define API routes.
- Decide labels or adjustments — AI only *proposes*; the user accepts or rejects in the UI.

### C depends on / delivers to
- **Delivers:** stubs (hour 1) and real implementation (hour 3) to **B**.
- **Depends on D** only for the read-only ground-truth file used in evaluation (C10).

### C is done when
All three AI functions work with a real provider and the mock provider; the app works end to end with `AI_ENABLED=false`; guardrail tests pass; demo script and deck are rehearsed once end to end.

---

## 8. MEMBER D — Analytics Core (Forecast, Anomaly, Decision Math, Simulation) + Data

**Directory:** `core/`, `data/`, `docs/CORE.md` · **Stack:** pure Python package `stocksense_core` — pandas, numpy, scipy (inverse normal), statsmodels; pytest. **No FastAPI, no database, no LLM imports.**

### D implements

| # | Deliverable | Details |
|---|---|---|
| D1 | **Types + stubs (hour 1)** | Frozen dataclasses and public function stubs from §4.2 returning valid example data |
| D2 | Series preparation | Build a daily series from `SalesRecord`s: sort, detect duplicate dates, fill missing days, keep `on_hand` / `promo_flag` aligned |
| D3 | z-factor | `service_level_to_z(p)` via inverse normal CDF; matches the spec table (90% → 1.282, 95% → 1.645, 97.5% → 1.960, 99% → 2.326); rejects `p ≤ 0` or `p ≥ 1` |
| D4 | Safety stock | Fixed-lead-time and variable-lead-time forms; round up; `σd = 0` handling |
| D5 | Reorder point & inventory position | `ROP = μd × L + SS`; `inventory_position = on_hand + on_order − backorders`; trigger logic |
| D6 | Order quantity | EOQ, then constraints in order: round up → MOQ → pack size → max storage; rejects `H = 0`, `S = 0` with clear messages |
| D7 | `compute_recommendation` | Composes D3–D6; produces `formulas` strings with substituted numbers, `assumptions`, `warnings` (e.g., < 28 days history), `confidence` |
| D8 | Anomaly detection | Rolling median + MAD robust z-score (default 3.5), plus rule flags (negative, duplicate date, impossible magnitude, zero sales while `on_hand = 0`) |
| D9 | Anomaly classification & treatment | Rule-based classes `promotion / data_error / stockout_censored / unknown` (promotion via promo windows or `promo_flag`), default treatments, `clean_series` applying treatments and user overrides |
| D10 | Forecasting | Baselines (naive, seasonal-naive, 14-day moving average) and the proposed model (Holt-Winters with weekly seasonality, or regression with weekday + trend + promo); applies user-approved `Adjustment`s; outputs `mu_d`, `sigma_d` |
| D11 | Forecast evaluation | Last-20% holdout (min 14 days); MAE, RMSE, WAPE, bias for baseline and proposed; **chosen-model rule: if the proposed model does not beat the best baseline, use the baseline and say so** |
| D12 | Cost & simulation | Cost model (holding + ordering + stockout); seeded vectorised Monte Carlo under the (ROP, Q) policy; outputs stockout probability, expected unmet units, average inventory, total cost P10 / P50 / P90 |
| D13 | Scenarios | `run_scenario` for demand surge, supplier delay, and combined; returns before-vs-after comparison and a recommended-action string |
| D14 | Synthetic data | `data/generate_synthetic.py` (seeded): multiple SKUs with weekly seasonality, trend, injected promotions, data errors and stockout-suppressed periods; `data/sample/sales.csv`, `sku_params.csv`, and `anomaly_ground_truth.csv`; clearly labelled **synthetic** |
| D15 | Core tests & docs | pytest: spec fixtures (Example A → ROP 70; Example B → SS 15, ROP 65; Example C → EOQ 428), edge cases from spec §6.6, evaluation determinism (same seed → same output); `docs/CORE.md` explaining each formula and assumption |

### D does NOT
- Define HTTP routes, database models or Pydantic API schemas.
- Call or import any LLM code.
- Build charts or UI.

### D depends on / delivers to
- **Delivers:** stubs (hour 1) and real implementations (hour 3) to **B**; sample data to everyone by hour 2.
- **Depends on:** nobody. D is the root of the dependency tree — prioritise D1, D3–D7 and D14 first.

### D is done when
All spec worked examples pass as tests; forecast evaluation reports baseline vs proposed for every sample SKU; scenarios produce sensible before/after changes (a +30% surge raises ROP and stockout risk; a longer lead time raises ROP).

---

## 9. Timeline & Sync Points (8-hour prototype)

| Hour | A — Frontend | B — Backend | C — AI + Demo | D — Core + Data |
|---|---|---|---|---|
| 0–1 | App shell, routing (A1) | **Contract + mocks (B2)**, skeleton (B1) | **Schemas + stubs (C1)**, config (C2) | **Types + stubs (D1)**, z-factor (D3) |
| **1** | **FREEZE POINT: all interfaces committed as stubs** | | | |
| 1–3 | API client (A2), Upload, Dashboard (A3–A4) | DB (B3), ingestion (B4), SKU endpoints (B5) | Client, prompts, suggester (C3–C5) | Safety stock, ROP, EOQ, recommend (D4–D7), sample data (D14) |
| **3** | **SYNC: real `core` and `ai` delivered to B** | | | |
| 3–5 | SKU detail, Show-the-Math, Evaluation (A5–A7) | Forecast, anomaly, recommendation, scenario endpoints (B6–B9) | Explainer, proposer, guardrails (C6–C9) | Anomaly, forecasting, evaluation (D8–D11) |
| 5–6.5 | Anomaly review, Scenarios, AI UI (A8–A10) | AI endpoints, errors, Docker (B10–B12) | AI tests/eval (C10), demo script (C11) | Simulation, scenarios (D12–D13), tests/docs (D15) |
| **6.5** | **SYNC: full end-to-end run on the sample dataset** | | | |
| 6.5–8 | UX states, tests (A11–A12) | Integration tests, README (B13–B14) | Deck, rehearsal (C12) | Bug-fix support on numbers |

Each owner fixes bugs **in their own area** during integration; cross-area bugs are reported to the owner, not patched by someone else.

---

## 10. Integration Checklist (run together at hour 6.5)

- [ ] `docker compose up` starts frontend, backend and database from a clean clone (B)
- [ ] Upload `data/sample/sales.csv` → SKU list appears (A + B)
- [ ] Spec Examples A, B, C produce 70 / 65 / 428 via the API (D + B)
- [ ] Forecast evaluation shows baseline vs proposed; baseline-wins banner works (D + A)
- [ ] Anomalies flagged; user relabel persists with source `user` (D + B + A)
- [ ] With `AI_ENABLED=true`: label suggestions, explanation, adjustment proposals work (C + B + A)
- [ ] With `AI_ENABLED=false`: entire flow still works; explanation uses template fallback (C + B + A)
- [ ] Scenario panel: demand surge and supplier delay show sensible before/after (D + B + A)
- [ ] Demo script runs in under 7 minutes without edits (C)

---

## 11. Who Owns What — Quick Lookup

| Question | Owner |
|---|---|
| "The reorder point looks wrong" | **D** |
| "The forecast metric is off" | **D** |
| "The API returns the wrong field / status code" | **B** |
| "CSV upload fails" | **B** (structure) / **D** (anomaly flags) |
| "The chart doesn't show / UI glitch" | **A** |
| "The AI explanation says a number that isn't in the result" | **C** |
| "AI label is wrong" | **C** (prompt/guardrails) — user decides the final label |
| "Docker/compose won't start" | **B** |
| "Demo flow or slides" | **C** |
| "Synthetic data looks unrealistic" | **D** |
| "Need a new field in an API response" | Ask **B**; B asks **D**/**C** if the data comes from them |
