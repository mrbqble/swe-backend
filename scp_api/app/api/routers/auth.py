from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("", summary="Placeholder endpoint")
async def read_auth_placeholder() -> dict[str, str]:
    return {"detail": "auth endpoint pending implementation"}
