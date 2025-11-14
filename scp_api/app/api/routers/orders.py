from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", summary="Placeholder")
async def read_orders_placeholder() -> dict[str, str]:
    return {"detail": "Orders endpoint pending implementation"}
