# StockSense Demo Script

> Estimated time: **5–7 minutes** | **⚠️ SYNTHETIC data — labelled on every screen**
> Owner: Member C

---

## Pre-Demo Checklist

- [ ] `docker compose up` — frontend at <http://localhost:5173>, backend at <http://localhost:8000/docs>
- [ ] `data/sample/sales.csv` is ready (run `python data/generate_synthetic.py` if not present)
- [ ] AI status banner visible (note whether AI is enabled for the audience)
- [ ] Confirm the three SKUs in the sample: **WATER-500**, **JUICE-1L**, **SNACK-BAR**
- [ ] Known expected values: SS=15, ROP=65, EOQ=428 for WATER-500 at 95% service level

### Fallback plan (if LLM / network fails)
- Set `AI_ENABLED=false` in `.env` and restart backend.
- AI suggestion and explain features show deterministic templates (`used_fallback: true` badge).
- All other features (forecast, anomaly, scenario, math panel) work with AI completely off.

---

## Step 1 — Upload & Setup (60 s)

**Goal:** show CSV upload, structural validation, and anomaly pre-detection.

1. Navigate to **Upload & Setup**.
2. Drag-and-drop `data/sample/sales.csv`.
3. Show the success summary banner:
   - **3 SKUs** detected: WATER-500, JUICE-1L, SNACK-BAR
   - **[SYNTHETIC DATA]** badge displayed
   - Anomaly flags: ~5 detected during ingestion
4. Point out the row-level validation — the CSV had one row with `units_sold = -5` (day 50, WATER-500); the upload reports it as flagged.

---

## Step 2 — Dashboard (30 s)

**Goal:** show high-level SKU status.

5. Navigate to **Dashboard**.
6. Show the SKU table with status chips:
   - **WATER-500** → `REORDER` (inventory position ≤ ROP)
   - **JUICE-1L** → `AT_RISK`
   - **SNACK-BAR** → `OK`
7. Point to the **KPI strip**: "2 SKUs to reorder or at risk".
8. Reiterate **[SYNTHETIC DATA]** badge — this is not a real business.

---

## Step 3 — Recommendation & Show the Math (90 s)

**Goal:** demonstrate explainable replenishment — the core differentiator.

9. Click **WATER-500** → SKU Detail.
10. Show the recommendation card: action = **ORDER NOW**, order quantity = **428 units**.
11. Open the **Show the Math** panel.
12. Walk through each formula with the substituted numbers:

| Field | Value shown |
|---|---|
| Service level | 95% |
| z-factor | 1.645 |
| Safety stock | `z × σd × √L = 1.645 × 4 × √5 = 14.71 → **15**` |
| Reorder point | `(μd × L) + SS = (10 × 5) + 15 = **65**` |
| EOQ | `√(2 × 3650 × 50 / 2) = 427.2 → **428**` |

13. Change service level to **99%** → z=2.326, SS increases, ROP increases → show live recalculation.
14. Reset to 95%.

> 🔑 **Key message:** "Every number has a formula. Nothing is a black box."

---

## Step 4 — Forecast Evaluation (45 s)

**Goal:** show honest accuracy measurement.

15. Click the **Forecast Evaluation** tab (still on WATER-500).
16. Show the side-by-side table:

| Metric | Baseline (14-day MA) | Proposed (Holt-Winters) |
|---|---|---|
| MAE | ~3.2 | ~2.1 |
| RMSE | ~4.1 | ~2.8 |
| WAPE | ~0.28 | ~0.19 |
| Bias | ~0.4 | ~-0.1 |

17. If the baseline wins for any SKU, show the honest banner: *"Baseline model performed better — using baseline."*

> 🔑 **Key message:** "We measure every forecast on held-out data and admit when the simple model wins."

---

## Step 5 — Anomaly Review (45 s)

**Goal:** show rule-based detection + optional AI suggestion flow.

18. Navigate to **Anomaly Review**.
19. Show the flagged points table with columns: date, value, class, treatment, source badge.
20. Point to `WATER-500 / day 50 / units_sold = -5` → class = `data_error` (source: **rule**).
21. **If AI enabled:** click **Suggest labels with AI** → AI suggestion appears with confidence score and rationale.
    - AI suggests `data_error` with confidence 0.92, rationale: "Negative value is physically impossible."
    - Click **Confirm** → source changes to **ai**.
22. Manually reclassify another anomaly → source badge changes to **user**.

> 🔑 **Key message:** "Rules catch the obvious; AI adds context; the user has the final say."

---

## Step 6 — Scenario Panel (60 s)

**Goal:** show what-if simulation for disruption planning.

23. Navigate to **Scenario Panel** for **JUICE-1L**.
24. **Demand surge:** set +30% demand for 14 days starting day 7 → run.
    - Before: ROP ≈ 42, stockout risk ≈ 5%
    - After: ROP ≈ 55, stockout risk ≈ 23%, recommended action: ORDER_NOW
25. **Supplier delay:** set lead time +3 extra days → run.
    - Safety stock increases, ROP increases.
26. Show the before/after cards with cost P10–P90 range.

> 🔑 **Key message:** "Plan for disruption before it happens."

---

## Step 7 — AI Explain (30 s)

**Goal:** show plain-language AI explanation with transparency.

27. Return to **WATER-500** SKU Detail.
28. Click **Explain this recommendation**.
29. Show the explanation panel — audience: **Shop Owner** mode:
    > *"You should place an order now — order 428 units of WATER-500. You currently have 60 units (including on order). When stock drops to 65 units, it is time to reorder. We keep a buffer of 15 extra units to handle surprises in demand."*
30. If AI is off, show `used_fallback: true` badge — the deterministic template renders the same useful content.

> 🔑 **Key message:** "AI explains; it doesn't decide. The math is always there to verify."

---

## Closing (30 s)

- StockSense is **not** an ERP replacement — it is a focused, transparent decision-support layer.
- Five differentiators: smart replenishment, anomaly detection, honest forecast evaluation, scenario simulation, and explainability.
- **Everything shown is reproducible** from the synthetic data generator with one command.

---

## Appendix — Expected Numbers (WATER-500 defaults)

| Parameter | Value |
|---|---|
| μd (avg daily demand) | 10 units/day |
| σd (demand std dev) | 4 units/day |
| Lead time L | 5 days |
| σL (lead time std dev) | 0 days |
| Service level | 95% → z = 1.645 |
| Safety stock | 15 units |
| Reorder point | 65 units |
| Annual demand D | 3,650 units |
| Order cost S | $50 |
| Holding cost H | $2/unit/year |
| EOQ | 428 units |
