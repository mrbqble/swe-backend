"""Admin: audit log endpoint."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db
from app.modules.admin.model import AdminAction, AdminUser
from app.utils.pagination import create_pagination_response

AdminAuditRouter = APIRouter(tags=["admin"])


@AdminAuditRouter.get("/audit")
async def list_audit(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin_id: int | None = Query(None),
    target_type: str | None = Query(None),
    target_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Paginated audit log, newest first."""
    base = select(AdminAction)

    if admin_id is not None:
        base = base.where(AdminAction.admin_id == admin_id)
    if target_type:
        base = base.where(AdminAction.target_type == target_type)
    if target_id is not None:
        base = base.where(AdminAction.target_id == target_id)
    if date_from:
        try:
            base = base.where(AdminAction.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            base = base.where(AdminAction.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(AdminAction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()

    items = [
        {
            "id": a.id,
            "admin_id": a.admin_id,
            "action_type": a.action_type,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "before_data": a.before_data,
            "after_data": a.after_data,
            "ip": a.ip,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]

    return create_pagination_response(items, page, limit, total).model_dump()
