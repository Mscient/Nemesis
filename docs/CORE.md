# CORE.md — Analytics Core Documentation

> **Owner: Member D** | Package: `stocksense_core` | Directory: `core/`

---

## Overview

`stocksense_core` is a **pure Python package** containing all deterministic, unit-tested inventory mathematics for StockSense. It has **zero imports** from `backend/`, `ai/`, FastAPI, or any database library. The only external dependencies are `pandas`, `numpy`, `scipy`, and `statsmodels`.

---

## Public API

```python
from stocksense_core import (
    service_level_to_z,
    detect_anomalies,
    clean_series,
    run_forecast,
    compute_recommendation,
    simulate,
    run_scenario,
)
```

---

## 1. Series Preparation (`series.py`)

**`build_daily_series(records) → pd.DataFrame`**

Converts a list of `SalesRecord` objects to a contiguous daily DataFrame:
- Sorts by date.
- Detects and marks duplicate dates (first occurrence kept).
- Fills calendar gaps (missing days → `units_sold=0`, `on_hand` forward-filled, `promo_flag=0`).

---

## 2. z-Factor (`engine/z_factor.py`)

**`service_level_to_z(p: float) → float`**

Returns the inverse-normal CDF (standard-normal quantile) for service level `p ∈ (0, 1)`.

| Service level | z |
|---|---|
| 90% | 1.282 |
| 95% | 1.645 |
| 97.5% | 1.960 |
| 99% | 2.326 |

Raises `ValueError` if `p ≤ 0` or `p ≥ 1`.

---

## 3. Safety Stock & Reorder Point (`engine/recommendation.py`)

### Safety Stock

**Constant lead time (σL = 0):**
```
SS = z × σd × √L       → rounded UP to whole unit
```

**Variable lead time (σL > 0):**
```
SS = z × √(L × σd²  +  μd² × σL²)   → rounded UP
```

If `σd = 0`: `SS = 0` and a warning is added ("No demand variability observed").

### Reorder Point
```
ROP = (μd × L) + SS
```
Trigger: place an order when `inventory_position ≤ ROP`.

`inventory_position = on_hand + on_order`

### Economic Order Quantity
```
EOQ = √(2 × D × S / H)
```
- `D` = annual demand (`μd × 365`)
- `S` = order cost per order
- `H` = holding cost per unit per year

Constraints applied in order: **ceil → enforce MOQ → round to pack_size → cap at max_storage**.

Raises `ValueError` if `H ≤ 0` or `S ≤ 0`.

### Worked Examples (from spec §6.5)

| Example | Inputs | Result |
|---|---|---|
| A | μd=10, L=5, SS=20 | ROP = **70** |
| B | μd=10, σd=4, L=5, z=1.645, σL=0 | SS = **15**, ROP = **65** |
| C | D=3650/yr, S=50, H=2 | EOQ = **428** |

---

## 4. Anomaly Detection (`anomaly/detection.py`)

**`detect_anomalies(records, promo_windows=(), threshold=3.5) → list[AnomalyFlag]`**

### Statistical Detection
- Rolling 14-day median and MAD.
- `robust_z = |x − median| / (1.4826 × MAD)` — configurable threshold (default 3.5).

### Rule-Based Flags
| Rule | Flag | Class |
|---|---|---|
| `units_sold < 0` | `negative` | `data_error` |
| Duplicate date | `duplicate_date` | `data_error` |
| Value > 10× median AND > 100 units above median | `impossible_magnitude` | `data_error` |
| `units_sold = 0` while `on_hand = 0` | `stockout_censored` | `stockout_censored` |
| Within a `promo_window` | `promotion` | `promotion` |
| `robust_z > threshold` (no other rule) | `robust_z>3.5` | `unknown` |

### Classification Priority
`data_error > stockout_censored > promotion > unknown`

---

## 5. Anomaly Treatment (`anomaly/treatment.py`)

**`clean_series(records, flags, user_decisions=None) → CleanedSeries`**

| Class | Default treatment |
|---|---|
| `data_error` | Exclude |
| `stockout_censored` | Exclude (never treat as low demand) |
| `promotion` | Keep (promo flag already set) |
| `unknown` | Keep (surfaced to user for review) |

`user_decisions` is a dict `{ISO-date: {"treatment": "exclude" | "keep"}}` that overrides the default.

---

## 6. Forecasting (`forecast/`)

### Models (`models.py`)

| Role | Model | When used |
|---|---|---|
| Baseline | Naive (last value) | Always |
| Baseline | Seasonal-naive (same weekday last week) | Always |
| Baseline | 14-day moving average | Always |
| Proposed | **Holt-Winters** (additive weekly seasonality) | ≥ 28 days history |
| Proposed (fallback) | Simple exponential smoothing | 14–27 days |
| Proposed (fallback) | 14-day moving average | < 14 days |

### Evaluation (`evaluation.py`)

1. Sort by date; holdout = last 20% (minimum 14 days).
2. Fit all models on training slice only.
3. Compute MAE, RMSE, WAPE, Bias on holdout.
4. **Chosen-model rule:** if proposed WAPE ≤ best-baseline WAPE → use proposed; otherwise use best baseline and warn.
5. Refit chosen model on **full series** for the final forecast.

### Runner (`runner.py`)

**`run_forecast(cleaned, horizon_days=14, holdout_fraction=0.2, adjustments=()) → ForecastResult`**

- Builds daily series → evaluates models → picks winner → refits on full series.
- `confidence`: `"high"` (WAPE < 15%), `"medium"` (< 30%), `"low"` (≥ 30% or < 28 days history).
- `adjustments`: user-approved `Adjustment` objects applied as multipliers on future dates.

---

## 7. Cost Model (`cost/model.py`)

**`compute_cost(params, average_inventory, number_of_orders, unmet_units, days) → CostBreakdown`**

```
Holding cost  = (H / 365) × average_inventory × days
Ordering cost = S × number_of_orders
Stockout cost = P × unmet_units
Total cost    = Holding + Ordering + Stockout
```

---

## 8. Monte Carlo Simulation (`simulation/monte_carlo.py`)

**`simulate(params, forecast, recommendation, n_runs=1000, seed=42, horizon_days=90) → SimulationResult`**

Per run:
1. Daily demand drawn from `Normal(mu_d, sigma_d)`.
2. Lead times drawn from `Normal(L, sigma_L)` (or fixed if `sigma_L = 0`).
3. **(ROP, Q) policy:** place order of Q when `inventory_position ≤ ROP`.
4. Track unmet demand, average on-hand, and order count.
5. Compute total cost per run via cost model.

Output: `stockout_probability`, `expected_unmet_units`, `average_inventory`, `total_cost_p10/p50/p90`.
Results are fully reproducible for a given `seed`.

---

## 9. Scenario Simulation (`simulation/scenarios.py`)

**`run_scenario(params, forecast, scenario, ...) → ScenarioComparison`**

| Scenario type | Effect |
|---|---|
| `demand_surge` | Multiplies first `surge_days` predictions by `(1 + surge_pct/100)` |
| `supplier_delay` | Increases `lead_time_days` by `delay_days`; σL adjusted via quadrature |
| `combined` | Both at once |

Returns before-vs-after `SimulationResult`s, `delta_rop`, `delta_safety_stock`, and a plain-language `recommended_action`.

---

## 10. Assumptions & Limitations

- Demand is modelled as **Normal**; heavy-tailed demand may underestimate stockout risk.
- Holt-Winters assumes **weekly seasonality** (period = 7). For different cycles, use regression.
- The (ROP, Q) policy is **continuous review**; periodic-review settings are not modelled.
- Monte Carlo results are **estimates under stated assumptions**, not guarantees.
- All sample data in `data/sample/` is **SYNTHETIC**.

---

## 11. Running Tests

```bash
cd core
pip install -e .[dev]   # or: pip install -e .
pytest tests/ -v
```

Key test fixtures (from spec §6.5):

| Test | Expected |
|---|---|
| `test_example_a_rop` | ROP = 70 |
| `test_example_b_safety_stock` | SS = 15 |
| `test_example_b_rop` | ROP = 65 |
| `test_example_c_eoq` | EOQ = 428 |
