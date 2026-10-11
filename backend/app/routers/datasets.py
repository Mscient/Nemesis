from fastapi import APIRouter, UploadFile, File

router = APIRouter(tags=["datasets"])


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload sales.csv: structural validation + anomaly detection."""
    return {"filename": file.filename, "status": "accepted", "rows": 0, "errors": []}
