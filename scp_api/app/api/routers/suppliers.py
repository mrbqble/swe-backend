from fastapi import APIRouter

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", summary="Placeholder")
async def read_suppliers_placeholder() -> dict[str, str]:
    return {"detail": "Suppliers endpoint pending implementation"}
