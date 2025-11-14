from fastapi import APIRouter

router = APIRouter(prefix="/consumers", tags=["consumers"])


@router.get("", summary="Placeholder endpoint")
async def read_consumers_placeholder() -> dict[str, str]:
    return {"detail": "consumers endpoint pending implementation"}
