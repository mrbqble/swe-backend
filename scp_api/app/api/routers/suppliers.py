from fastapi import APIRouter

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", summary="Placeholder endpoint")
async def read_suppliers_placeholder() -> dict[str, str]:
    return {"detail": "suppliers endpoint pending implementation"}
