from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", summary="Placeholder")
async def read_users_placeholder() -> dict[str, str]:
    return {"detail": "Users endpoint pending implementation"}


@router.get("/{user_id}", summary="Fetch user placeholder")
async def read_user(user_id: int) -> dict[str, str]:
    return {"detail": f"User {user_id} placeholder"}


@router.get("/error", summary="Force error")
async def trigger_error() -> None:
    raise RuntimeError("Simulated failure")
