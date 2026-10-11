# StockSense — Pitch Deck Outline

> Hackathon presentation | 3–5 minute pitch
> Owner: Member C

---

## Slide 1 — Problem (30 s)

**Headline:** Inventory is a $1.1 trillion problem — and most small businesses manage it by gut feel.

- Ordering too late → stockouts, lost sales
- Ordering too early → cash tied up in unsold stock
- Unusual demand (promotions, errors, disruptions) → inaccurate forecasts
- Existing ERP systems (SAP, NetSuite) are too complex and expensive for SMBs

**Visual:** Split screen — empty shelf (stockout) vs. overflowing warehouse (overstock)

---

## Slide 2 — Solution (45 s)

**Headline:** StockSense — an explainable, adaptive replenishment decision engine

Five core capabilities:
1. 📈 **Smart replenishment** — calculates reorder points using demand forecasts and safety stock formulas
2. 🔍 **Anomaly detection** — flags unusual sales (promotions, errors, stockouts) before they corrupt forecasts
3. 📊 **Honest forecast evaluation** — compares models on held-out data; admits when the simple baseline wins
4. 🌩️ **Scenario simulation** — simulates demand surges and supplier delays before they happen
5. 💡 **Full explainability** — every recommendation shows the formula, the numbers, and the assumptions

**Visual:** Screenshot of the "Show the Math" panel

---

## Slide 3 — Who Uses It (20 s)

| User | Need |
|---|---|
| Small business owner | "Order X units now" without ERP complexity |
| Replenishment planner | Daily reorder list they can trust and override |
| Procurement lead | Lead-time risk & supplier delay what-ifs |
| Finance / ops manager | Cost trade-offs and stockout risk numbers |

---

## Slide 4 — AI Integration (40 s)

**AI does three things — and only three:**

1. **Suggests** anomaly labels (promotion / data_error / stockout_censored / unknown)
2. **Explains** recommendations in plain language (shop owner or planner mode)
3. **Proposes** forecast adjustments for upcoming events

**AI never:** computes ROP, safety stock, EOQ, or any inventory number.

**Guardrails:**
- Number-consistency check — hallucinated numbers trigger automatic fallback
- Class allowlist — unknown classes are rejected
- Multiplier cap — AI adjustments bounded to 0.5× – 2.0×
- System fully works with `AI_ENABLED=false`

**Visual:** AI guardrails diagram (propose → user approves → accepted)

---

## Slide 5 — Architecture (30 s)

```
React Frontend → FastAPI Backend → stocksense_core (deterministic math)
                               → stocksense_ai    (optional AI layer)
                               → PostgreSQL
```

- One Python backend (in-process forecasting — no extra microservice)
- Provider-agnostic LLM client (Anthropic / OpenAI / mock)
- Docker Compose: `docker compose up` → full app

---

## Slide 6 — Results (30 s)

On the synthetic dataset (3 SKUs, 180 days):

| Metric | Result |
|---|---|
| Spec example A (ROP=70) | ✅ Passes |
| Spec example B (SS=15, ROP=65) | ✅ Passes |
| Spec example C (EOQ=428) | ✅ Passes |
| AI off → still fully functional | ✅ |
| Demand surge +30% → ROP increases | ✅ |
| Supplier delay +3 days → SS increases | ✅ |

---

## Slide 7 — Differentiation

| StockSense | Generic ERP |
|---|---|
| Shows every formula | Black box recommendation |
| Measures forecast accuracy on holdout | No forecast evaluation |
| Admits when baseline wins | Always claims improvement |
| AI explains, never decides | AI may replace human judgment |
| Open architecture, Docker-based | Proprietary, expensive |

---

## Pre-Demo Checklist

- [ ] `docker compose up` — verify frontend and backend are healthy
- [ ] Upload `data/sample/sales.csv` — check 3 SKUs appear
- [ ] Verify WATER-500: ROP=65, SS=15, EOQ=428
- [ ] Verify AI status banner (note enabled/disabled for audience)
- [ ] Open `/docs` (FastAPI) on a second tab — shows the full API
- [ ] Have `.env` with `AI_ENABLED=false` ready to switch if LLM fails
- [ ] Practice the "Show the Math" walkthrough — 90 seconds max
- [ ] Time the full script once — target: under 7 minutes

---

## Talking Points (Key Messages)

1. **"Nothing is a black box."** — Every number comes from a formula the user can inspect.
2. **"We measure honesty."** — Forecast evaluation on held-out data; we say when the baseline wins.
3. **"AI assists, humans decide."** — Every AI suggestion requires user approval before affecting the calculation.
4. **"It works without AI."** — Deterministic fallbacks for every AI feature.
5. **"Built for real disruptions."** — Scenario simulation lets planners test before the event, not after.
