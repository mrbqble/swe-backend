"""Admin: FAQ management + public FAQ endpoint."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.admin.model import AdminUser, FAQ

AdminFaqRouter = APIRouter(tags=["admin"])
PublicFaqRouter = APIRouter(tags=["faq"])


def _faq_dict(faq: FAQ) -> dict[str, Any]:
    return {
        "id": faq.id,
        "question_ru": faq.question_ru,
        "question_kz": faq.question_kz,
        "answer_ru": faq.answer_ru,
        "answer_kz": faq.answer_kz,
        "sort_order": faq.sort_order,
        "is_published": faq.is_published,
        "created_at": faq.created_at.isoformat(),
        "updated_at": faq.updated_at.isoformat(),
    }


@AdminFaqRouter.get("/faq")
async def admin_list_faq(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all FAQ items including unpublished."""
    rows = (
        await db.execute(select(FAQ).order_by(FAQ.sort_order, FAQ.id))
    ).scalars().all()
    return [_faq_dict(f) for f in rows]


@AdminFaqRouter.post("/faq")
async def admin_create_faq(
    body: dict,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a FAQ item."""
    if not body.get("question_ru") or not body.get("answer_ru"):
        raise ApplicationError("question_ru and answer_ru are required.")

    faq = FAQ(
        question_ru=body["question_ru"],
        question_kz=body.get("question_kz"),
        answer_ru=body["answer_ru"],
        answer_kz=body.get("answer_kz"),
        sort_order=int(body.get("sort_order", 0)),
        is_published=bool(body.get("is_published", False)),
    )
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return _faq_dict(faq)


@AdminFaqRouter.patch("/faq/{faq_id}")
async def admin_update_faq(
    faq_id: int,
    body: dict,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update any FAQ field."""
    faq = await db.get(FAQ, faq_id)
    if faq is None:
        raise ApplicationError("FAQ item not found.", status_code=404)

    allowed = {"question_ru", "question_kz", "answer_ru", "answer_kz", "sort_order", "is_published"}
    for field, value in body.items():
        if field in allowed:
            setattr(faq, field, value)

    faq.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(faq)
    return _faq_dict(faq)


@AdminFaqRouter.delete("/faq/{faq_id}")
async def admin_delete_faq(
    faq_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a FAQ item."""
    faq = await db.get(FAQ, faq_id)
    if faq is None:
        raise ApplicationError("FAQ item not found.", status_code=404)

    await db.delete(faq)
    await db.commit()
    return {"message": "Deleted"}


# ── Public FAQ (no auth) ──────────────────────────────────────────────────────

@PublicFaqRouter.get("/faq")  # public endpoint
async def public_faq(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List published FAQ items ordered by sort_order."""
    rows = (
        await db.execute(
            select(FAQ)
            .where(FAQ.is_published == True)  # noqa: E712
            .order_by(FAQ.sort_order, FAQ.id)
        )
    ).scalars().all()
    return [_faq_dict(f) for f in rows]
