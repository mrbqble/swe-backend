from fastapi import APIRouter

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.get("", summary="Placeholder")
async def read_complaints_placeholder() -> dict[str, str]:
    return {"detail": "Complaints endpoint pending implementation"}
