from fastapi import APIRouter

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("", summary="Placeholder endpoint")
async def read_complaints_placeholder() -> dict[str, str]:
    return {"detail": "complaints endpoint pending implementation"}
