from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("", summary="Auth placeholder")
async def read_auth_placeholder() -> dict[str, str]:
    return {"detail": "auth endpoint pending implementation"}
