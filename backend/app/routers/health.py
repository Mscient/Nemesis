from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
