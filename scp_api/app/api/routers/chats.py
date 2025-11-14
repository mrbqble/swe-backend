from fastapi import APIRouter

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", summary="Placeholder endpoint")
async def read_chats_placeholder() -> dict[str, str]:
    return {"detail": "chats endpoint pending implementation"}
