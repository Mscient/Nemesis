from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["ai"])


@router.get("/ai/status")
def ai_status():
    return {
        "enabled": settings.ai_enabled,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
    }


@router.post("/skus/{sku}/explain")
async def explain_recommendation(sku: str):
    return {"explanation": "AI disabled — template fallback.", "used_fallback": True}


@router.patch("/adjustments/{adjustment_id}")
def update_adjustment(adjustment_id: int):
    return {"id": adjustment_id}
