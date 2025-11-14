from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="Placeholder")
async def read_notifications_placeholder() -> dict[str, str]:
    return {"detail": "Notifications endpoint pending implementation"}
