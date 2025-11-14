from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", summary="Placeholder endpoint")
async def read_notifications_placeholder() -> dict[str, str]:
    return {"detail": "notifications endpoint pending implementation"}
