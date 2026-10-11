# StockSense API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness check |
| GET | `/api/ai/status` | AI enabled? provider / model |
| POST | `/api/datasets` | Upload `sales.csv` |
| GET | `/api/skus` | List SKUs with status |
| GET | `/api/skus/{sku}` | SKU detail |
| PUT | `/api/skus/{sku}/params` | Update SKU parameters |
| GET | `/api/skus/{sku}/history` | Sales history |
| GET | `/api/skus/{sku}/forecast` | Forecast + evaluation |
| GET | `/api/skus/{sku}/evaluation` | Baseline vs proposed |
| GET | `/api/skus/{sku}/anomalies` | Flagged anomalies |
| POST | `/api/skus/{sku}/anomalies/suggest` | AI label suggestions |
| PATCH | `/api/anomalies/{id}` | User reclassify |
| POST | `/api/skus/{sku}/recommendation` | Compute ROP / SS / EOQ |
| POST | `/api/skus/{sku}/scenarios` | What-if simulation |
| POST | `/api/skus/{sku}/explain` | AI plain-language explanation |
| POST | `/api/skus/{sku}/adjustments/propose` | AI forecast adjustment proposals |
| GET | `/api/skus/{sku}/adjustments` | List adjustments |
| PATCH | `/api/adjustments/{id}` | Accept / reject adjustment |

## Error envelope

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "field": "lead_time_days" } }
```

All fields use `snake_case`.
