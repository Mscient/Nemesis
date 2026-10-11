from fastapi import APIRouter

router = APIRouter(tags=["scenarios"])


@router.post("/skus/{sku}/scenarios")
def run_scenario(sku: str):
    """Run a what-if simulation (demand surge / supplier delay / combined)."""
    return {}
