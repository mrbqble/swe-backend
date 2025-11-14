from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", summary="Placeholder endpoint")
async def read_users_placeholder() -> dict[str, str]:
    return {"detail": "users endpoint pending implementation"}
