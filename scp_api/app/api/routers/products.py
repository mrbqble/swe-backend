from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", summary="Placeholder")
async def read_products_placeholder() -> dict[str, str]:
    return {"detail": "Products endpoint pending implementation"}
