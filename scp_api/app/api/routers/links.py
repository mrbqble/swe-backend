from fastapi import APIRouter

router = APIRouter(prefix="/links", tags=["Links"])


@router.get("", summary="Placeholder")
async def read_links_placeholder() -> dict[str, str]:
    return {"detail": "Links endpoint pending implementation"}
