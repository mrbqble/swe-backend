from fastapi import APIRouter

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", summary="Placeholder")
async def read_chats_placeholder() -> dict[str, str]:
    return {"detail": "Chats endpoint pending implementation"}
