from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", summary="Placeholder endpoint")
async def read_orders_placeholder() -> dict[str, str]:
    return {"detail": "orders endpoint pending implementation"}
