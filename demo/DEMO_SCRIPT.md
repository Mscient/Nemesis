# StockSense Demo Script

> Estimated time: 5–7 minutes | **SYNTHETIC data** — labelled on every screen

## Pre-demo checklist
- [ ] `docker compose up` is running — frontend at http://localhost:5173
- [ ] `data/sample/sales.csv` is ready (run `python data/generate_synthetic.py` if not)
- [ ] AI status banner is visible (enabled or disabled — note for audience)
- [ ] Fallback plan: if LLM fails, AI_ENABLED=false mode works fully

---

## Step 1 — Upload (60 s)
1. Navigate to **Upload & Setup**.
2. Upload `data/sample/sales.csv`.
3. Show the success summary: 3 SKUs, anomaly flags detected.

## Step 2 — Dashboard (30 s)
4. Point to SKU status chips: OK / REORDER / AT_RISK.
5. Note the **[SYNTHETIC DATA]** badge.

## Step 3 — Recommendation & Show the Math (90 s)
6. Click **WATER-500** → SKU Detail.
7. Open **Show the Math** panel.
8. Walk through: service level 95% → z=1.645, SS formula, ROP formula, EOQ.
9. Expected values: SS=15, ROP=65, EOQ=428.

## Step 4 — Forecast Evaluation (45 s)
10. Click **Forecast Evaluation** tab.
11. Show baseline vs proposed metrics (MAE, RMSE, WAPE, bias).
12. If baseline wins, show the honest banner.

## Step 5 — Anomaly Review (45 s)
13. Navigate to **Anomaly Review**.
14. Show the flagged `data_error` (day 50, units_sold = -5) for WATER-500.
15. If AI enabled, click **Suggest with AI** → show suggestion + user confirm flow.
16. Reclassify one anomaly manually → `source: user` badge appears.

## Step 6 — Scenario Panel (60 s)
17. Navigate to **Scenario Panel** for JUICE-1L.
18. Set demand surge +30% for 14 days → run.
19. Show before/after: ROP increases, stockout risk increases, recommended action.
20. Try supplier delay +3 days → show ROP and safety stock increase.

## Step 7 — AI Explain (30 s)
21. On the recommendation card, click **Explain this recommendation**.
22. Show plain-language explanation. Point out `used_fallback` if AI is off.

## Fallback plan (if network / LLM down)
- Switch to `AI_ENABLED=false` — all features except AI suggestions work.
- Explanation falls back to deterministic template (still demonstrates the feature).
