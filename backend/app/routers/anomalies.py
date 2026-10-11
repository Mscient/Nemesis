from fastapi import APIRouter

router = APIRouter(tags=["anomalies"])


@router.get("/skus/{sku}/anomalies")
def list_anomalies(sku: str):
    return []


@router.post("/skus/{sku}/anomalies/suggest")
async def suggest_anomaly_labels(sku: str):
    return {"suggestions": []}


@router.patch("/anomalies/{anomaly_id}")
def reclassify_anomaly(anomaly_id: int):
    return {"id": anomaly_id}
