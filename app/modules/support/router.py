"""Support / suggestions routes."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.support.model import Suggestion
from app.modules.user.model import User
from app.utils.pagination import create_pagination_response

SupportRouter = APIRouter(prefix="/support", tags=["support"])
AdminSuggestionRouter = APIRouter(tags=["admin"])


class SubmitSuggestionRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000)


def _suggestion_dict(s: Suggestion, user: User | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": s.id,
        "user_id": s.user_id,
        "text": s.text,
        "is_read": s.is_read,
        "created_at": s.created_at.isoformat(),
    }
    if user is not None:
        d["user"] = {
            "id": user.id,
            "phone": user.phone,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    return d


@SupportRouter.post("/suggestions")
async def submit_suggestion(
    body: SubmitSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    suggestion = Suggestion(user_id=current_user.id, text=body.text)
    db.add(suggestion)
    await db.commit()
    return {"message": "Suggestion submitted. Thank you!"}


@AdminSuggestionRouter.get("/suggestions")
async def list_suggestions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    is_read: bool | None = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    base = select(Suggestion)
    if is_read is not None:
        base = base.where(Suggestion.is_read == is_read)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Suggestion.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()

    user_ids = [s.user_id for s in rows if s.user_id is not None]
    user_map: dict[int, User] = {}
    if user_ids:
        users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        user_map = {u.id: u for u in users}

    items = [_suggestion_dict(s, user_map.get(s.user_id) if s.user_id else None) for s in rows]
    return create_pagination_response(items, page, limit, total).model_dump()


@AdminSuggestionRouter.patch("/suggestions/{suggestion_id}/read")
async def mark_suggestion_read(
    suggestion_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    suggestion = await db.get(Suggestion, suggestion_id)
    if suggestion is None:
        raise ApplicationError("Suggestion not found.", status_code=404)
    suggestion.is_read = True
    await db.commit()
    await db.refresh(suggestion)
    return _suggestion_dict(suggestion)
