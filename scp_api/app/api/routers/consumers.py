from fastapi import APIRouter

router = APIRouter(prefix="/consumers", tags=["Consumers"])


@router.get("", summary="Placeholder")
async def read_consumers_placeholder() -> dict[str, str]:
    return {"detail": "Consumers endpoint pending implementation"}
