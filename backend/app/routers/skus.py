from fastapi import APIRouter

router = APIRouter(tags=["skus"])


@router.get("/skus")
def list_skus():
    """List all SKUs with their current status."""
    return []


@router.get("/skus/{sku}")
def get_sku(sku: str):
    """Get SKU detail including parameters."""
    return {"sku": sku}


@router.put("/skus/{sku}/params")
def update_sku_params(sku: str):
    """Update SKU parameters."""
    return {"sku": sku}


@router.get("/skus/{sku}/history")
def get_sku_history(sku: str):
    """Get cleaned and raw sales history."""
    return []


@router.get("/skus/{sku}/forecast")
def get_forecast(sku: str, horizon: int = 14):
    """Get demand forecast + holdout evaluation."""
    return {}


@router.get("/skus/{sku}/evaluation")
def get_evaluation(sku: str):
    """Baseline vs proposed holdout comparison."""
    return {}


@router.post("/skus/{sku}/recommendation")
def compute_recommendation(sku: str):
    """Compute ROP, SS, order quantity."""
    return {}


@router.get("/skus/{sku}/adjustments")
def list_adjustments(sku: str):
    return []


@router.post("/skus/{sku}/adjustments/propose")
async def propose_adjustments(sku: str):
    return []
