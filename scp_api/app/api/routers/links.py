from fastapi import APIRouter

router = APIRouter(prefix="/links", tags=["links"])


@router.get("", summary="Placeholder endpoint")
async def read_links_placeholder() -> dict[str, str]:
    return {"detail": "links endpoint pending implementation"}
