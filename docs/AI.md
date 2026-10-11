# StockSense — AI Layer Documentation (`stocksense_ai`)

> Owner: **Member C** | Package: `ai/stocksense_ai/` | Spec ref: §12

---

## Overview

`stocksense_ai` is an optional AI layer that *suggests*, *explains*, and *proposes* — it **never computes inventory numbers**. The system is fully usable with `AI_ENABLED=false`.

Dependency direction: `backend/` imports `stocksense_ai`; `stocksense_ai` never imports `backend/` or `core/`.

---

## Configuration

Set via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `AI_ENABLED` | `false` | Enable the AI layer |
| `LLM_PROVIDER` | `mock` | `anthropic` / `openai` / `mock` |
| `LLM_MODEL` | `mock-model` | Model name (provider-specific) |
| `LLM_API_KEY` | _(empty)_ | Provider API key |
| `LLM_TIMEOUT_S` | `30` | Per-call timeout in seconds |
| `LLM_MAX_TOKENS` | `1024` | Max output tokens |
| `LLM_MAX_RETRIES` | `2` | Retry attempts on failure |

The `mock` provider is deterministic, requires no API key, and is used for tests and offline demo.

---

## Public API

```python
import stocksense_ai as ai

# Sync
ai.is_enabled()     -> bool
ai.status()         -> AIStatus

# Async — never raise; return fallbacks on error
await ai.suggest_anomaly_labels(items)        -> AnomalySuggestionBatch
await ai.explain_recommendation(req)         -> ExplainResult
await ai.propose_forecast_adjustments(req)   -> AdjustmentProposalBatch
```

---

## Three AI Tasks

### 1. Anomaly Label Suggestion (`suggest_anomaly_labels`)

- **Input:** `list[AnomalyContext]` — anomaly data fields (no secrets)
- **Output:** `AnomalySuggestionBatch` — one suggestion per item
- **Allowed classes:** `promotion | data_error | stockout_censored | unknown`
- **Guardrails:**
  - Class validated against the allowlist; invalid → `unknown`
  - Confidence clamped to `[0.0, 1.0]`
  - Batched in groups of 10 to respect token limits
  - Any missing item in LLM response → `unknown, confidence=0`
- **Fallback (AI off):** all items → `unknown, confidence=0`

### 2. Recommendation Explanation (`explain_recommendation`)

- **Input:** `ExplainRequest` — full recommendation dict + audience (`shop_owner | planner`)
- **Output:** `ExplainResult` — plain-language text + `used_fallback` flag
- **Guardrails:**
  - **Number-consistency check:** every number in the explanation must appear in the input recommendation; rogue numbers → template fallback
  - Two deterministic templates for the two audiences
- **Fallback (AI off or check fails):** deterministic template, `used_fallback=True`

### 3. Forecast Adjustment Proposals (`propose_forecast_adjustments`)

- **Input:** `AdjustmentRequest` — event notes + forecast summary
- **Output:** `AdjustmentProposalBatch` — bounded proposals
- **Guardrails:**
  - `multiplier` hard-clamped to `[0.5, 2.0]`
  - `end_date >= start_date` enforced; invalid → skipped
  - `status` is always `"proposed"` (user must accept)
  - `source` is always `"ai"`
  - `event_notes` JSON-encoded before insertion (prompt-injection defence)
- **Fallback (AI off or error):** empty proposals list

---

## Guardrails Summary

| Risk | Mitigation |
|---|---|
| Hallucinated numbers | Number-consistency check in explainer |
| Bad anomaly class | Allowlist validation |
| Extreme multipliers | Hard clamp `[0.5, 2.0]` |
| Prompt injection | User text JSON-encoded before insertion |
| LLM timeout / error | Retry with exponential backoff; then fallback |
| Secrets in prompt | Only needed data fields sent; no DB credentials |
| AI override of user choices | `status="proposed"` only; user must accept |

---

## Audit Records

Every LLM call produces an `AIAuditRecord`:

```python
class AIAuditRecord(BaseModel):
    task: str              # "suggest_anomaly_labels" | "explain_recommendation" | ...
    model: str             # e.g. "claude-3-5-sonnet-20241022"
    prompt_version: str    # "v1"
    latency_ms: float
    validation_outcome: str  # "ok" | "number_consistency_failed" | "llm_error: ..."
```

Backend (B) persists these to `ai_audit_log`.

---

## File Layout

```
ai/
├── pyproject.toml
├── stocksense_ai/
│   ├── __init__.py          # Public API exports
│   ├── config.py            # AIConfig — env var reader (C2)
│   ├── ai_status.py         # is_enabled(), status()
│   ├── client.py            # Provider-agnostic LLM client (C3)
│   ├── schemas.py           # All Pydantic models (C1)
│   ├── suggester.py         # Anomaly label suggester (C5)
│   ├── explainer.py         # Recommendation explainer (C6)
│   ├── proposer.py          # Forecast adjustment proposer (C7)
│   └── prompts/
│       ├── __init__.py
│       └── templates.py     # Versioned prompt templates (C4)
├── tests/
│   └── test_ai.py           # Full pytest test suite (C10)
└── eval/
    └── score_labels.py      # Label accuracy scoring script (C10)
```

---

## Running Tests

```bash
cd ai
pip install -e ".[dev]"       # or: pip install -e . pytest
pytest tests/ -v
```

No API key needed — tests use the mock provider.

---

## Evaluating Label Accuracy

```bash
# Requires D's ground truth file
python ai/eval/score_labels.py \
    --ground-truth data/sample/anomaly_ground_truth.csv \
    --output-json ai/eval/results.json
```

---

## Adding a New Provider

1. Add a new `async def _<provider>_complete(prompt, cfg)` function in `client.py`.
2. Add the provider name to the `if/elif` chain in `complete()`.
3. Add the provider name to the `.env.example` comment.
4. Write a test that patches `complete` and verifies the new integration.

---

## What AI Must Not Do

- Compute ROP, safety stock, EOQ, or any inventory number.
- Override user-selected service levels.
- Change `status` from `"proposed"` to `"accepted"`.
- Raise exceptions to the caller.
- Send data beyond what is required for the task.
