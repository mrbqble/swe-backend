from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", summary="Placeholder endpoint")
async def read_products_placeholder() -> dict[str, str]:
    return {"detail": "products endpoint pending implementation"}
